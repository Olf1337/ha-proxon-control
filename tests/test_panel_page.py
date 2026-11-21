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
        assert {"vent", "water", "auto"} <= set(r["sections"])
        en = r["energy"]
        assert en["shown"] and en["parts"] == ["comp", "vent", "water"] and en["overflow"] <= 0, f"{width}: energy tab {en}"
        assert en["week"][0] == 7 and en["week"][1].endswith("kWh") and en["week"][2], f"{width}: a column per weekday {en}"
        assert 28 <= en["month"][0] <= 31 and en["year"][0] == 12, f"{width}: a column per day / month {en}"
        title, empty, no_further = r["energy_empty_year"]
        assert int(title) == datetime.now().year - 1 and not empty and no_further, f"{width}: a year without statistics"
        total, key, filled = r["energy_year"]
        # each counter rose 120.5 kWh (January and June): compressor, ventilation, hot water (heat pump + heater) = 4 x 120.5
        assert total.startswith("482") and "Warmwasser (geschätzt) 241 kWh" in key and filled == 2, f"{width}: {r['energy_year']}"
        assert r["cost_none"]["hint"], f"{width}: no price, no costs: a hint"
        c = r["cost"]
        assert not c["hint"] and len(c["rows"]) == 4, f"{width}: costs so far {c}"
        assert c["today"] == 4 and "1,00" in c["rows"][0], f"{width}: today 4 kWh x 25 ct = 1,00 € {c}"
        for sec, s in r["settings"].items():
            assert s["shown"] and s["rows"], f"{width}/{sec}: the section is empty"
            assert s["overflow"] <= 0 and s["rows_out"] == 0, f"{width}/{sec}: runs out sideways: {s}"
            assert s["items_out"] == 0, f"{width}/{sec}: the list is wider than its column: {s}"
