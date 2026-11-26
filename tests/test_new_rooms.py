"""A room the unit reports only after the start (a room panel added later) gets its entities at the next reading, without a
restart, and its device goes into the area of the same name."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.proxon_control.const import DOMAIN

from .test_integration import setup


async def test_room_connected_later_gets_its_entities(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)  # rooms 0, 1 and 4
    reg = er.async_get(hass)

    def ids(domain: str, key: str) -> str | None:
        return reg.async_get_entity_id(domain, DOMAIN, f"abc123_{key}")

    assert ids("climate", "NBE2Thermostat") is None and ids("sensor", "NBE2Temperatur") is None
    area = ar.async_get(hass).async_create("Kinderzimmer")
    coordinator = entry.runtime_data
    room = {"NBE2Verbunden": 1.0, "NBE2name": "Kinderzimmer", "NBE2Temperatur": 21.5, "NBE2MittelTemperatur": 20.0,
            "NBE2OffsetTemperatur": 1.0, "NBE2PTC": 0.0, "NBE2Status": 1.0}
    coordinator.async_set_updated_data({**coordinator.data, **room})
    await hass.async_block_till_done()
    thermostat, temperature = ids("climate", "NBE2Thermostat"), ids("sensor", "NBE2Temperatur")
    assert thermostat and temperature
    assert hass.states.get(thermostat).attributes["temperature"] == 21.0  # base 20 + offset 1
    assert float(hass.states.get(temperature).state) == 21.5
    # the next reading puts the new room device into its area, and adds nothing twice
    coordinator.async_set_updated_data({**coordinator.data})
    await hass.async_block_till_done()
    device_id = reg.async_get(thermostat).device_id
    assert dr.async_get(hass).async_get(device_id).area_id == area.id
    assert len([e for e in er.async_entries_for_config_entry(reg, entry.entry_id) if e.unique_id.endswith("NBE2Thermostat")]) == 1
