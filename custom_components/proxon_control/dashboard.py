"""Ready-made dashboard: built from the entities this unit really has (with their real entity IDs), to paste as it is.

Sections view (columns side by side on wide screens, one below the other on a phone), built-in cards only:
unit picture with ventilation, hot-water picture with hot water and boost, house picture with the room thermostats,
and the functions (switches, limits, status).
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

TITLES = {
    "de": {"view": "Lüftung & Wärme", "unit": "Anlage", "tank": "Warmwasser", "house": "Haus", "functions": "Funktionen", "settings": "Einstellungen", "status": "Status"},
    "en": {"view": "Ventilation & heat", "unit": "Unit", "tank": "Hot water", "house": "House", "functions": "Functions", "settings": "Settings", "status": "Status"},
}


def _ids(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """unique-id suffix -> entity ID, for this unit's entities (left out when disabled)."""
    base = f"{entry.unique_id or entry.entry_id}_"
    out = {}
    for ent in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        if ent.disabled_by is None and ent.unique_id.startswith(base):
            out[ent.unique_id[len(base):]] = ent.entity_id
    return out


def build(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    t = TITLES["de" if (hass.config.language or "").startswith("de") else "en"]
    ids = _ids(hass, entry)

    def tile(key: str, **extra) -> list[dict]:
        return [{"type": "tile", "entity": ids[key], **extra}] if key in ids else []

    def picture(key: str) -> list[dict]:
        return [{"type": "picture-entity", "entity": ids[key], "show_name": False, "show_state": False}] if key in ids else []

    def heading(text: str) -> dict:
        return {"type": "heading", "heading": text}

    unit = [heading(t["unit"]), *picture("BildAnlage"),
            *tile("Lueftung", features=[{"type": "fan-speed"}], features_position="inline"),
            *tile("Betriebsart", features=[{"type": "select-options"}]), *tile("Intensivlueftung"), *tile("Stoerung"),
            *tile("FilterRestStunden_warning")]
    tank = [heading(t["tank"]), *picture("BildWarmwasser"),
            *tile("Warmwasser", features=[{"type": "water-heater-operation-modes", "operation_modes": ["off", "heat_pump", "high_demand", "electric"]}]),
            *tile("WarmwasserBoost"), *tile("BoostStatus")]
    rooms = sorted((k for k in ids if k.startswith("NBE") and k.endswith("Thermostat")), key=lambda k: int(k[3:-10]))
    house = [heading(t["house"]), *picture("BildHaus"),
             *[c for k in rooms for c in tile(k, features=[{"type": "target-temperature"}])]]
    switches = [c for k in ("SolarWarmwasser", "PreisWarmwasser", "Nachtkuehlung", "WarmwasserBoost", "Urlaubsmodus") for c in tile(k)]
    settings = [ids[k] for k in ("SolarSchwelle", "PreisSchwelle", "SpeicherTemperatur", "KuehlWunsch", "KuehlStufe", "BoostGrenze") if k in ids]
    status = [ids[k] for k in ("Energiemanager", "NachtkuehlungStatus", "BoostStatus", "Antwortzeit_path") if k in ids]
    functions = [heading(t["functions"]), *switches]
    if settings:
        functions.append({"type": "entities", "title": t["settings"], "entities": settings})
    if status:
        functions.append({"type": "entities", "title": t["status"], "entities": status})
    sections = [{"type": "grid", "cards": cards} for cards in (unit, tank, house, functions) if len(cards) > 1]
    return {"views": [{"title": t["view"], "path": "proxon", "icon": "mdi:hvac", "type": "sections", "max_columns": 4, "sections": sections}]}
