"""Version 0.11: automatic summer/winter, runtime statistics, night setback, hot-water module faults by name."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import issue_registry as ir

from custom_components.proxon_control import comfort as C, registers as R
from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.runtime import RuntimeTracker

from .test_integration import call, eid, setup
from .test_v09 import raw_key, state, writes

T0 = datetime(2026, 11, 9, 0, 0)


def feed(st: C.SeasonState, temps: list[float], start: datetime = T0, step: timedelta = timedelta(minutes=30)) -> datetime:
    now = start
    for t in temps:
        C.decide_season(now, C.SeasonSettings(), st, mode=2, outside=t, holiday=False)
        now += step
    return now


# ---------------- automatic summer / winter ----------------
def test_season_needs_twelve_hours_of_values() -> None:
    st = C.SeasonState()
    now = feed(st, [20.0] * 20)  # 10 hours
    s = C.SeasonSettings(on=True)
    assert C.decide_season(now, s, st, mode=2, outside=20.0, holiday=False)[:2] == (None, C.S_COLLECTING)
    now = feed(st, [20.0] * 6, now)  # now more than 12 hours
    write, status, details = C.decide_season(now, s, st, mode=2, outside=20.0, holiday=False)
    assert (write, status) == (C.MODE_SUMMER, C.S_SUMMER) and details["average_outdoor"] == 20.0


def test_season_switches_back_only_after_twelve_hours_and_below_the_lower_limit() -> None:
    st, s = C.SeasonState(), C.SeasonSettings(on=True)
    now = feed(st, [20.0] * 30)
    assert C.decide_season(now, s, st, mode=2, outside=20.0, holiday=False)[0] == C.MODE_SUMMER
    now = feed(st, [5.0] * 10, now)  # cold, but the average is still high and the last switch recent
    assert C.decide_season(now, s, st, mode=1, outside=5.0, holiday=False)[:2] == (None, C.S_SUMMER)
    now = feed(st, [5.0] * 90, now)  # two cold days
    assert C.decide_season(now, s, st, mode=1, outside=5.0, holiday=False)[0] == C.MODE_WINTER
    # between the limits: nothing changes
    st2 = C.SeasonState()
    now = feed(st2, [15.5] * 30)
    assert C.decide_season(now, s, st2, mode=2, outside=15.5, holiday=False)[:2] == (None, C.S_WINTER)


def test_season_leaves_other_modes_alone() -> None:
    st, s = C.SeasonState(), C.SeasonSettings(on=True)
    now = feed(st, [25.0] * 30)
    assert C.decide_season(now, s, st, mode=3, outside=25.0, holiday=False)[:2] == (None, C.S_MANUAL)  # ECO Comfort
    assert C.decide_season(now, s, st, mode=2, outside=25.0, holiday=True)[:2] == (None, C.S_BLOCKED)
    assert C.decide_season(now, C.SeasonSettings(on=False), st, mode=2, outside=25.0, holiday=False)[:2] == (None, C.S_OFF)
    assert C.SeasonState.from_dict(st.to_dict()).samples == st.samples  # kept across restarts


async def test_season_entities(hass: HomeAssistant, device) -> None:
    await setup(hass)
    switch = eid(hass, "switch", "SaisonAutomatik")
    assert hass.states.get(switch).state == "off"
    await call(hass, "switch", "turn_on", entity_id=switch)
    assert state(hass, "sensor", "SaisonStatus").state == "other_mode"  # the test unit runs ECO Comfort
    with pytest.raises(ServiceValidationError):
        await call(hass, "number", "set_value", entity_id=eid(hass, "number", "SaisonWinterUnter"), value=20)
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "SaisonWinterUnter"), value=12)
    assert state(hass, "number", "SaisonWinterUnter").state == "12.0"


# ---------------- runtime statistics ----------------
def test_runtime_tracker() -> None:
    tr = RuntimeTracker()
    off, on = {"DrehzahlKompressor": 0.0}, {"DrehzahlKompressor": 3000.0}
    tr.update(on, T0 + timedelta(hours=8))  # already running when counting starts: not a start
    tr.update(on, T0 + timedelta(hours=8, minutes=10))
    tr.update(off, T0 + timedelta(hours=8, minutes=20))
    out = tr.update(on, T0 + timedelta(hours=9))
    assert out["KompressorStartsHeute"] == 1 and out["KompressorLaufzeitHeute"] == round(20 / 60, 2)
    out = tr.update(on, T0 + timedelta(hours=11))  # a gap of 2 hours (Home Assistant stopped): not counted
    assert out["KompressorLaufzeitHeute"] == round(20 / 60, 2)
    # across midnight: the part before midnight counts for the old day
    tr.update(on, T0 + timedelta(hours=23, minutes=55))
    out = tr.update(on, T0 + timedelta(days=1, minutes=5))
    assert out["KompressorLaufzeitHeute"] == round(5 / 60, 2) and out["KompressorStartsHeute"] == 0
    assert out["KompressorStartsGestern"] == 1 and out["KompressorLaufzeitGestern"] == round(25 / 60, 2)
    restored = RuntimeTracker()
    restored.load(tr.dump())
    assert restored.dump() == tr.dump()


async def test_counters_and_runtime_sensors(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    assert state(hass, "sensor", "StundenKompressorHeizen").state == "18000"  # 2-hour steps
    assert state(hass, "sensor", "StundenStufe2").state == "40000"
    assert state(hass, "sensor", "T300StundenKompressor").state == "10000.0"
    assert state(hass, "sensor", "T300StundenHeizstab").state == "1000.0"
    assert state(hass, "sensor", "KompressorStartsHeute").state == "0"
    assert state(hass, "sensor", "HeizstabLaufzeitHeute").state == "0.0"
    issues = ir.async_get(hass)
    coordinator = entry.runtime_data
    coordinator.async_set_updated_data({**coordinator.data, "KompressorStartsHeute": 31.0})
    await hass.async_block_till_done()
    issue = issues.async_get_issue(DOMAIN, f"compressor_cycling_{entry.entry_id}")
    assert issue and issue.translation_placeholders == {"starts": "31"}


# ---------------- night setback ----------------
async def test_night_setback(hass: HomeAssistant, device) -> None:
    await setup(hass)
    assert state(hass, "switch", "NachtabsenkungAktiv").state == "off"
    assert state(hass, "number", "NachtabsenkungTemperatur").state == "19.0"
    assert state(hass, "time", "NachtabsenkungStart").state == "22:00:00"
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "NachtabsenkungAktiv"))
    assert writes(device)[-1] == (0, 1248, 1)
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "NachtabsenkungTemperatur"), value=18)
    assert writes(device)[-1] == (0, 1246, 1800)
    device.writes.clear()
    await call(hass, "time", "set_value", entity_id=eid(hass, "time", "NachtabsenkungStart"), time="21:30:00")
    assert writes(device) == [(0, 1238, 21), (0, 1240, 30)]
    assert state(hass, "time", "NachtabsenkungStart").state == "21:30:00"


# ---------------- hot-water module faults by name ----------------
def test_t300_fault_names() -> None:
    assert R.t300_faults({"Fehlerwort3_61": float(1 << 14 | 1 << 1)}) == ["filter", "low_pressure"]
    assert R.t300_fault_texts({"Fehlerwort3_61": float(1 << 14)}, "de") == ["Filter wechseln"]
    assert R.t300_faults({}) == []


async def test_t300_fault_in_sensor_and_notice(hass: HomeAssistant, device) -> None:
    device.raw[raw_key("Fehlerwort3_61")] = 1 << 14
    entry = await setup(hass)
    fault = state(hass, "binary_sensor", "Stoerung")
    assert fault.state == "on" and fault.attributes["hot_water_module"] == ["Change filter"]
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"unit_fault_{entry.entry_id}")
    assert "hot-water module: Change filter" in issue.translation_placeholders["words"]
