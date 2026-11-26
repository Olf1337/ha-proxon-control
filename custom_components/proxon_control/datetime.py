"""Holiday plan: departure and return as date and time (holiday mode switches itself on and off, see holiday.py)."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity

# one change at a time per platform: the unit allows only a few sessions, and every write is read back
PARALLEL_UPDATES = 1


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities([ProxonHolidayPlanTime(coordinator, "start"), ProxonHolidayPlanTime(coordinator, "end")])


class ProxonHolidayPlanTime(ProxonEntity, DateTimeEntity):
    """Departure ("start") or return ("end") of the holiday plan; empty while no plan is set."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, which: str) -> None:
        start = which == "start"
        super().__init__(coordinator, "UrlaubAb" if start else "UrlaubBis", "holiday_start" if start else "holiday_end")
        self._which = which

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.holiday.add_listener(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return True  # a setting of the integration: also while the unit can't be reached

    @property
    def native_value(self) -> datetime | None:
        holiday = self.coordinator.holiday
        return holiday.plan_start if self._which == "start" else holiday.plan_end

    async def async_set_value(self, value: datetime) -> None:
        await self.coordinator.holiday.async_set_plan(**{self._which: value})
