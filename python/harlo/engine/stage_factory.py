"""Stage factory — create MockUsdStage or CognitiveStage based on config.

Commandment 4: Same interface regardless of backend.
"""

from __future__ import annotations

from typing import Any, Optional


def create_stage(
    use_real_usd: Optional[bool] = None,
    stage_dir: Optional[str] = None,
    thresholds: Optional[dict[str, float]] = None,
    in_memory: bool = False,
) -> Any:
    """Create a stage backend.

    If use_real_usd is None, reads from engine_config.USE_REAL_USD.
    Returns either CognitiveStage (real USD) or MockUsdStage (dict-based).
    Both implement the same interface.
    """
    if use_real_usd is None:
        from .engine_config import USE_REAL_USD
        use_real_usd = USE_REAL_USD

    if use_real_usd:
        from .cognitive_stage import CognitiveStage
        return CognitiveStage(
            stage_dir=stage_dir,
            thresholds=thresholds,
            in_memory=in_memory,
        )
    else:
        from .mock_usd_stage import MockUsdStage
        return MockUsdStage(thresholds=thresholds)
