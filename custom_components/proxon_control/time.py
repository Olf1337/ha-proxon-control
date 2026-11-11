"""Weekly ventilation schedule: start and end of each phase as time settings, one device per weekday.

Changes are checked against the unit's rules first (see schedule.py): times only for phases that start at least 2 hours
from now, a running phase only in its level, no overlaps. A phase that is off can be prepared freely.
"""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity
from .registers import SCHEDULE_PHASES
from .schedule import read_day
from .services import async_set_phase, schedule_day_device


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    if read_day(coordinator.data or {}, 0) is None:
        return
    async_add_entities(
        ProxonPhaseTime(hass, coordinator, day, phase, end)
        for day in range(7) for phase in range(SCHEDULE_PHASES) for end in (False, True)
    )


class ProxonPhaseTime(ProxonEntity, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, hass: HomeAssistant, coordinator, day: int, phase: int, end: bool) -> None:
        which = "end" if end else "start"
        super().__init__(
            coordinator, f"ZP{day}_{phase}_{which}", f"phase_{which}", {"phase": str(phase + 1)},
            device=schedule_day_device(hass, coordinator, day),
        )
        self._day, self._phase, self._end = day, phase, end
        self._attr_icon = "mdi:clock-end" if end else "mdi:clock-start"

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and read_day(self.coordinator.data or {}, self._day) is not None

    @property
    def native_value(self) -> time | None:
        phases = read_day(self.coordinator.data or {}, self._day)
        if phases is None:
            return None
        p = phases[self._phase]
        minutes = p.end if self._end else p.start
        return time(minutes // 60 % 24, minutes % 60)

    async def async_set_value(self, value: time) -> None:
        minutes = value.hour * 60 + value.minute
        await async_set_phase(
            self.hass, self.coordinator, self._day, self._phase,
            None if self._end else minutes, minutes if self._end else None, None,
        )
