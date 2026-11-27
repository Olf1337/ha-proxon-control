"""Set points: ventilation level, limits, water temperatures (ranges from the original app). Rooms are thermostats (climate.py)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode, RestoreNumber
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .const import DOMAIN, PPM
from .entity import ProxonEnergyEntity, ProxonEntity, has_shower_target
from .registers import MODE_COMFORT, shower_minutes_at, shower_target_range, target_for_shower_minutes


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
    ProxonNumberDescription(key="Luefterstufe", translation_key="level", native_min_value=1, native_max_value=4, native_step=1, mode=NumberMode.SLIDER),
    ProxonNumberDescription(
        key="GrenzwertCO2", translation_key="co2_limit", native_min_value=400, native_max_value=1500, native_step=50,
        native_unit_of_measurement=PPM, mode=NumberMode.SLIDER,
    ),
    ProxonNumberDescription(
        key="GrenzwertFeuchte", translation_key="humidity_limit", native_min_value=0, native_max_value=100, native_step=5,
        native_unit_of_measurement=PERCENTAGE, mode=NumberMode.SLIDER,
    ),
    _temp("SollWassertemperatur", "water_target", 20, 55),
    _temp("NachtabsenkungTemperatur", "night_setback_temperature", 10, 30, 0.5),
    # how long a boost ventilation runs (the unit ends it by itself)
    ProxonNumberDescription(
        key="IntensivlueftungsDauer", translation_key="boost_duration", native_min_value=1, native_max_value=1440, native_step=1,
        native_unit_of_measurement=UnitOfTime.MINUTES, mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    _temp("Soll-E-Heizstab-Temperatur", "boost_temperature", 20, 70),
]


# one change at a time per platform: the unit allows only a few sessions, and every write is read back
PARALLEL_UPDATES = 1


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
    comfort = coordinator.comfort
    if comfort.cooling.supported:
        entities += [ProxonEnergyNumber(coordinator, d, comfort.cooling) for d in COOLING_NUMBERS]
    if comfort.boost.supported:
        entities += [ProxonEnergyNumber(coordinator, d, comfort.boost) for d in BOOST_NUMBERS]
    if comfort.season.supported:
        entities += [ProxonEnergyNumber(coordinator, d, comfort.season) for d in SEASON_NUMBERS]
    if has_shower_target(data):
        entities += [ProxonShowerTargetNumber(coordinator), ProxonShowerLowLimit(coordinator)]
    entities.append(ProxonHolidayLeadNumber(coordinator))
    async_add_entities(entities)


class ProxonNumber(ProxonEntity, NumberEntity):
    entity_description: ProxonNumberDescription

    def __init__(self, coordinator, description: ProxonNumberDescription) -> None:
        super().__init__(coordinator, description.key, description.translation_key or description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.raw_value

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
        entity_category=EntityCategory.CONFIG,
    ),
    ProxonEnergyNumberDescription(
        key="PreisSchwelle", translation_key="cheap_price", setting="price_ct", native_min_value=-50, native_max_value=100,
        native_step=0.5, native_unit_of_measurement="ct/kWh", mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    ProxonEnergyNumberDescription(
        key="SpeicherTemperatur", translation_key="store_temperature", setting="store_temp", native_min_value=40, native_max_value=55,
        native_step=1, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX, entity_category=EntityCategory.CONFIG,
    ),
]


COOLING_NUMBERS: list[ProxonEnergyNumberDescription] = [
    ProxonEnergyNumberDescription(
        key="KuehlWunsch", translation_key="cooling_wish", setting="wish", native_min_value=18, native_max_value=28, native_step=0.5,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    ProxonEnergyNumberDescription(
        key="KuehlStufe", translation_key="cooling_level", setting="level", native_min_value=2, native_max_value=4, native_step=1,
        mode=NumberMode.SLIDER, entity_category=EntityCategory.CONFIG,
    ),
]
BOOST_NUMBERS: list[ProxonEnergyNumberDescription] = [
    ProxonEnergyNumberDescription(
        key="BoostGrenze", translation_key="boost_limit", setting="limit", native_min_value=20, native_max_value=55, native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE, mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
]


SEASON_NUMBERS: list[ProxonEnergyNumberDescription] = [
    ProxonEnergyNumberDescription(
        key="SaisonWinterUnter", translation_key="season_winter_below", setting="winter_below", native_min_value=0, native_max_value=25,
        native_step=0.5, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX, entity_category=EntityCategory.CONFIG,
    ),
    ProxonEnergyNumberDescription(
        key="SaisonSommerUeber", translation_key="season_summer_above", setting="summer_above", native_min_value=5, native_max_value=30,
        native_step=0.5, native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX, entity_category=EntityCategory.CONFIG,
    ),
]


class ProxonEnergyNumber(ProxonEnergyEntity, NumberEntity):
    """Limits of the hot-water energy manager: solar surplus from, electricity price up to, and the store temperature."""

    entity_description: ProxonEnergyNumberDescription

    def __init__(self, coordinator, description: ProxonEnergyNumberDescription, manager=None) -> None:
        super().__init__(coordinator, description.key, description.translation_key or description.key, manager)
        self.entity_description = description

    @property
    def native_value(self) -> float:
        return float(getattr(self.manager.settings, self.entity_description.setting))

    async def async_set_native_value(self, value: float) -> None:
        setting = self.entity_description.setting
        s = self.manager.settings
        # automatic summer/winter: "summer above" has to stay above "winter below" (the gap keeps it from switching back and forth)
        if setting == "winter_below" and value >= getattr(s, "summer_above", value + 1):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="season_limits")
        if setting == "summer_above" and value <= getattr(s, "winter_below", value - 1):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="season_limits")
        await self.manager.async_set(**{setting: int(value) if setting == "level" else float(value)})


class ProxonHolidayLeadNumber(ProxonEntity, NumberEntity):
    """Holiday plan: how many hours before the return holiday mode goes off (house and water warm up again)."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 48
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "UrlaubVorlauf", "holiday_lead")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.holiday.add_listener(self.async_write_ha_state))

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        return self.coordinator.holiday.lead_h

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.holiday.async_set_plan(lead_h=value)


class ProxonShowerTargetNumber(ProxonEntity, NumberEntity):
    """The hot-water target said as a shower reserve (minutes of showering as set under Configure, full tank). Not a value of
    its own: it is worked out from the water target, and setting it writes the lowest water target that holds that many."""

    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "DuschvorratSoll", "shower_target")

    @property
    def native_min_value(self) -> float:
        return shower_target_range(*self.coordinator.shower)[0]

    @property
    def native_max_value(self) -> float:
        return shower_target_range(*self.coordinator.shower)[1]

    @property
    def raw_value(self) -> float | None:
        target = (self.coordinator.data or {}).get("SollWassertemperatur")
        return shower_minutes_at(float(target), *self.coordinator.shower) if isinstance(target, (int, float)) else None

    @property
    def native_value(self) -> float | None:
        return self.raw_value

    @property
    def extra_state_attributes(self) -> dict:
        return {"water_target": (self.coordinator.data or {}).get("SollWassertemperatur")}

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_write("SollWassertemperatur", target_for_shower_minutes(value, *self.coordinator.shower))


class ProxonShowerLowLimit(ProxonEntity, RestoreNumber):
    """Below how many minutes of shower supply "hot water low" comes on. Kept in Home Assistant, not in the unit."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 60
    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "DuschvorratGrenze", "shower_low_limit")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) is not None and last.native_value is not None:
            self.coordinator.shower_low_limit = float(last.native_value)
            self.coordinator.async_update_listeners()

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self) -> float:
        return self.coordinator.shower_low_limit

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.shower_low_limit = float(value)
        self.coordinator.async_update_listeners()  # "hot water low" follows at once
