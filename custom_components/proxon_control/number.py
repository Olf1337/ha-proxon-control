"""Set points: ventilation level, limits, water temperatures (ranges from the original app). Rooms are thermostats (climate.py)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION, PERCENTAGE, EntityCategory, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .const import DOMAIN
from .entity import ProxonEnergyEntity, ProxonEntity
from .registers import MODE_COMFORT


@dataclass(frozen=True, kw_only=True)
class ProxonNumberDescription(NumberEntityDescription):
    pass


def _temp(key: str, tk: str, lo: float, hi: float, step: float = 1) -> ProxonNumberDescription:
    return ProxonNumberDescription(
        key=key, translation_key=tk, native_min_value=lo, native_max_value=hi, native_step=step,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.SLIDER,
    )


NUMBERS: list[ProxonNumberDescription] = [
    ProxonNumberDescription(key="Luefterstufe", translation_key="level", native_min_value=1, native_max_value=4, native_step=1, mode=NumberMode.SLIDER, icon="mdi:fan"),
    ProxonNumberDescription(
        key="GrenzwertCO2", translation_key="co2_limit", native_min_value=400, native_max_value=1500, native_step=50,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION, mode=NumberMode.SLIDER, icon="mdi:molecule-co2",
    ),
    ProxonNumberDescription(
        key="GrenzwertFeuchte", translation_key="humidity_limit", native_min_value=0, native_max_value=100, native_step=5,
        native_unit_of_measurement=PERCENTAGE, mode=NumberMode.SLIDER, icon="mdi:water-percent",
    ),
    _temp("SollWassertemperatur", "water_target", 20, 55),
    _temp("Soll-E-Heizstab-Temperatur", "boost_temperature", 20, 70),
]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities: list[NumberEntity] = [
        ProxonNumber(coordinator, d)
        for d in NUMBERS
        # no CO2 limit when the unit has no CO2 sensor (a reading of 0 ppm), like the original app
        if d.key in data and not (d.key == "GrenzwertCO2" and not data.get("CurrentCO2"))
    ]
    if coordinator.energy.supported:
        entities += [ProxonEnergyNumber(coordinator, d) for d in ENERGY_NUMBERS]
    async_add_entities(entities)


class ProxonNumber(ProxonEntity, NumberEntity):
    entity_description: ProxonNumberDescription

    def __init__(self, coordinator, description: ProxonNumberDescription) -> None:
        super().__init__(coordinator, description.key, description.translation_key or description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.value

    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data or {}
        if self._key == "Luefterstufe" and (data.get("Intensivlueftung") or int(data.get("Betriebsart", -1)) == MODE_COMFORT):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="level_locked")
        await self.coordinator.async_write(self._key, value)


@dataclass(frozen=True, kw_only=True)
class ProxonEnergyNumberDescription(NumberEntityDescription):
    setting: str


ENERGY_NUMBERS: list[ProxonEnergyNumberDescription] = [
    ProxonEnergyNumberDescription(
        key="SolarSchwelle", translation_key="solar_surplus", setting="surplus_w", native_min_value=200, native_max_value=20000,
        native_step=100, native_unit_of_measurement=UnitOfPower.WATT, device_class=NumberDeviceClass.POWER, mode=NumberMode.BOX,
        icon="mdi:solar-power-variant", entity_category=EntityCategory.CONFIG,
    ),
    ProxonEnergyNumberDescription(
        key="PreisSchwelle", translation_key="cheap_price", setting="price_ct", native_min_value=-50, native_max_value=100,
        native_step=0.5, native_unit_of_measurement="ct/kWh", mode=NumberMode.BOX, icon="mdi:cash-clock",
        entity_category=EntityCategory.CONFIG,
    ),
    ProxonEnergyNumberDescription(
        key="SpeicherTemperatur", translation_key="store_temperature", setting="store_temp", native_min_value=40, native_max_value=55,
        native_step=1, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX, icon="mdi:water-boiler", entity_category=EntityCategory.CONFIG,
    ),
]


class ProxonEnergyNumber(ProxonEnergyEntity, NumberEntity):
    """Limits of the hot-water energy manager: solar surplus from, electricity price up to, and the store temperature."""

    entity_description: ProxonEnergyNumberDescription

    def __init__(self, coordinator, description: ProxonEnergyNumberDescription) -> None:
        super().__init__(coordinator, description.key, description.translation_key or description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float:
        return float(getattr(self.manager.settings, self.entity_description.setting))

    @property
    def value(self) -> float:
        # NumberEntity shows `value`; the base class of the Proxon entities uses that name for the unit's raw value
        return self.native_value

    async def async_set_native_value(self, value: float) -> None:
        await self.manager.async_set(**{self.entity_description.setting: float(value)})
