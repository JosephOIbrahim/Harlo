"""Checkpoint sync strategy tests.

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


def test_checkpoint_starts_clean():
    from harlo.sync import Checkpoint
    cp = Checkpoint()
    assert not cp.is_dirty()
    assert cp.dirty_paths() == frozenset()


def test_mark_dirty_tracks_paths():
    from harlo.sync import Checkpoint
    cp = Checkpoint()
    cp.mark_dirty("/Brain/Association/Traces/abc")
    cp.mark_dirty("/Brain/Composition/Layers/layer_001")
    cp.mark_dirty("/Brain/Association/Traces/abc")  # dedup
    assert cp.is_dirty()
    assert cp.dirty_paths() == frozenset({
        "/Brain/Association/Traces/abc",
        "/Brain/Composition/Layers/layer_001",
    })


def test_flush_no_op_when_clean(tmp_path):
    _import_persistence_or_skip()
    from harlo.sync import Checkpoint
    from harlo.usd_lite.stage import BrainStage

    cp = Checkpoint()
    target = str(tmp_path / "cp_clean.usda")
    wrote = cp.flush(BrainStage(), target)
    assert wrote is False
    assert not os.path.exists(target)


def test_flush_writes_when_dirty(tmp_path):
    _import_persistence_or_skip()
    from harlo.sync import Checkpoint
    from harlo.usd_lite.stage import BrainStage

    cp = Checkpoint()
    cp.mark_dirty("/Brain/Association/Traces/abc")

    target = str(tmp_path / "cp_dirty.usda")
    wrote = cp.flush(BrainStage(), target)
    assert wrote is True
    assert os.path.exists(target)
    # Dirty set cleared after flush
    assert not cp.is_dirty()


def test_flush_round_trip_equality(tmp_path):
    _import_persistence_or_skip()
    from harlo.sync import Checkpoint
    from harlo.usd_lite.persistence import read
    from harlo.usd_lite.stage import BrainStage
    from harlo.usd_lite.prims import (
        AssociationPrim, TracePrim,
    )
    from datetime import datetime, timezone

    sdr = [0] * 2048
    sdr[10] = sdr[100] = sdr[1000] = 1
    trace = TracePrim(
        trace_id="cp_test",
        sdr=sdr,
        content_hash="cp_hash",
        strength=0.9,
        last_accessed=datetime(2026, 4, 28, tzinfo=timezone.utc),
    )
    stage = BrainStage(association=AssociationPrim(traces={"cp_test": trace}))

    cp = Checkpoint()
    cp.mark_dirty("/Brain/Association/Traces/cp_test")

    target = str(tmp_path / "cp_rt.usda")
    cp.flush(stage, target)
    read_back = read(target)
    assert read_back == stage


def test_clear_drops_dirty_without_writing(tmp_path):
    """clear() abandons the dirty set without persisting."""
    from harlo.sync import Checkpoint

    cp = Checkpoint()
    cp.mark_dirty("/Brain/Session")
    assert cp.is_dirty()
    cp.clear()
    assert not cp.is_dirty()


def test_default_checkpoint_is_module_level():
    """`harlo.sync.default_checkpoint` is a stable per-process instance."""
    from harlo.sync import default_checkpoint
    from harlo.sync import default_checkpoint as second_ref
    assert default_checkpoint is second_ref


def _stub_persistence(monkeypatch, write_fn):
    """Inject a stub `harlo.usd_lite.persistence` module so the lazy import
    in Checkpoint.flush() resolves to ``write_fn`` regardless of whether the
    [substrate] extra (pxr) is installed in the test environment."""
    import sys
    import types
    fake = types.ModuleType("harlo.usd_lite.persistence")
    fake.write = write_fn
    monkeypatch.setitem(sys.modules, "harlo.usd_lite.persistence", fake)


def test_flush_preserves_dirty_on_write_failure(tmp_path, monkeypatch):
    """If write() raises, dirty paths must be preserved for retry."""
    from harlo.sync import Checkpoint
    cp = Checkpoint()
    cp.mark_dirty("/Brain/A")
    cp.mark_dirty("/Brain/B")

    def boom(_stage, _target):
        raise OSError("disk full")

    _stub_persistence(monkeypatch, boom)

    with pytest.raises(OSError, match="disk full"):
        cp.flush(object(), str(tmp_path / "fail.usda"))

    # The mutations are still pending; caller can retry.
    assert cp.is_dirty()
    assert cp.dirty_paths() == frozenset({"/Brain/A", "/Brain/B"})


def test_flush_preserves_concurrent_mark_dirty(tmp_path, monkeypatch):
    """A mark_dirty arriving during write() must NOT be lost when flush clears."""
    from harlo.sync import Checkpoint
    cp = Checkpoint()
    cp.mark_dirty("/Brain/Before")

    captured: list[str] = []

    def slow_write(_stage, _target):
        # Simulate a concurrent mark_dirty during the write window.
        captured.append("write_started")
        cp.mark_dirty("/Brain/During")

    _stub_persistence(monkeypatch, slow_write)

    cp.flush(object(), str(tmp_path / "ok.usda"))

    # The before-write mark was flushed; the during-write mark survives.
    assert cp.is_dirty()
    assert cp.dirty_paths() == frozenset({"/Brain/During"})
    assert captured == ["write_started"]
