"""Hot water as a water heater: current and target temperature, and which heat source runs (heat pump, immersion heater, both, off)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    STATE_ELECTRIC,
    STATE_HEAT_PUMP,
    STATE_HIGH_DEMAND,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_TENTHS, STATE_OFF, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .const import DOMAIN
from .entity import ProxonEntity

# Home Assistant 2026.11 renamed the temperature properties of water heaters to native_* (the old names stop working in 2027.11).
# Older versions (from 2026.3, the oldest this integration supports) only know the old names, so both are served.
NATIVE_NAMES = hasattr(WaterHeaterEntity, "native_current_temperature")

# range of the original app for the hot-water target
WATER_RANGE = (20.0, 55.0)
HEAT_PUMP_KEY = "T300Betriebsart"
HEATER_KEY = "E-Heizstab"
TARGET_KEY = "SollWassertemperatur"
CURRENT_KEY = "WarmwasserIstTemperatur"

# operation -> (heat pump on, immersion heater on)
OPERATIONS: dict[str, tuple[int, int]] = {
    STATE_OFF: (0, 0),
    STATE_HEAT_PUMP: (1, 0),
    STATE_HIGH_DEMAND: (1, 1),
    STATE_ELECTRIC: (0, 1),
}


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    # only with the hot-water heat pump (T300)
    if HEAT_PUMP_KEY in data and TARGET_KEY in data:
        async_add_entities([ProxonWaterHeater(coordinator)])


class ProxonWaterHeater(ProxonEntity, WaterHeaterEntity):
    if NATIVE_NAMES:
        _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    else:
        _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_precision = PRECISION_TENTHS
    _attr_min_temp = WATER_RANGE[0]
    _attr_max_temp = WATER_RANGE[1]
    _attr_operation_list = list(OPERATIONS)
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE | WaterHeaterEntityFeature.ON_OFF
    )

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Warmwasser", "hot_water")

    @property
    def _data(self) -> dict:
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._data.get(HEAT_PUMP_KEY) is not None

    @property
    def native_current_temperature(self) -> float | None:
        v = self._data.get(CURRENT_KEY)
        return float(v) if isinstance(v, (int, float)) else None

    @property
    def native_target_temperature(self) -> float | None:
        v = self._data.get(TARGET_KEY)
        return float(v) if isinstance(v, (int, float)) else None

    if not NATIVE_NAMES:
        current_temperature = native_current_temperature
        target_temperature = native_target_temperature

    @property
    def current_operation(self) -> str | None:
        pump, heater = self._data.get(HEAT_PUMP_KEY), self._data.get(HEATER_KEY)
        if pump is None:
            return None
        state = (1 if pump else 0, 1 if heater else 0)
        return next(op for op, s in OPERATIONS.items() if s == state)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (target := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        target = round(float(target))
        if not WATER_RANGE[0] <= target <= WATER_RANGE[1]:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="water_limit",
                translation_placeholders={"low": f"{WATER_RANGE[0]:g}", "high": f"{WATER_RANGE[1]:g}"},
            )
        await self.coordinator.async_write(TARGET_KEY, target)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        pump, heater = OPERATIONS[operation_mode]
        data = self._data
        heater_on = bool(data.get(HEATER_KEY))
        # switch off the immersion heater first, and switch it on only after the heat pump (order of the original app)
        if not heater and heater_on:
            await self.coordinator.async_write(HEATER_KEY, 0)
        if bool(data.get(HEAT_PUMP_KEY)) != bool(pump):
            await self.coordinator.async_write(HEAT_PUMP_KEY, pump)
        if heater and not heater_on:
            await self.coordinator.async_write(HEATER_KEY, 1)

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.current_operation == STATE_OFF:
            await self.async_set_operation_mode(STATE_HEAT_PUMP)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.async_set_operation_mode(STATE_OFF)
