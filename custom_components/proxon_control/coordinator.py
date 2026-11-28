"""Reads all values at the chosen interval (default 10 seconds) and writes changes with read-back."""
from __future__ import annotations

from datetime import timedelta
import logging
import time
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AuthError, BridgeApi, DirectApi, HybridApi, ProxonError, WriteNotAccepted
from .const import (
    CONF_READ_ONLY,
    CONF_SCAN_INTERVAL,
    CONF_SHOWER_FLOW,
    CONF_SHOWER_TEMP,
    CONF_WATER_HEATER_POWER,
    CONF_WATER_PUMP_POWER,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOWER_FLOW,
    DEFAULT_SHOWER_TEMP,
    DEFAULT_WATER_HEATER_POWER,
    DEFAULT_WATER_PUMP_POWER,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .registers import SCHEDULE_KEYS, HeatingTracker, active_faults, allowed_during_fault, hot_liters, shower_minutes
from .runtime import MAX_GAP_SECONDS, RuntimeTracker
from .schedule import clock_drift

if TYPE_CHECKING:
    from .comfort_manager import ComfortManager
    from .energy_manager import EnergyManager
    from .holiday import HolidayMode

_LOGGER = logging.getLogger(__name__)

# the weekly schedule changes rarely: read it every 5 minutes, not with every query
SCHEDULE_SECONDS = 300
# a standing fault is reported by the unit only now and then (seen on a real unit: for 30-90 seconds about every 10 minutes,
# all fault words 0 in between): a fault counts until the unit has reported none for this long
FAULT_HOLD = timedelta(minutes=15)


class ProxonCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """The values of the unit (numbers, plus room names and the connection path as text) and the managers using them."""

    # set up by __init__ before the entities are created
    holiday: HolidayMode
    energy: EnergyManager
    comfort: ComfortManager

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: HybridApi | DirectApi | BridgeApi) -> None:
        seconds = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        seconds = max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, seconds))
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=seconds))
        self.entry = entry
        self.api = api
        self._rooms_logged = False
        self._schedule: dict[str, float] = {}
        self._schedule_read_at: float | None = None
        # the last write the unit didn't take (shown by the sensor "Last write error")
        self.last_write_error: dict | None = None
        self.write_errors = 0
        self.device_id: str | None = None  # the appliance's device (rooms and schedule days are linked to it)
        # how this household showers (°C, l/min): for the shower supply and its target
        self.shower = (float(entry.options.get(CONF_SHOWER_TEMP, DEFAULT_SHOWER_TEMP)), float(entry.options.get(CONF_SHOWER_FLOW, DEFAULT_SHOWER_FLOW)))
        # below how many minutes of shower supply "hot water low" comes on (set by its number entity, restored at start)
        self.shower_low_limit = 10.0
        # how often / how long compressor and immersion heater ran today (kept across restarts)
        self.runtime = RuntimeTracker()
        # which rooms' heating elements heat, by the unit's thresholds (needs the previous state: switch-on/off gap)
        self.heating = HeatingTracker()
        # the last fault words the unit reported, and when (see faults())
        self.last_fault: tuple[Any, dict[str, int]] | None = None
        self._runtime_store: Store[dict] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}.runtime")

    async def async_load_runtime(self) -> None:
        self.runtime.load(await self._runtime_store.async_load() or {})

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data: dict[str, Any] = await self.hass.async_add_executor_job(self.api.read)
            if self._schedule_read_at is None or time.monotonic() - self._schedule_read_at >= SCHEDULE_SECONDS:
                try:
                    self._schedule.update(await self.hass.async_add_executor_job(self.api.read_schedule))
                    self._schedule_read_at = time.monotonic()
                except ProxonError as err:
                    _LOGGER.warning("Reading the weekly schedule failed: %s", err)
            data = {**data, **self._schedule}
            # how far the unit's clock is off (it can't be set over the network; the weekly schedule runs on it)
            if (drift := clock_drift(data, dt_util.now())) is not None:
                data["UhrAbweichung"] = float(drift)
            data.update(self.heating.update(data))
            data.update(self.water_power(data))
            # the shower supply as this household showers (the unit's reading assumes 40 °C and 8 l/min)
            if (minutes := shower_minutes(data, *self.shower)) is not None:
                data["WarmwasserDuschminuten"] = minutes
                data["WarmwasserHeissLiter"] = hot_liters(data, self.shower[0])
            interval = self.update_interval.total_seconds() if self.update_interval else 0
            data.update(self.runtime.update(data, dt_util.now(), max(MAX_GAP_SECONDS, 3 * interval)))
            self._runtime_store.async_delay_save(self.runtime.dump, 120)
            if not self._rooms_logged:
                self._rooms_logged = True
                # shows which rooms the unit reports (helps when rooms are missing or too many)
                _LOGGER.info(
                    "Proxon rooms: connected=%s names=%s",
                    {k: data.get(k) for k in sorted(data) if k.endswith("Verbunden") or k.startswith("NBEverbunden")},
                    {k: data.get(k) for k in sorted(data) if k.endswith("name")},
                )
            return data
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ProxonError as err:
            raise UpdateFailed(str(err)) from err

    def water_power(self, data: dict[str, Any]) -> dict[str, float]:
        """Power of the hot-water module, estimated: its rated power while its compressor / heater runs (the unit doesn't
        measure it). Only with the hot-water module."""
        if "T300Betriebsart" not in data or "T300RelaisKompressor" not in data:
            return {}
        rated = self.water_rated_power()
        return {"LeistungWarmwasserWP": rated["LeistungWarmwasserWP"] if data.get("T300RelaisKompressor") else 0.0,
                "LeistungHeizstab": rated["LeistungHeizstab"] if data.get("T300RelaisHeizstab") else 0.0}

    def water_rated_power(self) -> dict[str, float]:
        """Rated power (W) of the hot-water heat pump and the immersion heater: the datasheet's, or as set in the options."""
        options = self.config_entry.options if self.config_entry else {}
        return {"LeistungWarmwasserWP": float(options.get(CONF_WATER_PUMP_POWER, DEFAULT_WATER_PUMP_POWER)),
                "LeistungHeizstab": float(options.get(CONF_WATER_HEATER_POWER, DEFAULT_WATER_HEATER_POWER))}

    def faults(self) -> dict[str, int]:
        """Fault words that count as a fault (key -> 16-bit word): the ones the unit reports now, else the last ones it
        reported, for FAULT_HOLD after that. The fault sensor, the repair notice and the panel all use this."""
        now, current = dt_util.utcnow(), active_faults(self.data or {})
        if current:
            if self.last_fault is None or self.last_fault[1] != current:
                _LOGGER.warning("The unit reports a fault: %s", ", ".join(f"{k} = 0x{v:04X}" for k, v in current.items()))
            self.last_fault = (now, current)
            return current
        if self.last_fault is not None and now - self.last_fault[0] < FAULT_HOLD:
            return self.last_fault[1]
        if self.last_fault is not None:
            _LOGGER.info("The unit has reported no fault for %s minutes", int(FAULT_HOLD.total_seconds() // 60))
            self.last_fault = None
        return {}

    @property
    def read_only(self) -> bool:
        """Read-only mode (option): values are read as usual, but nothing is written to the unit."""
        return bool(self.entry.options.get(CONF_READ_ONLY))

    async def async_write(self, key: str, value: float) -> None:
        """Write a value and read it back from the unit. What the unit really reports is what is shown afterwards;
        if it did not take over the value, the change is reported as failed. While the unit reports a fault, only harmless
        changes are written (switching off, ventilation level, room temperatures). In read-only mode nothing is written.
        Every write of the integration (entities, actions, holiday mode, managers) goes through here."""
        if self.read_only:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="write_blocked_read_only", translation_placeholders={"name": key}
            )
        faults = active_faults(self.data or {})
        if faults and not allowed_during_fault(key, value):
            self._write_failed(key, value, "fault")
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="write_blocked_fault",
                translation_placeholders={"name": key, "words": ", ".join(f"{k} = 0x{v:04X}" for k, v in faults.items())},
            )
        try:
            got = await self.hass.async_add_executor_job(self.api.write, key, value)
        except WriteNotAccepted as err:
            self._write_failed(key, value, "not_accepted", err.got)
            if err.values:  # show what the unit really holds
                self._remember_schedule(err.values)
                self.async_set_updated_data({**(self.data or {}), **err.values})
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_not_accepted",
                translation_placeholders={"name": err.key or key, "wanted": f"{err.wanted:g}", "actual": "?" if err.got is None else f"{err.got:g}"},
            ) from err
        except ProxonError as err:
            self._write_failed(key, value, "no_connection")
            raise HomeAssistantError(f"Proxon: {err}") from err
        self._remember_schedule(got)
        self.async_set_updated_data({**(self.data or {}), **got})
        await self.async_request_refresh()

    def _write_failed(self, key: str, value: float, reason: str, got: float | None = None) -> None:
        self.write_errors += 1
        self.last_write_error = {"time": dt_util.utcnow(), "name": key, "wanted": value, "got": got, "reason": reason}
        self.async_update_listeners()

    def _remember_schedule(self, values: dict) -> None:
        self._schedule.update({k: v for k, v in values.items() if k in SCHEDULE_KEYS})
