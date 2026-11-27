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
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
import voluptuous as vol

from .api import MODE_LOCAL, AuthError, BridgeApi, HybridApi, ProxonError, TokenError, connect
from .const import (
    CONF_BASEMENT,
    CONF_CONNECTION,
    CONF_DEVICE_ID,
    CONF_FEED_IN_NEGATIVE,
    CONF_FIXED_PRICE,
    CONF_HOST,
    CONF_HOUSE_PHOTO,
    CONF_LOCAL_HOST,
    CONF_MODE,
    CONF_PANEL_LOOK,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_PRICE_SENSOR,
    CONF_READ_ONLY,
    CONF_SCAN_INTERVAL,
    CONF_SHOWER_FLOW,
    CONF_SHOWER_TEMP,
    CONF_SURPLUS_SENSOR,
    CONF_TILES_ACCENT,
    CONF_TILES_LAYOUT,
    CONF_TILES_SIZE,
    CONF_TOKEN,
    CONF_UPPER_FLOOR,
    CONF_WATER_HEATER_POWER,
    CONF_WATER_PUMP_POWER,
    CONNECTION_BRIDGE,
    CONNECTION_DIRECT,
    DEFAULT_MODE,
    DEFAULT_PANEL_LOOK,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SHOWER_FLOW,
    DEFAULT_SHOWER_TEMP,
    DEFAULT_WATER_HEATER_POWER,
    DEFAULT_WATER_PUMP_POWER,
    DOMAIN,
    ENTRY_MINOR_VERSION,
    ENTRY_VERSION,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    MODES,
    PANEL_LOOKS,
    TILES_ACCENTS,
    TILES_DEFAULTS,
    TILES_LAYOUTS,
    TILES_SIZES,
)
from .entity import guess_floor, house_rooms, room_name
from .nabto import library_supported

_LOGGER = logging.getLogger(__name__)


def mode_selector() -> SelectSelector:
    """Home network first / home network only / Proxon server only. Without Nabto's library: home network only."""
    options = MODES if library_supported() else [MODE_LOCAL]
    return SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST, translation_key=CONF_MODE))


class ProxonOptionsFlow(OptionsFlowWithReload):
    """"Configure" dialog: how often the unit is asked for its values, and whether Home Assistant may change anything."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            data: dict[str, Any] = {CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])}
            if user_input.get(CONF_READ_ONLY):
                data[CONF_READ_ONLY] = True
            for key in (CONF_SURPLUS_SENSOR, CONF_PRICE_SENSOR):
                if user_input.get(key):
                    data[key] = user_input[key]
            if user_input.get(CONF_FEED_IN_NEGATIVE):
                data[CONF_FEED_IN_NEGATIVE] = True
            if (price := user_input.get(CONF_FIXED_PRICE)) and float(price) > 0:
                data[CONF_FIXED_PRICE] = float(price)
            for key, default in ((CONF_WATER_PUMP_POWER, DEFAULT_WATER_PUMP_POWER), (CONF_WATER_HEATER_POWER, DEFAULT_WATER_HEATER_POWER)):
                if user_input.get(key) and int(user_input[key]) != default:  # kept only when it differs from the datasheet
                    data[key] = int(user_input[key])
            if user_input.get(CONF_PANEL_LOOK, DEFAULT_PANEL_LOOK) != DEFAULT_PANEL_LOOK:
                data[CONF_PANEL_LOOK] = user_input[CONF_PANEL_LOOK]
            for key, choice in TILES_DEFAULTS.items():  # kept only when it differs from the tile wall's default
                if user_input.get(key, choice) != choice:
                    data[key] = user_input[key]
            for key, usual in ((CONF_SHOWER_TEMP, DEFAULT_SHOWER_TEMP), (CONF_SHOWER_FLOW, DEFAULT_SHOWER_FLOW)):
                if user_input.get(key) is not None and float(user_input[key]) != usual:
                    data[key] = float(user_input[key])
            rooms = self._rooms()
            for key, floor in ((CONF_UPPER_FLOOR, 1), (CONF_BASEMENT, -1)):  # kept only when it differs from the guess
                if rooms and key in user_input:
                    chosen = sorted(set(user_input[key]) & set(rooms), key=int)
                    if chosen != self._guess(rooms, floor):
                        data[key] = chosen
            if photo := (user_input.get(CONF_HOUSE_PHOTO) or "").strip():
                if not photo.startswith(("/", "http://", "https://")):
                    errors = {CONF_HOUSE_PHOTO: "photo_path"}
                    return self._form(user_input, errors)
                data[CONF_HOUSE_PHOTO] = photo
            if self._login:  # kept only where it differs from the setup (an empty address: find the unit automatically)
                setup = self.config_entry.data
                mode, host = user_input.get(CONF_MODE, DEFAULT_MODE), (user_input.get(CONF_LOCAL_HOST) or "").strip()
                if mode != (setup.get(CONF_MODE) or DEFAULT_MODE):
                    data[CONF_MODE] = mode
                if host != (setup.get(CONF_LOCAL_HOST) or ""):
                    data[CONF_LOCAL_HOST] = host
            return self.async_create_entry(data=data)
        return self._form()

    def _form(self, user_input: dict[str, Any] | None = None, errors: dict[str, str] | None = None) -> ConfigFlowResult:
        connection = (
            {
                vol.Required(CONF_MODE, default=DEFAULT_MODE): mode_selector(),
                vol.Optional(CONF_LOCAL_HOST): str,
            }
            if self._login
            else {}
        )
        rooms = self._rooms()
        house: dict[Any, Any] = {}
        if rooms:  # which rooms lie upstairs and in the basement (rooms on the dashboard)
            for key in (CONF_UPPER_FLOOR, CONF_BASEMENT):
                house[vol.Optional(key)] = SelectSelector(SelectSelectorConfig(
                    options=[SelectOptionDict(value=i, label=name) for i, name in rooms.items()], multiple=True,
                    mode=SelectSelectorMode.LIST,
                ))
        house[vol.Optional(CONF_HOUSE_PHOTO)] = TextSelector()
        schema = vol.Schema(
            {
                **connection,
                # read only: show all values, never change anything on the unit
                vol.Optional(CONF_READ_ONLY, default=False): BooleanSelector(),
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
                    NumberSelectorConfig(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL, step=1, unit_of_measurement="s", mode=NumberSelectorMode.BOX)
                ),
                # hot water as a store for solar surplus / cheap electricity
                vol.Optional(CONF_SURPLUS_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor", device_class="power")),
                vol.Optional(CONF_FEED_IN_NEGATIVE, default=False): BooleanSelector(),
                vol.Optional(CONF_PRICE_SENSOR): EntitySelector(EntitySelectorConfig(domain="sensor")),
                # a fixed tariff: the price for the electricity cost when no price sensor is chosen
                vol.Optional(CONF_FIXED_PRICE): NumberSelector(
                    NumberSelectorConfig(min=0, max=200, step=0.01, unit_of_measurement="ct/kWh", mode=NumberSelectorMode.BOX)
                ),
                # the hot-water module's power for its estimated consumption (datasheet T300 as default)
                vol.Optional(CONF_WATER_PUMP_POWER, default=DEFAULT_WATER_PUMP_POWER): NumberSelector(
                    NumberSelectorConfig(min=100, max=2000, step=10, unit_of_measurement="W", mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_WATER_HEATER_POWER, default=DEFAULT_WATER_HEATER_POWER): NumberSelector(
                    NumberSelectorConfig(min=500, max=9000, step=100, unit_of_measurement="W", mode=NumberSelectorMode.BOX)
                ),
                # the look of the page "Proxon"
                vol.Optional(CONF_PANEL_LOOK, default=DEFAULT_PANEL_LOOK): SelectSelector(
                    SelectSelectorConfig(options=PANEL_LOOKS, mode=SelectSelectorMode.LIST, translation_key=CONF_PANEL_LOOK)
                ),
                # the tile wall: rooms as a row or a grid, tile size, accent colour
                **{vol.Optional(key, default=TILES_DEFAULTS[key]): SelectSelector(
                    SelectSelectorConfig(options=opts, mode=SelectSelectorMode.DROPDOWN, translation_key=key))
                   for key, opts in ((CONF_TILES_LAYOUT, TILES_LAYOUTS), (CONF_TILES_SIZE, TILES_SIZES), (CONF_TILES_ACCENT, TILES_ACCENTS))},
                # the shower supply: how warm and how much water a shower takes here
                vol.Optional(CONF_SHOWER_TEMP, default=DEFAULT_SHOWER_TEMP): NumberSelector(
                    NumberSelectorConfig(min=37, max=42, step=0.5, unit_of_measurement="°C", mode=NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_SHOWER_FLOW, default=DEFAULT_SHOWER_FLOW): NumberSelector(
                    NumberSelectorConfig(min=5, max=12, step=0.5, unit_of_measurement="l/min", mode=NumberSelectorMode.BOX)
                ),
                **house,
            }
        )
        current = {**self.config_entry.data, **self.config_entry.options}
        current.pop(CONF_PASSWORD, None)
        for key, floor in ((CONF_UPPER_FLOOR, 1), (CONF_BASEMENT, -1)):
            if rooms and key not in current:
                current[key] = self._guess(rooms, floor)
        if user_input:
            current.update(user_input)
        return self.async_show_form(step_id="init", data_schema=self.add_suggested_values_to_schema(schema, current), errors=errors)

    def _rooms(self) -> dict[str, str]:
        """Room number -> name of the rooms with a thermostat (empty while the integration isn't loaded)."""
        coordinator = getattr(self.config_entry, "runtime_data", None)
        data = getattr(coordinator, "data", None) or {}
        return {str(i): room_name(i, data) for i in house_rooms(data)} if data else {}

    def _guess(self, rooms: dict[str, str], floor: int = 1) -> list[str]:
        return [i for i, name in rooms.items() if guess_floor(name) == floor]

    @property
    def _login(self) -> bool:
        """Logged in with Device ID + password (not through the bridge)."""
        return self.config_entry.data.get(CONF_CONNECTION) != CONNECTION_BRIDGE


class ProxonConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = ENTRY_VERSION
    MINOR_VERSION = ENTRY_MINOR_VERSION

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

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change how the unit is reached without removing it: password, connection and IP address (Device ID + password), or
        address, port and access key (bridge). The Device ID stays, so entities and history stay too. Tested before saving."""
        entry = self._get_reconfigure_entry()
        if entry.data.get(CONF_CONNECTION) == CONNECTION_BRIDGE:
            return await self.async_step_reconfigure_bridge(user_input)
        errors: dict[str, str] = {}
        cloud_possible = library_supported()
        current = {**entry.data, **entry.options}
        if user_input is not None:
            password = user_input.get(CONF_PASSWORD) or entry.data[CONF_PASSWORD]  # empty: keep the one saved
            mode = user_input.get(CONF_MODE, DEFAULT_MODE) if cloud_possible else MODE_LOCAL
            host = (user_input.get(CONF_LOCAL_HOST) or "").strip()
            api = self._login_api(entry.data[CONF_DEVICE_ID], password, mode, host)
            err = await self._test(api, local_only=api.cloud is None)
            if err is None:
                data = {**entry.data, CONF_PASSWORD: password, CONF_MODE: mode}
                data.pop(CONF_LOCAL_HOST, None)
                if host:
                    data[CONF_LOCAL_HOST] = host
                # the same settings kept in the options (Configure) would hide the new ones
                options = {k: v for k, v in entry.options.items() if k not in (CONF_MODE, CONF_LOCAL_HOST)}
                self.hass.config_entries.async_update_entry(entry, options=options)
                return self.async_update_reload_and_abort(entry, data=data)
            errors["base"] = err
        fields: dict[Any, Any] = {vol.Optional(CONF_PASSWORD): str}
        if cloud_possible:
            fields[vol.Required(CONF_MODE, default=current.get(CONF_MODE) or DEFAULT_MODE)] = mode_selector()
        fields[vol.Optional(CONF_LOCAL_HOST)] = str
        suggested = user_input or {CONF_LOCAL_HOST: current.get(CONF_LOCAL_HOST, "")}
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(vol.Schema(fields), suggested),
            description_placeholders={"device_id": entry.data.get(CONF_DEVICE_ID, "")},
            errors=errors,
        )

    async def async_step_reconfigure_bridge(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port = user_input[CONF_HOST].strip(), user_input[CONF_PORT]
            token = (user_input.get(CONF_TOKEN) or "").strip()
            unique_id = f"bridge-{host}-{port}".lower()
            if any(e.unique_id == unique_id for e in self._async_current_entries() if e.entry_id != entry.entry_id):
                return self.async_abort(reason="already_configured")
            err = await self._test(BridgeApi(host, port, token))
            if err is None:
                data = {CONF_CONNECTION: CONNECTION_BRIDGE, CONF_HOST: host, CONF_PORT: port}
                if token:
                    data[CONF_TOKEN] = token
                return self.async_update_reload_and_abort(entry, unique_id=unique_id, data=data)
            errors["base"] = err
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT): int,
                vol.Optional(CONF_TOKEN): str,
            }
        )
        suggested = user_input or {CONF_HOST: entry.data.get(CONF_HOST), CONF_PORT: entry.data.get(CONF_PORT, DEFAULT_PORT),
                                   CONF_TOKEN: entry.data.get(CONF_TOKEN, "")}
        return self.async_show_form(step_id="reconfigure_bridge", data_schema=self.add_suggested_values_to_schema(schema, suggested), errors=errors)

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
