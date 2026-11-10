"""Summer night cooling and hot-water boost."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.proxon_control import comfort as C

from .test_integration import call, eid, setup

T0 = datetime(2026, 7, 10, 22, 0)
ON = C.CoolSettings(on=True, wish=22.0, level=3)


def cool(st: C.CoolState, minutes: int, inside, outside, level=2, mode=C.MODE_SUMMER, settings=ON, start=T0, boost=False, holiday=False):
    """Decide once per minute and apply the written level. Returns (decisions, level)."""
    out = []
    for m in range(minutes + 1):
        d = C.decide_cooling(
            start + timedelta(minutes=m), settings, st, mode=mode, inside=inside(m) if callable(inside) else inside,
            outside=outside(m) if callable(outside) else outside, level_now=level, boost=boost, holiday=holiday,
        )
        if d.level is not None:
            level = d.level
        out.append(d)
    return out, level


# ---------------- night cooling rules ----------------
def test_cools_when_outside_is_cooler_after_15_minutes() -> None:
    st = C.CoolState()
    ds, level = cool(st, 16, inside=25.0, outside=18.0)
    assert ds[10].status == C.C_WAITING and ds[10].level is None
    assert ds[15].level == 3 and level == 3 and st.mode == C.COOLING and st.saved_level == 2


def test_back_to_the_old_level_when_cool_enough() -> None:
    st = C.CoolState()
    _, level = cool(st, 15, inside=25.0, outside=18.0)
    ds, level = cool(st, 31, inside=21.4, outside=18.0, level=level, start=T0 + timedelta(minutes=16))
    assert level == 2 and st.mode is None  # restored after 15 more minutes
    assert ds[0].status == C.C_WAITING


def test_stays_cooling_a_little_below_the_wish_temperature() -> None:
    st = C.CoolState()
    _, level = cool(st, 15, inside=25.0, outside=18.0)
    ds, level = cool(st, 40, inside=21.8, outside=18.0, level=level, start=T0 + timedelta(minutes=16))
    assert level == 3 and all(d.status == C.C_COOLING for d in ds)  # 21.8 > 22 - 0.5


def test_heat_protection_during_hot_days() -> None:
    st = C.CoolState()
    ds, level = cool(st, 15, inside=24.0, outside=30.0, level=3)
    assert level == 1 and st.mode == C.PROTECTING and st.saved_level == 3


def test_not_cool_enough_outside_does_nothing() -> None:
    st = C.CoolState()
    ds, level = cool(st, 30, inside=25.0, outside=23.0)  # only 2 °C cooler
    assert level == 2 and all(d.status == C.C_IDLE for d in ds)


def test_only_in_summer_mode_and_not_during_holiday_or_boost() -> None:
    assert cool(C.CoolState(), 20, inside=25.0, outside=18.0, mode=2)[0][-1].status == C.C_NOT_SUMMER
    assert cool(C.CoolState(), 20, inside=25.0, outside=18.0, holiday=True)[0][-1].status == C.C_BLOCKED
    assert cool(C.CoolState(), 20, inside=25.0, outside=18.0, boost=True)[0][-1].status == C.C_BLOCKED


def test_switching_off_restores_the_level() -> None:
    st = C.CoolState()
    _, level = cool(st, 15, inside=25.0, outside=18.0)
    d = C.decide_cooling(T0 + timedelta(minutes=17), C.CoolSettings(on=False), st, mode=C.MODE_SUMMER, inside=25.0, outside=18.0,
                         level_now=level, boost=False, holiday=False)
    assert d.level == 2 and d.status == C.C_OFF and st.mode is None


def test_level_changes_at_most_every_15_minutes() -> None:
    st = C.CoolState()
    # cooling, then hot outside right after: the switch to heat protection waits for 15 minutes
    _, level = cool(st, 15, inside=25.0, outside=18.0)
    ds, level = cool(st, 14, inside=25.0, outside=30.0, level=level, start=T0 + timedelta(minutes=16))
    assert level == 3 and all(d.level is None for d in ds)


# ---------------- hot-water boost rules ----------------
B_ON = C.BoostSettings(on=True, limit=40.0)


def test_boost_switches_the_heater_on_below_the_limit() -> None:
    st = C.BoostState()
    assert C.decide_boost(T0, B_ON, st, water=38.0, heater_on=False, holiday=False) == ("on", C.B_HEATING)
    assert C.decide_boost(T0, B_ON, st, water=41.0, heater_on=False, holiday=False) == (None, C.B_IDLE)


def test_boost_switches_off_when_the_limit_is_reached_after_ten_minutes() -> None:
    st = C.BoostState(active=True, since=T0)
    assert C.decide_boost(T0 + timedelta(minutes=5), B_ON, st, water=40.5, heater_on=True, holiday=False) == (None, C.B_HEATING)
    assert C.decide_boost(T0 + timedelta(minutes=11), B_ON, st, water=40.5, heater_on=True, holiday=False) == ("off", C.B_IDLE)


def test_boost_leaves_a_heater_switched_on_by_hand_alone() -> None:
    st = C.BoostState()
    assert C.decide_boost(T0, B_ON, st, water=30.0, heater_on=True, holiday=False) == (None, C.B_ALREADY_ON)


def test_boost_pause_and_holiday() -> None:
    st = C.BoostState(last_stop=T0)
    assert C.decide_boost(T0 + timedelta(minutes=5), B_ON, st, water=30.0, heater_on=False, holiday=False) == (None, C.B_PAUSED)
    st = C.BoostState(active=True, since=T0)
    assert C.decide_boost(T0 + timedelta(minutes=1), B_ON, st, water=30.0, heater_on=True, holiday=True) == ("off", C.B_BLOCKED)


# ---------------- in Home Assistant ----------------
def set_raw(device, **values) -> None:
    from custom_components.proxon_control import registers as R

    for key, raw in values.items():
        g = R.BY_KEY[key]
        device.raw[(g.set_point, *g.read)] = raw


async def test_entities(hass: HomeAssistant, device) -> None:
    await setup(hass)
    assert hass.states.get(eid(hass, "switch", "Nachtkuehlung")).state == "off"
    assert hass.states.get(eid(hass, "switch", "WarmwasserBoost")).state == "off"
    assert float(hass.states.get(eid(hass, "number", "KuehlWunsch")).state) == 22.0
    assert float(hass.states.get(eid(hass, "number", "KuehlStufe")).state) == 3
    assert float(hass.states.get(eid(hass, "number", "BoostGrenze")).state) == 40
    assert hass.states.get(eid(hass, "sensor", "NachtkuehlungStatus")).state == "off"


async def test_night_cooling_in_home_assistant(hass: HomeAssistant, device) -> None:
    set_raw(device, Betriebsart=1, T7Abluft=2500, T3Frischluft=1700)  # summer, inside 25 °C, outside 17 °C
    entry = await setup(hass)
    comfort = entry.runtime_data.comfort
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "Nachtkuehlung"))
    now = dt_util.now()
    await comfort.async_evaluate(now)
    assert hass.states.get(eid(hass, "sensor", "NachtkuehlungStatus")).state == "waiting"
    await comfort.async_evaluate(now + timedelta(minutes=15))
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 0, "address": 54, "value": 3}
    status = hass.states.get(eid(hass, "sensor", "NachtkuehlungStatus"))
    assert status.state == "cooling" and status.attributes["previous_level"] == 2
    await call(hass, "switch", "turn_off", entity_id=eid(hass, "switch", "Nachtkuehlung"))
    assert device.writes[-1] == {"obj": 0, "address": 54, "value": 2}  # level from before


async def test_hot_water_boost_in_home_assistant(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)  # hot water 36 °C, immersion heater off
    comfort = entry.runtime_data.comfort
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "BoostGrenze"), value=42)
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "WarmwasserBoost"))
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 1, "address": 1, "value": 1}  # immersion heater on
    assert hass.states.get(eid(hass, "sensor", "BoostStatus")).state == "heating"
    # warm enough again, after the minimum run
    set_raw(device, WarmwasserIstTemperatur=1425)  # 42.5 °C
    await entry.runtime_data.async_refresh()
    await comfort.async_evaluate(dt_util.now() + timedelta(minutes=11))
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 1, "address": 1, "value": 0}
    assert hass.states.get(eid(hass, "sensor", "BoostStatus")).state == "idle"


async def test_boost_is_off_during_holiday_mode(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    entry.runtime_data.holiday.restore_delay = 0
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "Urlaubsmodus"))
    device.writes.clear()
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "WarmwasserBoost"))
    await hass.async_block_till_done()
    assert device.writes == []
    assert hass.states.get(eid(hass, "sensor", "BoostStatus")).state == "blocked"


async def test_settings_survive_a_restart(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "Nachtkuehlung"))
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "KuehlWunsch"), value=21.5)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "switch", "Nachtkuehlung")).state == "on"
    assert float(hass.states.get(eid(hass, "number", "KuehlWunsch")).state) == 21.5
