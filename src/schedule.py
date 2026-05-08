"""Schedule — declarative work-hours configuration on the cognitive twin stage.

USD round-trip + clock-free evaluator. Honors Commandment 3 — the evaluator
takes current_time_iso as INPUT, never reads the clock.

Per docs/temporal-models.md:
- This module accepts T3 (UTC ISO 8601 µs) as input via current_time_iso.
- Conversion to local time uses zoneinfo (stdlib).
- Schedule data is stored as USD prims with default values, NOT time-sampled.

The evaluator and dataclasses do not import pxr; the USD round-trip helpers
import pxr inline so the evaluator stays usable without USD installed.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .schemas import ScheduleBlock, ScheduleKind

WEEKDAYS = (
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
)


# ─── Dataclasses ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DayWindow:
    """A single window on a single weekday. Half-open [start, end)."""
    start: Optional[datetime.time] = None
    end: Optional[datetime.time] = None
    all_day: bool = False

    def contains(self, t: datetime.time) -> bool:
        if self.all_day:
            return True
        if self.start is None or self.end is None:
            return False
        return self.start <= t < self.end


@dataclass(frozen=True)
class Override:
    """One-off date-bounded override (vacation, demo, sick, travel, etc.).

    `state` is the ScheduleKind to produce when matched.
    `kind` is the human-readable reason, surfaced as override_reason.
    """
    name: str
    kind: str
    start_date: datetime.date
    end_date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    state: ScheduleKind
    notes: str = ""

    def matches(self, local_dt: datetime.datetime) -> bool:
        d = local_dt.date()
        if not (self.start_date <= d <= self.end_date):
            return False
        return self.start_time <= local_dt.time() < self.end_time


@dataclass(frozen=True)
class Schedule:
    """Loaded schedule. Empty timezone signals 'not configured' → evaluator returns WORK."""
    timezone: str = ""
    work_hours: dict[str, DayWindow] = field(default_factory=dict)
    family_hours: dict[str, DayWindow] = field(default_factory=dict)
    overrides: tuple[Override, ...] = ()


# ─── Parsing helpers ─────────────────────────────────────────────────────

def _parse_hhmm(s) -> Optional[datetime.time]:
    if not isinstance(s, str) or not s:
        return None
    try:
        h, m = s.split(":")
        return datetime.time(int(h), int(m))
    except (ValueError, AttributeError):
        return None


def _format_hhmm(t: datetime.time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def _parse_date(s) -> Optional[datetime.date]:
    if not isinstance(s, str) or not s:
        return None
    try:
        return datetime.date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


# ─── Pure evaluator (Commandment 3 clean — no clock read) ────────────────

def evaluate_schedule(
    schedule: Schedule,
    current_time_iso: str,
) -> ScheduleBlock:
    """Resolve ScheduleKind for current_time_iso (UTC ISO 8601, Z suffix per T3).

    Precedence: overrides → family_hours → work_hours → OFF_HOURS.
    Half-open intervals [start, end) — boundary belongs to the next state.

    Backwards compat: empty timezone, missing schedule, unknown tz, or
    unparseable input all return ScheduleBlock(kind=WORK) — preserves the
    pre-schedule always-WORK behavior.
    """
    if not schedule.timezone:
        return ScheduleBlock(kind=ScheduleKind.WORK)

    try:
        tz = ZoneInfo(schedule.timezone)
    except ZoneInfoNotFoundError:
        return ScheduleBlock(kind=ScheduleKind.WORK)

    utc_str = current_time_iso
    if isinstance(utc_str, str) and utc_str.endswith("Z"):
        utc_str = utc_str[:-1] + "+00:00"
    try:
        utc_dt = datetime.datetime.fromisoformat(utc_str)
    except (ValueError, TypeError):
        return ScheduleBlock(kind=ScheduleKind.WORK)

    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=datetime.UTC)

    local_dt = utc_dt.astimezone(tz)

    for ov in schedule.overrides:
        if ov.matches(local_dt):
            return ScheduleBlock(kind=ov.state, override_reason=ov.kind)

    weekday = WEEKDAYS[local_dt.weekday()]
    fam = schedule.family_hours.get(weekday)
    if fam is not None and fam.contains(local_dt.time()):
        return ScheduleBlock(kind=ScheduleKind.FAMILY)

    work = schedule.work_hours.get(weekday)
    if work is not None and work.contains(local_dt.time()):
        return ScheduleBlock(kind=ScheduleKind.WORK)

    return ScheduleBlock(kind=ScheduleKind.OFF_HOURS)


# ─── USD round-trip (pxr imported inline; evaluator above stays USD-free) ──

def load_schedule_from_stage(stage) -> Schedule:
    """Read /schedule/ prims off the stage and build a Schedule.

    Returns empty Schedule (timezone="") if /schedule/ doesn't exist or
    has no usable data — evaluator will then fall back to WORK.
    """
    schedule_prim = stage.GetPrimAtPath("/schedule")
    if not schedule_prim or not schedule_prim.IsValid():
        return Schedule()

    tz = ""
    tz_attr = schedule_prim.GetAttribute("timezone")
    if tz_attr and tz_attr.IsValid():
        v = tz_attr.Get()
        if isinstance(v, str):
            tz = v

    work_hours = _read_day_table(stage, "/schedule/work_hours")
    family_hours = _read_day_table(stage, "/schedule/family_hours")

    overrides_list: list[Override] = []
    ov_root = stage.GetPrimAtPath("/schedule/overrides")
    if ov_root and ov_root.IsValid():
        for child in ov_root.GetChildren():
            ov = _read_override(child)
            if ov is not None:
                overrides_list.append(ov)

    return Schedule(
        timezone=tz,
        work_hours=work_hours,
        family_hours=family_hours,
        overrides=tuple(overrides_list),
    )


def _read_day_table(stage, root_path: str) -> dict[str, DayWindow]:
    out: dict[str, DayWindow] = {}
    root = stage.GetPrimAtPath(root_path)
    if not root or not root.IsValid():
        return out
    for child in root.GetChildren():
        day = child.GetName().lower()
        if day not in WEEKDAYS:
            continue
        out[day] = _read_day_window(child)
    return out


def _read_day_window(prim) -> DayWindow:
    all_day = False
    all_attr = prim.GetAttribute("all_day")
    if all_attr and all_attr.IsValid():
        v = all_attr.Get()
        if v is not None:
            all_day = bool(v)
    if all_day:
        return DayWindow(all_day=True)

    start_attr = prim.GetAttribute("start")
    end_attr = prim.GetAttribute("end")
    start = _parse_hhmm(start_attr.Get()) if start_attr and start_attr.IsValid() else None
    end = _parse_hhmm(end_attr.Get()) if end_attr and end_attr.IsValid() else None
    return DayWindow(start=start, end=end, all_day=False)


def _read_override(prim) -> Optional[Override]:
    def _gets(name: str) -> str:
        a = prim.GetAttribute(name)
        if not a or not a.IsValid():
            return ""
        v = a.Get()
        return v if isinstance(v, str) else ""

    kind = _gets("kind")
    start_date = _parse_date(_gets("start_date"))
    end_date = _parse_date(_gets("end_date"))
    if not kind or start_date is None or end_date is None:
        return None

    start_time = _parse_hhmm(_gets("start_time")) or datetime.time(0, 0)
    end_time = _parse_hhmm(_gets("end_time")) or datetime.time(23, 59)

    state_str = _gets("state").upper() or "WORK"
    try:
        state = ScheduleKind[state_str]
    except KeyError:
        state = ScheduleKind.WORK

    return Override(
        name=prim.GetName(),
        kind=kind,
        start_date=start_date,
        end_date=end_date,
        start_time=start_time,
        end_time=end_time,
        state=state,
        notes=_gets("notes"),
    )


def author_empty_skeleton(stage) -> None:
    """Author the /schedule/ skeleton on a stage that doesn't have it.

    Idempotent. Empty timezone signals 'not configured' → evaluator returns WORK.
    """
    from pxr import Sdf

    if stage.GetPrimAtPath("/schedule").IsValid():
        return

    schedule_prim = stage.DefinePrim("/schedule")
    tz_attr = schedule_prim.CreateAttribute(
        "timezone", Sdf.ValueTypeNames.String, custom=True,
    )
    tz_attr.Set("")

    stage.DefinePrim("/schedule/work_hours")
    stage.DefinePrim("/schedule/family_hours")
    stage.DefinePrim("/schedule/overrides")
    stage.DefinePrim("/schedule/inferred")


def author_schedule_to_stage(stage, schedule: Schedule) -> None:
    """Write a full Schedule to the stage's /schedule/ prim hierarchy.

    Replaces existing children under work_hours/family_hours/overrides.
    Used by the Phase 4 bootstrap and any future schedule-edit path.
    """
    from pxr import Sdf

    if not stage.GetPrimAtPath("/schedule").IsValid():
        author_empty_skeleton(stage)

    schedule_prim = stage.GetPrimAtPath("/schedule")
    tz_attr = schedule_prim.GetAttribute("timezone")
    if not tz_attr or not tz_attr.IsValid():
        tz_attr = schedule_prim.CreateAttribute(
            "timezone", Sdf.ValueTypeNames.String, custom=True,
        )
    tz_attr.Set(schedule.timezone)

    _replace_day_table(stage, "/schedule/work_hours", schedule.work_hours)
    _replace_day_table(stage, "/schedule/family_hours", schedule.family_hours)
    _replace_overrides(stage, "/schedule/overrides", schedule.overrides)

    if not stage.GetPrimAtPath("/schedule/inferred").IsValid():
        stage.DefinePrim("/schedule/inferred")


def _replace_day_table(stage, root_path: str, table: dict[str, DayWindow]) -> None:
    root = stage.GetPrimAtPath(root_path)
    if root and root.IsValid():
        for child in list(root.GetChildren()):
            stage.RemovePrim(child.GetPath())
    else:
        stage.DefinePrim(root_path)
    for day, window in table.items():
        _author_day_window(stage, f"{root_path}/{day}", window)


def _author_day_window(stage, path: str, window: DayWindow) -> None:
    from pxr import Sdf
    prim = stage.DefinePrim(path)
    if window.all_day:
        prim.CreateAttribute(
            "all_day", Sdf.ValueTypeNames.Bool, custom=True,
        ).Set(True)
        return
    if window.start is not None:
        prim.CreateAttribute(
            "start", Sdf.ValueTypeNames.String, custom=True,
        ).Set(_format_hhmm(window.start))
    if window.end is not None:
        prim.CreateAttribute(
            "end", Sdf.ValueTypeNames.String, custom=True,
        ).Set(_format_hhmm(window.end))


def _replace_overrides(stage, root_path: str, overrides) -> None:
    root = stage.GetPrimAtPath(root_path)
    if root and root.IsValid():
        for child in list(root.GetChildren()):
            stage.RemovePrim(child.GetPath())
    else:
        stage.DefinePrim(root_path)
    for ov in overrides:
        _author_override(stage, f"{root_path}/{ov.name}", ov)


def _author_override(stage, path: str, ov: Override) -> None:
    from pxr import Sdf
    prim = stage.DefinePrim(path)
    prim.CreateAttribute("kind", Sdf.ValueTypeNames.String, custom=True).Set(ov.kind)
    prim.CreateAttribute("start_date", Sdf.ValueTypeNames.String, custom=True).Set(ov.start_date.isoformat())
    prim.CreateAttribute("end_date", Sdf.ValueTypeNames.String, custom=True).Set(ov.end_date.isoformat())
    prim.CreateAttribute("start_time", Sdf.ValueTypeNames.String, custom=True).Set(_format_hhmm(ov.start_time))
    prim.CreateAttribute("end_time", Sdf.ValueTypeNames.String, custom=True).Set(_format_hhmm(ov.end_time))
    prim.CreateAttribute("state", Sdf.ValueTypeNames.String, custom=True).Set(ov.state.name)
    if ov.notes:
        prim.CreateAttribute("notes", Sdf.ValueTypeNames.String, custom=True).Set(ov.notes)
