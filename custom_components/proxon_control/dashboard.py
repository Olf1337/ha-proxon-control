"""Ready-made dashboard: built from the entities this unit really has (with their real entity IDs), to paste as it is.

Two tabs, built-in cards only:
* Overview - unit and house as large pictures (two columns wide), next to them hot water and the functions. The pictures can be
  tapped: the unit opens the ventilation, the tank the hot water, every room its thermostat. Function tiles span the full width,
  with short names and what the function is doing ("On · Waiting").
* Settings - limits with +/- buttons, weekly schedule, diagnostics.
On a phone the sections are shown one below the other.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .pictures import TANK_H, TANK_W, UNIT_H, UNIT_W, HOUSE_W, house_layout, house_targets, tank_targets, unit_targets

TEXT = {
    "de": {
        "overview": "Übersicht", "settings": "Einstellungen", "unit": "Anlage", "tank": "Warmwasser", "house": "Haus",
        "functions": "Funktionen", "store": "Warmwasser-Speicher (Solar / Strompreis)", "cooling": "Sommer-Nachtkühlung",
        "boost": "Warmwasser-Boost", "schedule": "Wochenprogramm Lüftung", "diagnostics": "Diagnose",
        "names": {
            "Lueftung": "Lüftung", "Betriebsart": "Betriebsart", "Warmwasser": "Warmwasser", "Stoerung": "Störung",
            "FilterRestStunden_warning": "Filterwechsel", "SolarWarmwasser": "Solar-Warmwasser", "PreisWarmwasser": "Günstiger Strom",
            "Nachtkuehlung": "Nachtkühlung", "WarmwasserBoost": "Warmwasser-Boost", "Urlaubsmodus": "Urlaubsmodus",
            "Intensivlueftung": "Intensivlüftung", "SolarSchwelle": "Solar-Überschuss ab", "PreisSchwelle": "Strompreis bis",
            "SpeicherTemperatur": "Speichertemperatur", "Energiemanager": "Status", "KuehlWunsch": "Wunschtemperatur",
            "KuehlStufe": "Kühlstufe", "NachtkuehlungStatus": "Status", "BoostGrenze": "Boost unter",
            "Soll-E-Heizstab-Temperatur": "Heizstab-Soll", "BoostStatus": "Status", "SollWassertemperatur": "Warmwasser-Soll",
            "WarmwasserLadezustand": "Ladezustand", "Legionellenfunktion": "Legionellenschaltung", "AktuellerBetrieb": "Betrieb",
            "Waermerueckgewinnung": "Wärmerückgewinnung", "IntensivlueftungsDauer": "Dauer Intensivlüftung",
            "LeistungGesamt": "Leistung", "EnergieGesamt": "Verbrauch",
            "ZeitprogrammMoDiFr": "Montag → Dienstag bis Freitag", "ZeitprogrammMoAlle": "Montag → alle Tage",
        },
        "holiday_confirm": "Urlaubsmodus umschalten? Das ändert Lüftung, Raumtemperaturen und Warmwasser.",
        "days": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], "schedule_on": "Programm aktiv",
        "diag": {"Antwortzeit": "Antwortzeit", "Antwortzeit_path": "Verbindungsweg", "Uhr": "Uhr der Anlage",
                 "FilterRestStunden": "Filter-Restlaufzeit", "FirmwareVersion": "Firmware", "Betriebsstundenzaehler": "Betriebsstunden",
                 "UhrAbweichung": "Uhrabweichung", "LetzterSchreibfehler": "Letzter Schreibfehler", "FirmwareT300": "Firmware Warmwasser"},
    },
    "en": {
        "overview": "Overview", "settings": "Settings", "unit": "Unit", "tank": "Hot water", "house": "House",
        "functions": "Functions", "store": "Hot-water store (solar / price)", "cooling": "Summer night cooling",
        "boost": "Hot-water boost", "schedule": "Weekly ventilation schedule", "diagnostics": "Diagnostics",
        "names": {
            "Lueftung": "Ventilation", "Betriebsart": "Operating mode", "Warmwasser": "Hot water", "Stoerung": "Fault",
            "FilterRestStunden_warning": "Filter change", "SolarWarmwasser": "Solar hot water", "PreisWarmwasser": "Cheap power",
            "Nachtkuehlung": "Night cooling", "WarmwasserBoost": "Hot-water boost", "Urlaubsmodus": "Holiday mode",
            "Intensivlueftung": "Boost ventilation", "SolarSchwelle": "Solar surplus from", "PreisSchwelle": "Price up to",
            "SpeicherTemperatur": "Store temperature", "Energiemanager": "Status", "KuehlWunsch": "Wish temperature",
            "KuehlStufe": "Cooling level", "NachtkuehlungStatus": "Status", "BoostGrenze": "Boost below",
            "Soll-E-Heizstab-Temperatur": "Heater target", "BoostStatus": "Status", "SollWassertemperatur": "Hot-water target",
            "WarmwasserLadezustand": "Charge", "Legionellenfunktion": "Legionella protection", "AktuellerBetrieb": "Operation",
            "Waermerueckgewinnung": "Heat recovery", "IntensivlueftungsDauer": "Boost duration",
            "LeistungGesamt": "Power", "EnergieGesamt": "Consumption",
            "ZeitprogrammMoDiFr": "Monday → Tuesday to Friday", "ZeitprogrammMoAlle": "Monday → all days",
        },
        "holiday_confirm": "Switch holiday mode? This changes ventilation, room temperatures and hot water.",
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], "schedule_on": "Schedule active",
        "diag": {"Antwortzeit": "Response time", "Antwortzeit_path": "Connection path", "Uhr": "Unit clock",
                 "FilterRestStunden": "Filter time left", "FirmwareVersion": "Firmware", "Betriebsstundenzaehler": "Working hours",
                 "UhrAbweichung": "Clock deviation", "LetzterSchreibfehler": "Last write error", "FirmwareT300": "Hot-water firmware"},
    },
}

FULL = {"columns": "full"}
HALF = {"columns": 6}
# functions that report what they are doing (status attribute, shown on the tile next to on/off)
WITH_STATUS = ("SolarWarmwasser", "PreisWarmwasser", "Nachtkuehlung", "WarmwasserBoost")


def _ids(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, str]:
    """unique-id suffix -> entity ID, for this unit's entities (left out when disabled)."""
    base = f"{entry.unique_id or entry.entry_id}_"
    out = {}
    for ent in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id):
        if ent.disabled_by is None and ent.unique_id.startswith(base):
            out[ent.unique_id[len(base):]] = ent.entity_id
    return out


def _area(entity_id: str, target: tuple[float, float, float, float], picture: tuple[int, int]) -> dict:
    """An invisible tap area on a picture that opens the entity's dialog: a transparent image with the area's shape
    (an image element reacts on its whole surface; its height follows from the shape)."""
    x, y, w, h = target
    shape_w, shape_h = w / 100 * picture[0], h / 100 * picture[1]
    return {
        "type": "image", "entity": entity_id, "tap_action": {"action": "more-info"},
        "image": f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {shape_w:.0f} {shape_h:.0f}'/%3E",
        "style": {"left": f"{x:.1f}%", "top": f"{y:.1f}%", "width": f"{w:.1f}%", "cursor": "pointer"},
    }


def build(hass: HomeAssistant, entry: ConfigEntry) -> dict:
    t = TEXT["de" if (hass.config.language or "").startswith("de") else "en"]
    ids = _ids(hass, entry)
    names = t["names"]

    def tile(key: str, grid: dict = FULL, **extra) -> list[dict]:
        if key not in ids:
            return []
        card = {"type": "tile", "entity": ids[key], "grid_options": grid}
        if key in names:
            card["name"] = names[key]
        return [{**card, **extra}]

    def number(key: str) -> list[dict]:
        return tile(key, FULL, features=[{"type": "numeric-input", "style": "buttons"}], features_position="inline")

    def picture(key: str, areas: list[dict]) -> list[dict]:
        if key not in ids:
            return []
        return [{"type": "picture-elements", "image_entity": ids[key], "elements": areas, "grid_options": FULL}]

    def heading(text: str) -> dict:
        return {"type": "heading", "heading": text, "heading_style": "title"}

    # ---- overview ----
    # the pictures carry their own titles: no extra headings above them
    unit_areas = [_area(ids["Lueftung"], unit_targets()["unit"], (UNIT_W, UNIT_H))] if "Lueftung" in ids else []
    unit = [
        *picture("BildAnlage", unit_areas),
        *tile("Lueftung", HALF, features=[{"type": "fan-speed"}], features_position="inline"),
        *tile("Betriebsart", HALF, features=[{"type": "select-options"}], features_position="inline"),
        *tile("Stoerung", HALF), *tile("FilterRestStunden_warning", HALF),
        *tile("AktuellerBetrieb", HALF), *tile("Waermerueckgewinnung", HALF),
        *tile("LeistungGesamt", HALF), *tile("EnergieGesamt", HALF),
    ]
    tank_areas = [_area(ids["Warmwasser"], tank_targets()["tank"], (TANK_W, TANK_H))] if "Warmwasser" in ids else []
    tank = [
        *picture("BildWarmwasser", tank_areas),
        *tile("Warmwasser", FULL, features=[{"type": "water-heater-operation-modes", "operation_modes": ["off", "heat_pump", "high_demand", "electric"]}]),
        *tile("WarmwasserLadezustand", FULL),
    ]
    rooms = sorted((k for k in ids if k.startswith("NBE") and k.endswith("Thermostat")), key=lambda k: int(k[3:-10]))
    house_size = (HOUSE_W, house_layout(len(rooms))[0])
    house_areas = [_area(ids[k], target, house_size) for k, target in zip(rooms, house_targets(len(rooms)))]
    house = picture("BildHaus", house_areas)
    functions = [heading(t["functions"])]
    for key in ("SolarWarmwasser", "PreisWarmwasser", "Nachtkuehlung", "WarmwasserBoost", "Urlaubsmodus", "Intensivlueftung"):
        extra: dict = {"state_content": ["state", "status"]} if key in WITH_STATUS else {}
        if key == "Urlaubsmodus":
            extra["icon_tap_action"] = {"action": "toggle", "confirmation": {"text": t["holiday_confirm"]}}
        functions += tile(key, FULL, **extra)
    # two columns without gaps: unit and house on the left (two columns wide), hot water and functions on the right
    if len(functions) == 1:
        functions = []
    overview = [
        {"type": "grid", "column_span": 2, "cards": [*unit, *house]},
        {"type": "grid", "cards": [*tank, *functions]},
    ]
    overview = [s for s in overview if s["cards"]]

    # ---- settings ----
    store = [heading(t["store"]), *tile("SolarWarmwasser", FULL, state_content=["state", "status"]), *number("SolarSchwelle"),
             *tile("PreisWarmwasser", FULL, state_content=["state", "status"]), *number("PreisSchwelle"), *number("SpeicherTemperatur")]
    cooling = [heading(t["cooling"]), *tile("Nachtkuehlung", FULL, state_content=["state", "status"]), *number("KuehlWunsch"),
               *number("KuehlStufe")]
    boost = [heading(t["boost"]), *tile("WarmwasserBoost", FULL, state_content=["state", "status"]), *number("BoostGrenze"),
             *number("Soll-E-Heizstab-Temperatur"), *number("SollWassertemperatur"), *tile("Legionellenfunktion", FULL),
             *number("IntensivlueftungsDauer")]
    rows = [("ZeitprogrammAktiv", t["schedule_on"]), *[(f"Zeitprogramm{d}", t["days"][d]) for d in range(7)]]
    schedule_rows = [{"entity": ids[k], "name": name} for k, name in rows if k in ids]
    schedule = [heading(t["schedule"]), {"type": "entities", "entities": schedule_rows, "grid_options": FULL}] if schedule_rows else []
    if schedule:  # copy Monday with one tap (asks first: it changes several days)
        for key in ("ZeitprogrammMoDiFr", "ZeitprogrammMoAlle"):
            schedule += tile(key, HALF, icon_tap_action={"action": "perform-action", "perform_action": "button.press",
                                                          "target": {"entity_id": ids.get(key)}, "confirmation": True},
                             tap_action={"action": "perform-action", "perform_action": "button.press",
                                         "target": {"entity_id": ids.get(key)}, "confirmation": True})
    diag_rows = [{"entity": ids[k], "name": name} for k, name in t["diag"].items() if k in ids]
    diagnostics = [heading(t["diagnostics"]), {"type": "entities", "entities": diag_rows, "grid_options": FULL}] if diag_rows else []
    settings = [{"type": "grid", "cards": cards} for cards in (store, cooling, boost, schedule, diagnostics) if len(cards) > 1]

    views = [{"title": t["overview"], "path": "proxon", "icon": "mdi:hvac", "type": "sections", "max_columns": 3,
              "sections": overview}]
    if settings:
        views.append({"title": t["settings"], "path": "proxon-settings", "icon": "mdi:tune", "type": "sections", "max_columns": 3,
                      "sections": settings})
    return {"views": views}
