"""Ready-made dashboard: built from the entities this unit really has (with their real entity IDs), to paste as it is.

Five tabs, built-in cards only, in the "Proxon Glas" look (frosted glass on a dark gradient; theme installed by an action,
without it the tabs keep the normal look), one for each thing to do:
* Home - operate the ventilation (level, operating mode, boost, holiday), the house as a floor plan from above and drawn
  isometric (tap a room: its thermostat), the key temperatures, the unit, hot water in short, and every room with its target
  (+/-) and the temperature of the last day. On a phone your own house photo (or the floor plan) comes first.
* Hot water - the T300 cut open, everything to set, the last day, what the automatic functions are doing.
* Optimisation - every automatic function (solar / cheap power, boost, legionella, night cooling, summer/winter, night
  setback) with its switch, what it is doing and its limits.
* Power - consumption (and cost, with a price sensor) today / this week / month / year, split into compressor and
  ventilation, per day and month, power of the last day, runtimes and compressor starts per day.
* Settings - ventilation limits, weekly schedule, heating elements, the unit's values, runtimes, diagnostics.
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
        "rooms": "Räume", "floors": ["Erdgeschoss", "Obergeschoss"], "now": "Jetzt", "whole": "Gesamt", "elements": "Wärmeelemente",
        "last_day": "Letzte 24 Stunden", "switches": "Schalter", "pills": {"T3Frischluft": "Außen ", "RaumMittel": "Innen ",
                                                                          "WarmwasserIstTemperatur": "Warmwasser "},
        "outside": "Außen", "power_today": "Strom heute",
        "air": {"T1Zuluft": "Zuluft", "T7Abluft": "Abluft", "T4Fortluft": "Fortluft"},
        "badges": {"IstLuefterstufe": "Lüftungsstufe", "Antwortzeit_path": "Verbindung", "Stoerung": "Störung"},
        "functions": "Funktionen", "store": "Warmwasser-Speicher (Solar / Strompreis)", "cooling": "Sommer-Nachtkühlung",
        "boost": "Warmwasser-Boost", "schedule": "Wochenprogramm Lüftung", "diagnostics": "Diagnose",
        "season": "Sommer/Winter-Automatik", "night": "Nachtabsenkung", "runtime": "Laufzeit heute",
        "energy": "Strom", "consumption": "Verbrauch", "ventilation": "Lüftung", "temperatures": "Temperaturen", "inside": "Innen (Mittel)",
        "optimize": "Optimierung", "automatic": "Automatik", "legionella": "Legionellenschutz mit Sonne", "last_day_short": "24 h",
        "split": "Aufteilung", "forecast": "Hochrechnung", "auto_names": {"Energiemanager": "Solar / günstiger Strom", "BoostStatus": "Warmwasser-Boost",
                                              "LegionellenStatus": "Legionellenschutz"}, "periods": {"day": "Heute", "week": "Diese Woche", "month": "Dieser Monat",
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
            "LeistungGesamt": "Leistung jetzt", "EnergieGesamt": "Verbrauch",
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
            "GrenzwertFeuchte": "Grenzwert Feuchte", "GrenzwertCO2": "Grenzwert CO₂",
            "EnergieGesamtMonatPrognose": "Verbrauch Monat", "StromkostenMonatPrognose": "Kosten Monat",
            "EnergieGesamtJahrPrognose": "Verbrauch Jahr", "StromkostenJahrPrognose": "Kosten Jahr",
        },
        "holiday_confirm": "Urlaubsmodus umschalten? Das ändert Lüftung, Raumtemperaturen und Warmwasser.",
        "days": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], "schedule_on": "Programm aktiv",
        "diag": {"Antwortzeit": "Antwortzeit", "Antwortzeit_path": "Verbindungsweg", "Uhr": "Uhr der Anlage",
                 "FilterRestStunden": "Filter-Restlaufzeit", "FirmwareVersion": "Firmware", "Betriebsstundenzaehler": "Betriebsstunden",
                 "UhrAbweichung": "Uhrabweichung", "LetzterSchreibfehler": "Letzter Schreibfehler", "FirmwareT300": "Firmware Warmwasser"},
    },
    "en": {
        "home": "Home", "settings": "Settings", "unit": "Unit", "tank": "Hot water", "house": "House",
        "rooms": "Rooms", "floors": ["Ground floor", "Upper floor"], "now": "Right now", "whole": "Total", "elements": "Heating elements",
        "last_day": "Last 24 hours", "switches": "Switches", "pills": {"T3Frischluft": "Outdoor ", "RaumMittel": "Indoor ",
                                                                       "WarmwasserIstTemperatur": "Hot water "},
        "outside": "Outdoor", "power_today": "Power today",
        "air": {"T1Zuluft": "Supply air", "T7Abluft": "Extract air", "T4Fortluft": "Exhaust air"},
        "badges": {"IstLuefterstufe": "Ventilation level", "Antwortzeit_path": "Connection", "Stoerung": "Fault"},
        "functions": "Functions", "store": "Hot-water store (solar / price)", "cooling": "Summer night cooling",
        "boost": "Hot-water boost", "schedule": "Weekly ventilation schedule", "diagnostics": "Diagnostics",
        "season": "Summer/winter automatic", "night": "Night setback", "runtime": "Runtime today",
        "energy": "Power", "consumption": "Consumption", "ventilation": "Ventilation", "temperatures": "Temperatures",
        "inside": "Indoor (average)", "optimize": "Optimisation", "automatic": "Automatic", "legionella": "Legionella protection with solar",
        "last_day_short": "24 h", "split": "Split", "forecast": "Forecast",
        "auto_names": {"Energiemanager": "Solar / cheap power", "BoostStatus": "Hot-water boost", "LegionellenStatus": "Legionella protection"},
        "periods": {"day": "Today", "week": "This week", "month": "This month",
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
            "LeistungGesamt": "Power now", "EnergieGesamt": "Consumption",
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
            "GrenzwertFeuchte": "Humidity limit", "GrenzwertCO2": "CO₂ limit",
            "EnergieGesamtMonatPrognose": "Consumption month", "StromkostenMonatPrognose": "Cost month",
            "EnergieGesamtJahrPrognose": "Consumption year", "StromkostenJahrPrognose": "Cost year",
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

    # ---- what several tabs use ----
    def go(path: str) -> dict:
        """Tapping opens another tab of this dashboard (a path relative to the one shown)."""
        return {"action": "navigate", "navigation_path": path}

    ventilation = [
        heading(t["ventilation"]),
        *tile("Lueftung", FULL, features=[{"type": "fan-speed"}], features_position="inline"),
        *tile("Betriebsart", FULL, features=[{"type": "select-options"}], features_position="inline"),
        *tile("Intensivlueftung", HALF),
        *tile("Urlaubsmodus", HALF, icon_tap_action={"action": "toggle", "confirmation": {"text": t["holiday_confirm"]}}),
    ]
    hot_water_short = [
        heading(t["tank"]),
        *tile("Warmwasser", HALF, tap_action=go("proxon-hot-water")),
        *tile("WarmwasserDuschminuten", HALF, tap_action=go("proxon-hot-water")),
    ]
    air_rows = [{"entity": ids[k], "name": name} for k, name in t["air"].items() if k in ids]
    if "RaumMittel" in ids:
        air_rows.insert(0, {"entity": ids["RaumMittel"], "name": t["inside"]})
    temperatures: list[dict] = [heading(t["temperatures"])]
    if "T3Frischluft" in ids:
        temperatures.append({"type": "sensor", "entity": ids["T3Frischluft"], "name": t["outside"], "graph": "line",
                             "hours_to_show": 24, "detail": 1, "grid_options": FULL})
    if air_rows:
        temperatures.append({"type": "entities", "entities": air_rows, "grid_options": FULL})
    # the power right now (tap: the power tab)
    temperatures += tile("LeistungGesamt", FULL, features=[{"type": "trend-graph", "hours_to_show": 1}], features_position="inline",
                         tap_action=go("proxon-energy"))

    # every room: target with +/- right on the card, below it the temperature of the last day (tap: the thermostat)
    def room_card(i: int, grid: dict) -> list[dict]:
        thermostat, sensor = ids.get(f"NBE{i}Thermostat"), ids.get(f"NBE{i}Temperatur")
        if not thermostat:
            return []
        cards: list[dict] = [{"type": "tile", "entity": thermostat, "name": room_name(i, data),
                              "state_content": ["current_temperature", "hvac_action"], "features": [{"type": "target-temperature"}]}]
        if sensor:
            # one flat row: "24 h" with the curve right next to it
            cards.append({"type": "tile", "entity": sensor, "name": t["last_day_short"], "hide_state": True,
                          "features": [{"type": "trend-graph", "hours_to_show": 24}], "features_position": "inline",
                          "tap_action": {"action": "more-info", "entity": thermostat}})
        return [{"type": "vertical-stack", "cards": cards, "grid_options": grid}]

    def room_cards(grid: dict) -> list[dict]:
        out: list[dict] = []
        for floor in (0, 1):
            cards = [c for i, f in zip(rooms, floors) if f == floor for c in room_card(i, grid)]
            if cards:
                title = t["floors"][floor] if any(floors) else t["rooms"]
                out += [heading(title, "subtitle" if any(floors) else "title"), *cards]
        return out

    # ---- 1. home: operate the ventilation, the house (floor plan and drawn), temperatures, the unit, hot water, rooms ----
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
    # four columns (computer): ventilation, hot water and the rooms | house and unit (two wide) | temperatures; fewer
    # columns: the sections fill the gaps. A phone gets the photo (or the floor plan) first.
    home: list[dict[str, Any]] = [
        {"type": "grid", "cards": [*ventilation, *hot_water_short, *room_cards(FULL)], "visibility": WIDE},
        {"type": "grid", "column_span": 2, "cards": [*plan_picture, *house_picture, *unit_picture], "visibility": WIDE},
        {"type": "grid", "cards": temperatures, "visibility": WIDE},
        {"type": "grid", "cards": [*hero, *ventilation], "visibility": NARROW},
        {"type": "grid", "cards": room_cards(HALF), "visibility": NARROW},
        {"type": "grid", "cards": [*hot_water_short, *temperatures, *house_picture, *(plan_picture if photo else []), *unit_picture],
         "visibility": NARROW},
    ]
    # at the top: operating mode, ventilation level, connection, fault
    badges = []
    for key in ("Betriebsart", "IstLuefterstufe", "Antwortzeit_path", "Stoerung"):
        if key in ids:
            badge: dict = {"type": "entity", "entity": ids[key], "show_state": True, "show_icon": True, "show_name": key in t["badges"]}
            if key in t["badges"]:
                badge["name"] = t["badges"][key]
            badges.append(badge)

    # ---- 2. hot water: the T300 cut open, everything to set, what the automatic functions are doing ----
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
    water_settings = [heading(t["settings"]), *number("SollWassertemperatur"), *tile("T300Betriebsart", FULL), *tile("E-Heizstab", FULL),
                      *number("Soll-E-Heizstab-Temperatur"), *tile("Legionellenfunktion", FULL)]
    # the automatic functions for hot water: only what they are doing; tapping opens them in the optimisation tab
    water_auto = [c for key in ("Energiemanager", "BoostStatus", "LegionellenStatus")
                  for c in tile(key, FULL, name=t["auto_names"][key], tap_action=go("proxon-optimize"))]
    hot_water: list[dict[str, Any]] = [
        {"type": "grid", "cards": tank_picture},
        {"type": "grid", "cards": water},
        {"type": "grid", "cards": [*water_settings, *([heading(t["automatic"]), *water_auto] if water_auto else [])]
         if len(water_settings) > 1 or water_auto else []},
    ]

    # ---- 3. optimisation: every automatic function with its switch, what it is doing, and its limits ----
    def block(title: str, switches: list[str], numbers: list[str], more: list[dict] | None = None) -> list[dict]:
        cards = [c for key in switches for c in tile(key, FULL, state_content=["state", "status"] if key in WITH_STATUS else ["state"])]
        if not cards:
            return []
        return [heading(title), *cards, *[c for key in numbers for c in number(key)], *(more or [])]

    optimize = [
        block(t["store"], ["SolarWarmwasser", "PreisWarmwasser"], ["SolarSchwelle", "PreisSchwelle", "SpeicherTemperatur"]),
        block(t["boost"], ["WarmwasserBoost"], ["BoostGrenze", "Soll-E-Heizstab-Temperatur"]),
        block(t["legionella"], ["LegionellenSonne"], [], tile("LegionellenStatus", FULL, name=names["LegionellenStatus"])),
        block(t["cooling"], ["Nachtkuehlung"], ["KuehlWunsch", "KuehlStufe"]),
        block(t["season"], ["SaisonAutomatik"], ["SaisonWinterUnter", "SaisonSommerUeber"]),
        block(t["night"], ["NachtabsenkungAktiv"], ["NachtabsenkungTemperatur"],
              [*tile("NachtabsenkungStart", HALF), *tile("NachtabsenkungEnde", HALF)]),
    ]
    optimize_view = [{"type": "grid", "cards": cards} for cards in optimize if cards]

    # ---- 4. power: consumption and cost by day / week / month / year, split, per day and month, power, runtimes ----
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
    # right now: the whole unit with the last hour, compressor and ventilation with electronics
    now_power = [*tile("LeistungGesamt", FULL, features=[{"type": "trend-graph", "hours_to_show": 1}]),
                 *tile("LeistungKompressor", HALF), *tile("LeistungLueftung", HALF)]
    totals = [*([heading(t["now"]), *now_power] if now_power else []), heading(t["consumption"]),
              *[c for period in ("day", "week", "month", "year") for c in statistic("EnergieGesamt", p[period], period)]]
    if "Stromkosten" in ids:
        totals += [heading(t["cost"]), *[c for period in ("day", "week", "month", "year") for c in statistic("Stromkosten", p[period], period)]]
    # what this month and year will probably come to
    forecast = [c for key in ("EnergieGesamtMonatPrognose", "StromkostenMonatPrognose", "EnergieGesamtJahrPrognose", "StromkostenJahrPrognose")
                for c in tile(key, HALF)]
    if forecast:
        totals += [heading(t["forecast"]), *forecast]
    # compressor (heating / cooling) and ventilation with electronics: today / this week / this month / this year
    split: list[dict] = []
    for key in ("EnergieKompressor", "EnergieLueftung"):
        rows = [{"entity": ids[f"{key}{suffix}"], "name": p[period]}
                for suffix, period in (("Heute", "day"), ("Woche", "week"), ("Monat", "month"), ("Jahr", "year")) if f"{key}{suffix}" in ids]
        if rows:
            split.append({"type": "entities", "title": names[key], "entities": rows, "grid_options": FULL})
    power_rows = [{"entity": ids[k], "name": t["whole"] if k == "LeistungGesamt" else names[k]}
                  for k in ("LeistungGesamt", "LeistungKompressor", "LeistungLueftung") if k in ids]
    # left: totals, split, power and runtimes one below the other; right (two wide): consumption and cost per day and month
    energy_view: list[dict[str, Any]] = [
        {"type": "grid", "cards": [
            *(totals if len(totals) > 1 else []),
            *([heading(t["split"]), *split] if split else []),
            *([heading(t["power_day"], "subtitle"), {"type": "history-graph", "entities": power_rows, "hours_to_show": 24,
                                                      "grid_options": FULL}] if power_rows else []),
        ]},
        {"type": "grid", "column_span": 2, "cards": [
            *bars(t["per_day"], ["EnergieGesamt", "EnergieKompressor", "EnergieLueftung"], "change", "day", 30),
            *bars(t["cost_per_day"], ["Stromkosten"], "change", "day", 30),
            *bars(t["per_month"], ["EnergieGesamt"], "change", "month", 365),
            *bars(t["runtime_days"], ["KompressorLaufzeitHeute", "WarmwasserKompressorLaufzeitHeute", "HeizstabLaufzeitHeute"], "change", "day", 14),
            *bars(t["starts_days"], ["KompressorStartsHeute", "WarmwasserKompressorStartsHeute"], "change", "day", 14),
        ]},
    ]

    # ---- 5. settings: ventilation limits, weekly schedule, heating elements, the unit, runtimes, diagnostics ----
    limits = [heading(t["ventilation"]), *number("IntensivlueftungsDauer"), *number("GrenzwertCO2"), *number("GrenzwertFeuchte")]
    elements = [{"entity": ids[f"NBE{i}Waermeelement"], "name": room_name(i, data)} for i in rooms if f"NBE{i}Waermeelement" in ids]
    heating = [heading(t["elements"]), {"type": "entities", "entities": elements, "grid_options": FULL}] if elements else []
    unit = [heading(t["unit"]), *tile("AktuellerBetrieb", HALF), *tile("Waermerueckgewinnung", HALF),
            *tile("LeistungGesamt", HALF), *tile("FilterRestStunden", HALF),
            *tile("Stoerung", HALF), *tile("FilterRestStunden_warning", HALF)]
    runtime = [heading(t["runtime"]), *tile("KompressorStartsHeute", HALF), *tile("KompressorLaufzeitHeute", HALF),
               *tile("WarmwasserKompressorLaufzeitHeute", HALF), *tile("HeizstabLaufzeitHeute", HALF)]
    schedule_keys = [("ZeitprogrammAktiv", t["schedule_on"]), *[(f"Zeitprogramm{d}", t["days"][d]) for d in range(7)]]
    schedule_rows = [{"entity": ids[k], "name": name} for k, name in schedule_keys if k in ids]
    schedule = [heading(t["schedule"]), {"type": "entities", "entities": schedule_rows, "grid_options": FULL}] if schedule_rows else []
    if schedule:  # copy Monday with one tap (asks first: it changes several days)
        for key in ("ZeitprogrammMoDiFr", "ZeitprogrammMoAlle"):
            schedule += tile(key, HALF, icon_tap_action={"action": "perform-action", "perform_action": "button.press",
                                                          "target": {"entity_id": ids.get(key)}, "confirmation": True},
                             tap_action={"action": "perform-action", "perform_action": "button.press",
                                         "target": {"entity_id": ids.get(key)}, "confirmation": True})
    diag_rows = [{"entity": ids[k], "name": name} for k, name in t["diag"].items() if k in ids]
    diagnostics = [heading(t["diagnostics"]), {"type": "entities", "entities": diag_rows, "grid_options": FULL}] if diag_rows else []
    settings = [{"type": "grid", "cards": cards} for cards in (limits, schedule, heating, unit, runtime, diagnostics) if len(cards) > 1]

    def view(title: str, path: str, icon: str, sections: list[dict], columns: int = 3, **extra) -> list[dict]:
        sections = [s for s in sections if s["cards"]]
        if not sections:
            return []
        return [{"title": title, "path": path, "icon": icon, "type": "sections", "max_columns": columns, "theme": THEME_NAME,
                 **extra, "sections": sections}]

    return {"views": [
        *view(t["home"], "proxon", "mdi:home-thermometer-outline", home, 4, dense_section_placement=True,
              **({"badges": badges} if badges else {})),
        *view(t["tank"], "proxon-hot-water", "mdi:water-boiler", hot_water),
        *view(t["optimize"], "proxon-optimize", "mdi:leaf", optimize_view),
        *view(t["energy"], "proxon-energy", "mdi:lightning-bolt-outline", energy_view),
        *view(t["settings"], "proxon-settings", "mdi:tune", settings),
    ]}
