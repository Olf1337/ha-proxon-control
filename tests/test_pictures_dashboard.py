"""Dashboard pictures (unit, hot water, house) and the ready-made dashboard."""
from __future__ import annotations

import xml.dom.minidom

from homeassistant.core import HomeAssistant
from homeassistant.util.yaml import parse_yaml

from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.pictures import Room, house_svg, tank_svg, unit_svg

from .test_integration import eid, setup

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


def test_unit_picture_heat_pump() -> None:
    svg = valid(unit_svg({**DATA, "DrehzahlKompressor": 4010.0}, "en"))
    assert "Heating" in svg and "4010 rpm" in svg and "animation-duration:0.60s" in svg
    assert "Cooling" in valid(unit_svg({**DATA, "DrehzahlKompressor": 4010.0, "Kuehlbetrieb4Wegeventil": 1.0}, "en"))


def test_tank_picture() -> None:
    svg = valid(tank_svg(DATA, "de", boost_limit=40))
    assert "Soll 46°" in svg and "41,1°" in svg and "Heizstab aus" in svg and "Boost unter 40°" in svg and "Heizstab-Soll 44°" in svg
    assert 'class="glow"' not in svg
    on = valid(tank_svg({**DATA, "E-Heizstab": 1.0}, "de"))
    assert 'class="glow"' in on and "Heizstab an" in on


def test_house_picture_lays_out_any_number_of_rooms() -> None:
    rooms = [Room(f"Raum {i}", t, 22.0, i == 2) for i, t in enumerate((20.0, 21.5, 22.0, 22.5, 23.5, 24.0))]
    svg = valid(house_svg(rooms, 7.6, "de"))
    assert svg.count('class="flame"') == 1 and "Zuheizer an" in svg and "Raum 5" in svg
    assert "#dcebfb" in svg and "#ddf3e9" in svg and "#fde4d8" in svg  # too cold, fine, too warm
    big = valid(house_svg([Room(f"R{i}", 21.0, 21.0, False) for i in range(14)], None, "en"))
    assert 'height="' in big and "R13" in big
    assert valid(house_svg([Room("Küche & <Bad>", None, None, False)], None, "de"))  # names are escaped, missing values shown as –


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


async def test_picture_is_only_announced_when_it_changes(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    entity_id = eid(hass, "image", "BildAnlage")
    before = hass.states.get(entity_id).state
    coordinator = entry.runtime_data
    coordinator.async_set_updated_data(dict(coordinator.data))  # same values
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == before
    coordinator.async_set_updated_data({**coordinator.data, "T3Frischluft": 3.5})
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state != before


async def test_create_dashboard_action(hass: HomeAssistant, device) -> None:
    await setup(hass)
    result = await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    dashboard = parse_yaml(result["yaml"])
    view = dashboard["views"][0]
    assert view["type"] == "sections"
    cards = [c for s in view["sections"] for c in s["cards"]]
    entities = {c.get("entity") for c in cards} | {e for c in cards for e in c.get("entities", [])}
    for platform, key in (("image", "BildAnlage"), ("image", "BildWarmwasser"), ("image", "BildHaus"), ("fan", "Lueftung"),
                          ("water_heater", "Warmwasser"), ("climate", "NBE0Thermostat"), ("climate", "NBE4Thermostat"),
                          ("switch", "SolarWarmwasser"), ("switch", "Nachtkuehlung"), ("switch", "Urlaubsmodus"), ("number", "BoostGrenze")):
        assert eid(hass, platform, key) in entities, key
    assert all(e is None or hass.states.get(e) is not None for e in entities)  # only entities that exist
    headings = [c["heading"] for c in cards if c["type"] == "heading"]
    assert headings == ["Anlage", "Warmwasser", "Haus", "Funktionen"] or headings == ["Unit", "Hot water", "House", "Functions"]
