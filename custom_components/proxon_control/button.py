"""Weekly ventilation schedule: copy Monday to the working days or to the whole week with one press. Set the unit's clock
to the time of Home Assistant (the weekly schedule and the night setback run on that clock)."""
from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ProxonConfigEntry
from .entity import ProxonEntity
from .schedule import clock_writes, read_day, unit_clock
from .services import async_copy_day

COPIES = [("ZeitprogrammMoDiFr", "copy_monday_weekdays", [1, 2, 3, 4]), ("ZeitprogrammMoAlle", "copy_monday_all", [1, 2, 3, 4, 5, 6])]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities: list[ButtonEntity] = []
    if read_day(data, 0) is not None:
        entities += [ProxonCopyButton(coordinator, key, tk, days) for key, tk, days in COPIES]
    if unit_clock(data) is not None:
        entities.append(ProxonSetClockButton(coordinator))
    async_add_entities(entities)


class ProxonCopyButton(ProxonEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:content-copy"

    def __init__(self, coordinator, key: str, tk: str, days: list[int]) -> None:
        super().__init__(coordinator, key, tk)
        self._days = days

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and read_day(self.coordinator.data or {}, 0) is not None

    async def async_press(self) -> None:
        await async_copy_day(self.hass, self.coordinator, 0, self._days)


# the minute must not change between writing it and the unit reading it back: start just after a new minute begins
LATEST_SECOND = 45


class ProxonSetClockButton(ProxonEntity, ButtonEntity):
    """Sets the unit's clock to the time of Home Assistant. The weekly ventilation schedule and the night setback run on the
    unit's clock, so a clock that is off shifts them (Settings -> Repairs names the deviation)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "UhrStellen", "set_clock")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and unit_clock(self.coordinator.data or {}) is not None

    async def async_press(self) -> None:
        second = dt_util.now().second
        if second == 0 or second > LATEST_SECOND:  # wait for the next minute, plus a second
            await asyncio.sleep((60 - second) % 60 + 1)
        now = dt_util.now()
        for key, value in clock_writes(self.coordinator.data or {}, now):
            await self.coordinator.async_write(key, value)
