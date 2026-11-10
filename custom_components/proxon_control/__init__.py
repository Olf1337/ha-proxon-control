"""Proxon Control: the ventilation / heat unit as a Home Assistant integration."""
from __future__ import annotations

import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .api import BridgeApi, DirectApi
from .const import (
    CONF_CONNECTION,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TOKEN,
    CONNECTION_BRIDGE,
    DEFAULT_PORT,
    DOMAIN,
)
from .coordinator import ProxonCoordinator
from .comfort_manager import ComfortManager
from .energy_manager import EnergyManager
from .holiday import HolidayMode
from .repairs_watch import remove_issues, update_issues
from .services import async_setup_services

PLATFORMS = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.WATER_HEATER,
    Platform.IMAGE,
]

type ProxonConfigEntry = ConfigEntry[ProxonCoordinator]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Actions for the weekly ventilation schedule (registered once, for all units)."""
    async_setup_services(hass)
    return True


def make_api(hass: HomeAssistant, data: dict) -> DirectApi | BridgeApi:
    if data.get(CONF_CONNECTION) == CONNECTION_BRIDGE:
        return BridgeApi(data[CONF_HOST], data.get(CONF_PORT, DEFAULT_PORT), data.get(CONF_TOKEN))
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
    coordinator.holiday = HolidayMode(hass, coordinator, entry.entry_id)
    await coordinator.holiday.async_load()
    coordinator.energy = EnergyManager(hass, coordinator, entry)
    await coordinator.energy.async_load()
    coordinator.comfort = ComfortManager(hass, coordinator, entry)
    await coordinator.comfort.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # notices under Settings -> Repairs (filter change soon, fault of the unit)
    update_issues(hass, entry, coordinator.data)
    entry.async_on_unload(coordinator.async_add_listener(lambda: update_issues(hass, entry, coordinator.data)))
    _remove_legacy_room_entities(hass, entry)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # hot water as a store for solar surplus / cheap electricity
    coordinator.energy.async_start()
    entry.async_on_unload(coordinator.energy.async_stop)
    # summer night cooling and hot-water boost
    coordinator.comfort.async_start()
    entry.async_on_unload(coordinator.comfort.async_stop)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        remove_issues(hass, entry)
        await hass.async_add_executor_job(entry.runtime_data.api.close)
    return ok
