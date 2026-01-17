"""Document mutation service with Diataxis framework support."""
import logging
from typing import Literal

from src.services.llm import BaseLLMClient, LLMMessage, Role

logger = logging.getLogger(__name__)

DiataxisType = Literal["tutorial", "how-to", "reference", "explanation"]

# Diataxis framework structure templates
DIATAXIS_STRUCTURES = {
    "tutorial": """
# {title}

## What You'll Learn
- Learning objective 1
- Learning objective 2

## Prerequisites
- Prerequisite 1

## Step-by-Step Guide

### Step 1: [First Step]
Instructions...

### Step 2: [Second Step]
Instructions...

## Summary
What you've accomplished.

## Next Steps
Where to go from here.
""",
    "how-to": """
# {title}

## Problem
What problem does this solve?

## Prerequisites
- Prerequisite 1

## Steps

### 1. [First Action]
How to do it...

### 2. [Second Action]
How to do it...

## Verification
How to verify it worked.

## Troubleshooting
Common issues and solutions.
""",
    "reference": """
# {title}

## Overview
Brief description of what this documents.

## [Section 1]
Technical details...

## [Section 2]
Technical details...

## See Also
Related documentation.
""",
    "explanation": """
# {title}

## Introduction
What concept are we explaining?

## Background
Context and background information.

## How It Works
Detailed explanation of the concept.

## Why It Matters
Practical implications.

## Related Concepts
Links to related topics.
"""
}


def classify_document_type(
    content: str,
    document_name: str,
    user_instruction: str
) -> DiataxisType:
    """
    Classify document type using heuristics.

    Args:
        content: Document content
        document_name: Document title/name
        user_instruction: User's instruction (may hint at type)

    Returns:
        Document type according to Diataxis framework
    """
    content_lower = content.lower()
    name_lower = document_name.lower()
    combined = f"{name_lower} {content_lower}"

    # Tutorial indicators
    if any(keyword in combined for keyword in [
        "getting started", "tutorial", "learn", "introduction to",
        "step-by-step", "beginner", "first time"
    ]):
        return "tutorial"

    # How-to indicators
    if any(keyword in combined for keyword in [
        "how to", "troubleshoot", "fix", "solve", "configure",
        "setup", "install", "deploy"
    ]):
        return "how-to"

    # Reference indicators
    if any(keyword in combined for keyword in [
        "api", "reference", "specification", "documentation",
        "endpoint", "parameter", "configuration options"
    ]):
        return "reference"

    # Explanation indicators
    if any(keyword in combined for keyword in [
        "understanding", "concept", "why", "architecture",
        "overview", "explanation", "theory"
    ]):
        return "explanation"

    # Default to how-to for task-oriented content
    return "how-to"


def apply_diataxis_structure(doc_type: DiataxisType, content: str) -> str:
    """
    Apply Diataxis structure template to content.

    This is a simple template-based approach. The LLM will do the real work
    of fitting content into the structure.

    Args:
        doc_type: Type of document
        content: Original content

    Returns:
        Content with structure guidance
    """
    template = DIATAXIS_STRUCTURES[doc_type]
    return f"{template}\n\n<!-- Original content to incorporate:\n{content}\n-->"


class DocumentMutationService:
    """Service for AI-powered document mutations with Diataxis framework."""

    def __init__(self, llm_client: BaseLLMClient):
        """
        Initialize document mutation service.

        Args:
            llm_client: LLM client for content generation
        """
        self.llm = llm_client

    async def generate_cleaned_content(
        self,
        original_content: str,
        document_name: str,
        user_instruction: str,
    ) -> tuple[str, str]:
        """
        Generate cleaned and restructured content.

        Applies Diataxis framework based on document type inference.

        Args:
            original_content: Original document content
            document_name: Document title/name
            user_instruction: User's instruction (e.g., "clean this up")

        Returns:
            Tuple of (cleaned_content, summary_of_changes)
        """
        # Classify document type
        doc_type = classify_document_type(original_content, document_name, user_instruction)

        logger.info(f"Classified document '{document_name}' as {doc_type}")

        # Build prompt for LLM
        system_prompt = f"""You are a technical documentation expert.
Your task is to clean up and restructure documentation according to the Diataxis framework.

This document should be structured as a {doc_type.upper()}:
- Tutorial: Learning-oriented, step-by-step for beginners
- How-to: Task-oriented, solve a specific problem
- Reference: Information-oriented, technical descriptions
- Explanation: Understanding-oriented, clarify concepts

Apply appropriate structure, fix formatting issues, improve clarity, and ensure consistency.
Return ONLY the cleaned markdown content, no explanations."""

        user_prompt = f"""Document Name: {document_name}
Document Type: {doc_type}
User Instruction: {user_instruction}

Original Content:
{original_content}

Please clean up this document:
1. Fix any formatting issues (numbered lists, headings, code blocks)
2. Apply {doc_type} structure from Diataxis framework
3. Improve clarity and readability
4. Ensure consistent markdown formatting

Return the cleaned content in markdown format."""

        messages = [
            LLMMessage(role=Role.SYSTEM, content=system_prompt),
            LLMMessage(role=Role.USER, content=user_prompt),
        ]

        try:
            response = await self.llm.complete(messages, max_tokens=4000)
            cleaned_content = response.content

            if not cleaned_content:
                logger.warning(
                    f"LLM returned empty content for document '{document_name}'"
                )
                raise ValueError("LLM returned empty response")

        except Exception as e:
            logger.error(
                f"Failed to generate cleaned content for '{document_name}': {e}",
                exc_info=True
            )
            raise

        # Generate summary
        summary = f"Restructured as {doc_type}, fixed formatting, improved clarity"

        return cleaned_content, summary
