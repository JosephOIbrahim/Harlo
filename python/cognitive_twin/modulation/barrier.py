"""Blood-Brain Barrier: JSON schema validation for LLM output.

Rule 8: JSON Barrier uses jsonschema.validate(). Strip epigenetic_wash on write path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import jsonschema

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "config" / "barrier_schema.json"
_schema_cache: dict | None = None


def _load_schema() -> dict:
    """Load and cache the barrier schema."""
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return _schema_cache


def validate_llm_output(raw: str) -> dict:
    """Validate raw LLM output string against barrier schema.

    Args:
        raw: JSON string from LLM.

    Returns:
        Parsed and validated dict.

    Raises:
        json.JSONDecodeError: If raw is not valid JSON.
        jsonschema.ValidationError: If output does not match schema.
    """
    parsed = json.loads(raw)
    schema = _load_schema()
    jsonschema.validate(instance=parsed, schema=schema)
    return parsed


def strip_epigenetic_wash(validated: dict) -> dict:
    """Strip ephemeral epigenetic_wash from validated output.

    Returns ONLY core_memory. Mood is ephemeral. Facts are permanent.

    Args:
        validated: A dict that has already passed validate_llm_output().

    Returns:
        Dict containing only the core_memory key.
    """
    return {"core_memory": validated.get("core_memory", {})}
