"""Phase 3 persistence — observation buffer + /cognitive/biometrics USD prim.

BufferUsdStore implements the Phase 2 BiometricStore.upsert interface, so the
HTTP handler is unchanged. One upsert writes two sinks:

  1. ObservationBuffer organic partition, kind='biometric_prior' (excluded from
     behavioral feature windows; idempotent on calendar date).
  2. /cognitive/biometrics on the real USD stage via CognitiveStage.author —
     the native USD mechanism, time-sampled by a date code (YYYYMMDD), so a
     re-POST for the same date overwrites that time sample rather than appending.

The read helpers (today_prior / recent_priors) back the Phase 4 seed.
"""

from __future__ import annotations

import json
from typing import Optional

from .schema import BiometricPrior

PRIM_PATH = "/cognitive/biometrics"


def date_timecode(calendar_date: str) -> int:
    """YYYY-MM-DD → YYYYMMDD integer USD time code (one sample per date,
    human-readable in the .usda, monotonic, date-unique → idempotent)."""
    return int(calendar_date.replace("-", ""))


class BufferUsdStore:
    def __init__(self, buffer, stage=None) -> None:
        """buffer: engine.observation_buffer.ObservationBuffer.
        stage: engine.cognitive_stage.CognitiveStage (or None → buffer-only,
        e.g. when pxr/USD is unavailable)."""
        self._buffer = buffer
        self._stage = stage

    def upsert(self, prior: BiometricPrior) -> bool:
        date = prior.calendar_date
        obs_json = prior.model_dump_json()
        _obs_id, created = self._buffer.add_biometric_prior(obs_json, date)
        if self._stage is not None:
            # Native USD mechanism — same author() set_capacity would use.
            self._stage.author(PRIM_PATH, date_timecode(date), json.loads(obs_json))
            self._stage.save()
        return created

    # ---- read path (Phase 4) -------------------------------------------------
    def today_prior(self, calendar_date: str) -> Optional[BiometricPrior]:
        raw = self._buffer.biometric_prior_json(calendar_date)
        return BiometricPrior.model_validate_json(raw) if raw else None

    def recent_priors(self, limit: int = 14) -> list[BiometricPrior]:
        return [
            BiometricPrior.model_validate_json(r)
            for r in self._buffer.recent_biometric_prior_jsons(limit)
        ]


def default_store() -> "BufferUsdStore":
    """Production store: the engine's observation buffer + real USD stage.
    Degrades to buffer-only if pxr/USD is unavailable."""
    from harlo.engine.engine_config import BUFFER_DB_PATH, STAGE_DIR
    from harlo.engine.observation_buffer import ObservationBuffer

    buffer = ObservationBuffer(BUFFER_DB_PATH)
    stage = None
    try:
        from harlo.engine.stage_factory import create_stage

        stage = create_stage(stage_dir=STAGE_DIR)
    except Exception:
        stage = None
    return BufferUsdStore(buffer, stage)
