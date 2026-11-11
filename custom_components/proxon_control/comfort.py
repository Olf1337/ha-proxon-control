"""Summer night cooling and hot-water boost: the decision rules (no Home Assistant imports). Only the unit's own sensors are used.

Summer night cooling (operating mode "Summer" only):
  * cooling: inside (extract air T7) warmer than the wish temperature and outside (fresh air T3) at least COOL_DIFF cooler
    -> ventilation at the cooling level; goes on while inside is above wish − 0.5 °C and outside at least 1 °C cooler,
  * heat protection: inside warmer than the wish temperature and outside warmer than inside -> ventilation level 1,
  * otherwise the level from before is restored.
  A new situation has to last HOLD minutes, and the level changes at most every HOLD minutes.

Hot-water boost: hot water below the limit -> immersion heater on, until the limit is reached again -> off.
Only switched off again if the boost switched it on; at least MIN_RUN on and MIN_PAUSE off. Not during holiday mode.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

# ---------------- summer night cooling ----------------
HOLD = timedelta(minutes=15)
COOL_DIFF = 3.0  # outside at least this much cooler than inside to start cooling
COOL_KEEP_DIFF = 1.0  # ... and still this much cooler to go on
TARGET_BAND = 0.5  # cooling goes on down to wish temperature − this
MODE_SUMMER = 1

COOLING = "cooling"
PROTECTING = "heat_protection"
# status
C_OFF = "off"
C_IDLE = "idle"  # nothing to do (inside cool enough / outside not cooler)
C_WAITING = "waiting"  # situation changed, waiting for HOLD
C_COOLING = "cooling"
C_PROTECTING = "heat_protection"
C_NOT_SUMMER = "not_summer"  # only in operating mode "Summer"
C_BLOCKED = "blocked"  # holiday mode, boost ventilation, values missing


@dataclass
class CoolSettings:
    on: bool = False
    wish: float = 22.0
    level: int = 3


@dataclass
class CoolState:
    mode: str | None = None  # COOLING / PROTECTING while it controls the level
    saved_level: int | None = None  # level before it took over
    last_change: datetime | None = None
    want: str | None = None  # situation seen, and since when
    want_since: datetime | None = None

    def to_dict(self) -> dict:
        return {"mode": self.mode, "saved_level": self.saved_level, "last_change": self.last_change.isoformat() if self.last_change else None}

    @classmethod
    def from_dict(cls, d: dict) -> CoolState:
        lc = d.get("last_change")
        return cls(mode=d.get("mode"), saved_level=d.get("saved_level"), last_change=datetime.fromisoformat(lc) if lc else None)


@dataclass
class CoolDecision:
    level: int | None  # level to write now (None = nothing)
    status: str
    details: dict = field(default_factory=dict)


def _situation(s: CoolSettings, st: CoolState, inside: float, outside: float) -> str | None:
    if st.mode == COOLING:
        if inside > s.wish - TARGET_BAND and outside <= inside - COOL_KEEP_DIFF:
            return COOLING
    elif inside > s.wish and outside <= inside - COOL_DIFF:
        return COOLING
    if st.mode == PROTECTING:
        if inside > s.wish - TARGET_BAND and outside >= inside:
            return PROTECTING
    elif inside > s.wish and outside >= inside + COOL_KEEP_DIFF:
        return PROTECTING
    return None


def decide_cooling(
    now: datetime, s: CoolSettings, st: CoolState, *, mode: int | None, inside: float | None, outside: float | None,
    level_now: float | None, boost: bool, holiday: bool,
) -> CoolDecision:
    details = {"inside": inside, "outside": outside}
    restore = st.saved_level if st.mode else None

    def leave(status: str, write: bool) -> CoolDecision:
        st.mode, st.saved_level, st.want, st.want_since = None, None, None, None
        st.last_change = now if restore is not None and write else st.last_change
        return CoolDecision(restore if write and restore is not None and restore != level_now else None, status, details)

    if not s.on:
        return leave(C_OFF, write=mode == MODE_SUMMER and not boost)
    if mode != MODE_SUMMER:
        return leave(C_NOT_SUMMER, write=False)  # the unit chooses the level in the other modes / it isn't summer
    if holiday or boost or inside is None or outside is None or level_now is None:
        return leave(C_BLOCKED, write=not holiday and not boost and level_now is not None)

    wanted = _situation(s, st, inside, outside)
    if wanted == st.mode:
        st.want, st.want_since = None, None
        status = {COOLING: C_COOLING, PROTECTING: C_PROTECTING}.get(st.mode, C_IDLE)
        # cooling level changed while cooling: follow it
        if st.mode == COOLING and int(level_now) != s.level and (st.last_change is None or now - st.last_change >= HOLD):
            st.last_change = now
            return CoolDecision(s.level, status, details)
        return CoolDecision(None, status, details)
    if st.want_since is None or st.want != wanted:
        st.want, st.want_since = wanted, now
    if now - st.want_since < HOLD or (st.last_change is not None and now - st.last_change < HOLD):
        return CoolDecision(None, C_WAITING, details)
    # the new situation has lasted long enough
    if st.mode is None:
        st.saved_level = int(level_now)
    st.want, st.want_since, st.last_change = None, None, now
    if wanted is None:
        level, st.mode, st.saved_level = st.saved_level, None, None
        return CoolDecision(level if level is not None and level != level_now else None, C_IDLE, details)
    st.mode = wanted
    level = s.level if wanted == COOLING else 1
    return CoolDecision(level if level != level_now else None, C_COOLING if wanted == COOLING else C_PROTECTING, details)


# ---------------- hot-water boost ----------------
MIN_RUN = timedelta(minutes=10)
MIN_PAUSE = timedelta(minutes=10)
B_OFF = "off"
B_IDLE = "idle"  # hot water warm enough
B_HEATING = "heating"  # immersion heater switched on by the boost
B_ALREADY_ON = "heater_on"  # immersion heater already on (switched on by hand or the unit)
B_PAUSED = "paused"
B_BLOCKED = "blocked"  # holiday mode or value missing


@dataclass
class BoostSettings:
    on: bool = False
    limit: float = 40.0


@dataclass
class BoostState:
    active: bool = False  # the boost switched the immersion heater on
    since: datetime | None = None
    last_stop: datetime | None = None

    def to_dict(self) -> dict:
        def iso(v):
            return v.isoformat() if v else None
        return {"active": self.active, "since": iso(self.since), "last_stop": iso(self.last_stop)}

    @classmethod
    def from_dict(cls, d: dict) -> BoostState:
        def dt(v):
            return datetime.fromisoformat(v) if v else None
        return cls(active=bool(d.get("active")), since=dt(d.get("since")), last_stop=dt(d.get("last_stop")))


def decide_boost(now: datetime, s: BoostSettings, st: BoostState, *, water: float | None, heater_on: bool | None, holiday: bool) -> tuple[str | None, str]:
    """Returns (action, status); action is "on", "off" or None."""
    if not s.on or holiday:
        return ("off" if st.active else None), (B_OFF if not s.on else B_BLOCKED)
    if water is None or heater_on is None:
        return None, B_BLOCKED
    if st.active:
        if water >= s.limit and st.since is not None and now - st.since >= MIN_RUN:
            return "off", B_IDLE
        return None, B_HEATING
    if water >= s.limit:
        return None, B_IDLE
    if heater_on:
        return None, B_ALREADY_ON
    if st.last_stop is not None and now - st.last_stop < MIN_PAUSE:
        return None, B_PAUSED
    return "on", B_HEATING


# ---------------- automatic summer / winter ----------------
# Switches between the operating modes "Summer" and "Winter" by the average outdoor temperature (fresh air T3) of the last
# two days: below "winter below" -> Winter, above "summer above" -> Summer, in between nothing changes. Only while the unit
# is in Summer or Winter (ECO Comfort, Off, stove mode and holiday stay untouched), at most every MIN_SWITCH.
SEASON_WINDOW = timedelta(hours=48)
SEASON_MIN_DATA = timedelta(hours=12)  # enough values for an average
SEASON_SAMPLE = timedelta(minutes=30)
SEASON_MIN_SWITCH = timedelta(hours=12)
MODE_WINTER = 2

S_OFF = "off"
S_COLLECTING = "collecting"  # not enough outdoor temperatures yet
S_SUMMER = "summer"
S_WINTER = "winter"
S_MANUAL = "other_mode"  # the unit is in ECO Comfort / Off / stove mode: left alone
S_BLOCKED = "blocked"  # holiday mode, values missing


@dataclass
class SeasonSettings:
    on: bool = False
    winter_below: float = 14.0
    summer_above: float = 17.0


@dataclass
class SeasonState:
    samples: list[tuple[datetime, float]] = field(default_factory=list)
    last_switch: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "samples": [[t.isoformat(), v] for t, v in self.samples],
            "last_switch": self.last_switch.isoformat() if self.last_switch else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> SeasonState:
        samples = []
        for item in d.get("samples") or []:
            try:
                samples.append((datetime.fromisoformat(item[0]), float(item[1])))
            except (TypeError, ValueError, IndexError):
                continue
        ls = d.get("last_switch")
        return cls(samples=samples, last_switch=datetime.fromisoformat(ls) if ls else None)


def season_average(st: SeasonState, now: datetime) -> float | None:
    """Average outdoor temperature of the last two days, once at least 12 hours are known."""
    st.samples = [(t, v) for t, v in st.samples if now - t <= SEASON_WINDOW]
    if not st.samples or now - st.samples[0][0] < SEASON_MIN_DATA:
        return None
    return round(sum(v for _, v in st.samples) / len(st.samples), 1)


def decide_season(
    now: datetime, s: SeasonSettings, st: SeasonState, *, mode: int | None, outside: float | None, holiday: bool,
) -> tuple[int | None, str, dict]:
    """Returns (mode to write or None, status, details). Outdoor temperatures are collected even while switched off."""
    if outside is not None and (not st.samples or now - st.samples[-1][0] >= SEASON_SAMPLE):
        st.samples.append((now, float(outside)))
    avg = season_average(st, now)
    details = {"average_outdoor": avg, "hours_known": round((now - st.samples[0][0]).total_seconds() / 3600, 1) if st.samples else 0}
    if not s.on:
        return None, S_OFF, details
    if holiday or mode is None:
        return None, S_BLOCKED, details
    if mode not in (MODE_SUMMER, MODE_WINTER):
        return None, S_MANUAL, details
    current = S_SUMMER if mode == MODE_SUMMER else S_WINTER
    if avg is None:
        return None, S_COLLECTING, details
    if st.last_switch is not None and now - st.last_switch < SEASON_MIN_SWITCH:
        return None, current, details
    if mode == MODE_WINTER and avg > s.summer_above:
        st.last_switch = now
        return MODE_SUMMER, S_SUMMER, details
    if mode == MODE_SUMMER and avg < s.winter_below:
        st.last_switch = now
        return MODE_WINTER, S_WINTER, details
    return None, current, details
