"""Tests for src/schedule_migrate.py — disk-level migration of /schedule/.

The Harlo daemon authors per-exchange to harlo.usda. /schedule/ moved to a
dedicated sublayer schedule.usda the daemon never authors to. These tests
exercise migrate_inline() directly: pre-migration → migrated, idempotence,
and the no-schedule-yet branch.
"""

from __future__ import annotations

import os

import pytest

from pxr import Sdf, Usd

from src.schedule import (
    DayWindow,
    Schedule,
    author_schedule_to_stage,
    load_schedule_from_stage,
)
from src.schedule_migrate import migrate_inline


def _craft_pre_migration_root(stage_dir: str) -> str:
    """Author a legacy harlo.usda containing /schedule/ on the root layer."""
    os.makedirs(stage_dir, exist_ok=True)
    root_path = os.path.join(stage_dir, "harlo.usda")
    stage = Usd.Stage.CreateNew(root_path)
    sched = Schedule(
        timezone="America/New_York",
        family_hours={"saturday": [DayWindow(all_day=True)]},
    )
    author_schedule_to_stage(stage, sched)
    stage.GetRootLayer().Save()
    return root_path


def _craft_no_schedule_root(stage_dir: str) -> str:
    """Author a legacy harlo.usda with no /schedule/ prim at all."""
    os.makedirs(stage_dir, exist_ok=True)
    root_path = os.path.join(stage_dir, "harlo.usda")
    stage = Usd.Stage.CreateNew(root_path)
    stage.DefinePrim("/state", "Scope")
    stage.GetRootLayer().Save()
    return root_path


class TestPreMigrationStageMigrates:
    def test_pre_migration_stage_migrates(self, tmp_path):
        stage_dir = str(tmp_path)
        root_path = _craft_pre_migration_root(stage_dir)

        result = migrate_inline(stage_dir)
        assert result["migrated"] is True
        assert result["status"] == "migrated"

        sched_path = os.path.join(stage_dir, "schedule.usda")
        assert os.path.exists(sched_path), "schedule.usda must be created"

        # /schedule/ opinions live on schedule.usda only.
        sched_layer = Sdf.Layer.FindOrOpen(sched_path)
        assert sched_layer.GetPrimAtPath("/schedule") is not None
        assert sched_layer.GetPrimAtPath("/schedule/family_hours/saturday") is not None

        # /schedule/ is gone from harlo.usda.
        root_layer = Sdf.Layer.FindOrOpen(root_path)
        assert root_layer.GetPrimAtPath("/schedule") is None

        # schedule.usda is wired as a sublayer of harlo.usda.
        assert any(
            os.path.normpath(p) == os.path.normpath(sched_path)
            for p in root_layer.subLayerPaths
        )

        # Composed stage still loads the schedule via composition.
        composed = Usd.Stage.Open(root_path)
        loaded = load_schedule_from_stage(composed)
        assert loaded.timezone == "America/New_York"
        assert loaded.family_hours["saturday"][0].all_day is True


class TestMigrationIdempotent:
    def test_migration_idempotent(self, tmp_path):
        stage_dir = str(tmp_path)
        _craft_pre_migration_root(stage_dir)

        first = migrate_inline(stage_dir)
        assert first["migrated"] is True

        sched_path = os.path.join(stage_dir, "schedule.usda")
        root_path = os.path.join(stage_dir, "harlo.usda")
        sched_mtime = os.path.getmtime(sched_path)
        root_mtime = os.path.getmtime(root_path)

        # Bump time past second-resolution filesystems before the second call,
        # so any unwanted write would be detectable.
        future = max(sched_mtime, root_mtime) + 1.0
        os.utime(sched_path, (future, future))
        os.utime(root_path, (future, future))

        second = migrate_inline(stage_dir)
        assert second["migrated"] is False
        assert second["status"] == "already_migrated"

        # No write — mtimes unchanged from the bump.
        assert os.path.getmtime(sched_path) == future
        assert os.path.getmtime(root_path) == future


class TestMigrationNoScheduleAuthorsSkeleton:
    def test_migration_no_schedule_authors_skeleton(self, tmp_path):
        stage_dir = str(tmp_path)
        root_path = _craft_no_schedule_root(stage_dir)

        result = migrate_inline(stage_dir)
        assert result["migrated"] is True

        sched_path = os.path.join(stage_dir, "schedule.usda")
        assert os.path.exists(sched_path)

        sched_layer = Sdf.Layer.FindOrOpen(sched_path)
        assert sched_layer.GetPrimAtPath("/schedule") is not None
        assert sched_layer.GetPrimAtPath("/schedule/work_hours") is not None
        assert sched_layer.GetPrimAtPath("/schedule/family_hours") is not None
        assert sched_layer.GetPrimAtPath("/schedule/overrides") is not None
        assert sched_layer.GetPrimAtPath("/schedule/inferred") is not None

        # Composed stage produces an empty Schedule (timezone="").
        composed = Usd.Stage.Open(root_path)
        loaded = load_schedule_from_stage(composed)
        assert loaded.timezone == ""
        assert loaded.work_hours == {}
        assert loaded.family_hours == {}
        assert loaded.overrides == ()
