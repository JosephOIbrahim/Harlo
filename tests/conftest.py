"""Shared pytest configuration for the Harlo test suite.

Triage rationale (Test Infra, 2026-05-09):
-------------------------------------------
The full pytest sweep had 53 failures + 16 errors + 1 collection error
when run against a fresh venv. Root-cause split:

  Class A — pip-installable optional deps (65 of 70):
      sentence_transformers   (python/harlo/encoder/semantic_encoder.py:13)
      anthropic               (python/harlo/provider/claude.py:11)
    Resolution: install the [dev] extra:  pip install -e ".[dev]"
    See INSTALL.md "Run the test suite" section.

  Class B — model artifact not on disk (5 of 70):
      models/cognitive_predictor_v1.joblib (XGBoost predictor)
    This is NOT a pip dep — it is a binary artifact distributed
    out-of-band. A fresh checkout will not have it. Tests that hard-
    require it must skip gracefully when it is missing, otherwise
    the suite is not runnable in CI / on a fresh clone.

The `requires_predictor_model` marker below covers Class B. It is the
ONLY skip mechanism added by triage — Class A is solved by [dev]
install, not by silently skipping the dep'd tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Repo root = parent of tests/
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PREDICTOR_MODEL = _REPO_ROOT / "models" / "cognitive_predictor_v1.joblib"


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers so pytest --strict-markers stays clean."""
    config.addinivalue_line(
        "markers",
        "requires_predictor_model: skip when models/cognitive_predictor_v1.joblib "
        "is not present on disk. The XGBoost predictor is a binary artifact, not a "
        "pip dependency — fresh clones will not have it. See tests/conftest.py "
        "Class B for full rationale.",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Apply skip to all items carrying the requires_predictor_model marker."""
    if _PREDICTOR_MODEL.exists():
        return  # Model is present — let the tests run.

    skip_marker = pytest.mark.skip(
        reason=(
            f"Predictor model artifact not found at {_PREDICTOR_MODEL.relative_to(_REPO_ROOT)}. "
            "This is a binary artifact (XGBoost .joblib), not a pip dep. "
            "Generate via training pipeline or restore from artifact storage to enable."
        )
    )
    for item in items:
        if "requires_predictor_model" in item.keywords:
            item.add_marker(skip_marker)
