"""Every connected room as a thermostat: current and target temperature, and whether the room's electric heating element may help.

Modes: "Auto" = the unit heats/cools the room itself with the heat pump (heating element off),
"Heat" = additionally the room's electric heating element is released. There is no "Off": the unit always keeps the room's target.
What the unit is doing right now comes from the compressor and the 4-way valve, like the status line of the original app
(the room's own status value turned out not to mean "heating now" on a real unit).
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity, room_device
from .registers import MODE_OFF, ROOM_COUNT, room_base, room_connected, room_demand, room_heating, room_target, room_write

# ranges of the original app: living room 10-30 °C; other rooms 14-26 °C and at most 3 °C around the room's own base value
LIVING_ROOM_RANGE = (10.0, 30.0)
OTHER_ROOM_RANGE = (14.0, 26.0)
ROOM_OFFSET_LIMIT = 3.0


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    async_add_entities(ProxonRoomThermostat(coordinator, i) for i in range(ROOM_COUNT) if room_connected(data, i) and room_target(data, i) is not None)


# Home Assistant 2026.11 renamed the temperature properties of thermostats to native_* (the old names stop working in 2027.11).
# Older versions (from 2026.3, the oldest this integration supports) only know the old names, so both are served.
NATIVE_NAMES = hasattr(ClimateEntity, "native_current_temperature")


class ProxonRoomThermostat(ProxonEntity, ClimateEntity):
    if NATIVE_NAMES:
        _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    else:
        _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.AUTO, HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_precision = 0.1

    def __init__(self, coordinator, room: int) -> None:
        super().__init__(coordinator, f"NBE{room}Thermostat", "room_thermostat", device=room_device(coordinator, room))
        self._attr_name = None  # the thermostat is the room's main entity: it carries the room device's name
        self._room = room
        # the living room's target is stored in hundredths of a degree (half degrees possible);
        # the other rooms store a whole-degree offset to their own base value
        self._attr_target_temperature_step = 0.5 if room == 0 else 1.0

    @property
    def _data(self) -> dict:
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and room_target(self._data, self._room) is not None

    @property
    def native_current_temperature(self) -> float | None:
        v = self._data.get(f"NBE{self._room}Temperatur")
        return float(v) if isinstance(v, (int, float)) else None

    @property
    def native_target_temperature(self) -> float | None:
        return room_target(self._data, self._room)

    if not NATIVE_NAMES:
        current_temperature = native_current_temperature
        target_temperature = native_target_temperature

    @property
    def min_temp(self) -> float:
        if self._room == 0:
            return LIVING_ROOM_RANGE[0]
        base = room_base(self._data, self._room)
        return OTHER_ROOM_RANGE[0] if base is None else max(OTHER_ROOM_RANGE[0], base - ROOM_OFFSET_LIMIT)

    @property
    def max_temp(self) -> float:
        if self._room == 0:
            return LIVING_ROOM_RANGE[1]
        base = room_base(self._data, self._room)
        return OTHER_ROOM_RANGE[1] if base is None else min(OTHER_ROOM_RANGE[1], base + ROOM_OFFSET_LIMIT)

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT if self._data.get(f"NBE{self._room}PTC") else HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction | None:
        data = self._data
        mode = data.get("Betriebsart")
        if mode is not None and int(mode) == MODE_OFF:
            return HVACAction.OFF
        if room_heating(data, self._room):
            return HVACAction.HEATING  # the room's heating element heats (released and the room too cold)
        rpm = data.get("DrehzahlKompressor")
        if rpm is None:
            return None
        if rpm > 0:
            return HVACAction.COOLING if data.get("Kuehlbetrieb4Wegeventil") else HVACAction.HEATING
        return HVACAction.FAN  # only ventilating

    @property
    def extra_state_attributes(self) -> dict:
        # too_cold / at_target / warmer, as the room panel's LED shows it
        return {"heat_demand": room_demand(self._data, self._room), "heating_element_heats": room_heating(self._data, self._room)}

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (target := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        key, raw = room_write(self._data, self._room, float(target))
        await self.coordinator.async_write(key, raw)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.coordinator.async_write(f"NBE{self._room}PTC", 1 if hvac_mode is HVACMode.HEAT else 0)
