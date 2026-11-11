"""Summer night cooling, hot-water boost and automatic summer/winter in Home Assistant: settings and state on disk, a check every minute, writing to the unit.

The decision rules are in comfort.py. Both features use only the unit's own values.
"""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import comfort as C
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
CHECK_EVERY = timedelta(minutes=1)


class Feature:
    """One feature as the entities see it: settings, status, and a way to change the settings."""

    def __init__(self, manager: ComfortManager, settings, state, required: tuple[str, ...]) -> None:
        self._manager = manager
        self.settings = settings
        self.state = state
        self.status = C.C_OFF
        self.details: dict[str, Any] = {}
        self._required = required
        self._updates: list[CALLBACK_TYPE] = []

    @property
    def supported(self) -> bool:
        data = self._manager.coordinator.data or {}
        return all(k in data for k in self._required)

    @callback
    def add_entity_listener(self, update: CALLBACK_TYPE) -> CALLBACK_TYPE:
        self._updates.append(update)
        return lambda: self._updates.remove(update)

    def notify(self) -> None:
        for update in list(self._updates):
            update()

    async def async_set(self, **changes: Any) -> None:
        for key, value in changes.items():
            setattr(self.settings, key, value)
        await self._manager.async_save()
        await self._manager.async_evaluate()


class ComfortManager:
    def __init__(self, hass: HomeAssistant, coordinator, entry: ConfigEntry) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self.entry = entry
        self.cooling = Feature(self, C.CoolSettings(), C.CoolState(), ("T3Frischluft", "T7Abluft", "Luefterstufe", "Betriebsart"))
        self.boost = Feature(self, C.BoostSettings(), C.BoostState(), ("E-Heizstab", "WarmwasserIstTemperatur"))
        self.boost.status = C.B_OFF
        self.season = Feature(self, C.SeasonSettings(), C.SeasonState(), ("T3Frischluft", "Betriebsart"))
        self.season.status = C.S_OFF
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.comfort")
        self._lock = asyncio.Lock()
        self._pending = False
        self._listeners: list[Callable[[], None]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        for feature, cls_s, cls_st, key in (
            (self.cooling, C.CoolSettings, C.CoolState, "cooling"),
            (self.boost, C.BoostSettings, C.BoostState, "boost"),
            (self.season, C.SeasonSettings, C.SeasonState, "season"),
        ):
            part = data.get(key) or {}
            s = part.get("settings") or {}
            feature.settings = cls_s(**{k: v for k, v in s.items() if k in cls_s.__dataclass_fields__})
            feature.state = cls_st.from_dict(part.get("state") or {})

    async def async_save(self) -> None:
        await self._store.async_save({
            "cooling": {"settings": vars(self.cooling.settings), "state": self.cooling.state.to_dict()},
            "boost": {"settings": vars(self.boost.settings), "state": self.boost.state.to_dict()},
            "season": {"settings": vars(self.season.settings), "state": self.season.state.to_dict()},
        })

    @callback
    def async_start(self) -> None:
        self._listeners.append(self.coordinator.async_add_listener(self._schedule))
        self._listeners.append(async_track_time_interval(self.hass, self._tick, CHECK_EVERY, cancel_on_shutdown=True))
        # check as soon as Home Assistant runs (right away when it already does), so the status is right from the start
        self._listeners.append(async_at_started(self.hass, self._started))

    @callback
    def async_stop(self) -> None:
        while self._listeners:
            self._listeners.pop()()

    @callback
    def _started(self, hass: HomeAssistant) -> None:
        self._schedule()

    @callback
    def _tick(self, now: datetime) -> None:
        # a @callback runs in Home Assistant's event loop (a plain function would be run in a worker thread)
        self._schedule()

    @callback
    def _schedule(self) -> None:
        if not self.hass.is_running or self._lock.locked() or self._pending:
            return
        self._pending = True
        self.entry.async_create_background_task(self.hass, self._background(), "proxon night cooling / hot-water boost")

    async def _background(self) -> None:
        try:
            if not self._lock.locked():
                await self.async_evaluate()
        finally:
            self._pending = False

    def _holiday(self) -> bool:
        holiday = getattr(self.coordinator, "holiday", None)
        return bool(holiday and holiday.active)

    async def async_evaluate(self, now: datetime | None = None) -> None:
        async with self._lock:
            now = now or dt_util.now()
            data = self.coordinator.data or {}
            ok = self.coordinator.last_update_success

            def num(key: str) -> float | None:
                v = data.get(key)
                return float(v) if ok and isinstance(v, (int, float)) else None

            changed = False
            if self.cooling.supported:
                mode = num("Betriebsart")
                d = C.decide_cooling(
                    now, self.cooling.settings, self.cooling.state, mode=None if mode is None else int(mode),
                    inside=num("T7Abluft"), outside=num("T3Frischluft"), level_now=num("Luefterstufe"),
                    boost=bool(data.get("Intensivlueftung")), holiday=self._holiday(),
                )
                self.cooling.status, self.cooling.details = d.status, d.details
                if d.level is not None:
                    changed = True
                    await self._write("Luefterstufe", d.level, f"night cooling: ventilation level {d.level}")
            if self.boost.supported:
                heater = num("E-Heizstab")
                action, status = C.decide_boost(
                    now, self.boost.settings, self.boost.state, water=num("WarmwasserIstTemperatur"),
                    heater_on=None if heater is None else bool(heater), holiday=self._holiday(),
                )
                self.boost.status = status
                self.boost.details = {"water": num("WarmwasserIstTemperatur"), "heater_target": num("Soll-E-Heizstab-Temperatur")}
                if action == "on":
                    self.boost.state.active, self.boost.state.since = True, now
                    changed = True
                    await self.async_save()  # saved first: after a restart it still knows it switched the heater on
                    await self._write("E-Heizstab", 1, "hot-water boost: immersion heater on")
                elif action == "off":
                    self.boost.state.active, self.boost.state.since, self.boost.state.last_stop = False, None, now
                    changed = True
                    await self._write("E-Heizstab", 0, "hot-water boost: immersion heater off")
            if self.season.supported:
                mode = num("Betriebsart")
                samples_before = len(self.season.state.samples)
                write, status, details = C.decide_season(
                    now, self.season.settings, self.season.state, mode=None if mode is None else int(mode),
                    outside=num("T3Frischluft"), holiday=self._holiday(),
                )
                self.season.status, self.season.details = status, details
                if write is not None:
                    changed = True
                    await self.async_save()  # saved first: after a restart it knows when it last switched
                    await self._write("Betriebsart", write, f"automatic summer/winter: mode {'Summer' if write == C.MODE_SUMMER else 'Winter'}")
                elif len(self.season.state.samples) != samples_before:
                    changed = True  # a new outdoor temperature: keep it across restarts
            if changed:
                await self.async_save()
            self.cooling.notify()
            self.boost.notify()
            self.season.notify()

    async def _write(self, key: str, value: float, what: str) -> None:
        _LOGGER.info("Proxon %s", what)
        try:
            await self.coordinator.async_write(key, value)
        except HomeAssistantError as err:
            _LOGGER.warning("Proxon %s failed: %s", what, err)
