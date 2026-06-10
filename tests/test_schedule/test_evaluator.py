"""Tests for the pure evaluator in src/schedule.py.

Honors Commandment 3: the evaluator takes current_time_iso as INPUT,
never reads the clock. These tests pass synthetic UTC ISO strings.
"""

from __future__ import annotations

import datetime
from zoneinfo import ZoneInfo

import pytest

from harlo.engine.schedule import (
    DayWindow,
    Override,
    Schedule,
    evaluate_schedule,
)
from harlo.engine.schemas import ScheduleKind

NY = ZoneInfo("America/New_York")


def _ny_to_utc_iso(year, month, day, hour, minute):
    """Build a UTC ISO 8601 µs string from a NY-local datetime."""
    local = datetime.datetime(year, month, day, hour, minute, tzinfo=NY)
    return (
        local.astimezone(datetime.UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


@pytest.fixture
def schedule() -> Schedule:
    """Synthetic test schedule covering work, family, all-day, and an override."""
    return Schedule(
        timezone="America/New_York",
        work_hours={
            "monday":    [DayWindow(start=datetime.time(9, 0),  end=datetime.time(18, 0))],
            "tuesday":   [DayWindow(start=datetime.time(9, 0),  end=datetime.time(18, 0))],
            "friday":    [DayWindow(start=datetime.time(9, 0),  end=datetime.time(15, 0))],
        },
        family_hours={
            "monday":    [DayWindow(start=datetime.time(18, 0), end=datetime.time(21, 0))],
            "saturday":  [DayWindow(all_day=True)],
            "sunday":    [DayWindow(all_day=True)],
        },
        overrides=(
            Override(
                name="demo_day",
                kind="demo",
                start_date=datetime.date(2026, 5, 16),
                end_date=datetime.date(2026, 5, 16),
                start_time=datetime.time(10, 0),
                end_time=datetime.time(14, 0),
                state=ScheduleKind.WORK,
                notes="Saturday demo override",
            ),
        ),
    )


class TestFallbacks:
    """Backwards compat: undefined / invalid input falls back to WORK."""

    def test_empty_timezone_returns_work(self):
        result = evaluate_schedule(Schedule(), "2026-05-08T22:00:00.000000Z")
        assert result.kind == ScheduleKind.WORK
        assert result.override_reason == ""

    def test_unknown_timezone_returns_work(self):
        s = Schedule(timezone="Mars/Olympus")
        result = evaluate_schedule(s, "2026-05-08T22:00:00.000000Z")
        assert result.kind == ScheduleKind.WORK

    def test_unparseable_iso_returns_work(self, schedule):
        assert evaluate_schedule(schedule, "not-an-iso").kind == ScheduleKind.WORK

    def test_naive_iso_treated_as_utc(self, schedule):
        # Without Z or offset — fromisoformat produces naive dt, code injects UTC tz
        result = evaluate_schedule(schedule, "2026-05-11T13:00:00")  # 09:00 NY
        assert result.kind == ScheduleKind.WORK


class TestBoundaries:
    """Half-open [start, end) — start inclusive, end exclusive."""

    def test_work_start_inclusive(self, schedule):
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 9, 0)).kind == ScheduleKind.WORK

    def test_just_before_work_start_off_hours(self, schedule):
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 8, 59)).kind == ScheduleKind.OFF_HOURS

    def test_work_end_exclusive_yields_family_at_18(self, schedule):
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 17, 59)).kind == ScheduleKind.WORK
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 18, 0)).kind == ScheduleKind.FAMILY

    def test_family_end_exclusive_yields_off_hours_at_21(self, schedule):
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 20, 59)).kind == ScheduleKind.FAMILY
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 21, 0)).kind == ScheduleKind.OFF_HOURS

    def test_friday_short_day(self, schedule):
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 15, 14, 59)).kind == ScheduleKind.WORK
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 15, 15, 0)).kind == ScheduleKind.OFF_HOURS


class TestMissingDays:
    """Missing per-day prims behave as 'no entry that day'."""

    def test_missing_weekday_during_typical_work_hours_off_hours(self, schedule):
        # Wednesday has no work_hours entry in this fixture
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 13, 14, 0)).kind == ScheduleKind.OFF_HOURS


class TestAllDay:
    """all_day=True covers the full local day."""

    def test_saturday_all_day_family_morning(self, schedule):
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 16, 3, 0)).kind == ScheduleKind.FAMILY

    def test_sunday_all_day_family_noon(self, schedule):
        assert evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 17, 12, 0)).kind == ScheduleKind.FAMILY


class TestOverrides:
    """Overrides: highest precedence, date+time bounded, kind flows through as override_reason."""

    def test_override_overrides_all_day_family(self, schedule):
        # Sat 11:00 falls inside demo override (10–14) — wins over all_day family
        result = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 16, 11, 0))
        assert result.kind == ScheduleKind.WORK
        assert result.override_reason == "demo"

    def test_override_end_time_exclusive(self, schedule):
        # 14:00 = override end (exclusive) → falls back to underlying state (Sat all_day = FAMILY)
        result = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 16, 14, 0))
        assert result.kind == ScheduleKind.FAMILY
        assert result.override_reason == ""

    def test_override_outside_date_range_no_match(self, schedule):
        # The Saturday before — same time, no override
        result = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 9, 11, 0))
        assert result.kind == ScheduleKind.FAMILY
        assert result.override_reason == ""

    def test_override_outside_time_range_no_match(self, schedule):
        # Same Saturday but 09:00 — before override start (10:00)
        result = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 16, 9, 0))
        assert result.kind == ScheduleKind.FAMILY
        assert result.override_reason == ""


class TestDST:
    """zoneinfo handles DST transitions; same-day all_day stays consistent across the boundary."""

    def test_dst_spring_forward_sunday_remains_family(self, schedule):
        # 2026-03-08: NY 02:00 EST → 03:00 EDT. Sunday all_day in fixture.
        before = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 3, 8, 1, 30))
        after = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 3, 8, 4, 0))
        assert before.kind == ScheduleKind.FAMILY
        assert after.kind == ScheduleKind.FAMILY

    def test_dst_fall_back_sunday_remains_family(self, schedule):
        # 2026-11-01: NY 02:00 EDT → 01:00 EST. Sunday all_day in fixture.
        early = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 11, 1, 1, 30))
        late = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 11, 1, 3, 0))
        assert early.kind == ScheduleKind.FAMILY
        assert late.kind == ScheduleKind.FAMILY


class TestMultipleWindowsPerDay:
    """Per-weekday list[DayWindow] — supports cross-midnight FAMILY via two windows."""

    @pytest.fixture
    def split_family_schedule(self) -> Schedule:
        # FAMILY 17:00 → next-day 09:00 encoded as morning + evening windows per day
        morning = DayWindow(start=datetime.time(0, 0), end=datetime.time(9, 0))
        evening = DayWindow(start=datetime.time(17, 0), end=datetime.time(23, 59, 59))
        return Schedule(
            timezone="America/New_York",
            work_hours={
                "monday":    [DayWindow(start=datetime.time(9, 0), end=datetime.time(17, 0))],
                "tuesday":   [DayWindow(start=datetime.time(9, 0), end=datetime.time(17, 0))],
            },
            family_hours={
                "monday":    [morning, evening],
                "tuesday":   [morning, evening],
            },
        )

    def test_morning_window_matches(self, split_family_schedule):
        # Mon 06:00 — inside the morning rollover window
        result = evaluate_schedule(split_family_schedule, _ny_to_utc_iso(2026, 5, 11, 6, 0))
        assert result.kind == ScheduleKind.FAMILY

    def test_evening_window_matches(self, split_family_schedule):
        # Mon 19:30 — inside the evening window
        result = evaluate_schedule(split_family_schedule, _ny_to_utc_iso(2026, 5, 11, 19, 30))
        assert result.kind == ScheduleKind.FAMILY

    def test_between_windows_falls_through_to_work(self, split_family_schedule):
        # Mon 12:00 — between morning (ends 09:00) and evening (starts 17:00); WORK matches
        result = evaluate_schedule(split_family_schedule, _ny_to_utc_iso(2026, 5, 11, 12, 0))
        assert result.kind == ScheduleKind.WORK

    def test_morning_end_boundary_yields_work(self, split_family_schedule):
        # 09:00 — morning FAMILY ends (exclusive), WORK starts (inclusive)
        result = evaluate_schedule(split_family_schedule, _ny_to_utc_iso(2026, 5, 11, 9, 0))
        assert result.kind == ScheduleKind.WORK

    def test_evening_start_boundary_yields_family(self, split_family_schedule):
        # 17:00 — WORK ends (exclusive), evening FAMILY starts (inclusive)
        result = evaluate_schedule(split_family_schedule, _ny_to_utc_iso(2026, 5, 11, 17, 0))
        assert result.kind == ScheduleKind.FAMILY


class TestPrecedenceOrder:
    """OVERRIDE > FAMILY > WORK > OFF_HOURS resolved correctly."""

    def test_override_beats_family(self, schedule):
        # Override on Sat (Sat is family all_day) → override WORK wins
        result = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 16, 11, 0))
        assert result.kind == ScheduleKind.WORK

    def test_family_beats_work_at_overlap(self, schedule):
        # Mon 18:00 — work_end == family_start. With half-open, family wins.
        result = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 18, 0))
        assert result.kind == ScheduleKind.FAMILY

    def test_work_beats_off_hours_in_window(self, schedule):
        result = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 12, 0))
        assert result.kind == ScheduleKind.WORK

    def test_off_hours_default_outside_all_windows(self, schedule):
        # Mon 22:30 — past family end, past work end, no override
        result = evaluate_schedule(schedule, _ny_to_utc_iso(2026, 5, 11, 22, 30))
        assert result.kind == ScheduleKind.OFF_HOURS
