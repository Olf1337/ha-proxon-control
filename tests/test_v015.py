"""0.15.0: shower supply, legionella protection with solar power, electricity cost and the energy tab."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.proxon_control import legionella as L
from custom_components.proxon_control import registers as R

from .test_comfort import set_raw
from .test_energy import setup_with_sensors
from .test_integration import call, eid, setup

T0 = datetime(2026, 11, 10, 12, 0)


# ---------------- shower supply ----------------
def test_shower_minutes() -> None:
    assert R.shower_minutes({"WarmwasserIstTemperatur": 50.0, "WarmwasserUntenTemperatur": 30.0}) == 25.0  # 204 l of 40 °C
    assert R.shower_minutes({"WarmwasserIstTemperatur": 52.0, "WarmwasserUntenTemperatur": 48.0}) == 50.0
    assert R.shower_minutes({"WarmwasserIstTemperatur": 38.0, "WarmwasserUntenTemperatur": 30.0}) == 0.0  # nothing above 40 °C
    assert R.shower_minutes({"WarmwasserIstTemperatur": 50.0}) is None


async def test_shower_sensor(hass: HomeAssistant, device) -> None:
    await setup(hass)  # middle 36 °C, bottom 30 °C: too cold for a shower
    assert hass.states.get(eid(hass, "sensor", "WarmwasserDuschminuten")).state == "0"
    assert hass.states.get(eid(hass, "sensor", "WarmwasserDuschminuten")).attributes["unit_of_measurement"] == "min"


# ---------------- legionella protection: rules ----------------
def run(st: L.State, start: datetime, minutes: int, water=45.0, surplus=None, step=1):
    out = []
    for m in range(0, minutes + 1, step):
        now = start + timedelta(minutes=m)
        action, status = L.decide(now, st, water=water(m) if callable(water) else water,
                                  surplus_w=surplus(m) if callable(surplus) else surplus, surplus_limit=1500, blocked=False)
        if action in ("start_solar", "start_due"):
            L.started(st, now, L.SOLAR if action == "start_solar" else L.DUE, 55.0, False)
        elif action == "stop":
            L.stopped(st, now, (water(m) if callable(water) else water) >= L.REACHED)
        out.append((action, status))
    return out


def test_waits_a_few_days_then_looks_for_sun() -> None:
    st = L.State(on=True, reference=T0)
    assert run(st, T0 + timedelta(days=4), 0, surplus=3000)[-1] == (None, L.WAITING)  # just done: no need yet
    ds = run(st, T0 + timedelta(days=5), 12, surplus=3000)
    assert ds[5][1] == L.STARTING and ds[10] == ("start_solar", L.HEATING_SOLAR)
    assert st.active == L.SOLAR


def test_no_sun_for_a_week_heats_anyway() -> None:
    st = L.State(on=True, reference=T0)
    assert run(st, T0 + timedelta(days=6), 0, surplus=200)[-1] == (None, L.LOOKING)
    assert run(st, T0 + timedelta(days=7), 0, surplus=None)[-1] == ("start_due", L.HEATING_DUE)


def test_heating_ends_when_hot_and_counts_as_done() -> None:
    st = L.State(on=True, reference=T0)
    start = T0 + timedelta(days=7)
    ds = run(st, start, 75, water=lambda m: 50.0 if m < 75 else 60.0)  # 60 °C after 75 minutes
    assert ds[0][0] == "start_due" and ds[75] == ("stop", L.WAITING)
    assert st.active is None and st.last_done == start + timedelta(minutes=75) and st.last_try is None
    assert L.next_due(st) == start + timedelta(minutes=75) + L.INTERVAL


def test_gives_up_after_four_hours_and_tries_again_later() -> None:
    st = L.State(on=True, reference=T0)
    start = T0 + timedelta(days=7)
    ds = run(st, start, 4 * 60, water=50.0, step=10)
    assert ds[-1] == ("stop", L.WAITING) and st.last_try == start + timedelta(hours=4)
    assert run(st, start + timedelta(hours=10), 0)[-1] == (None, L.WAITING)
    assert run(st, start + timedelta(hours=16), 0)[-1][0] == "start_due"


def test_hot_water_by_itself_counts() -> None:
    st = L.State(on=True, reference=T0)
    run(st, T0 + timedelta(days=3), 0, water=61.0)
    assert run(st, T0 + timedelta(days=7), 0, water=50.0)[-1] == (None, L.WAITING)  # only 4 days since then


def test_off_and_blocked() -> None:
    st = L.State(on=False, reference=T0)
    assert L.decide(T0 + timedelta(days=9), st, water=40.0, surplus_w=3000, surplus_limit=1500, blocked=False) == (None, L.OFF)
    st.on = True
    assert L.decide(T0 + timedelta(days=9), st, water=40.0, surplus_w=3000, surplus_limit=1500, blocked=True) == (None, L.BLOCKED)


def test_state_survives_saving() -> None:
    st = L.State(on=True, reference=T0, last_done=T0, active=L.DUE, since=T0, saved_heater_target=55.0, saved_heater_on=False,
                 unit_function_was_on=True)
    assert L.State.from_dict(st.to_dict()) == st


# ---------------- legionella protection in Home Assistant ----------------
async def test_legionella_in_home_assistant(hass: HomeAssistant, device) -> None:
    set_raw(device, Legionellenfunktion=1)  # the unit's own legionella function is on
    entry = await setup_with_sensors(hass)  # hot water 36 °C, heater off, heater target 56 °C
    manager = entry.runtime_data.energy
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "LegionellenSonne"))
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 1, "address": 25, "value": 0}  # the unit's own function off
    assert hass.states.get(eid(hass, "sensor", "LegionellenStatus")).state == "waiting"
    # a week later without sun: heats anyway, heater target 60 °C and heater on
    later = dt_util.now() + timedelta(days=7, minutes=1)
    device.writes.clear()
    await manager.async_evaluate(later)
    await hass.async_block_till_done()
    assert device.writes == [{"obj": 1, "address": 3, "value": 600}, {"obj": 1, "address": 1, "value": 1}]
    assert hass.states.get(eid(hass, "sensor", "LegionellenStatus")).state == "heating_due"
    assert hass.states.get(eid(hass, "switch", "LegionellenSonne")).attributes["status"] == "heating_due"
    # 60 °C reached: heater target and heater back as they were
    set_raw(device, WarmwasserIstTemperatur=1600)
    device.writes.clear()
    await entry.runtime_data.async_refresh()  # the new reading is checked right away
    await hass.async_block_till_done()
    assert device.writes == [{"obj": 1, "address": 3, "value": 560}, {"obj": 1, "address": 1, "value": 0}]
    status = hass.states.get(eid(hass, "sensor", "LegionellenStatus"))
    assert status.state == "waiting" and status.attributes["last_done"]
    # switched off: the unit's own function on again
    await call(hass, "switch", "turn_off", entity_id=eid(hass, "switch", "LegionellenSonne"))
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 1, "address": 25, "value": 1}


async def test_boost_leaves_the_heater_on_for_legionella(hass: HomeAssistant, device) -> None:
    entry = await setup_with_sensors(hass)
    manager, comfort = entry.runtime_data.energy, entry.runtime_data.comfort
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "BoostGrenze"), value=42)
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "WarmwasserBoost"))  # boost: heater on
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "LegionellenSonne"))
    await manager.async_evaluate(dt_util.now() + timedelta(days=7, minutes=1))  # legionella heats too
    assert manager.legionella.state.active == L.DUE and manager.legionella.state.saved_heater_on is False
    set_raw(device, WarmwasserIstTemperatur=1450, **{"E-Heizstab": 1})  # 45 °C: the boost is done
    await entry.runtime_data.async_refresh()
    device.writes.clear()
    await comfort.async_evaluate(dt_util.now() + timedelta(minutes=11))
    await hass.async_block_till_done()
    assert {"obj": 1, "address": 1, "value": 0} not in device.writes  # the heater stays on for legionella


# ---------------- electricity cost ----------------
async def test_electricity_cost(hass: HomeAssistant, device) -> None:
    entry = await setup_with_sensors(hass)  # price 0.30 €/kWh, the unit draws 531.8 W
    sensor = eid(hass, "sensor", "Stromkosten")
    cost = next(e for e in hass.data["sensor"].entities if e.entity_id == sensor)
    for minute in range(61):  # one hour, a reading every minute
        cost._add(1000.0 + minute * 60)
    assert round(cost.native_value, 3) == round(0.5318 * 0.30, 3)
    hass.states.async_set("sensor.preis", "unknown")
    cost._add(1000.0 + 61 * 60)  # no price: costs nothing
    assert round(cost.native_value, 3) == round(0.5318 * 0.30, 3)
    state = hass.states.get(sensor)
    assert state.attributes["device_class"] == "monetary" and state.attributes["state_class"] == "total"
    assert entry.options["price_sensor"] == "sensor.preis"


async def test_no_cost_without_price_sensor(hass: HomeAssistant, device) -> None:
    await setup(hass)
    from homeassistant.helpers import entity_registry as er

    assert er.async_get(hass).async_get_entity_id("sensor", "proxon_control", "abc123_Stromkosten") is None
