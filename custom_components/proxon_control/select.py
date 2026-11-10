"""Operating mode (Betriebsart)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity
from .registers import MODE_CHOICES, MODE_HOLIDAY, MODE_KEYS


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([ProxonModeSelect(entry.runtime_data)])


class ProxonModeSelect(ProxonEntity, SelectEntity):
    _attr_icon = "mdi:hvac"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Betriebsart", "mode")

    @property
    def options(self) -> list[str]:
        opts = [MODE_KEYS[m] for m in MODE_CHOICES]
        # holiday mode can't be chosen here (as in the original), but is shown while active
        if self.value is not None and int(self.value) == MODE_HOLIDAY:
            opts.append(MODE_KEYS[MODE_HOLIDAY])
        return opts

    @property
    def current_option(self) -> str | None:
        return MODE_KEYS.get(int(self.value)) if self.value is not None else None

    async def async_select_option(self, option: str) -> None:
        mode = next(m for m, k in MODE_KEYS.items() if k == option)
        await self.coordinator.async_write("Betriebsart", mode)
