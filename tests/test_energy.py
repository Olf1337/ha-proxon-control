"""Hot water as a store for solar surplus and cheap electricity."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant

from custom_components.proxon_control import energy as E

from .test_integration import call, eid, make_entry, setup

T0 = datetime(2026, 11, 10, 12, 0)
ON = E.Settings(solar_on=True, price_on=True, surplus_w=1500, price_ct=10, store_temp=55)


def run(st: E.State, minutes: int, surplus=None, price=None, settings=ON, unit_ok=True, start=T0):
    """Decide once per minute; apply starts/stops like the manager does. Returns the decisions."""
    out = []
    for m in range(minutes + 1):
        now = start + timedelta(minutes=m)
        d = E.decide(now, settings, st, surplus(m) if callable(surplus) else surplus, price(m) if callable(price) else price, unit_ok)
        if d.action == "start":
            E.started(st, now, d.source, 46.0)
        elif d.action == "stop":
            E.stopped(st, now)
        out.append(d)
    return out


# ---------------- rules ----------------
def test_solar_needs_ten_minutes_of_surplus() -> None:
    st = E.State()
    ds = run(st, 12, surplus=2000)
    assert [d.action for d in ds].index("start") == 10
    assert ds[5].status == E.STARTING and ds[10].status == E.HEATING_SOLAR


def test_short_surplus_does_not_start() -> None:
    st = E.State()
    ds = run(st, 20, surplus=lambda m: 2000 if m % 8 < 5 else 300)  # clouds
    assert all(d.action is None for d in ds)


def test_heating_goes_on_while_still_feeding_in() -> None:
    """The heat pump uses part of the surplus itself: heating goes on as long as power is still fed in."""
    st = E.State()
    run(st, 10, surplus=2000)
    ds = run(st, 60, surplus=200, start=T0 + timedelta(minutes=11))
    assert all(d.action is None and d.status == E.HEATING_SOLAR for d in ds)


def test_stop_after_ten_minutes_of_grid_import_but_not_before_30_minutes() -> None:
    st = E.State()
    run(st, 10, surplus=2000)  # started at minute 10
    ds = run(st, 40, surplus=-500, start=T0 + timedelta(minutes=11))
    stop = [d.action for d in ds].index("stop")
    assert stop + 11 >= 10 + 30  # minimum run of 30 minutes from the start
    assert st.active is None


def test_pause_after_stop_and_daily_limit() -> None:
    st = E.State(last_stop=T0 - timedelta(minutes=5))
    ds = run(st, 0, price=5)
    assert ds[0].status == E.PAUSED and ds[0].action is None
    st = E.State(starts=E.MAX_STARTS, starts_day=T0.date())
    assert run(st, 0, price=5)[0].status == E.PAUSED
    st = E.State(starts=E.MAX_STARTS, starts_day=(T0 - timedelta(days=1)).date())  # a new day
    assert run(st, 0, price=5)[0].action == "start"


def test_cheap_price_starts_right_away_and_stops_when_expensive() -> None:
    st = E.State()
    ds = run(st, 0, price=8.5)
    assert ds[0].action == "start" and st.active == E.PRICE
    ds = run(st, 45, price=25, start=T0 + timedelta(minutes=1))
    assert "stop" in [d.action for d in ds]


def test_switching_off_stops_right_away() -> None:
    st = E.State()
    run(st, 0, price=5)
    d = E.decide(T0 + timedelta(minutes=2), E.Settings(solar_on=True, price_on=False), st, 0, 5, True)
    assert d.action == "stop"


def test_blocked_when_hot_water_is_off() -> None:
    st = E.State()
    assert run(st, 0, price=5, unit_ok=False)[0].status == E.BLOCKED
    run(st, 0, price=5)
    assert E.decide(T0 + timedelta(minutes=1), ON, st, None, 5, False).action == "stop"


def test_no_sensor() -> None:
    assert run(E.State(), 0)[0].status == E.NO_SOURCE
    assert run(E.State(), 0, settings=E.Settings())[0].status == E.OFF


def test_units() -> None:
    assert E.price_in_cent(0.085, "€/kWh") == 8.5
    assert E.price_in_cent(0.085, "EUR/kWh") == 8.5
    assert E.price_in_cent(8.5, "ct/kWh") == 8.5
    assert E.price_in_cent(85, "EUR/MWh") == 8.5
    assert E.power_in_watt(1.5, "kW", False) == 1500
    assert E.power_in_watt(-1500, "W", True) == 1500


def test_state_survives_saving() -> None:
    st = E.State(active=E.SOLAR, since=T0, last_stop=T0, starts_day=T0.date(), starts=2, saved_target=46.0)
    back = E.State.from_dict(st.to_dict())
    assert (back.active, back.since, back.starts, back.saved_target) == (E.SOLAR, T0, 2, 46.0)


# ---------------- in Home Assistant ----------------
async def setup_with_sensors(hass: HomeAssistant):
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"surplus_sensor": "sensor.netz", "price_sensor": "sensor.preis", "feed_in_negative": True})
    hass.states.async_set("sensor.netz", "0", {"unit_of_measurement": "W"})
    hass.states.async_set("sensor.preis", "0.30", {"unit_of_measurement": "€/kWh"})
    return await setup(hass, entry)


async def test_entities_and_defaults(hass: HomeAssistant, device) -> None:
    await setup(hass)
    assert hass.states.get(eid(hass, "switch", "SolarWarmwasser")).state == "off"
    assert hass.states.get(eid(hass, "switch", "PreisWarmwasser")).state == "off"
    assert float(hass.states.get(eid(hass, "number", "SolarSchwelle")).state) == 1500
    assert float(hass.states.get(eid(hass, "number", "PreisSchwelle")).state) == 10
    assert float(hass.states.get(eid(hass, "number", "SpeicherTemperatur")).state) == 55
    assert hass.states.get(eid(hass, "sensor", "Energiemanager")).state == "off"


async def test_solar_surplus_raises_and_restores_the_hot_water_target(hass: HomeAssistant, device) -> None:
    entry = await setup_with_sensors(hass)
    manager = entry.runtime_data.energy
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "SolarWarmwasser"))
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "SolarSchwelle"), value=1000)
    hass.states.async_set("sensor.netz", "-1800", {"unit_of_measurement": "W"})  # 1.8 kW fed in (negative = feed-in)
    now = datetime(2026, 11, 10, 12, 0)
    await manager.async_evaluate(now)
    assert hass.states.get(eid(hass, "sensor", "Energiemanager")).state == "starting"
    assert device.writes == []
    await manager.async_evaluate(now + timedelta(minutes=10))
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 1, "address": 0, "value": 550}  # hot water 34 -> 55 °C
    status = hass.states.get(eid(hass, "sensor", "Energiemanager"))
    assert status.state == "heating_solar" and status.attributes["previous_target"] == 34.0
    assert status.attributes["surplus_w"] == 1800
    # grid import for 10 minutes after the minimum run: back to the old target
    hass.states.async_set("sensor.netz", "400", {"unit_of_measurement": "W"})
    await manager.async_evaluate(now + timedelta(minutes=35))
    await manager.async_evaluate(now + timedelta(minutes=45))
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 1, "address": 0, "value": 340}
    assert hass.states.get(eid(hass, "sensor", "Energiemanager")).state == "waiting"


async def test_cheap_price_heats_and_user_target_is_kept(hass: HomeAssistant, device) -> None:
    entry = await setup_with_sensors(hass)
    manager = entry.runtime_data.energy
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "PreisWarmwasser"))
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "PreisSchwelle"), value=12)
    hass.states.async_set("sensor.preis", "0.09", {"unit_of_measurement": "€/kWh"})  # 9 ct
    now = datetime(2026, 11, 10, 2, 0)
    await manager.async_evaluate(now)
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 1, "address": 0, "value": 550}
    # the user sets another target meanwhile: it isn't overwritten when the cheap hours end
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "SollWassertemperatur"), value=50)
    n = len(device.writes)
    hass.states.async_set("sensor.preis", "0.31", {"unit_of_measurement": "€/kWh"})
    await manager.async_evaluate(now + timedelta(minutes=31))
    await manager.async_evaluate(now + timedelta(minutes=45))
    await hass.async_block_till_done()
    assert len(device.writes) == n and manager.state.active is None


async def test_switching_off_restores_right_away(hass: HomeAssistant, device) -> None:
    entry = await setup_with_sensors(hass)
    manager = entry.runtime_data.energy
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "PreisWarmwasser"))
    hass.states.async_set("sensor.preis", "0.05", {"unit_of_measurement": "€/kWh"})
    await manager.async_evaluate(datetime(2026, 11, 10, 2, 0))
    await call(hass, "switch", "turn_off", entity_id=eid(hass, "switch", "PreisWarmwasser"))
    await hass.async_block_till_done()
    assert device.writes[-1] == {"obj": 1, "address": 0, "value": 340}


async def test_settings_survive_a_restart(hass: HomeAssistant, device) -> None:
    entry = await setup_with_sensors(hass)
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "SolarWarmwasser"))
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "SolarSchwelle"), value=2500)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "switch", "SolarWarmwasser")).state == "on"
    assert float(hass.states.get(eid(hass, "number", "SolarSchwelle")).state) == 2500


async def test_sensors_are_chosen_in_the_options(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"scan_interval": 10, "surplus_sensor": "sensor.netz", "feed_in_negative": True, "price_sensor": "sensor.preis"}
    )
    assert entry.options == {"scan_interval": 10, "surplus_sensor": "sensor.netz", "price_sensor": "sensor.preis", "feed_in_negative": True}


async def test_checks_every_minute_on_its_own(hass: HomeAssistant, device) -> None:
    """A cheaper price arrives between two queries of the unit: the check every minute picks it up (in Home Assistant's event loop)."""
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    from homeassistant.util import dt as dt_util

    await setup_with_sensors(hass)
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "PreisWarmwasser"))
    assert device.writes == []  # 30 ct: too expensive
    hass.states.async_set("sensor.preis", "0.05", {"unit_of_measurement": "€/kWh"})
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done(wait_background_tasks=True)
    assert device.writes[-1] == {"obj": 1, "address": 0, "value": 550}
