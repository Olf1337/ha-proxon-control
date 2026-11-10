"""Proxon Control: the ventilation / heat unit as a Home Assistant integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .api import BridgeApi, DirectApi
from .const import (
    CONF_CONNECTION,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONNECTION_BRIDGE,
    DEFAULT_PORT,
    DOMAIN,
)
from .coordinator import ProxonCoordinator

PLATFORMS = [Platform.SENSOR, Platform.SELECT, Platform.NUMBER, Platform.SWITCH, Platform.BINARY_SENSOR]

type ProxonConfigEntry = ConfigEntry[ProxonCoordinator]


def make_api(hass: HomeAssistant, data: dict) -> DirectApi | BridgeApi:
    if data.get(CONF_CONNECTION) == CONNECTION_BRIDGE:
        return BridgeApi(data[CONF_HOST], data.get(CONF_PORT, DEFAULT_PORT))
    return DirectApi(data[CONF_DEVICE_ID], data[CONF_PASSWORD], hass.config.path(DOMAIN))


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    coordinator = ProxonCoordinator(hass, entry, make_api(hass, dict(entry.data)))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await hass.async_add_executor_job(entry.runtime_data.api.close)
    return ok
