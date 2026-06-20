"""Profile loading from YAML config."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


_DEFAULT_PATH = Path(__file__).resolve().parents[3] / "config" / "default_profile.yaml"


@dataclass
class Profile:
    """Harlo modulation profile."""

    # Modulation parameters
    s_nm: float = 0.0
    association_radius: int = 10
    escalation_threshold: float = 0.7
    decay_lambda: float = 0.05
    tangent_tolerance: float = 1.0
    verbosity: str = "normal"

    # Structural anchors - ALWAYS gain 1.0 (Rule 10)
    anchors: List[str] = field(
        default_factory=lambda: ["SAFETY", "CONSENT", "KNOWLEDGE", "CONSTITUTIONAL"]
    )

    # Inquiry settings
    inquiry_depth: str = "standard"
    inquiry_consent_level: str = "standard"
    inquiry_boundaries: List[str] = field(default_factory=list)

    # Motor settings
    motor_session_consent: int = 0
    motor_scope: Dict[str, Any] = field(default_factory=dict)


def _parse_yaml_simple(text: str) -> dict:
    """Minimal YAML parser for flat/simple config structures.
    Fallback when PyYAML is not installed.
    """
    result: dict = {}
    stack: list = [(result, -1)]

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        # Pop stack to correct level
        while len(stack) > 1 and stack[-1][1] >= indent:
            stack.pop()

        if stripped.startswith("- "):
            val = stripped[2:].strip()
            parent = stack[-1][0]
            if isinstance(parent, list):
                parent.append(val)
            continue

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()

            if not val:
                # Could be dict or list - peek ahead not possible, default dict
                new_container: Any = {}
                stack[-1][0][key] = new_container
                stack.append((new_container, indent))
            elif val == "[]":
                stack[-1][0][key] = []
                stack.append((stack[-1][0][key], indent))
            elif val == "{}":
                stack[-1][0][key] = {}
            else:
                # Parse scalar
                try:
                    parsed = json.loads(val)
                except (json.JSONDecodeError, ValueError):
                    parsed = val
                stack[-1][0][key] = parsed

    return result


def _load_yaml(path: Path) -> dict:
    """Load YAML file using PyYAML if available, else simple parser."""
    text = path.read_text(encoding="utf-8")
    if _HAS_YAML:
        return yaml.safe_load(text) or {}
    return _parse_yaml_simple(text)


def load_profile(path: str | Path | None = None) -> Profile:
    """Load a Profile from YAML config file."""
    p = Path(path) if path else _DEFAULT_PATH
    raw = _load_yaml(p)

    mod = raw.get("modulation", {})
    anchors_list = raw.get("anchors", ["SAFETY", "CONSENT", "KNOWLEDGE", "CONSTITUTIONAL"])
    inquiry = raw.get("inquiry", {})
    motor = raw.get("motor", {})

    return Profile(
        s_nm=float(mod.get("s_nm", 0.0)),
        association_radius=int(mod.get("association_radius", 10)),
        escalation_threshold=float(mod.get("escalation_threshold", 0.7)),
        decay_lambda=float(mod.get("decay_lambda", 0.05)),
        tangent_tolerance=float(mod.get("tangent_tolerance", 1.0)),
        verbosity=str(mod.get("verbosity", "normal")),
        anchors=anchors_list,
        inquiry_depth=str(inquiry.get("depth", "standard")),
        inquiry_consent_level=str(inquiry.get("consent_level", "standard")),
        inquiry_boundaries=inquiry.get("boundaries", []),
        motor_session_consent=int(motor.get("session_consent", 0)),
        motor_scope=motor.get("scope", {}),
    )
