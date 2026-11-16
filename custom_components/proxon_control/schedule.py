"""Weekly ventilation schedule: reading phases, the edit rules of the unit, and the order of the writes.

7 days x 3 phases; each phase has a start, an end and a ventilation level (0 = phase not active, 1..4).
Rules (found on a real unit and documented by the ha-lan-proxon project, MIT licence):
  * an active phase ends after it starts. Phases across midnight (e.g. 21:01-06:00, set at the unit's panel) do exist on
    real units: they are kept and respected, only new ones aren't written from here,
  * active phases of a day don't overlap and don't share a boundary minute,
  * a phase that is running right now may only change its level (1..4), with at least 10 minutes to both ends,
  * times may only change (or a phase be switched on) when it starts at least 2 hours from now by the unit's clock.
No Home Assistant imports, so the rules can be tested on their own.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .registers import SCHEDULE_FIELDS, SCHEDULE_PHASES, schedule_key

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MIN_LEAD_MINUTES = 120  # time changes only for phases starting at least 2 h from now
RUNNING_MARGIN_MINUTES = 10  # level changes of a running phase need this much time to both ends
WEEK_MINUTES = 7 * 24 * 60


class ScheduleError(Exception):
    """A change the unit would not accept. `key` and `placeholders` are used for the translated message."""

    def __init__(self, key: str, **placeholders: str) -> None:
        super().__init__(f"{key}: {placeholders}")
        self.key = key
        self.placeholders = placeholders


@dataclass(frozen=True)
class Phase:
    start: int  # minutes after midnight
    end: int
    level: int  # 0 = not active

    @property
    def active(self) -> bool:
        return self.level > 0

    def fields(self) -> tuple[int, int, int, int, int]:
        return (self.start // 60, self.start % 60, self.end // 60, self.end % 60, self.level)


def hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def read_day(values: dict, day: int) -> list[Phase] | None:
    """The three phases of a day as the unit holds them, or None while the schedule hasn't been read."""
    phases = []
    for p in range(SCHEDULE_PHASES):
        raw = [values.get(schedule_key(day, p, f)) for f in range(len(SCHEDULE_FIELDS))]
        if any(not isinstance(v, (int, float)) for v in raw):
            return None
        sh, sm, eh, em, lv = (int(v) for v in raw if v is not None)
        phases.append(Phase(sh * 60 + sm, eh * 60 + em, lv if 0 <= lv <= 4 else 0))
    return phases


def summary(phases: list[Phase], level_word: str, off_word: str) -> str:
    """One line per day, e.g. "06:00–08:00 Stufe 2 · 17:00–22:00 Stufe 3"."""
    parts = [f"{hhmm(p.start)}–{hhmm(p.end)} {level_word} {p.level}" for p in sorted(phases, key=lambda p: p.start) if p.active]
    return " · ".join(parts) if parts else off_word


def unit_clock(values: dict) -> datetime | None:
    """The unit's own clock (local time), or None when it isn't known."""
    keys = ("UhrMinute", "UhrStunde", "UhrTag", "UhrMonat", "UhrJahr")
    raw = [values.get(k) for k in keys]
    if any(not isinstance(v, (int, float)) for v in raw):
        return None
    minute, hour, day, month, year = (int(v) for v in raw if v is not None)
    try:
        return datetime(2000 + year if year < 100 else year, month, day, hour, minute)
    except ValueError:
        return None


def clock_drift(values: dict, now: datetime) -> int | None:
    """How many minutes the unit's clock is ahead (+) or behind (-) of `now` (local time). The unit's clock has whole minutes."""
    clock = unit_clock(values)
    if clock is None:
        return None
    return round((clock - now.replace(tzinfo=None, second=0, microsecond=0)).total_seconds() / 60)


DAY_MINUTES = 24 * 60


def _covered(p: Phase) -> set[int]:
    """The minutes of the day a phase covers, both ends included (a phase across midnight covers the evening and the morning)."""
    if p.start <= p.end:
        return set(range(p.start, p.end + 1))
    return set(range(p.start, DAY_MINUTES)) | set(range(0, p.end + 1))


def validate_day(phases: list[Phase], changed: set[int] | None = None, allow_overnight: bool = False) -> None:
    """Check a day's phases. `changed`: the phases being changed (None = all) - a phase across midnight is only accepted
    when it is not one of them (it was set at the unit itself), or when `allow_overnight` (copied from another day of the
    unit, which holds it)."""
    for i, p in enumerate(phases):
        if not p.active:
            continue
        if not (0 <= p.start < DAY_MINUTES and 0 <= p.end < DAY_MINUTES):
            raise ScheduleError("schedule_invalid_time", phase=str(i + 1))
        if p.end == p.start or (p.end < p.start and not allow_overnight and (changed is None or i in changed)):
            raise ScheduleError("schedule_end_before_start", phase=str(i + 1), start=hhmm(p.start), end=hhmm(p.end))
    active = sorted((p for p in phases if p.active), key=lambda p: p.start)
    for n, a in enumerate(active):
        for b in active[n + 1:]:
            if _covered(a) & _covered(b):
                raise ScheduleError(
                    "schedule_overlap", first=f"{hhmm(a.start)}–{hhmm(a.end)}", second=f"{hhmm(b.start)}–{hhmm(b.end)}"
                )


def _running(p: Phase, day: int, now: datetime) -> bool:
    """Whether a phase of `day` is running at `now` (a phase across midnight runs on into the next morning)."""
    if not p.active:
        return False
    now_m = now.hour * 60 + now.minute
    if p.start < p.end:
        return now.weekday() == day and p.start <= now_m < p.end
    return (now.weekday() == day and now_m >= p.start) or (now.weekday() == (day + 1) % 7 and now_m < p.end)


def _minutes_until(now: datetime, day: int, minute: int) -> int:
    """Minutes from `now` until the next time `day` (0 = Monday) at `minute` comes round."""
    now_m = now.weekday() * 24 * 60 + now.hour * 60 + now.minute
    return (day * 24 * 60 + minute - now_m) % WEEK_MINUTES


def plan_day(day: int, old: list[Phase], new: list[Phase], now: datetime | None, allow_overnight: bool = False) -> list[tuple[str, int]]:
    """Check a new set of phases for one day against the rules and return the writes (key, value) in a safe order:
    first switch off phases whose times change, then write the times, then the levels."""
    # phases whose times change or that are switched on: these must end after they start (a level change alone is fine)
    validate_day(
        new, {i for i, (o, n) in enumerate(zip(old, new)) if n.active and ((o.start, o.end) != (n.start, n.end) or not o.active)},
        allow_overnight,
    )
    deactivate: list[tuple[str, int]] = []
    times: list[tuple[str, int]] = []
    levels: list[tuple[str, int]] = []
    for p, (o, n) in enumerate(zip(old, new)):
        if o == n:
            continue
        if not o.active and not n.active:
            # a phase that stays off: its times can be prepared freely (they only count once it is switched on)
            for f, (a, b) in enumerate(zip(o.fields()[:4], n.fields()[:4])):
                if a != b:
                    times.append((schedule_key(day, p, f), b))
            continue
        times_change = (o.start, o.end) != (n.start, n.end)
        if now is not None and _running(o, day, now):
            if times_change or not n.active:
                raise ScheduleError("schedule_running", phase=str(p + 1), start=hhmm(o.start), end=hhmm(o.end))
            now_m = now.hour * 60 + now.minute
            if (now_m - o.start) % DAY_MINUTES < RUNNING_MARGIN_MINUTES or (o.end - now_m) % DAY_MINUTES < RUNNING_MARGIN_MINUTES:
                raise ScheduleError("schedule_running_margin", phase=str(p + 1))
            levels.append((schedule_key(day, p, 4), n.level))
            continue
        if not n.active:
            # switching a phase off: only its level (its times stay as they are)
            levels.append((schedule_key(day, p, 4), 0))
            continue
        if times_change or not o.active:
            if now is None:
                raise ScheduleError("schedule_clock_unknown")
            starts = [n.start] + ([o.start] if o.active else [])
            if any(_minutes_until(now, day, s) < MIN_LEAD_MINUTES for s in starts):
                raise ScheduleError("schedule_too_soon", phase=str(p + 1))
        if not times_change:
            levels.append((schedule_key(day, p, 4), n.level))
            continue
        if o.active:
            deactivate.append((schedule_key(day, p, 4), 0))
        for f, (a, b) in enumerate(zip(o.fields()[:4], n.fields()[:4])):
            if a != b:
                times.append((schedule_key(day, p, f), b))
        levels.append((schedule_key(day, p, 4), n.level))
    return deactivate + times + levels


def set_phase(phases: list[Phase], phase: int, start: int | None, end: int | None, level: int) -> list[Phase]:
    """The day's phases with one phase changed (start/end None = keep)."""
    out = list(phases)
    cur = out[phase]
    out[phase] = replace(cur, start=cur.start if start is None else start, end=cur.end if end is None else end, level=level)
    return out
