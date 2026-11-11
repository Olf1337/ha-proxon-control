"""Setup dialog: log in with Device ID + password (like the original app) - home network and/or Proxon server -, or use the bridge add-on."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from .api import MODE_LOCAL, AuthError, BridgeApi, HybridApi, ProxonError, TokenError, connect
from .const import (
    CONF_CONNECTION,
    CONF_DEVICE_ID,
    CONF_FEED_IN_NEGATIVE,
    CONF_HOST,
    CONF_LOCAL_HOST,
    CONF_MODE,
    CONF_PASSWORD,
    CONF_PICTURE_THEME,
    CONF_PORT,
    CONF_PRICE_SENSOR,
    CONF_SCAN_INTERVAL,
    CONF_SURPLUS_SENSOR,
    CONF_TOKEN,
    CONNECTION_BRIDGE,
    CONNECTION_DIRECT,
    DEFAULT_MODE,
    DEFAULT_PICTURE_THEME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MODES,
    PICTURE_THEMES,
)
from .nabto import library_supported

_LOGGER = logging.getLogger(__name__)


def mode_selector() -> SelectSelector:
    """Home network first / home network only / Proxon server only. Without Nabto's library: home network only."""
    options = MODES if library_supported() else [MODE_LOCAL]
    return SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST, translation_key=CONF_MODE))


class ProxonOptionsFlow(OptionsFlowWithReload):
    """"Configure" dialog: how often the unit is asked for its values."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            data: dict[str, Any] = {CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            for key in (CONF_SURPLUS_SENSOR, CONF_PRICE_SENSOR):
                if user_input.get(key):
                    data[key] = user_input[key]
            if user_input.get(CONF_FEED_IN_NEGATIVE):
                data[CONF_FEED_IN_NEGATIVE] = True
            if user_input.get(CONF_PICTURE_THEME, DEFAULT_PICTURE_THEME) != DEFAULT_PICTURE_THEME:
                data[CONF_PICTURE_THEME] = user_input[CONF_PICTURE_THEME]
            if self._login:  # kept only where it differs from the setup (an empty address: find the unit automatically)
                setup = self.config_entry.data
                mode, host = user_input.get(CONF_MODE, DEFAULT_MODE), (user_input.get(CONF_LOCAL_HOST) or "").strip()
                if mode != (setup.get(CONF_MODE) or DEFAULT_MODE):
                    data[CONF_MODE] = mode
                if host != (setup.get(CONF_LOCAL_HOST) or ""):
                    data[CONF_LOCAL_HOST] = host
            return self.async_create_entry(data=data)
        connection = (
            {
                vol.Required(CONF_MODE, default=DEFAULT_MODE): mode_selector(),
                vol.Optional(CONF_LOCAL_HOST): str,
            }
            if self._login
            else {}
        )
        schema = vol.Schema(
            {
                **connection,
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
                    NumberSelectorConfig(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, step=1, unit_of_measurement="s", mode=NumberSelectorMode.BOX)
                ),
                # hot water as a store for solar surplus / cheap electricity
                vol.Optional(CONF_SURPLUS_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor", device_class="power")),
                vol.Optional(CONF_FEED_IN_NEGATIVE, default=False): BooleanSelector(),
                vol.Optional(CONF_PRICE_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
                # dashboard pictures: light / dark
                vol.Optional(CONF_PICTURE_THEME, default=DEFAULT_PICTURE_THEME): SelectSelector(
                    SelectSelectorConfig(options=PICTURE_THEMES, mode=SelectSelectorMode.DROPDOWN, translation_key=CONF_PICTURE_THEME)
                ),
            }
        )
        current = {**self.config_entry.data, **self.config_entry.options}
        current.pop(CONF_PASSWORD, None)
        return self.async_show_form(step_id="init", data_schema=self.add_suggested_values_to_schema(schema, current))

    @property
    def _login(self) -> bool:
        """Logged in with Device ID + password (not through the bridge)."""
        return self.config_entry.data.get(CONF_CONNECTION) != CONNECTION_BRIDGE


class ProxonConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ProxonOptionsFlow:
        return ProxonOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return self.async_show_menu(step_id="user", menu_options=[CONNECTION_DIRECT, CONNECTION_BRIDGE])

    async def _test(self, api: HybridApi | BridgeApi, local_only: bool = False) -> str | None:
        try:
            await self.hass.async_add_executor_job(api.test)
        except AuthError:
            return "invalid_auth"
        except TokenError:
            return "invalid_token"
        except ProxonError as err:
            _LOGGER.warning("Proxon connection test failed: %s", err)
            return "cannot_connect_local" if local_only else "cannot_connect"
        except Exception:  # noqa: BLE001 - shown as a generic error in the dialog
            _LOGGER.exception("Unexpected error while testing the Proxon connection")
            return "unknown"
        finally:
            await self.hass.async_add_executor_job(api.close)
        return None

    def _login_api(self, device: str, password: str, mode: str, host: str | None) -> HybridApi:
        return connect(device, password, self.hass.config.path(DOMAIN), mode, host, library_supported())

    async def async_step_direct(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Device ID + password. Where Nabto's library doesn't exist (e.g. Raspberry Pi), the home network only."""
        errors: dict[str, str] = {}
        cloud_possible = library_supported()
        if user_input is not None:
            device = user_input[CONF_DEVICE_ID].strip()
            mode = user_input.get(CONF_MODE, DEFAULT_MODE) if cloud_possible else MODE_LOCAL
            host = (user_input.get(CONF_LOCAL_HOST) or "").strip()
            await self.async_set_unique_id(device.lower())
            self._abort_if_unique_id_configured()
            api = self._login_api(device, user_input[CONF_PASSWORD], mode, host)
            err = await self._test(api, local_only=api.cloud is None)
            if err is None:
                data = {CONF_CONNECTION: CONNECTION_DIRECT, CONF_DEVICE_ID: device, CONF_PASSWORD: user_input[CONF_PASSWORD], CONF_MODE: mode}
                if host:
                    data[CONF_LOCAL_HOST] = host
                return self.async_create_entry(title=f"Proxon {device}", data=data)
            errors["base"] = err
        fields: dict[Any, Any] = {vol.Required(CONF_DEVICE_ID): str, vol.Required(CONF_PASSWORD): str}
        if cloud_possible:
            fields[vol.Required(CONF_MODE, default=DEFAULT_MODE)] = mode_selector()
        fields[vol.Optional(CONF_LOCAL_HOST)] = str
        return self.async_show_form(
            step_id="direct" if cloud_possible else "local",
            data_schema=self.add_suggested_values_to_schema(vol.Schema(fields), user_input),
            errors=errors,
        )

    async def async_step_local(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """The same dialog on systems without Nabto's library (form shown with its own explanation)."""
        return await self.async_step_direct(user_input)

    async def async_step_bridge(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port = user_input[CONF_HOST].strip(), user_input[CONF_PORT]
            token = (user_input.get(CONF_TOKEN) or "").strip()
            await self.async_set_unique_id(f"bridge-{host}-{port}".lower())
            self._abort_if_unique_id_configured()
            err = await self._test(BridgeApi(host, port, token))
            if err is None:
                data = {CONF_CONNECTION: CONNECTION_BRIDGE, CONF_HOST: host, CONF_PORT: port}
                if token:
                    data[CONF_TOKEN] = token
                return self.async_create_entry(title="Proxon (Bridge)", data=data)
            errors["base"] = err
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default="homeassistant.local"): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_TOKEN, default=""): str,
            }
        )
        return self.async_show_form(step_id="bridge", data_schema=self.add_suggested_values_to_schema(schema, user_input), errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            current = {**entry.data, **entry.options}
            api = self._login_api(entry.data[CONF_DEVICE_ID], user_input[CONF_PASSWORD], current.get(CONF_MODE) or DEFAULT_MODE, current.get(CONF_LOCAL_HOST))
            err = await self._test(api, local_only=api.cloud is None)
            if err is None:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]})
            errors["base"] = err
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"device_id": entry.data.get(CONF_DEVICE_ID, "")},
            errors=errors,
        )
