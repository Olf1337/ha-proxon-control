"""Proxon Control: the ventilation / heat unit as a Home Assistant integration."""
from __future__ import annotations

import logging
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
    ENTRY_MINOR_VERSION,
    ENTRY_VERSION,
    MANUFACTURER,
    MODEL,
)
from .coordinator import ProxonCoordinator
from .energy_manager import EnergyManager
from .entity import room_identifier, room_name
from .holiday import HolidayMode
from .nabto import library_supported
from .panel import async_register as async_register_panel
from .panel import async_unregister as async_unregister_panel
from .registers import ROOM_COUNT, room_connected
from .repairs_watch import remove_issues, update_issues
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

REMOVED_BEFORE_1_0 = ("_T14Sauggas", "_T300StundenKompressor", "_StatusKompressor", "_StatusVentilatoren")

PLATFORMS = [
    Platform.SENSOR,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.FAN,
    Platform.WATER_HEATER,
    Platform.TIME,
    Platform.DATETIME,
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
        # "weekly schedule active" was a read-only sensor; it is a switch since 0.18.0
        elif ent.domain == "binary_sensor" and ent.unique_id.endswith("_ZeitprogrammAktiv"):
            reg.async_remove(ent.entity_id)
        # the button "set the unit's clock" of 0.20.0: the unit refuses writing its clock over the network (NO_ACCESS)
        elif ent.domain == "button" and ent.unique_id.endswith("_UhrStellen"):
            reg.async_remove(ent.entity_id)
        # removed before 1.0: two readings whose meaning was never confirmed and two raw status words (all hidden by default)
        elif ent.domain == "sensor" and ent.unique_id.endswith(REMOVED_BEFORE_1_0):
            reg.async_remove(ent.entity_id)
        # the dashboard pictures (unit, hot water, house, floor plan), removed in 1.0: the page "Proxon" shows all of it
        elif ent.domain == "image":
            reg.async_remove(ent.entity_id)
    if "picture_theme" in entry.options:  # their light/dark option
        hass.config_entries.async_update_entry(entry, options={k: v for k, v in entry.options.items() if k != "picture_theme"})


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
    # holiday plan: departure and return
    entry.async_on_unload(coordinator.holiday.async_start())
    # summer night cooling and hot-water boost
    coordinator.comfort.async_start()
    entry.async_on_unload(coordinator.comfort.async_stop)
    # the "Proxon" page in the sidebar (our own interface)
    await async_register_panel(hass, entry)
    return True


async def async_remove_config_entry_device(hass: HomeAssistant, entry: ConfigEntry, device: dr.DeviceEntry) -> bool:
    """A room the unit no longer reports can be deleted by hand (device page → Delete); the unit, its schedule days and the
    rooms it still reports can't (they would come back at the next start)."""
    coordinator = getattr(entry, "runtime_data", None)
    data = getattr(coordinator, "data", None) or {}
    # only on a fresh reading of the unit: a failed or empty one would make every room look disconnected
    if coordinator is None or not coordinator.last_update_success or "NBE0MittelTemperatur" not in data:
        return False
    rooms = {room_identifier(coordinator, n): n for n in range(ROOM_COUNT)}
    return all(i in rooms and not room_connected(data, rooms[i]) for i in device.identifiers)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Bring settings saved by an older version up to date. Settings saved by a newer version (after going back to an older
    release) are left alone and the entry is not loaded, so nothing is overwritten that this version doesn't understand."""
    if entry.version > ENTRY_VERSION:
        _LOGGER.error("Proxon Control: these settings were saved by a newer version (%s.%s); please update the integration again",
                      entry.version, entry.minor_version)
        return False
    # version 1 is the current layout: nothing to change yet. A future version 2 converts here, e.g.
    # hass.config_entries.async_update_entry(entry, data=..., version=2, minor_version=1)
    if (entry.version, entry.minor_version) != (ENTRY_VERSION, ENTRY_MINOR_VERSION):
        hass.config_entries.async_update_entry(entry, version=ENTRY_VERSION, minor_version=ENTRY_MINOR_VERSION)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ProxonConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        async_unregister_panel(hass, entry)
        remove_issues(hass, entry)
        await hass.async_add_executor_job(entry.runtime_data.api.close)
    return ok
