"""Set points: ventilation level, limits, water and room temperatures (ranges from the original app)."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION, PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ProxonConfigEntry
from .const import DOMAIN
from .entity import ProxonEntity, room_name
from .registers import MODE_COMFORT, ROOM_COUNT, room_base, room_connected, room_target, room_write

ROOM_OFFSET_LIMIT = 3.0


@dataclass(frozen=True, kw_only=True)
class ProxonNumberDescription(NumberEntityDescription):
    room: int | None = None


def _temp(key: str, tk: str, lo: float, hi: float, room: int | None = None, step: float = 1) -> ProxonNumberDescription:
    return ProxonNumberDescription(
        key=key, translation_key=tk, native_min_value=lo, native_max_value=hi, native_step=step,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.SLIDER, room=room,
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
    # the living room's target is stored in hundredths of a degree, so it can be set in half degrees;
    # the other rooms store a whole-degree offset to their own base value
    _temp("NBE0MittelTemperatur", "room_target", 10, 30, 0, step=0.5),
    *[_temp(f"NBE{i}Ziel", "room_target", 14, 26, i) for i in range(1, ROOM_COUNT)],
]


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities = []
    for d in NUMBERS:
        if d.room is not None:
            if room_target(data, d.room) is None or not room_connected(data, d.room):
                continue
        elif d.key not in data or (d.key == "GrenzwertCO2" and not data.get("CurrentCO2")):
            continue
        entities.append(ProxonNumber(coordinator, d))
    async_add_entities(entities)


class ProxonNumber(ProxonEntity, NumberEntity):
    entity_description: ProxonNumberDescription

    def __init__(self, coordinator, description: ProxonNumberDescription) -> None:
        placeholders = {"room": room_name(description.room, coordinator.data)} if description.room is not None else None
        super().__init__(coordinator, description.key, description.translation_key or description.key, placeholders)
        self.entity_description = description

    @property
    def value(self) -> float | None:
        if self.entity_description.room is not None:
            return room_target(self.coordinator.data or {}, self.entity_description.room)
        return super().value

    @property
    def native_value(self) -> float | None:
        return self.value

    async def async_set_native_value(self, value: float) -> None:
        data = self.coordinator.data or {}
        room = self.entity_description.room
        if self._key == "Luefterstufe" and (data.get("Intensivlueftung") or int(data.get("Betriebsart", -1)) == MODE_COMFORT):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="level_locked")
        if room is not None and room > 0:
            base = room_base(data, room)
            if base is None:
                base = data.get("NBE0MittelTemperatur", 20.0)
            if abs(value - base) > ROOM_OFFSET_LIMIT:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="room_limit",
                    translation_placeholders={"low": f"{base - ROOM_OFFSET_LIMIT:g}", "high": f"{base + ROOM_OFFSET_LIMIT:g}"},
                )
        if room is not None:
            key, raw = room_write(data, room, value)
            await self.coordinator.async_write(key, raw)
        else:
            await self.coordinator.async_write(self._key, value)
