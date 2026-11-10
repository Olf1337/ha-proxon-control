"""Filter change warning and compressor state."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity
from .registers import FAULT_POINTS, active_faults, fault_key

# warn when 30 days or less are left (estimated; the original's exact threshold wasn't found)
FILTER_WARN_HOURS = 30 * 24


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities: list[BinarySensorEntity] = []
    if "FilterRestStunden" in data:
        entities.append(ProxonFilterWarning(coordinator))
    if "DrehzahlKompressor" in data:
        entities.append(ProxonCompressor(coordinator))
    if "ZeitprogrammAktiv" in data:
        entities.append(ProxonScheduleActive(coordinator))
    if any(fault_key(p) in data for p in FAULT_POINTS):
        entities.append(ProxonFault(coordinator))
    async_add_entities(entities)


class ProxonFilterWarning(ProxonEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "FilterRestStunden", "filter_change")
        self._attr_unique_id = f"{self._attr_unique_id}_warning"

    @property
    def is_on(self) -> bool | None:
        return None if self.raw_value is None else self.raw_value <= FILTER_WARN_HOURS


class ProxonCompressor(ProxonEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "DrehzahlKompressor", "compressor")
        self._attr_unique_id = f"{self._attr_unique_id}_running"

    @property
    def is_on(self) -> bool | None:
        return None if self.raw_value is None else self.raw_value > 0


class ProxonScheduleActive(ProxonEntity, BinarySensorEntity):
    """Whether the weekly ventilation schedule is switched on at the unit (can only be changed at the unit or in the app)."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "ZeitprogrammAktiv", "schedule_active")

    @property
    def is_on(self) -> bool | None:
        return None if self.raw_value is None else bool(self.raw_value)


class ProxonFault(ProxonEntity, BinarySensorEntity):
    """Fault of the unit: any fault word with a bit set (known harmless notice bits left out). The words are attributes."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Stoerung", "fault")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and any(fault_key(p) in (self.coordinator.data or {}) for p in FAULT_POINTS)

    @property
    def is_on(self) -> bool:
        return bool(active_faults(self.coordinator.data or {}))

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        return {fault_key(p): f"0x{int(data[fault_key(p)]) & 0xFFFF:04X}" for p in FAULT_POINTS if isinstance(data.get(fault_key(p)), (int, float))}
