"""Hot water as a store for solar surplus and cheap electricity: settings, timers and writing to the unit.

Settings (the two switches, the limits and the store temperature) and the running state are kept on disk, so they survive a
restart of Home Assistant. The decision rules are in energy.py.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import energy as E
from .const import CONF_FEED_IN_NEGATIVE, CONF_PRICE_SENSOR, CONF_SURPLUS_SENSOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

TARGET_KEY = "SollWassertemperatur"
HEAT_PUMP_KEY = "T300Betriebsart"
CHECK_EVERY = timedelta(minutes=1)


class EnergyManager:
    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.entry = entry
        self.settings = E.Settings()
        self.state = E.State()
        self.status = E.OFF
        self.details: dict[str, Any] = {}
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.energy")
        self._lock = asyncio.Lock()
        self._listeners: list[CALLBACK_TYPE] = []
        self._entity_updates: list[CALLBACK_TYPE] = []

    # ---- setup ----
    @property
    def supported(self) -> bool:
        """Only units with the hot-water heat pump (T300) have a hot-water target."""
        data = self.coordinator.data or {}
        return TARGET_KEY in data and HEAT_PUMP_KEY in data

    async def async_load(self) -> None:
        if data := await self._store.async_load():
            s = data.get("settings") or {}
            self.settings = E.Settings(**{k: v for k, v in s.items() if k in E.Settings.__dataclass_fields__})
            self.state = E.State.from_dict(data.get("state") or {})

    @callback
    def async_start(self) -> None:
        self._listeners.append(self.coordinator.async_add_listener(self._schedule))
        self._listeners.append(async_track_time_interval(self.hass, lambda now: self._schedule(), CHECK_EVERY))

    @callback
    def async_stop(self) -> None:
        while self._listeners:
            self._listeners.pop()()

    @callback
    def add_entity_listener(self, update: CALLBACK_TYPE) -> CALLBACK_TYPE:
        self._entity_updates.append(update)
        return lambda: self._entity_updates.remove(update)

    def _notify(self) -> None:
        for update in list(self._entity_updates):
            update()

    async def _save(self) -> None:
        await self._store.async_save({"settings": vars(self.settings), "state": self.state.to_dict()})

    # ---- settings (switches and number entities) ----
    async def async_set(self, **changes: Any) -> None:
        for key, value in changes.items():
            setattr(self.settings, key, value)
        await self._save()
        await self.async_evaluate()

    # ---- inputs ----
    def _sensor_value(self, option: str) -> tuple[float | None, str | None]:
        entity_id = self.entry.options.get(option)
        if not entity_id:
            return None, None
        state = self.hass.states.get(entity_id)
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN, ""):
            return None, None
        try:
            return float(state.state), state.attributes.get("unit_of_measurement")
        except ValueError:
            return None, None

    def _surplus(self) -> float | None:
        value, unit = self._sensor_value(CONF_SURPLUS_SENSOR)
        return None if value is None else E.power_in_watt(value, unit, bool(self.entry.options.get(CONF_FEED_IN_NEGATIVE)))

    def _price(self) -> float | None:
        value, unit = self._sensor_value(CONF_PRICE_SENSOR)
        return None if value is None else E.price_in_cent(value, unit)

    def _unit_ok(self) -> bool:
        data = self.coordinator.data or {}
        holiday = getattr(self.coordinator, "holiday", None)
        return (
            self.coordinator.last_update_success
            and bool(data.get(HEAT_PUMP_KEY))
            and isinstance(data.get(TARGET_KEY), (int, float))
            and not (holiday and holiday.active)
        )

    # ---- evaluation ----
    @callback
    def _schedule(self) -> None:
        if not self._lock.locked():
            self.entry.async_create_background_task(self.hass, self.async_evaluate(), "proxon hot water energy manager")

    async def async_evaluate(self, now: datetime | None = None) -> None:
        if not self.supported:
            return
        async with self._lock:
            now = now or dt_util.now()
            d = E.decide(now, self.settings, self.state, self._surplus(), self._price(), self._unit_ok())
            self.status, self.details = d.status, d.details
            try:
                if d.action == "start":
                    await self._start(now, d.source)
                elif d.action == "stop":
                    await self._stop(now)
            except HomeAssistantError as err:
                _LOGGER.warning("Hot-water energy manager: %s", err)
            self._notify()

    async def _start(self, now: datetime, source: str | None) -> None:
        data = self.coordinator.data or {}
        current = float(data[TARGET_KEY])
        target = float(self.settings.store_temp)
        saved = current if target > current else None
        E.started(self.state, now, source or E.SOLAR, saved)
        await self._save()  # saved before writing: a restart in between still restores the old target
        if saved is not None:
            _LOGGER.info("Hot water: storing %s energy, target %s -> %s °C", source, current, target)
            await self.coordinator.async_write(TARGET_KEY, target)

    async def _stop(self, now: datetime) -> None:
        saved = self.state.saved_target
        data = self.coordinator.data or {}
        E.stopped(self.state, now)
        await self._save()
        # write the old target back only if nobody changed the target in the meantime
        current = data.get(TARGET_KEY)
        if saved is not None and isinstance(current, (int, float)) and abs(current - self.settings.store_temp) < 0.05:
            _LOGGER.info("Hot water: back to %s °C", saved)
            await self.coordinator.async_write(TARGET_KEY, saved)
