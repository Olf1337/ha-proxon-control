"""Holiday mode as the original app does it, with restore.

Switching on saves the current values and then sets: ventilation level 1, living room 18 °C, every other room to its lowest
value (offset −3 °C), all room heating elements off, hot-water heat pump off.
Switching off writes the saved values back in the app's order: hot-water heat pump first, after 2 seconds the immersion
heater, then the rest. The saved values are kept on disk, so a restart of Home Assistant in between loses nothing.
The unit's own operating mode 5 ("holiday") is deliberately not written: the manufacturer disabled it in app 1.7.4 and its
effect on the controller is unknown. (Sequence as documented by the ha-lan-proxon project, MIT licence.)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .registers import ROOM_COUNT, room_connected

_LOGGER = logging.getLogger(__name__)

HOLIDAY_LIVING_ROOM = 18.0
HOLIDAY_ROOM_OFFSET = -3
HOLIDAY_LEVEL = 1
HEAT_PUMP_KEY = "T300Betriebsart"
HEATER_KEY = "E-Heizstab"


class HolidayMode:
    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str) -> None:
        self.coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry_id}.holiday")
        self._state: dict[str, Any] = {"active": False, "saved": {}}
        self._lock = asyncio.Lock()
        self.restore_delay = 2.0

    async def async_load(self) -> None:
        if data := await self._store.async_load():
            self._state = data

    @property
    def active(self) -> bool:
        return bool(self._state.get("active"))

    @property
    def saved(self) -> dict[str, float]:
        return dict(self._state.get("saved") or {})

    def _rooms(self) -> list[int]:
        data = self.coordinator.data or {}
        return [n for n in range(1, ROOM_COUNT) if room_connected(data, n) and f"NBE{n}OffsetTemperatur" in data]

    def _profile(self) -> list[tuple[str, float]]:
        """The holiday values (without the hot-water heat pump, which is switched off last)."""
        writes: list[tuple[str, float]] = [("Luefterstufe", HOLIDAY_LEVEL), ("NBE0MittelTemperatur", HOLIDAY_LIVING_ROOM), ("NBE0PTC", 0)]
        for n in self._rooms():
            writes += [(f"NBE{n}OffsetTemperatur", HOLIDAY_ROOM_OFFSET), (f"NBE{n}PTC", 0)]
        data = self.coordinator.data or {}
        return [(k, v) for k, v in writes if k in data]

    async def async_turn_on(self) -> None:
        async with self._lock:
            if self.active:
                return
            data = self.coordinator.data or {}
            keys = [k for k, _ in self._profile()] + [k for k in (HEAT_PUMP_KEY, HEATER_KEY) if k in data]
            # keep the values saved by an earlier attempt that failed half-way
            saved = self.saved or {k: data[k] for k in keys if isinstance(data.get(k), (int, float))}
            if len(saved) < len(keys):
                raise HomeAssistantError(translation_domain=DOMAIN, translation_key="holiday_not_ready")
            # marked active before writing: if a write fails, switching off restores the saved values
            self._state = {"active": True, "saved": saved}
            await self._store.async_save(self._state)
            for key, value in self._profile():
                await self.coordinator.async_write(key, value)
            if HEAT_PUMP_KEY in data:
                await self.coordinator.async_write(HEAT_PUMP_KEY, 0)
            _LOGGER.info("Holiday mode on, %d values saved", len(saved))

    async def async_turn_off(self) -> None:
        async with self._lock:
            saved = self.saved
            if saved:
                if HEAT_PUMP_KEY in saved:
                    await self.coordinator.async_write(HEAT_PUMP_KEY, saved[HEAT_PUMP_KEY])
                    await asyncio.sleep(self.restore_delay)
                if HEATER_KEY in saved:
                    await self.coordinator.async_write(HEATER_KEY, saved[HEATER_KEY])
                for key, value in saved.items():
                    if key not in (HEAT_PUMP_KEY, HEATER_KEY):
                        await self.coordinator.async_write(key, value)
            self._state = {"active": False, "saved": {}}
            await self._store.async_save(self._state)
            _LOGGER.info("Holiday mode off, %d values restored", len(saved))
