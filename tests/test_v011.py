"""Version 0.11: automatic summer/winter, runtime statistics, night setback, hot-water module faults by name."""
from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import issue_registry as ir
import pytest

from custom_components.proxon_control import comfort as C
from custom_components.proxon_control import registers as R
from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.runtime import RuntimeTracker

from .test_integration import call, eid, setup
from .test_v09 import raw_key, state, writes

T0 = datetime(2026, 11, 9, 0, 0)


def feed(st: C.SeasonState, temps: list[float], start: datetime = T0, step: timedelta = timedelta(minutes=30), mode: int = 2) -> datetime:
    now = start
    for t in temps:
        C.decide_season(now, C.SeasonSettings(), st, mode=mode, outside=t, holiday=False)
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
    now = feed(st, [5.0] * 10, now, mode=1)  # cold, but the average is still high and the last switch recent
    assert C.decide_season(now, s, st, mode=1, outside=5.0, holiday=False)[:2] == (None, C.S_SUMMER)
    now = feed(st, [5.0] * 90, now, mode=1)  # two cold days
    assert C.decide_season(now, s, st, mode=1, outside=5.0, holiday=False)[0] == C.MODE_WINTER
    # between the limits: nothing changes
    st2 = C.SeasonState()
    now = feed(st2, [15.5] * 30)
    assert C.decide_season(now, s, st2, mode=2, outside=15.5, holiday=False)[:2] == (None, C.S_WINTER)


def test_season_keeps_a_mode_set_by_hand_for_twelve_hours() -> None:
    st, s = C.SeasonState(), C.SeasonSettings(on=True)
    now = feed(st, [20.0] * 30, mode=1)  # warm and in Summer
    assert C.decide_season(now, s, st, mode=1, outside=20.0, holiday=False)[:2] == (None, C.S_SUMMER)
    # set to Winter by hand: kept although the average says summer
    assert C.decide_season(now, s, st, mode=2, outside=20.0, holiday=False)[:2] == (None, C.S_WINTER)
    later = now + timedelta(hours=11)
    assert C.decide_season(later, s, st, mode=2, outside=20.0, holiday=False)[0] is None
    assert C.decide_season(now + timedelta(hours=13), s, st, mode=2, outside=20.0, holiday=False)[0] == C.MODE_SUMMER


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
    device.raw[raw_key("Fehlerwort3_61")] = 1 << 1
    entry = await setup(hass)
    fault = state(hass, "binary_sensor", "Stoerung")
    assert fault.state == "on" and fault.attributes["hot_water_module"] == ["Low pressure"]
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"unit_fault_{entry.entry_id}")
    assert "hot-water module: Low pressure" in issue.translation_placeholders["words"]


async def test_t300_filter_reminder_is_no_fault(hass: HomeAssistant, device) -> None:
    device.raw[raw_key("Fehlerwort3_61")] = 1 << 14
    await setup(hass)
    fault = state(hass, "binary_sensor", "Stoerung")
    assert fault.state == "off" and fault.attributes["hot_water_module"] == ["Change filter"]  # shown, but no fault
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "SollWassertemperatur"), value=45)  # not blocked


# ---------------- 0.12: room heat demand, heating elements, device type, compressor power ----------------
def test_room_demand_and_heating() -> None:
    v = {"NBE1LED": 6.0, "NBE1PTC": 1.0, "NBE2LED": 6.0, "NBE2PTC": 0.0, "NBE3LED": 5.0, "NBE3PTC": 1.0}
    assert R.room_demand(v, 1) == "too_cold" and R.room_heating(v, 1)
    assert R.room_demand(v, 2) == "too_cold" and not R.room_heating(v, 2)  # element not released
    assert R.room_demand(v, 3) == "at_target" and not R.room_heating(v, 3)
    # central panel: no LED level, temperature against target
    assert R.room_demand({"NBE0Temperatur": 20.0, "NBE0MittelTemperatur": 22.0}, 0) == "too_cold"
    assert R.room_demand({"NBE0Temperatur": 22.1, "NBE0MittelTemperatur": 22.0}, 0) == "at_target"
    assert R.heating_channels({"HeizmodulRelais": float(0b1000000101)}) == ["K1", "K3", "K10"]


async def test_room_heat_demand_in_the_thermostat(hass: HomeAssistant, device) -> None:
    await setup(hass)
    bedroom = hass.states.get(eid(hass, "climate", "NBE1Thermostat"))  # LED 6, element released
    assert bedroom.attributes["heat_demand"] == "too_cold" and bedroom.attributes["heating_element_heats"] is True
    assert bedroom.attributes["hvac_action"] == "heating"
    bath = hass.states.get(eid(hass, "climate", "NBE4Thermostat"))  # LED 5
    assert bath.attributes["heat_demand"] == "at_target" and bath.attributes["heating_element_heats"] is False
    elements = state(hass, "binary_sensor", "HeizmodulRelais")
    assert elements.state == "on" and elements.attributes["active_channels"] == ["K3", "K10"]
    assert state(hass, "sensor", "KompressorLeistung").state == "65.0"
    assert state(hass, "sensor", "GeraeteTyp").state == "heating_cooling"


async def test_no_cooling_switch_on_heating_only_units(hass: HomeAssistant, device) -> None:
    from homeassistant.helpers import entity_registry as er

    device.raw[raw_key("GeraeteTyp")] = 0
    await setup(hass)
    assert er.async_get(hass).async_get_entity_id("switch", DOMAIN, "abc123_GlobalKuehlungFreigabe") is None
    assert state(hass, "sensor", "GeraeteTyp").state == "heating_only"


# ---------------- review fixes (0.12.1) ----------------
def test_copy_takes_over_a_night_phase_from_the_unit() -> None:
    from custom_components.proxon_control.schedule import Phase, plan_day

    monday = [Phase(361, 1260, 3), Phase(1261, 360, 2), Phase(421, 1275, 0)]
    tuesday = [Phase(420, 1260, 3), Phase(1261, 419, 2), Phase(360, 419, 0)]
    now = datetime(2026, 11, 9, 10, 0)
    writes = plan_day(1, tuesday, monday, now, allow_overnight=True)
    assert ("ZP1_1_end_m", 0) in writes and ("ZP1_1_level", 2) in writes  # night phase now ends 06:00, switched on again


def test_home_network_is_the_last_resort_while_paused() -> None:
    from custom_components.proxon_control import api as A

    class Way:
        def __init__(self, error=None):
            self.error, self.calls = error, 0

        def read(self):
            self.calls += 1
            if self.error:
                raise self.error
            return {"x": 1.0}

    local, cloud = Way(A.ProxonError("blip")), Way()
    api = A.HybridApi(A.MODE_AUTO, local, cloud)
    assert api.read()[A.PATH_KEY] == "cloud"  # local failed once: paused
    cloud.error, local.error = A.ProxonError("internet down"), None
    assert api.read()[A.PATH_KEY] == "local" and local.calls == 2  # cloud down too: home network tried anyway


def test_room_names_are_read_only_now_and_then() -> None:
    from .conftest import FakeDevice

    dev = FakeDevice()
    asked: list[int] = []

    class Client:
        def invoke(self, query, request):
            asked.append(len(request["list"]))
            return dev.invoke(query, request)

    cache = R.NameCache()
    first = cache.read(Client())
    sizes_first = sum(asked)
    asked.clear()
    second = cache.read(Client())
    assert sum(asked) < sizes_first  # names left out
    assert second["NBE1name"] == first["NBE1name"] == "Schlafzimmer"  # but still there


def test_key_file_is_private(tmp_path) -> None:
    import os
    from unittest.mock import MagicMock, patch

    from custom_components.proxon_control import local_cert as LC

    cert = "-----BEGIN CERTIFICATE-----\nAAAA\n-----END CERTIFICATE-----\n"
    resp = MagicMock()
    resp.__enter__.return_value.read.return_value = ("0\nOK\n" + cert).encode()
    with patch.object(LC.urllib.request, "urlopen", return_value=resp):
        LC.fetch(str(tmp_path), "abc123", "pw")
    assert os.stat(tmp_path / "local" / "abc123" / "key.pem").st_mode & 0o777 == 0o600
