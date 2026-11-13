"""Ready-made dashboard: built from the entities this unit really has (with their real entity IDs), to paste as it is.

Five tabs, built-in cards only, in the "Proxon Glas" look (frosted glass on a dark gradient; theme installed by an action,
without it the tabs keep the normal look):
* Home - on a tablet or computer (from 1024 px wide) like a control panel: outdoor and air temperatures, power and heat
  recovery on the left, the floor plan from above in the middle (every room with temperature, target and a flame while its
  heating element heats; tap: its thermostat), the T300 on the right, the functions below. On a phone: your own house photo
  with the key values on it (without a photo the floor plan), every room as a card with its temperature curve, ventilation,
  hot water and the functions with what they are doing ("On · Waiting").
* House - the house drawn isometric (both floors, ducts, heating elements) and the unit, heating elements, the unit's values.
* Hot water - the T300 cut open, its controls, the temperatures of the last 24 hours, its switches.
* Energy - consumption (and cost, with a price sensor) today / this week / month / year, per day and month, power of the
  last day, runtimes and compressor starts per day.
* Settings - limits with +/- buttons, weekly schedule, runtimes, diagnostics.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_HOUSE_PHOTO
from .entity import house_rooms, room_floors, room_name
from .pictures import (
    PLAN_H,
    PLAN_W,
    TANK_H,
    TANK_W,
    UNIT_H,
    UNIT_W,
    house_layout,
    house_targets,
    plan_targets,
    tank_targets,
    unit_targets,
)
from .theme import THEME_NAME

TEXT: dict[str, dict[str, Any]] = {
    "de": {
        "home": "Zuhause", "settings": "Einstellungen", "unit": "Anlage", "tank": "Warmwasser", "house": "Haus",
        "rooms": "Räume", "floors": ["Erdgeschoss", "Obergeschoss"], "now": "Gerade", "elements": "Wärmeelemente",
        "last_day": "Letzte 24 Stunden", "switches": "Schalter", "pills": {"T3Frischluft": "Außen ", "RaumMittel": "Innen ",
                                                                          "WarmwasserIstTemperatur": "Warmwasser "},
        "outside": "Außen", "power_today": "Strom heute",
        "air": {"T1Zuluft": "Zuluft", "T7Abluft": "Abluft", "T4Fortluft": "Fortluft"},
        "badges": {"IstLuefterstufe": "Lüftungsstufe", "Antwortzeit_path": "Verbindung", "Stoerung": "Störung"},
        "functions": "Funktionen", "store": "Warmwasser-Speicher (Solar / Strompreis)", "cooling": "Sommer-Nachtkühlung",
        "boost": "Warmwasser-Boost", "schedule": "Wochenprogramm Lüftung", "diagnostics": "Diagnose",
        "season": "Sommer/Winter-Automatik", "night": "Nachtabsenkung", "runtime": "Laufzeit heute",
        "energy": "Energie", "consumption": "Verbrauch", "periods": {"day": "Heute", "week": "Diese Woche", "month": "Dieser Monat",
                                                                     "year": "Dieses Jahr"},
        "cost": "Kosten", "per_day": "Verbrauch pro Tag (30 Tage)", "per_month": "Verbrauch pro Monat", "power_day": "Leistung, letzte 24 Stunden",
        "cost_per_day": "Kosten pro Tag (30 Tage)", "runtime_days": "Laufzeit pro Tag (14 Tage)", "starts_days": "Kompressor-Starts pro Tag",
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
            "WarmwasserIstTemperatur": "Warmwasser Mitte", "WarmwasserUntenTemperatur": "Warmwasser unten", "FilterRestStunden": "Filter",
            "T300Betriebsart": "Wärmepumpe Warmwasser", "E-Heizstab": "Heizstab freigegeben",
            "WarmwasserDuschminuten": "Duschvorrat", "LegionellenSonne": "Legionellenschutz mit Sonne", "LegionellenStatus": "Status",
            "EnergieKompressor": "Kompressor", "EnergieLueftung": "Lüftung und Elektronik", "LeistungKompressor": "Kompressor", "LeistungLueftung": "Lüftung und Elektronik",
            "Stromkosten": "Kosten", "WarmwasserKompressorStartsHeute": "Warmwasser-Kompressor",
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
        "outside": "Outdoor", "power_today": "Power today",
        "air": {"T1Zuluft": "Supply air", "T7Abluft": "Extract air", "T4Fortluft": "Exhaust air"},
        "badges": {"IstLuefterstufe": "Ventilation level", "Antwortzeit_path": "Connection", "Stoerung": "Fault"},
        "functions": "Functions", "store": "Hot-water store (solar / price)", "cooling": "Summer night cooling",
        "boost": "Hot-water boost", "schedule": "Weekly ventilation schedule", "diagnostics": "Diagnostics",
        "season": "Summer/winter automatic", "night": "Night setback", "runtime": "Runtime today",
        "energy": "Energy", "consumption": "Consumption", "periods": {"day": "Today", "week": "This week", "month": "This month",
                                                                       "year": "This year"},
        "cost": "Cost", "per_day": "Consumption per day (30 days)", "per_month": "Consumption per month", "power_day": "Power, last 24 hours",
        "cost_per_day": "Cost per day (30 days)", "runtime_days": "Runtime per day (14 days)", "starts_days": "Compressor starts per day",
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
            "WarmwasserIstTemperatur": "Hot water middle", "WarmwasserUntenTemperatur": "Hot water bottom", "FilterRestStunden": "Filter",
            "T300Betriebsart": "Hot-water heat pump", "E-Heizstab": "Immersion heater released",
            "WarmwasserDuschminuten": "Shower supply", "LegionellenSonne": "Legionella protection with solar", "LegionellenStatus": "Status",
            "EnergieKompressor": "Compressor", "EnergieLueftung": "Ventilation and electronics", "LeistungKompressor": "Compressor", "LeistungLueftung": "Ventilation and electronics",
            "Stromkosten": "Cost", "WarmwasserKompressorStartsHeute": "Hot-water compressor",
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
WITH_STATUS = ("SolarWarmwasser", "PreisWarmwasser", "Nachtkuehlung", "WarmwasserBoost", "SaisonAutomatik", "LegionellenSonne")
FUNCTIONS = ("SolarWarmwasser", "PreisWarmwasser", "Nachtkuehlung", "WarmwasserBoost", "SaisonAutomatik", "Urlaubsmodus", "Intensivlueftung")
# the start page: a control panel on wide screens (tablet, computer), photo and room cards on narrow ones (phone)
WIDE = [{"condition": "screen", "media_query": "(min-width: 1024px)"}]
NARROW = [{"condition": "screen", "media_query": "(max-width: 1023px)"}]
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

    def function_tiles(grid: dict = FULL, **layout) -> list[dict]:
        cards: list[dict] = []
        for key in FUNCTIONS:
            extra: dict = {"state_content": ["state", "status"]} if key in WITH_STATUS else {}
            if key == "Urlaubsmodus":
                extra["icon_tap_action"] = {"action": "toggle", "confirmation": {"text": t["holiday_confirm"]}}
            cards += tile(key, grid, **extra, **layout)
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
    names_now = [room_name(i, data) for i in rooms]
    plan_areas = [
        _area(ids[f"NBE{i}Thermostat"], target, (PLAN_W, PLAN_H))
        for i, target in zip(rooms, plan_targets(names_now, floors)) if f"NBE{i}Thermostat" in ids
    ]
    plan_picture = picture("BildGrundriss", plan_areas)

    # ---- home on a tablet / computer: values left, floor plan in the middle, hot water right, functions below ----
    air_rows = [{"entity": ids[k], "name": name} for k, name in t["air"].items() if k in ids]
    left: list[dict] = []
    if "T3Frischluft" in ids:
        left.append({"type": "sensor", "entity": ids["T3Frischluft"], "name": t["outside"], "graph": "line", "hours_to_show": 24,
                     "detail": 1, "grid_options": FULL})
    if air_rows:
        left.append({"type": "entities", "entities": air_rows, "grid_options": FULL})
    if "EnergieGesamt" in ids:
        left.append({"type": "statistic", "entity": ids["EnergieGesamt"], "name": t["power_today"], "stat_type": "change",
                     "period": {"calendar": {"period": "day"}}, "grid_options": HALF})
    left += [*tile("LeistungGesamt", HALF), *tile("Waermerueckgewinnung", HALF), *tile("FilterRestStunden", HALF)]
    right = [*tank_picture, *tile("Warmwasser", FULL, features=[{"type": "target-temperature"}])]
    panel_functions = function_tiles({"columns": 8}, vertical=True)

    # ---- home on a phone: photo (or the floor plan), rooms, what's going on ----
    photo = entry.options.get(CONF_HOUSE_PHOTO)
    if photo:
        pills = []
        shown = [k for k in ("T3Frischluft", "RaumMittel", "WarmwasserIstTemperatur", "AktuellerBetrieb") if k in ids]  # by column
        for (left_at, bottom), value in zip(PILL_SPOTS, shown):
            pill: dict = {"type": "state-label", "entity": ids[value], "style": {"left": left_at, "bottom": bottom, **PILL_STYLE}}
            if value in t["pills"]:
                pill["prefix"] = t["pills"][value]
            if value == "WarmwasserIstTemperatur" and "Warmwasser" in ids:
                pill["tap_action"] = {"action": "more-info", "entity": ids["Warmwasser"]}
            pills.append(pill)
        hero = [{"type": "picture-elements", "image": photo, "dark_mode_filter": "brightness(0.85)", "elements": pills, "grid_options": FULL}]
    else:
        hero = plan_picture
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
        *tile("Warmwasser", HALF), *tile("WarmwasserDuschminuten", HALF),
        *tile("Stoerung", HALF), *tile("FilterRestStunden_warning", HALF),
    ]
    # four columns (computer): values | floor plan (two wide) | T300, then functions | rooms; three (tablet): values | plan,
    # then T300 | functions, then rooms; two: values | T300, then the plan, functions, rooms (sections fill the gaps)
    home: list[dict[str, Any]] = [
        {"type": "grid", "cards": left, "visibility": WIDE},
        {"type": "grid", "column_span": 2, "cards": plan_picture, "visibility": WIDE},
        {"type": "grid", "cards": right, "visibility": WIDE},
        {"type": "grid", "column_span": 2, "cards": panel_functions, "visibility": WIDE},
        {"type": "grid", "column_span": 2, "cards": room_cards, "visibility": WIDE},
        {"type": "grid", "cards": [*hero, *room_cards], "visibility": NARROW},
        {"type": "grid", "cards": [*(now if len(now) > 1 else []), *function_tiles()], "visibility": NARROW},
    ]
    # at the top: operating mode, ventilation level, connection, fault
    badges = []
    for key in ("Betriebsart", "IstLuefterstufe", "Antwortzeit_path", "Stoerung"):
        if key in ids:
            badge: dict = {"type": "entity", "entity": ids[key], "show_state": True, "show_icon": True, "show_name": key in t["badges"]}
            if key in t["badges"]:
                badge["name"] = t["badges"][key]
            badges.append(badge)

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
        *tile("WarmwasserLadezustand", HALF), *tile("WarmwasserDuschminuten", HALF),
        *([heading(t["last_day"], "subtitle"), {"type": "history-graph", "entities": curve, "hours_to_show": 24, "grid_options": FULL}]
          if curve else []),
    ]
    switches = [*tile("T300Betriebsart", FULL), *tile("E-Heizstab", FULL), *tile("Legionellenfunktion", FULL),
                *tile("SolarWarmwasser", FULL, state_content=["state", "status"]), *tile("PreisWarmwasser", FULL, state_content=["state", "status"]),
                *tile("WarmwasserBoost", FULL, state_content=["state", "status"]),
                *tile("LegionellenSonne", FULL, state_content=["state", "status"]), *number("SollWassertemperatur"),
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
             *tile("LegionellenSonne", FULL, state_content=["state", "status"]), *number("IntensivlueftungsDauer")]
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

    # ---- energy: consumption and cost by day / week / month / year, per day and month, power, runtimes ----
    def statistic(key: str, name: str, period: str) -> list[dict]:
        if key not in ids:
            return []
        return [{"type": "statistic", "entity": ids[key], "name": name, "stat_type": "change",
                 "period": {"calendar": {"period": period}}, "grid_options": HALF}]

    def bars(title: str, keys: list[str], stat: str, period: str, days: int) -> list[dict]:
        shown = [{"entity": ids[k], "name": names.get(k, k)} for k in keys if k in ids]
        if not shown:
            return []
        return [heading(title, "subtitle"), {"type": "statistics-graph", "entities": shown, "stat_types": [stat], "period": period,
                                              "days_to_show": days, "chart_type": "bar", "hide_legend": len(shown) == 1,
                                              "grid_options": FULL}]

    p = t["periods"]
    totals = [heading(t["consumption"]), *[c for period in ("day", "week", "month", "year") for c in statistic("EnergieGesamt", p[period], period)]]
    if "Stromkosten" in ids:
        totals += [heading(t["cost"]), *statistic("Stromkosten", p["day"], "day"), *statistic("Stromkosten", p["month"], "month")]
    power_rows = [{"entity": ids[k], "name": names[k]} for k in ("LeistungGesamt", "LeistungKompressor", "LeistungLueftung") if k in ids]
    # left: totals, power and runtimes one below the other; right (two wide): consumption and cost per day and month
    energy_view: list[dict[str, Any]] = [
        {"type": "grid", "cards": [
            *(totals if len(totals) > 1 else []),
            *([heading(t["power_day"], "subtitle"), {"type": "history-graph", "entities": power_rows, "hours_to_show": 24,
                                                      "grid_options": FULL}] if power_rows else []),
            *bars(t["runtime_days"], ["KompressorLaufzeitHeute", "WarmwasserKompressorLaufzeitHeute", "HeizstabLaufzeitHeute"], "change", "day", 14),
            *bars(t["starts_days"], ["KompressorStartsHeute", "WarmwasserKompressorStartsHeute"], "change", "day", 14),
        ]},
        {"type": "grid", "column_span": 2, "cards": [
            *bars(t["per_day"], ["EnergieGesamt", "EnergieKompressor", "EnergieLueftung"], "change", "day", 30),
            *bars(t["cost_per_day"], ["Stromkosten"], "change", "day", 30),
            *bars(t["per_month"], ["EnergieGesamt"], "change", "month", 365),
        ]},
    ]

    def view(title: str, path: str, icon: str, sections: list[dict], columns: int = 3, **extra) -> list[dict]:
        sections = [s for s in sections if s["cards"]]
        if not sections:
            return []
        return [{"title": title, "path": path, "icon": icon, "type": "sections", "max_columns": columns, "theme": THEME_NAME,
                 **extra, "sections": sections}]

    return {"views": [
        *view(t["home"], "proxon", "mdi:home-thermometer-outline", home, 4, dense_section_placement=True,
              **({"badges": badges} if badges else {})),
        *view(t["house"], "proxon-house", "mdi:floor-plan", house),
        *view(t["tank"], "proxon-hot-water", "mdi:water-boiler", hot_water),
        *view(t["energy"], "proxon-energy", "mdi:lightning-bolt-outline", energy_view),
        *view(t["settings"], "proxon-settings", "mdi:tune", settings),
    ]}
