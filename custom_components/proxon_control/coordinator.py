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
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_SCAN_INTERVAL, MIN_SCAN_INTERVAL
from .registers import SCHEDULE_KEYS, HeatingTracker, active_faults, allowed_during_fault
from .runtime import MAX_GAP_SECONDS, RuntimeTracker
from .schedule import clock_drift

if TYPE_CHECKING:
    from .comfort_manager import ComfortManager
    from .energy_manager import EnergyManager
    from .holiday import HolidayMode

_LOGGER = logging.getLogger(__name__)

# the weekly schedule changes rarely: read it every 5 minutes, not with every query
SCHEDULE_SECONDS = 300


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
        # how often / how long compressor and immersion heater ran today (kept across restarts)
        self.runtime = RuntimeTracker()
        # which rooms' heating elements heat, by the unit's thresholds (needs the previous state: switch-on/off gap)
        self.heating = HeatingTracker()
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

    async def async_write(self, key: str, value: float) -> None:
        """Write a value and read it back from the unit. What the unit really reports is what is shown afterwards;
        if it did not take over the value, the change is reported as failed. While the unit reports a fault, only harmless
        changes are written (switching off, ventilation level, room temperatures)."""
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
