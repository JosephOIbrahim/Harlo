"""Tests for daemon-clobber prevention.

Covers the engine helper (reload_if_disk_changed) and the regression
scenario where an external writer modified /schedule/ on disk and the
daemon's per-exchange stage.save() reverted it.

USD's Sdf.Layer interns by canonical path — opening the same path twice
in one process returns the SAME layer object, so in-process Stage.Open
cannot simulate cross-process divergence. We sidestep this by authoring
to an intermediate file (different path → different layer instance) then
byte-copying over the target. The daemon's in-memory layer for target_path
is unchanged; disk advances.
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pxr import Usd

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from harlo.engine.cognitive_engine import CognitiveEngine
from harlo.engine.schedule import (
    DayWindow,
    Schedule,
    author_schedule_to_stage,
    load_schedule_from_stage,
)
from harlo.engine.schemas import ScheduleKind

NY = ZoneInfo("America/New_York")


def _ny_iso(year, month, day, hour, minute) -> str:
    local = datetime.datetime(year, month, day, hour, minute, tzinfo=NY)
    return (
        local.astimezone(datetime.UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _external_overwrite(target_path: str, schedule: Schedule, tmp_path: Path) -> None:
    """Simulate a cross-process external write to a USD stage on disk.

    Authors `schedule` into a fresh intermediate .usda (different path → its
    own Sdf.Layer instance), then byte-copies the result over `target_path`.
    Bumps mtime by 1s afterward to defeat second-resolution filesystems.
    """
    intermediate = str(tmp_path / "_external_write.usda")
    int_stage = Usd.Stage.CreateNew(intermediate)
    author_schedule_to_stage(int_stage, schedule)
    int_stage.GetRootLayer().Save()
    del int_stage
    shutil.copy(intermediate, target_path)
    future = os.path.getmtime(target_path) + 1.0
    os.utime(target_path, (future, future))


@pytest.fixture
def disk_engine(tmp_path):
    eng = CognitiveEngine(
        stage_dir=str(tmp_path), in_memory=False, prediction_enabled=False,
    )
    yield eng
    eng.close()


# ════════════════════════════════════════════════════════════════════════
# reload_if_disk_changed helper — direct coverage
# ════════════════════════════════════════════════════════════════════════

class TestReloadHelper:
    def test_no_change_returns_unchanged(self, disk_engine):
        result = disk_engine.reload_if_disk_changed()
        assert result["reloaded"] is False
        assert "unchanged" in result["reason"]

    def test_picks_up_external_write(self, disk_engine, tmp_path):
        disk_engine.process_exchange(
            "warmup", {}, current_time_iso=_ny_iso(2026, 5, 8, 14, 0),
        )
        target = str(tmp_path / "harlo.usda")
        ext_sched = Schedule(
            timezone="America/New_York",
            family_hours={"saturday": [DayWindow(all_day=True)]},
        )
        _external_overwrite(target, ext_sched, tmp_path)

        result = disk_engine.reload_if_disk_changed()
        assert result["reloaded"] is True
        assert "absorbed" in result["reason"]

    def test_force_bypasses_mtime_cache(self, disk_engine):
        # Disk hasn't advanced past baseline; default returns "unchanged".
        # force=True should attempt the reload regardless — it might still
        # be a no-op if there's nothing actually different on disk, but the
        # mtime gate should not be the reason for skipping.
        result = disk_engine.reload_if_disk_changed(force=True)
        assert "unchanged" not in result.get("reason", "")


# ════════════════════════════════════════════════════════════════════════
# Regression: the original clobber pattern, end-to-end
# ════════════════════════════════════════════════════════════════════════

class TestExternalWriteSurvivesDaemonSave:
    """Sublayer parking: daemon never authors to schedule.usda, so external
    edits land directly on it and are not racing against root saves."""

    def test_external_schedule_edit_lands_on_schedule_layer(self, disk_engine, tmp_path):
        # Settle the daemon's mtime baseline against an authored file
        disk_engine.process_exchange(
            "warmup", {}, current_time_iso=_ny_iso(2026, 5, 8, 14, 0),
        )

        root_path = str(tmp_path / "harlo.usda")
        sched_path = str(tmp_path / "schedule.usda")
        assert os.path.exists(sched_path), (
            "bootstrap should have created schedule.usda sublayer"
        )

        # Capture mtimes BEFORE the next per-exchange save.
        sched_mtime_before = os.path.getmtime(sched_path)
        root_mtime_before = os.path.getmtime(root_path)

        # External write to schedule.usda directly (the supported edit surface).
        from pxr import Usd
        ext_stage = Usd.Stage.CreateNew(str(tmp_path / "_ext_sched.usda"))
        author_schedule_to_stage(
            ext_stage,
            Schedule(
                timezone="America/New_York",
                family_hours={"saturday": [DayWindow(all_day=True)]},
            ),
        )
        ext_stage.GetRootLayer().Save()
        del ext_stage
        shutil.copy(str(tmp_path / "_ext_sched.usda"), sched_path)
        future = os.path.getmtime(sched_path) + 1.0
        os.utime(sched_path, (future, future))

        # Force the daemon to absorb the external schedule.usda edit, then
        # run an exchange — the per-exchange save should advance harlo.usda
        # but NOT schedule.usda.
        disk_engine.reload_schedule(force=True)
        disk_engine.process_exchange(
            "post_external_write", {},
            current_time_iso=_ny_iso(2026, 5, 9, 11, 0),  # Saturday 11:00 NY
        )

        # In-memory observation reflects the absorbed schedule.
        last = disk_engine._observations[-1]
        assert last.schedule.kind == ScheduleKind.FAMILY, (
            "schedule.usda reload didn't pick up external schedule edit"
        )

        # schedule.usda mtime must NOT have advanced past the external write.
        # The daemon never authors to it. Save() must skip it entirely.
        sched_mtime_after = os.path.getmtime(sched_path)
        assert sched_mtime_after == future, (
            f"daemon save advanced schedule.usda mtime "
            f"({sched_mtime_after} != {future}) — sublayer parking violated"
        )

        # harlo.usda must NOT carry any /schedule/ opinion.
        with open(root_path, "r") as f:
            root_text = f.read()
        assert 'def "schedule"' not in root_text, (
            "/schedule/ opinion leaked back to harlo.usda — sublayer parking violated"
        )

        # schedule.usda must still carry the external edit.
        with open(sched_path, "r") as f:
            sched_text = f.read()
        assert "all_day = 1" in sched_text, (
            "schedule.usda lost the external edit"
        )


# ════════════════════════════════════════════════════════════════════════
# stage_reload MCP tool — verifies the JSON wrapper around the helper
# ════════════════════════════════════════════════════════════════════════

class TestStageReloadTool:
    def test_tool_picks_up_external_write(self, monkeypatch, tmp_path):
        # python/ on sys.path so 'harlo' is importable
        python_root = PROJECT_ROOT / "python"
        if str(python_root) not in sys.path:
            sys.path.insert(0, str(python_root))
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        import harlo.mcp_server as mcp

        eng = CognitiveEngine(
            stage_dir=str(tmp_path), in_memory=False, prediction_enabled=False,
        )
        monkeypatch.setattr(mcp, "_engine", eng, raising=False)
        try:
            eng.process_exchange(
                "warmup", {}, current_time_iso=_ny_iso(2026, 5, 8, 14, 0),
            )
            target = str(tmp_path / "harlo.usda")
            _external_overwrite(
                target,
                Schedule(
                    timezone="America/New_York",
                    family_hours={"saturday": [DayWindow(all_day=True)]},
                ),
                tmp_path,
            )
            raw = mcp.stage_reload(force=False)
            result = json.loads(raw)
            assert result["status"] == "ok"
            assert result["reloaded"] is True
            assert "absorbed" in result["reason"]
        finally:
            eng.close()

    def test_tool_no_change_returns_unchanged(self, monkeypatch, tmp_path):
        python_root = PROJECT_ROOT / "python"
        if str(python_root) not in sys.path:
            sys.path.insert(0, str(python_root))
        if str(PROJECT_ROOT) not in sys.path:
            sys.path.insert(0, str(PROJECT_ROOT))
        import harlo.mcp_server as mcp

        eng = CognitiveEngine(
            stage_dir=str(tmp_path), in_memory=False, prediction_enabled=False,
        )
        monkeypatch.setattr(mcp, "_engine", eng, raising=False)
        try:
            raw = mcp.stage_reload(force=False)
            result = json.loads(raw)
            assert result["status"] == "ok"
            assert result["reloaded"] is False
            assert "unchanged" in result["reason"]
        finally:
            eng.close()
