"""Legionella protection with solar power: the decision rules (no Home Assistant imports).

Once a week the hot water has to get hot enough against legionella (60 °C). Instead of the unit's own legionella function
(which heats at a fixed time, often from the grid), the immersion heater does it on a day with solar surplus:
  * from DAYS_SUN days after the last time the water was that hot, a sunny moment is looked for: the surplus has to stay above
    the limit of "solar hot water" for START_DELAY,
  * without sun it heats anyway on the day a week is over, at DUE_TIME (a time of the user's choice, e.g. midday for the
    last bit of sun or the night for a cheap tariff; so between 6 and 8 days after the last time),
  * heating: the heater's target is set to TEMP and the heater switched on; it ends when the middle of the tank reached TEMP,
    or after MAX_RUN (then it tries again after RETRY), and the heater's target and switch are put back as they were,
  * any time the water gets that hot by itself, that counts as done,
  * not in holiday mode and not without the unit's values.
Planned instead ("plan"): the same heating once a week on a chosen weekday at a chosen time, sun or not; skipped when the
water was that hot in the day before; a heating that didn't reach TEMP is tried again after RETRY, up to PLAN_WINDOW after
the planned time. Only one of the two is on: switching one on switches the other off.
While one of them is on, the unit's own legionella function is switched off (and switched on again when both are off).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta

TEMP = 60.0
REACHED = TEMP - 0.5  # the sensor sits in the middle of the tank: half a degree below counts
INTERVAL = timedelta(days=7)
DAYS_SUN = timedelta(days=5)
START_DELAY = timedelta(minutes=10)
MAX_RUN = timedelta(hours=4)
RETRY = timedelta(hours=12)
DUE_TIME = time(13, 0)  # default time of the heating without sun
PLAN_DAY = 6  # default weekday of the planned heating (0 Monday ... 6 Sunday)
PLAN_TIME = time(13, 0)
PLAN_WINDOW = timedelta(hours=24)  # a planned heating is tried this long after its time (then it waits for the next week)

SOLAR = "solar"
DUE = "due"
PLAN = "plan"

# status shown by the sensor
OFF = "off"
WAITING = "waiting"  # done not long ago, next one later
LOOKING = "looking_for_sun"  # due soon: waits for solar surplus
STARTING = "starting"  # surplus there, waiting for START_DELAY
HEATING_SOLAR = "heating_solar"
HEATING_DUE = "heating_due"  # a week without sun: heats anyway
BLOCKED = "blocked"  # holiday mode or values missing
PLANNED = "planned"  # planned: waits for the chosen day and time
HEATING_PLANNED = "heating_planned"


@dataclass
class State:
    on: bool = False
    reference: datetime | None = None  # switched on at (counts as the last time until the water was really hot)
    last_done: datetime | None = None  # the water reached TEMP
    active: str | None = None  # SOLAR / DUE while heating
    since: datetime | None = None
    want_since: datetime | None = None
    last_try: datetime | None = None  # a heating that ended without reaching TEMP
    saved_heater_target: float | None = None
    saved_heater_on: bool | None = None
    unit_function_was_on: bool = False  # the unit's own legionella function was on when this was switched on
    watching_since: datetime | None = None  # since when the water temperature is watched (for the legionella notice)
    due_time: time = DUE_TIME  # when it heats without sun, on the day a week is over
    plan_on: bool = False  # planned instead: on a weekday at a time
    plan_day: int = PLAN_DAY
    plan_time: time = PLAN_TIME
    plan_slot: datetime | None = None  # the planned time last dealt with (done, skipped or given up)

    def to_dict(self) -> dict:
        def iso(v):
            return v.isoformat() if v else None
        return {
            "on": self.on, "reference": iso(self.reference), "last_done": iso(self.last_done), "active": self.active,
            "since": iso(self.since), "last_try": iso(self.last_try), "saved_heater_target": self.saved_heater_target,
            "saved_heater_on": self.saved_heater_on, "unit_function_was_on": self.unit_function_was_on,
            "watching_since": iso(self.watching_since), "due_time": self.due_time.strftime("%H:%M"),
            "plan_on": self.plan_on, "plan_day": self.plan_day, "plan_time": self.plan_time.strftime("%H:%M"),
            "plan_slot": iso(self.plan_slot),
        }

    @classmethod
    def from_dict(cls, d: dict) -> State:
        def dt(v):
            return datetime.fromisoformat(v) if v else None
        return cls(
            on=bool(d.get("on")), reference=dt(d.get("reference")), last_done=dt(d.get("last_done")), active=d.get("active"),
            since=dt(d.get("since")), last_try=dt(d.get("last_try")), saved_heater_target=d.get("saved_heater_target"),
            saved_heater_on=d.get("saved_heater_on"), unit_function_was_on=bool(d.get("unit_function_was_on")),
            watching_since=dt(d.get("watching_since")), due_time=_time(d.get("due_time")),
            plan_on=bool(d.get("plan_on")), plan_day=_day(d.get("plan_day")), plan_time=_time(d.get("plan_time"), PLAN_TIME),
            plan_slot=dt(d.get("plan_slot")),
        )


def _time(v, default: time = DUE_TIME) -> time:
    try:
        return time.fromisoformat(v) if v else default
    except (TypeError, ValueError):
        return default


def _day(v) -> int:
    return v if isinstance(v, int) and 0 <= v <= 6 else PLAN_DAY


def last_slot(now: datetime, day: int, at: time) -> datetime:
    """The latest planned time (weekday `day` at `at`) that isn't after now."""
    slot = datetime.combine((now - timedelta(days=(now.weekday() - day) % 7)).date(), at, tzinfo=now.tzinfo)
    return slot - timedelta(days=7) if slot > now else slot


def next_slot(now: datetime, st: State) -> datetime:
    """The next planned heating (the latest planned time if it is still to be done)."""
    slot = last_slot(now, st.plan_day, st.plan_time)
    return slot if st.plan_slot is None or st.plan_slot < slot else slot + timedelta(days=7)


def _due(ref: datetime, at: time) -> datetime:
    """The heating without sun: on the day INTERVAL after ref is over, at the chosen time."""
    return datetime.combine((ref + INTERVAL).date(), at, tzinfo=ref.tzinfo)


def next_due(st: State) -> datetime | None:
    """When it heats at the latest (sun or not)."""
    ref = st.last_done or st.reference
    return None if ref is None else _due(ref, st.due_time)


def decide(now: datetime, st: State, *, water: float | None, surplus_w: float | None, surplus_limit: float,
           blocked: bool) -> tuple[str | None, str]:
    """Returns (action, status); action is "start_solar", "start_due", "start_plan", "stop" or None. Updates last_done /
    want_since / plan_slot."""
    rest = PLANNED if st.plan_on else WAITING
    if water is not None and water >= REACHED:
        st.last_done = now
        if st.active:
            return "stop", rest
    if not st.on and not st.plan_on:
        st.want_since = None
        return ("stop" if st.active else None), OFF
    if blocked or water is None:
        st.want_since = None
        return ("stop" if st.active else None), BLOCKED
    if st.active:
        if st.since is not None and now - st.since >= MAX_RUN:
            return "stop", rest
        return None, {SOLAR: HEATING_SOLAR, PLAN: HEATING_PLANNED}.get(st.active, HEATING_DUE)
    if st.plan_on:
        return _decide_plan(now, st)
    ref = st.last_done or st.reference or now
    if st.last_try is not None and now - st.last_try < RETRY:
        st.want_since = None
        return None, WAITING
    if now >= _due(ref, st.due_time):
        return "start_due", HEATING_DUE
    if now - ref < DAYS_SUN:
        st.want_since = None
        return None, WAITING
    if surplus_w is None or surplus_w < surplus_limit:
        st.want_since = None
        return None, LOOKING
    st.want_since = st.want_since or now
    if now - st.want_since >= START_DELAY:
        return "start_solar", HEATING_SOLAR
    return None, STARTING


def started(st: State, now: datetime, source: str, heater_target: float | None, heater_on: bool | None) -> None:
    st.active, st.since, st.want_since = source, now, None
    st.saved_heater_target, st.saved_heater_on = heater_target, heater_on


def stopped(st: State, now: datetime, reached: bool) -> None:
    st.active, st.since, st.want_since = None, None, None
    if not reached:
        st.last_try = now


def days_without_heat(now: datetime, st: State, *, protected: bool) -> int | None:
    """For the notice under Repairs: the whole days the hot water hasn't reached TEMP, once that is INTERVAL or longer and
    nothing protects against legionella (neither this function nor the unit's own one is on); else None."""
    since = st.last_done or st.watching_since
    if protected or since is None or now - since < INTERVAL:
        return None
    return (now - since).days


def _decide_plan(now: datetime, st: State) -> tuple[str | None, str]:
    """The planned heating: at the latest planned time, unless it was dealt with already."""
    st.want_since = None
    slot = last_slot(now, st.plan_day, st.plan_time)
    if st.plan_slot is not None and st.plan_slot >= slot:
        return None, PLANNED
    if now - slot >= PLAN_WINDOW or (st.last_done is not None and st.last_done >= slot - timedelta(days=1)):
        st.plan_slot = slot  # given up for this week, or the water was hot enough the day before: nothing to do
        return None, PLANNED
    if st.last_try is not None and now - st.last_try < RETRY:
        return None, PLANNED
    return "start_plan", HEATING_PLANNED
