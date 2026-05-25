"""Extractor behavior tests (extraction_strategy.md Section 7)."""

from __future__ import annotations

from harness.path_d.pvh.extractor import (
    MISSING_FIELDS,
    NO_SESSION_SENTINEL,
    ExtractorError,
    iter_sessions,
)
from src.train_predictor import _build_sliding_window, _encode_observation

import pytest


def test_session_grouping(obs_db):
    db = obs_db([{"session_id": "live", "exchange_index": i} for i in range(5)])
    sessions = list(iter_sessions(db))
    assert len(sessions) == 1
    assert sessions[0].session_id == "live"
    assert sessions[0].metadata.obs_count == 5


def test_window_count(obs_db):
    db = obs_db([{"session_id": "s", "exchange_index": i} for i in range(10)])
    sess = list(iter_sessions(db))[0]
    assert sess.metadata.window_count == 8  # 10 - 3 + 1


def test_ordering_determinism(obs_db):
    # Insert rows out of exchange_index order; extractor must sort.
    rows = [{"session_id": "s", "exchange_index": i} for i in [3, 0, 4, 1, 2]]
    db = obs_db(rows)
    sess = list(iter_sessions(db))[0]
    exchange_order = [o.exchange_index for o in sess.observations]
    assert exchange_order == [0, 1, 2, 3, 4]


def test_short_session(obs_db):
    db = obs_db([{"session_id": "s", "exchange_index": i} for i in range(2)])
    sess = list(iter_sessions(db))[0]
    assert sess.metadata.below_window_threshold is True
    assert sess.metadata.window_count == 0
    assert sess.windows == ()


def test_malformed_json_skipped(obs_db):
    db = obs_db(
        [{"session_id": "s", "exchange_index": i} for i in range(3)],
        raw_extra=[("bad1", "{not valid json", "organic", None)],
    )
    sessions = list(iter_sessions(db))
    # 3 good obs in one session; bad row skipped, counted as dropped.
    assert len(sessions) == 1
    assert sessions[0].metadata.obs_count == 3
    assert sessions[0].metadata.dropped_rows == 1


def test_empty_db(obs_db):
    db = obs_db([])
    assert list(iter_sessions(db)) == []


def test_missing_fields_metadata(obs_db):
    db = obs_db([{"session_id": "s", "exchange_index": i} for i in range(3)])
    sess = list(iter_sessions(db))[0]
    assert sess.metadata.missing_fields == MISSING_FIELDS
    # v1: deflection columns are structurally None
    for w in sess.windows:
        assert w.deflection_flag is None
        assert w.overshoot_baseline_flag is None
        assert w.lead_time is None
        assert w.predicted is None  # no predictor supplied


def test_missing_session_id_sentinel(obs_db):
    db = obs_db([{"session_id": "", "exchange_index": i} for i in range(3)])
    sess = list(iter_sessions(db))[0]
    assert sess.session_id == NO_SESSION_SENTINEL


def test_db_unavailable_raises():
    with pytest.raises(ExtractorError):
        list(iter_sessions("/nonexistent/path/to/observations.db"))


def test_feature_parity_with_training_encoder(obs_db):
    """Extractor windows must encode identically to _build_sliding_window (D47)."""
    db = obs_db([{"session_id": "s", "exchange_index": i} for i in range(6)])
    sess = list(iter_sessions(db))[0]
    traj = list(sess.observations)
    X, y = _build_sliding_window(traj, 3)
    assert len(sess.windows) == len(X)
    for k, w in enumerate(sess.windows):
        feats: list[float] = []
        for o in w.observations:
            feats.extend(_encode_observation(o))
        assert feats == X[k], f"feature mismatch at window {k}"
        assert [w.actual["momentum"], w.actual["burnout"], w.actual["energy"], w.actual["burst_phase"]] == list(y[k])
