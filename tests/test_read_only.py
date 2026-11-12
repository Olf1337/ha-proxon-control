"""Read-only mode: every value is read as usual, nothing is ever written to the unit."""
from __future__ import annotations

from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_control.const import DOMAIN

from .test_comfort import set_raw
from .test_integration import DATA, call, eid, setup


def read_only_entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=DATA, options={"read_only": True}, unique_id="abc123", title="Proxon abc123")


async def test_option_in_the_configure_dialog(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    assert entry.runtime_data.read_only is False  # off by default
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "read_only" in {str(k) for k in result["data_schema"].schema}
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 10, "read_only": True})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {"scan_interval": 10, "read_only": True}
    assert entry.runtime_data.read_only is True
    # switched off again: not stored at all (like the other options that are off)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 10, "read_only": False})
    await hass.async_block_till_done()
    assert entry.options == {"scan_interval": 10}
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "GrenzwertFeuchte"), value=50)
    assert device.writes  # writing works again


async def test_values_are_read_but_nothing_is_written(hass: HomeAssistant, device) -> None:
    await setup(hass, read_only_entry())
    assert float(hass.states.get(eid(hass, "number", "Luefterstufe")).state) == 2  # values are still read
    attempts = [
        ("number", "set_value", eid(hass, "number", "GrenzwertFeuchte"), {"value": 50}),
        ("select", "select_option", eid(hass, "select", "Betriebsart"), {"option": "stove"}),
        ("switch", "turn_off", eid(hass, "switch", "GlobalKuehlungFreigabe"), {}),
    ]
    for domain, service, entity_id, data in attempts:
        with pytest.raises(HomeAssistantError) as err:
            await call(hass, domain, service, entity_id=entity_id, **data)
        assert err.value.translation_key == "write_blocked_read_only", entity_id
    assert device.writes == []


async def test_holiday_mode_is_refused_before_anything_is_saved(hass: HomeAssistant, device) -> None:
    entry = await setup(hass, read_only_entry())
    with pytest.raises(HomeAssistantError) as err:
        await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "Urlaubsmodus"))
    assert err.value.translation_key == "holiday_read_only"
    assert entry.runtime_data.holiday.active is False
    assert device.writes == []


async def test_managers_do_not_write(hass: HomeAssistant, device) -> None:
    set_raw(device, Betriebsart=1, T7Abluft=2500, T3Frischluft=1700)  # summer, inside 25 °C, outside 17 °C: night cooling would start
    entry = await setup(hass, read_only_entry())
    comfort = entry.runtime_data.comfort
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "Nachtkuehlung"))  # a setting of the integration, not of the unit
    now = dt_util.now()
    await comfort.async_evaluate(now)
    await comfort.async_evaluate(now + timedelta(minutes=15))
    await entry.runtime_data.energy.async_evaluate(now)
    await hass.async_block_till_done()
    assert device.writes == []
