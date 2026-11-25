"""The ready-made dashboard (deprecated since 1.0), the floors of the rooms, and the removal of the dashboard pictures."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util.yaml import dump, parse_yaml
import pytest

from custom_components.proxon_control.const import DOMAIN
from custom_components.proxon_control.entity import guess_floor

from .test_integration import call, eid, make_entry, setup


def test_floor_guess() -> None:
    names = ("Schlafzimmer", "Kinderzimmer 2", "Bad oben", "Eltern", "Bedroom", "Wohnzimmer", "Küche", "Gäste-WC", "Bad", "Büro")
    assert [guess_floor(n) for n in names] == [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]



async def test_switching_on_without_a_sensor_is_refused(hass: HomeAssistant, device) -> None:
    """Without the sensor it needs, a function isn't switched on (it would be on and never heat): a message says where to
    choose the sensor. With a fixed electricity price there are no cheap hours."""
    from homeassistant.exceptions import ServiceValidationError

    entry = await setup(hass)
    solar, cheap = eid(hass, "switch", "SolarWarmwasser"), eid(hass, "switch", "PreisWarmwasser")
    assert "status" not in hass.states.get(solar).attributes  # off: just "off"
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "switch", "turn_on", entity_id=solar)
    assert err.value.translation_key == "solar_needs_sensor"
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "switch", "turn_on", entity_id=cheap)
    assert err.value.translation_key == "price_needs_sensor"
    assert hass.states.get(solar).state == "off" and hass.states.get(cheap).state == "off"
    hass.config_entries.async_update_entry(entry, options={**entry.options, "fixed_price": 32.5, "price_sensor": "sensor.preis"})
    await hass.async_block_till_done()
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "switch", "turn_on", entity_id=eid(hass, "switch", "PreisWarmwasser"))
    assert err.value.translation_key == "price_fixed"


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
    dashboard = await hass.services.async_call(DOMAIN, "create_dashboard", {"paste_only": True}, blocking=True, return_response=True)
    assert list(dashboard) == ["views"]  # the answer is the dashboard itself: paste it as it is
    assert parse_yaml(dump(dashboard)) == dashboard
    views = dashboard["views"]
    # one tab for each thing to do: home, hot water, optimisation, power, settings
    assert [v["path"] for v in views] == ["proxon", "proxon-hot-water", "proxon-optimize", "proxon-energy", "proxon-settings"]
    assert all(v["type"] == "sections" for v in views)
    home, water, optimize, energy, settings = views

    def cards(view: dict) -> list[dict]:
        out = []
        for c in (c for s in view["sections"] for c in s["cards"]):
            out += [c, *c.get("cards", [])]  # the cards of a stack too
        return out

    assert all(v["theme"] == "Proxon Bento" for v in views)  # the bento look (normal look until the theme is installed)
    # no pictures any more (removed in 1.0): no picture cards, no tab for the drawn house
    assert not [c for v in views for c in cards(v) if "image_entity" in c]
    # ---- home ----
    wide = [s for s in home["sections"] if s["visibility"] == [{"condition": "screen", "media_query": "(min-width: 1024px)"}]]
    narrow = [s for s in home["sections"] if s["visibility"] == [{"condition": "screen", "media_query": "(max-width: 1023px)"}]]
    assert len(wide) + len(narrow) == len(home["sections"])
    figures, controls, house, side = wide
    # the key figures over the whole width, four side by side: outdoor, indoor, hot water with their last day, power now
    assert figures["column_span"] == 4
    row = figures["cards"][0]
    assert row["type"] == "grid" and row["columns"] == 4 and row["square"] is False
    assert [c["entity"] for c in row["cards"]] == [eid(hass, "sensor", k) for k in
                                                   ("T3Frischluft", "RaumMittel", "WarmwasserIstTemperatur", "LeistungGesamt")]
    assert row["cards"][0]["features"] == [{"type": "trend-graph", "hours_to_show": 24}]
    assert row["cards"][2]["tap_action"] == {"action": "navigate", "navigation_path": "proxon-hot-water"}
    assert row["cards"][3]["tap_action"] == {"action": "navigate", "navigation_path": "proxon-energy"}
    # operate the ventilation (with the weekly schedule), then the automatic functions with their status
    entities = [c.get("entity") for c in controls["cards"]]
    assert entities[1:6] == [eid(hass, "fan", "Lueftung"), eid(hass, "select", "Betriebsart"), eid(hass, "switch", "Intensivlueftung"),
                             eid(hass, "switch", "Urlaubsmodus"), eid(hass, "switch", "ZeitprogrammAktiv")]
    assert "confirmation" in controls["cards"][4]["icon_tap_action"]
    solar_home = next(c for c in controls["cards"] if c.get("entity") == eid(hass, "switch", "SolarWarmwasser"))
    assert solar_home["state_content"] == ["state", "status"]
    # every room as a tile, two side by side: the temperature large, the target with -/+, the heating element
    # above the rooms the switch for the heating elements of all rooms, then the first floor's heading
    assert house["column_span"] == 2 and house["cards"][0]["entity"] == eid(hass, "switch", "WaermeelementeAlle")
    assert house["cards"][1]["type"] == "heading"
    stacks = [c for c in house["cards"] if c["type"] == "vertical-stack"]
    assert [st["cards"][0]["entity"] for st in stacks] == [eid(hass, "sensor", f"NBE{n}Temperatur") for n in (0, 4, 1)]
    assert [st["cards"][0]["name"] for st in stacks] == ["Wohnzimmer", "Bad", "Schlafzimmer"]
    assert all(st["cards"][0]["type"] == "entity" for st in stacks)
    target = stacks[1]["cards"][1]
    assert target["entity"] == eid(hass, "climate", "NBE4Thermostat") and target["features"] == [{"type": "target-temperature"}]
    assert target["features_position"] == "inline" and target["hide_state"] is True and target["name"] == "Target temperature"
    element = stacks[1]["cards"][2]
    assert element["entity"] == eid(hass, "sensor", "NBE4Waermeelement") and element["name"] == "Heating element"
    assert element["tap_action"] == {"action": "more-info", "entity": eid(hass, "climate", "NBE4Thermostat")}
    assert all(st["grid_options"] == {"columns": 12} for st in stacks)  # two rooms side by side
    assert {"Ground floor", "Upper floor"} <= {c["heading"] for c in cards(home) if c["type"] == "heading"}
    # hot water in short and the air on the right
    assert side["cards"][0]["heading"] == "Hot water"
    short = next(c for c in side["cards"] if c.get("entity") == eid(hass, "water_heater", "Warmwasser"))
    assert short["tap_action"] == {"action": "navigate", "navigation_path": "proxon-hot-water"}
    assert home["dense_section_placement"] is True and home["max_columns"] == 4
    assert [b["entity"] for b in home["badges"]] == [eid(hass, "select", "Betriebsart"), eid(hass, "sensor", "IstLuefterstufe"),
                                                    eid(hass, "sensor", "Antwortzeit_path"), eid(hass, "binary_sensor", "Stoerung")]
    # phone: key figures, then (without a photo) right away the ventilation; the rooms one below the other; the rest
    phone = narrow[0]["cards"]
    assert phone[0]["columns"] == 2 and phone[0]["cards"] == row["cards"]  # the key figures, two side by side
    assert phone[1]["type"] == "heading" and phone[2]["entity"] == eid(hass, "fan", "Lueftung")
    assert eid(hass, "fan", "Lueftung") in [c.get("entity") for c in phone]
    assert [c["cards"][0]["entity"] for c in narrow[1]["cards"] if c["type"] == "vertical-stack"] == [
        eid(hass, "sensor", f"NBE{n}Temperatur") for n in (0, 4, 1)]

    # ---- hot water: the tank, its controls, the last day, settings, what the automatic functions are doing ----
    graph = next(c for c in cards(water) if c["type"] == "history-graph")
    assert graph["entities"] == [eid(hass, "sensor", k) for k in ("WarmwasserIstTemperatur", "WarmwasserUntenTemperatur")]
    heater = next(c for c in cards(water) if c.get("entity") == eid(hass, "water_heater", "Warmwasser"))
    assert {"type": "target-temperature"} in heater["features"]
    water_entities = {c.get("entity") for c in cards(water)}
    assert {eid(hass, "sensor", "WarmwasserDuschminuten"), eid(hass, "number", "SollWassertemperatur"),
            eid(hass, "switch", "Legionellenfunktion")} <= water_entities
    status = next(c for c in cards(water) if c.get("entity") == eid(hass, "sensor", "BoostStatus"))
    assert status["tap_action"] == {"action": "navigate", "navigation_path": "proxon-optimize"}
    assert eid(hass, "switch", "WarmwasserBoost") not in water_entities  # switched in the optimisation tab

    # ---- optimisation: every function with its switch, status and limits ----
    blocks = {s["cards"][0]["heading"]: [c.get("entity") for c in s["cards"][1:]] for s in optimize["sections"]}
    assert list(blocks) == ["Hot-water store (solar / price)", "Hot-water boost", "Legionella protection",
                            "Summer night cooling", "Summer/winter automatic", "Night setback"]
    # legionella: with solar or planned (weekday and time)
    assert blocks["Legionella protection"][:2] == [eid(hass, "switch", "LegionellenSonne"), eid(hass, "switch", "LegionellenGeplant")]
    assert eid(hass, "select", "LegionellenTag") in blocks["Legionella protection"]
    assert blocks["Hot-water boost"] == [eid(hass, "switch", "WarmwasserBoost"), eid(hass, "number", "BoostGrenze"),
                                         eid(hass, "number", "Soll-E-Heizstab-Temperatur")]
    solar = next(c for c in cards(optimize) if c.get("entity") == eid(hass, "switch", "SolarWarmwasser"))
    assert solar["name"] == "Solar hot water" and solar["state_content"] == ["state", "status"]
    numbers = [c for c in cards(optimize) if c.get("features") == [{"type": "numeric-input", "style": "buttons"}]]
    assert {c["entity"] for c in numbers} >= {eid(hass, "number", k) for k in ("SolarSchwelle", "PreisSchwelle", "BoostGrenze", "KuehlWunsch")}

    # ---- power: right now, consumption today / week / month / year, the split, per day and month, runtimes and starts ----
    now = [c.get("entity") for c in energy["sections"][0]["cards"][1:4]]
    assert now == [eid(hass, "sensor", k) for k in ("LeistungGesamt", "LeistungKompressor", "LeistungLueftung")]
    assert energy["sections"][0]["cards"][1]["features"] == [{"type": "trend-graph", "hours_to_show": 1}]
    totals = [c for c in cards(energy) if c["type"] == "statistic"]
    assert [c["period"]["calendar"]["period"] for c in totals] == ["day", "week", "month", "year"]
    forecast = [c["entity"] for c in cards(energy) if c.get("entity", "").endswith("forecast_this_month")
                or c.get("entity", "").endswith("forecast_this_year")]
    assert forecast == [eid(hass, "sensor", "EnergieGesamtMonatPrognose"), eid(hass, "sensor", "EnergieGesamtJahrPrognose")]
    assert all(c["entity"] == eid(hass, "sensor", "EnergieGesamt") and c["stat_type"] == "change" for c in totals)
    split = [c for c in cards(energy) if c["type"] == "entities"]
    assert [c["title"] for c in split] == ["Compressor", "Ventilation and electronics"]
    assert [r["entity"] for r in split[0]["entities"]] == [eid(hass, "sensor", f"EnergieKompressor{p}") for p in ("Heute", "Woche", "Monat", "Jahr")]
    graphs = [c for c in cards(energy) if c["type"] == "statistics-graph"]
    assert [(g["period"], g["stat_types"], g["days_to_show"]) for g in graphs] == [
        ("day", ["change"], 30), ("month", ["change"], 365), ("day", ["change"], 14), ("day", ["change"], 14)]
    assert [e["entity"] for e in graphs[0]["entities"]] == [eid(hass, "sensor", k) for k in ("EnergieGesamt", "EnergieKompressor", "EnergieLueftung")]
    assert all(g["chart_type"] == "bar" for g in graphs)
    assert any(c["type"] == "history-graph" for c in cards(energy))

    # ---- settings: ventilation limits, the weekly schedule with day names, heating elements, the unit, diagnostics ----
    all_settings = cards(settings)
    assert eid(hass, "number", "GrenzwertFeuchte") in {c.get("entity") for c in all_settings}
    schedule = next(c for c in all_settings if c["type"] == "entities" and any(r.get("name") == "Monday" for r in c["entities"]))
    assert [r["name"] for r in schedule["entities"]][1:] == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    elements = next(c for c in all_settings if c["type"] == "entities" and c["entities"][0]["entity"].endswith("heating_element"))
    assert [r["name"] for r in elements["entities"]] == ["Wohnzimmer", "Schlafzimmer", "Bad"]

    # only entities that exist
    every = {c.get("entity") for v in views for c in cards(v)} | {r["entity"] for v in views for c in cards(v) for r in c.get("entities", [])
                                                                  if isinstance(r, dict)}
    every |= {e for v in views for c in cards(v) if c["type"] == "history-graph" for e in c["entities"] if isinstance(e, str)}
    assert all(e is None or hass.states.get(e) is not None for e in every)


async def test_dashboard_with_house_photo(hass: HomeAssistant, device) -> None:
    """With the user's own house photo the start page shows it, with the main values on it."""
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"house_photo": "/local/proxon/haus.jpg"})
    await setup(hass, entry)
    dashboard = await hass.services.async_call(DOMAIN, "create_dashboard", {"paste_only": True}, blocking=True, return_response=True)
    phone = next(s for s in dashboard["views"][0]["sections"] if s["visibility"][0]["media_query"] == "(max-width: 1023px)")
    hero = next(c for c in phone["cards"] if c["type"] == "picture-elements")  # after the key figures
    assert hero["type"] == "picture-elements" and hero["image"] == "/local/proxon/haus.jpg" and "image_entity" not in hero
    labels = {e["entity"]: e for e in hero["elements"]}
    assert all(e["type"] == "state-label" for e in labels.values())
    assert labels[eid(hass, "sensor", "T3Frischluft")]["prefix"] == "Outdoor "
    assert labels[eid(hass, "sensor", "RaumMittel")]["prefix"] == "Indoor "
    assert labels[eid(hass, "sensor", "WarmwasserIstTemperatur")]["tap_action"]["entity"] == eid(hass, "water_heater", "Warmwasser")
    assert eid(hass, "sensor", "AktuellerBetrieb") in labels
    # the photo is for the phone only
    wide = [s for s in dashboard["views"][0]["sections"] if s["visibility"][0]["media_query"] == "(min-width: 1024px)"]
    assert all(c.get("image") != "/local/proxon/haus.jpg" for s in wide for c in s["cards"])


async def test_indoor_average(hass: HomeAssistant, device) -> None:
    await setup(hass)
    state = hass.states.get(eid(hass, "sensor", "RaumMittel"))
    assert float(state.state) == round((22.5 + 21.0 + 19.0) / 3, 2) and state.attributes["rooms"] == 3
    assert state.attributes["unit_of_measurement"] == "°C"


async def test_house_floors_and_photo_in_the_options(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)

    async def house() -> list[str]:
        """The floor headings over the rooms of the dashboard."""
        dashboard = await hass.services.async_call(DOMAIN, "create_dashboard", {"paste_only": True}, blocking=True, return_response=True)
        rooms = next(s for s in dashboard["views"][0]["sections"] if s.get("column_span") == 2)
        return [c["heading"] for c in rooms["cards"] if c["type"] == "heading"]

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


def test_theme_file_in_the_repository() -> None:
    """The dashboard's themes are a file in the repository to add by hand (the integration writes nothing into the
    configuration folder); the dashboard names the theme in it."""
    from pathlib import Path

    from custom_components.proxon_control.theme import GLASS_THEME_NAME, THEME_NAME

    themes = parse_yaml((Path(__file__).parents[1] / "themes" / "proxon_control.yaml").read_text(encoding="utf-8"))
    assert set(themes) == {THEME_NAME, GLASS_THEME_NAME}
    bento = themes[THEME_NAME]
    assert set(bento["modes"]) == {"light", "dark"} and bento["ha-card-border-radius"] == "22px"
    assert themes[GLASS_THEME_NAME]["primary-text-color"] == "#f3f5ff"


async def test_create_dashboard_is_for_admins_only(hass: HomeAssistant, device, hass_read_only_user) -> None:
    """It writes a dashboard into Home Assistant: a user without admin rights can't run it."""
    from homeassistant.core import Context
    from homeassistant.exceptions import Unauthorized

    await setup(hass)
    user = hass_read_only_user
    assert not user.is_admin
    with pytest.raises(Unauthorized):
        await hass.services.async_call(DOMAIN, "create_dashboard", {"paste_only": True}, blocking=True, return_response=True,
                                       context=Context(user_id=user.id))
    assert not hass.services.has_service(DOMAIN, "install_glass_theme")  # the theme isn't written by the integration any more


async def test_create_dashboard_puts_it_into_home_assistant(hass: HomeAssistant, device, hass_ws_client) -> None:
    """Without "paste only" the action creates the dashboard "Proxon Control" (sidebar) and writes it anew on the next run."""
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "lovelace", {})
    await setup(hass)
    answer = await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    assert answer["url"] == "/proxon-dashboard" and answer["created"] is True
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "lovelace/dashboards/list"})
    boards = (await client.receive_json())["result"]
    proxon = next(b for b in boards if b["url_path"] == "proxon-dashboard")
    assert proxon["title"] == "Proxon Control" and proxon["show_in_sidebar"] is True and proxon["mode"] == "storage"
    await client.send_json_auto_id({"type": "lovelace/config", "url_path": "proxon-dashboard"})
    views = (await client.receive_json())["result"]["views"]
    assert [v["path"] for v in views] == ["proxon", "proxon-hot-water", "proxon-optimize", "proxon-energy", "proxon-settings"]
    # the next run writes it anew instead of creating a second one
    answer = await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    assert answer["created"] is False and "replaced" in answer["message"]
    await client.send_json_auto_id({"type": "lovelace/dashboards/list"})
    assert [b["url_path"] for b in (await client.receive_json())["result"]].count("proxon-dashboard") == 1


async def test_old_dashboard_title_is_renamed(hass: HomeAssistant, device, hass_ws_client) -> None:
    """Until 0.21 the dashboard was called "Proxon"; since the page "Proxon" is our own interface it is "Proxon Control" (a
    title chosen by hand stays)."""
    from homeassistant.setup import async_setup_component

    from custom_components.proxon_control.dashboard_store import async_retitle

    assert await async_setup_component(hass, "lovelace", {})
    await setup(hass)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "lovelace/dashboards/create", "url_path": "proxon-dashboard", "title": "Proxon",
                                    "icon": "mdi:home", "show_in_sidebar": True, "require_admin": False, "mode": "storage"})
    assert (await client.receive_json())["success"]

    async def title() -> str:
        await client.send_json_auto_id({"type": "lovelace/dashboards/list"})
        return next(b for b in (await client.receive_json())["result"] if b["url_path"] == "proxon-dashboard")["title"]

    assert await async_retitle(hass, "proxon-dashboard", "Proxon Control", only_from="Unser Haus") is False  # chosen by hand: kept
    assert await title() == "Proxon"
    await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    assert await title() == "Proxon Control"


async def test_create_dashboard_without_dashboards(hass: HomeAssistant, device) -> None:
    """Without Home Assistant's dashboards the action says how to paste it instead."""
    from homeassistant.exceptions import ServiceValidationError

    await setup(hass)
    with pytest.raises(ServiceValidationError, match="paste only"):
        await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)


# ---------------- basement ----------------
def test_basement_by_name() -> None:
    assert [guess_floor(n) for n in ("Keller", "Hobbyraum", "UG Werkstatt", "Schlafen", "Wohnen", "Basement")] == [-1, -1, -1, 1, 0, -1]


async def test_basement_in_the_options_and_on_the_dashboard(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)  # rooms Wohnzimmer (0), Schlafzimmer (1), Bad (4)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "basement_rooms" in {str(k) for k in result["data_schema"].schema}
    await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 10, "basement_rooms": ["4"]})
    await hass.async_block_till_done()
    assert entry.options["basement_rooms"] == ["4"]
    dashboard = await hass.services.async_call(DOMAIN, "create_dashboard", {"paste_only": True}, blocking=True, return_response=True)
    home = dashboard["views"][0]
    rooms = next(s for s in home["sections"] if s.get("column_span") == 2)
    headings = [c["heading"] for c in rooms["cards"] if c["type"] == "heading"]
    assert headings == ["Ground floor", "Upper floor", "Basement"]
    last = [c for c in rooms["cards"] if c["type"] == "vertical-stack"][-1]
    assert last["cards"][0]["entity"] == eid(hass, "sensor", "NBE4Temperatur")  # the bathroom, now in the basement


def test_room_chosen_for_both_floors_counts_as_upstairs() -> None:
    """A room in both lists of the options (upper floor and basement) is listed upstairs."""
    from custom_components.proxon_control.entity import room_floors

    data = {f"NBE{n}name": name for n, name in ((1, "Arbeitszimmer"), (2, "Hobbyraum"), (3, "Schlafen"))}
    both = {"upper_floor_rooms": ["1"], "basement_rooms": ["1", "2"]}
    assert room_floors(both, data, [1, 2, 3]) == [1, -1, 0]  # 1 in both: upstairs; 3 not chosen upstairs: ground floor
    # without a choice the names decide; a basement name wins over an upstairs one
    assert room_floors({}, data, [1, 2, 3]) == [0, -1, 1]
    assert room_floors({}, {"NBE1name": "Kinderzimmer Keller"}, [1]) == [-1]


async def test_all_rooms_upstairs_get_one_heading(hass: HomeAssistant, device) -> None:
    """With all rooms on one floor (here all upstairs) the dashboard shows one heading "Rooms", not the floor's name."""
    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"upper_floor_rooms": ["0", "1", "4"], "basement_rooms": []})
    await setup(hass, entry)
    dashboard = await hass.services.async_call(DOMAIN, "create_dashboard", {"paste_only": True}, blocking=True, return_response=True)
    rooms = next(s for s in dashboard["views"][0]["sections"] if s.get("column_span") == 2)
    headings = [c for c in rooms["cards"] if c["type"] == "heading"]
    assert [(h["heading"], h["heading_style"]) for h in headings] == [("Rooms", "title")]


async def test_ready_made_dashboard_is_deprecated(hass: HomeAssistant, device, hass_ws_client) -> None:
    """The page "Proxon" replaces the ready-made dashboard (it goes in 2.0): a notice under Repairs while one exists, none
    without it; the action still works until then."""
    from homeassistant.helpers import issue_registry as ir
    from homeassistant.setup import async_setup_component

    from custom_components.proxon_control.panel import DEPRECATED_ISSUE, async_dashboard_notice

    assert await async_setup_component(hass, "lovelace", {})
    await setup(hass)
    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, DEPRECATED_ISSUE) is None  # no dashboard: nothing to say
    answer = await hass.services.async_call(DOMAIN, "create_dashboard", {}, blocking=True, return_response=True)
    assert answer["created"] is True
    issue = issues.async_get_issue(DOMAIN, DEPRECATED_ISSUE)
    assert issue and issue.severity is ir.IssueSeverity.WARNING and issue.translation_placeholders == {"url": "/proxon-dashboard"}
    # deleted by hand: the notice goes (on the next start, when the page is registered again)
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "lovelace/dashboards/list"})
    board = next(b for b in (await client.receive_json())["result"] if b["url_path"] == "proxon-dashboard")
    await client.send_json_auto_id({"type": "lovelace/dashboards/delete", "dashboard_id": board["id"]})
    assert (await client.receive_json())["success"]
    async_dashboard_notice(hass)
    assert issues.async_get_issue(DOMAIN, DEPRECATED_ISSUE) is None



async def test_pictures_of_earlier_versions_are_removed(hass: HomeAssistant, device) -> None:
    """The dashboard pictures were removed in 1.0: their entities and their light/dark option go at the next start."""
    from homeassistant.helpers import entity_registry as er

    entry = make_entry()
    entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(entry, options={"picture_theme": "dark", "scan_interval": 10})
    reg = er.async_get(hass)
    old = reg.async_get_or_create("image", DOMAIN, f"{entry.unique_id}_BildAnlage", config_entry=entry)
    await setup(hass, entry)
    assert reg.async_get(old.entity_id) is None
    assert not [e for e in er.async_entries_for_config_entry(reg, entry.entry_id) if e.domain == "image"]
    assert entry.options == {"scan_interval": 10}
