"""Dashboard pictures (unit, hot water, house) and the ready-made dashboard."""
from __future__ import annotations

import time
from unittest.mock import patch
import xml.dom.minidom

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util.yaml import dump, parse_yaml

from custom_components.proxon_control import image as image_module
from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.pictures import (
    LABELS,
    PLAN_H,
    PLAN_W,
    Room,
    guess_floor,
    house_layout,
    house_svg,
    house_targets,
    plan_layout,
    plan_svg,
    plan_targets,
    room_kind,
    tank_svg,
    tank_targets,
    unit_svg,
    unit_targets,
)

from .test_integration import call, eid, make_entry, setup

DATA = {
    "Betriebsart": 3.0, "Luefterstufe": 1.0, "IstLuefterstufe": 2.0, "T3Frischluft": 7.6, "T1Zuluft": 19.7, "T7Abluft": 23.1,
    "T4Fortluft": 9.0, "DrehzahlKompressor": 0.0, "Kuehlbetrieb4Wegeventil": 0.0, "FilterRestStunden": 3244.0,
    "WarmwasserIstTemperatur": 41.1, "SollWassertemperatur": 46.0, "E-Heizstab": 0.0, "T300Betriebsart": 1.0, "Soll-E-Heizstab-Temperatur": 44.0,
}


def valid(svg: str) -> str:
    xml.dom.minidom.parseString(svg)  # well-formed
    return svg


# ---------------- pictures ----------------
def test_unit_picture_shows_the_values_and_turns_the_fans() -> None:
    svg = valid(unit_svg(DATA, "de"))
    for text in ("Außenluft", "7,6°", "Zuluft", "19,7°", "Abluft", "23,1°", "Fortluft", "9,0°", "ECO Komfort", "Stufe 2", "135 Tage"):
        assert text in svg, text
    assert 'class="spin" style="animation-duration:1.20s"' in svg  # level 2: one turn in 1.2 s
    assert 'class="flow"' in svg  # air moving
    off = valid(unit_svg({**DATA, "Betriebsart": 0.0}, "de"))
    assert 'class="spin"' not in off and 'class="flow"' not in off  # unit off: nothing moves


def test_unit_picture_heat_pump_and_chips() -> None:
    svg = valid(unit_svg({**DATA, "DrehzahlKompressor": 4010.0}, "en"))
    assert "Heating" in svg and "4010 rpm" in svg and "animation-duration:0.60s" in svg
    assert "Cooling" in valid(unit_svg({**DATA, "DrehzahlKompressor": 4010.0, "Kuehlbetrieb4Wegeventil": 1.0}, "en"))
    chips = valid(unit_svg({**DATA, "Intensivlueftung": 1.0}, "de", cooling_status="cooling", fault=True))
    assert "Nachtkühlung: kühlt" in chips and "Intensivlüftung" in chips and "Störung" in chips
    assert "Nachtkühlung" not in valid(unit_svg(DATA, "de"))  # only when switched on


def test_tank_picture() -> None:
    svg = valid(tank_svg(DATA, "de", 40, energy_status="waiting", boost_status="off"))
    assert ">46°<" in svg and "41,1°" in svg and "Heizstab aus" in svg and "Heizstab-Soll" in svg and "44°" in svg
    assert "Solar: wartet" in svg and "Boost: aus (&lt; 40°)" in svg
    assert 'class="glow"' not in svg
    on = valid(tank_svg({**DATA, "E-Heizstab": 1.0}, "de", energy_status="heating_price"))
    assert 'class="glow"' in on and "Heizstab an" in on and "Günstiger Strom: heizt" in on
    assert "Solar" not in valid(tank_svg(DATA, "de"))  # no chips while the functions are off


def test_pictures_follow_light_and_dark() -> None:
    auto = unit_svg(DATA, "de")
    assert "prefers-color-scheme:dark" in auto and "--fg:#1f2933" in auto and "--fg:#e6eaee" in auto
    dark = unit_svg(DATA, "de", "dark")
    assert "prefers-color-scheme" not in dark and "--fg:#e6eaee" in dark and "--fg:#1f2933" not in dark
    light = house_svg([Room("A", 21.0, 21.0, False)], 5.0, "de", "light")
    assert "prefers-color-scheme" not in light and "--fg:#1f2933" in light
    assert '<rect width="800"' not in auto and 'fill="#eef1f4"' not in auto  # transparent: no background, the card's colour shows


def test_tank_in_section() -> None:
    """The T300 cut open: the two sensors, the charge, the rod glows while its relay is on, the fan turns while the compressor runs."""
    data = {**DATA, "WarmwasserUntenTemperatur": 30.0, "WarmwasserLadezustand": 64.0, "T300RelaisKompressor": 1.0,
            "T300RelaisHeizstab": 0.0, "E-Heizstab": 1.0}
    svg = valid(tank_svg(data, "de"))
    assert "Mitte" in svg and "Unten" in svg and "30,0°" in svg and "Ladezustand 64 %" in svg
    assert "Wärmepumpe an" in svg and 'class="spin"' in svg
    assert "Heizstab an" in svg and 'class="glow"' not in svg  # released, but its relay is off: it doesn't heat
    heating = valid(tank_svg({**data, "T300RelaisHeizstab": 1.0}, "de"))
    assert 'class="glow"' in heating and "heizt" in heating
    plain = valid(tank_svg(DATA, "de"))  # no bottom sensor, no relays reported
    assert "Unten" not in plain and "Wärmepumpe" not in plain and 'class="spin"' not in plain


def test_house_picture_lays_out_any_number_of_rooms() -> None:
    rooms = [Room(f"Raum {i}", t, 22.0, i == 2) for i, t in enumerate((20.0, 21.5, 22.0, 22.5, 23.5, 24.0))]
    svg = valid(house_svg(rooms, 7.6, "de"))
    assert svg.count('class="flame"') == 1 and "Raum 5" in svg
    assert 'class="r-cold sep"' in svg and 'class="r-fine sep"' in svg and 'class="r-warm sep"' in svg  # too cold, fine, too warm
    assert "zu kalt" in svg and "antippen zum Einstellen" in svg and "Lüftungsanlage" in svg and "Innen 22,3°" in svg
    assert "Obergeschoss" not in svg  # one floor: no floor names
    big = valid(house_svg([Room(f"R{i}", 21.0, 21.0, False) for i in range(14)], None, "en"))
    assert "R13" in big
    assert valid(house_svg([Room("Küche & <Bad>", None, None, False)], None, "de"))  # names are escaped, missing values shown as –


def test_house_with_two_floors() -> None:
    rooms = [Room("Wohnen", 22.0, 22.0, False, 0), Room("Küche", 21.0, 21.0, False, 0), Room("Kind", 20.0, 22.0, True, 1)]
    svg = valid(house_svg(rooms, 5.0, "de"))
    assert "Erdgeschoss" in svg and "Obergeschoss" in svg and "Kind" in svg
    assert svg.count('class="flow"') >= 4  # supply air into every room, up to the upper floor, extract air back
    still = valid(house_svg(rooms, 5.0, "de", running=False))
    assert 'class="flow"' not in still  # ventilation off: the air stands still


def test_room_labels_never_overlap() -> None:
    """However many rooms on however many floors: the labels (also the tap areas) don't cover each other."""
    for n in range(1, 22):
        for upper in {0, n // 3, n // 2, n}:
            floors = [1 if i < upper else 0 for i in range(n)]
            lay = house_layout(floors)
            boxes = lay.labels
            assert len(boxes) == n
            for k, (x, y, w, h) in enumerate(boxes):
                assert 0 <= x and x + w <= lay.width and 0 <= y and y + h <= lay.height  # inside the picture
                for x2, y2, w2, h2 in boxes[k + 1:]:
                    assert x + w <= x2 or x2 + w2 <= x or y + h <= y2 or y2 + h2 <= y, (n, upper)
    assert house_layout([0, 0, 0]).style == LABELS[0][0]  # few rooms: the full labels with the target


def test_floor_guess() -> None:
    names = ("Schlafzimmer", "Kinderzimmer 2", "Bad oben", "Eltern", "Bedroom", "Wohnzimmer", "Küche", "Gäste-WC", "Bad", "Büro")
    assert [guess_floor(n) for n in names] == [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]


def test_tap_areas_match_the_drawing() -> None:
    floors = [0, 1, 0, 1, 1, 0]
    lay = house_layout(floors)
    svg = house_svg([Room(f"R{i}", 21.0, 21.0, False, f) for i, f in enumerate(floors)], None, "de")
    assert f'viewBox="0 0 {lay.width} {lay.height}"' in svg
    for (x, y, w, h), (cx, cy, pw, ph) in zip(lay.labels, house_targets(floors)):
        assert abs(cx / 100 * lay.width - (x + w / 2)) < 0.5 and abs(cy / 100 * lay.height - (y + h / 2)) < 0.5
        assert abs(pw / 100 * lay.width - w) < 0.5 and abs(ph / 100 * lay.height - h) < 0.5
        assert f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}"' in svg  # the label is drawn right there
    assert len(house_targets([0] * 14)) == 14
    assert unit_targets()["unit"][:2] == (50.0, 50.0)
    assert 0 < tank_targets()["tank"][0] < 100


def test_floor_plan() -> None:
    """The rooms from above: floors and furniture by kind, labels with target and flame, too cold / too warm marked."""
    rooms = [Room("Wohnen", 22.7, 23.0, False, 0), Room("Küche & Essen", 22.0, 22.0, False, 0), Room("Bad", 20.0, 22.5, True, 0),
             Room("Schlafen", 24.0, 22.0, False, 1), Room("Kind 1", None, None, False, 1)]
    svg = valid(plan_svg(rooms, "de"))
    assert f'viewBox="0 0 {PLAN_W} {PLAN_H}"' in svg
    assert "Küche &amp; Essen" in svg and "22,7°" in svg and "Soll 23°" in svg and "Soll 22,5°" in svg and "–" in svg
    assert svg.count('class="flame"') == 1  # the bath heats
    assert 'stroke="#4f97e8"' in svg and 'stroke="#f07a3a"' in svg  # the bath too cold, the bedroom too warm
    assert "url(#wood)" in svg and "url(#tile)" in svg and "Erdgeschoss" in svg and "Obergeschoss" in svg
    one_floor = valid(plan_svg([Room("Wohnen", 21.0, 21.0, False)], "en"))
    assert "Ground floor" not in one_floor  # one floor: no floor names
    assert valid(plan_svg([], "de"))


def test_room_kinds() -> None:
    kinds = [room_kind(n)[0] for n in ("Wohnzimmer", "Wohn-/Esszimmer", "Gäste-WC", "Gästebad", "Gästezimmer", "Bad oben", "Kind 2",
                                       "Schlafen", "Diele", "Arbeitszimmer", "Hauswirtschaft", "Küche", "Hobbyraum")]
    assert kinds == ["living", "living", "wc", "bath", "guest", "bath", "child", "bedroom", "hall", "office", "utility", "kitchen", "room"]


def test_floor_plan_rooms_and_labels() -> None:
    """Rooms fill the plan without overlapping, labels sit inside their room; tap areas are the rooms."""
    for n in range(1, 22):
        for upper in {0, n // 2}:
            names = [f"Raum {i}" for i in range(n)]
            floors = [1 if i < upper else 0 for i in range(n)]
            lay = plan_layout(names, floors)
            area = sum(w * h for _x, _y, w, h in lay.rooms)
            assert abs(area - (PLAN_W - 28) * (PLAN_H - 28)) < 2  # the rooms cover the plan
            for (x, y, w, h), (lx, ly, lw, lh), style in zip(lay.rooms, lay.labels, lay.styles):
                if style != "mini":
                    assert x < lx and lx + lw < x + w and y < ly and ly + lh < y + h, (n, upper)
            for k, (x, y, w, h) in enumerate(lay.rooms):
                for x2, y2, w2, h2 in lay.rooms[k + 1:]:
                    assert x + w <= x2 + 0.01 or x2 + w2 <= x + 0.01 or y + h <= y2 + 0.01 or y2 + h2 <= y + 0.01
    names, floors = ["Wohnen", "Bad", "Kind"], [0, 0, 1]
    lay = plan_layout(names, floors)
    for (x, y, w, h), (cx, cy, pw, ph) in zip(lay.rooms, plan_targets(names, floors)):
        assert abs(cx / 100 * PLAN_W - (x + w / 2)) < 0.5 and abs(cy / 100 * PLAN_H - (y + h / 2)) < 0.5
        assert abs(pw / 100 * PLAN_W - (w - 8)) < 0.5 and abs(ph / 100 * PLAN_H - (h - 8)) < 0.5


# ---------------- in Home Assistant ----------------
async def test_picture_entities(hass: HomeAssistant, device, hass_client) -> None:
    await setup(hass)
    client = await hass_client()
    # values of the simulated unit (the test system runs in English)
    for key, expected in (("BildAnlage", "Outdoor air"), ("BildWarmwasser", "36,0°"), ("BildHaus", "Schlafzimmer"),
                          ("BildGrundriss", "Wohnzimmer")):
        entity_id = eid(hass, "image", key)
        resp = await client.get(f"/api/image_proxy/{entity_id}")
        assert resp.status == 200 and resp.content_type == "image/svg+xml"
        body = await resp.text()
        valid(body)
        assert expected in body, key


async def test_pictures_reload_calmly(hass: HomeAssistant, device) -> None:
    """Changed temperatures are shown at most once a minute (a new picture restarts the animations); a switch right away."""
    entry = await setup(hass)
    entity_id = eid(hass, "image", "BildAnlage")
    coordinator = entry.runtime_data
    before = hass.states.get(entity_id).state
    coordinator.async_set_updated_data(dict(coordinator.data))  # same values
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == before
    coordinator.async_set_updated_data({**coordinator.data, "T3Frischluft": 3.5})  # only a temperature
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == before
    coordinator.async_set_updated_data({**coordinator.data, "Betriebsart": 2.0})  # something switched
    await hass.async_block_till_done()
    switched = hass.states.get(entity_id).state
    assert switched != before
    with patch.object(image_module.time, "monotonic", return_value=time.monotonic() + 61):
        coordinator.async_set_updated_data({**coordinator.data, "T3Frischluft": 2.0})  # a minute later
        await hass.async_block_till_done()
    assert hass.states.get(entity_id).state != switched


async def test_picture_theme_option(hass: HomeAssistant, device, hass_client) -> None:
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"picture_theme": "dark"})
    await setup(hass, entry)
    client = await hass_client()
    body = await (await client.get(f"/api/image_proxy/{eid(hass, 'image', 'BildHaus')}")).text()
    assert "--fg:#e6eaee" in body and "prefers-color-scheme" not in body


async def test_function_tiles_show_what_is_going_on(hass: HomeAssistant, device) -> None:
    await setup(hass)
    solar = eid(hass, "switch", "SolarWarmwasser")
    assert "status" not in hass.states.get(solar).attributes  # off: just "off"
    await call(hass, "switch", "turn_on", entity_id=solar)
    assert hass.states.get(solar).attributes["status"] == "no_source"  # on, but no surplus sensor chosen


async def test_status_is_right_from_the_start(hass: HomeAssistant, device, hass_storage) -> None:
    """Functions that were on before a restart show their status at once, not "off" until the next query."""
    entry = make_entry()
    hass_storage[f"{DOMAIN}.{entry.entry_id}.energy"] = {
        "version": 1, "key": f"{DOMAIN}.{entry.entry_id}.energy", "data": {"settings": {"solar_on": True}, "state": {}},
    }
    await setup(hass, entry)
    assert hass.states.get(eid(hass, "switch", "SolarWarmwasser")).attributes["status"] == "no_source"


async def test_create_dashboard_action(hass: HomeAssistant, device) -> None:
    await setup(hass)
    dashboard = await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    assert list(dashboard) == ["views"]  # the answer is the dashboard itself: paste it as it is
    assert parse_yaml(dump(dashboard)) == dashboard
    views = dashboard["views"]
    assert [v["path"] for v in views] == ["proxon", "proxon-house", "proxon-hot-water", "proxon-settings"]
    assert all(v["type"] == "sections" for v in views)
    home, house, water, settings = views

    def cards(view: dict) -> list[dict]:
        return [c for s in view["sections"] for c in s["cards"]]

    assert all(v["theme"] == "Proxon Glas" for v in views)  # the glass look (normal look until the theme is installed)
    pictures = {c["image_entity"]: c for v in views for c in cards(v) if c["type"] == "picture-elements"}
    assert set(pictures) == {eid(hass, "image", k) for k in ("BildAnlage", "BildWarmwasser", "BildHaus", "BildGrundriss")}
    # tapping: the unit opens the ventilation, the tank the hot water, every room its thermostat (house and floor plan)
    targets = {k: [e["entity"] for e in c["elements"]] for k, c in pictures.items()}
    assert targets[eid(hass, "image", "BildAnlage")] == [eid(hass, "fan", "Lueftung")]
    assert targets[eid(hass, "image", "BildWarmwasser")] == [eid(hass, "water_heater", "Warmwasser")]
    thermostats = [eid(hass, "climate", f"NBE{n}Thermostat") for n in (0, 1, 4)]
    assert targets[eid(hass, "image", "BildHaus")] == targets[eid(hass, "image", "BildGrundriss")] == thermostats
    assert all(e["type"] == "image" and e["tap_action"]["action"] == "more-info" for c in pictures.values() for e in c["elements"])
    # home on a tablet / computer: values left, floor plan in the middle (two columns), hot water right, functions below
    wide = [s for s in home["sections"] if s["visibility"] == [{"condition": "screen", "media_query": "(min-width: 1024px)"}]]
    narrow = [s for s in home["sections"] if s["visibility"] == [{"condition": "screen", "media_query": "(max-width: 1023px)"}]]
    assert len(wide) + len(narrow) == len(home["sections"])
    left, middle, right, below, rooms_wide = wide
    assert [c["type"] for c in left["cards"][:3]] == ["sensor", "entities", "statistic"]
    assert left["cards"][0]["entity"] == eid(hass, "sensor", "T3Frischluft")
    assert middle["column_span"] == 2 and middle["cards"][0]["image_entity"] == eid(hass, "image", "BildGrundriss")
    assert right["cards"][0]["image_entity"] == eid(hass, "image", "BildWarmwasser")
    assert below["column_span"] == 2 and all(c.get("vertical") is True for c in below["cards"] if c["type"] == "tile")
    assert home["dense_section_placement"] is True and home["max_columns"] == 4
    assert [c["entity"] for c in rooms_wide["cards"] if c["type"] == "tile"] == [eid(hass, "sensor", f"NBE{n}Temperatur") for n in (0, 4, 1)]
    assert [b["entity"] for b in home["badges"]] == [eid(hass, "select", "Betriebsart"), eid(hass, "sensor", "IstLuefterstufe"),
                                                    eid(hass, "sensor", "Antwortzeit_path"), eid(hass, "binary_sensor", "Stoerung")]
    # home on a phone: without a photo the floor plan leads, then every room with its curve - ground floor first
    phone = narrow[0]
    assert phone["cards"][0]["image_entity"] == eid(hass, "image", "BildGrundriss")
    rooms = [c for c in narrow[0]["cards"] if c.get("features") == [{"type": "trend-graph", "hours_to_show": 24}]]
    assert [c["tap_action"]["entity"] for c in rooms] == [eid(hass, "climate", f"NBE{n}Thermostat") for n in (0, 4, 1)]
    assert [c["name"] for c in rooms] == ["Wohnzimmer", "Bad", "Schlafzimmer"]
    assert {"Ground floor", "Upper floor"} <= {c["heading"] for c in cards(home) if c["type"] == "heading"}
    # functions: short names, status next to on/off
    tiles = {c["entity"]: c for c in narrow[1]["cards"] if c["type"] == "tile"}
    solar = tiles[eid(hass, "switch", "SolarWarmwasser")]
    assert solar["name"] == "Solar hot water" and solar["state_content"] == ["state", "status"] and solar["grid_options"] == {"columns": "full"}
    holiday = tiles[eid(hass, "switch", "Urlaubsmodus")]
    assert "confirmation" in holiday["icon_tap_action"]
    # house: the drawing and the unit wide, the heating elements by room name
    assert [c["image_entity"] for c in house["sections"][0]["cards"]] == [eid(hass, "image", k) for k in ("BildHaus", "BildAnlage")]
    elements = next(c for c in cards(house) if c["type"] == "entities")
    assert [r["name"] for r in elements["entities"]] == ["Wohnzimmer", "Schlafzimmer", "Bad"]
    # hot water: the tank, its controls, the last 24 hours
    graph = next(c for c in cards(water) if c["type"] == "history-graph")
    assert graph["entities"] == [eid(hass, "sensor", k) for k in ("WarmwasserIstTemperatur", "WarmwasserUntenTemperatur")]
    heater = next(c for c in cards(water) if c.get("entity") == eid(hass, "water_heater", "Warmwasser"))
    assert {"type": "target-temperature"} in heater["features"]
    # settings: limits with +/- buttons, the weekly schedule with day names
    all_settings = cards(settings)
    numbers = [c for c in all_settings if c.get("features") == [{"type": "numeric-input", "style": "buttons"}]]
    assert {c["entity"] for c in numbers} >= {eid(hass, "number", k) for k in ("SolarSchwelle", "PreisSchwelle", "BoostGrenze", "KuehlWunsch")}
    schedule = next(c for c in all_settings if c["type"] == "entities" and any(r.get("name") == "Monday" for r in c["entities"]))
    assert [r["name"] for r in schedule["entities"]][1:] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    every = {c.get("entity") for v in views for c in cards(v)} | {r["entity"] for v in views for c in cards(v) for r in c.get("entities", [])
                                                                  if isinstance(r, dict)}
    every |= {e for v in views for c in cards(v) if c["type"] == "history-graph" for e in c["entities"]} | set(sum(targets.values(), []))
    every |= {c["tap_action"]["entity"] for c in rooms}
    assert all(e is None or hass.states.get(e) is not None for e in every)  # only entities that exist


async def test_dashboard_with_house_photo(hass: HomeAssistant, device) -> None:
    """With the user's own house photo the start page shows it, with the main values on it."""
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"house_photo": "/local/proxon/haus.jpg"})
    await setup(hass, entry)
    dashboard = await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    phone = next(s for s in dashboard["views"][0]["sections"] if s["visibility"][0]["media_query"] == "(max-width: 1023px)")
    hero = phone["cards"][0]
    assert hero["type"] == "picture-elements" and hero["image"] == "/local/proxon/haus.jpg" and "image_entity" not in hero
    labels = {e["entity"]: e for e in hero["elements"]}
    assert all(e["type"] == "state-label" for e in labels.values())
    assert labels[eid(hass, "sensor", "T3Frischluft")]["prefix"] == "Outdoor "
    assert labels[eid(hass, "sensor", "RaumMittel")]["prefix"] == "Indoor "
    assert labels[eid(hass, "sensor", "WarmwasserIstTemperatur")]["tap_action"]["entity"] == eid(hass, "water_heater", "Warmwasser")
    assert eid(hass, "sensor", "AktuellerBetrieb") in labels
    # the photo is for the phone; tablet and computer keep the floor plan, the house tab the drawn house
    wide = dashboard["views"][0]["sections"][1]
    assert wide["cards"][0]["image_entity"] == eid(hass, "image", "BildGrundriss")
    house = dashboard["views"][1]["sections"][0]["cards"][0]
    assert house["image_entity"] == eid(hass, "image", "BildHaus")


async def test_indoor_average(hass: HomeAssistant, device) -> None:
    await setup(hass)
    state = hass.states.get(eid(hass, "sensor", "RaumMittel"))
    assert float(state.state) == round((22.5 + 21.0 + 19.0) / 3, 2) and state.attributes["rooms"] == 3
    assert state.attributes["unit_of_measurement"] == "°C"


async def test_house_floors_and_photo_in_the_options(hass: HomeAssistant, device, hass_client) -> None:
    entry = await setup(hass)
    client = await hass_client()

    async def house() -> str:
        return await (await client.get(f"/api/image_proxy/{eid(hass, 'image', 'BildHaus')}")).text()

    assert "Upper floor" in await house()  # guessed from the names: the bedroom lies upstairs
    result = await hass.config_entries.options.async_init(entry.entry_id)
    fields = {str(k): k for k in result["data_schema"].schema}
    assert fields["upper_floor_rooms"].description["suggested_value"] == ["1"]  # the guess, to confirm or change
    assert "house_photo" in fields
    bad = await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 10, "house_photo": "haus.jpg"})
    assert bad["type"] is FlowResultType.FORM and bad["errors"] == {"house_photo": "photo_path"}
    done = await hass.config_entries.options.async_configure(
        bad["flow_id"], {"scan_interval": 10, "upper_floor_rooms": [], "house_photo": " /local/proxon/haus.jpg "}
    )
    assert done["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {"scan_interval": 10, "upper_floor_rooms": [], "house_photo": "/local/proxon/haus.jpg"}
    assert "Upper floor" not in await house()  # a bungalow: everything on one floor
    # choosing just what was guessed keeps nothing extra: the guess follows renamed rooms
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 10, "upper_floor_rooms": ["1"]})
    await hass.async_block_till_done()
    assert entry.options == {"scan_interval": 10}


async def test_install_glass_theme(hass: HomeAssistant, device, tmp_path) -> None:
    """The action writes the theme into the themes folder and draws the pictures dark; it tells whether the theme loads."""
    entry = await setup(hass)
    hass.config.config_dir = str(tmp_path)
    answer = await hass.services.async_call(DOMAIN, "install_glass_theme", {}, blocking=True, return_response=True)
    written = (tmp_path / "themes" / "proxon_control.yaml").read_text(encoding="utf-8")
    assert "Proxon Glas:" in written and "ha-card-backdrop-filter" in written
    assert parse_yaml(written)["Proxon Glas"]["primary-text-color"] == "#f3f5ff"
    assert answer["installed"] is False and "configuration.yaml" in answer["message"]  # this test system loads no themes folder
    assert entry.options["picture_theme"] == "dark"
    with patch("custom_components.proxon_control.services.async_install_theme", return_value=True):
        answer = await hass.services.async_call(DOMAIN, "install_glass_theme", {}, blocking=True, return_response=True)
    assert answer["installed"] is True and answer["theme"] == "Proxon Glas"
