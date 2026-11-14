"""Filter change warning, compressor, fault, and on/off states of the unit (bypass, geothermal exchanger, PV input, ...)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .entity import ProxonEntity
from .registers import FAULT_POINTS, active_faults, fault_key, heating_channels, t300_fault_texts

# warn when 30 days or less are left (estimated; the original's exact threshold wasn't found)
FILTER_WARN_HOURS = 30 * 24

# simple on/off values of the unit: key, translation key, device class, icon, diagnostic
STATES: list[tuple[str, str, BinarySensorDeviceClass | None, str | None, bool]] = [
    ("Bypass", "bypass", BinarySensorDeviceClass.OPENING, "mdi:valve", False),
    ("Erdwaerme", "geothermal", BinarySensorDeviceClass.RUNNING, "mdi:earth", False),
    ("Magnetventil", "solenoid_valve", BinarySensorDeviceClass.OPENING, "mdi:valve", True),
    ("PVFreigabe", "pv_enabled", None, "mdi:solar-power", False),
    ("PVSignalHeizstab", "pv_signal_heater", None, "mdi:solar-power-variant", False),
    ("PVSignalWaermepumpe", "pv_signal_heat_pump", None, "mdi:solar-power-variant", False),
    ("BedienpanelGesperrt", "panel_locked", None, "mdi:lock-outline", True),
]
# values of the hot-water module: only when it is there
T300_KEYS = {"PVFreigabe", "PVSignalHeizstab", "PVSignalWaermepumpe"}


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities: list[BinarySensorEntity] = []
    if "FilterRestStunden" in data:
        entities.append(ProxonFilterWarning(coordinator))
    if "DrehzahlKompressor" in data:
        entities.append(ProxonCompressor(coordinator))
    if any(fault_key(p) in data for p in FAULT_POINTS):
        entities.append(ProxonFault(coordinator))
    if "HeizmodulRelais" in data:
        entities.append(ProxonHeatingElements(coordinator))
    entities += [
        ProxonState(coordinator, key, tk, dc, icon, diag)
        for key, tk, dc, icon, diag in STATES
        if key in data and (key not in T300_KEYS or "T300Betriebsart" in data)
    ]
    async_add_entities(entities)


class ProxonHeatingElements(ProxonEntity, BinarySensorEntity):
    """Whether the electric heating elements of the rooms heat right now (relays K1-K10 of the heating module). Which relay
    belongs to which room depends on the wiring; the switched-on relays are an attribute."""

    _attr_device_class = BinarySensorDeviceClass.HEAT
    _attr_icon = "mdi:radiator"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "HeizmodulRelais", "heating_elements")

    @property
    def is_on(self) -> bool | None:
        return None if self.raw_value is None else bool(heating_channels(self.coordinator.data or {}))

    @property
    def extra_state_attributes(self) -> dict:
        return {"active_channels": heating_channels(self.coordinator.data or {})}


class ProxonState(ProxonEntity, BinarySensorEntity):
    def __init__(self, coordinator, key: str, tk: str, device_class, icon: str | None, diag: bool) -> None:
        super().__init__(coordinator, key, tk)
        self._attr_device_class = device_class
        self._attr_icon = icon
        if diag:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        return None if self.raw_value is None else bool(self.raw_value)


class ProxonFilterWarning(ProxonEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "FilterRestStunden", "filter_change")
        self._attr_unique_id = f"{self._attr_unique_id}_warning"

    @property
    def is_on(self) -> bool | None:
        return None if self.raw_value is None else self.raw_value <= FILTER_WARN_HOURS


class ProxonCompressor(ProxonEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "DrehzahlKompressor", "compressor")
        self._attr_unique_id = f"{self._attr_unique_id}_running"

    @property
    def is_on(self) -> bool | None:
        return None if self.raw_value is None else self.raw_value > 0


class ProxonFault(ProxonEntity, BinarySensorEntity):
    """Fault of the unit: any fault word with a bit set (known harmless notice bits left out). The words are attributes."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "Stoerung", "fault")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and any(fault_key(p) in (self.coordinator.data or {}) for p in FAULT_POINTS)

    @property
    def is_on(self) -> bool:
        return bool(active_faults(self.coordinator.data or {}))

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        attrs: dict = {fault_key(p): f"0x{int(data[fault_key(p)]) & 0xFFFF:04X}" for p in FAULT_POINTS if isinstance(data.get(fault_key(p)), (int, float))}
        # the hot-water module names its faults (Proxon's Modbus list); the main unit's fault words have no names
        attrs["hot_water_module"] = t300_fault_texts(data, self.hass.config.language if self.hass else None)
        return attrs
