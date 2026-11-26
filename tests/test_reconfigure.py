"""Reconfigure: change how the unit is reached without removing it (Device ID + password, or the bridge)."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_control.api import AuthError
from custom_components.proxon_control.const import DOMAIN

from .test_integration import setup


async def test_reconfigure_keeps_the_password_and_sets_the_address(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    hass.config_entries.async_update_entry(entry, options={**entry.options, "local_host": "192.168.1.9", "scan_interval": 10})
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "reconfigure"
    assert result["description_placeholders"] == {"device_id": "abc123"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"mode": "auto", "local_host": " 192.168.1.20 "})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "reconfigure_successful"
    assert entry.data["password"] == "secret" and entry.data["local_host"] == "192.168.1.20" and entry.data["mode"] == "auto"
    assert entry.options == {"scan_interval": 10}  # the old address in the options no longer hides the new one


async def test_reconfigure_with_a_new_password_tests_it_first(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    result = await entry.start_reconfigure_flow(hass)
    with patch("custom_components.proxon_control.api.HybridApi.test", side_effect=AuthError("bad")):
        bad = await hass.config_entries.flow.async_configure(result["flow_id"], {"password": "wrong", "mode": "auto"})
    assert bad["type"] is FlowResultType.FORM and bad["errors"] == {"base": "invalid_auth"}
    assert entry.data["password"] == "secret"
    done = await hass.config_entries.flow.async_configure(bad["flow_id"], {"password": "new-secret", "mode": "auto", "local_host": ""})
    assert done["reason"] == "reconfigure_successful" and entry.data["password"] == "new-secret" and "local_host" not in entry.data


async def test_reconfigure_the_bridge(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"connection": "bridge", "host": "old.local", "port": 8765}, unique_id="bridge-old.local-8765")
    entry.add_to_hass(hass)
    other = MockConfigEntry(domain=DOMAIN, data={"connection": "bridge", "host": "taken.local", "port": 8765}, unique_id="bridge-taken.local-8765")
    other.add_to_hass(hass)
    with patch("custom_components.proxon_control.async_setup_entry", return_value=True), \
         patch("custom_components.proxon_control.config_flow.BridgeApi.test"):
        result = await entry.start_reconfigure_flow(hass)
        assert result["type"] is FlowResultType.FORM and result["step_id"] == "reconfigure_bridge"
        taken = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "taken.local", "port": 8765})
        assert taken["type"] is FlowResultType.ABORT and taken["reason"] == "already_configured"
        result = await entry.start_reconfigure_flow(hass)
        done = await hass.config_entries.flow.async_configure(result["flow_id"], {"host": "new.local", "port": 9000, "token": "abc"})
    assert done["reason"] == "reconfigure_successful"
    assert entry.data == {"connection": "bridge", "host": "new.local", "port": 9000, "token": "abc"} and entry.unique_id == "bridge-new.local-9000"
