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
    data = coordinator.data or {}
    entities: list[TimeEntity] = []
    if all(k in data for k in NIGHT_KEYS[False] + NIGHT_KEYS[True]):
        entities += [ProxonNightTime(coordinator, end) for end in (False, True)]
    if read_day(data, 0) is not None:
        entities += [
            ProxonPhaseTime(hass, coordinator, day, phase, end)
            for day in range(7) for phase in range(SCHEDULE_PHASES) for end in (False, True)
        ]
    async_add_entities(entities)


# night setback: start and end (hour, minute)
NIGHT_KEYS = {False: ("NachtabsenkungStartH", "NachtabsenkungStartM"), True: ("NachtabsenkungEndeH", "NachtabsenkungEndeM")}


class ProxonNightTime(ProxonEntity, TimeEntity):
    """Start / end of the unit's night setback of the room temperature."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, end: bool) -> None:
        super().__init__(coordinator, f"Nachtabsenkung{'Ende' if end else 'Start'}", f"night_setback_{'end' if end else 'start'}")
        self._keys = NIGHT_KEYS[end]
        self._attr_icon = "mdi:weather-sunset-up" if end else "mdi:weather-sunset-down"

    @property
    def available(self) -> bool:
        data = self.coordinator.data or {}
        return self.coordinator.last_update_success and all(k in data for k in self._keys)

    @property
    def native_value(self) -> time | None:
        data = self.coordinator.data or {}
        h, m = (data.get(k) for k in self._keys)
        if not isinstance(h, (int, float)) or not isinstance(m, (int, float)) or not (0 <= h < 24 and 0 <= m < 60):
            return None
        return time(int(h), int(m))

    async def async_set_value(self, value: time) -> None:
        data = self.coordinator.data or {}
        for key, v in zip(self._keys, (value.hour, value.minute)):
            if data.get(key) != v:
                await self.coordinator.async_write(key, v)


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
