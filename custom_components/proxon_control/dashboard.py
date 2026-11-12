"""Ready-made dashboard: built from the entities this unit really has (with their real entity IDs), to paste as it is.

Four tabs, built-in cards only:
* Home - made for the phone: your own house photo (option) with outdoor, indoor, hot water and operation on it (without a
  photo the drawn house), every room as a card with its temperature curve (tap: its thermostat), next to it ventilation,
  hot water and the functions with what they are doing ("On · Waiting").
* House - the house drawn isometric (both floors, ducts, heating elements; tap a room for its thermostat) and the unit (tap:
  the ventilation), the heating elements and the unit's values.
* Hot water - the T300 cut open (tap: the water heater), its controls, the temperatures of the last 24 hours, its switches.
* Settings - limits with +/- buttons, weekly schedule, runtimes, diagnostics.
On a phone the sections are shown one below the other.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_HOUSE_PHOTO
from .entity import house_rooms, room_floors, room_name
from .pictures import TANK_H, TANK_W, UNIT_H, UNIT_W, house_layout, house_targets, tank_targets, unit_targets

TEXT: dict[str, dict[str, Any]] = {
    "de": {
        "home": "Zuhause", "settings": "Einstellungen", "unit": "Anlage", "tank": "Warmwasser", "house": "Haus",
        "rooms": "Räume", "floors": ["Erdgeschoss", "Obergeschoss"], "now": "Gerade", "elements": "Wärmeelemente",
        "last_day": "Letzte 24 Stunden", "switches": "Schalter", "pills": {"T3Frischluft": "Außen ", "RaumMittel": "Innen ",
                                                                          "WarmwasserIstTemperatur": "Warmwasser "},
        "functions": "Funktionen", "store": "Warmwasser-Speicher (Solar / Strompreis)", "cooling": "Sommer-Nachtkühlung",
        "boost": "Warmwasser-Boost", "schedule": "Wochenprogramm Lüftung", "diagnostics": "Diagnose",
        "season": "Sommer/Winter-Automatik", "night": "Nachtabsenkung", "runtime": "Laufzeit heute",
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
            "SaisonAutomatik": "Sommer/Winter automatisch", "SaisonWinterUnter": "Winter unter", "SaisonSommerUeber": "Sommer über",
            "NachtabsenkungAktiv": "Nachtabsenkung", "NachtabsenkungTemperatur": "Nachttemperatur", "NachtabsenkungStart": "Beginn",
            "NachtabsenkungEnde": "Ende", "KompressorStartsHeute": "Kompressor-Starts", "KompressorLaufzeitHeute": "Kompressor",
            "WarmwasserKompressorLaufzeitHeute": "Warmwasser-Kompressor", "HeizstabLaufzeitHeute": "Heizstab",
            "ZeitprogrammMoDiFr": "Montag → Dienstag bis Freitag", "ZeitprogrammMoAlle": "Montag → alle Tage",
            "WarmwasserIstTemperatur": "Warmwasser Mitte", "WarmwasserUntenTemperatur": "Warmwasser unten",
            "T300Betriebsart": "Wärmepumpe Warmwasser", "E-Heizstab": "Heizstab freigegeben",
        },
        "holiday_confirm": "Urlaubsmodus umschalten? Das ändert Lüftung, Raumtemperaturen und Warmwasser.",
        "days": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], "schedule_on": "Programm aktiv",
        "diag": {"Antwortzeit": "Antwortzeit", "Antwortzeit_path": "Verbindungsweg", "Uhr": "Uhr der Anlage",
                 "FilterRestStunden": "Filter-Restlaufzeit", "FirmwareVersion": "Firmware", "Betriebsstundenzaehler": "Betriebsstunden",
                 "UhrAbweichung": "Uhrabweichung", "LetzterSchreibfehler": "Letzter Schreibfehler", "FirmwareT300": "Firmware Warmwasser"},
    },
    "en": {
        "home": "Home", "settings": "Settings", "unit": "Unit", "tank": "Hot water", "house": "House",
        "rooms": "Rooms", "floors": ["Ground floor", "Upper floor"], "now": "Right now", "elements": "Heating elements",
        "last_day": "Last 24 hours", "switches": "Switches", "pills": {"T3Frischluft": "Outdoor ", "RaumMittel": "Indoor ",
                                                                       "WarmwasserIstTemperatur": "Hot water "},
        "functions": "Functions", "store": "Hot-water store (solar / price)", "cooling": "Summer night cooling",
        "boost": "Hot-water boost", "schedule": "Weekly ventilation schedule", "diagnostics": "Diagnostics",
        "season": "Summer/winter automatic", "night": "Night setback", "runtime": "Runtime today",
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
            "SaisonAutomatik": "Automatic summer/winter", "SaisonWinterUnter": "Winter below", "SaisonSommerUeber": "Summer above",
            "NachtabsenkungAktiv": "Night setback", "NachtabsenkungTemperatur": "Night temperature", "NachtabsenkungStart": "Start",
            "NachtabsenkungEnde": "End", "KompressorStartsHeute": "Compressor starts", "KompressorLaufzeitHeute": "Compressor",
            "WarmwasserKompressorLaufzeitHeute": "Hot-water compressor", "HeizstabLaufzeitHeute": "Immersion heater",
            "ZeitprogrammMoDiFr": "Monday → Tuesday to Friday", "ZeitprogrammMoAlle": "Monday → all days",
            "WarmwasserIstTemperatur": "Hot water middle", "WarmwasserUntenTemperatur": "Hot water bottom",
            "T300Betriebsart": "Hot-water heat pump", "E-Heizstab": "Immersion heater released",
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
WITH_STATUS = ("SolarWarmwasser", "PreisWarmwasser", "Nachtkuehlung", "WarmwasserBoost", "SaisonAutomatik")
FUNCTIONS = ("SolarWarmwasser", "PreisWarmwasser", "Nachtkuehlung", "WarmwasserBoost", "SaisonAutomatik", "Urlaubsmodus", "Intensivlueftung")
# values on the house photo: two rows of two at its bottom left, held by the bottom edge (whatever the photo's shape)
PILL_SPOTS = (("12px", "52px"), ("12px", "12px"), ("min(52%, 160px)", "52px"), ("min(52%, 160px)", "12px"))
PILL_STYLE = {
    "top": "auto", "transform": "none", "background": "rgba(17, 24, 39, 0.6)", "color": "#ffffff", "padding": "0 4px",
    "border-radius": "999px", "font-size": "14px", "font-weight": "500", "line-height": "18px",
    "backdrop-filter": "blur(6px)", "-webkit-backdrop-filter": "blur(6px)",
}


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
    coordinator = getattr(entry, "runtime_data", None)
    data: dict = getattr(coordinator, "data", None) or {}

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

    def heading(text: str, style: str = "title") -> dict:
        return {"type": "heading", "heading": text, "heading_style": style}

    def function_tiles() -> list[dict]:
        cards: list[dict] = []
        for key in FUNCTIONS:
            extra: dict = {"state_content": ["state", "status"]} if key in WITH_STATUS else {}
            if key == "Urlaubsmodus":
                extra["icon_tap_action"] = {"action": "toggle", "confirmation": {"text": t["holiday_confirm"]}}
            cards += tile(key, FULL, **extra)
        return [heading(t["functions"]), *cards] if cards else []

    # ---- the pictures, with their tap areas ----
    unit_areas = [_area(ids["Lueftung"], unit_targets()["unit"], (UNIT_W, UNIT_H))] if "Lueftung" in ids else []
    tank_areas = [_area(ids["Warmwasser"], tank_targets()["tank"], (TANK_W, TANK_H))] if "Warmwasser" in ids else []
    rooms = house_rooms(data)
    floors = room_floors(entry.options, data, rooms)
    layout = house_layout(floors)
    house_areas = [
        _area(ids[f"NBE{i}Thermostat"], target, (layout.width, layout.height))
        for i, target in zip(rooms, house_targets(floors)) if f"NBE{i}Thermostat" in ids
    ]
    unit_picture, tank_picture, house_picture = picture("BildAnlage", unit_areas), picture("BildWarmwasser", tank_areas), picture("BildHaus", house_areas)

    # ---- home: photo (or the drawn house), rooms, what's going on ----
    photo = entry.options.get(CONF_HOUSE_PHOTO)
    if photo:
        pills = []
        shown = [k for k in ("T3Frischluft", "RaumMittel", "WarmwasserIstTemperatur", "AktuellerBetrieb") if k in ids]  # by column
        for (left, bottom), value in zip(PILL_SPOTS, shown):
            pill: dict = {"type": "state-label", "entity": ids[value], "style": {"left": left, "bottom": bottom, **PILL_STYLE}}
            if value in t["pills"]:
                pill["prefix"] = t["pills"][value]
            if value == "WarmwasserIstTemperatur" and "Warmwasser" in ids:
                pill["tap_action"] = {"action": "more-info", "entity": ids["Warmwasser"]}
            pills.append(pill)
        hero = [{"type": "picture-elements", "image": photo, "dark_mode_filter": "brightness(0.85)", "elements": pills, "grid_options": FULL}]
    else:
        hero = house_picture
    room_cards: list[dict] = []
    for floor in (0, 1):
        cards = []
        for i, f in zip(rooms, floors):
            sensor, thermostat = f"NBE{i}Temperatur", ids.get(f"NBE{i}Thermostat")
            if f != floor or sensor not in ids:
                continue
            card: dict = {"type": "tile", "entity": ids[sensor], "name": room_name(i, data), "grid_options": HALF,
                          "features": [{"type": "trend-graph", "hours_to_show": 24}]}
            if thermostat:
                card["tap_action"] = card["icon_tap_action"] = {"action": "more-info", "entity": thermostat}
            cards.append(card)
        if cards:
            title = t["floors"][floor] if any(floors) else t["rooms"]
            room_cards += [heading(title, "subtitle" if any(floors) else "title"), *cards]
    now = [
        heading(t["now"]),
        *tile("Lueftung", FULL, features=[{"type": "fan-speed"}], features_position="inline"),
        *tile("Betriebsart", FULL, features=[{"type": "select-options"}], features_position="inline"),
        *tile("AktuellerBetrieb", HALF), *tile("LeistungGesamt", HALF),
        *tile("Warmwasser", HALF), *tile("WarmwasserLadezustand", HALF),
        *tile("Stoerung", HALF), *tile("FilterRestStunden_warning", HALF),
    ]
    home: list[dict[str, Any]] = [{"type": "grid", "column_span": 2, "cards": [*hero, *room_cards]},
            {"type": "grid", "cards": [*(now if len(now) > 1 else []), *function_tiles()]}]

    # ---- house: the drawing, the unit, heating elements, the unit's values ----
    elements = [{"entity": ids[f"NBE{i}Waermeelement"], "name": room_name(i, data)} for i in rooms if f"NBE{i}Waermeelement" in ids]
    house_side = [
        *([heading(t["elements"]), {"type": "entities", "entities": elements, "grid_options": FULL}] if elements else []),
        heading(t["unit"]),
        *tile("AktuellerBetrieb", HALF), *tile("Waermerueckgewinnung", HALF),
        *tile("LeistungGesamt", HALF), *tile("EnergieGesamt", HALF),
        *tile("Stoerung", HALF), *tile("FilterRestStunden_warning", HALF),
    ]
    house: list[dict[str, Any]] = [{"type": "grid", "column_span": 2, "cards": [*house_picture, *unit_picture]},
             {"type": "grid", "cards": house_side if len(house_side) > 1 else []}]

    # ---- hot water: the T300 cut open, controls, the last day, switches ----
    curve = [ids[k] for k in ("WarmwasserIstTemperatur", "WarmwasserUntenTemperatur") if k in ids]
    water = [
        *tile("Warmwasser", FULL, features=[
            {"type": "water-heater-operation-modes", "operation_modes": ["off", "heat_pump", "high_demand", "electric"]},
            {"type": "target-temperature"},
        ]),
        *tile("WarmwasserLadezustand", HALF), *tile("WarmwasserUntenTemperatur", HALF),
        *([heading(t["last_day"], "subtitle"), {"type": "history-graph", "entities": curve, "hours_to_show": 24, "grid_options": FULL}]
          if curve else []),
    ]
    switches = [*tile("T300Betriebsart", FULL), *tile("E-Heizstab", FULL), *tile("Legionellenfunktion", FULL),
                *tile("SolarWarmwasser", FULL, state_content=["state", "status"]), *tile("PreisWarmwasser", FULL, state_content=["state", "status"]),
                *tile("WarmwasserBoost", FULL, state_content=["state", "status"]), *number("SollWassertemperatur"),
                *number("Soll-E-Heizstab-Temperatur")]
    hot_water: list[dict[str, Any]] = [{"type": "grid", "cards": tank_picture}, {"type": "grid", "cards": water},
                 {"type": "grid", "cards": [heading(t["switches"]), *switches] if switches else []}]

    # ---- settings ----
    store = [heading(t["store"]), *tile("SolarWarmwasser", FULL, state_content=["state", "status"]), *number("SolarSchwelle"),
             *tile("PreisWarmwasser", FULL, state_content=["state", "status"]), *number("PreisSchwelle"), *number("SpeicherTemperatur")]
    cooling = [heading(t["cooling"]), *tile("Nachtkuehlung", FULL, state_content=["state", "status"]), *number("KuehlWunsch"),
               *number("KuehlStufe")]
    boost = [heading(t["boost"]), *tile("WarmwasserBoost", FULL, state_content=["state", "status"]), *number("BoostGrenze"),
             *number("Soll-E-Heizstab-Temperatur"), *number("SollWassertemperatur"), *tile("Legionellenfunktion", FULL),
             *number("IntensivlueftungsDauer")]
    season = [heading(t["season"]), *tile("SaisonAutomatik", FULL, state_content=["state", "status"]), *number("SaisonWinterUnter"),
              *number("SaisonSommerUeber")]
    night = [heading(t["night"]), *tile("NachtabsenkungAktiv", FULL), *number("NachtabsenkungTemperatur"),
             *tile("NachtabsenkungStart", HALF), *tile("NachtabsenkungEnde", HALF)]
    runtime = [heading(t["runtime"]), *tile("KompressorStartsHeute", HALF), *tile("KompressorLaufzeitHeute", HALF),
               *tile("WarmwasserKompressorLaufzeitHeute", HALF), *tile("HeizstabLaufzeitHeute", HALF)]
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
    settings = [{"type": "grid", "cards": cards} for cards in (store, cooling, boost, season, night, schedule, runtime, diagnostics)
                if len(cards) > 1]

    def view(title: str, path: str, icon: str, sections: list[dict]) -> list[dict]:
        sections = [s for s in sections if s["cards"]]
        return [{"title": title, "path": path, "icon": icon, "type": "sections", "max_columns": 3, "sections": sections}] if sections else []

    return {"views": [
        *view(t["home"], "proxon", "mdi:home-thermometer-outline", home),
        *view(t["house"], "proxon-house", "mdi:floor-plan", house),
        *view(t["tank"], "proxon-hot-water", "mdi:water-boiler", hot_water),
        *view(t["settings"], "proxon-settings", "mdi:tune", settings),
    ]}
