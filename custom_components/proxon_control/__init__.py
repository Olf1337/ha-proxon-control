"""Proxon Control: the ventilation / heat unit as a Home Assistant integration."""
from __future__ import annotations

import re

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .api import BridgeApi, HybridApi, connect
from .comfort_manager import ComfortManager
from .const import (
    CONF_CONNECTION,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_LOCAL_HOST,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TOKEN,
    CONNECTION_BRIDGE,
    DEFAULT_MODE,
    DEFAULT_PORT,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)
from .coordinator import ProxonCoordinator
from .energy_manager import EnergyManager
from .entity import room_identifier, room_name
from .holiday import HolidayMode
from .nabto import library_supported
from .registers import ROOM_COUNT
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
    Platform.TIME,
    Platform.BUTTON,
]

type ProxonConfigEntry = ConfigEntry[ProxonCoordinator]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Actions for the weekly ventilation schedule (registered once, for all units)."""
    async_setup_services(hass)
    return True


def make_api(hass: HomeAssistant, data: dict) -> HybridApi | BridgeApi:
    """The way to the unit. `data`: the entry's data and options together.

    Logged in with Device ID + password: home network and/or Proxon server, as chosen. Where Nabto's library doesn't exist
    (e.g. Raspberry Pi), only the home network is possible.
    """
    if data.get(CONF_CONNECTION) == CONNECTION_BRIDGE:
        return BridgeApi(data[CONF_HOST], data.get(CONF_PORT, DEFAULT_PORT), data.get(CONF_TOKEN))
    return connect(
        data[CONF_DEVICE_ID], data[CONF_PASSWORD], hass.config.path(DOMAIN),
        data.get(CONF_MODE) or DEFAULT_MODE, data.get(CONF_LOCAL_HOST), library_supported(),
    )


# entities of version 0.1.x that the room thermostats replace (room target numbers, room heating element switches)
_LEGACY = re.compile(r"_(NBE0MittelTemperatur|NBE[1-4]Ziel|NBE[0-4]PTC)$")


def _remove_legacy_room_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(reg, entry.entry_id):
        if ent.domain in ("number", "switch") and _LEGACY.search(ent.unique_id):
            reg.async_remove(ent.entity_id)


@callback
def _put_new_rooms_into_areas(hass: HomeAssistant, entry: ConfigEntry, coordinator: ProxonCoordinator, known: set[str]) -> None:
    """A room device that was just created goes into the area of the same name, if there is one (e.g. room "Bad" -> area "Bad").
    Only once, when the device is new: an area chosen or removed by hand later stays as it is."""
    devices, areas = dr.async_get(hass), ar.async_get(hass)
    by_identifier = {i: d for d in dr.async_entries_for_config_entry(devices, entry.entry_id) for i in d.identifiers}
    for n in range(ROOM_COUNT):
        device = by_identifier.get(room_identifier(coordinator, n))
        if device is None or device.id in known or device.area_id:
            continue
        if area := areas.async_get_area_by_name(room_name(n, coordinator.data)):
            devices.async_update_device(device.id, area_id=area.id)


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    coordinator = ProxonCoordinator(hass, entry, make_api(hass, {**entry.data, **entry.options}))
    coordinator.holiday = HolidayMode(hass, coordinator, entry.entry_id)
    await coordinator.holiday.async_load()
    coordinator.energy = EnergyManager(hass, coordinator, entry)
    await coordinator.energy.async_load()
    coordinator.comfort = ComfortManager(hass, coordinator, entry)
    await coordinator.comfort.async_load()
    await coordinator.async_load_runtime()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    # notices under Settings -> Repairs (filter change soon, fault of the unit)
    update_issues(hass, entry, coordinator.data)
    entry.async_on_unload(coordinator.async_add_listener(lambda: update_issues(hass, entry, coordinator.data)))
    _remove_legacy_room_entities(hass, entry)
    devices = dr.async_get(hass)
    known = {d.id for d in dr.async_entries_for_config_entry(devices, entry.entry_id)}
    # the appliance first: the room and schedule devices are linked to it
    coordinator.device_id = devices.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.unique_id or entry.entry_id)}, manufacturer=MANUFACTURER, model=MODEL,
        name="Proxon",
    ).id
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _put_new_rooms_into_areas(hass, entry, coordinator, known)
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
