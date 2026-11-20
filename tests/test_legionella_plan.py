"""Legionella protection: planned on a weekday at a time; "with solar" only with a surplus sensor."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util
import pytest

from custom_components.proxon_control import legionella as L

from .test_comfort import set_raw
from .test_energy import setup_with_sensors
from .test_integration import call, eid, setup

SUN = datetime(2026, 11, 22, 13, 0)  # a Sunday at 13:00 (the default planned time)


def plan(**kw) -> L.State:
    return L.State(plan_on=True, plan_day=6, plan_time=time(13, 0), **kw)


def decide(st: L.State, now: datetime, water: float = 45.0) -> tuple[str | None, str]:
    return L.decide(now, st, water=water, surplus_w=None, surplus_limit=1500, blocked=False)


# ---------------- rules ----------------
def test_slots() -> None:
    assert L.last_slot(SUN, 6, time(13, 0)) == SUN
    assert L.last_slot(SUN - timedelta(minutes=1), 6, time(13, 0)) == SUN - timedelta(days=7)
    assert L.last_slot(SUN + timedelta(days=3), 6, time(13, 0)) == SUN
    st = plan(plan_slot=SUN - timedelta(days=7))
    assert L.next_slot(SUN - timedelta(hours=1), st) == SUN


def test_planned_heating_at_its_time() -> None:
    st = plan(plan_slot=SUN - timedelta(days=7))  # switched on during the week before
    assert decide(st, SUN - timedelta(minutes=1)) == (None, L.PLANNED)
    assert decide(st, SUN) == ("start_plan", L.HEATING_PLANNED)
    L.started(st, SUN, L.PLAN, 55.0, False)
    assert decide(st, SUN + timedelta(minutes=30)) == (None, L.HEATING_PLANNED)
    assert decide(st, SUN + timedelta(minutes=80), water=60.0) == ("stop", L.PLANNED)  # hot enough
    L.stopped(st, SUN + timedelta(minutes=80), True)
    assert decide(st, SUN + timedelta(hours=2)) == (None, L.PLANNED) and st.plan_slot == SUN  # done for this week
    assert decide(st, SUN + timedelta(days=7)) == ("start_plan", L.HEATING_PLANNED)  # next Sunday


def test_planned_heating_skipped_or_retried() -> None:
    st = plan(plan_slot=SUN - timedelta(days=7), last_done=SUN - timedelta(hours=20))  # hot the evening before
    assert decide(st, SUN) == (None, L.PLANNED) and st.plan_slot == SUN
    st = plan(plan_slot=SUN - timedelta(days=7))
    L.started(st, SUN, L.PLAN, 55.0, False)
    assert decide(st, SUN + L.MAX_RUN) == ("stop", L.PLANNED)  # not hot after four hours
    L.stopped(st, SUN + L.MAX_RUN, False)
    assert decide(st, SUN + L.MAX_RUN + timedelta(hours=1)) == (None, L.PLANNED)
    assert decide(st, SUN + L.MAX_RUN + L.RETRY) == ("start_plan", L.HEATING_PLANNED)  # tried again
    st = plan(plan_slot=SUN - timedelta(days=7))
    assert decide(st, SUN + L.PLAN_WINDOW) == (None, L.PLANNED) and st.plan_slot == SUN  # too late: next week


def test_plan_survives_a_restart() -> None:
    st = plan(plan_slot=SUN)
    st.plan_day, st.plan_time = 2, time(6, 30)
    back = L.State.from_dict(st.to_dict())
    assert (back.plan_on, back.plan_day, back.plan_time, back.plan_slot) == (True, 2, time(6, 30), SUN)
    assert L.State.from_dict({}).plan_day == L.PLAN_DAY and L.State.from_dict({"plan_day": 9}).plan_day == L.PLAN_DAY


# ---------------- in Home Assistant ----------------
async def test_with_solar_needs_a_sensor(hass: HomeAssistant, device) -> None:
    await setup(hass)  # no surplus sensor chosen
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "LegionellenSonne"))
    assert err.value.translation_key == "legionella_needs_sensor"
    assert hass.states.get(eid(hass, "switch", "LegionellenSonne")).state == "off"
    # planned works without one
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "LegionellenGeplant"))
    assert hass.states.get(eid(hass, "switch", "LegionellenGeplant")).state == "on"


async def test_planned_in_home_assistant(hass: HomeAssistant, device) -> None:
    set_raw(device, Legionellenfunktion=1)  # the unit's own legionella function is on
    entry = await setup_with_sensors(hass)
    feature = entry.runtime_data.energy.legionella
    await call(hass, "select", "select_option", entity_id=eid(hass, "select", "LegionellenTag"), option="wednesday")
    await call(hass, "time", "set_value", entity_id=eid(hass, "time", "LegionellenPlanZeit"), time="06:30")
    assert hass.states.get(eid(hass, "select", "LegionellenTag")).state == "wednesday"
    assert hass.states.get(eid(hass, "time", "LegionellenPlanZeit")).state == "06:30:00"
    device.writes.clear()
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "LegionellenGeplant"))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert {"obj": 1, "address": 25, "value": 0} in device.writes  # the unit's own function off
    assert hass.states.get(eid(hass, "sensor", "LegionellenStatus")).state == "planned"
    nxt = dt_util.parse_datetime(hass.states.get(eid(hass, "sensor", "LegionellenStatus")).attributes["planned_next"])
    assert nxt.weekday() == 2 and (nxt.hour, nxt.minute) == (6, 30) and nxt > dt_util.now()
    # at the planned time it heats: heater target 60 °C and heater on
    device.writes.clear()
    await entry.runtime_data.energy.async_evaluate(nxt + timedelta(minutes=1))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert device.writes == [{"obj": 1, "address": 3, "value": 600}, {"obj": 1, "address": 1, "value": 1}]
    assert feature.state.active == L.PLAN
    # "with solar" switched on (a surplus sensor is chosen here): "planned" goes off, only one of them is on
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "LegionellenSonne"))
    assert hass.states.get(eid(hass, "switch", "LegionellenGeplant")).state == "off"
    assert hass.states.get(eid(hass, "switch", "LegionellenSonne")).state == "on"
    # both off: the unit's own function on again
    device.writes.clear()
    await call(hass, "switch", "turn_off", entity_id=eid(hass, "switch", "LegionellenSonne"))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert {"obj": 1, "address": 25, "value": 1} in device.writes
