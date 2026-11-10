"""Setup dialog: log in with Device ID + password (like the original app), or use the bridge add-on."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .api import AuthError, BridgeApi, DirectApi, ProxonError
from .const import (
    CONF_CONNECTION,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONNECTION_BRIDGE,
    CONNECTION_DIRECT,
    DEFAULT_PORT,
    DOMAIN,
)
from .nabto import library_supported

_LOGGER = logging.getLogger(__name__)


class ProxonConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=[CONNECTION_DIRECT, CONNECTION_BRIDGE])

    async def _test(self, api: DirectApi | BridgeApi) -> str | None:
        try:
            await self.hass.async_add_executor_job(api.test)
        except AuthError:
            return "invalid_auth"
        except ProxonError as err:
            _LOGGER.warning("Proxon connection test failed: %s", err)
            return "cannot_connect"
        except Exception:  # noqa: BLE001 - shown as a generic error in the dialog
            _LOGGER.exception("Unexpected error while testing the Proxon connection")
            return "unknown"
        finally:
            await self.hass.async_add_executor_job(api.close)
        return None

    async def async_step_direct(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if not library_supported():
            return self.async_abort(reason="unsupported_system")
        if user_input is not None:
            device = user_input[CONF_DEVICE_ID].strip()
            await self.async_set_unique_id(device.lower())
            self._abort_if_unique_id_configured()
            api = DirectApi(device, user_input[CONF_PASSWORD], self.hass.config.path(DOMAIN))
            err = await self._test(api)
            if err is None:
                return self.async_create_entry(
                    title=f"Proxon {device}",
                    data={CONF_CONNECTION: CONNECTION_DIRECT, CONF_DEVICE_ID: device, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )
            errors["base"] = err
        schema = vol.Schema({vol.Required(CONF_DEVICE_ID): str, vol.Required(CONF_PASSWORD): str})
        return self.async_show_form(step_id="direct", data_schema=self.add_suggested_values_to_schema(schema, user_input), errors=errors)

    async def async_step_bridge(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port = user_input[CONF_HOST].strip(), user_input[CONF_PORT]
            await self.async_set_unique_id(f"bridge-{host}-{port}".lower())
            self._abort_if_unique_id_configured()
            err = await self._test(BridgeApi(host, port))
            if err is None:
                return self.async_create_entry(
                    title="Proxon (Bridge)",
                    data={CONF_CONNECTION: CONNECTION_BRIDGE, CONF_HOST: host, CONF_PORT: port},
                )
            errors["base"] = err
        schema = vol.Schema({vol.Required(CONF_HOST, default="homeassistant.local"): str, vol.Required(CONF_PORT, default=DEFAULT_PORT): int})
        return self.async_show_form(step_id="bridge", data_schema=self.add_suggested_values_to_schema(schema, user_input), errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            api = DirectApi(entry.data[CONF_DEVICE_ID], user_input[CONF_PASSWORD], self.hass.config.path(DOMAIN))
            err = await self._test(api)
            if err is None:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]})
            errors["base"] = err
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"device_id": entry.data.get(CONF_DEVICE_ID, "")},
            errors=errors,
        )
