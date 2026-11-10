"""The ventilation as a fan: level 1-4 as speed, boost ventilation as preset. Works with fan cards and voice assistants.

Turning the fan off is not offered on purpose: the ventilation only stops when the whole unit is switched off
(operating mode "Off"), which would also stop heating and hot water. That stays in the operating mode select.
"""
from __future__ import annotations

import math

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value, ranged_value_to_percentage

from . import ProxonConfigEntry
from .const import DOMAIN
from .entity import ProxonEntity
from .registers import MODE_COMFORT, MODE_OFF

LEVEL_RANGE = (1, 4)
PRESET_NORMAL = "normal"
PRESET_BOOST = "boost"


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    if "Luefterstufe" in (coordinator.data or {}):
        async_add_entities([ProxonVentilationFan(coordinator)])


class ProxonVentilationFan(ProxonEntity, FanEntity):
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
    _attr_preset_modes = [PRESET_NORMAL, PRESET_BOOST]
    _attr_speed_count = LEVEL_RANGE[1] - LEVEL_RANGE[0] + 1

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Lueftung", "ventilation")

    @property
    def _data(self) -> dict:
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._data.get("Luefterstufe") is not None

    def _unit_sets_level(self) -> bool:
        """In ECO Comfort and during boost ventilation the unit chooses the level itself."""
        return bool(self._data.get("Intensivlueftung")) or int(self._data.get("Betriebsart", -1)) == MODE_COMFORT

    @property
    def is_on(self) -> bool | None:
        mode = self._data.get("Betriebsart")
        return None if mode is None else int(mode) != MODE_OFF

    @property
    def percentage(self) -> int | None:
        if not self.is_on:
            return 0
        # when the unit chooses the level, show the level it actually runs; otherwise the level that was set
        level = self._data.get("IstLuefterstufe") if self._unit_sets_level() else None
        if level is None:
            level = self._data.get("Luefterstufe")
        if level is None:
            return None
        level = max(LEVEL_RANGE[0], min(LEVEL_RANGE[1], int(level)))
        return ranged_value_to_percentage(LEVEL_RANGE, level)

    @property
    def preset_mode(self) -> str | None:
        boost = self._data.get("Intensivlueftung")
        return None if boost is None else (PRESET_BOOST if boost else PRESET_NORMAL)

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="fan_no_off")
        if self._unit_sets_level():
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="level_locked")
        level = math.ceil(percentage_to_ranged_value(LEVEL_RANGE, percentage))
        await self.coordinator.async_write("Luefterstufe", level)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.coordinator.async_write("Intensivlueftung", 1 if preset_mode == PRESET_BOOST else 0)
