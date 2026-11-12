"""Shared base for all Proxon entities: the appliance is one device, every room panel and every weekday of the ventilation
schedule a device of its own linked to it (so rooms can be put into their areas)."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, CONF_UPPER_FLOOR, DEFAULT_ROOM_NAMES, DOMAIN, MANUFACTURER, MODEL, ROOM_MODEL
from .coordinator import ProxonCoordinator
from .pictures import guess_floor
from .registers import ROOM_COUNT, room_connected, room_name_from_unit, room_target


def room_name(i: int, data: dict | None = None) -> str:
    """The room's name as stored in the unit (what the Proxon app shows); a default name only if the unit has none."""
    stored = room_name_from_unit(data or {}, i)
    if stored:
        return stored
    return DEFAULT_ROOM_NAMES[i] if i < len(DEFAULT_ROOM_NAMES) else f"Raum {i + 1}"


def house_rooms(data: dict) -> list[int]:
    """The rooms the house picture shows (those with a thermostat), in order; the dashboard places its tap areas by them."""
    return [i for i in range(ROOM_COUNT) if room_connected(data, i) and room_target(data, i) is not None]


def room_floors(options: Mapping[str, Any], data: dict, rooms: Iterable[int]) -> list[int]:
    """Floor of each room for the house picture (0 ground, 1 upper): as chosen in the options, else guessed from the name."""
    chosen = options.get(CONF_UPPER_FLOOR)
    if chosen is not None:
        return [1 if str(i) in chosen else 0 for i in rooms]
    return [guess_floor(room_name(i, data)) for i in rooms]


def base_id(coordinator: ProxonCoordinator) -> str:
    entry = coordinator.entry
    return entry.unique_id or entry.entry_id


# Home Assistant 2026.10 links a device to its parent by the parent's device id (via_device_id); older versions by its identifier
VIA_DEVICE_ID = "via_device_id" in DeviceInfo.__annotations__


def _via(coordinator: ProxonCoordinator) -> dict:
    if VIA_DEVICE_ID and coordinator.device_id:
        return {"via_device_id": coordinator.device_id}
    return {"via_device": (DOMAIN, base_id(coordinator))}


def room_identifier(coordinator: ProxonCoordinator, room: int) -> tuple[str, str]:
    return (DOMAIN, f"{base_id(coordinator)}_room{room}")


def room_device(coordinator: ProxonCoordinator, room: int) -> DeviceInfo:
    """A room panel as a device of its own (can be put into the room's area)."""
    return DeviceInfo(
        identifiers={room_identifier(coordinator, room)},
        manufacturer=MANUFACTURER,
        model=ROOM_MODEL,
        name=f"Proxon {room_name(room, coordinator.data)}",
        **_via(coordinator),
    )


def schedule_device(coordinator: ProxonCoordinator, day: int, day_name: str, title: str) -> DeviceInfo:
    """One weekday of the ventilation schedule as a device (its phases' times and levels)."""
    return DeviceInfo(
        identifiers={(DOMAIN, f"{base_id(coordinator)}_schedule{day}")},
        manufacturer=MANUFACTURER,
        model=MODEL,
        name=f"Proxon {title} {day_name}",
        **_via(coordinator),
    )


class ProxonEntity(CoordinatorEntity[ProxonCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: ProxonCoordinator, key: str, translation_key: str, placeholders: dict[str, str] | None = None,
        *, device: DeviceInfo | None = None,
    ) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        base = base_id(coordinator)
        self._key = key
        self._attr_unique_id = f"{base}_{key}"
        self._attr_translation_key = translation_key
        if placeholders:
            self._attr_translation_placeholders = placeholders
        if device is not None:
            self._attr_device_info = device
            return
        version = (coordinator.data or {}).get("FirmwareVersion")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, base)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name="Proxon",
            serial_number=entry.data.get(CONF_DEVICE_ID),
            sw_version=str(int(version)) if version is not None else None,
        )

    @property
    def raw_value(self) -> float | None:
        """The unit's value for this entity's key (not called `value`: some entity types use that name themselves)."""
        return (self.coordinator.data or {}).get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self.raw_value is not None


class ProxonEnergyEntity(ProxonEntity):
    """Entities whose values live in a manager, not in the unit: the hot-water energy manager (solar surplus / cheap
    electricity), summer night cooling and hot-water boost."""

    def __init__(self, coordinator, key: str, translation_key: str, manager=None) -> None:
        super().__init__(coordinator, key, translation_key)
        self.manager = manager or coordinator.energy

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.manager.add_entity_listener(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.manager.supported
