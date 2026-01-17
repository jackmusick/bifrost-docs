"""
Reindex State Service.

Manages reindex job state in Redis for multi-worker support.
State is stored with 24-hour TTL and accessible from any API/worker instance.
"""

import json
import time
from dataclasses import asdict, dataclass
from typing import Literal

from redis.asyncio import Redis

REINDEX_STATE_KEY = "reindex:state:{job_id}"
REINDEX_CURRENT_JOB_KEY = "reindex:current_job"
REINDEX_CANCEL_KEY = "reindex:cancel:{job_id}"
REINDEX_STATE_TTL = 86400  # 24 hours

ReindexStatus = Literal["running", "cancelling", "cancelled", "completed", "failed"]


@dataclass
class ReindexProgress:
    """Progress state for a reindex job."""

    job_id: str
    status: ReindexStatus
    total: int
    processed: int
    errors: int
    current_entity_type: str | None
    error_message: str | None
    started_at: float
    completed_at: float | None


class ReindexStateService:
    """
    Service for managing reindex job state in Redis.

    Enables multiple workers to update progress and any API instance
    to read the current state.
    """

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def start_job(self, job_id: str, total: int) -> None:
        """Initialize a new reindex job in Redis."""
        state = ReindexProgress(
            job_id=job_id,
            status="running",
            total=total,
            processed=0,
            errors=0,
            current_entity_type=None,
            error_message=None,
            started_at=time.time(),
            completed_at=None,
        )
        await self.redis.setex(
            REINDEX_STATE_KEY.format(job_id=job_id),
            REINDEX_STATE_TTL,
            json.dumps(asdict(state)),
        )
        await self.redis.set(REINDEX_CURRENT_JOB_KEY, job_id)

    async def update_progress(
        self,
        job_id: str,
        processed: int,
        errors: int,
        entity_type: str,
    ) -> None:
        """Update job progress - called by worker after each entity."""
        key = REINDEX_STATE_KEY.format(job_id=job_id)
        state_json = await self.redis.get(key)
        if state_json:
            state = json.loads(state_json)
            state["processed"] = processed
            state["errors"] = errors
            state["current_entity_type"] = entity_type
            await self.redis.setex(key, REINDEX_STATE_TTL, json.dumps(state))

    async def complete_job(self, job_id: str) -> None:
        """Mark job as completed."""
        key = REINDEX_STATE_KEY.format(job_id=job_id)
        state_json = await self.redis.get(key)
        if state_json:
            state = json.loads(state_json)
            state["status"] = "completed"
            state["completed_at"] = time.time()
            await self.redis.setex(key, REINDEX_STATE_TTL, json.dumps(state))

    async def fail_job(self, job_id: str, error_message: str) -> None:
        """Mark job as failed with error message."""
        key = REINDEX_STATE_KEY.format(job_id=job_id)
        state_json = await self.redis.get(key)
        if state_json:
            state = json.loads(state_json)
            state["status"] = "failed"
            state["error_message"] = error_message
            state["completed_at"] = time.time()
            await self.redis.setex(key, REINDEX_STATE_TTL, json.dumps(state))

    async def get_job(self, job_id: str) -> ReindexProgress | None:
        """Get job state by ID."""
        state_json = await self.redis.get(REINDEX_STATE_KEY.format(job_id=job_id))
        if state_json:
            data = json.loads(state_json)
            return ReindexProgress(**data)
        return None

    async def get_current_job(self) -> ReindexProgress | None:
        """Get the most recent job."""
        job_id = await self.redis.get(REINDEX_CURRENT_JOB_KEY)
        if job_id:
            job_id_str = job_id.decode() if isinstance(job_id, bytes) else job_id
            return await self.get_job(job_id_str)
        return None

    async def is_job_running(self) -> bool:
        """Check if any job is currently running."""
        current = await self.get_current_job()
        return current is not None and current.status in ("running", "cancelling")

    async def request_cancel(self, job_id: str) -> bool:
        """
        Request graceful cancellation of a job.

        Sets the cancel flag and updates status to 'cancelling'.
        Worker will check this flag and stop at next entity boundary.

        Returns True if cancellation was requested, False if job not found/not running.
        """
        key = REINDEX_STATE_KEY.format(job_id=job_id)
        state_json = await self.redis.get(key)
        if not state_json:
            return False

        state = json.loads(state_json)
        if state["status"] not in ("running", "cancelling"):
            return False

        # Set cancel flag
        await self.redis.setex(
            REINDEX_CANCEL_KEY.format(job_id=job_id),
            REINDEX_STATE_TTL,
            "1",
        )

        # Update status to cancelling
        state["status"] = "cancelling"
        await self.redis.setex(key, REINDEX_STATE_TTL, json.dumps(state))
        return True

    async def is_cancelled(self, job_id: str) -> bool:
        """Check if cancellation has been requested for this job."""
        cancel_flag = await self.redis.get(REINDEX_CANCEL_KEY.format(job_id=job_id))
        return cancel_flag is not None

    async def mark_cancelled(self, job_id: str) -> None:
        """Mark job as cancelled (called by worker after stopping)."""
        key = REINDEX_STATE_KEY.format(job_id=job_id)
        state_json = await self.redis.get(key)
        if state_json:
            state = json.loads(state_json)
            state["status"] = "cancelled"
            state["completed_at"] = time.time()
            await self.redis.setex(key, REINDEX_STATE_TTL, json.dumps(state))

        # Clean up cancel flag
        await self.redis.delete(REINDEX_CANCEL_KEY.format(job_id=job_id))

    async def force_cancel(self, job_id: str) -> bool:
        """
        Force cancel a job immediately.

        Clears all state regardless of worker status. Use when worker
        is not responding or job is stuck.

        Returns True if job was found and cancelled, False otherwise.
        """
        key = REINDEX_STATE_KEY.format(job_id=job_id)
        state_json = await self.redis.get(key)
        if not state_json:
            return False

        state = json.loads(state_json)

        # Update state to cancelled
        state["status"] = "cancelled"
        state["completed_at"] = time.time()
        state["error_message"] = "Force cancelled by administrator"
        await self.redis.setex(key, REINDEX_STATE_TTL, json.dumps(state))

        # Clear current job pointer if this was the active job
        current_job_id = await self.redis.get(REINDEX_CURRENT_JOB_KEY)
        if current_job_id:
            current_job_id_str = (
                current_job_id.decode() if isinstance(current_job_id, bytes) else current_job_id
            )
            if current_job_id_str == job_id:
                await self.redis.delete(REINDEX_CURRENT_JOB_KEY)

        # Clean up cancel flag
        await self.redis.delete(REINDEX_CANCEL_KEY.format(job_id=job_id))

        return True
