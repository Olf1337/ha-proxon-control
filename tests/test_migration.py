"""Saved settings across versions: older ones are brought up to date, ones from a newer version are left alone."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.proxon_control.config_flow import ProxonConfigFlow
from custom_components.proxon_control.const import DOMAIN, ENTRY_MINOR_VERSION, ENTRY_VERSION

from .test_integration import DATA


def entry(version: int, minor: int) -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="abc123", title="Proxon abc123", version=version, minor_version=minor)


def test_flow_saves_the_current_layout() -> None:
    assert (ProxonConfigFlow.VERSION, ProxonConfigFlow.MINOR_VERSION) == (ENTRY_VERSION, ENTRY_MINOR_VERSION)


async def test_current_settings_load_unchanged(hass: HomeAssistant, device) -> None:
    e = entry(ENTRY_VERSION, ENTRY_MINOR_VERSION)
    e.add_to_hass(hass)
    assert await hass.config_entries.async_setup(e.entry_id)
    assert e.state is ConfigEntryState.LOADED and (e.version, e.minor_version) == (ENTRY_VERSION, ENTRY_MINOR_VERSION)
    assert dict(e.data) == DATA


async def test_older_minor_version_is_brought_up_to_date(hass: HomeAssistant, device) -> None:
    e = entry(ENTRY_VERSION, 0)
    e.add_to_hass(hass)
    assert await hass.config_entries.async_setup(e.entry_id)
    assert e.state is ConfigEntryState.LOADED and (e.version, e.minor_version) == (ENTRY_VERSION, ENTRY_MINOR_VERSION)
    assert dict(e.data) == DATA  # nothing to convert yet


async def test_settings_from_a_newer_version_are_not_loaded(hass: HomeAssistant, device) -> None:
    e = entry(ENTRY_VERSION + 1, 1)
    e.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(e.entry_id)
    assert e.state is ConfigEntryState.MIGRATION_ERROR
    assert e.version == ENTRY_VERSION + 1 and dict(e.data) == DATA  # left as they were
