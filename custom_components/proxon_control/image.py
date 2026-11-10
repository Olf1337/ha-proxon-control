"""Dashboard pictures as image entities: the unit, the hot-water tank and the house, drawn from the live values (pictures.py).

The pictures are SVG with animations. Every new picture makes the dashboard load it again, which restarts the animations, so a
new picture is announced right away only when something switches (mode, level, heater, a function, a room's heating element),
and otherwise - for changing temperatures - at most once a minute.
"""
from __future__ import annotations

import hashlib
import time

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import ProxonConfigEntry
from .const import CONF_PICTURE_THEME, DEFAULT_PICTURE_THEME
from .entity import ProxonEntity, room_name
from .pictures import Room, house_svg, tank_svg, unit_svg
from .registers import ROOM_COUNT, active_faults, room_connected, room_target

TEMPERATURES_EVERY = 60  # seconds: changed temperatures are shown at most this often


async def async_setup_entry(hass: HomeAssistant, entry: ProxonConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data or {}
    entities = [ProxonPicture(hass, coordinator, "BildAnlage", "picture_unit", "unit"), ProxonPicture(hass, coordinator, "BildHaus", "picture_house", "house")]
    if "WarmwasserIstTemperatur" in data:
        entities.insert(1, ProxonPicture(hass, coordinator, "BildWarmwasser", "picture_hot_water", "tank"))
    async_add_entities(entities)


def _f(v) -> float | None:
    return float(v) if isinstance(v, (int, float)) else None


class ProxonPicture(ProxonEntity, ImageEntity):
    _attr_content_type = "image/svg+xml"

    def __init__(self, hass: HomeAssistant, coordinator, key: str, tk: str, kind: str) -> None:
        ProxonEntity.__init__(self, coordinator, key, tk)
        ImageEntity.__init__(self, hass)
        self._kind = kind
        self._svg = b""
        self._hash = ""
        self._signature: tuple | None = None
        self._announced = 0.0

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    def _features(self):
        energy = getattr(self.coordinator, "energy", None)
        comfort = getattr(self.coordinator, "comfort", None)
        return energy, (comfort.cooling if comfort else None), (comfort.boost if comfort else None)

    def _draw(self) -> tuple[str, tuple]:
        """The picture, and what makes it look different apart from temperatures (a change there is shown right away)."""
        data = self.coordinator.data or {}
        lang = self.hass.config.language if self.hass else "de"
        theme = self.coordinator.config_entry.options.get(CONF_PICTURE_THEME, DEFAULT_PICTURE_THEME)
        energy, cooling, boost = self._features()
        if self._kind == "unit":
            cooling_status = cooling.status if cooling and cooling.supported and cooling.settings.on else None
            fault = bool(active_faults(data))
            sig = (data.get("Betriebsart"), data.get("IstLuefterstufe"), data.get("Luefterstufe"), bool(data.get("DrehzahlKompressor")),
                   data.get("Kuehlbetrieb4Wegeventil"), data.get("Intensivlueftung"), fault, cooling_status, theme, lang)
            return unit_svg(data, lang, theme, cooling_status, fault), sig
        if self._kind == "tank":
            energy_on = energy and energy.supported and (energy.settings.solar_on or energy.settings.price_on)
            energy_status = energy.status if energy_on else None
            boost_on = boost and boost.supported and boost.settings.on
            boost_status = boost.status if boost_on else None
            limit = boost.settings.limit if boost_on else None
            sig = (data.get("E-Heizstab"), data.get("T300Betriebsart"), data.get("SollWassertemperatur"), data.get("Soll-E-Heizstab-Temperatur"),
                   energy_status, boost_status, limit, theme, lang)
            return tank_svg(data, lang, limit, theme, energy_status, boost_status), sig
        rooms = [
            Room(room_name(i, data), _f(data.get(f"NBE{i}Temperatur")), room_target(data, i), bool(data.get(f"NBE{i}PTC")))
            for i in range(ROOM_COUNT)
            if room_connected(data, i) and room_target(data, i) is not None
        ]
        sig = (tuple((r.name, r.target, r.heating) for r in rooms), theme, lang)
        return house_svg(rooms, _f(data.get("T3Frischluft")), lang, theme), sig

    @callback
    def _refresh(self) -> bool:
        """Draw the picture; announce it when it shows something new. Returns whether it was announced."""
        svg, signature = self._draw()
        raw = svg.encode()
        digest = hashlib.sha1(raw).hexdigest()
        if digest == self._hash:
            return False
        now = time.monotonic()
        if self._hash and signature == self._signature and now - self._announced < TEMPERATURES_EVERY:
            return False  # only temperatures changed, and the last picture is less than a minute old
        self._svg, self._hash, self._signature, self._announced = raw, digest, signature, now
        self._attr_image_last_updated = dt_util.utcnow()
        return True

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._refresh()
        # functions switched on/off or changing their status show up right away
        for feature in self._features():
            if feature is not None:
                self.async_on_remove(feature.add_entity_listener(self._feature_changed))

    @callback
    def _feature_changed(self) -> None:
        if self._refresh():
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._refresh()
        super()._handle_coordinator_update()

    async def async_image(self) -> bytes | None:
        if not self._svg:
            self._refresh()
        return self._svg
