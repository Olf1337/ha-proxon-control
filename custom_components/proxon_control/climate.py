"""Every connected room as a thermostat: current and target temperature, heating element on/off, "is heating" state."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity, room_name
from .registers import ROOM_COUNT, room_base, room_connected, room_target, room_write

# ranges of the original app: living room 10-30 °C; other rooms 14-26 °C and at most 3 °C around the room's own base value
LIVING_ROOM_RANGE = (10.0, 30.0)
OTHER_ROOM_RANGE = (14.0, 26.0)
ROOM_OFFSET_LIMIT = 3.0


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    async_add_entities(ProxonRoomThermostat(coordinator, i) for i in range(ROOM_COUNT) if room_connected(data, i) and room_target(data, i) is not None)


class ProxonRoomThermostat(ProxonEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    _attr_precision = 0.1

    def __init__(self, coordinator, room: int) -> None:
        super().__init__(coordinator, f"NBE{room}Thermostat", "room_thermostat", {"room": room_name(room, coordinator.data)})
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
    def current_temperature(self) -> float | None:
        v = self._data.get(f"NBE{self._room}Temperatur")
        return float(v) if isinstance(v, (int, float)) else None

    @property
    def target_temperature(self) -> float | None:
        return room_target(self._data, self._room)

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
        return HVACMode.HEAT if self._data.get(f"NBE{self._room}PTC") else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode is HVACMode.OFF:
            return HVACAction.OFF
        return HVACAction.HEATING if self._data.get(f"NBE{self._room}Status") else HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (target := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        key, raw = room_write(self._data, self._room, float(target))
        await self.coordinator.async_write(key, raw)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.coordinator.async_write(f"NBE{self._room}PTC", 1 if hvac_mode is HVACMode.HEAT else 0)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)
