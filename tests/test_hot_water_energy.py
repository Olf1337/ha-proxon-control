"""Hot-water consumption, estimated: the unit doesn't measure the hot-water module's power, so it is its rated power while
its compressor / heater runs (datasheet PROXON T300 by default, adjustable in the options), added up like the unit's own."""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_control.const import DOMAIN

from .test_integration import DATA, eid, setup


async def refresh(hass: HomeAssistant, entry, **values) -> None:
    entry.runtime_data.async_set_updated_data({**entry.runtime_data.data, **values})
    await hass.async_block_till_done()


async def test_power_from_the_datasheet_while_running(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    # the test unit: hot-water compressor running, heater off
    assert float(hass.states.get(eid(hass, "sensor", "LeistungWarmwasserWP")).state) == 430
    assert float(hass.states.get(eid(hass, "sensor", "LeistungHeizstab")).state) == 0
    data = entry.runtime_data.water_power({**entry.runtime_data.data, "T300RelaisKompressor": 0, "T300RelaisHeizstab": 1})
    assert data == {"LeistungWarmwasserWP": 0.0, "LeistungHeizstab": 1500.0}
    # not part of the unit's measured total
    assert float(hass.states.get(eid(hass, "sensor", "LeistungGesamt")).state) == entry.runtime_data.data["LeistungGesamt"]


async def test_rated_power_from_the_options(hass: HomeAssistant, device) -> None:
    """A BOOST heater (4.5 kW) or a measured heat pump: the values from the options count."""
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="abc123", title="Proxon abc123",
                            options={"hot_water_pump_power": 520, "hot_water_heater_power": 4500})
    await setup(hass, entry)
    data = entry.runtime_data.water_power({**entry.runtime_data.data, "T300RelaisKompressor": 1, "T300RelaisHeizstab": 1})
    assert data == {"LeistungWarmwasserWP": 520.0, "LeistungHeizstab": 4500.0}


async def test_no_estimate_without_the_hot_water_module(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    assert entry.runtime_data.water_power({"LeistungGesamt": 100}) == {}


async def test_energy_is_added_up(hass: HomeAssistant, device) -> None:
    """One hour of the heat pump at 430 W: 0.43 kWh in the total and today."""
    entry = await setup(hass)
    total = next(e for e in hass.data["sensor"].entities if e.entity_id == eid(hass, "sensor", "EnergieWarmwasserWP"))
    total._kwh, total._last = 0.0, None
    clock = [1000.0]
    with patch("custom_components.proxon_control.sensor.time.monotonic", side_effect=lambda: clock[0]):
        await refresh(hass, entry)
        for _ in range(12):  # an hour in five-minute steps
            clock[0] += timedelta(minutes=5).total_seconds()
            await refresh(hass, entry)
    assert round(float(hass.states.get(eid(hass, "sensor", "EnergieWarmwasserWP")).state), 3) == 0.43
    assert round(float(hass.states.get(eid(hass, "sensor", "EnergieHeizstab")).state), 3) == 0.0
