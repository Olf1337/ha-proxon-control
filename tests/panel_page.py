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
    # the four air temperatures: in the picture on wide screens, large below it on a phone
    r["unit_temps"] = js(f"""() => [getComputedStyle({root}.querySelector('.unit-temps')).display,
      [...{root}.querySelectorAll('.unit-temps b')].map(b => b.textContent), getComputedStyle({root}.getElementById('v-fresh')).display]""")

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
    # Home Assistant's time zone, not the browser's (Kiritimati, UTC+14, no daylight saving): last week's Monday row lands on
    # Monday; Monday had a cost sensor (1,00 €), Tuesday not yet (4 kWh at the fixed 25 ct = 1,00 €)
    js("""() => {
      const h = window.hassFake; h.config = { currency: 'EUR', time_zone: 'Pacific/Kiritimati' }; window.panel.hass = { ...h };
      window.panel._config.price = 25; window.panel._config.entities.Stromkosten = 'sensor.test_cost';
      const k = new Date(Date.now() + 14 * 3600e3), back = (k.getUTCDay() + 6) % 7 + 7;
      const mon = Date.UTC(k.getUTCFullYear(), k.getUTCMonth(), k.getUTCDate() - back) - 14 * 3600e3, tue = mon + 86400e3;
      const E = window.panel._config.entities;
      window.wsAnswer = msg => ({ [E.EnergieKompressor]: [{ start: mon, change: 10 }, { start: tue, change: 4 }],
        [E.EnergieGesamt]: [{ start: mon, change: 10 }, { start: tue, change: 4 }], 'sensor.test_cost': [{ start: mon, change: 1 }] });
      window.panel._eStats = {}; window.panel._eOff = -1; window.panel._updateEnergy();
    }""")
    page.wait_for_timeout(300)
    r["energy_tz"] = js(f"""() => ({{ cols: [...{root}.querySelectorAll('.e-col')].map(c => c.children.length), total: {root}.getElementById('e-total').textContent,
      sub: {root}.getElementById('e-sub').textContent }})""")
    # the shown period as a CSV download: one row per day, kWh per part and the total (German: ";" and a decimal comma)
    r["energy_csv"] = js(f"""async () => {{
      let blob = null, name = null; const make = URL.createObjectURL, click = HTMLAnchorElement.prototype.click;
      URL.createObjectURL = b => {{ blob = b; return 'blob:test'; }}; HTMLAnchorElement.prototype.click = function () {{ name = this.download; }};
      {root}.getElementById('e-csv').click();
      URL.createObjectURL = make; HTMLAnchorElement.prototype.click = click;
      return {{ name, text: blob ? await blob.text() : null }};
    }}""")
    # compared with the week before: a mark per column, the difference over finished days; the period as a table
    r["energy_cmp"] = js(f"""() => {{
      const E = window.panel._config.entities, shown = window.panel._ePeriod().start.getTime();
      window.wsAnswer = msg => {{ const s = new Date(msg.start_time).getTime(), mine = s === shown, day = 86400e3;
        return {{ [E.EnergieKompressor]: [{{ start: s + 3600e3, change: mine ? 10 : 5 }}, {{ start: s + day + 3600e3, change: mine ? 4 : 5 }}] }}; }};
      window.panel._eStats = {{}}; {root}.getElementById('e-cmp').click();
      return null;
    }}""")
    page.wait_for_timeout(400)
    r["energy_cmp"] = js(f"""() => ({{ pressed: {root}.getElementById('e-cmp').getAttribute('aria-pressed'), sub: {root}.getElementById('e-sub').textContent,
      marks: {root}.querySelectorAll('.e-pm').length, head: [...{root}.querySelectorAll('.e-tbl th')].map(x => x.textContent),
      total: [...{root}.querySelectorAll('.e-tbl tr.sum td')].map(x => [...x.childNodes].map(n => n.textContent).join(' ').trim()) }})""")
    r["energy_csv_cmp"] = js(f"""async () => {{
      let blob = null; const make = URL.createObjectURL, click = HTMLAnchorElement.prototype.click;
      URL.createObjectURL = b => {{ blob = b; return 'blob:test'; }}; HTMLAnchorElement.prototype.click = function () {{}};
      {root}.getElementById('e-csv').click();
      URL.createObjectURL = make; HTMLAnchorElement.prototype.click = click;
      return blob ? (await blob.text()).split('\\r\\n').slice(0, 3) : null;
    }}""")
    js(f"() => {{ {root}.getElementById('e-cmp').click(); }}")
    page.wait_for_timeout(200)
    r["energy_cmp_off"] = js(f"() => [{root}.querySelectorAll('.e-pm').length, {root}.getElementById('e-sub').textContent.includes('Vorwoche')]")
    # a failed query: said so, not "no values", and earlier periods stay reachable; tried again later
    js("() => { window.wsAnswer = () => { throw new Error('recorder down'); }; window.panel._eStats = {}; window.panel._updateEnergy(); }")
    page.wait_for_timeout(300)
    r["energy_failed"] = js(f"() => [{root}.getElementById('e-failed').hidden, {root}.getElementById('e-empty').hidden, {root}.getElementById('e-prev').disabled]")
    # the running period is fetched again every hour (its finished days change after midnight)
    js("() => { window.wsAnswer = null; window.panel._eOff = 0; window.panel._eStats = {}; window.panel._updateEnergy(); }")
    page.wait_for_timeout(200)
    r["energy_tags"] = js("() => Object.keys(window.panel._eStats)")
    js("""() => { const h = window.hassFake; h.config = { currency: 'EUR' }; delete window.panel._config.entities.Stromkosten;
                  window.panel._config.price = null; window.panel.hass = { ...h }; }""")
    page.wait_for_timeout(200)
    # costs: without a price a hint; with a fixed price (25 ct/kWh) so far and expected, worked out from the consumption
    cost = f"""() => ({{ hint: !{root}.getElementById('e-cost-none').hidden, rows: [...{root}.querySelectorAll('#e-cost-run .e-run')].map(r => r.innerText),
      today: window.panel._eSum(['EnergieGesamt'], 'Heute') }})"""
    r["cost_none"] = js(cost)
    today = data["config"]["entities"]["EnergieGesamtHeute"]
    js("""(e) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], state: '4.0' } }; window.panel.hass = { ...h };
                   window.panel._config.price = 25; window.panel._updateEnergy(); }""", today)
    page.wait_for_timeout(200)
    r["cost"] = js(cost)
    js("() => { window.panel._config.price = null; window.panel._updateEnergy(); }")
    page.wait_for_timeout(300)

    # the look "Soft" (option): set on the page, the glass backdrop gone, nothing runs out sideways
    js("() => { window.panel._config.look = 'soft'; window.panel.hass = { ...window.hassFake }; }")
    page.wait_for_timeout(200)
    r["soft"] = js(f"""() => ({{ on: window.panel.hasAttribute('softui'), backdrop: getComputedStyle({root}.querySelector('.backdrop')).display,
      card: getComputedStyle({root}.querySelector('.card')).backdropFilter, overflow: Math.max(document.documentElement.scrollWidth, window.panel.scrollWidth) - innerWidth }})""")
    js("() => { window.panel._config.look = 'glass'; window.panel.hass = { ...window.hassFake }; }")
    page.wait_for_timeout(200)
    r["glass_again"] = js("() => window.panel.hasAttribute('softui')")

    # the look "Tile wall": the headline says whether everything runs, the unit as four tiles, a tap on a room opens it (- and +),
    # a second tap its details; the font comes from the integration's own files
    js(f"""() => {{ window.panel._config.look = 'tiles'; window.panel._config.static = '/proxon_control_static'; window.panel.hass = {{ ...window.hassFake }};
      {root}.getElementById('tab-home').click(); }}""")
    page.wait_for_timeout(300)
    r["tiles"] = js(f"""() => {{
      const room = {root}.querySelector('.rooms > .room'), sheet = {root}.getElementById('sheet');
      const before = [room.classList.contains('open'), getComputedStyle(room.querySelector('.rs-btn')).display];
      room.click();
      const opened = [room.classList.contains('open'), getComputedStyle(room.querySelector('.rs-btn')).display, sheet.hidden];
      room.querySelector('.room-temp').click();
      const closed = [room.classList.contains('open'), sheet.hidden];
      room.click(); room.querySelector('.room-name .nm').click();
      const details = !sheet.hidden; window.panel._closeSheet();
      return {{ on: window.panel.hasAttribute('tiles'), hero: {root}.getElementById('hero-h').textContent,
        heroShown: getComputedStyle({root}.getElementById('hero')).display, unit: getComputedStyle({root}.querySelector('.unit-temps')).display,
        picture: getComputedStyle({root}.querySelector('svg.diagram')).display, tint: room.style.getPropertyValue('--rt'), before, opened, closed, details,
        font: [...document.querySelectorAll('style')].some(x => x.textContent.includes('/proxon_control_static/fonts/antonio-latin.woff2')),
        overflow: Math.max(document.documentElement.scrollWidth, window.panel.scrollWidth) - innerWidth }};
    }}""")
    # the tile wall's options: all rooms in a grid, large tiles, a blue accent; the shower counted as set under Configure
    r["tiles_opts"] = js(f"""() => {{
      window.panel._config.tiles = {{ layout: 'grid', size: 'large', accent: 'blue' }}; window.panel._config.shower = {{ temp: 38, flow: 6 }};
      window.panel.hass = {{ ...window.hassFake }};
      const rooms = {root}.querySelector('.rooms'), cs = getComputedStyle(window.panel);
      return {{ display: getComputedStyle(rooms).display, width: cs.getPropertyValue('--tile-w').trim(), accent: cs.getPropertyValue('--accent').trim(),
        shower: {root}.getElementById('w-shower-wrap').textContent,
        overflow: Math.max(document.documentElement.scrollWidth, window.panel.scrollWidth) - innerWidth }};
    }}""")
    js("() => { window.panel._config.tiles = null; window.panel._config.shower = null; window.panel._config.look = 'glass'; window.panel.hass = { ...window.hassFake }; }")
    page.wait_for_timeout(200)

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
    # next to the taller ventilation card the hot-water card has no empty strip below its target (wide screens)
    r["water_gap"] = js(f"""() => {{ const w = {root}.getElementById('water'), set = {root}.getElementById('w-set-wrap');
      return Math.round(w.getBoundingClientRect().bottom - set.getBoundingClientRect().bottom); }}""")
    # cooling: a section with the release switch and its function chip while it is released; cooling with solar in the automations
    cool = data["config"]["entities"].get("GlobalKuehlungFreigabe")
    if cool:
        js("""(e) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], state: 'on' } }; window.panel.hass = { ...h }; }""", cool)
        page.wait_for_timeout(300)
        r["cool_chip"] = js(f"() => [...{root}.querySelectorAll('.fchip, .fn')].map(x => x.textContent.replace(/\\s+/g, ' ').trim()).filter(x => x.includes('Kühlung'))")
        js("""(e) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], state: 'off' } }; window.panel.hass = { ...h }; }""", cool)
        page.wait_for_timeout(200)
    # a room's key lock: a small lock in its tile (lit while locked) and a line in its sheet - shown, not switched
    lock_room = next((k[3:-12] for k in data["config"]["entities"] if k.startswith("NBE") and k.endswith("Tastensperre")), None)
    if lock_room:
        lid = data["config"]["entities"][f"NBE{lock_room}Tastensperre"]
        js("""(e) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], state: 'on' } }; window.panel.hass = { ...h }; }""", lid)
        page.wait_for_timeout(200)
        r["key_lock"] = js(f"""() => {{ const locks = [...{root}.querySelectorAll('.room .lock')].filter(l => !l.hidden);
          window.panel._sheetRoom({lock_room}, null); const line = {root}.getElementById('r-lock').textContent; window.panel._closeSheet();
          return {{ shown: locks.length, lit: locks.filter(l => l.classList.contains('on')).length, line, switch: !!{root}.getElementById('s-lock') }}; }}""")
        js("""(e) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], state: 'off' } }; window.panel.hass = { ...h }; }""", lid)
        page.wait_for_timeout(200)

    # the hot-water card: what really heats now (the T300 relays) while no automation heats
    relays = data["config"]["entities"]
    if "T300RelaisKompressor" in relays and "T300RelaisHeizstab" in relays:
        set_state = """([e, v]) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], state: v } }; window.panel.hass = { ...h }; }"""
        said = f"() => {root}.getElementById('w-working').hidden ? null : {root}.getElementById('w-who').textContent"
        r["relay"] = []
        for pump, heater in (("on", "off"), ("off", "on"), ("off", "off")):
            js(set_state, [relays["T300RelaisKompressor"], pump])
            js(set_state, [relays["T300RelaisHeizstab"], heater])
            page.wait_for_timeout(150)
            r["relay"].append(js(said))

    # the hot-water card: the litres warmer than the shower (from the shower supply's attribute), else from the charge
    sm = data["config"]["entities"].get("WarmwasserDuschminuten")
    if sm:
        attrs = """([e, a]) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], attributes: { ...h.states[e].attributes, ...a } } }; window.panel.hass = { ...h }; }"""
        liters = f"() => [{root}.getElementById('w-liters').textContent, {root}.getElementById('w-liters-sub').textContent]"
        js(attrs, [sm, {"hot_liters": 75}])
        page.wait_for_timeout(150)
        r["hot_liters"] = [js(liters)]
        js(attrs, [sm, {"hot_liters": None}])
        page.wait_for_timeout(150)
        r["hot_liters"].append(js(liters))

    # the settings: automations in two groups, the shower supply in "Hot water", the cooling section jumps to its automations
    js(f"() => {root}.getElementById('tab-settings').click()")
    page.wait_for_timeout(300)
    r["auto_view"] = js(f"""() => {{ const p = window.panel, q = s => {root}.querySelector(s);
      const groups = [...{root}.querySelectorAll('#page-auto .auto-group')].map(h => h.textContent);
      const autos = [...{root}.querySelectorAll('#page-auto .auto-head')].map(h => h.id.slice(3));
      const showerInWater = !!q('#page-water #set-DuschvorratModus'), showerInAuto = !!q('#page-auto #set-DuschvorratModus');
      const summary = {root}.getElementById('navsum-auto').textContent;
      const tags = [...{root}.querySelectorAll('#page-auto .auto-head .tag')].length, switches = [...{root}.querySelectorAll('#page-auto .auto-head .switch')].length;
      p._showSection('coolrel', false); const jump = q('#page-coolrel .jump[data-open="pvcool"]'); if (jump) jump.click();
      const opened = q('#ah-pvcool') ? q('#ah-pvcool').getAttribute('aria-expanded') : null, page = !q('#page-auto').hidden;
      return {{ groups, autos, showerInWater, showerInAuto, summary, jump: !!jump, opened, page, tags, switches }}; }}""")
    js(f"() => {root}.getElementById('tab-home').click()")
    page.wait_for_timeout(200)

    # a room's target: a decimal only where there is one; the unit's picture cropped to the drawing on a phone
    r["targets"] = js(f"() => [...{root}.querySelectorAll('.rooms .tv')].map(x => x.textContent)")
    r["diagram_box"] = js(f"() => {root}.querySelector('svg.diagram').getAttribute('viewBox')")

    # the hot water as a shower supply (switch in the automations): the card's label, value and − / + follow it
    E = data["config"]["entities"]
    if E.get("DuschvorratModus"):
        flip = """([e, on]) => { const h = window.hassFake; h.states = { ...h.states, [e]: { ...h.states[e], state: on } }; window.panel.hass = { ...h }; }"""
        card = f"() => [{root}.getElementById('w-set-t').textContent, {root}.getElementById('w-target').textContent, {root}.getElementById('w-up').getAttribute('aria-label')]"
        js("() => { window.calls = []; }")
        js(flip, [E["DuschvorratModus"], "on"])
        page.wait_for_timeout(200)
        r["shower_card"] = js(card)
        js(f"() => {root}.getElementById('w-up').click()")
        page.wait_for_timeout(900)
        r["shower_calls"] = [c for c in js("() => window.calls") if c[1] == "set_value"]
        js(flip, [E["DuschvorratModus"], "off"])
        page.wait_for_timeout(200)
        r["temp_card"] = js(card)
        r["shower_ids"] = [E["DuschvorratSoll"]]

    # names, options and states come from Home Assistant: anyone who can rename an entity must not get markup into the page
    r["escaped"] = js(f"""() => {{
      const bad = '<img src=x onerror="window.__xss=1">', h = window.hassFake, E = window.panel._config.entities;
      const room = Object.keys(h.states).find(e => e.startsWith('climate.'));
      const sel = E.Betriebsart;
      h.states = Object.fromEntries(Object.entries(h.states).map(([e, st]) => [e, {{ ...st, attributes: {{ ...st.attributes, friendly_name: bad + st.attributes.friendly_name,
        ...(e === sel ? {{ options: [...st.attributes.options, bad] }} : {{}}) }} }}]));
      window.panel.hass = {{ ...h }};
      const found = [];
      window.panel._sheetRoom(0, null); found.push({root}.querySelectorAll('#sheet-body img').length); window.panel._closeSheet();
      window.panel._sheetAll('unit', null); found.push({root}.querySelectorAll('#sheet-body img').length); window.panel._closeSheet();
      window.panel._sheetVentilation(null); found.push({root}.querySelectorAll('#sheet-body img').length); window.panel._closeSheet();
      h.states = Object.fromEntries(Object.entries(h.states).map(([e, st]) => [e, {{ ...st, attributes: {{ ...st.attributes, friendly_name: 'x' + bad }} }}]));
      window.panel.hass = {{ ...h }};
      return {{ found, label: window.panel._label('NichtUebersetzt'), img: {root}.querySelectorAll('img').length, xss: window.__xss || 0, room }};
    }}""")
    page.wait_for_timeout(300)
    r["escaped"]["xss"] = js("() => window.__xss || 0")
    return r


if __name__ == "__main__":
    print(json.dumps(run(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))))
