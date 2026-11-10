"""Readings: temperatures, fan speeds, CO2/humidity, boost time, filter and running hours."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION, PERCENTAGE, REVOLUTIONS_PER_MINUTE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity, room_name
from .registers import ROOM_COUNT, room_connected


@dataclass(frozen=True, kw_only=True)
class ProxonSensorDescription(SensorEntityDescription):
    room: int | None = None


def _temp(key: str, tk: str, room: int | None = None, diag: bool = False) -> ProxonSensorDescription:
    return ProxonSensorDescription(
        key=key,
        translation_key=tk,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        room=room,
        entity_category=EntityCategory.DIAGNOSTIC if diag else None,
    )


def _rpm(key: str, tk: str) -> ProxonSensorDescription:
    return ProxonSensorDescription(
        key=key, translation_key=tk, native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:fan", entity_category=EntityCategory.DIAGNOSTIC,
    )


SENSORS: list[ProxonSensorDescription] = [
    *[_temp(f"NBE{i}Temperatur", "room_temperature", i) for i in range(ROOM_COUNT)],
    _temp("T3Frischluft", "outdoor_air"),
    _temp("T1Zuluft", "supply_air"),
    _temp("T7Abluft", "extract_air"),
    _temp("T4Fortluft", "exhaust_air"),
    _temp("WarmwasserIstTemperatur", "water_temperature"),
    _temp("T300VorVerdampfer", "t300_pre_evaporator", diag=True),
    _temp("T300Verdampfer", "t300_evaporator", diag=True),
    _temp("T300Kompressor", "t300_compressor", diag=True),
    _rpm("DrehzahlZuluft", "rpm_intake"),
    _rpm("DrehzahlAbluft", "rpm_exhaust"),
    _rpm("DrehzahlKompressor", "rpm_compressor"),
    ProxonSensorDescription(key="IstLuefterstufe", translation_key="actual_level", icon="mdi:fan", state_class=SensorStateClass.MEASUREMENT),
    ProxonSensorDescription(
        key="CurrentCO2", translation_key="co2", native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2, state_class=SensorStateClass.MEASUREMENT,
    ),
    ProxonSensorDescription(
        key="LuftfeuchteRel", translation_key="humidity", native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY, state_class=SensorStateClass.MEASUREMENT,
    ),
    ProxonSensorDescription(
        key="IntensivlueftungsRestDauer", translation_key="boost_remaining", native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION, icon="mdi:timer-outline",
    ),
    ProxonSensorDescription(
        key="FilterRestStunden", translation_key="filter_remaining", native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_unit_of_measurement=UnitOfTime.DAYS, suggested_display_precision=0,
        device_class=SensorDeviceClass.DURATION, icon="mdi:air-filter",
    ),
    ProxonSensorDescription(
        key="LaufzeitFilter", translation_key="filter_runtime", native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION, state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ProxonSensorDescription(
        key="Betriebsstundenzaehler", translation_key="working_hours", native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION, state_class=SensorStateClass.TOTAL_INCREASING, entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ProxonSensorDescription(key="FirmwareVersion", translation_key="firmware", entity_category=EntityCategory.DIAGNOSTIC),
    ProxonSensorDescription(
        key="Kuehlbetrieb4Wegeventil", translation_key="valve", device_class=SensorDeviceClass.ENUM,
        options=["heating", "cooling"], entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities = []
    for d in SENSORS:
        # only what the unit actually reports (rooms, CO2 sensor, hot-water heat pump)
        if d.key not in data:
            continue
        # like the original app: a CO₂ reading of exactly 0 ppm means the unit has no CO₂ sensor
        if d.key == "CurrentCO2" and not data.get("CurrentCO2"):
            continue
        if d.room is not None and not room_connected(data, d.room):
            continue
        entities.append(ProxonSensor(coordinator, d))
    async_add_entities(entities)


class ProxonSensor(ProxonEntity, SensorEntity):
    entity_description: ProxonSensorDescription

    def __init__(self, coordinator, description: ProxonSensorDescription) -> None:
        placeholders = {"room": room_name(description.room, coordinator.data)} if description.room is not None else None
        super().__init__(coordinator, description.key, description.translation_key or description.key, placeholders)
        self.entity_description = description

    @property
    def native_value(self):
        v = self.value
        if v is None:
            return None
        if self._key == "Kuehlbetrieb4Wegeventil":
            return "cooling" if v else "heating"
        if self._key in ("FirmwareVersion", "IstLuefterstufe", "IntensivlueftungsRestDauer"):
            return int(v)
        return v
