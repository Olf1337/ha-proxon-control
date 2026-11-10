"""Reads all values at the chosen interval (default 10 seconds) and writes changes with read-back."""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthError, BridgeApi, DirectApi, ProxonError, WriteNotAccepted
from .registers import SCHEDULE_KEYS
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_SCAN_INTERVAL, MIN_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# the weekly schedule changes rarely: read it every 5 minutes, not with every query
SCHEDULE_SECONDS = 300


class ProxonCoordinator(DataUpdateCoordinator[dict[str, float]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: DirectApi | BridgeApi) -> None:
        seconds = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        seconds = max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, seconds))
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=timedelta(seconds=seconds))
        self.api = api
        self._rooms_logged = False
        self._schedule: dict[str, float] = {}
        self.holiday = None  # HolidayMode, set up by __init__
        self.energy = None  # EnergyManager, set up by __init__
        self.comfort = None  # ComfortManager (night cooling, hot-water boost), set up by __init__
        self._schedule_read_at: float | None = None

    async def _async_update_data(self) -> dict[str, float]:
        try:
            data = await self.hass.async_add_executor_job(self.api.read)
            if self._schedule_read_at is None or time.monotonic() - self._schedule_read_at >= SCHEDULE_SECONDS:
                try:
                    self._schedule.update(await self.hass.async_add_executor_job(self.api.read_schedule))
                    self._schedule_read_at = time.monotonic()
                except ProxonError as err:
                    _LOGGER.warning("Reading the weekly schedule failed: %s", err)
            data = {**data, **self._schedule}
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
        if it did not take over the value, the change is reported as failed."""
        try:
            got = await self.hass.async_add_executor_job(self.api.write, key, value)
        except WriteNotAccepted as err:
            if err.values:  # show what the unit really holds
                self._remember_schedule(err.values)
                self.async_set_updated_data({**(self.data or {}), **err.values})
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_not_accepted",
                translation_placeholders={"name": err.key or key, "wanted": f"{err.wanted:g}", "actual": "?" if err.got is None else f"{err.got:g}"},
            ) from err
        except ProxonError as err:
            raise HomeAssistantError(f"Proxon: {err}") from err
        self._remember_schedule(got)
        self.async_set_updated_data({**(self.data or {}), **got})
        await self.async_request_refresh()

    def _remember_schedule(self, values: dict) -> None:
        self._schedule.update({k: v for k, v in values.items() if k in SCHEDULE_KEYS})
