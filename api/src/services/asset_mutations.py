"""Custom asset mutation service."""
import json
import logging
import re
from typing import Any

from src.services.llm import BaseLLMClient, LLMMessage, Role

logger = logging.getLogger(__name__)


def extract_field_updates(current_fields: dict[str, Any], instruction: str) -> dict[str, str]:
    """
    Extract field updates using heuristics.

    This is a simple pattern-matching approach. The LLM will do the real work.

    Args:
        current_fields: Current field values
        instruction: User instruction

    Returns:
        Dictionary of field updates (field_name -> new_value)
    """
    updates = {}

    # Simple pattern: "change X to Y", "update X to Y", "set X to Y"
    # Value pattern allows dots (for IPs), alphanumeric, underscores, hyphens
    patterns = [
        r"(?:change|update|set)\s+(\w+)\s+to\s+['\"]([^'\"]+)['\"]",  # "set location to 'New York'"
        r"(?:change|update|set)\s+(\w+)\s+to\s+([\w\.\-]+)",  # "change IP to 10.0.0.5"
        r"(?:and\s+)?(\w+)\s+to\s+([\w\.\-]+)",  # "and location to DC2"
        r"(\w+)\s*[:=]\s*([\w\.\-]+)",  # "IP: 10.0.0.5" or "IP=10.0.0.5"
    ]

    instruction_lower = instruction.lower()

    for pattern in patterns:
        matches = re.finditer(pattern, instruction_lower)
        for match in matches:
            field_name = match.group(1)
            field_value = match.group(2)

            # Try to match against current field names (case-insensitive)
            # Support partial matches (e.g., "IP" matches "ip_address")
            for current_field in current_fields:
                current_normalized = current_field.lower().replace("_", "")
                field_normalized = field_name.replace("_", "")

                # Check for exact match or if field_name is contained in current_field
                if (current_normalized == field_normalized or
                    current_normalized.startswith(field_normalized) or
                    field_normalized in current_normalized):
                    updates[current_field] = field_value
                    break

    return updates


class AssetMutationService:
    """Service for AI-powered custom asset field mutations."""

    def __init__(self, llm_client: BaseLLMClient):
        """
        Initialize asset mutation service.

        Args:
            llm_client: LLM client for field extraction
        """
        self.llm = llm_client

    async def generate_field_updates(
        self,
        asset_type: str,
        current_fields: dict[str, Any],
        user_instruction: str,
    ) -> tuple[dict[str, str], str]:
        """
        Generate field updates based on user instruction.

        Args:
            asset_type: Type of custom asset (e.g., "Server", "Network Device")
            current_fields: Current field values
            user_instruction: User's instruction

        Returns:
            Tuple of (field_updates, summary_of_changes)
        """
        system_prompt = """You are a data extraction expert.
Your task is to extract field updates from user instructions.

Return a JSON object with ONLY the fields that should be updated.
Do not include fields that are not mentioned in the instruction.

Example:
Instruction: "change IP to 10.0.0.5"
Current fields: {"ip_address": "10.0.0.1", "location": "DC1", "status": "active"}
Output: {"ip_address": "10.0.0.5"}

Return ONLY valid JSON, no explanations."""

        user_prompt = f"""Asset Type: {asset_type}
Current Fields: {json.dumps(current_fields, indent=2)}
User Instruction: {user_instruction}

Extract the field updates as JSON."""

        messages = [
            LLMMessage(role=Role.SYSTEM, content=system_prompt),
            LLMMessage(role=Role.USER, content=user_prompt),
        ]

        response = await self.llm.complete(messages, max_tokens=1000)
        content = response.content or "{}"

        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

            updates = json.loads(content)

            # Filter to only include existing fields
            filtered_updates = {
                k: v for k, v in updates.items()
                if k in current_fields
            }

            # Generate summary
            if filtered_updates:
                changes = ", ".join(f"{k} → {v}" for k, v in filtered_updates.items())
                summary = f"Updated {len(filtered_updates)} field(s): {changes}"
            else:
                summary = "No field changes detected"

            return filtered_updates, summary

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            # Fallback to heuristic extraction
            updates = extract_field_updates(current_fields, user_instruction)
            summary = f"Updated {len(updates)} field(s)" if updates else "No changes"
            return updates, summary
