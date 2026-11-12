"""Readings: temperatures, fan speeds, CO2/humidity, boost time, filter and running hours."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import time

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ProxonConfigEntry
from . import legionella as L
from .api import PATH_KEY
from .comfort import (
    B_ALREADY_ON,
    B_BLOCKED,
    B_HEATING,
    B_IDLE,
    B_OFF,
    B_PAUSED,
    C_BLOCKED,
    C_COOLING,
    C_IDLE,
    C_NOT_SUMMER,
    C_OFF,
    C_PROTECTING,
    C_WAITING,
    S_BLOCKED,
    S_COLLECTING,
    S_MANUAL,
    S_OFF,
    S_SUMMER,
    S_WINTER,
)
from .const import CONF_PRICE_SENSOR, PPM
from .energy import BLOCKED, HEATING_PRICE, HEATING_SOLAR, NO_SOURCE, OFF, PAUSED, STARTING, WAITING
from .entity import ProxonEnergyEntity, ProxonEntity, room_device
from .registers import (
    HOUR_COUNTERS,
    OPERATION_KEYS,
    ROOM_COUNT,
    element_state,
    filter_months,
    heat_recovery,
    ptc_thresholds,
    room_connected,
    room_target,
)
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


def _raw(key: str, tk: str, icon: str, enabled: bool = True) -> ProxonSensorDescription:
    """A raw diagnostic value of the unit (positions, status words)."""
    return ProxonSensorDescription(
        key=key, translation_key=tk, icon=icon, entity_category=EntityCategory.DIAGNOSTIC, entity_registry_enabled_default=enabled,
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
    _temp("WarmwasserUntenTemperatur", "water_bottom"),
    ProxonSensorDescription(
        key="KompressorLeistung", translation_key="compressor_power_percent", native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, icon="mdi:heat-pump",
    ),
    ProxonSensorDescription(
        key="GeraeteTyp", translation_key="device_type", device_class=SensorDeviceClass.ENUM,
        options=["heating_only", "heating_cooling"], entity_category=EntityCategory.DIAGNOSTIC, icon="mdi:information-outline",
    ),
    *[
        ProxonSensorDescription(
            key=key, translation_key=tk, native_unit_of_measurement=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0,
        )
        for key, tk in (("LeistungGesamt", "power_total"), ("LeistungKompressor", "power_compressor"), ("LeistungLueftung", "power_ventilation"))
    ],
    ProxonSensorDescription(
        key="WarmwasserLadezustand", translation_key="water_charge", native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:water-boiler",
    ),
    ProxonSensorDescription(
        key="WarmwasserDuschminuten", translation_key="shower_minutes", native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=0, icon="mdi:shower-head",
    ),
    ProxonSensorDescription(
        key="AktuellerBetrieb", translation_key="operation", device_class=SensorDeviceClass.ENUM,
        options=list(OPERATION_KEYS.values()), icon="mdi:heat-pump-outline",
    ),
    # diagnostics of the heat pump / air paths
    _temp("T12VorKondensator", "t12_pre_condenser", diag=True),
    _temp("T13Kompressor", "t13_compressor", diag=True),
    _temp("T14Sauggas", "t14_suction_gas", diag=True),
    _temp("T300Saugleitung", "t300_suction", diag=True),
    _rpm("T300LuefterDrehzahl", "t300_fan_rpm"),
    ProxonSensorDescription(
        key="DruckVerdampfer", translation_key="evaporator_pressure", native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    _raw("Schieberposition", "damper_position", "mdi:valve"),
    _raw("VentilHeizung", "valve_heating", "mdi:valve"),
    _raw("VentilVorwaerme", "valve_preheat", "mdi:valve"),
    _raw("VentilKuehlung", "valve_cooling", "mdi:valve"),
    _raw("StatusKompressor", "compressor_status", "mdi:heat-pump", enabled=False),
    _raw("StatusVentilatoren", "fan_status", "mdi:fan", enabled=False),
    # operating hours of the unit's parts (lifetime counters of the unit)
    *[
        ProxonSensorDescription(
            key=key, translation_key=f"hours_{key.removeprefix('Stunden').lower()}", native_unit_of_measurement=UnitOfTime.HOURS,
            device_class=SensorDeviceClass.DURATION, state_class=SensorStateClass.TOTAL_INCREASING, icon="mdi:counter",
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        for key in (*HOUR_COUNTERS, "T300StundenKompressor", "T300StundenHeizstab")
    ],
    # today (counted in Home Assistant, yesterday as attribute)
    *[
        ProxonSensorDescription(
            key=f"{name}StartsHeute", translation_key=f"starts_today_{tk}", state_class=SensorStateClass.TOTAL_INCREASING,
            icon="mdi:restart",
        )
        for name, tk in (("Kompressor", "compressor"), ("WarmwasserKompressor", "hot_water_compressor"), ("Heizstab", "heater"))
    ],
    *[
        ProxonSensorDescription(
            key=f"{name}LaufzeitHeute", translation_key=f"runtime_today_{tk}", native_unit_of_measurement=UnitOfTime.HOURS,
            device_class=SensorDeviceClass.DURATION, state_class=SensorStateClass.TOTAL_INCREASING, suggested_display_precision=1,
            icon="mdi:timer-outline",
        )
        for name, tk in (("Kompressor", "compressor"), ("WarmwasserKompressor", "hot_water_compressor"), ("Heizstab", "heater"))
    ],
    *[
        ProxonSensorDescription(
            key=key, translation_key=tk, native_unit_of_measurement="K", suggested_display_precision=1,
            icon="mdi:thermometer-chevron-down", entity_category=EntityCategory.DIAGNOSTIC,
        )
        for key, tk in (("PTCEinschaltSchwelle", "ptc_on_threshold"), ("PTCAusschaltSchwelle", "ptc_off_threshold"))
    ],
    ProxonSensorDescription(
        key="FilterStandzeit", translation_key="filter_lifetime", native_unit_of_measurement=UnitOfTime.MONTHS,
        icon="mdi:air-filter", entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ProxonSensorDescription(
        key="UhrAbweichung", translation_key="clock_drift", native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT, icon="mdi:clock-alert-outline", entity_category=EntityCategory.DIAGNOSTIC,
    ),
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
    ProxonSensorDescription(key="FirmwareT300", translation_key="firmware_t300", entity_category=EntityCategory.DIAGNOSTIC),
    ProxonSensorDescription(
        key="Kuehlbetrieb4Wegeventil", translation_key="valve", device_class=SensorDeviceClass.ENUM,
        options=["heating", "cooling"], entity_category=EntityCategory.DIAGNOSTIC,
    ),
]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities: list[SensorEntity] = []
    for d in SENSORS:
        # only what the unit actually reports (rooms, CO2 sensor, hot-water heat pump)
        if d.key not in data:
            continue
        # like the original app: a CO₂ reading of exactly 0 ppm means the unit has no CO₂ sensor
        if d.key == "CurrentCO2" and not data.get("CurrentCO2"):
            continue
        if d.room is not None and not room_connected(data, d.room):
            continue
        # the hot-water module's own values only when it is there (it answers 0 otherwise)
        if (d.key in ("FirmwareT300", "T300LuefterDrehzahl") or d.key.startswith(("T300Stunden", "WarmwasserKompressor", "Heizstab"))) \
                and "T300Betriebsart" not in data:
            continue
        entities.append(ProxonSensor(coordinator, d))
    entities += [ProxonEnergy(coordinator, key, power, tk) for key, power, tk in ENERGY if power in data]
    if all(k in data for k in ("T3Frischluft", "T1Zuluft", "T7Abluft")):
        entities.append(ProxonHeatRecovery(coordinator))
    if "NBE0Temperatur" in data:
        entities.append(ProxonRoomAverage(coordinator))
    entities.append(ProxonLastWriteError(coordinator))
    # every room's heating element: not released / ready / heating
    entities += [ProxonHeatingElement(coordinator, i) for i in range(ROOM_COUNT) if room_connected(data, i) and element_state(data, i) is not None]
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
    if coordinator.energy.legionella.supported:
        entities.append(ProxonFeatureStatus(coordinator, coordinator.energy.legionella, "LegionellenStatus", "legionella_status",
                                            "mdi:bacteria-outline", [L.OFF, L.WAITING, L.LOOKING, L.STARTING, L.HEATING_SOLAR,
                                                                     L.HEATING_DUE, L.BLOCKED]))
    if entry.options.get(CONF_PRICE_SENSOR) and "LeistungGesamt" in data:
        entities.append(ProxonEnergyCost(coordinator, hass.config.currency))
    if comfort.season.supported:
        entities.append(ProxonFeatureStatus(coordinator, comfort.season, "SaisonStatus", "season_status", "mdi:sun-snowflake-variant",
                                            [S_OFF, S_COLLECTING, S_SUMMER, S_WINTER, S_MANUAL, S_BLOCKED]))
    if "Antwortzeit" in data:
        entities += [ProxonResponseTime(coordinator), ProxonConnectionPath(coordinator)]
    async_add_entities(entities)


class ProxonSensor(ProxonEntity, SensorEntity):
    entity_description: ProxonSensorDescription

    def __init__(self, coordinator, description: ProxonSensorDescription) -> None:
        device = room_device(coordinator, description.room) if description.room is not None else None
        super().__init__(coordinator, description.key, description.translation_key or description.key, device=device)
        self.entity_description = description

    @property
    def native_value(self):
        v = self.raw_value
        if v is None:
            return None
        if self._key == "Kuehlbetrieb4Wegeventil":
            return "cooling" if v else "heating"
        if self._key == "AktuellerBetrieb":
            return OPERATION_KEYS.get(int(v))
        if self._key == "GeraeteTyp":
            return {0: "heating_only", 1: "heating_cooling"}.get(int(v))
        if self._key in ("FirmwareVersion", "FirmwareT300", "IstLuefterstufe", "IntensivlueftungsRestDauer", "UhrAbweichung",
                         "FilterStandzeit", "WarmwasserLadezustand", "WarmwasserDuschminuten") or self._key.endswith("StartsHeute"):
            return int(v)
        return v

    @property
    def extra_state_attributes(self) -> dict | None:
        data = self.coordinator.data or {}
        if self._key == "FilterRestStunden":
            return {"filter_lifetime_months": filter_months(data)}
        if self._key.endswith("Heute"):
            return {"yesterday": data.get(self._key.removesuffix("Heute") + "Gestern")}
        return None


# energy counters for the Energy dashboard: (key, power value they add up, translation key)
ENERGY = [("EnergieGesamt", "LeistungGesamt", "energy_total"), ("EnergieKompressor", "LeistungKompressor", "energy_compressor")]
# a gap between two readings longer than this (or three query intervals; Home Assistant stopped, unit not reachable) isn't counted
MAX_GAP_SECONDS = 15 * 60


class ProxonEnergy(ProxonEntity, RestoreSensor):
    """Energy the unit used (kWh), added up from its power readings (trapezoidal rule). Kept across restarts; for the
    Energy dashboard (individual devices)."""

    _attr_native_unit_of_measurement: str | None = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator, key: str, power_key: str, tk: str) -> None:
        super().__init__(coordinator, key, tk)
        self._power_key = power_key
        self._kwh = 0.0
        self._last: tuple[float, float] | None = None  # (watt, monotonic time)

    @property
    def available(self) -> bool:
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None and isinstance(last.native_value, (int, float)):
            self._kwh = float(last.native_value)
        self._add(time.monotonic())

    def _add(self, now: float) -> None:
        watt = (self.coordinator.data or {}).get(self._power_key)
        if not isinstance(watt, (int, float)) or not self.coordinator.last_update_success:
            self._last = None
            return
        interval = self.coordinator.update_interval.total_seconds() if self.coordinator.update_interval else 0
        if self._last is not None and 0 < now - self._last[1] <= max(MAX_GAP_SECONDS, 3 * interval):
            self._kwh += self._count((self._last[0] + watt) / 2 * (now - self._last[1]) / 3_600_000)
        self._last = (float(watt), now)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._add(time.monotonic())
        super()._handle_coordinator_update()

    def _count(self, kwh: float) -> float:
        """What a piece of energy adds to the total."""
        return kwh

    @property
    def native_value(self) -> float:
        return round(self._kwh, 4)


class ProxonEnergyCost(ProxonEnergy):
    """What the unit's electricity cost (in the currency of Home Assistant), added up from its power and the price sensor
    chosen in the options. A piece of energy is counted at the price of that moment; without a price it costs nothing."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator, currency: str) -> None:
        super().__init__(coordinator, "Stromkosten", "LeistungGesamt", "energy_cost")
        self._attr_native_unit_of_measurement = currency

    def _count(self, kwh: float) -> float:
        price_ct = self.coordinator.energy.price_ct()
        return 0.0 if price_ct is None else kwh * price_ct / 100


class ProxonHeatingElement(ProxonEntity, SensorEntity):
    """The room's electric heating element: not released, ready (released, no heat needed) or heating (released and the room
    too cold, as the Proxon app shows it)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["off", "ready", "heating"]

    def __init__(self, coordinator, room: int) -> None:
        super().__init__(coordinator, f"NBE{room}Waermeelement", "heating_element", device=room_device(coordinator, room))
        self._room = room

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and element_state(self.coordinator.data or {}, self._room) is not None

    @property
    def native_value(self) -> str | None:
        return element_state(self.coordinator.data or {}, self._room)

    @property
    def icon(self) -> str:
        return {"heating": "mdi:radiator", "ready": "mdi:radiator-disabled"}.get(self.native_value or "", "mdi:radiator-off")

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        temp, target = data.get(f"NBE{self._room}Temperatur"), room_target(data, self._room)
        below = round(target - temp, 1) if isinstance(temp, (int, float)) and isinstance(target, (int, float)) else None
        # "thresholds": as the unit decides (its switch-on/off thresholds), "panel": by the room panel's LED level
        return {"below_target": below, "decided_by": "thresholds" if ptc_thresholds(data) else "panel"}


class ProxonHeatRecovery(ProxonEntity, RestoreSensor):
    """Efficiency of the heat exchanger (%), from outdoor, supply and extract air. Only measurable while the heat pump is off,
    the bypass closed and outdoor and extract air at least 5 K apart; in between the last measured value is kept."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heat-wave"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Waermerueckgewinnung", "heat_recovery")
        self._last: float | None = None
        self._measured_at: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Take over the last measurement from before a restart: while the heat pump runs (most of the winter) nothing
        can be measured, and the sensor would stay empty until it pauses."""
        await super().async_added_to_hass()
        if self._last is not None:
            return
        if (last := await self.async_get_last_sensor_data()) is not None and isinstance(last.native_value, (int, float)):
            self._last = float(last.native_value)
            state = await self.async_get_last_state()
            when = state.attributes.get("measured_at") if state else None
            self._measured_at = dt_util.parse_datetime(when) if isinstance(when, str) else None
            self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self) -> float | None:
        value = heat_recovery(self.coordinator.data or {})
        if value is not None:
            if value != self._last or self._measured_at is None:
                self._measured_at = dt_util.utcnow()
            self._last = value
        return None if self._last is None else int(self._last)

    @property
    def extra_state_attributes(self) -> dict:
        return {"measuring_now": heat_recovery(self.coordinator.data or {}) is not None, "measured_at": self._measured_at}


class ProxonRoomAverage(ProxonEntity, SensorEntity):
    """Mean temperature of all rooms with a panel (the indoor temperature on the dashboard's start page)."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "RaumMittel", "rooms_average")

    def _temperatures(self) -> list[float]:
        data = self.coordinator.data or {}
        out = []
        for i in range(ROOM_COUNT):
            value = data.get(f"NBE{i}Temperatur")
            if room_connected(data, i) and isinstance(value, (int, float)):
                out.append(float(value))
        return out

    @property
    def raw_value(self) -> float | None:
        temps = self._temperatures()
        return round(sum(temps) / len(temps), 2) if temps else None

    @property
    def native_value(self) -> float | None:
        return self.raw_value

    @property
    def extra_state_attributes(self) -> dict:
        return {"rooms": len(self._temperatures())}


class ProxonLastWriteError(ProxonEntity, SensorEntity):
    """When the unit last refused or didn't take a change, which value, and why (fault, not taken over, no connection)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "LetzterSchreibfehler", "last_write_error")

    @property
    def available(self) -> bool:
        return True

    @property
    def native_value(self):
        err = self.coordinator.last_write_error
        return None if err is None else err["time"]

    @property
    def extra_state_attributes(self) -> dict:
        err = self.coordinator.last_write_error or {}
        return {"value": err.get("name"), "wanted": err.get("wanted"), "got": err.get("got"), "reason": err.get("reason"),
                "count": self.coordinator.write_errors}


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
        self._attr_unique_id = f"{(self._attr_unique_id or '').removesuffix('_UhrMinute')}_Uhr"

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
    """The way the data takes: home network, directly over the internet, or through Nabto's relay server.
    Exact for the integration's own home network connection; through the Proxon server estimated from the response time,
    because the Nabto library doesn't tell it."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["local", "internet", "relay"]
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Antwortzeit", "connection_path")
        self._attr_unique_id = f"{self._attr_unique_id}_path"

    @property
    def _direct(self) -> bool:
        return (self.coordinator.data or {}).get(PATH_KEY) == "local"

    @property
    def native_value(self) -> str | None:
        if self._direct:
            return "local"
        return None if self.raw_value is None else connection_path(float(self.raw_value))

    @property
    def extra_state_attributes(self) -> dict:
        attrs = {"response_time_ms": self.raw_value, "estimated": not self._direct}
        if via := (self.coordinator.data or {}).get(PATH_KEY):
            attrs["via"] = via  # "local": the integration's home network connection, "cloud": through the Proxon server
        return attrs


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
