"""Dashboard pictures as image entities: the unit, the hot-water tank and the house, drawn from the live values (pictures.py).

The pictures are SVG with animations. A new picture is only announced when it actually changes, so the dashboard reloads it
then and not on every query of the unit.
"""
from __future__ import annotations

import hashlib

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ProxonConfigEntry
from .entity import ProxonEntity, room_name
from .pictures import Room, house_svg, tank_svg, unit_svg
from .registers import ROOM_COUNT, room_connected, room_target


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities = [ProxonPicture(hass, coordinator, "BildAnlage", "picture_unit", "unit"), ProxonPicture(hass, coordinator, "BildHaus", "picture_house", "house")]
    if "WarmwasserIstTemperatur" in data:
        entities.insert(1, ProxonPicture(hass, coordinator, "BildWarmwasser", "picture_hot_water", "tank"))
    async_add_entities(entities)


class ProxonPicture(ProxonEntity, ImageEntity):
    _attr_content_type = "image/svg+xml"

    def __init__(self, hass: HomeAssistant, coordinator, key: str, tk: str, kind: str) -> None:
        ProxonEntity.__init__(self, coordinator, key, tk)
        ImageEntity.__init__(self, hass)
        self._kind = kind
        self._svg = b""
        self._hash = ""

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    def _draw(self) -> str:
        data = self.coordinator.data or {}
        lang = self.hass.config.language if self.hass else "de"
        if self._kind == "unit":
            return unit_svg(data, lang)
        if self._kind == "tank":
            boost = getattr(self.coordinator, "comfort", None)
            limit = boost.boost.settings.limit if boost and boost.boost.settings.on else None
            return tank_svg(data, lang, limit)
        rooms = [
            Room(room_name(i, data), _f(data.get(f"NBE{i}Temperatur")), room_target(data, i), bool(data.get(f"NBE{i}PTC")))
            for i in range(ROOM_COUNT)
            if room_connected(data, i) and room_target(data, i) is not None
        ]
        return house_svg(rooms, _f(data.get("T3Frischluft")), lang)

    @callback
    def _refresh(self) -> None:
        svg = self._draw().encode()
        digest = hashlib.sha1(svg).hexdigest()
        if digest != self._hash:
            self._svg, self._hash = svg, digest
            self._attr_image_last_updated = dt_util.utcnow()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        if not self._svg:
            self._refresh()
        return self._svg


def _f(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None
