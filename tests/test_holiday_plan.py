"""Heating elements of all rooms at once; holiday plan with departure and return."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.proxon_control.holiday import plan_action

from .test_integration import call, eid, setup

T0 = datetime(2026, 12, 20, 8, 0)


# ---------------- heating elements of all rooms ----------------
async def test_all_heating_elements(hass: HomeAssistant, device) -> None:
    await setup(hass)  # living room's element off, bedroom and bath on
    switch = eid(hass, "switch", "WaermeelementeAlle")
    state = hass.states.get(switch)
    assert state.state == "off"
    assert state.attributes["rooms_on"] == ["Schlafzimmer", "Bad"] and state.attributes["rooms_off"] == ["Wohnzimmer"]
    device.writes.clear()
    await call(hass, "switch", "turn_on", entity_id=switch)
    assert device.writes == [{"obj": 0, "address": 384, "value": 1}]  # only the room that was off
    assert hass.states.get(switch).state == "on"
    device.writes.clear()
    await call(hass, "switch", "turn_off", entity_id=switch)
    assert device.writes == [{"obj": 0, "address": a, "value": 0} for a in (384, 516, 522)]
    assert hass.states.get(switch).state == "off"
    assert hass.states.get(eid(hass, "climate", "NBE1Thermostat")).state == "auto"  # the rooms' thermostats follow


# ---------------- holiday plan: rules ----------------
def test_plan_rules() -> None:
    start, end = T0, T0 + timedelta(days=7)
    assert plan_action(T0 - timedelta(minutes=1), start, end, 6, active=False, started=False) is None
    assert plan_action(T0, start, end, 6, active=False, started=False) == "on"
    assert plan_action(T0 + timedelta(days=2), start, end, 6, active=True, started=True) is None
    # switched off by hand during the holiday: not switched on again
    assert plan_action(T0 + timedelta(days=2), start, end, 6, active=False, started=True) is None
    back = end - timedelta(hours=6)
    assert plan_action(back - timedelta(minutes=1), start, end, 6, active=True, started=True) is None
    assert plan_action(back, start, end, 6, active=True, started=True) == "off"
    assert plan_action(back, start, end, 6, active=False, started=True) == "clear"
    # shorter than the warm-up: nothing happens, the plan goes away once it began
    assert plan_action(T0, start, T0 + timedelta(hours=5), 6, active=False, started=False) == "clear"
    assert plan_action(T0, None, end, 6, active=False, started=False) is None


# ---------------- holiday plan in Home Assistant ----------------
async def test_holiday_plan(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    holiday = entry.runtime_data.holiday
    holiday.restore_delay = 0
    start = dt_util.now().replace(microsecond=0) + timedelta(days=1)
    end = start + timedelta(days=7)
    await call(hass, "datetime", "set_value", entity_id=eid(hass, "datetime", "UrlaubAb"), datetime=start)
    await call(hass, "datetime", "set_value", entity_id=eid(hass, "datetime", "UrlaubBis"), datetime=end)
    assert dt_util.parse_datetime(hass.states.get(eid(hass, "datetime", "UrlaubAb")).state) == start
    assert float(hass.states.get(eid(hass, "number", "UrlaubVorlauf")).state) == 6
    switch = eid(hass, "switch", "Urlaubsmodus")
    assert dt_util.parse_datetime(hass.states.get(switch).attributes["plan_off_at"]) == end - timedelta(hours=6)
    assert hass.states.get(switch).state == "off"
    # departure: holiday mode on
    await holiday.async_check_plan(start + timedelta(minutes=1))
    await hass.async_block_till_done()
    assert hass.states.get(switch).state == "on" and holiday.saved
    # six hours before the return: off, everything back, plan gone
    await holiday.async_check_plan(end - timedelta(hours=6))
    await hass.async_block_till_done()
    assert hass.states.get(switch).state == "off"
    assert hass.states.get(eid(hass, "datetime", "UrlaubAb")).state == "unknown"
    assert hass.states.get(eid(hass, "datetime", "UrlaubBis")).state == "unknown"


async def test_holiday_plan_off_by_hand_and_cleared(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    holiday = entry.runtime_data.holiday
    holiday.restore_delay = 0
    start = dt_util.now().replace(microsecond=0) + timedelta(days=1)
    await holiday.async_set_plan(start=start, end=start + timedelta(days=7), lead_h=12)
    assert float(hass.states.get(eid(hass, "number", "UrlaubVorlauf")).state) == 12
    await holiday.async_check_plan(start)
    assert holiday.active
    # back early, switched off by hand: the plan is done and doesn't switch it on again
    await call(hass, "switch", "turn_off", entity_id=eid(hass, "switch", "Urlaubsmodus"))
    assert not holiday.active and holiday.plan_start is None
    await holiday.async_check_plan(start + timedelta(days=1))
    assert not holiday.active
    # a new plan, cleared with the button before it starts
    await holiday.async_set_plan(start=start + timedelta(days=30), end=start + timedelta(days=37))
    await call(hass, "button", "press", entity_id=eid(hass, "button", "UrlaubsplanLoeschen"))
    assert holiday.plan_start is None and holiday.plan_end is None


async def test_dashboard_settings(hass: HomeAssistant, device) -> None:
    await setup(hass)
    dashboard = await hass.services.async_call("proxon_control", "create_dashboard", {"paste_only": True}, blocking=True,
                                               return_response=True)
    settings = dashboard["views"][-1]
    entities = [c.get("entity") for s in settings["sections"] for c in s["cards"]]
    for key in ("UrlaubAb", "UrlaubBis", "UrlaubsplanLoeschen"):
        assert eid(hass, "datetime" if key.startswith("UrlaubA") or key == "UrlaubBis" else "button", key) in entities
    assert eid(hass, "number", "UrlaubVorlauf") in entities and eid(hass, "switch", "WaermeelementeAlle") in entities


async def test_both_on_the_start_page(hass: HomeAssistant, device) -> None:
    await setup(hass)
    dashboard = await hass.services.async_call("proxon_control", "create_dashboard", {"paste_only": True}, blocking=True,
                                               return_response=True)
    home = dashboard["views"][0]
    for section in home["sections"]:  # wide and narrow screens alike
        entities = [c.get("entity") for c in section["cards"]]
        if eid(hass, "switch", "Urlaubsmodus") in entities:  # departure and return right with holiday mode
            assert eid(hass, "datetime", "UrlaubAb") in entities and eid(hass, "datetime", "UrlaubBis") in entities
        if any(c["type"] == "vertical-stack" for c in section["cards"]):  # all heating elements right above the rooms
            assert section["cards"][0]["entity"] == eid(hass, "switch", "WaermeelementeAlle")  # above "Ground floor"
            assert section["cards"][1]["heading"] == "Ground floor"
