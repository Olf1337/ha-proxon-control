"""Version 0.5: fault and filter notices, holiday mode, response time, bridge access key, automation blueprints."""
from __future__ import annotations

from datetime import timedelta
import shutil
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import issue_registry as ir
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

from custom_components.proxon_control import registers as R
from custom_components.proxon_control.api import BridgeApi, TokenError
from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.sensor import connection_path

from .test_integration import call, eid, setup

ROOT = Path(__file__).resolve().parent.parent


def writes(device) -> list[tuple[int, int, int]]:
    return [(w["obj"], w["address"], w["value"]) for w in device.writes]


# ---------------- fault and filter notices ----------------
async def test_filter_notice_comes_and_goes(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)  # 120 h filter time left
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"filter_change_{entry.entry_id}")
    assert issue is not None and issue.translation_placeholders == {"days": "5"}
    coordinator = entry.runtime_data
    coordinator.async_set_updated_data({**coordinator.data, "FilterRestStunden": 2000.0})
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"filter_change_{entry.entry_id}") is None


async def test_fault_sensor_and_notice(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    fault = eid(hass, "binary_sensor", "Stoerung")
    assert hass.states.get(fault).state == "off"
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"unit_fault_{entry.entry_id}") is None
    coordinator = entry.runtime_data
    # a known harmless notice bit alone is not a fault
    coordinator.async_set_updated_data({**coordinator.data, "Fehlerwort0_50": 64.0})
    await hass.async_block_till_done()
    assert hass.states.get(fault).state == "off"
    coordinator.async_set_updated_data({**coordinator.data, "Fehlerwort1_7": 2.0})
    await hass.async_block_till_done()
    state = hass.states.get(fault)
    assert state.state == "on" and state.attributes["Fehlerwort1_7"] == "0x0002"
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"unit_fault_{entry.entry_id}")
    assert issue.severity is ir.IssueSeverity.ERROR and "Fehlerwort1_7 = 0x0002" in issue.translation_placeholders["words"]
    coordinator.async_set_updated_data({**coordinator.data, "Fehlerwort1_7": 0.0})
    await hass.async_block_till_done()
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"unit_fault_{entry.entry_id}") is None


async def test_notices_are_removed_with_the_integration(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, f"filter_change_{entry.entry_id}") is None


# ---------------- holiday mode ----------------
async def test_holiday_mode_on_and_off_restores_everything(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    entry.runtime_data.holiday.restore_delay = 0
    holiday = eid(hass, "switch", "Urlaubsmodus")
    assert hass.states.get(holiday).state == "off"
    await call(hass, "switch", "turn_on", entity_id=holiday)
    assert writes(device) == [
        (0, 54, 1), (0, 150, 1800), (0, 384, 0),  # level 1, living room 18 °C, its heating element off
        (0, 436, 65533), (0, 516, 0), (0, 442, 65533), (0, 522, 0),  # rooms 1 and 4: offset -3, heating element off
        (1, 2, 0),  # hot-water heat pump off, last
    ]
    state = hass.states.get(holiday)
    assert state.state == "on" and state.attributes["saved_values"]["Luefterstufe"] == 2.0
    device.writes.clear()
    await call(hass, "switch", "turn_off", entity_id=holiday)
    assert writes(device) == [
        (1, 2, 1), (1, 1, 0),  # hot-water heat pump first, then the immersion heater
        (0, 54, 2), (0, 150, 2000), (0, 384, 0), (0, 436, 2), (0, 516, 1), (0, 442, 65535), (0, 522, 1),
    ]
    assert hass.states.get(holiday).state == "off"
    assert float(hass.states.get(eid(hass, "number", "Luefterstufe")).state) == 2


async def test_holiday_mode_survives_a_restart(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "Urlaubsmodus"))
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "switch", "Urlaubsmodus")).state == "on"
    assert entry.runtime_data.holiday.saved["NBE1OffsetTemperatur"] == 2.0


# ---------------- response time / connection path ----------------
def test_connection_path_from_response_time() -> None:
    assert connection_path(4) == "local"
    assert connection_path(35) == "internet"
    assert connection_path(140) == "relay"


async def test_response_time_sensors(hass: HomeAssistant, device) -> None:
    await setup(hass)
    assert float(hass.states.get(eid(hass, "sensor", "Antwortzeit")).state) < 15
    path = hass.states.get(eid(hass, "sensor", "Antwortzeit_path"))
    assert path.state == "local" and path.attributes["estimated"] is True


# ---------------- bridge with access key ----------------
@pytest.fixture
def bridge_with_key(device, socket_enabled):
    sys.path.insert(0, str(ROOT / "proxon_bridge"))
    try:
        import bridge as addon  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    b = addon.Bridge("abc123", "pw")
    b.client = device
    b.poll()
    server = ThreadingHTTPServer(("127.0.0.1", 0), addon.make_handler(b, "geheim"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def test_bridge_access_key(bridge_with_key) -> None:
    port = bridge_with_key
    assert BridgeApi("127.0.0.1", port, "geheim").read()["Luefterstufe"] == 2.0
    for key in (None, "falsch"):
        with pytest.raises(TokenError):
            BridgeApi("127.0.0.1", port, key).read()


async def test_bridge_dialog_with_access_key(hass: HomeAssistant, bridge_with_key) -> None:
    port = bridge_with_key
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "bridge"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "127.0.0.1", "port": port, "token": "falsch"})
    assert result["type"] is FlowResultType.FORM and result["errors"] == {"base": "invalid_token"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "127.0.0.1", "port": port, "token": "geheim"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["token"] == "geheim"


def test_bridge_reads_options_from_environment(monkeypatch, tmp_path) -> None:
    sys.path.insert(0, str(ROOT / "proxon_bridge"))
    try:
        import bridge as addon  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    monkeypatch.setattr(addon, "OPTIONS", str(tmp_path / "missing.json"))
    monkeypatch.setenv("PROXON_DEVICE_ID", "abc")
    monkeypatch.setenv("PROXON_PASSWORD", "pw")
    monkeypatch.setenv("PROXON_TOKEN", "key")
    assert addon.load_options() == {"device_id": "abc", "password": "pw", "poll_seconds": 10, "token": "key"}


# ---------------- automation blueprints ----------------
@pytest.fixture
def blueprints(hass: HomeAssistant, tmp_path):
    hass.config.config_dir = str(tmp_path)
    shutil.copytree(ROOT / "blueprints", tmp_path / "blueprints")


async def test_humidity_blueprint_switches_on_boost(hass: HomeAssistant, device, blueprints) -> None:
    await setup(hass)
    boost = eid(hass, "switch", "Intensivlueftung")
    hass.states.async_set("sensor.bad_feuchte", "50", {"device_class": "humidity", "unit_of_measurement": "%"})
    assert await async_setup_component(hass, "automation", {"automation": [{"use_blueprint": {
        "path": "proxon_control/humidity_boost.yaml",
        "input": {"humidity_sensor": "sensor.bad_feuchte", "threshold": 70, "boost_switch": boost},
    }}]})
    await hass.async_block_till_done()
    hass.states.async_set("sensor.bad_feuchte", "82", {"device_class": "humidity", "unit_of_measurement": "%"})
    await hass.async_block_till_done()
    assert device.writes == []  # not yet: has to stay above the limit for 2 minutes
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=3))
    await hass.async_block_till_done()
    assert writes(device)[-1] == (0, 380, 1)


async def test_other_blueprints_load(hass: HomeAssistant, device, blueprints) -> None:
    await setup(hass)
    hass.states.async_set("zone.home", "1")
    assert await async_setup_component(hass, "automation", {"automation": [
        {"use_blueprint": {"path": "proxon_control/filter_reminder.yaml", "input": {
            "filter_sensor": eid(hass, "binary_sensor", "FilterRestStunden_warning"),
            "reminder": [{"action": "persistent_notification.create", "data": {"message": "Filter!"}}],
        }}},
        {"use_blueprint": {"path": "proxon_control/away_holiday.yaml", "input": {
            "holiday_switch": eid(hass, "switch", "Urlaubsmodus"),
        }}},
    ]})
    await hass.async_block_till_done()
    autos = hass.states.async_entity_ids("automation")
    assert len(autos) == 2 and all(hass.states.get(a).state == "on" for a in autos)
    await hass.services.async_call("automation", "turn_off", {"entity_id": autos}, blocking=True)  # detach the daily timer
