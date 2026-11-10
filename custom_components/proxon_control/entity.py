"""Shared base for all Proxon entities (one device per appliance)."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DEFAULT_ROOM_NAMES, DOMAIN, MANUFACTURER, MODEL
from .coordinator import ProxonCoordinator
from .registers import room_name_from_unit


def room_name(i: int, data: dict | None = None) -> str:
    """The room's name as stored in the unit (what the Proxon app shows); a default name only if the unit has none."""
    stored = room_name_from_unit(data or {}, i)
    if stored:
        return stored
    return DEFAULT_ROOM_NAMES[i] if i < len(DEFAULT_ROOM_NAMES) else f"Raum {i + 1}"


class ProxonEntity(CoordinatorEntity[ProxonCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ProxonCoordinator, key: str, translation_key: str, placeholders: dict[str, str] | None = None) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        base = entry.unique_id or entry.entry_id
        self._key = key
        self._attr_unique_id = f"{base}_{key}"
        self._attr_translation_key = translation_key
        if placeholders:
            self._attr_translation_placeholders = placeholders
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
    def value(self) -> float | None:
        return (self.coordinator.data or {}).get(self._key)

    @property
    def available(self) -> bool:
        return super().available and self.value is not None
