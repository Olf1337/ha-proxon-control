"""Reads all values every 10 seconds and writes changes."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AuthError, BridgeApi, DirectApi, ProxonError
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ProxonCoordinator(DataUpdateCoordinator[dict[str, float]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: DirectApi | BridgeApi) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.api = api
        self._rooms_logged = False

    async def _async_update_data(self) -> dict[str, float]:
        try:
            data = await self.hass.async_add_executor_job(self.api.read)
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
        try:
            await self.hass.async_add_executor_job(self.api.write, key, value)
        except ProxonError as err:
            raise HomeAssistantError(f"Proxon: {err}") from err
        data = dict(self.data or {})
        data[key] = float(value)
        if key == "Intensivlueftung":
            # turning boost on also shows the full boost time right away (as the original does)
            data["IntensivlueftungsRestDauer"] = data.get("IntensivlueftungsDauer", 0.0) if value else 0.0
        self.async_set_updated_data(data)
        await self.async_request_refresh()
