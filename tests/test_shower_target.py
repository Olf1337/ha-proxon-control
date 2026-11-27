"""1.1: the hot-water target said as a shower reserve, and the switch that lets the page "Proxon" set it that way."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, State
from pytest_homeassistant_custom_component.common import mock_restore_cache

from custom_components.proxon_control import registers as R

from .test_integration import call, eid, setup


def test_shower_minutes_of_a_full_tank() -> None:
    assert R.shower_minutes_at(40) == 0.0  # nothing warmer than the shower
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
