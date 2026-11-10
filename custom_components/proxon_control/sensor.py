"""Readings: temperatures, fan speeds, CO2/humidity, boost time, filter and running hours."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, REVOLUTIONS_PER_MINUTE, EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ProxonConfigEntry
from .const import PPM
from .entity import ProxonEnergyEntity, ProxonEntity, room_name
from .registers import ROOM_COUNT, room_connected
from .comfort import (
    B_ALREADY_ON, B_BLOCKED, B_HEATING, B_IDLE, B_OFF, B_PAUSED,
    C_BLOCKED, C_COOLING, C_IDLE, C_NOT_SUMMER, C_OFF, C_PROTECTING, C_WAITING,
)
from .energy import BLOCKED, HEATING_PRICE, HEATING_SOLAR, NO_SOURCE, OFF, PAUSED, STARTING, WAITING
from .schedule import DAYS, hhmm, read_day, summary, unit_clock


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
        key="CurrentCO2", translation_key="co2", native_unit_of_measurement=PPM,
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
    # weekly ventilation schedule: one sensor per day, and the unit's clock (the schedule follows it)
    if read_day(data, 0) is not None:
        entities += [ProxonScheduleDay(coordinator, day) for day in range(7)]
    if unit_clock(data) is not None:
        entities.append(ProxonClock(coordinator))
    if coordinator.energy.supported:
        entities.append(ProxonEnergyStatus(coordinator))
    comfort = coordinator.comfort
    if comfort.cooling.supported:
        entities.append(ProxonFeatureStatus(coordinator, comfort.cooling, "NachtkuehlungStatus", "night_cooling_status", "mdi:weather-night",
                                            [C_OFF, C_IDLE, C_WAITING, C_COOLING, C_PROTECTING, C_NOT_SUMMER, C_BLOCKED]))
    if comfort.boost.supported:
        entities.append(ProxonFeatureStatus(coordinator, comfort.boost, "BoostStatus", "hot_water_boost_status", "mdi:heating-coil",
                                            [B_OFF, B_IDLE, B_HEATING, B_ALREADY_ON, B_PAUSED, B_BLOCKED]))
    if "Antwortzeit" in data:
        entities += [ProxonResponseTime(coordinator), ProxonConnectionPath(coordinator)]
    async_add_entities(entities)


class ProxonSensor(ProxonEntity, SensorEntity):
    entity_description: ProxonSensorDescription

    def __init__(self, coordinator, description: ProxonSensorDescription) -> None:
        placeholders = {"room": room_name(description.room, coordinator.data)} if description.room is not None else None
        super().__init__(coordinator, description.key, description.translation_key or description.key, placeholders)
        self.entity_description = description

    @property
    def native_value(self):
        v = self.raw_value
        if v is None:
            return None
        if self._key == "Kuehlbetrieb4Wegeventil":
            return "cooling" if v else "heating"
        if self._key in ("FirmwareVersion", "IstLuefterstufe", "IntensivlueftungsRestDauer"):
            return int(v)
        return v


class ProxonScheduleDay(ProxonEntity, SensorEntity):
    """One day of the weekly ventilation schedule in one line; the three phases as attributes."""

    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator, day: int) -> None:
        super().__init__(coordinator, f"Zeitprogramm{day}", f"schedule_{DAYS[day]}")
        self._day = day

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and read_day(self.coordinator.data or {}, self._day) is not None

    @property
    def native_value(self) -> str | None:
        phases = read_day(self.coordinator.data or {}, self._day)
        if phases is None:
            return None
        german = (self.hass.config.language or "").startswith("de") if self.hass else False
        return summary(phases, "Stufe" if german else "level", "Aus" if german else "Off")

    @property
    def extra_state_attributes(self) -> dict:
        phases = read_day(self.coordinator.data or {}, self._day) or []
        return {
            f"phase_{i + 1}": {"start": hhmm(p.start), "end": hhmm(p.end), "level": p.level, "active": p.active}
            for i, p in enumerate(phases)
        }


class ProxonClock(ProxonEntity, SensorEntity):
    """The unit's own clock. The weekly schedule runs on it, so a wrong clock shifts the schedule."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "UhrMinute", "unit_clock")
        self._attr_unique_id = f"{self._attr_unique_id.removesuffix('_UhrMinute')}_Uhr"

    @property
    def native_value(self):
        clock = unit_clock(self.coordinator.data or {})
        return None if clock is None else clock.replace(tzinfo=dt_util.get_default_time_zone())


# rough limits for guessing the connection path from the response time (Nabto doesn't report the path for these queries)
LOCAL_MS = 15
DIRECT_MS = 60


def connection_path(ms: float) -> str:
    if ms < LOCAL_MS:
        return "local"
    if ms < DIRECT_MS:
        return "internet"
    return "relay"


class ProxonResponseTime(ProxonEntity, SensorEntity):
    """How quickly the unit answers (the quickest query of the last read)."""

    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 0
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Antwortzeit", "response_time")

    @property
    def native_value(self):
        return self.raw_value


class ProxonConnectionPath(ProxonEntity, SensorEntity):
    """Estimated way the data takes: home network, directly over the internet, or through Nabto's relay server.
    Estimated from the response time, because the Nabto library doesn't tell it for these queries."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["local", "internet", "relay"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Antwortzeit", "connection_path")
        self._attr_unique_id = f"{self._attr_unique_id}_path"

    @property
    def native_value(self) -> str | None:
        return None if self.raw_value is None else connection_path(float(self.raw_value))

    @property
    def extra_state_attributes(self) -> dict:
        return {"response_time_ms": self.raw_value, "estimated": True}


class ProxonEnergyStatus(ProxonEnergyEntity, SensorEntity):
    """What the hot-water energy manager is doing, and why (surplus, price, starts today as attributes)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [OFF, WAITING, STARTING, HEATING_SOLAR, HEATING_PRICE, PAUSED, BLOCKED, NO_SOURCE]
    _attr_icon = "mdi:water-boiler-auto"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Energiemanager", "energy_status")

    @property
    def native_value(self) -> str:
        return self.manager.status

    @property
    def extra_state_attributes(self) -> dict:
        d = self.manager.details
        st = self.manager.state
        return {
            "surplus_w": d.get("surplus_w"),
            "price_ct_kwh": None if d.get("price_ct") is None else round(d["price_ct"], 2),
            "starts_today": st.starts,
            "heating_since": st.since.isoformat() if st.since else None,
            "previous_target": st.saved_target,
        }


class ProxonFeatureStatus(ProxonEnergyEntity, SensorEntity):
    """What summer night cooling / hot-water boost is doing; the values it decided on as attributes."""

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator, feature, key: str, tk: str, icon: str, options: list[str]) -> None:
        super().__init__(coordinator, key, tk, feature)
        self._attr_icon = icon
        self._attr_options = options

    @property
    def native_value(self) -> str:
        return self.manager.status

    @property
    def extra_state_attributes(self) -> dict:
        attrs = dict(self.manager.details)
        saved = getattr(self.manager.state, "saved_level", None)
        if saved is not None:
            attrs["previous_level"] = saved
        return attrs
