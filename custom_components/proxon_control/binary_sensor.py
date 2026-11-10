"""Filter change warning and compressor state."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity

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
    async_add_entities(entities)


class ProxonFilterWarning(ProxonEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "FilterRestStunden", "filter_change")
        self._attr_unique_id = f"{self._attr_unique_id}_warning"

    @property
    def is_on(self) -> bool | None:
        return None if self.value is None else self.value <= FILTER_WARN_HOURS


class ProxonCompressor(ProxonEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "DrehzahlKompressor", "compressor")
        self._attr_unique_id = f"{self._attr_unique_id}_running"

    @property
    def is_on(self) -> bool | None:
        return None if self.value is None else self.value > 0
