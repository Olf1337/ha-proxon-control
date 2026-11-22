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


def _ran_today(hass_storage, entry, seconds: float) -> None:
    """The hot-water heat pump ran `seconds` today before the integration started (its running time, kept by the integration)."""
    from homeassistant.util import dt as dt_util

    hass_storage[f"{DOMAIN}.{entry.entry_id}.runtime"] = {"version": 1, "key": f"{DOMAIN}.{entry.entry_id}.runtime", "data": {
        "WarmwasserKompressor": {"day": dt_util.now().date().isoformat(), "seconds": seconds, "on": False}}}


async def test_new_counter_starts_with_todays_running_time(hass: HomeAssistant, device, hass_storage) -> None:
    """Installed after the heat pump ran today: the estimate starts with that (2.2 h x 430 W), and today shows it too."""
    from .test_integration import make_entry

    entry = make_entry()
    _ran_today(hass_storage, entry, 2.2 * 3600)
    entry.add_to_hass(hass)
    await setup(hass, entry)
    total = float(hass.states.get(eid(hass, "sensor", "EnergieWarmwasserWP")).state)
    assert round(total, 3) == 0.946
    assert round(float(hass.states.get(eid(hass, "sensor", "EnergieWarmwasserWPHeute")).state), 3) == 0.946
    assert round(float(hass.states.get(eid(hass, "sensor", "EnergieWarmwasserWPWoche")).state), 3) == 0.946
    assert float(hass.states.get(eid(hass, "sensor", "EnergieHeizstab")).state) == 0  # the heater didn't run


async def test_counter_still_at_zero_takes_over_today(hass: HomeAssistant, device, hass_storage) -> None:
    """A counter that has counted nothing since it was created (the beta installed after the heat pump ran) takes over
    today's running time at the next start; a counter that has counted keeps its own value."""
    from homeassistant.core import State
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import mock_restore_cache, mock_restore_cache_with_extra_data

    from .test_integration import make_entry

    entry = make_entry()
    _ran_today(hass_storage, entry, 3600)
    today = dt_util.now().date().isoformat()
    total_id = "sensor.proxon_energy_hot_water_heat_pump_estimated"
    today_id = "sensor.proxon_energy_hot_water_heat_pump_today_estimated"
    mock_restore_cache_with_extra_data(hass, [(State(total_id, "0.0"), {"native_value": 0.0, "native_unit_of_measurement": "kWh"})])
    mock_restore_cache(hass, [State(today_id, "0.0", {"period": today, "period_start_value": 0.0})])
    entry.add_to_hass(hass)
    await setup(hass, entry)
    assert eid(hass, "sensor", "EnergieWarmwasserWP") == total_id and eid(hass, "sensor", "EnergieWarmwasserWPHeute") == today_id
    assert float(hass.states.get(total_id).state) == 0.43
    assert float(hass.states.get(today_id).state) == 0.43
