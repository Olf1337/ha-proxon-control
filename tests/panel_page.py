"""Drives the "Proxon" page in a real browser (Chrome through Playwright) for tests/test_panel_page.py.

Run as its own process (the Home Assistant test harness blocks sockets and threads that a browser needs):
    python tests/panel_page.py input.json
input.json holds the page's configuration, the entity states of a set-up test unit and the path of the script. The page
gets a stand-in for Home Assistant's `hass` object that records every action. The findings are printed as JSON; the test
decides what is right.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

HARNESS = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>html, body { margin: 0; }</style></head><body></body></html>"""

# a stand-in for Home Assistant: the states, a record of actions, and the hooks the page uses
BOOT = """([config, states, narrow]) => {
  window.calls = []; window.reject = {};
  const hass = {
    states, language: "de", themes: { darkMode: false }, user: { is_admin: true },
    callService: async (domain, service, data) => {
      window.calls.push([domain, service, data]);
      const why = window.reject[`${domain}.${service}:${data.entity_id}`];
      if (why) throw why;
    },
    formatEntityState: (st, s) => s ?? st.state,
    config: { currency: "EUR" },
    callWS: async msg => { window.ws.push(msg); return window.wsAnswer ? window.wsAnswer(msg) : {}; },
  };
  window.ws = [];
  window.hassFake = hass;
  const el = document.createElement("proxon-panel");
  el.narrow = narrow; el.panel = { config }; el.hass = hass;
  document.body.appendChild(el);
  window.panel = el;
}"""


def run(data: dict) -> dict:
    out: dict = {}
    script = Path(data["script"]).read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        try:
            for name, size, narrow in (("phone", {"width": 375, "height": 812}, True), ("wide", {"width": 1100, "height": 800}, False)):
                page = browser.new_page(viewport=size, has_touch=narrow)
                errors: list[str] = []
                page.on("pageerror", lambda e, errors=errors: errors.append(str(e)))
                page.on("console", lambda m, errors=errors: errors.append(m.text) if m.type == "error" else None)
                page.set_content(HARNESS)
                page.add_script_tag(content=script)
                page.evaluate(BOOT, [data["config"], data["states"], narrow])
                page.wait_for_timeout(300)
                out[name] = check(page, data)
                out[name]["errors"] = errors
                page.close()
        finally:
            browser.close()
    return out


def check(page, data: dict) -> dict:
    r: dict = {}
    js = lambda code, arg=None: page.evaluate(code, arg)  # noqa: E731
    root = "window.panel.shadowRoot"
    r["overflow_home"] = js("() => Math.max(document.documentElement.scrollWidth, window.panel.scrollWidth) - innerWidth")
    r["sliders"] = js(f"() => {root}.querySelectorAll('.slider, input[type=range]').length")

    # a sideways swipe over the hot-water card and a room tile changes nothing
    for sel in ("#water", ".room"):
        box = js(f"(s) => {{ const e = {root}.querySelector(s); e.scrollIntoView({{block: 'center'}}); const b = e.getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; }}", sel)
        x, y = box[0] + box[2] * 0.2, box[1] + box[3] * 0.4
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + box[2] * 0.6, y + 6, steps=8)
        page.mouse.up()
    page.wait_for_timeout(900)
    r["calls_after_swipes"] = [c for c in js("() => window.calls") if c[1] in ("set_value", "set_temperature")]
    js(f"() => {root}.getElementById('sheet').hidden || window.panel._closeSheet()")
    page.wait_for_timeout(400)

    # + on the hot-water card: one degree more, sent once after the taps
    js("() => { window.calls = []; }")
    before = js(f"() => {root}.getElementById('w-target').textContent")
    js(f"() => {{ const b = {root}.getElementById('w-up'); b.click(); b.click(); }}")
    page.wait_for_timeout(900)
    r["water_step"] = {"before": before, "after": js(f"() => {root}.getElementById('w-target').textContent"),
                       "calls": js("() => window.calls"), "sheet_open": js(f"() => !{root}.getElementById('sheet').hidden")}

    # a refused action shows the page's own hint
    sw = data["config"]["entities"].get("SolarWarmwasser")
    if sw:
        js("(e) => { window.reject['switch.turn_on:' + e] = { message: 'Sensor fehlt' }; window.panel._toggle('SolarWarmwasser'); }", sw)
        page.wait_for_timeout(400)
        r["toast"] = js(f"() => [{root}.getElementById('toast').hidden, {root}.getElementById('toast-text').textContent]")

    # the fan level: four buttons, a tap sends that level (disabled while the unit chooses it itself)
    js(f"() => {{ window.calls = []; window.panel._sheetVentilation({root}.getElementById('unit')); }}")
    page.wait_for_timeout(500)
    r["level_eco"] = js(f"() => [...{root}.querySelectorAll('#level button')].every(b => b.disabled)")
    # another mode than ECO comfort: the level is chosen by hand
    mode = data["config"]["entities"].get("Betriebsart")
    js("""(e) => { const h = window.hassFake, st = h.states[e]; const other = (st.attributes.options || []).find(o => o !== 'eco_comfort' && o !== st.state);
                   h.states = { ...h.states, [e]: { ...st, state: other } }; window.panel.hass = { ...h }; }""", mode)
    page.wait_for_timeout(300)
    r["level"] = js(f"""() => {{
      const b = [...{root}.querySelectorAll('#level button')];
      const free = b.find(x => !x.disabled && x.getAttribute('aria-pressed') !== 'true');
      if (free) free.click();
      return {{ buttons: b.length, auto: b.every(x => x.disabled), chosen: free ? +free.dataset.n : null }};
    }}""")
    page.wait_for_timeout(300)
    r["level"]["calls"] = js("() => window.calls")
    js("() => window.panel._closeSheet()")
    page.wait_for_timeout(400)

    # a switched-on function: a chip in the status row that opens its settings
    leg = data["config"]["entities"].get("LegionellenGeplant")
    if leg:
        js("""(e) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], state: 'on' } }; window.panel.hass = { ...h }; }""", leg)
        page.wait_for_timeout(500)
        r["chips"] = js(f"() => [...{root}.querySelectorAll('#status .fchip')].map(c => c.getAttribute('aria-label'))")
        js(f"() => {root}.querySelector('#status .fchip').click()")
        page.wait_for_timeout(600)
        r["chip_opens"] = js("() => [window.panel._current, window.panel._section]")

    # energy: stacked columns per day (week, month) or month (year); earlier periods from Home Assistant's statistics
    js(f"() => {root}.getElementById('tab-energy').click()")
    page.wait_for_timeout(500)
    cols = f"() => [{root}.querySelectorAll('.e-col').length, {root}.getElementById('e-total').textContent, {root}.getElementById('e-empty').hidden]"
    r["energy"] = {"shown": js(f"() => !{root}.getElementById('v-energy').hidden"), "parts": js("() => window.panel._eParts().map(p => p.k)"),
                   "week": js(cols), "overflow": js("() => Math.max(document.documentElement.scrollWidth, window.panel.scrollWidth) - innerWidth")}
    for per in ("month", "year"):
        js(f"(p) => {root}.querySelector(`#e-per button[data-p='${{p}}']`).click()", per)
        page.wait_for_timeout(300)
        r["energy"][per] = js(cols)
    # the year before: without statistics empty (and no further back), with rows their sum
    js(f"() => {root}.getElementById('e-prev').click()")
    page.wait_for_timeout(300)
    r["energy_empty_year"] = js(f"() => [{root}.getElementById('e-title').textContent, {root}.getElementById('e-empty').hidden, {root}.getElementById('e-prev').disabled]")
    js("""() => {
      const y = new Date().getFullYear() - 1;
      window.wsAnswer = msg => Object.fromEntries(msg.statistic_ids.map(id => [id, [{ start: new Date(y, 0, 1).getTime(), change: 100 },
        { start: new Date(y, 5, 1).getTime(), change: 20.5 }]]));
      window.panel._eStats = {}; window.panel._updateEnergy();
    }""")
    page.wait_for_timeout(300)
    r["energy_year"] = js(f"""() => [{root}.getElementById('e-total').textContent, {root}.getElementById('e-key').textContent,
      [...{root}.querySelectorAll('.e-col')].filter(c => c.children.length).length]""")
    js(f"() => {{ window.wsAnswer = null; {root}.querySelector('#e-per button[data-p=week]').click(); }}")
    page.wait_for_timeout(300)

    # settings: every section; the list stays in its column, nothing runs out sideways
    js(f"() => {root}.getElementById('tab-settings').click()")
    page.wait_for_timeout(400)
    sections = js(f"() => [...{root}.querySelectorAll('.sa-item')].map(b => b.dataset.p)")
    r["sections"] = sections
    r["settings"] = {}
    for sec in sections:
        js(f"(s) => {{ window.panel._closeSection(); {root}.querySelector(`.sa-item[data-p='${{s}}']`).click(); }}", sec)
        page.wait_for_timeout(450)
        r["settings"][sec] = js(f"""() => {{
          const r = {root}, list = r.querySelector('.sa-list').getBoundingClientRect(), page = r.getElementById('page-' + window.panel._section);
          const items = [...r.querySelectorAll('.sa-item')].map(i => i.getBoundingClientRect()).filter(b => b.width);
          const rows = [...page.querySelectorAll('.row, .day, .auto-head')].map(e => e.getBoundingClientRect()).filter(b => b.width);
          return {{
            overflow: Math.max(document.documentElement.scrollWidth, window.panel.scrollWidth) - innerWidth,
            items_out: items.filter(b => b.right > list.right + 1).length,
            rows_out: rows.filter(b => b.right > innerWidth + 1 || b.left < -1).length,
            rows: rows.length, shown: !page.hidden && page.getBoundingClientRect().width > 0,
            wide: [...r.querySelectorAll('*')].filter(e => !e.closest('.backdrop') && e.getBoundingClientRect().right > innerWidth + 1)
              .slice(0, 5).map(e => `${{e.tagName}}.${{e.className}}#${{e.id}}`),  // what sticks out, for the message
          }};
        }}""")
    return r


if __name__ == "__main__":
    print(json.dumps(run(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))))
