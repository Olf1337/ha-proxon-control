"""On/off settings: boost ventilation, cooling, hot-water heat pump, immersion heater, legionella function, weekly schedule,
the heating elements of all rooms at once. (Each room's heating element is part of its thermostat.)"""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ProxonConfigEntry
from .entity import ProxonEnergyEntity, ProxonEntity, house_rooms, room_name

SWITCHES: list[tuple[str, str, str, int | None]] = [
    ("Intensivlueftung", "boost", "mdi:fan-plus", None),
    ("GlobalKuehlungFreigabe", "cooling", "mdi:snowflake", None),
    ("T300Betriebsart", "water_heat_pump", "mdi:water-boiler", None),
    ("E-Heizstab", "immersion_heater", "mdi:heating-coil", None),
    ("Legionellenfunktion", "legionella", "mdi:bacteria-outline", None),
    ("NachtabsenkungAktiv", "night_setback", "mdi:weather-night", None),
    ("ZeitprogrammAktiv", "schedule", "mdi:calendar-clock", None),
]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities: list[SwitchEntity] = [
        ProxonSwitch(coordinator, key, tk, icon, room)
        for key, tk, icon, room in SWITCHES
        # no cooling switch on units that can only heat (device type reported by the unit)
        if key in data and not (key == "GlobalKuehlungFreigabe" and data.get("GeraeteTyp") == 0)
    ]
    entities.append(ProxonHolidaySwitch(coordinator))
    if any(f"NBE{i}PTC" in data for i in house_rooms(data)):
        entities.append(ProxonAllElementsSwitch(coordinator))
    comfort = coordinator.comfort
    if comfort.cooling.supported:
        entities.append(ProxonEnergySwitch(coordinator, "on", "Nachtkuehlung", "night_cooling", "mdi:weather-night", comfort.cooling))
    if comfort.boost.supported:
        entities.append(ProxonEnergySwitch(coordinator, "on", "WarmwasserBoost", "hot_water_boost", "mdi:heating-coil", comfort.boost))
    if comfort.season.supported:
        entities.append(ProxonEnergySwitch(coordinator, "on", "SaisonAutomatik", "season_auto", "mdi:sun-snowflake-variant", comfort.season))
    if coordinator.energy.supported:
        entities += [ProxonEnergySwitch(coordinator, "solar_on", "SolarWarmwasser", "solar_hot_water", "mdi:solar-power-variant"),
                     ProxonEnergySwitch(coordinator, "price_on", "PreisWarmwasser", "cheap_hot_water", "mdi:cash-clock")]
    if coordinator.energy.legionella.supported:
        entities += [ProxonEnergySwitch(coordinator, "on", "LegionellenSonne", "legionella_solar", "mdi:bacteria-outline",
                                        coordinator.energy.legionella),
                     ProxonEnergySwitch(coordinator, "plan_on", "LegionellenGeplant", "legionella_planned", "mdi:calendar-check-outline",
                                        coordinator.energy.legionella)]
    async_add_entities(entities)


class ProxonSwitch(ProxonEntity, SwitchEntity):
    def __init__(self, coordinator, key: str, tk: str, icon: str, room: int | None) -> None:
        super().__init__(coordinator, key, tk)
        self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        return bool(self.raw_value) if self.raw_value is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self._key, 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_write(self._key, 0)


class ProxonHolidaySwitch(ProxonEntity, SwitchEntity):
    """Holiday mode: lowers ventilation and temperatures and switches off hot water; switching off restores the saved values."""

    _attr_icon = "mdi:bag-suitcase"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Urlaubsmodus", "holiday")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        return self.coordinator.holiday.active

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.holiday.add_listener(self.async_write_ha_state))

    @property
    def extra_state_attributes(self) -> dict:
        holiday = self.coordinator.holiday
        start, back = holiday.plan_start, holiday.back_on_at

        def iso(v):
            return dt_util.as_local(v).isoformat() if v else None
        return {"saved_values": holiday.saved, "plan_on_at": iso(start), "plan_off_at": iso(back)}

    async def async_turn_on(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.holiday.async_turn_on()
        finally:
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        try:
            await self.coordinator.holiday.async_turn_off()
        finally:
            self.async_write_ha_state()


class ProxonEnergySwitch(ProxonEnergyEntity, SwitchEntity):
    """Switches the use of solar surplus / cheap electricity for the hot-water store on and off."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, setting: str, key: str, tk: str, icon: str, manager=None) -> None:
        super().__init__(coordinator, key, tk, manager)
        self._setting = setting
        self._attr_icon = icon

    @property
    def is_on(self) -> bool:
        return bool(getattr(self.manager.settings, self._setting))

    @property
    def extra_state_attributes(self) -> dict:
        # what the function is doing right now (shown on the dashboard tile next to on/off); nothing while it is off
        return {"status": self.manager.status} if self.is_on else {}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.manager.async_set(**{self._setting: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.manager.async_set(**{self._setting: False})


class ProxonAllElementsSwitch(ProxonEntity, SwitchEntity):
    """The heating elements of all rooms at once: on when every room's element is released; switching writes each room
    whose element differs (one write per room, like in the room's thermostat)."""

    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "WaermeelementeAlle", "all_heating_elements")

    def _rooms(self) -> list[int]:
        data = self.coordinator.data or {}
        return [i for i in house_rooms(data) if f"NBE{i}PTC" in data]

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self._rooms())

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data or {}
        rooms = self._rooms()
        return all(data.get(f"NBE{i}PTC") for i in rooms) if rooms else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        rooms = self._rooms()
        return {"rooms_on": [room_name(i, data) for i in rooms if data.get(f"NBE{i}PTC")],
                "rooms_off": [room_name(i, data) for i in rooms if not data.get(f"NBE{i}PTC")]}

    async def _set(self, on: bool) -> None:
        # every room is tried; the first failure is reported afterwards (the others are written anyway)
        failed: HomeAssistantError | None = None
        for i in self._rooms():
            if bool((self.coordinator.data or {}).get(f"NBE{i}PTC")) != on:
                try:
                    await self.coordinator.async_write(f"NBE{i}PTC", 1 if on else 0)
                except HomeAssistantError as err:
                    failed = failed or err
        if failed:
            raise failed

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
