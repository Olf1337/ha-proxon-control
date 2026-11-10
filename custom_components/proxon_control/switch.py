"""On/off settings: boost ventilation, cooling, hot-water heat pump, immersion heater. (Room heating elements are part of the room thermostats.)"""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity

SWITCHES: list[tuple[str, str, str, int | None]] = [
    ("Intensivlueftung", "boost", "mdi:fan-plus", None),
    ("GlobalKuehlungFreigabe", "cooling", "mdi:snowflake", None),
    ("T300Betriebsart", "water_heat_pump", "mdi:water-boiler", None),
    ("E-Heizstab", "immersion_heater", "mdi:heating-coil", None),
]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities: list[SwitchEntity] = [ProxonSwitch(coordinator, key, tk, icon, room) for key, tk, icon, room in SWITCHES if key in data]
    entities.append(ProxonHolidaySwitch(coordinator))
    async_add_entities(entities)


class ProxonSwitch(ProxonEntity, SwitchEntity):
    def __init__(self, coordinator, key: str, tk: str, icon: str, room: int | None) -> None:
        super().__init__(coordinator, key, tk)
        self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        return bool(self.value) if self.value is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self._key, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self._key, 0)


class ProxonHolidaySwitch(ProxonEntity, SwitchEntity):
    """Holiday mode: lowers ventilation and temperatures and switches off hot water; switching off restores the saved values."""

    _attr_icon = "mdi:bag-suitcase"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Urlaubsmodus", "holiday")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self.coordinator.holiday.active

    @property
    def extra_state_attributes(self) -> dict:
        return {"saved_values": self.coordinator.holiday.saved}

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.holiday.async_turn_on()
        finally:
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.holiday.async_turn_off()
        finally:
            self.async_write_ha_state()
