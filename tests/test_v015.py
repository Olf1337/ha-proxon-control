"""0.15.0: shower supply, legionella protection with solar power, electricity cost and the energy tab."""
from __future__ import annotations

from datetime import datetime, timedelta
import time

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
    # readings on the sensor's monotonic clock, far after the real readings of the setup (on a freshly started machine the
    # clock is small, so fixed times could lie right after them and count a part of that)
    base = time.monotonic() + 100_000
    for minute in range(61):  # one hour, a reading every minute
        cost._add(base + minute * 60)
    assert round(cost.native_value, 3) == round(0.5318 * 0.30, 3)
    hass.states.async_set("sensor.preis", "unknown")
    cost._add(base + 61 * 60)  # no price: costs nothing
    assert round(cost.native_value, 3) == round(0.5318 * 0.30, 3)
    state = hass.states.get(sensor)
    assert state.attributes["device_class"] == "monetary" and state.attributes["state_class"] == "total"
    assert entry.options["price_sensor"] == "sensor.preis"


async def test_no_cost_without_price_sensor(hass: HomeAssistant, device) -> None:
    await setup(hass)
    from homeassistant.helpers import entity_registry as er

    assert er.async_get(hass).async_get_entity_id("sensor", "proxon_control", "abc123_Stromkosten") is None



# ---------------- FWT 3.0 ----------------
def test_fwt3_led_values_fall_back_to_the_temperature() -> None:
    """FWT 3.0, firmware 12: the LED field holds two bytes (high byte = offset + 4), not the 4/5/6 demand level."""
    base = {"NBE0MittelTemperatur": 23.0}
    room = {"NBE1MittelTemperatur": 20.0, "NBE1OffsetTemperatur": 2.0}  # target 22 °C
    assert R.room_demand({**base, **room, "NBE1LED": 1540.0, "NBE1Temperatur": 24.1}, 1) == "warmer"
    assert R.room_demand({**base, **room, "NBE1LED": 1540.0, "NBE1Temperatur": 22.0}, 1) == "at_target"
    assert R.room_demand({**base, **room, "NBE1LED": 1540.0, "NBE1Temperatur": 21.0}, 1) == "too_cold"



# ---------------- energy per day / week / month / year ----------------
def test_period_of() -> None:
    from custom_components.proxon_control.sensor import period_of

    t = datetime(2026, 11, 13, 7, 30)  # a Friday
    assert [period_of(t, p) for p in ("day", "week", "month", "year")] == ["2026-11-13", "2026-W46", "2026-11", "2026"]
    assert period_of(datetime(2027, 1, 1), "week") == "2026-W53"  # 1 January 2027 still belongs to the last week of 2026


async def test_energy_per_period(hass: HomeAssistant, device, freezer) -> None:
    await hass.config.async_set_time_zone("Europe/Berlin")  # periods follow the local time
    freezer.move_to("2026-11-13 10:00:00+01:00")
    entry = await setup(hass)
    total = next(e for e in hass.data["sensor"].entities if e.entity_id == eid(hass, "sensor", "EnergieGesamt"))
    names = {p: eid(hass, "sensor", f"EnergieGesamt{p}") for p in ("Heute", "Woche", "Monat", "Jahr")}
    assert eid(hass, "sensor", "EnergieKompressorHeute") and eid(hass, "sensor", "EnergieLueftungJahr")
    async def refresh() -> None:
        entry.runtime_data.async_set_updated_data(dict(entry.runtime_data.data))
        await hass.async_block_till_done()

    total._kwh = 0.0  # nothing counted yet (the test unit's first readings are dropped)
    await refresh()
    assert {p: float(hass.states.get(e).state) for p, e in names.items()} == {"Heute": 0, "Woche": 0, "Monat": 0, "Jahr": 0}
    total._kwh += 3.5  # used since the start
    await refresh()
    assert all(float(hass.states.get(e).state) == 3.5 for e in names.values())
    # next day (Saturday): today starts again, the week goes on
    freezer.move_to("2026-11-14 00:05:00+01:00")
    await refresh()
    total._kwh += 0.5
    await refresh()
    assert float(hass.states.get(names["Heute"]).state) == 0.5
    assert float(hass.states.get(names["Woche"]).state) == 4.0
    state = hass.states.get(names["Heute"])
    assert state.attributes["period"] == "2026-11-14" and state.attributes["period_start_value"] == 3.5
    assert state.attributes["state_class"] == "total_increasing"

    # counted right through midnight: today counts from its start (for the forecasts)
    assert state.attributes["counting_since"] == "2026-11-14T00:00:00+01:00"


def test_period_bounds() -> None:
    from homeassistant.util import dt as dt_util

    from custom_components.proxon_control.sensor import period_bounds

    t = datetime(2026, 11, 13, 7, 30, tzinfo=dt_util.get_default_time_zone())
    start, end = period_bounds(t, "week")
    assert (start.date().isoformat(), end.date().isoformat()) == ("2026-11-09", "2026-11-16")  # Monday to Monday
    start, end = period_bounds(t, "month")
    assert (start.date().isoformat(), end.date().isoformat()) == ("2026-11-01", "2026-12-01")
    start, end = period_bounds(datetime(2026, 12, 31, 23, 0, tzinfo=t.tzinfo), "year")
    assert (start.date().isoformat(), end.date().isoformat()) == ("2026-01-01", "2027-01-01")


async def test_cost_per_period_and_forecasts(hass: HomeAssistant, device, freezer) -> None:
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to("2026-11-10 12:00:00+01:00")  # 10 November: 30 days in the month
    entry = await setup_with_sensors(hass)
    sensors = {e.entity_id: e for e in hass.data["sensor"].entities}
    total = sensors[eid(hass, "sensor", "EnergieGesamt")]
    cost = sensors[eid(hass, "sensor", "Stromkosten")]
    total._kwh, cost._kwh = 0.0, 0.0

    async def refresh() -> None:
        entry.runtime_data.async_set_updated_data(dict(entry.runtime_data.data))
        await hass.async_block_till_done()

    await refresh()  # counting starts now (12:00), within the month
    month = eid(hass, "sensor", "EnergieGesamtMonatPrognose")
    assert hass.states.get(month).state == "unknown"  # not enough counted yet
    # one day later: 10 kWh and 3 € so far -> 30 days in November: 300 kWh, 90 €
    freezer.move_to("2026-11-11 12:00:00+01:00")
    total._kwh, cost._kwh = 10.0, 3.0
    await refresh()
    assert float(hass.states.get(month).state) == 300.0
    assert float(hass.states.get(eid(hass, "sensor", "StromkostenMonatPrognose")).state) == 90.0
    assert hass.states.get(month).attributes["counted_days"] == 1.0
    assert hass.states.get(eid(hass, "sensor", "EnergieGesamtJahrPrognose")).state == "unknown"  # a year needs 3 days
    # the cost of today: money, a total with its reset at midnight
    today = hass.states.get(eid(hass, "sensor", "StromkostenHeute"))
    assert today.attributes["device_class"] == "monetary" and today.attributes["state_class"] == "total"
    assert today.attributes["last_reset"] == "2026-11-11T00:00:00+01:00"
    assert float(hass.states.get(eid(hass, "sensor", "StromkostenMonat")).state) == 3.0
    # only the whole unit has a forecast
    from homeassistant.helpers import entity_registry as er

    assert er.async_get(hass).async_get_entity_id("sensor", "proxon_control", "abc123_EnergieKompressorMonatPrognose") is None


# ---------------- fixed electricity price ----------------
async def test_fixed_price_for_the_cost(hass: HomeAssistant, device) -> None:
    """Without a price sensor a fixed price (ct/kWh) from the options counts; a price sensor goes first."""
    from .test_integration import make_entry

    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"fixed_price": 32.5})
    await setup(hass, entry)
    sensor = eid(hass, "sensor", "Stromkosten")
    assert eid(hass, "sensor", "StromkostenMonatPrognose")
    assert entry.runtime_data.energy.price_ct() == 32.5
    cost = next(e for e in hass.data["sensor"].entities if e.entity_id == sensor)
    base = time.monotonic() + 100_000
    for minute in range(61):  # one hour at 531.8 W
        cost._add(base + minute * 60)
    assert round(cost.native_value, 3) == round(0.5318 * 0.325, 3)
    # with a price sensor too, the sensor counts
    hass.states.async_set("sensor.preis", "0.20", {"unit_of_measurement": "€/kWh"})
    hass.config_entries.async_update_entry(entry, options={"fixed_price": 32.5, "price_sensor": "sensor.preis"})
    await hass.async_block_till_done()
    assert entry.runtime_data.energy.price_ct() == 20.0


async def test_fixed_price_in_the_options(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "fixed_price" in {str(k) for k in result["data_schema"].schema}
    await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 10, "fixed_price": 29.9})
    await hass.async_block_till_done()
    assert entry.options == {"scan_interval": 10, "fixed_price": 29.9}
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 10, "fixed_price": 0})
    await hass.async_block_till_done()
    assert "fixed_price" not in entry.options  # 0: no fixed price


# ---------------- year forecast by the season ----------------
def test_heating_weight() -> None:
    from homeassistant.util import dt as dt_util

    from custom_components.proxon_control.sensor import HEATING_SHARE, heating_weight

    tz = dt_util.get_default_time_zone()
    assert round(sum(HEATING_SHARE), 6) == 1.0
    assert round(heating_weight(datetime(2026, 1, 1, tzinfo=tz), datetime(2027, 1, 1, tzinfo=tz)), 6) == 1.0
    assert round(heating_weight(datetime(2026, 11, 10, tzinfo=tz), datetime(2026, 11, 14, tzinfo=tz)), 6) == round(0.125 * 4 / 30, 6)
    # four days in January weigh far more than four days in July
    assert heating_weight(datetime(2026, 1, 10, tzinfo=tz), datetime(2026, 1, 14, tzinfo=tz)) > 30 * heating_weight(
        datetime(2026, 7, 10, tzinfo=tz), datetime(2026, 7, 14, tzinfo=tz))


async def test_year_forecast_by_the_season(hass: HomeAssistant, device, freezer) -> None:
    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to("2026-11-10 00:00:00+01:00")
    entry = await setup_with_sensors(hass)  # price 0.30 €/kWh
    sensors = {e.entity_id: e for e in hass.data["sensor"].entities}
    total, comp, vent, cost = (sensors[eid(hass, "sensor", k)] for k in ("EnergieGesamt", "EnergieKompressor", "EnergieLueftung", "Stromkosten"))
    for s in (total, comp, vent, cost):
        s._kwh = 0.0

    async def refresh() -> None:
        entry.runtime_data.async_set_updated_data(dict(entry.runtime_data.data))
        await hass.async_block_till_done()

    await refresh()  # counting starts on 10 November
    # four days: the compressor 10 kWh a day, ventilation and electronics 1 kWh a day
    freezer.move_to("2026-11-14 00:00:00+01:00")
    comp._kwh, vent._kwh = 40.0, 4.0
    total._kwh, cost._kwh = 44.0, 13.2
    await refresh()
    year = hass.states.get(eid(hass, "sensor", "EnergieGesamtJahrPrognose"))
    # compressor: 40 kWh in 4/30 of November (12.5 % of a year's heating) -> 2400 kWh; ventilation 1 kWh a day -> 365 kWh
    assert float(year.state) == 2765.0 and year.attributes["method"] == "seasonal"
    # the cost at the average price so far (0.30 €/kWh)
    assert float(hass.states.get(eid(hass, "sensor", "StromkostenJahrPrognose")).state) == 829.5
    # the month stays linear: 44 kWh in 4 days -> 330 kWh in November
    assert float(hass.states.get(eid(hass, "sensor", "EnergieGesamtMonatPrognose")).state) == 330.0
