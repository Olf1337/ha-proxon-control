"""The "Proxon" page in a real browser, at phone and desktop width, with the entities of a set-up test unit: it loads
without errors, nothing runs out sideways, a swipe over a card changes nothing, − and + do, a refused action shows the
page's hint, a switched-on function shows as a chip, and every settings section fits.

Needs Playwright and Google Chrome (installed on GitHub's runners); without them the test is skipped. The browser runs
in its own process (tests/panel_page.py).
"""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys

from homeassistant.core import HomeAssistant
import pytest

from custom_components.proxon_control import panel as P

from .test_integration import setup

pytest.importorskip("playwright")
CHROME = any(Path(p).exists() for p in ("/Applications/Google Chrome.app", "/opt/google/chrome/chrome")) or shutil.which("google-chrome")
pytestmark = pytest.mark.skipif(not CHROME, reason="Google Chrome is not installed")
HERE = Path(__file__).parent


def _browse(data: dict, tmp: Path) -> dict:
    (tmp / "input.json").write_text(json.dumps(data), encoding="utf-8")
    done = subprocess.run([sys.executable, str(HERE / "panel_page.py"), str(tmp / "input.json")],  # noqa: S603 - our own script
                          capture_output=True, text=True, timeout=120, check=False)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@pytest.mark.timeout(180)
async def test_page_in_a_browser(hass: HomeAssistant, device, tmp_path: Path) -> None:
    entry = await setup(hass)
    config = {**P.panel_config(hass, entry), "version": "test"}
    states = {s.entity_id: {"entity_id": s.entity_id, "state": s.state, "attributes": dict(s.attributes)} for s in hass.states.async_all()}
    data = json.loads(json.dumps({"config": config, "states": states, "script": str(P.FRONTEND_DIR / "proxon-panel.js")}, default=str))
    result = await hass.async_add_executor_job(_browse, data, tmp_path)

    for width, r in result.items():
        assert r["errors"] == [], f"{width}: errors in the page"
        assert r["overflow_home"] <= 0, f"{width}: the home page runs out sideways"
        assert r["sliders"] == 0, f"{width}: a slider is back"
        grid, temps, in_picture = r["unit_temps"]
        assert all(v.endswith("°") for v in temps) and len(temps) == 4, f"{width}: {r['unit_temps']}"
        assert (grid, in_picture) == (("grid", "none") if width == "phone" else ("none", "block")), f"{width}: {r['unit_temps']}"
        assert r["calls_after_swipes"] == [], f"{width}: a swipe over a card changed a value"
        step = r["water_step"]
        assert not step["sheet_open"], f"{width}: + opened the sheet"
        assert [c[:2] for c in step["calls"]] == [["number", "set_value"]], f"{width}: two taps are sent once: {step['calls']}"
        assert float(step["calls"][0][2]["value"]) == float(step["before"].rstrip("°")) + 2
        assert r["toast"] == [False, "Sensor fehlt"], f"{width}: a refused action shows the page's hint"
        lv = r["level"]
        assert lv["buttons"] == 4, f"{width}: the fan level has four buttons"
        assert r["level_eco"], f"{width}: in ECO comfort mode the unit chooses the level (buttons disabled)"
        assert not lv["auto"], f"{width}: in another mode the level can be chosen"
        assert [c[:2] + [c[2]["value"]] for c in lv["calls"]] == [["number", "set_value", lv["chosen"]]], f"{width}: {lv}"
        assert any(c.startswith("Legionellenschutz") for c in r["chips"]), f"{width}: no chip for a switched-on function"
        assert r["chip_opens"] == ["settings", "auto"]
        assert {"vent", "water", "auto", "coolrel"} <= set(r["sections"])
        en = r["energy"]
        assert en["shown"] and en["parts"] == ["comp", "vent", "water"] and en["overflow"] <= 0, f"{width}: energy tab {en}"
        assert en["week"][0] == 7 and en["week"][1].endswith("kWh") and en["week"][2], f"{width}: a column per weekday {en}"
        assert 28 <= en["month"][0] <= 31 and en["year"][0] == 12, f"{width}: a column per day / month {en}"
        title, empty, no_further = r["energy_empty_year"]
        assert int(title) == datetime.now().year - 1 and not empty and no_further, f"{width}: a year without statistics"
        total, key, filled = r["energy_year"]
        # each counter rose 120.5 kWh (January and June): compressor, ventilation, hot water (heat pump + heater) = 4 x 120.5
        assert total.startswith("482") and "Warmwasser (geschätzt) 241 kWh" in key and filled == 2, f"{width}: {r['energy_year']}"
        tz = r["energy_tz"]
        assert tz["cols"][0] == 1 and tz["cols"][1] == 1 and sum(tz["cols"][2:]) == 0, f"{width}: rows by HA's days {tz}"
        assert tz["total"].startswith("14") and "2,00" in tz["sub"], f"{width}: cost of its time + fixed price before {tz}"
        csv = r["energy_csv"]
        lines = csv["text"].lstrip("\ufeff").splitlines()
        assert csv["name"].startswith("proxon-energie-") and csv["name"].endswith(".csv"), f"{width}: {csv}"
        assert lines[0].startswith("Datum;Kompressor") and lines[0].endswith("Summe (kWh)") and len(lines) == 8, f"{width}: {lines}"
        assert lines[1].split(";")[1] == "10,000" and lines[2].split(";")[-1] == "4,000", f"{width}: a day's kWh {lines}"
        failed_shown, empty_hidden, prev_disabled = r["energy_failed"]
        assert not failed_shown and empty_hidden and not prev_disabled, f"{width}: a failed query {r['energy_failed']}"
        assert any("@" in tag for tag in r["energy_tags"]), f"{width}: the running period is fetched per hour {r['energy_tags']}"
        assert r["cost_none"]["hint"], f"{width}: no price, no costs: a hint"
        c = r["cost"]
        assert not c["hint"] and len(c["rows"]) == 4, f"{width}: costs so far {c}"
        assert c["today"] == 4 and "1,00" in c["rows"][0], f"{width}: today 4 kWh x 25 ct = 1,00 € {c}"
        soft = r["soft"]
        assert soft["on"] and soft["backdrop"] == "none" and soft["card"] in ("none", "") and soft["overflow"] <= 0, f"{width}: soft {soft}"
        assert r["glass_again"] is False
        csv = r["energy_csv_cmp"]
        assert csv[0].endswith(";Summe (kWh);Vorwoche (kWh)") and csv[1].endswith(";10,000;5,000") and csv[2].endswith(";4,000;5,000"), csv
        assert r["water_gap"] < 40, f"{width}: empty strip below the hot-water target ({r['water_gap']} px)"
        assert r["cool_chip"] and "freigegeben" in r["cool_chip"][0], r["cool_chip"]
        kl = r["key_lock"]
        assert kl["shown"] >= 1 and kl["lit"] == 1 and kl["line"] == "An" and not kl["switch"], kl
        av = r["auto_view"]
        assert av["groups"] == ["Warmwasser", "Heizen & Kühlen"] and av["showerInWater"] and not av["showerInAuto"], av
        assert av["autos"][:5] == ["boost", "solar", "price", "legsun", "legplan"] and av["autos"].index("legplan") < av["autos"].index("heatlock") and "shower" not in av["autos"], av
        assert av["jump"] and av["opened"] == "true" and av["page"], av
        assert "von" not in av["summary"] and av["summary"], av
        assert av["tags"] == 0 and av["switches"] == len(av["autos"]), av
        assert r["targets"] and not any(x.endswith(",0°") for x in r["targets"]), r["targets"]
        assert r["diagram_box"] == ("48 28 624 304" if width == "phone" else "0 0 720 360"), r["diagram_box"]
        to = r["tiles_opts"]
        assert to["display"] == "grid" and to["width"] == "212px" and to["accent"] == "#1f6fb2" and to["overflow"] <= 0, to
        assert "Duschen bei 38 °C" in to["shower"], to
        cmp = r["energy_cmp"]
        assert cmp["pressed"] == "true" and "+40 % (+1,00\xa0€) gegenüber Vorwoche" in cmp["sub"] and cmp["marks"] == 2, cmp
        assert cmp["head"] == ["", "Summe", "Ø Tag", "Min.", "Max."] and cmp["total"] == ["Gesamt", "14,0", "2,00", "0,00 Mi", "10,0 Mo"], cmp
        assert r["energy_cmp_off"] == [0, False], r["energy_cmp_off"]
        assert r["shower_card"] == ["Duschvorrat", "0 Min.", "Mehr"], f"{width}: {r['shower_card']}"
        assert r["shower_calls"] == [["number", "set_value", {"entity_id": r["shower_ids"][0], "value": 35}]], r["shower_calls"]
        assert r["temp_card"] == ["Soll", "34°", "Wärmer"], f"{width}: {r['temp_card']}"
        esc = r["escaped"]
        assert esc["found"] == [0, 0, 0] and esc["img"] == 0 and esc["xss"] == 0, f"{width}: markup from an entity name ran {esc}"
        tl = r["tiles"]
        assert tl["on"] and tl["hero"] == "Filter wechseln."  # the test unit: filter change in 5 days and tl["heroShown"] == "grid" and tl["font"], f"{width}: tile wall {tl}"
        assert tl["unit"] == "grid" and tl["picture"] == "none" and tl["tint"].startswith("color-mix"), f"{width}: {tl}"
        assert tl["before"] == [False, "none"] and tl["opened"] == [True, "block", True] and tl["details"], f"{width}: tap opens {tl}"
        assert tl["closed"] == [False, True], f"{width}: a second tap closes the tile again {tl}"
        assert tl["overflow"] <= 0, f"{width}: the tile wall runs out sideways {tl}"
        for sec, s in r["settings"].items():
            assert s["shown"] and s["rows"], f"{width}/{sec}: the section is empty"
            assert s["overflow"] <= 0 and s["rows_out"] == 0, f"{width}/{sec}: runs out sideways: {s}"
            assert s["items_out"] == 0, f"{width}/{sec}: the list is wider than its column: {s}"
