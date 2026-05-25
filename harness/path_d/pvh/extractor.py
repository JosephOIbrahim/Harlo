"""Trajectory extraction from data/observations.db (read-only).

Implements extraction_strategy.md (Phase 1 design). Reads the observation
buffer via a read-only SQLite URI, groups rows into per-session trajectories,
orders them deterministically, and builds 3-observation windows.

Design decisions in force: D42 (ordering), D43 (short sessions emitted),
D44 (missing session_id sentinel), D45 (no ObservationBuffer.sample()),
D46 (v1 actual = state at window's final obs), D47 (reuse src encoder).

v1 caveat (D38/D39): predicted output is NOT a forecast — the reference model
has target leakage and no horizon. predicted ≈ actual by construction.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Iterator, Optional

from src.predict import CognitivePredictor  # D47: reuse, do not reimplement
from src.schemas import CognitiveObservation
from src.train_predictor import TARGET_NAMES

WINDOW_SIZE = 3
MISSING_FIELDS = ("delegate_id", "scaffolding_requirements", "intervention_type")
NO_SESSION_SENTINEL = "<no-session-id>"


class ExtractorError(RuntimeError):
    """Raised when the observation database cannot be read."""


@dataclass(frozen=True)
class Window:
    index: int  # the window's final observation index within the session
    observations: tuple[CognitiveObservation, CognitiveObservation, CognitiveObservation]
    actual: dict[str, int]  # D46: state at the final observation
    predicted: Optional[dict[str, int]] = None  # reference-model output; None if no predictor
    # v2 columns — structurally present, always None in v1 (D39):
    deflection_flag: None = None
    overshoot_baseline_flag: None = None
    lead_time: None = None


@dataclass(frozen=True)
class SessionMeta:
    obs_count: int
    window_count: int
    below_window_threshold: bool
    missing_fields: tuple[str, ...]
    dropped_rows: int
    ordering_warnings: tuple[str, ...]
    created_at_range: tuple[Optional[str], Optional[str]]


@dataclass(frozen=True)
class Session:
    session_id: str
    partition: str
    observations: tuple[CognitiveObservation, ...]
    windows: tuple[Window, ...]
    metadata: SessionMeta


@dataclass
class _Row:
    obs_id: str
    obs: CognitiveObservation
    partition: str
    created_at: Optional[str]


def _actual_state(obs: CognitiveObservation) -> dict[str, int]:
    """Extract the 4 target fields from an observation (parity with _encode_targets)."""
    return {
        "momentum": int(obs.state.momentum),
        "burnout": int(obs.state.burnout),
        "energy": int(obs.state.energy),
        "burst_phase": int(obs.dynamics.burst_phase),
    }


def _read_rows(db_path: str) -> tuple[list[_Row], int]:
    """Read all buffer rows read-only. Returns (parsed_rows, dropped_count)."""
    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:  # pragma: no cover - exercised via fixture
        raise ExtractorError(f"cannot open observation db read-only: {db_path}") from exc

    try:
        raw = conn.execute(
            "SELECT obs_id, observation_json, partition, created_at FROM observation_buffer"
        ).fetchall()
    except sqlite3.Error as exc:
        raise ExtractorError(f"cannot query observation_buffer in {db_path}") from exc
    finally:
        conn.close()

    rows: list[_Row] = []
    dropped = 0
    for obs_id, obs_json, partition, created_at in raw:
        try:
            obs = CognitiveObservation.model_validate_json(obs_json)
        except Exception:  # malformed JSON or schema mismatch -> skip (D5/§5)
            dropped += 1
            continue
        rows.append(_Row(obs_id=obs_id, obs=obs, partition=partition or "organic", created_at=created_at))
    return rows, dropped


def _order_key(row: _Row):
    """D42: exchange_index primary; tiebreaks observation_index, created_at, obs_id."""
    return (
        row.obs.exchange_index,
        row.obs.observation_index,
        row.created_at or "",
        row.obs_id,
    )


def _build_session(session_id: str, rows: list[_Row], dropped_for_group: int,
                   predictor: Optional[CognitivePredictor]) -> Session:
    ordering_warnings: list[str] = []

    # Detect created_at disagreeing with exchange_index order before sorting (§5).
    by_exchange = sorted(rows, key=_order_key)
    created_seq = [r.created_at for r in by_exchange if r.created_at]
    if created_seq != sorted(created_seq):
        ordering_warnings.append("created_at order disagrees with exchange_index; trusting exchange_index")

    partitions = {r.partition for r in by_exchange}
    if len(partitions) > 1:
        ordering_warnings.append(f"session spans multiple partitions: {sorted(partitions)}")
    partition = by_exchange[0].partition if by_exchange else "organic"

    observations = tuple(r.obs for r in by_exchange)
    created_ats = [r.created_at for r in by_exchange if r.created_at]
    created_range = (created_ats[0], created_ats[-1]) if created_ats else (None, None)

    windows: list[Window] = []
    if len(observations) >= WINDOW_SIZE:
        for i in range(WINDOW_SIZE - 1, len(observations)):
            win_obs = observations[i - (WINDOW_SIZE - 1): i + 1]
            predicted = predictor.predict(list(win_obs)) if predictor is not None else None
            windows.append(
                Window(
                    index=i,
                    observations=(win_obs[0], win_obs[1], win_obs[2]),
                    actual=_actual_state(win_obs[-1]),
                    predicted=predicted,
                )
            )

    meta = SessionMeta(
        obs_count=len(observations),
        window_count=len(windows),
        below_window_threshold=len(observations) < WINDOW_SIZE,
        missing_fields=MISSING_FIELDS,
        dropped_rows=dropped_for_group,
        ordering_warnings=tuple(ordering_warnings),
        created_at_range=created_range,
    )
    return Session(
        session_id=session_id,
        partition=partition,
        observations=observations,
        windows=tuple(windows),
        metadata=meta,
    )


def iter_sessions(
    db_path: str = "data/observations.db",
    predictor: Optional[CognitivePredictor] = None,
) -> Iterator[Session]:
    """Yield one Session per session_id, ordered, with 3-obs windows.

    Read-only. If `predictor` is supplied, each window carries the reference
    model's output in `predicted` (subject to the D38 leakage caveat); otherwise
    `predicted` is None.
    """
    rows, dropped = _read_rows(db_path)

    groups: dict[str, list[_Row]] = {}
    for row in rows:
        sid = row.obs.session_id or NO_SESSION_SENTINEL
        groups.setdefault(sid, []).append(row)

    # Dropped rows can't be attributed to a session (their JSON failed to parse),
    # so surface the total on the first emitted session for visibility.
    first = True
    if not groups:
        return
    for session_id in sorted(groups):
        yield _build_session(
            session_id,
            groups[session_id],
            dropped if first else 0,
            predictor,
        )
        first = False
