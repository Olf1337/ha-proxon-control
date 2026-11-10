"""Dashboard pictures (unit, hot water, house) and the ready-made dashboard."""
from __future__ import annotations

import time
from unittest.mock import patch
import xml.dom.minidom

from homeassistant.core import HomeAssistant
from homeassistant.util.yaml import dump, parse_yaml

from custom_components.proxon_control import image as image_module
from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.pictures import (
    HOUSE_W, Room, house_layout, house_svg, house_targets, tank_svg, tank_targets, unit_svg, unit_targets,
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


def test_house_picture_lays_out_any_number_of_rooms() -> None:
    rooms = [Room(f"Raum {i}", t, 22.0, i == 2) for i, t in enumerate((20.0, 21.5, 22.0, 22.5, 23.5, 24.0))]
    svg = valid(house_svg(rooms, 7.6, "de"))
    assert svg.count('class="flame"') == 1 and "Raum 5" in svg
    assert "#dcebfb" in svg and "#ddf3e9" in svg and "#fde4d8" in svg  # too cold, fine, too warm
    assert "zu kalt" in svg and "antippen zum Einstellen" in svg
    big = valid(house_svg([Room(f"R{i}", 21.0, 21.0, False) for i in range(14)], None, "en"))
    assert "R13" in big
    assert valid(house_svg([Room("Küche & <Bad>", None, None, False)], None, "de"))  # names are escaped, missing values shown as –


def test_tap_areas_match_the_drawing() -> None:
    height, boxes = house_layout(6)
    for (x, y, w, h), (cx, cy, pw, ph) in zip(boxes, house_targets(6)):
        assert abs(cx / 100 * HOUSE_W - (x + w / 2)) < 0.5 and abs(cy / 100 * height - (y + h / 2)) < 0.5
        assert abs(pw / 100 * HOUSE_W - w) < 0.5 and abs(ph / 100 * height - h) < 0.5
    assert len(house_targets(14)) == 14
    assert unit_targets()["unit"][:2] == (50.0, 50.0)
    assert 0 < tank_targets()["tank"][0] < 100


# ---------------- in Home Assistant ----------------
async def test_picture_entities(hass: HomeAssistant, device, hass_client) -> None:
    await setup(hass)
    client = await hass_client()
    # values of the simulated unit (the test system runs in English)
    for key, expected in (("BildAnlage", "Outdoor air"), ("BildWarmwasser", "36,0°"), ("BildHaus", "Schlafzimmer")):
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
    overview, settings = dashboard["views"]
    assert overview["type"] == settings["type"] == "sections"
    left, right = overview["sections"]
    assert left["column_span"] == 2  # unit and house: wide
    pictures = {c["image_entity"]: c for s in overview["sections"] for c in s["cards"] if c["type"] == "picture-elements"}
    assert set(pictures) == {eid(hass, "image", k) for k in ("BildAnlage", "BildWarmwasser", "BildHaus")}
    # tapping: the unit opens the ventilation, the tank the hot water, every room its thermostat
    targets = {k: [e["entity"] for e in c["elements"]] for k, c in pictures.items()}
    assert targets[eid(hass, "image", "BildAnlage")] == [eid(hass, "fan", "Lueftung")]
    assert targets[eid(hass, "image", "BildWarmwasser")] == [eid(hass, "water_heater", "Warmwasser")]
    assert targets[eid(hass, "image", "BildHaus")] == [eid(hass, "climate", f"NBE{n}Thermostat") for n in (0, 1, 4)]
    assert all(e["type"] == "image" and e["tap_action"]["action"] == "more-info" for c in pictures.values() for e in c["elements"])
    # functions: full width, short names, status next to on/off
    tiles = {c["entity"]: c for c in right["cards"] if c["type"] == "tile"}
    solar = tiles[eid(hass, "switch", "SolarWarmwasser")]
    assert solar["name"] == "Solar hot water" and solar["state_content"] == ["state", "status"] and solar["grid_options"] == {"columns": "full"}
    holiday = tiles[eid(hass, "switch", "Urlaubsmodus")]
    assert "confirmation" in holiday["icon_tap_action"]
    # settings: limits with +/- buttons, the weekly schedule with day names
    cards = [c for s in settings["sections"] for c in s["cards"]]
    numbers = [c for c in cards if c.get("features") == [{"type": "numeric-input", "style": "buttons"}]]
    assert {c["entity"] for c in numbers} >= {eid(hass, "number", k) for k in ("SolarSchwelle", "PreisSchwelle", "BoostGrenze", "KuehlWunsch")}
    schedule = next(c for c in cards if c["type"] == "entities" and any(r.get("name") == "Monday" for r in c["entities"]))
    assert [r["name"] for r in schedule["entities"]][1:] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    every = {c.get("entity") for c in cards} | {r["entity"] for c in cards for r in c.get("entities", [])} | set(sum(targets.values(), []))
    assert all(e is None or hass.states.get(e) is not None for e in every)  # only entities that exist
