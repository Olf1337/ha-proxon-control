"""Hot water as a store for solar surplus and cheap electricity: settings, timers and writing to the unit.

Settings (the two switches, the limits and the store temperature) and the running state are kept on disk, so they survive a
restart of Home Assistant. The decision rules are in energy.py.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, time, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import energy as E
from . import legionella as L
from .const import CONF_FEED_IN_NEGATIVE, CONF_FIXED_PRICE, CONF_PRICE_SENSOR, CONF_SURPLUS_SENSOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

TARGET_KEY = "SollWassertemperatur"
HEAT_PUMP_KEY = "T300Betriebsart"
HEATER_KEY = "E-Heizstab"
HEATER_TARGET_KEY = "Soll-E-Heizstab-Temperatur"
WATER_KEY = "WarmwasserIstTemperatur"
UNIT_LEGIONELLA_KEY = "Legionellenfunktion"
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
        self._pending = False
        self.legionella = LegionellaFeature(self)

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
            self.legionella.state = L.State.from_dict(data.get("legionella") or {})

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
    def add_entity_listener(self, update: CALLBACK_TYPE) -> CALLBACK_TYPE:
        self._entity_updates.append(update)
        return lambda: self._entity_updates.remove(update)

    def _notify(self) -> None:
        for update in list(self._entity_updates):
            update()
        self.legionella.notify()

    async def _save(self) -> None:
        await self._store.async_save({"settings": vars(self.settings), "state": self.state.to_dict(),
                                      "legionella": self.legionella.state.to_dict()})

    # ---- settings (switches and number entities) ----
    async def async_set(self, **changes: Any) -> None:
        # switching on without what the function needs is refused with a hint, instead of a switch that is on and never heats
        if changes.get("solar_on") and not self.settings.solar_on and not self.entry.options.get(CONF_SURPLUS_SENSOR):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="solar_needs_sensor")
        if changes.get("price_on") and not self.settings.price_on:
            if self._fixed_price() is not None:
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="price_fixed")
            if not self.entry.options.get(CONF_PRICE_SENSOR):
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key="price_needs_sensor")
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

    def surplus_w(self) -> float | None:
        """The solar surplus in W (positive: fed into the grid), or None without a surplus sensor."""
        return self._surplus()

    def _surplus(self) -> float | None:
        value, unit = self._sensor_value(CONF_SURPLUS_SENSOR)
        return None if value is None else E.power_in_watt(value, unit, bool(self.entry.options.get(CONF_FEED_IN_NEGATIVE)))

    def _fixed_price(self) -> float | None:
        """The fixed price from the options (ct/kWh, a fixed tariff), or None."""
        fixed = self.entry.options.get(CONF_FIXED_PRICE)
        return float(fixed) if isinstance(fixed, (int, float)) and fixed > 0 else None

    def price_ct(self) -> float | None:
        """The electricity price now in ct/kWh for the cost: a fixed price from the options (a fixed tariff), else the price
        sensor (a dynamic tariff), else None."""
        fixed = self._fixed_price()
        return fixed if fixed is not None else self._price()

    def _price(self) -> float | None:
        """The price for "cheap power": the price sensor - but not with a fixed tariff (a fixed price is never cheaper, and
        the sensor is then ignored altogether)."""
        if self._fixed_price() is not None:
            return None
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
    def _started(self, hass: HomeAssistant) -> None:
        self._schedule()

    @callback
    def _tick(self, now: datetime) -> None:
        # a @callback runs in Home Assistant's event loop (a plain function would be run in a worker thread)
        self._schedule()

    @callback
    def _schedule(self) -> None:
        if not self.hass.is_running:  # starting up, shutting down or stopped
            return
        # one check at a time: while one runs (e.g. waiting for the slow hot-water module), further ones are left out
        if self._lock.locked() or self._pending:
            return
        self._pending = True
        self.entry.async_create_background_task(self.hass, self._background_evaluate(), "proxon hot water energy manager")

    async def _background_evaluate(self) -> None:
        try:
            if not self._lock.locked():
                await self.async_evaluate()
        finally:
            self._pending = False

    async def async_evaluate(self, now: datetime | None = None) -> None:
        if not self.supported or self.coordinator.read_only:  # read only: nothing may be written, so nothing is started
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
            try:
                await self.legionella.async_evaluate(now)
            except HomeAssistantError as err:
                _LOGGER.warning("Legionella protection: %s", err)
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


class LegionellaFeature:
    """Legionella protection with solar power (rules in legionella.py), as the switch and the status sensor see it."""

    def __init__(self, manager: EnergyManager) -> None:
        self._manager = manager
        self.state = L.State()
        self.status = L.OFF
        self._updates: list[CALLBACK_TYPE] = []

    @property
    def settings(self) -> L.State:  # the switch reads `settings.on`
        return self.state

    @property
    def supported(self) -> bool:
        data = self._manager.coordinator.data or {}
        return self._manager.supported and all(k in data for k in (HEATER_KEY, HEATER_TARGET_KEY, WATER_KEY))

    @property
    def details(self) -> dict[str, Any]:
        """Shown as attributes of the status sensor."""
        due = L.next_due(self.state)
        return {
            "last_done": self.state.last_done.isoformat() if self.state.last_done else None,
            "due_at_the_latest": due.isoformat() if due and self.state.on else None,
            "planned_next": L.next_slot(dt_util.now(), self.state).isoformat() if self.state.plan_on else None,
            "heating_since": self.state.since.isoformat() if self.state.since else None,
            "temperature": L.TEMP,
        }

    @callback
    def add_entity_listener(self, update: CALLBACK_TYPE) -> CALLBACK_TYPE:
        self._updates.append(update)
        return lambda: self._updates.remove(update)

    def notify(self) -> None:
        for update in list(self._updates):
            update()

    async def async_set(self, on: bool | None = None, plan_on: bool | None = None) -> None:
        """Switch "with solar" (`on`) or "planned" (`plan_on`); only one of them is on: switching one on switches the other off."""
        m, st = self._manager, self.state
        want_on = st.on if on is None else on
        want_plan = st.plan_on if plan_on is None else plan_on
        if on:
            want_plan = False
        if plan_on:
            want_on = False
        # read only: switching it either way would write the unit's own legionella function, so it is refused before
        # anything is saved (it would show "on" without doing anything)
        if (want_on, want_plan) != (st.on, st.plan_on) and m.coordinator.read_only:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="legionella_read_only")
        # "with solar" without a surplus sensor would never use the sun: refused with a hint (planned works without one)
        if want_on and not st.on and not m.entry.options.get(CONF_SURPLUS_SENSOR):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="legionella_needs_sensor")
        data, now = m.coordinator.data or {}, dt_util.now()
        was_any, any_now = st.on or st.plan_on, want_on or want_plan
        if want_on and not st.on:
            st.reference = now
        if want_plan and not st.plan_on:
            st.plan_slot = L.last_slot(now, st.plan_day, st.plan_time)  # from the next planned time on, not one just past
        st.on, st.plan_on = want_on, want_plan
        if any_now and not was_any:
            st.unit_function_was_on = bool(data.get(UNIT_LEGIONELLA_KEY))
            await m._save()
            if st.unit_function_was_on:  # the unit's own function would heat at its fixed time as well
                _LOGGER.info("Legionella protection on: the unit's own legionella function off")
                await m.coordinator.async_write(UNIT_LEGIONELLA_KEY, 0)
        elif was_any and not any_now:
            was_on, st.unit_function_was_on = st.unit_function_was_on, False
            await m._save()
            if was_on and UNIT_LEGIONELLA_KEY in data:
                await m.coordinator.async_write(UNIT_LEGIONELLA_KEY, 1)
        else:
            await m._save()
        await m.async_evaluate()

    async def async_set_plan(self, day: int | None = None, at: time | None = None) -> None:
        """Weekday and time of the planned heating (settings of this function only: nothing is written to the unit)."""
        st = self.state
        if day is not None:
            st.plan_day = day
        if at is not None:
            st.plan_time = at.replace(second=0, microsecond=0)
        st.plan_slot = L.last_slot(dt_util.now(), st.plan_day, st.plan_time)  # a time just past waits for next week
        await self._manager._save()
        await self._manager.async_evaluate()

    async def async_set_due_time(self, at: time) -> None:
        """The time of the heating without sun (a setting of this function only: nothing is written to the unit)."""
        self.state.due_time = at.replace(second=0, microsecond=0)
        await self._manager._save()
        await self._manager.async_evaluate()

    def _num(self, key: str) -> float | None:
        v = (self._manager.coordinator.data or {}).get(key)
        return float(v) if isinstance(v, (int, float)) else None

    @property
    def boost_running(self) -> bool:
        comfort = getattr(self._manager.coordinator, "comfort", None)
        return bool(comfort and comfort.boost.state.active)

    async def async_evaluate(self, now: datetime) -> None:
        """Called by the energy manager (under its lock), once a minute and with every new reading."""
        if not self.supported:
            return
        m = self._manager
        holiday = getattr(m.coordinator, "holiday", None)
        blocked = not m.coordinator.last_update_success or bool(holiday and holiday.active)
        water = self._num(WATER_KEY)
        before = self.state.last_done
        action, self.status = L.decide(now, self.state, water=water, surplus_w=m._surplus(),
                                       surplus_limit=float(m.settings.surplus_w), blocked=blocked)
        if action in ("start_solar", "start_due", "start_plan"):
            await self._start(now, {"start_solar": L.SOLAR, "start_plan": L.PLAN}.get(action, L.DUE))
        elif action == "stop":
            await self._stop(now, water is not None and water >= L.REACHED)
        elif self.state.last_done != before and (before is None or now - before > timedelta(hours=1)):
            await m._save()  # the water was hot enough: remember it across restarts (not with every reading)
        await self._notice(now)

    async def _notice(self, now: datetime) -> None:
        """A notice under Repairs while the hot water hasn't reached 60 °C for a week and no legionella protection is on
        (this function or the unit's own one); it goes away by itself."""
        m = self._manager
        if self.state.watching_since is None:
            self.state.watching_since = now
            await m._save()
        protected = self.state.on or self.state.plan_on or bool(self._num(UNIT_LEGIONELLA_KEY))
        days = L.days_without_heat(now, self.state, protected=protected)
        issue_id = f"legionella_risk_{m.entry.entry_id}"
        if days is None:
            ir.async_delete_issue(m.hass, DOMAIN, issue_id)
        else:
            ir.async_create_issue(m.hass, DOMAIN, issue_id, is_fixable=False, is_persistent=False,
                                  severity=ir.IssueSeverity.WARNING, translation_key="legionella_risk",
                                  translation_placeholders={"days": str(days), "temperature": f"{L.TEMP:g}"})

    async def _start(self, now: datetime, source: str) -> None:
        m = self._manager
        heater_target = self._num(HEATER_TARGET_KEY)
        # a heater switched on by the hot-water boost counts as off: the boost leaves it to this function while it heats
        heater_on = bool(self._num(HEATER_KEY)) and not self.boost_running
        L.started(self.state, now, source, heater_target, heater_on)
        await m._save()  # saved before writing: a restart in between still puts the heater back
        _LOGGER.info("Legionella protection: heating to %s °C (%s)", L.TEMP, source)
        if heater_target is None or heater_target < L.TEMP:
            await m.coordinator.async_write(HEATER_TARGET_KEY, L.TEMP)
        await m.coordinator.async_write(HEATER_KEY, 1)

    async def _stop(self, now: datetime, reached: bool) -> None:
        m = self._manager
        saved_target, saved_on = self.state.saved_heater_target, self.state.saved_heater_on
        L.stopped(self.state, now, reached)
        await m._save()
        _LOGGER.info("Legionella protection: %s", "done" if reached else "stopped")
        target = self._num(HEATER_TARGET_KEY)
        # put back only what nobody changed in the meantime
        if saved_target is not None and saved_target < L.TEMP and target is not None and abs(target - L.TEMP) < 0.05:
            await m.coordinator.async_write(HEATER_TARGET_KEY, saved_target)
        if not saved_on and not self.boost_running:
            await m.coordinator.async_write(HEATER_KEY, 0)
