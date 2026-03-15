"""Domain-tuned verification depth.

Loads depth configuration from config/verification_depth.yaml.
Higher-stakes domains get deeper verification.
"""

from __future__ import annotations

from pathlib import Path

_DEPTH_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "verification_depth.yaml"

# Hardcoded fallback matching verification_depth.yaml
_DEFAULTS = {
    "medical": 3,
    "financial": 3,
    "trading": 3,
    "legal": 3,
    "research": 2,
    "analysis": 2,
    "general": 2,
    "creative": 1,
    "vfx": 1,
    "brainstorm": 1,
}
_DEFAULT_DEPTH = 2

_loaded: dict | None = None


def _load_config() -> dict:
    """Load depth config from YAML (or use hardcoded defaults)."""
    global _loaded
    if _loaded is not None:
        return _loaded

    try:
        import yaml
        with open(_DEPTH_CONFIG_PATH) as f:
            data = yaml.safe_load(f)
        _loaded = data.get("domains", _DEFAULTS)
        return _loaded
    except Exception:
        _loaded = _DEFAULTS
        return _loaded


def get_depth(domain: str) -> int:
    """Get verification depth for a domain.

    Args:
        domain: Domain name (e.g., "medical", "creative", "general").

    Returns:
        Verification depth (1=shallow, 2=standard, 3=deep).
    """
    config = _load_config()
    return config.get(domain.lower(), _DEFAULT_DEPTH)


def get_max_depth() -> int:
    """Get the maximum allowed verification depth."""
    return 3
