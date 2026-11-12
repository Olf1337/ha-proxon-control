"""Legionella protection with solar power: the decision rules (no Home Assistant imports).

Once a week the hot water has to get hot enough against legionella (60 °C). Instead of the unit's own legionella function
(which heats at a fixed time, often from the grid), the immersion heater does it on a day with solar surplus:
  * from DAYS_SUN days after the last time the water was that hot, a sunny moment is looked for: the surplus has to stay above
    the limit of "solar hot water" for START_DELAY,
  * after INTERVAL it heats anyway (at the latest after a week, sun or not),
  * heating: the heater's target is set to TEMP and the heater switched on; it ends when the middle of the tank reached TEMP,
    or after MAX_RUN (then it tries again after RETRY), and the heater's target and switch are put back as they were,
  * any time the water gets that hot by itself, that counts as done,
  * not in holiday mode and not without the unit's values.
While the function is on, the unit's own legionella function is switched off (and switched on again with this one off).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

TEMP = 60.0
REACHED = TEMP - 0.5  # the sensor sits in the middle of the tank: half a degree below counts
INTERVAL = timedelta(days=7)
DAYS_SUN = timedelta(days=5)
START_DELAY = timedelta(minutes=10)
MAX_RUN = timedelta(hours=4)
RETRY = timedelta(hours=12)

SOLAR = "solar"
DUE = "due"

# status shown by the sensor
OFF = "off"
WAITING = "waiting"  # done not long ago, next one later
LOOKING = "looking_for_sun"  # due soon: waits for solar surplus
STARTING = "starting"  # surplus there, waiting for START_DELAY
HEATING_SOLAR = "heating_solar"
HEATING_DUE = "heating_due"  # a week without sun: heats anyway
BLOCKED = "blocked"  # holiday mode or values missing


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

    def to_dict(self) -> dict:
        def iso(v):
            return v.isoformat() if v else None
        return {
            "on": self.on, "reference": iso(self.reference), "last_done": iso(self.last_done), "active": self.active,
            "since": iso(self.since), "last_try": iso(self.last_try), "saved_heater_target": self.saved_heater_target,
            "saved_heater_on": self.saved_heater_on, "unit_function_was_on": self.unit_function_was_on,
        }

    @classmethod
    def from_dict(cls, d: dict) -> State:
        def dt(v):
            return datetime.fromisoformat(v) if v else None
        return cls(
            on=bool(d.get("on")), reference=dt(d.get("reference")), last_done=dt(d.get("last_done")), active=d.get("active"),
            since=dt(d.get("since")), last_try=dt(d.get("last_try")), saved_heater_target=d.get("saved_heater_target"),
            saved_heater_on=d.get("saved_heater_on"), unit_function_was_on=bool(d.get("unit_function_was_on")),
        )


def next_due(st: State) -> datetime | None:
    """When it heats at the latest (sun or not)."""
    ref = st.last_done or st.reference
    return None if ref is None else ref + INTERVAL


def decide(now: datetime, st: State, *, water: float | None, surplus_w: float | None, surplus_limit: float,
           blocked: bool) -> tuple[str | None, str]:
    """Returns (action, status); action is "start_solar", "start_due", "stop" or None. Updates last_done / want_since."""
    if water is not None and water >= REACHED:
        st.last_done = now
        if st.active:
            return "stop", WAITING
    if not st.on:
        st.want_since = None
        return ("stop" if st.active else None), OFF
    if blocked or water is None:
        st.want_since = None
        return ("stop" if st.active else None), BLOCKED
    if st.active:
        if st.since is not None and now - st.since >= MAX_RUN:
            return "stop", WAITING
        return None, HEATING_SOLAR if st.active == SOLAR else HEATING_DUE
    ref = st.last_done or st.reference or now
    if st.last_try is not None and now - st.last_try < RETRY:
        st.want_since = None
        return None, WAITING
    if now - ref >= INTERVAL:
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
