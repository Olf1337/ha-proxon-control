"""Setup dialog, entities and controls of the Proxon Control integration inside Home Assistant."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant import config_entries
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from custom_components.proxon_control.api import AuthError
from custom_components.proxon_control.const import DOMAIN

DATA = {"connection": "direct", "device_id": "abc123", "password": "secret"}


async def setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="abc123", title="Proxon abc123")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def eid(hass: HomeAssistant, platform: str, key: str) -> str:
    ent = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"abc123_{key}")
    assert ent, f"no {platform} for {key}"
    return ent


async def test_login_dialog(hass: HomeAssistant, device) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "direct"})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "direct"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"device_id": " abc123 ", "password": "secret"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == DATA


async def test_login_wrong_password(hass: HomeAssistant, device) -> None:
    with patch("custom_components.proxon_control.api.DirectApi.test", side_effect=AuthError("bad")):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "direct"})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"device_id": "abc123", "password": "x"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_unsupported_system_points_to_addon(hass: HomeAssistant) -> None:
    with patch("custom_components.proxon_control.config_flow.library_supported", return_value=False):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "direct"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "unsupported_system"


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
    assert float(st("number", "NBE4Ziel").state) == 19.0  # master 20 + offset -1
    assert float(st("number", "SollWassertemperatur").state) == 34.0
    assert st("switch", "NBE4PTC").state == "on"
    assert st("switch", "Intensivlueftung").state == "off"
    assert st("binary_sensor", "FilterRestStunden_warning").state == "on"  # 120 h left
    assert st("binary_sensor", "DrehzahlKompressor_running").state == "on"
    # rooms the unit doesn't report are left out
    assert er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "abc123_NBE2Temperatur") is None
    # entity names come from the translations
    assert "Wohnzimmer" in (st("sensor", "NBE0Temperatur").attributes.get("friendly_name") or "")


async def test_controls_write_to_the_unit(hass: HomeAssistant, device) -> None:
    await setup(hass)
    await hass.services.async_call("select", "select_option", {ATTR_ENTITY_ID: eid(hass, "select", "Betriebsart"), "option": "winter"}, blocking=True)
    assert device.writes[-1] == {"obj": 0, "address": 42, "value": 2}
    # now not in ECO Comfort: level can be set
    await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: eid(hass, "number", "Luefterstufe"), "value": 3}, blocking=True)
    assert device.writes[-1] == {"obj": 0, "address": 54, "value": 3}
    await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: eid(hass, "number", "NBE4Ziel"), "value": 22}, blocking=True)
    assert device.writes[-1] == {"obj": 0, "address": 442, "value": 2}  # offset +2 to the living room
    await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: eid(hass, "number", "SollWassertemperatur"), "value": 45}, blocking=True)
    assert device.writes[-1] == {"obj": 1, "address": 0, "value": 450}
    await hass.services.async_call("switch", "turn_on", {ATTR_ENTITY_ID: eid(hass, "switch", "Intensivlueftung")}, blocking=True)
    assert device.writes[-1] == {"obj": 0, "address": 380, "value": 1}
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "switch", "Intensivlueftung")).state == "on"


async def test_rooms_and_names_come_from_the_unit(hass: HomeAssistant, device) -> None:
    device.set_name(4, "Dusche")
    await setup(hass)
    reg = er.async_get(hass)
    # only the rooms the unit reports as connected (living room, bedroom, bathroom); no kids room / kitchen
    for n, present in {0: True, 1: True, 2: False, 3: False, 4: True}.items():
        assert (reg.async_get_entity_id("sensor", DOMAIN, f"abc123_NBE{n}Temperatur") is not None) is present, n
    assert "Dusche" in hass.states.get(eid(hass, "sensor", "NBE4Temperatur")).attributes["friendly_name"]
    assert "Schlafzimmer" in hass.states.get(eid(hass, "sensor", "NBE1Temperatur")).attributes["friendly_name"]


async def test_room_target_is_own_base_plus_offset(hass: HomeAssistant, device) -> None:
    """Like the original's room screen: base value of the room itself + its offset (not the living room's value)."""
    device.raw[(True, 1, 23)] = 18  # NBE1MittelTemperatur
    await setup(hass)
    assert float(hass.states.get(eid(hass, "number", "NBE1Ziel")).state) == 20.0  # 18 + offset 2, living room is 20
    await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: eid(hass, "number", "NBE1Ziel"), "value": 19}, blocking=True)
    assert device.writes[-1] == {"obj": 0, "address": 436, "value": 1}  # offset 1 relative to its own 18
    with pytest.raises(ServiceValidationError):  # limit is +-3 around the room's own value (15..21)
        await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: eid(hass, "number", "NBE1Ziel"), "value": 22}, blocking=True)


async def test_living_room_target_in_half_degrees(hass: HomeAssistant, device) -> None:
    await setup(hass)
    entity = eid(hass, "number", "NBE0MittelTemperatur")
    assert hass.states.get(entity).attributes["step"] == 0.5
    await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: entity, "value": 20.5}, blocking=True)
    assert device.writes[-1] == {"obj": 0, "address": 150, "value": 2050}
    await hass.async_block_till_done()
    assert float(hass.states.get(entity).state) == 20.5


def test_room_list_rule_and_names() -> None:
    from custom_components.proxon_control import registers as R

    assert R.decode_text([ord("K") * 256 + ord("ü"), ord("c") * 256 + ord("h"), ord("e") * 256, 0]) == "Küche"
    assert R.decode_text([-1 & 0xFFFF]) == "ÿÿ"  # signed words are treated as 16-bit patterns
    assert R.room_connected({}, 0)
    assert R.room_connected({"NBE3Verbunden": 1.0}, 3) and not R.room_connected({"NBE3Verbunden": 0.0, "NBE3name": "Küche"}, 3)
    # without the unit's bit field: connected only when the unit holds a name for the room
    assert R.room_connected({"NBE3name": "Küche"}, 3) and not R.room_connected({"NBE3name": ""}, 3) and not R.room_connected({}, 3)
    assert R.room_target({"NBE2MittelTemperatur": 19.0, "NBE2OffsetTemperatur": 1.0, "NBE0MittelTemperatur": 22.0}, 2) == 20.0
    assert R.room_write({"NBE2MittelTemperatur": 19.0}, 2, 21.4) == ("NBE2OffsetTemperatur", 2.0)


async def test_no_co2_sensor_means_no_co2_entities(hass: HomeAssistant, device) -> None:
    # the original treats a CO2 reading of 0 ppm as "no CO2 sensor" and leaves out the CO2 limit
    device.raw[(False, 0, 21)] = 0
    await setup(hass)
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("sensor", DOMAIN, "abc123_CurrentCO2") is None
    assert reg.async_get_entity_id("number", DOMAIN, "abc123_GrenzwertCO2") is None
    assert reg.async_get_entity_id("number", DOMAIN, "abc123_GrenzwertFeuchte") is not None


async def test_writes_are_answered_without_data(hass: HomeAssistant, device) -> None:
    """The unit answers a write with a status only; that must not count as an error."""
    await setup(hass)
    await hass.services.async_call("switch", "turn_on", {ATTR_ENTITY_ID: eid(hass, "switch", "E-Heizstab")}, blocking=True)
    await hass.services.async_call("switch", "turn_on", {ATTR_ENTITY_ID: eid(hass, "switch", "NBE0PTC")}, blocking=True)
    await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: eid(hass, "number", "NBE0MittelTemperatur"), "value": 22}, blocking=True)
    assert [w["address"] for w in device.writes] == [1, 384, 150]
    assert device.writes[-1]["value"] == 2200


async def test_rules_from_the_original(hass: HomeAssistant, device) -> None:
    await setup(hass)
    # ECO Comfort: the unit sets the level itself
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: eid(hass, "number", "Luefterstufe"), "value": 3}, blocking=True)
    # other rooms: living room target ± 3 °C
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call("number", "set_value", {ATTR_ENTITY_ID: eid(hass, "number", "NBE1Ziel"), "value": 25}, blocking=True)
    assert device.writes == []
