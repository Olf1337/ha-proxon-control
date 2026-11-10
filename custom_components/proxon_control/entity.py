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
