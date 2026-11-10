"""Proxon Control: the ventilation / heat unit as a Home Assistant integration."""
from __future__ import annotations

import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

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

PLATFORMS = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.WATER_HEATER,
]

type ProxonConfigEntry = ConfigEntry[ProxonCoordinator]


def make_api(hass: HomeAssistant, data: dict) -> DirectApi | BridgeApi:
    if data.get(CONF_CONNECTION) == CONNECTION_BRIDGE:
        return BridgeApi(data[CONF_HOST], data.get(CONF_PORT, DEFAULT_PORT))
    return DirectApi(data[CONF_DEVICE_ID], data[CONF_PASSWORD], hass.config.path(DOMAIN))


# entities of version 0.1.x that the room thermostats replace (room target numbers, room heating element switches)
_LEGACY = re.compile(r"_(NBE0MittelTemperatur|NBE[1-4]Ziel|NBE[0-4]PTC)$")


def _remove_legacy_room_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(reg, entry.entry_id):
        if ent.domain in ("number", "switch") and _LEGACY.search(ent.unique_id):
            reg.async_remove(ent.entity_id)


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    coordinator = ProxonCoordinator(hass, entry, make_api(hass, dict(entry.data)))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    _remove_legacy_room_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        await hass.async_add_executor_job(entry.runtime_data.api.close)
    return ok
