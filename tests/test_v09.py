"""Version 0.9: values from the ha-lan-proxon comparison, stove mode, legionella, boost duration, filter lifetime, rooms as
devices, schedule entities, write guard, clock deviation, heat recovery and the new blueprints."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
import pytest

from custom_components.proxon_control import registers as R
from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.schedule import clock_drift

from .test_integration import call, eid, setup

ROOT = Path(__file__).resolve().parents[1]


def writes(device) -> list[tuple[int, int, int]]:
    return [(w["obj"], w["address"], w["value"]) for w in device.writes]


def raw_key(key: str) -> tuple:
    g = R.BY_KEY[key]
    return (g.set_point, *g.read)


def get_device(hass: HomeAssistant, identifier: str):
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    return next(d for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id) if (DOMAIN, identifier) in d.identifiers)


def state(hass: HomeAssistant, platform: str, key: str):
    return hass.states.get(eid(hass, platform, key))


# ---------------- helpers without Home Assistant ----------------
def test_filter_lifetime_from_the_unit() -> None:
    assert R.filter_months({"FilterStandzeit": 4.0}) == 4
    assert R.filter_months({"FilterStandzeit": 0.0}) == 6 and R.filter_months({}) == 6  # not set / not reported: usual 6 months


def test_water_charge() -> None:
    full = {"WarmwasserIstTemperatur": 50.0, "WarmwasserUntenTemperatur": 50.0, "SollWassertemperatur": 50.0}
    assert R.water_charge(full) == 100.0
    assert R.water_charge({**full, "WarmwasserUntenTemperatur": 12.0}) == 50.0  # cold at the bottom: half
    assert R.water_charge({**full, "WarmwasserIstTemperatur": 10.0, "WarmwasserUntenTemperatur": 10.0}) == 0.0
    assert R.water_charge({"WarmwasserIstTemperatur": 40.0}) is None


def test_heat_recovery() -> None:
    v = {"T3Frischluft": 0.0, "T1Zuluft": 18.0, "T7Abluft": 22.0, "DrehzahlKompressor": 0.0, "Betriebsart": 2.0}
    assert R.heat_recovery(v) == 82.0
    assert R.heat_recovery({**v, "DrehzahlKompressor": 3000.0}) is None  # heat pump heats the supply air: not measurable
    assert R.heat_recovery({**v, "Bypass": 1.0}) is None
    assert R.heat_recovery({**v, "T3Frischluft": 19.0}) is None  # outdoor and extract air too close


def test_operation_from_compressor_and_valve() -> None:
    assert R.operation({"DrehzahlKompressor": 3000.0, "Kuehlbetrieb4Wegeventil": 0.0, "Betriebsart": 2.0}) == 1.0
    assert R.operation({"DrehzahlKompressor": 3000.0, "Kuehlbetrieb4Wegeventil": 1.0, "Betriebsart": 1.0}) == 2.0
    assert R.operation({"DrehzahlKompressor": 0.0, "Betriebsart": 3.0}) == 0.0
    assert R.operation({"DrehzahlKompressor": 0.0, "Betriebsart": 0.0}) is None  # unit off


async def test_probe_values_are_in_the_diagnostics(hass: HomeAssistant, device) -> None:
    from custom_components.proxon_control.diagnostics import async_get_config_entry_diagnostics

    entry = await setup(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    assert all(f"Pruefwert_DP0_{n}" in diag["values"] for n in R.PROBE_POINTS)


def test_clock_drift() -> None:
    clock = {"UhrMinute": 0, "UhrStunde": 10, "UhrTag": 9, "UhrMonat": 11, "UhrJahr": 26}
    assert clock_drift(clock, datetime(2026, 11, 9, 10, 0, 40)) == 0
    assert clock_drift(clock, datetime(2026, 11, 9, 11, 0)) == -60  # summer/winter time not switched at the unit
    assert clock_drift({}, datetime(2026, 11, 9)) is None


def test_write_guard_rules() -> None:
    assert R.allowed_during_fault("E-Heizstab", 0) and not R.allowed_during_fault("E-Heizstab", 1)
    assert R.allowed_during_fault("NBE3PTC", 0) and not R.allowed_during_fault("NBE3PTC", 1)
    assert R.allowed_during_fault("Luefterstufe", 3) and R.allowed_during_fault("NBE2OffsetTemperatur", 1)
    assert R.allowed_during_fault("Betriebsart", 0) and not R.allowed_during_fault("Betriebsart", 4)
    assert not R.allowed_during_fault("SollWassertemperatur", 50)


# ---------------- new values and controls ----------------
async def test_new_values(hass: HomeAssistant, device) -> None:
    await setup(hass)
    assert state(hass, "sensor", "WarmwasserUntenTemperatur").state == "30.0"
    assert state(hass, "sensor", "WarmwasserLadezustand").state == "95"  # middle 36 °C, bottom 30 °C, target 34 °C
    assert state(hass, "sensor", "AktuellerBetrieb").state == "cooling"  # compressor runs, 4-way valve on cooling
    assert state(hass, "sensor", "DruckVerdampfer").state == "2.85"
    assert state(hass, "sensor", "FirmwareT300").state == "35"
    assert state(hass, "sensor", "FilterStandzeit").state == "6"
    assert state(hass, "binary_sensor", "Bypass").state == "off"
    assert state(hass, "binary_sensor", "PVFreigabe").state == "on"
    assert state(hass, "binary_sensor", "BedienpanelGesperrt").state == "off"
    # raw status words exist but are switched off by default
    assert er.async_get(hass).async_get(eid(hass, "sensor", "StatusKompressor")).disabled_by is not None


async def test_filter_follows_the_units_lifetime(hass: HomeAssistant, device) -> None:
    device.raw[raw_key("FilterStandzeit")] = 4  # 4 months = 2880 h, the filter has run 4200 h
    await setup(hass)
    remaining = state(hass, "sensor", "FilterRestStunden")
    assert float(remaining.state) == 0 and remaining.attributes["filter_lifetime_months"] == 4
    assert state(hass, "binary_sensor", "FilterRestStunden_warning").state == "on"


async def test_stove_mode_legionella_and_boost_duration(hass: HomeAssistant, device) -> None:
    await setup(hass)
    mode = eid(hass, "select", "Betriebsart")
    assert "stove" in hass.states.get(mode).attributes["options"]
    await call(hass, "select", "select_option", entity_id=mode, option="stove")
    assert writes(device)[-1] == (0, 42, 4)
    assert hass.states.get(mode).state == "stove"
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "Legionellenfunktion"))
    assert writes(device)[-1] == (1, 25, 1)
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "IntensivlueftungsDauer"), value=30)
    assert writes(device)[-1] == (0, 382, 30)


async def test_heat_recovery_keeps_the_last_measurement(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    sensor = eid(hass, "sensor", "Waermerueckgewinnung")
    assert hass.states.get(sensor).state == "unknown"  # heat pump running: nothing measured yet
    coordinator = entry.runtime_data
    coordinator.async_set_updated_data({**coordinator.data, "DrehzahlKompressor": 0.0, "T3Frischluft": 0.0, "T1Zuluft": 18.0, "T7Abluft": 22.0})
    await hass.async_block_till_done()
    assert hass.states.get(sensor).state == "82"
    coordinator.async_set_updated_data({**coordinator.data, "DrehzahlKompressor": 3500.0})
    await hass.async_block_till_done()
    s = hass.states.get(sensor)
    assert s.state == "82" and s.attributes["measuring_now"] is False


async def test_heat_recovery_survives_a_restart(hass: HomeAssistant, device) -> None:
    """After a restart the last measurement is shown again, even while the heat pump runs (nothing measurable then)."""
    from homeassistant.core import State
    from pytest_homeassistant_custom_component.common import mock_restore_cache_with_extra_data

    entry = await setup(hass)
    sensor = eid(hass, "sensor", "Waermerueckgewinnung")
    assert await hass.config_entries.async_unload(entry.entry_id)
    measured = "2026-11-01T10:00:00+00:00"
    mock_restore_cache_with_extra_data(hass, [(
        State(sensor, "79", {"measured_at": measured}),
        {"native_value": 79, "native_unit_of_measurement": "%"},
    )])
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    s = hass.states.get(sensor)
    assert s.state == "79" and s.attributes["measuring_now"] is False
    assert s.attributes["measured_at"].isoformat() == measured

# ---------------- clock ----------------
async def test_clock_deviation_notice(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    issues = ir.async_get(hass)
    coordinator = entry.runtime_data
    coordinator.async_set_updated_data({**coordinator.data, "UhrAbweichung": -60.0})
    await hass.async_block_till_done()
    issue = issues.async_get_issue(DOMAIN, f"clock_drift_{entry.entry_id}")
    assert issue and issue.translation_placeholders == {"minutes": "60", "direction": "-"}
    coordinator.async_set_updated_data({**coordinator.data, "UhrAbweichung": 1.0})
    await hass.async_block_till_done()
    assert issues.async_get_issue(DOMAIN, f"clock_drift_{entry.entry_id}") is None
    assert "UhrAbweichung" in coordinator.data  # measured with every query


# ---------------- write guard ----------------
async def test_fault_blocks_risky_writes(hass: HomeAssistant, device) -> None:
    device.raw[raw_key(R.fault_key((0, 2)))] = 1
    await setup(hass)
    with pytest.raises(HomeAssistantError) as err:
        await call(hass, "select", "select_option", entity_id=eid(hass, "select", "Betriebsart"), option="stove")
    assert err.value.translation_key == "write_blocked_fault"
    assert device.writes == []
    last = state(hass, "sensor", "LetzterSchreibfehler")
    assert last.attributes["value"] == "Betriebsart" and last.attributes["reason"] == "fault" and last.attributes["count"] == 1
    await call(hass, "switch", "turn_off", entity_id=eid(hass, "switch", "GlobalKuehlungFreigabe"))  # switching off: allowed
    assert writes(device)[-1] == (0, 134, 0)


async def test_last_write_error_when_the_unit_ignores_a_value(hass: HomeAssistant, device) -> None:
    await setup(hass)
    assert state(hass, "sensor", "LetzterSchreibfehler").state == "unknown"
    device.ignore_writes = True
    with pytest.raises(HomeAssistantError):
        await call(hass, "number", "set_value", entity_id=eid(hass, "number", "GrenzwertFeuchte"), value=50)
    last = state(hass, "sensor", "LetzterSchreibfehler")
    assert last.state != "unknown" and last.attributes["reason"] == "not_accepted"


# ---------------- rooms as devices ----------------
async def test_rooms_are_devices_in_their_areas(hass: HomeAssistant, device) -> None:
    bath = ar.async_get(hass).async_create("Bad")
    await setup(hass)
    entities = er.async_get(hass)
    unit = get_device(hass, "abc123")
    bedroom = get_device(hass, "abc123_room1")
    assert bedroom.name == "Proxon Schlafzimmer" and bedroom.via_device_id == unit.id
    assert bedroom.area_id is None  # no area of that name
    assert get_device(hass, "abc123_room4").area_id == bath.id
    thermostat = eid(hass, "climate", "NBE1Thermostat")
    assert entities.async_get(thermostat).device_id == bedroom.id
    assert hass.states.get(thermostat).attributes["friendly_name"] == "Proxon Schlafzimmer"
    temp = eid(hass, "sensor", "NBE1Temperatur")
    assert entities.async_get(temp).device_id == bedroom.id
    assert hass.states.get(temp).attributes["friendly_name"] == "Proxon Schlafzimmer Temperature"


async def test_area_chosen_by_hand_stays(hass: HomeAssistant, device) -> None:
    areas = ar.async_get(hass)
    entry = await setup(hass)
    devices = dr.async_get(hass)
    bath = get_device(hass, "abc123_room4")
    areas.async_create("Bad")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert devices.async_get(bath.id).area_id is None  # only new devices are put into areas


# ---------------- weekly schedule as entities ----------------
async def test_schedule_entities(hass: HomeAssistant, device) -> None:
    await setup(hass)
    tuesday = get_device(hass, "abc123_schedule1")
    assert tuesday.name == "Proxon schedule Tuesday"
    start = eid(hass, "time", "ZP1_0_start")
    assert hass.states.get(start).state == "06:00:00"
    assert hass.states.get(eid(hass, "time", "ZP1_0_end")).state == "08:00:00"
    level = eid(hass, "select", "ZP1_1_stufe")
    assert hass.states.get(level).state == "3" and hass.states.get(eid(hass, "select", "ZP1_2_stufe")).state == "off"
    # the unit's clock is Monday 10:00: Tuesday's first phase may be moved
    await call(hass, "time", "set_value", entity_id=start, time="05:30:00")
    k = R.schedule_index(1, 0, 0)
    assert writes(device) == [(0, 1026 + 2 * (k + 4), 0), (0, 1026 + 2 * k, 5), (0, 1026 + 2 * (k + 1), 30), (0, 1026 + 2 * (k + 4), 2)]
    assert hass.states.get(start).state == "05:30:00"
    device.writes.clear()
    await call(hass, "select", "select_option", entity_id=level, option="4")
    assert writes(device) == [(0, 1026 + 2 * R.schedule_index(1, 1, 4), 4)]


async def test_schedule_entity_follows_the_rules(hass: HomeAssistant, device) -> None:
    await setup(hass)
    # the unit's clock is Monday 10:00: Monday's evening phase can't start at 11:00 (less than 2 hours ahead)
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "time", "set_value", entity_id=eid(hass, "time", "ZP0_1_start"), time="11:00:00")
    assert err.value.translation_key == "schedule_too_soon"
    assert device.writes == []


async def test_inactive_phase_times_can_be_prepared(hass: HomeAssistant, device) -> None:
    await setup(hass)
    await call(hass, "time", "set_value", entity_id=eid(hass, "time", "ZP2_2_start"), time="12:00:00")
    assert writes(device) == [(0, 1026 + 2 * R.schedule_index(2, 2, 0), 12)]


async def test_copy_monday_buttons(hass: HomeAssistant, device) -> None:
    device.raw[raw_key(R.schedule_key(0, 0, 4))] = 3  # Monday's morning phase: level 3 instead of 2
    await setup(hass)
    await call(hass, "button", "press", entity_id=eid(hass, "button", "ZeitprogrammMoDiFr"))
    assert writes(device) == [(0, 1026 + 2 * R.schedule_index(d, 0, 4), 3) for d in (1, 2, 3, 4)]
    device.writes.clear()
    await call(hass, "button", "press", entity_id=eid(hass, "button", "ZeitprogrammMoAlle"))
    assert writes(device) == [(0, 1026 + 2 * R.schedule_index(d, 0, 4), 3) for d in (5, 6)]


# ---------------- blueprints ----------------
@pytest.fixture
def blueprints(hass: HomeAssistant, tmp_path):
    hass.config.config_dir = str(tmp_path)
    shutil.copytree(ROOT / "blueprints", tmp_path / "blueprints")


async def test_stove_blueprint(hass: HomeAssistant, device, blueprints) -> None:
    await setup(hass)
    mode = eid(hass, "select", "Betriebsart")
    hass.states.async_set("input_boolean.ofen", "off")
    assert await async_setup_component(hass, "automation", {"automation": [{"use_blueprint": {
        "path": "proxon_control/stove_mode.yaml", "input": {"stove": "input_boolean.ofen", "mode_select": mode},
    }}]})
    await hass.async_block_till_done()
    hass.states.async_set("input_boolean.ofen", "on")
    await hass.async_block_till_done()
    assert writes(device)[-1] == (0, 42, 4)


async def test_new_blueprints_load(hass: HomeAssistant, device, blueprints) -> None:
    await setup(hass)
    hass.states.async_set("zone.home", "1")
    hass.states.async_set("sensor.pm25", "5")
    level = eid(hass, "number", "Luefterstufe")
    assert await async_setup_component(hass, "automation", {"automation": [
        {"use_blueprint": {"path": "proxon_control/outdoor_air.yaml", "input": {"air_sensor": "sensor.pm25", "level": level}}},
        {"use_blueprint": {"path": "proxon_control/nobody_home.yaml", "input": {"level": level}}},
        {"use_blueprint": {"path": "proxon_control/humidity_boost.yaml", "input": {
            "humidity_sensor": "sensor.bad", "boost_switch": eid(hass, "switch", "Intensivlueftung"),
        }}},
    ]})
    await hass.async_block_till_done()
    autos = hass.states.async_entity_ids("automation")
    assert len(autos) == 3 and all(hass.states.get(a).state == "on" for a in autos)


# ---------------- power and energy (0.10) ----------------
async def test_power_and_energy(hass: HomeAssistant, device) -> None:
    from unittest.mock import patch

    from custom_components.proxon_control import sensor as sensor_module

    t = [1000.0]
    with patch.object(sensor_module.time, "monotonic", lambda: t[0]):
        entry = await setup(hass)
        assert state(hass, "sensor", "LeistungGesamt").state == "531.8"
        assert state(hass, "sensor", "LeistungKompressor").state == "470.9"
        assert state(hass, "sensor", "LeistungLueftung").state == "60.9"
        energy = eid(hass, "sensor", "EnergieGesamt")
        assert float(hass.states.get(energy).state) == 0
        coordinator = entry.runtime_data
        t[0] += 720  # 12 minutes from 531.8 W to 468.2 W: on average 500 W = 0.1 kWh
        coordinator.async_set_updated_data({**coordinator.data, "LeistungGesamt": 468.2})
        await hass.async_block_till_done()
        assert float(hass.states.get(energy).state) == 0.1
        t[0] += 2 * 3600  # a gap of two hours (Home Assistant was stopped): not counted
        coordinator.async_set_updated_data({**coordinator.data, "LeistungGesamt": 468.2})
        await hass.async_block_till_done()
        assert float(hass.states.get(energy).state) == 0.1
    s = hass.states.get(energy)
    assert s.attributes["state_class"] == "total_increasing" and s.attributes["unit_of_measurement"] == "kWh"
