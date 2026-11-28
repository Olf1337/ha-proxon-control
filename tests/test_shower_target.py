"""1.1: the hot-water target said as a shower reserve, and the switch that lets the page "Proxon" set it that way."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.proxon_control import registers as R

from .test_integration import call, eid, setup


def test_shower_minutes_of_a_full_tank() -> None:
    assert R.shower_minutes_at(37) == 0.0  # too cold for the shower
    assert R.shower_minutes_at(40) == 35.0  # as warm as the shower: 300 l as they are
    assert R.shower_minutes_at(41) == 35.0
    assert R.shower_minutes_at(55) == 55.0


def test_lowest_target_for_each_step() -> None:
    lo, hi = R.SHOWER_TARGET_RANGE
    targets = {m: R.target_for_shower_minutes(m) for m in range(lo, hi + 1, 5)}
    assert targets == {35: 41.0, 40: 42.0, 45: 46.0, 50: 50.0, 55: 54.0}
    for minutes, target in targets.items():
        assert R.shower_minutes_at(target) >= minutes  # holds them ...
        assert target == 41 or R.shower_minutes_at(target - 1) < minutes  # ... and is the lowest that does
    assert R.target_for_shower_minutes(90) == 55.0  # never above the highest water target
    assert R.target_for_shower_minutes(0) == 41.0  # never at or below the shower's own temperature


async def test_setting_the_shower_reserve_writes_the_water_target(hass: HomeAssistant, device) -> None:
    await setup(hass)  # water target 34 °C: too cold for a shower
    number = eid(hass, "number", "DuschvorratSoll")
    st = hass.states.get(number)
    assert st.state == "0.0" and st.attributes["min"] == 35 and st.attributes["max"] == 55 and st.attributes["step"] == 5
    assert st.attributes["water_target"] == 34.0
    await call(hass, "number", "set_value", entity_id=number, value=45)
    await hass.async_block_till_done()
    assert device.writes[-1]["value"] == 460  # 46 °C, in tenths
    assert hass.states.get(number).state == "45.0"
    assert hass.states.get(eid(hass, "number", "SollWassertemperatur")).state == "46.0"


async def test_shower_mode_only_changes_the_page(hass: HomeAssistant, device) -> None:
    await setup(hass)
    switch = eid(hass, "switch", "DuschvorratModus")
    assert hass.states.get(switch).state == "off"
    before = len(device.writes)
    await call(hass, "switch", "turn_on", entity_id=switch)
    assert hass.states.get(switch).state == "on"
    await call(hass, "switch", "turn_off", entity_id=switch)
    assert hass.states.get(switch).state == "off"
    assert len(device.writes) == before  # nothing is written to the unit


async def test_shower_mode_survives_a_restart(hass: HomeAssistant, device) -> None:
    mock_restore_cache(hass, [State("switch.proxon_set_hot_water_as_shower_supply", "on")])
    await setup(hass)
    switch = eid(hass, "switch", "DuschvorratModus")
    assert switch == "switch.proxon_set_hot_water_as_shower_supply"
    assert hass.states.get(switch).state == "on"


async def test_no_shower_target_without_hot_water_module(hass: HomeAssistant, device) -> None:
    from .test_integration import no_entity
    device.raw = {k: v for k, v in device.raw.items() if k != (False, *R.BY_KEY["WarmwasserIstTemperatur"].read)}
    await setup(hass)
    assert no_entity(hass, "number", "DuschvorratSoll") and no_entity(hass, "switch", "DuschvorratModus")


# ---------------- 1.1.0: the household's own shower, "hot water low", the tile wall's options ----------------
def test_a_different_shower() -> None:
    # an economy shower head (6 l/min) at 38 °C: the same tank lasts longer
    assert R.shower_minutes({"WarmwasserIstTemperatur": 50.0, "WarmwasserUntenTemperatur": 48.0}, 38.0, 6.0) == 70.0  # 427 l at 6 l/min
    assert R.shower_target_range(38.0, 6.0) == (50.0, 80.0)
    target = R.target_for_shower_minutes(70, 38.0, 6.0)
    assert R.shower_minutes_at(target, 38.0, 6.0) >= 70 > R.shower_minutes_at(target - 1, 38.0, 6.0)
    assert R.shower_target_range() == (35.0, 55.0)  # the usual shower: unchanged


async def _configure(hass: HomeAssistant, entry, **changes):
    from homeassistant.data_entry_flow import FlowResultType
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(flow["flow_id"], {"scan_interval": 10, **changes})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return result


async def test_shower_options_change_supply_and_target(hass: HomeAssistant, device) -> None:
    from custom_components.proxon_control import panel as P
    entry = await setup(hass)
    await _configure(hass, entry, shower_temperature=38, shower_flow=6)
    assert entry.options["shower_temperature"] == 38.0 and entry.options["shower_flow"] == 6.0
    st = hass.states.get(eid(hass, "number", "DuschvorratSoll"))
    assert (st.attributes["min"], st.attributes["max"]) == (50, 80)
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "DuschvorratSoll"), value=70)
    await hass.async_block_till_done()
    assert device.writes[-1]["value"] == 10 * R.target_for_shower_minutes(70, 38.0, 6.0)
    assert P.panel_config(hass, entry)["shower"] == {"temp": 38.0, "flow": 6.0}
    await _configure(hass, entry, shower_temperature=40, shower_flow=8)  # back to the usual: nothing kept
    assert "shower_temperature" not in entry.options and "shower_flow" not in entry.options


async def test_hot_water_low_follows_its_limit(hass: HomeAssistant, device) -> None:
    await setup(hass)  # middle 36 °C: no shower supply at all
    low, limit = eid(hass, "binary_sensor", "WarmwasserKnapp"), eid(hass, "number", "DuschvorratGrenze")
    assert hass.states.get(limit).state == "10.0"
    assert hass.states.get(low).state == "on" and hass.states.get(low).attributes["shower_minutes"] == 0
    await call(hass, "number", "set_value", entity_id=limit, value=0)
    assert hass.states.get(low).state == "off"  # nothing is below 0 minutes


async def test_hot_water_low_limit_survives_a_restart(hass: HomeAssistant, device) -> None:
    from pytest_homeassistant_custom_component.common import mock_restore_cache_with_extra_data
    mock_restore_cache_with_extra_data(hass, [(State("number.proxon_shower_supply_warn_below", "0"), {
        "native_value": 0.0, "native_min_value": 0, "native_max_value": 60, "native_step": 5, "native_unit_of_measurement": "min"})])
    await setup(hass)
    assert eid(hass, "number", "DuschvorratGrenze") == "number.proxon_shower_supply_warn_below"
    assert hass.states.get("number.proxon_shower_supply_warn_below").state == "0.0"
    assert hass.states.get(eid(hass, "binary_sensor", "WarmwasserKnapp")).state == "off"


async def test_tile_wall_options(hass: HomeAssistant, device) -> None:
    from custom_components.proxon_control import panel as P
    entry = await setup(hass)
    assert P.panel_config(hass, entry)["tiles"] == {"layout": "row", "size": "medium", "accent": "amber"}
    await _configure(hass, entry, tiles_layout="grid", tiles_size="large", tiles_accent="blue")
    assert P.panel_config(hass, entry)["tiles"] == {"layout": "grid", "size": "large", "accent": "blue"}
    await _configure(hass, entry, tiles_layout="row", tiles_size="medium", tiles_accent="amber")
    assert not any(k.startswith("tiles_") for k in entry.options)


def test_a_tank_still_charging_has_water_at_the_top() -> None:
    """1.2.1: middle 41.5 °C, bottom 36.7 °C, target 45 °C, showering at 42 °C - the top is warmer than the middle, so there
    is some shower supply (before: 0 minutes next to "250 l warm water")."""
    charging = {"WarmwasserIstTemperatur": 41.5, "WarmwasserUntenTemperatur": 36.7, "SollWassertemperatur": 45.0}
    assert R.tank_layers(charging) == [(75.0, 45.0), (75.0, 41.5), (150.0, 36.7)]
    assert R.shower_minutes(charging, 42, 8) == 15.0  # 82.5 l from the top, 75 l of 41.5 °C as they are
    assert R.hot_liters(charging, 42) == 150.0
    # the top is never guessed above the target, nor below the middle
    assert R.tank_layers({**charging, "WarmwasserUntenTemperatur": 20.0})[0][1] == 45.0
    assert R.tank_layers({**charging, "WarmwasserUntenTemperatur": 50.0})[0][1] == 41.5
    hot = {"WarmwasserIstTemperatur": 50.0, "WarmwasserUntenTemperatur": 44.0, "SollWassertemperatur": 45.0}
    assert R.tank_layers(hot)[0][1] == 50.0
    # without a target: no warmer than the middle; without sensors: nothing
    assert R.tank_layers({"WarmwasserIstTemperatur": 41.5, "WarmwasserUntenTemperatur": 36.7})[0][1] == 41.5
    assert R.tank_layers({}) is None and R.hot_liters({}) is None and R.shower_minutes({}) is None
    # 1.2.2: a mixed tank just below the shower is not empty (was 0 l / 0 min); 3 K below it is
    mixed = {"WarmwasserIstTemperatur": 41.7, "WarmwasserUntenTemperatur": 41.6, "SollWassertemperatur": 45.0}
    assert R.hot_liters(mixed, 42) == 300.0 and R.shower_minutes(mixed, 42, 8) == 35.0
    cold = {"WarmwasserIstTemperatur": 39.0, "WarmwasserUntenTemperatur": 38.9, "SollWassertemperatur": 45.0}
    assert R.hot_liters(cold, 42) == 0.0 and R.shower_minutes(cold, 42, 8) == 0.0
    # a tank at one temperature throughout: the same as before
    assert R.hot_liters({"WarmwasserIstTemperatur": 50.0, "WarmwasserUntenTemperatur": 50.0}) == 300.0
    assert R.shower_minutes_at(41) == 35.0


async def test_shower_supply_says_its_hot_litres(hass: HomeAssistant, device) -> None:
    await setup(hass)
    entry = hass.config_entries.async_entries("proxon_control")[0]
    data = entry.runtime_data.data
    st = hass.states.get(eid(hass, "sensor", "WarmwasserDuschminuten"))
    assert st.attributes["hot_liters"] == R.hot_liters(data, entry.runtime_data.shower[0]) is not None
