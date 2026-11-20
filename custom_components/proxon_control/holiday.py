"""Holiday mode as the original app does it, with restore.

Switching on saves the current values and then sets: ventilation level 1, living room 18 °C, every other room to its lowest
value (offset −3 °C), all room heating elements off, hot-water heat pump off.
Switching off writes the saved values back in the app's order: hot-water heat pump first, after 2 seconds the immersion
heater, then the rest. The saved values are kept on disk, so a restart of Home Assistant in between loses nothing.
The unit's own operating mode 5 ("holiday") is deliberately not written: the manufacturer disabled it in app 1.7.4 and its
effect on the controller is unknown. (Sequence as documented by the ha-lan-proxon project, MIT licence.)

Holiday plan: departure and return as dates. Holiday mode switches itself on at the departure and off LEAD hours before the
return (so house and water are warm again), checked once a minute. The plan is cleared afterwards, and also when holiday
mode is switched off by hand while the plan has started it.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .registers import ROOM_COUNT, room_connected

_LOGGER = logging.getLogger(__name__)

HOLIDAY_LIVING_ROOM = 18.0
HOLIDAY_ROOM_OFFSET = -3
HOLIDAY_LEVEL = 1
HEAT_PUMP_KEY = "T300Betriebsart"
HEATER_KEY = "E-Heizstab"
DEFAULT_LEAD_H = 6.0  # back on this many hours before the return
PLAN_CHECK = timedelta(minutes=1)


def plan_action(now: datetime, start: datetime | None, end: datetime | None, lead_h: float, *, active: bool,
                started: bool) -> str | None:
    """What the holiday plan does now: "on" (departure reached), "off" (time to warm up before the return), "clear" (the plan
    is over or can't work) or None."""
    if start is None or end is None:
        return None
    back = end - timedelta(hours=lead_h)
    if back <= start:  # shorter than the warm-up: nothing to do
        return "clear" if now >= start else None
    if now >= back:
        return "off" if active else "clear"
    if now >= start and not active and not started:
        return "on"
    return None


class HolidayMode:
    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str) -> None:
        self.coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.{entry_id}.holiday")
        self._state: dict[str, Any] = {"active": False, "saved": {}}
        self._lock = asyncio.Lock()
        self._plan_lock = asyncio.Lock()
        self.restore_delay = 2.0
        self._hass = hass
        self._updates: list[CALLBACK_TYPE] = []

    async def async_load(self) -> None:
        if data := await self._store.async_load():
            self._state = data

    @property
    def active(self) -> bool:
        return bool(self._state.get("active"))

    # ---- holiday plan ----
    @property
    def plan(self) -> dict[str, Any]:
        return dict(self._state.get("plan") or {})

    def _plan_time(self, key: str) -> datetime | None:
        v = self.plan.get(key)
        try:
            return datetime.fromisoformat(v) if v else None
        except (TypeError, ValueError):
            return None

    @property
    def plan_start(self) -> datetime | None:
        return self._plan_time("start")

    @property
    def plan_end(self) -> datetime | None:
        return self._plan_time("end")

    @property
    def lead_h(self) -> float:
        lead = self._state.get("lead_h")
        return float(lead) if isinstance(lead, (int, float)) else DEFAULT_LEAD_H

    @property
    def back_on_at(self) -> datetime | None:
        """When holiday mode goes off again (the end minus the warm-up)."""
        end = self.plan_end
        return None if end is None else end - timedelta(hours=self.lead_h)

    @callback
    def add_listener(self, update: CALLBACK_TYPE) -> CALLBACK_TYPE:
        self._updates.append(update)
        return lambda: self._updates.remove(update)

    def _notify(self) -> None:
        for update in list(self._updates):
            update()

    async def async_set_plan(self, **changes: Any) -> None:
        """start / end (datetime or None) and lead_h; a changed plan starts afresh."""
        plan = self.plan
        for key in ("start", "end"):
            if key in changes:
                v = changes[key]
                plan[key] = dt_util.as_utc(v).isoformat() if v else None
        plan["started"] = False
        self._state = {**self._state, "plan": plan}
        if "lead_h" in changes:
            self._state["lead_h"] = float(changes["lead_h"])
        await self._store.async_save(self._state)
        self._notify()
        await self.async_check_plan()

    async def async_clear_plan(self) -> None:
        self._state = {**self._state, "plan": {}}
        await self._store.async_save(self._state)
        self._notify()

    @callback
    def async_start(self) -> CALLBACK_TYPE:
        """Check the plan once a minute; returns the function that stops it."""
        @callback
        def tick(_now: datetime) -> None:
            if self.plan.get("start") or self.plan.get("end"):
                self._hass.async_create_task(self.async_check_plan(), "proxon holiday plan")
        return async_track_time_interval(self._hass, tick, PLAN_CHECK, cancel_on_shutdown=True)

    async def async_check_plan(self, now: datetime | None = None) -> None:
        async with self._plan_lock:
            now = now or dt_util.utcnow()
            plan = self.plan
            action = plan_action(now, self.plan_start, self.plan_end, self.lead_h, active=self.active,
                                 started=bool(plan.get("started")))
            if action == "on":
                plan["started"] = True  # also when switching on fails (read only): tried once, not every minute
                self._state = {**self._state, "plan": plan}
                await self._store.async_save(self._state)
                _LOGGER.info("Holiday plan: departure, holiday mode on")
                try:
                    await self.async_turn_on()
                except HomeAssistantError as err:
                    _LOGGER.warning("Holiday plan: holiday mode could not be switched on: %s", err)
            elif action == "off":
                _LOGGER.info("Holiday plan: back soon, holiday mode off")
                try:
                    await self.async_turn_off()
                except HomeAssistantError as err:
                    _LOGGER.warning("Holiday plan: holiday mode could not be switched off: %s", err)
                    return  # tried again in a minute
                await self.async_clear_plan()
            elif action == "clear":
                await self.async_clear_plan()
            self._notify()

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
        # read only: refused before anything is saved, so holiday mode isn't marked active without having written anything
        if self.coordinator.read_only:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="holiday_read_only")
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
            self._state = {**self._state, "active": True, "saved": saved}
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
            # switched off (by hand or by the plan) after the plan switched it on: the plan is done
            plan = {} if self.plan.get("started") else self.plan
            self._state = {**self._state, "active": False, "saved": {}, "plan": plan}
            await self._store.async_save(self._state)
            _LOGGER.info("Holiday mode off, %d values restored", len(saved))
        self._notify()
