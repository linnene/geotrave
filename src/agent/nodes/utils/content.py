"""Shared utilities for extracting content and token usage from LLM responses."""

import json
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel


def format_json_schema(model_cls: Type[BaseModel]) -> str:
    """Return JSON Schema string for a Pydantic model, for LLM format instructions."""
    return json.dumps(model_cls.model_json_schema(), indent=2, ensure_ascii=False)


def extract_content_str(raw_result: Any) -> str:
    """Extract a plain string from an LLM response, handling list content blocks."""
    content = raw_result.content if hasattr(raw_result, "content") else str(raw_result)

    if isinstance(content, list):
        return "".join(
            t.get("text", "") if isinstance(t, dict) else str(t) for t in content
        )
    return str(content)


def extract_token_usage(raw_result: Any) -> Optional[Dict[str, int]]:
    """Extract token usage from LLM response metadata, or None if unavailable."""
    if not hasattr(raw_result, "response_metadata"):
        return None
    metadata = getattr(raw_result, "response_metadata", {}) or {}
    usage = metadata.get("token_usage", {})
    if not usage:
        return None
    return {
        "prompt": usage.get("prompt_tokens", 0),
        "completion": usage.get("completion_tokens", 0),
        "total": usage.get("total_tokens", 0),
    }
