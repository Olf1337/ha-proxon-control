"""Operating mode (Betriebsart), and the ventilation level of each phase of the weekly schedule."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity
from .registers import MODE_CHOICES, MODE_HOLIDAY, MODE_KEYS, SCHEDULE_PHASES
from .schedule import read_day
from .services import async_set_phase, schedule_day_device

LEVEL_OPTIONS = ["off", "1", "2", "3", "4"]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = [ProxonModeSelect(coordinator)]
    if read_day(coordinator.data or {}, 0) is not None:
        entities += [ProxonPhaseLevel(hass, coordinator, day, phase) for day in range(7) for phase in range(SCHEDULE_PHASES)]
    async_add_entities(entities)


class ProxonModeSelect(ProxonEntity, SelectEntity):
    _attr_icon = "mdi:hvac"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Betriebsart", "mode")

    @property
    def options(self) -> list[str]:
        opts = [MODE_KEYS[m] for m in MODE_CHOICES]
        # holiday mode can't be chosen here (as in the original), but is shown while active
        if self.raw_value is not None and int(self.raw_value) == MODE_HOLIDAY:
            opts.append(MODE_KEYS[MODE_HOLIDAY])
        return opts

    @property
    def current_option(self) -> str | None:
        return MODE_KEYS.get(int(self.raw_value)) if self.raw_value is not None else None

    async def async_select_option(self, option: str) -> None:
        mode = next(m for m, k in MODE_KEYS.items() if k == option)
        await self.coordinator.async_write("Betriebsart", mode)


class ProxonPhaseLevel(ProxonEntity, SelectEntity):
    """Ventilation level of one phase of the weekly schedule ("off" = phase not active)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:fan-clock"
    _attr_options = LEVEL_OPTIONS

    def __init__(self, hass: HomeAssistant, coordinator, day: int, phase: int) -> None:
        super().__init__(
            coordinator, f"ZP{day}_{phase}_stufe", "phase_level", {"phase": str(phase + 1)},
            device=schedule_day_device(hass, coordinator, day),
        )
        self._day, self._phase = day, phase

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and read_day(self.coordinator.data or {}, self._day) is not None

    @property
    def current_option(self) -> str | None:
        phases = read_day(self.coordinator.data or {}, self._day)
        if phases is None:
            return None
        level = phases[self._phase].level
        return LEVEL_OPTIONS[level] if 0 <= level <= 4 else None

    async def async_select_option(self, option: str) -> None:
        await async_set_phase(self.hass, self.coordinator, self._day, self._phase, None, None, LEVEL_OPTIONS.index(option))
