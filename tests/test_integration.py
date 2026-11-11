"""Setup dialog, entities and controls of the Proxon Control integration inside Home Assistant."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.proxon_control.api import AuthError
from custom_components.proxon_control.const import DOMAIN

DATA = {"connection": "direct", "device_id": "abc123", "password": "secret"}


def make_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="abc123", title="Proxon abc123")


async def setup(hass: HomeAssistant, entry: MockConfigEntry | None = None) -> MockConfigEntry:
    entry = entry or make_entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def eid(hass: HomeAssistant, platform: str, key: str) -> str:
    ent = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"abc123_{key}")
    assert ent, f"no {platform} for {key}"
    return ent


def no_entity(hass: HomeAssistant, platform: str, key: str) -> bool:
    return er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"abc123_{key}") is None


async def call(hass: HomeAssistant, domain: str, service: str, **data) -> None:
    await hass.services.async_call(domain, service, data, blocking=True)


# ---------------- setup dialog ----------------
async def test_login_dialog(hass: HomeAssistant, device) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "direct"})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "direct"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"device_id": " abc123 ", "password": "secret"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {**DATA, "mode": "auto"}  # home network first, Proxon server as fallback


async def test_login_wrong_password(hass: HomeAssistant, device) -> None:
    with patch("custom_components.proxon_control.api.DirectApi.test", side_effect=AuthError("bad")):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "direct"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"device_id": "abc123", "password": "x"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_raspberry_pi_logs_in_over_the_home_network(hass: HomeAssistant, local_device) -> None:
    """Without Nabto's library (e.g. Raspberry Pi) the same login works, over the home network only."""
    with patch("custom_components.proxon_control.config_flow.library_supported", return_value=False):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "direct"})
        assert result["type"] is FlowResultType.FORM and result["step_id"] == "local"
        assert "mode" not in result["data_schema"].schema  # nothing to choose
        with patch("custom_components.proxon_control.api.DirectApi.test", side_effect=AssertionError("no cloud here")):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {"device_id": "abc123", "password": "secret", "local_host": " 192.168.1.50 "}
            )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {**DATA, "mode": "local", "local_host": "192.168.1.50"}


async def test_unit_not_found_in_the_home_network(hass: HomeAssistant, device) -> None:
    with patch("custom_components.proxon_control.config_flow.library_supported", return_value=False):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "direct"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"device_id": "abc123", "password": "secret"})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "cannot_connect_local"}


async def test_bridge_dialog(hass: HomeAssistant, device) -> None:
    with patch("custom_components.proxon_control.api.BridgeApi.test", return_value={}):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "bridge"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "homeassistant.local", "port": 8765})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {"connection": "bridge", "host": "homeassistant.local", "port": 8765}


async def test_reauth_updates_the_password(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "new-secret"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reauth_successful"
    assert entry.data["password"] == "new-secret"


async def test_wrong_login_starts_reauth(hass: HomeAssistant, device) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    with patch("custom_components.proxon_control.api.DirectApi.read", side_effect=AuthError("bad")):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert any(f["context"]["source"] == "reauth" for f in hass.config_entries.flow.async_progress())


async def test_integration_can_be_switched_off(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


# ---------------- adjustable query interval ----------------
async def test_query_interval_is_adjustable(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    assert entry.runtime_data.update_interval == timedelta(seconds=10)  # default
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 30})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {"scan_interval": 30}
    assert entry.runtime_data.update_interval == timedelta(seconds=30)  # the integration was reloaded with the new interval


async def test_connection_is_chosen_in_the_options(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert {"mode", "local_host"} <= {str(k) for k in result["data_schema"].schema}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 10, "mode": "cloud", "local_host": ""}
    )
    await hass.async_block_till_done()
    assert entry.options == {"scan_interval": 10, "mode": "cloud"}
    api = entry.runtime_data.api
    assert api.mode == "cloud" and api.local is None


async def test_query_interval_limits(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    for bad in (2, 4000):
        with pytest.raises(InvalidData):
            await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": bad})


async def test_stored_interval_is_kept_within_limits(hass: HomeAssistant, device) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"scan_interval": 1})
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.runtime_data.update_interval == timedelta(seconds=5)


# ---------------- what the unit shows ----------------
async def test_entities_show_the_unit(hass: HomeAssistant, device) -> None:
    await setup(hass)
    st = lambda p, k: hass.states.get(eid(hass, p, k))  # noqa: E731
    assert st("select", "Betriebsart").state == "eco_comfort"
    assert float(st("sensor", "NBE0Temperatur").state) == 22.5
    assert float(st("sensor", "T3Frischluft").state) == 17.5
    assert float(st("sensor", "T4Fortluft").state) == -0.09
    assert float(st("sensor", "WarmwasserIstTemperatur").state) == 36.0
    assert st("sensor", "Kuehlbetrieb4Wegeventil").state == "cooling"
    assert float(st("number", "Luefterstufe").state) == 2
    assert float(st("number", "SollWassertemperatur").state) == 34.0
    assert st("switch", "Intensivlueftung").state == "off"
    assert st("binary_sensor", "FilterRestStunden_warning").state == "on"  # 120 h left
    assert st("binary_sensor", "DrehzahlKompressor_running").state == "on"
    # rooms the unit doesn't report are left out; the room names come from the unit
    assert no_entity(hass, "sensor", "NBE2Temperatur") and no_entity(hass, "climate", "NBE2Thermostat")
    assert "Wohnzimmer" in st("sensor", "NBE0Temperatur").attributes["friendly_name"]


async def test_rooms_and_names_come_from_the_unit(hass: HomeAssistant, device) -> None:
    device.set_name(4, "Dusche")
    await setup(hass)
    for n, present in {0: True, 1: True, 2: False, 3: False, 4: True}.items():
        assert (not no_entity(hass, "sensor", f"NBE{n}Temperatur")) is present, n
        assert (not no_entity(hass, "climate", f"NBE{n}Thermostat")) is present, n
    assert "Dusche" in hass.states.get(eid(hass, "sensor", "NBE4Temperatur")).attributes["friendly_name"]
    assert "Dusche" in hass.states.get(eid(hass, "climate", "NBE4Thermostat")).attributes["friendly_name"]
    assert "Schlafzimmer" in hass.states.get(eid(hass, "climate", "NBE1Thermostat")).attributes["friendly_name"]


async def test_no_co2_sensor_means_no_co2_entities(hass: HomeAssistant, device) -> None:
    # the original treats a CO2 reading of 0 ppm as "no CO2 sensor" and leaves out the CO2 limit
    device.raw[(False, 0, 21)] = 0
    await setup(hass)
    assert no_entity(hass, "sensor", "CurrentCO2") and no_entity(hass, "number", "GrenzwertCO2")
    assert not no_entity(hass, "number", "GrenzwertFeuchte")


# ---------------- room thermostats ----------------
async def test_rooms_are_thermostats(hass: HomeAssistant, device) -> None:
    await setup(hass)
    living = hass.states.get(eid(hass, "climate", "NBE0Thermostat"))
    assert living.state == "auto"  # heating element of the living room is off: the unit regulates the room itself
    assert living.attributes["current_temperature"] == 22.5
    assert living.attributes["temperature"] == 20.0
    assert living.attributes["target_temp_step"] == 0.5
    assert (living.attributes["min_temp"], living.attributes["max_temp"]) == (10.0, 30.0)
    assert living.attributes["hvac_modes"] == ["auto", "heat"]
    assert living.attributes["hvac_action"] == "cooling"  # compressor runs, 4-way valve on cooling
    bedroom = hass.states.get(eid(hass, "climate", "NBE1Thermostat"))
    assert bedroom.state == "heat"  # heating element released
    assert bedroom.attributes["temperature"] == 22.0  # own base value 20 + offset 2
    assert bedroom.attributes["target_temp_step"] == 1.0
    assert (bedroom.attributes["min_temp"], bedroom.attributes["max_temp"]) == (17.0, 23.0)  # own base value +-3
    bath = hass.states.get(eid(hass, "climate", "NBE4Thermostat"))
    assert bath.state == "heat"
    assert bath.attributes["temperature"] == 19.0


async def test_thermostat_follows_the_rooms_own_base_value(hass: HomeAssistant, device) -> None:
    """Like the original's room screen: base value of the room itself + its offset (not the living room's value)."""
    device.raw[(True, 1, 23)] = 18  # NBE1MittelTemperatur
    await setup(hass)
    bedroom = eid(hass, "climate", "NBE1Thermostat")
    state = hass.states.get(bedroom)
    assert state.attributes["temperature"] == 20.0  # 18 + offset 2
    assert (state.attributes["min_temp"], state.attributes["max_temp"]) == (15.0, 21.0)
    await call(hass, "climate", "set_temperature", entity_id=bedroom, temperature=19)
    assert device.writes[-1] == {"obj": 0, "address": 436, "value": 1}  # offset 1 relative to its own 18
    with pytest.raises(ServiceValidationError):  # outside the +-3 around the room's own value
        await call(hass, "climate", "set_temperature", entity_id=bedroom, temperature=22)


async def test_living_room_thermostat_in_half_degrees(hass: HomeAssistant, device) -> None:
    await setup(hass)
    living = eid(hass, "climate", "NBE0Thermostat")
    await call(hass, "climate", "set_temperature", entity_id=living, temperature=20.5)
    assert device.writes[-1] == {"obj": 0, "address": 150, "value": 2050}
    await hass.async_block_till_done()
    assert hass.states.get(living).attributes["temperature"] == 20.5


async def test_thermostat_heating_element_on_and_off(hass: HomeAssistant, device) -> None:
    await setup(hass)
    living = eid(hass, "climate", "NBE0Thermostat")
    await call(hass, "climate", "set_hvac_mode", entity_id=living, hvac_mode="heat")
    assert device.writes[-1] == {"obj": 0, "address": 384, "value": 1}
    assert hass.states.get(living).state == "heat"
    bath = eid(hass, "climate", "NBE4Thermostat")
    await call(hass, "climate", "set_hvac_mode", entity_id=bath, hvac_mode="auto")
    assert device.writes[-1] == {"obj": 0, "address": 522, "value": 0}
    assert hass.states.get(bath).state == "auto"
    await call(hass, "climate", "set_hvac_mode", entity_id=bath, hvac_mode="heat")
    assert hass.states.get(bath).state == "heat"


async def test_old_room_entities_are_removed(hass: HomeAssistant, device) -> None:
    """Version 0.1 had room target numbers and room heating element switches; the thermostats replace them."""
    entry = make_entry()
    entry.add_to_hass(hass)
    reg = er.async_get(hass)
    old = [
        reg.async_get_or_create("number", DOMAIN, "abc123_NBE1Ziel", config_entry=entry),
        reg.async_get_or_create("number", DOMAIN, "abc123_NBE0MittelTemperatur", config_entry=entry),
        reg.async_get_or_create("switch", DOMAIN, "abc123_NBE4PTC", config_entry=entry),
    ]
    keep = reg.async_get_or_create("number", DOMAIN, "abc123_Luefterstufe", config_entry=entry)
    await setup(hass, entry)
    assert all(reg.async_get(e.entity_id) is None for e in old)
    assert reg.async_get(keep.entity_id) is not None


# ---------------- other controls ----------------
async def test_controls_write_to_the_unit(hass: HomeAssistant, device) -> None:
    await setup(hass)
    await call(hass, "select", "select_option", entity_id=eid(hass, "select", "Betriebsart"), option="winter")
    assert device.writes[-1] == {"obj": 0, "address": 42, "value": 2}
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "Luefterstufe"), value=3)  # not in ECO Comfort any more
    assert device.writes[-1] == {"obj": 0, "address": 54, "value": 3}
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "SollWassertemperatur"), value=45)
    assert device.writes[-1] == {"obj": 1, "address": 0, "value": 450}
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "Intensivlueftung"))
    assert device.writes[-1] == {"obj": 0, "address": 380, "value": 1}
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "switch", "Intensivlueftung")).state == "on"


async def test_rules_from_the_original(hass: HomeAssistant, device) -> None:
    await setup(hass)
    # ECO Comfort: the unit sets the level itself
    with pytest.raises(ServiceValidationError):
        await call(hass, "number", "set_value", entity_id=eid(hass, "number", "Luefterstufe"), value=3)
    assert device.writes == []


async def test_writes_are_answered_without_data(hass: HomeAssistant, device) -> None:
    """The unit answers a write with a status only; that must not count as an error."""
    await setup(hass)
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "E-Heizstab"))
    await call(hass, "climate", "set_temperature", entity_id=eid(hass, "climate", "NBE0Thermostat"), temperature=22)
    assert [w["address"] for w in device.writes] == [1, 150]
    assert device.writes[-1]["value"] == 2200


# ---------------- writing with read-back ----------------
async def test_write_is_confirmed_by_reading_back(hass: HomeAssistant, device) -> None:
    await setup(hass)
    entity = eid(hass, "number", "GrenzwertFeuchte")
    await call(hass, "number", "set_value", entity_id=entity, value=45)
    assert float(hass.states.get(entity).state) == 45.0
    assert device.raw[(True, 0, 118)] == 45  # what the unit holds


async def test_a_slow_unit_gets_a_moment(hass: HomeAssistant, device) -> None:
    """The value shows up only on the second read: the read-back tries again before giving up."""
    await setup(hass)
    device.apply_delay = 1
    entity = eid(hass, "number", "GrenzwertFeuchte")
    await call(hass, "number", "set_value", entity_id=entity, value=55)
    assert float(hass.states.get(entity).state) == 55.0


async def test_a_value_the_unit_does_not_take_is_reported(hass: HomeAssistant, device) -> None:
    await setup(hass)
    living = eid(hass, "climate", "NBE0Thermostat")
    device.ignore_writes = True
    with pytest.raises(HomeAssistantError, match="did not take over"):
        await call(hass, "climate", "set_temperature", entity_id=living, temperature=22)
    await hass.async_block_till_done()
    assert hass.states.get(living).attributes["temperature"] == 20.0  # shows what the unit really holds, not what was asked
    device.ignore_writes = False
    await call(hass, "climate", "set_temperature", entity_id=living, temperature=22)
    assert hass.states.get(living).attributes["temperature"] == 22.0
