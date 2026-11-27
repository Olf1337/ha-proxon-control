"""1.2: cooling with solar surplus (the unit's cooling release), and the raw set points in the diagnostics (to find the key lock)."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.proxon_control import comfort as C
from custom_components.proxon_control import registers as R
from custom_components.proxon_control.diagnostics import async_get_config_entry_diagnostics

from .test_comfort import set_raw
from .test_energy import setup_with_sensors
from .test_integration import call, eid, setup

T0 = datetime(2026, 7, 10, 12, 0)


def go(st, s, minutes, **kw):
    base = {"mode": 3, "inside": 26.0, "surplus": 2500.0, "released": False, "holiday": False}
    return C.decide_pv_cooling(T0 + timedelta(minutes=minutes), s, st, **{**base, **kw})


def test_rules() -> None:
    s, st = C.PVCoolSettings(on=True, surplus_w=1500, wish=24), C.PVCoolState()
    assert go(st, s, 0) == ("on", C.PV_COOLING) and st.active
    assert go(st, s, 1, released=True) == (None, C.PV_COOLING)
    # a cloud: too little surplus, but not for 10 minutes yet / not 20 minutes run yet
    assert go(st, s, 5, released=True, surplus=200) == (None, C.PV_COOLING)
    assert go(st, s, 16, released=True, surplus=200) == (None, C.PV_COOLING)  # 11 min low, but only 16 min run
    assert go(st, s, 21, released=True, surplus=200) == ("off", C.PV_IDLE) and not st.active
    assert go(st, s, 25, released=False) == (None, C.PV_PAUSED)  # 10 minutes pause
    assert go(st, s, 32, released=False) == ("on", C.PV_COOLING)
    # cool enough: off after the minimum run
    assert go(st, s, 60, released=True, inside=23.4) == ("off", C.PV_IDLE)


def test_respects_the_hand() -> None:
    s, st = C.PVCoolSettings(on=True), C.PVCoolState()
    assert go(st, s, 0, released=True) == (None, C.PV_ALREADY_ON)  # released by hand: not ours to switch off
    assert go(st, s, 1, released=True, surplus=0) == (None, C.PV_ALREADY_ON)
    assert go(st, s, 2) == ("on", C.PV_COOLING)
    assert go(st, s, 3, released=False) == (None, C.PV_IDLE) and not st.active  # switched off by hand: stays off
    s.on = False
    st2 = C.PVCoolState(active=True, since=T0)
    assert go(st2, s, 30, released=True) == ("off", C.PV_OFF)  # switching the automation off ends its release


def test_only_in_eco_comfort_and_summer() -> None:
    s = C.PVCoolSettings(on=True)
    assert go(C.PVCoolState(), s, 0, mode=2) == (None, C.PV_NOT_MODE)
    assert go(C.PVCoolState(), s, 0, mode=1)[0] == "on"
    assert go(C.PVCoolState(), s, 0, surplus=None) == (None, C.PV_NO_SENSOR)
    assert go(C.PVCoolState(), s, 0, holiday=True) == (None, C.PV_BLOCKED)


async def test_cooling_with_surplus_switches_the_release(hass: HomeAssistant, device) -> None:
    await setup_with_sensors(hass)  # feed-in counted negative: -2500 W is 2500 W surplus
    comfort = hass.config_entries.async_entries("proxon_control")[0].runtime_data.comfort
    switch = eid(hass, "switch", "PVKuehlung")
    assert hass.states.get(switch).state == "off" and hass.states.get(eid(hass, "sensor", "PVKuehlStatus")).state == "off"
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "PVKuehlWunsch"), value=21)  # inside is 22.2 °C
    set_raw(device, Betriebsart=1)
    hass.states.async_set("sensor.netz", "-2500", {"unit_of_measurement": "W"})
    await call(hass, "switch", "turn_on", entity_id=switch)
    await comfort.async_evaluate(dt_util.now())
    assert device.writes[-1]["value"] == 1  # the cooling release on
    assert hass.states.get(eid(hass, "sensor", "PVKuehlStatus")).state == "cooling"
    await call(hass, "switch", "turn_off", entity_id=switch)
    assert device.writes[-1]["value"] == 0  # the automation off: its release goes off again


async def test_manual_cooling_switch_exists(hass: HomeAssistant, device) -> None:
    await setup(hass)
    cooling = eid(hass, "switch", "GlobalKuehlungFreigabe")
    await call(hass, "switch", "turn_on", entity_id=cooling)
    assert device.writes[-1]["value"] == 1


async def test_diagnostics_hold_the_raw_set_points(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    raw = diag["raw_setpoints"]
    assert raw["errors"] == []
    assert len(raw["values"]) == sum(n for _, n in R.SCAN_RANGES)
    assert raw["values"]["0:16"] == 3  # the operating mode, raw
    assert not any(k.startswith("6:") for k in raw["values"])  # room names are left out
    data = diag["raw_datapoints"]
    assert data["errors"] == [] and len(data["values"]) == sum(n for _, n in R.SCAN_DATA_RANGES)
    g = R.BY_KEY["T7Abluft"]
    assert data["values"][f"{g.read[0]}:{g.read[1]}"] == 2220  # extract air 22.2 °C, raw


# ---------------- the room panels' key lock (found with the raw values above), read only ----------------
async def test_key_lock_is_shown_per_room(hass: HomeAssistant, device) -> None:
    from homeassistant.helpers import entity_registry as er

    from .test_integration import make_entry
    entry = make_entry()
    entry.add_to_hass(hass)
    # the key lock switch of 1.2.0b3 (the unit refuses writing it): removed at the start
    er.async_get(hass).async_get_or_create("switch", "proxon_control", "abc123_NBE1Tastensperre", config_entry=entry)
    room = 1
    g = R.BY_KEY[f"NBE{room}Tastensperre"]
    assert g.read == (1, 62 + room) and g.write is None
    device.raw[(True, *g.read)] = 1
    await setup(hass, entry)
    assert er.async_get(hass).async_get_entity_id("switch", "proxon_control", "abc123_NBE1Tastensperre") is None
    assert hass.states.get(eid(hass, "binary_sensor", f"NBE{room}Tastensperre")).state == "on"


# ---------------- no electric heating (instead of the unit's global heating release) ----------------
def test_heat_lock_rules() -> None:
    s, st = C.HeatLockSettings(on=True), C.HeatLockState()
    assert C.decide_heat_lock(s, st, {0: True, 1: False, 2: True}) == ({0: 0, 2: 0}, C.H_LOCKED) and st.saved == [0, 2]
    assert C.decide_heat_lock(s, st, {0: False, 1: True, 2: False}) == ({1: 0}, C.H_LOCKED)  # switched on at a panel
    assert st.saved == [0, 2]  # what to restore stays what was on at the start
    s.on = False
    assert C.decide_heat_lock(s, st, {0: False, 1: False, 2: False}) == ({0: 1, 2: 1}, C.H_OFF) and not st.active
    assert C.decide_heat_lock(s, st, {0: False}) == ({}, C.H_OFF)


async def test_heat_lock_switches_releases(hass: HomeAssistant, device) -> None:
    await setup(hass)
    switch = eid(hass, "switch", "HeizenSperren")
    rooms_on = [k for k, v in hass.config_entries.async_entries("proxon_control")[0].runtime_data.data.items() if k.endswith("PTC") and v]
    assert rooms_on
    await call(hass, "switch", "turn_on", entity_id=switch)
    await hass.async_block_till_done()
    assert hass.states.get(switch).attributes["status"] == "locked"
    offs = [w for w in device.writes if w["value"] == 0]
    assert len(offs) >= len(rooms_on)
    await call(hass, "switch", "turn_off", entity_id=switch)
    await hass.async_block_till_done()
    assert [w["value"] for w in device.writes[-len(rooms_on):]] == [1] * len(rooms_on)  # restored


async def test_cooling_with_surplus_needs_the_sensor(hass: HomeAssistant, device) -> None:
    """Like hot water with solar surplus: without a surplus sensor it can't be switched on (a hint instead)."""
    from homeassistant.exceptions import ServiceValidationError
    import pytest
    await setup(hass)
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "PVKuehlung"))
    assert err.value.translation_key == "pv_cooling_needs_sensor"
    assert hass.states.get(eid(hass, "switch", "PVKuehlung")).state == "off"
