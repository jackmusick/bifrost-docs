# Async Indexing Queue Design

## Problem

Asset indexing into vector storage currently happens synchronously in API router calls, causing:
1. **Slow API responses** - Each create/update waits for OpenAI embedding generation (100-500ms)
2. **No throttling** - Burst operations can overwhelm the OpenAI API

## Solution

Use `arq` (async Redis queue) to process indexing jobs asynchronously. This leverages existing Redis infrastructure.

## Architecture

**Current flow (synchronous):**
```
Router → await index_entity_for_search() → OpenAI API → DB → Response
         ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
         This blocks (100-500ms per entity)
```

**New flow (async with arq):**
```
Router → enqueue_job() → Response immediately (~1ms)
                ↓
         Redis Queue
                ↓
         Worker → index_entity_for_search() → OpenAI API → DB
```

## Components

### 1. Queue Interface (`src/services/indexing_queue.py`)

Provides simple functions for routers to enqueue indexing jobs:

```python
async def enqueue_index_entity(entity_type: str, entity_id: str, org_id: str) -> None
async def enqueue_remove_entity(entity_type: str, entity_id: str) -> None
```

### 2. Worker (`src/worker.py`)

arq worker configuration with task definitions:

- `index_entity_task` - Process single entity indexing
- `remove_entity_task` - Remove entity from index

Configuration:
- `max_jobs = 10` - Concurrent jobs per worker (throttling)
- `job_timeout = 60` - Seconds before timeout
- `max_tries = 3` - Retry failed jobs

### 3. Redis-Based Reindex State (`src/services/reindex_state.py`)

Replaces in-memory `_reindex_job_state` for multi-worker support:

- `start_job(job_id, total)` - Initialize job in Redis
- `update_progress(job_id, processed, errors, entity_type)` - Update from worker
- `get_job(job_id)` - Read state from any API instance
- `get_current_job()` - Get most recent job

State stored with 24-hour TTL. Workers publish progress via existing Redis pub/sub for real-time WebSocket updates.

### 4. Docker Worker Service

New service using same image as API, different entrypoint:

```yaml
worker:
  image: jackmusick/bifrost-docs-api:latest
  environment:
    BIFROST_DOCS_DATABASE_URL: postgresql+asyncpg://...
    BIFROST_DOCS_REDIS_URL: redis://redis:6379/0
  command: arq src.worker.WorkerSettings
```

Note: Worker does not need `BIFROST_DOCS_SECRET_KEY` (no Fernet decryption) or `BIFROST_DOCS_OPENAI_API_KEY` (reads from database).

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `api/src/worker.py` | arq worker configuration and task definitions |
| `api/src/services/indexing_queue.py` | Queue interface for routers |
| `api/src/services/reindex_state.py` | Redis-based job state management |

### Modified Files

| File | Change |
|------|--------|
| `api/pyproject.toml` | Add `arq>=0.26.0` dependency |
| `api/src/services/search_indexing.py` | Update to use queue instead of direct indexing |
| `api/src/routers/admin.py` | Update reindex to use Redis state + queue individual jobs |
| `api/src/routers/documents.py` | Replace `await index_entity_for_search()` with `await enqueue_index_entity()` |
| `api/src/routers/custom_assets.py` | Same change |
| `api/src/routers/passwords.py` | Same change |
| `api/src/routers/configurations.py` | Same change |
| `api/src/routers/locations.py` | Same change |
| `docker-compose.yml` | Add worker service |
| `docker-compose.dev.yml` | Add worker service with hot reload |

## Scaling

```bash
# Run multiple worker replicas
docker compose up -d --scale worker=3
```

Each worker handles 10 concurrent jobs, so 3 workers = 30 concurrent indexing operations.

## Trade-offs vs RabbitMQ

| Aspect | arq (Redis) | RabbitMQ |
|--------|-------------|----------|
| Message durability | Redis persistence (RDB/AOF) | Disk-backed queues |
| Delivery guarantees | At-least-once | At-least-once, exactly-once |
| Dead letter handling | Manual | Native DLX |
| Ops complexity | Reuse existing Redis | New service |
| Throughput | ~100k msg/sec | ~50k msg/sec |

arq is sufficient for background indexing where occasional retry is acceptable. Can migrate to RabbitMQ later if needed.

## Testing

- **Unit tests**: Mock queue, verify jobs enqueued correctly
- **Integration tests**: Run worker in test docker-compose, verify end-to-end indexing
