"""Weekly ventilation schedule: copy Monday to the working days or to the whole week with one press."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity
from .schedule import read_day
from .services import async_copy_day

COPIES = [("ZeitprogrammMoDiFr", "copy_monday_weekdays", [1, 2, 3, 4]), ("ZeitprogrammMoAlle", "copy_monday_all", [1, 2, 3, 4, 5, 6])]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    if read_day(coordinator.data or {}, 0) is None:
        return
    async_add_entities(ProxonCopyButton(coordinator, key, tk, days) for key, tk, days in COPIES)


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
