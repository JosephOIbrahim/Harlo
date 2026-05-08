"""Tests for USD round-trip in src/schedule.py.

Uses an in-memory pxr.Usd.Stage. No filesystem writes outside pytest's tmp_path.
"""

from __future__ import annotations

import datetime

import pytest

from pxr import Usd

from src.schedule import (
    DayWindow,
    Override,
    Schedule,
    author_empty_skeleton,
    author_schedule_to_stage,
    load_schedule_from_stage,
)
from src.schemas import ScheduleKind


@pytest.fixture
def in_memory_stage():
    return Usd.Stage.CreateInMemory()


@pytest.fixture
def populated_schedule() -> Schedule:
    return Schedule(
        timezone="America/New_York",
        work_hours={
            "monday": DayWindow(start=datetime.time(9, 0), end=datetime.time(18, 0)),
            "friday": DayWindow(start=datetime.time(9, 0), end=datetime.time(15, 0)),
        },
        family_hours={
            "monday":   DayWindow(start=datetime.time(18, 0), end=datetime.time(21, 0)),
            "saturday": DayWindow(all_day=True),
        },
        overrides=(
            Override(
                name="wwdc_2026",
                kind="travel",
                start_date=datetime.date(2026, 6, 8),
                end_date=datetime.date(2026, 6, 12),
                start_time=datetime.time(0, 0),
                end_time=datetime.time(23, 59),
                state=ScheduleKind.WORK,
                notes="WWDC keynote week",
            ),
        ),
    )


class TestEmptySkeleton:
    def test_authors_required_prim_paths(self, in_memory_stage):
        author_empty_skeleton(in_memory_stage)
        for path in (
            "/schedule",
            "/schedule/work_hours",
            "/schedule/family_hours",
            "/schedule/overrides",
            "/schedule/inferred",
        ):
            assert in_memory_stage.GetPrimAtPath(path).IsValid(), f"missing {path}"

    def test_idempotent_does_not_clobber(self, in_memory_stage, populated_schedule):
        author_empty_skeleton(in_memory_stage)
        author_schedule_to_stage(in_memory_stage, populated_schedule)
        # Second call must not wipe data
        author_empty_skeleton(in_memory_stage)
        loaded = load_schedule_from_stage(in_memory_stage)
        assert loaded.timezone == "America/New_York"
        assert "monday" in loaded.work_hours

    def test_empty_skeleton_loads_as_empty_schedule(self, in_memory_stage):
        author_empty_skeleton(in_memory_stage)
        loaded = load_schedule_from_stage(in_memory_stage)
        assert loaded.timezone == ""
        assert loaded.work_hours == {}
        assert loaded.family_hours == {}
        assert loaded.overrides == ()


class TestRoundTrip:
    def test_full_schedule_round_trips(self, in_memory_stage, populated_schedule):
        author_schedule_to_stage(in_memory_stage, populated_schedule)
        loaded = load_schedule_from_stage(in_memory_stage)

        assert loaded.timezone == "America/New_York"
        assert loaded.work_hours["monday"].start == datetime.time(9, 0)
        assert loaded.work_hours["monday"].end == datetime.time(18, 0)
        assert loaded.work_hours["friday"].end == datetime.time(15, 0)
        assert loaded.family_hours["saturday"].all_day is True
        assert len(loaded.overrides) == 1

        ov = loaded.overrides[0]
        assert ov.name == "wwdc_2026"
        assert ov.kind == "travel"
        assert ov.start_date == datetime.date(2026, 6, 8)
        assert ov.end_date == datetime.date(2026, 6, 12)
        assert ov.state == ScheduleKind.WORK
        assert ov.notes == "WWDC keynote week"

    def test_save_to_disk_and_reopen(self, populated_schedule, tmp_path):
        path = str(tmp_path / "stage.usda")
        stage = Usd.Stage.CreateNew(path)
        author_schedule_to_stage(stage, populated_schedule)
        stage.GetRootLayer().Save()

        reopened = Usd.Stage.Open(path)
        loaded = load_schedule_from_stage(reopened)
        assert loaded.timezone == "America/New_York"
        assert loaded.family_hours["saturday"].all_day is True

    def test_replace_clears_existing_children(self, in_memory_stage, populated_schedule):
        author_schedule_to_stage(in_memory_stage, populated_schedule)

        # Author a smaller schedule — old days must not linger
        smaller = Schedule(
            timezone="America/New_York",
            work_hours={
                "tuesday": DayWindow(start=datetime.time(10, 0), end=datetime.time(16, 0)),
            },
            family_hours={},
            overrides=(),
        )
        author_schedule_to_stage(in_memory_stage, smaller)

        loaded = load_schedule_from_stage(in_memory_stage)
        assert "tuesday" in loaded.work_hours
        assert "monday" not in loaded.work_hours, "old monday entry should have been removed"
        assert "friday" not in loaded.work_hours
        assert loaded.family_hours == {}
        assert loaded.overrides == ()


class TestRawUsdaIsReadable:
    """Sanity check the raw .usda is human-readable per the INSTALL.md ethos."""

    def test_raw_usda_contains_expected_tokens(self, populated_schedule, tmp_path):
        path = str(tmp_path / "stage.usda")
        stage = Usd.Stage.CreateNew(path)
        author_schedule_to_stage(stage, populated_schedule)
        stage.GetRootLayer().Save()

        with open(path) as f:
            text = f.read()

        assert 'def "schedule"' in text
        assert 'timezone = "America/New_York"' in text
        assert 'def "monday"' in text
        assert 'start = "09:00"' in text
        assert 'end = "18:00"' in text
        assert 'all_day = 1' in text
        assert 'def "wwdc_2026"' in text
        assert 'kind = "travel"' in text
