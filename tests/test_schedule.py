"""Weekly ventilation schedule: the unit's rules, the day sensors and the two actions."""
from __future__ import annotations

from datetime import datetime

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.proxon_control import registers as R
from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.schedule import Phase, ScheduleError, plan_day, read_day, summary, unit_clock, validate_day

from .test_integration import eid, setup

MON_10 = datetime(2026, 11, 9, 10, 0)  # a Monday
DAY = [Phase(6 * 60, 8 * 60, 2), Phase(17 * 60, 22 * 60, 3), Phase(0, 0, 0)]


def addr(day: int, phase: int, field: int) -> int:
    return 1026 + 2 * R.schedule_index(day, phase, field)


# ---------------- rules ----------------
def test_schedule_addresses_match_the_app() -> None:
    g = R.BY_KEY["ZP1_0_start_h"]
    assert (g.read, g.write) == ((5, 16), (0, 1056))
    g = R.BY_KEY["ZP6_2_level"]
    assert (g.read, g.write) == ((5, 105), (0, 1234))


def test_read_and_summary() -> None:
    values = {R.schedule_key(0, p, f): v for p, fs in enumerate(((6, 0, 8, 0, 2), (17, 30, 22, 0, 3), (0, 0, 0, 0, 0))) for f, v in enumerate(fs)}
    phases = read_day(values, 0)
    assert phases == [Phase(360, 480, 2), Phase(1050, 1320, 3), Phase(0, 0, 0)]
    assert summary(phases, "Stufe", "Aus") == "06:00–08:00 Stufe 2 · 17:30–22:00 Stufe 3"
    assert summary([Phase(0, 0, 0)] * 3, "Stufe", "Aus") == "Aus"
    assert read_day({}, 0) is None


def test_unit_clock() -> None:
    assert unit_clock({"UhrMinute": 5, "UhrStunde": 10, "UhrTag": 9, "UhrMonat": 11, "UhrJahr": 26}) == datetime(2026, 11, 9, 10, 5)
    assert unit_clock({"UhrMinute": 5}) is None


@pytest.mark.parametrize(
    ("phases", "key"),
    [
        ([Phase(480, 360, 2), Phase(0, 0, 0), Phase(0, 0, 0)], "schedule_end_before_start"),
        ([Phase(360, 480, 2), Phase(420, 600, 1), Phase(0, 0, 0)], "schedule_overlap"),
        ([Phase(360, 480, 2), Phase(480, 600, 1), Phase(0, 0, 0)], "schedule_overlap"),  # touching boundary
    ],
)
def test_invalid_days(phases, key) -> None:
    with pytest.raises(ScheduleError) as err:
        validate_day(phases)
    assert err.value.key == key


def test_inactive_phases_dont_count() -> None:
    validate_day([Phase(360, 480, 2), Phase(400, 300, 0), Phase(0, 0, 0)])


def test_future_phase_is_switched_off_moved_and_switched_on_again() -> None:
    new = [Phase(7 * 60, 9 * 60, 2), DAY[1], DAY[2]]
    writes = plan_day(1, DAY, new, MON_10)  # Tuesday
    assert writes == [("ZP1_0_level", 0), ("ZP1_0_start_h", 7), ("ZP1_0_end_h", 9), ("ZP1_0_level", 2)]


def test_level_only_change_is_one_write() -> None:
    assert plan_day(1, DAY, [Phase(360, 480, 4), DAY[1], DAY[2]], MON_10) == [("ZP1_0_level", 4)]


def test_switching_a_phase_on_and_off() -> None:
    new = [DAY[0], DAY[1], Phase(23 * 60, 23 * 60 + 30, 1)]
    assert plan_day(0, DAY, new, MON_10) == [("ZP0_2_start_h", 23), ("ZP0_2_end_h", 23), ("ZP0_2_end_m", 30), ("ZP0_2_level", 1)]
    assert plan_day(0, DAY, [DAY[0], Phase(17 * 60, 22 * 60, 0), DAY[2]], MON_10) == [("ZP0_1_level", 0)]


def test_times_only_two_hours_ahead() -> None:
    with pytest.raises(ScheduleError) as err:  # 11:00 is only one hour away
        plan_day(0, DAY, [DAY[0], Phase(11 * 60, 22 * 60, 3), DAY[2]], MON_10)
    assert err.value.key == "schedule_too_soon"
    plan_day(0, DAY, [DAY[0], Phase(18 * 60, 22 * 60, 3), DAY[2]], MON_10)  # 17:00 -> 18:00 is fine
    # over the end of the week: Sunday 23:00, a Monday phase at 00:30 is 90 minutes away
    with pytest.raises(ScheduleError):
        plan_day(0, DAY, [Phase(30, 120, 1), DAY[1], DAY[2]], datetime(2026, 11, 15, 23, 0))


def test_running_phase_only_changes_its_level() -> None:
    at_7 = datetime(2026, 11, 9, 7, 0)
    assert plan_day(0, DAY, [Phase(360, 480, 3), DAY[1], DAY[2]], at_7) == [("ZP0_0_level", 3)]
    for new in ([Phase(360, 500, 2), DAY[1], DAY[2]], [Phase(360, 480, 0), DAY[1], DAY[2]]):
        with pytest.raises(ScheduleError) as err:
            plan_day(0, DAY, new, at_7)
        assert err.value.key == "schedule_running"
    with pytest.raises(ScheduleError) as err:  # five minutes before its end
        plan_day(0, DAY, [Phase(360, 480, 3), DAY[1], DAY[2]], datetime(2026, 11, 9, 7, 55))
    assert err.value.key == "schedule_running_margin"


def test_times_need_the_unit_clock() -> None:
    with pytest.raises(ScheduleError) as err:
        plan_day(1, DAY, [Phase(420, 540, 2), DAY[1], DAY[2]], None)
    assert err.value.key == "schedule_clock_unknown"
    assert plan_day(1, DAY, [Phase(360, 480, 1), DAY[1], DAY[2]], None) == [("ZP1_0_level", 1)]


# ---------------- in Home Assistant ----------------
async def test_day_sensors_and_clock(hass: HomeAssistant, device) -> None:
    await setup(hass)
    tuesday = hass.states.get(eid(hass, "sensor", "Zeitprogramm1"))
    assert tuesday.state == "06:00–08:00 level 2 · 17:00–22:00 level 3"
    assert tuesday.attributes["phase_1"] == {"start": "06:00", "end": "08:00", "level": 2, "active": True}
    assert tuesday.attributes["phase_3"]["active"] is False
    assert "Tuesday" in tuesday.attributes["friendly_name"]
    assert hass.states.get(eid(hass, "binary_sensor", "ZeitprogrammAktiv")).state == "on"
    clock = hass.states.get(eid(hass, "sensor", "Uhr"))
    assert clock.state.startswith("2026-11-09T")


async def test_schedule_is_read_every_few_minutes_only(hass: HomeAssistant, device) -> None:
    reads = []
    invoke = device.invoke

    def recording(query, request):
        if query == R.QUERY_SET_READ and any(i["obj"] == 5 and 1 <= i["address"] <= 105 for i in request["list"]):
            reads.append(1)
        return invoke(query, request)

    device.invoke = recording
    entry = await setup(hass)
    assert len(reads) == 2  # 105 values in two queries
    await entry.runtime_data.async_refresh()
    assert len(reads) == 2  # not again with the next query
    assert hass.states.get(eid(hass, "sensor", "Zeitprogramm0")).state != "unavailable"


async def test_set_phase_action(hass: HomeAssistant, device) -> None:
    await setup(hass)
    await hass.services.async_call(
        DOMAIN, "set_schedule_phase", {"day": "tuesday", "phase": 1, "start": "07:00:00", "end": "09:00:00", "level": 2}, blocking=True
    )
    assert [(w["address"], w["value"]) for w in device.writes] == [
        (addr(1, 0, 4), 0), (addr(1, 0, 0), 7), (addr(1, 0, 2), 9), (addr(1, 0, 4), 2),
    ]
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "sensor", "Zeitprogramm1")).state.startswith("07:00–09:00 level 2")


async def test_set_phase_action_checks_the_rules(hass: HomeAssistant, device) -> None:
    await setup(hass)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, "set_schedule_phase", {"day": "tuesday", "phase": 3, "start": "07:00:00", "end": "09:00:00", "level": 1}, blocking=True
        )
    assert err.value.translation_key == "schedule_overlap"
    assert err.value.translation_placeholders["day"] == "Tuesday"
    assert device.writes == []


async def test_copy_day_action(hass: HomeAssistant, device) -> None:
    device.raw[(True, 5, 1 + R.schedule_index(0, 0, 0))] = 5  # Monday: first phase from 05:00
    await setup(hass)
    await hass.services.async_call(DOMAIN, "copy_schedule_day", {"source_day": "monday", "target_days": ["tuesday", "wednesday", "monday"]}, blocking=True)
    assert [(w["address"], w["value"]) for w in device.writes] == [
        (addr(1, 0, 4), 0), (addr(1, 0, 0), 5), (addr(1, 0, 4), 2),
        (addr(2, 0, 4), 0), (addr(2, 0, 0), 5), (addr(2, 0, 4), 2),
    ]
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "sensor", "Zeitprogramm2")).state.startswith("05:00–08:00")


async def test_copy_day_writes_nothing_if_one_day_cannot_take_it(hass: HomeAssistant, device) -> None:
    device.raw[(True, 5, 1 + R.schedule_index(0, 0, 0))] = 5
    device.raw[(True, 3, 59)] = 2  # the unit's clock: Tuesday 05:30
    device.raw[(True, 3, 58)] = 5
    device.raw[(True, 3, 57)] = 30
    device.raw[(True, 3, 60)] = 10
    await setup(hass)
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(DOMAIN, "copy_schedule_day", {"source_day": "monday", "target_days": ["wednesday", "tuesday"]}, blocking=True)
    assert err.value.translation_key == "schedule_too_soon"
    assert device.writes == []
