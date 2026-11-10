"""Hot water as a store for solar surplus and cheap electricity: the decision rules (no Home Assistant imports).

While solar surplus or a cheap electricity price is available, the hot-water target is raised (e.g. 46 -> 55 °C), so the
hot-water heat pump heats the tank with that energy; afterwards the previous target is written back.

Protection for the unit (the hot-water module takes a while for every change, frequent switching isn't good for it):
  * solar: the surplus has to stay above the limit for START_DELAY before heating starts,
  * heating stops only after the reason has been gone for STOP_DELAY, and never before MIN_RUN,
  * after a stop it waits MIN_PAUSE before starting again, and starts at most MAX_STARTS times a day.
While heating with solar power the heat pump uses part of the surplus itself, so heating goes on as long as power is still
being fed in (no grid import), not only while the surplus is above the limit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

START_DELAY = timedelta(minutes=10)
STOP_DELAY = timedelta(minutes=10)
MIN_RUN = timedelta(minutes=30)
MIN_PAUSE = timedelta(minutes=30)
MAX_STARTS = 6

SOLAR = "solar"
PRICE = "price"

# status shown by the sensor
OFF = "off"  # both switches off
WAITING = "waiting"  # switched on, no surplus / price too high
STARTING = "starting"  # condition met, waiting for START_DELAY
HEATING_SOLAR = "heating_solar"
HEATING_PRICE = "heating_price"
PAUSED = "paused"  # minimum pause after a stop or daily limit reached
BLOCKED = "blocked"  # hot water switched off, holiday mode, or values missing
NO_SOURCE = "no_source"  # switched on, but no sensor chosen / sensor without a value


@dataclass
class Settings:
    solar_on: bool = False
    price_on: bool = False
    surplus_w: float = 1500.0
    price_ct: float = 10.0
    store_temp: float = 55.0


@dataclass
class State:
    active: str | None = None  # SOLAR / PRICE while heating
    since: datetime | None = None  # start of the current heating
    want_since: datetime | None = None  # since when the reason to start has been there
    bad_since: datetime | None = None  # since when the reason to go on has been gone
    last_stop: datetime | None = None
    starts_day: date | None = None
    starts: int = 0
    saved_target: float | None = None  # hot-water target before heating started

    def to_dict(self) -> dict:
        def iso(v):
            return v.isoformat() if v else None
        return {
            "active": self.active, "since": iso(self.since), "last_stop": iso(self.last_stop),
            "starts_day": iso(self.starts_day), "starts": self.starts, "saved_target": self.saved_target,
        }

    @classmethod
    def from_dict(cls, d: dict) -> State:
        def dt(v):
            return datetime.fromisoformat(v) if v else None
        return cls(
            active=d.get("active"), since=dt(d.get("since")), last_stop=dt(d.get("last_stop")),
            starts_day=date.fromisoformat(d["starts_day"]) if d.get("starts_day") else None,
            starts=int(d.get("starts") or 0), saved_target=d.get("saved_target"),
        )


@dataclass
class Decision:
    action: str | None  # "start", "stop" or None
    status: str
    source: str | None = None  # what the start is for
    details: dict = field(default_factory=dict)


def decide(now: datetime, s: Settings, st: State, surplus_w: float | None, price_ct: float | None, unit_ok: bool) -> Decision:
    """What to do now. Updates the timers in `st` (want_since / bad_since); start/stop bookkeeping is done by the caller."""
    details = {"surplus_w": surplus_w, "price_ct": price_ct}
    if st.starts_day != now.date():
        st.starts_day, st.starts = now.date(), 0
    details["starts_today"] = st.starts

    if not s.solar_on and not s.price_on:
        st.want_since = st.bad_since = None
        return Decision("stop" if st.active else None, OFF, details=details)
    if not unit_ok:
        st.want_since = st.bad_since = None
        return Decision("stop" if st.active else None, BLOCKED, details=details)

    solar_start = s.solar_on and surplus_w is not None and surplus_w >= s.surplus_w
    solar_go_on = s.solar_on and surplus_w is not None and surplus_w >= 0  # still feeding in
    price_ok = s.price_on and price_ct is not None and price_ct <= s.price_ct
    has_source = (s.solar_on and surplus_w is not None) or (s.price_on and price_ct is not None)

    if st.active:
        heating = HEATING_SOLAR if st.active == SOLAR else HEATING_PRICE
        if (st.active == SOLAR and not s.solar_on) or (st.active == PRICE and not s.price_on):
            # the user switched this off: stop right away (or carry on if the other reason would start heating anyway)
            if price_ok or solar_start:
                st.active = PRICE if price_ok else SOLAR
                return Decision(None, HEATING_PRICE if price_ok else HEATING_SOLAR, details=details)
            return Decision("stop", OFF if not (s.solar_on or s.price_on) else WAITING, details=details)
        if price_ok or solar_go_on:
            st.bad_since = None
            return Decision(None, heating, details=details)
        st.bad_since = st.bad_since or now
        if now - st.bad_since >= STOP_DELAY and st.since is not None and now - st.since >= MIN_RUN:
            return Decision("stop", WAITING, details=details)
        return Decision(None, heating, details=details)

    if not has_source:
        st.want_since = None
        return Decision(None, NO_SOURCE, details=details)
    if not (solar_start or price_ok):
        st.want_since = None
        return Decision(None, WAITING, details=details)
    st.want_since = st.want_since or now
    if st.starts >= MAX_STARTS or (st.last_stop is not None and now - st.last_stop < MIN_PAUSE):
        return Decision(None, PAUSED, details=details)
    # a cheap price is known in advance and changes in steps: start right away; solar surplus has to last a while
    if price_ok:
        return Decision("start", HEATING_PRICE, PRICE, details)
    if now - st.want_since >= START_DELAY:
        return Decision("start", HEATING_SOLAR, SOLAR, details)
    return Decision(None, STARTING, details=details)


def started(st: State, now: datetime, source: str, saved_target: float | None) -> None:
    st.active, st.since, st.want_since, st.bad_since = source, now, None, None
    st.starts += 1
    st.saved_target = saved_target


def stopped(st: State, now: datetime) -> None:
    st.active, st.since, st.bad_since, st.want_since = None, None, None, None
    st.last_stop = now
    st.saved_target = None


def price_in_cent(value: float, unit: str | None) -> float:
    """Electricity price in ct/kWh, whatever unit the sensor uses (€/kWh, EUR/kWh, ct/kWh, EUR/MWh)."""
    u = (unit or "").lower().replace(" ", "")
    if "mwh" in u:
        return value / 10  # €/MWh -> ct/kWh
    if "ct" in u or "cent" in u:
        return value
    if "€" in u or "eur" in u:
        return value * 100
    return value


def power_in_watt(value: float, unit: str | None, feed_in_negative: bool) -> float:
    """Surplus in W (positive = fed into the grid)."""
    u = (unit or "").lower()
    w = value * 1000 if u.startswith("kw") else value
    return -w if feed_in_negative else w
