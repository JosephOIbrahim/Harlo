"""Write-through sync strategy tests.

Per Phase 3 design §6.
"""
from __future__ import annotations

import os

import pytest


def _import_persistence_or_skip():
    try:
        from harlo.usd_lite.persistence import read, write  # noqa: F401
    except ImportError as exc:
        pytest.skip(f"persistence layer unavailable: {exc}")


def test_persist_writes_file(tmp_path):
    _import_persistence_or_skip()
    from harlo.sync import write_through
    from harlo.usd_lite.stage import BrainStage

    stage = BrainStage()
    target = str(tmp_path / "wt.usda")
    write_through.persist(stage, target)

    assert os.path.exists(target), "write_through.persist did not produce a file"


def test_persist_round_trip_equality(tmp_path):
    _import_persistence_or_skip()
    from harlo.sync import write_through
    from harlo.usd_lite.persistence import read
    from harlo.usd_lite.stage import BrainStage
    from harlo.usd_lite.prims import SessionPrim, RetrievalPath

    stage = BrainStage(session=SessionPrim(
        current_session_id="wt_test",
        exchange_count=42,
        surprise_rolling_mean=0.0,
        surprise_rolling_std=0.0,
        last_query_surprise=0.0,
        last_retrieval_path=RetrievalPath.SYSTEM_2,
    ))
    target = str(tmp_path / "wt_rt.usda")
    write_through.persist(stage, target)

    read_back = read(target)
    assert read_back == stage


def test_persist_prim_records_path_argument(tmp_path):
    """persist_prim accepts a prim_path argument (currently unused)."""
    _import_persistence_or_skip()
    from harlo.sync import write_through
    from harlo.usd_lite.stage import BrainStage

    stage = BrainStage()
    target = str(tmp_path / "wt_prim.usda")
    # Should not raise; prim_path is recorded but not yet used.
    write_through.persist_prim(stage, "/Brain/Session", target)
    assert os.path.exists(target)
