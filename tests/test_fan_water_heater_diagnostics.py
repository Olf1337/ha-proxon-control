"""Ventilation as a fan, hot water as a water heater, and the diagnostics download."""
from __future__ import annotations

import json

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest

from custom_components.proxon_control.diagnostics import async_get_config_entry_diagnostics

from .test_integration import call, eid, no_entity, setup


# ---------------- ventilation as a fan ----------------
async def test_fan_shows_level_and_boost(hass: HomeAssistant, device) -> None:
    await setup(hass)
    fan = hass.states.get(eid(hass, "fan", "Lueftung"))
    assert fan.state == "on"
    assert fan.attributes["percentage"] == 50  # level 2 of 4
    assert fan.attributes["percentage_step"] == 25
    assert fan.attributes["preset_mode"] == "normal"
    assert fan.attributes["preset_modes"] == ["normal", "boost"]


async def test_fan_sets_the_level(hass: HomeAssistant, device) -> None:
    await setup(hass)
    fan = eid(hass, "fan", "Lueftung")
    await call(hass, "select", "select_option", entity_id=eid(hass, "select", "Betriebsart"), option="winter")
    await call(hass, "fan", "set_percentage", entity_id=fan, percentage=75)
    assert device.writes[-1] == {"obj": 0, "address": 54, "value": 3}
    assert hass.states.get(fan).attributes["percentage"] == 75
    await call(hass, "fan", "set_percentage", entity_id=fan, percentage=10)  # rounds up to the lowest level
    assert device.writes[-1] == {"obj": 0, "address": 54, "value": 1}


async def test_fan_level_is_locked_when_the_unit_chooses(hass: HomeAssistant, device) -> None:
    await setup(hass)  # ECO Comfort
    with pytest.raises(ServiceValidationError):
        await call(hass, "fan", "set_percentage", entity_id=eid(hass, "fan", "Lueftung"), percentage=75)
    assert device.writes == []


async def test_fan_cannot_be_switched_off_on_its_own(hass: HomeAssistant, device) -> None:
    await setup(hass)
    await call(hass, "select", "select_option", entity_id=eid(hass, "select", "Betriebsart"), option="winter")
    with pytest.raises(ServiceValidationError):
        await call(hass, "fan", "set_percentage", entity_id=eid(hass, "fan", "Lueftung"), percentage=0)
    assert [w["address"] for w in device.writes] == [42]  # only the operating mode


async def test_fan_boost_preset(hass: HomeAssistant, device) -> None:
    await setup(hass)
    fan = eid(hass, "fan", "Lueftung")
    await call(hass, "fan", "set_preset_mode", entity_id=fan, preset_mode="boost")
    assert device.writes[-1] == {"obj": 0, "address": 380, "value": 1}
    assert hass.states.get(fan).attributes["preset_mode"] == "boost"
    assert hass.states.get(eid(hass, "switch", "Intensivlueftung")).state == "on"
    await call(hass, "fan", "set_preset_mode", entity_id=fan, preset_mode="normal")
    assert device.writes[-1] == {"obj": 0, "address": 380, "value": 0}


async def test_fan_is_off_when_the_unit_is_off(hass: HomeAssistant, device) -> None:
    await setup(hass)
    await call(hass, "select", "select_option", entity_id=eid(hass, "select", "Betriebsart"), option="off")
    fan = hass.states.get(eid(hass, "fan", "Lueftung"))
    assert fan.state == "off" and fan.attributes["percentage"] == 0


# ---------------- hot water as a water heater ----------------
async def test_water_heater_shows_hot_water(hass: HomeAssistant, device) -> None:
    await setup(hass)
    wh = hass.states.get(eid(hass, "water_heater", "Warmwasser"))
    assert wh.state == "heat_pump"  # heat pump on, immersion heater off
    assert wh.attributes["current_temperature"] == 36.0
    assert wh.attributes["temperature"] == 34.0
    assert (wh.attributes["min_temp"], wh.attributes["max_temp"]) == (20.0, 55.0)
    assert wh.attributes["operation_list"] == ["off", "heat_pump", "high_demand", "electric"]


async def test_water_heater_target_temperature(hass: HomeAssistant, device) -> None:
    await setup(hass)
    wh = eid(hass, "water_heater", "Warmwasser")
    await call(hass, "water_heater", "set_temperature", entity_id=wh, temperature=45)
    assert device.writes[-1] == {"obj": 1, "address": 0, "value": 450}
    assert hass.states.get(wh).attributes["temperature"] == 45.0
    with pytest.raises(ServiceValidationError):
        await call(hass, "water_heater", "set_temperature", entity_id=wh, temperature=60)


async def test_water_heater_operation_modes(hass: HomeAssistant, device) -> None:
    await setup(hass)
    wh = eid(hass, "water_heater", "Warmwasser")
    await call(hass, "water_heater", "set_operation_mode", entity_id=wh, operation_mode="high_demand")
    assert device.writes == [{"obj": 1, "address": 1, "value": 1}]  # only the immersion heater was missing
    assert hass.states.get(wh).state == "high_demand"
    device.writes.clear()
    await call(hass, "water_heater", "turn_off", entity_id=wh)
    # immersion heater off first, then the heat pump
    assert device.writes == [{"obj": 1, "address": 1, "value": 0}, {"obj": 1, "address": 2, "value": 0}]
    assert hass.states.get(wh).state == "off"
    device.writes.clear()
    await call(hass, "water_heater", "turn_on", entity_id=wh)
    assert device.writes == [{"obj": 1, "address": 2, "value": 1}]
    assert hass.states.get(wh).state == "heat_pump"
    device.writes.clear()
    await call(hass, "water_heater", "set_operation_mode", entity_id=wh, operation_mode="electric")
    assert device.writes == [{"obj": 1, "address": 2, "value": 0}, {"obj": 1, "address": 1, "value": 1}]
    assert hass.states.get(wh).state == "electric"


async def test_no_water_heater_without_hot_water_heat_pump(hass: HomeAssistant, device) -> None:
    from custom_components.proxon_control import registers as R

    read_all = R.read_all
    with pytest.MonkeyPatch.context() as mp:
        # a unit without the hot-water heat pump doesn't report its operating mode
        mp.setattr(R, "read_all", lambda c, names=True: {k: v for k, v in read_all(c, names).items() if k != "T300Betriebsart"})
        await setup(hass)
    assert no_entity(hass, "water_heater", "Warmwasser")


# ---------------- diagnostics download ----------------
async def test_diagnostics_hide_login_and_room_names(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = json.dumps(diag)
    assert "secret" not in text and "abc123" not in text  # password, Device ID
    assert "Schlafzimmer" not in text  # room names
    assert diag["entry"]["data"]["password"] == "**REDACTED**"
    assert diag["entry"]["connection"] == "direct"
    assert diag["coordinator"]["update_interval_seconds"] == 10
    assert diag["coordinator"]["last_update_success"] is True
    assert diag["values"]["Luefterstufe"] == 2
    assert diag["values"]["T3Frischluft"] == 17.5
