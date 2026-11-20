// Proxon Control: the "Proxon" page in the sidebar. A web component without a build step and without libraries.
// It reads the unit's entities live from Home Assistant (`hass`) and changes them only through their normal actions.
// Motion follows Apple's fluid-interface rules: springs (damping ratio + response) that start from the value on screen,
// 1:1 dragging with momentum projection and rubber-banding, and no animation at all with "reduce motion".
// The page's configuration (entity IDs by unique-id suffix, rooms with their floor) comes from panel.py.

const TEXT = {
  de: {
    title: "Zuhause", outside: "Außen", op: "Betrieb", ok: "Alles in Ordnung", fault: "Störung", filter: "Filter bald wechseln",
    unit: "Lüftungsanlage", boost: "Intensivlüftung", left: "noch {m} Min.", level: "Stufe", levelBoost: "4 (Intensiv)",
    tapUnit: "antippen zum Einstellen", fresh: "Frischluft", supply: "Zuluft", extract: "Abluft", exhaust: "Fortluft",
    out: "Außen", house: "Haus", fanSupply: "Zuluftlüfter", fanExhaust: "Abluftlüfter", recovery: "Wärmerückgewinnung",
    water: "Warmwasser", shower: "Reicht für ca. {m} Min. Duschen", middle: "Mitte", min: "Min.",
    litersSub: "warmes Wasser im Speicher", showerSub: "Duschen bei 40 °C", bottom: "Unten", target: "Soll", charge: "Ladezustand",
    floors: { "0": "Erdgeschoss", "1": "Obergeschoss", "-1": "Keller" }, rooms: "Räume", sent: "✓ gesendet", allEl: "Wärmeelemente aller Räume", allOn: "{a} von {b} Räumen an",
    allOff: "Wärmeelemente aller Räume aus", allOnDone: "Wärmeelemente aller Räume an",
    element: { off: "Heizpanel aus", ready: "Heizpanel bereit", heating: "Heizpanel heizt" },
    ventilation: "Lüftung", mode: "Betriebsart", boostSub: "läuft {m} Minuten, dann zurück", waterTarget: "Solltemperatur",
    pump: "Wärmepumpe", pumpSub: "heizt das Wasser sparsam", heater: "Heizstab", heaterSub: "schneller, braucht mehr Strom",
    now: "Jetzt", range: "{a} bis {b} °C in {s}-°C-Schritten", released: "Heizpanel freigegeben",
    releasedSub: "heizt elektrisch zu, wenn der Raum zu kalt ist", dragHint: "Auf der Kachel geht es schneller: zur Seite ziehen.",
    more: "Alle Werte", device: "Gerät in Home Assistant öffnen", groups: { temp: "Temperaturen", meas: "Messwerte", state: "Zustände", set: "Einstellungen" },
    close: "Schließen", warmer: "Wärmer", colder: "Kälter", off: "{f} aus", undo: "Rückgängig",
    end: "{f} beenden", unavailable: "nicht erreichbar", home: "Zuhause", settings: "Einstellungen", status: "Status",
    days: ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], phase: "Phase {n}", from: "von", to: "bis", lvl: "Stufe",
    daysShort: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    hint: {
      GrenzwertCO2: "Darüber lüftet die Anlage im ECO-Komfortbetrieb stärker (nur mit CO₂-Fühler).",
      GrenzwertFeuchte: "Darunter lüftet die Anlage im ECO-Komfortbetrieb schwächer, damit die Luft nicht zu trocken wird.",
      LegionellenGeplant: "Heizt jede Woche am gewählten Tag zur gewählten Uhrzeit auf 60 °C, mit oder ohne Sonne.",
      LegionellenSonne: "Heizt einmal pro Woche auf 60 °C, bevorzugt mit Solarüberschuss.",
    },
    copyWeekdays: "Montag → Dienstag bis Freitag", copyAll: "Montag → alle Tage", sure: "Wirklich? Nochmal tippen", empty: "keine Phase",
    s: {
      vent: "Lüftung", schedule: "Wochenprogramm Lüftung", holiday: "Urlaub", water: "Warmwasser", boost: "Warmwasser-Boost",
      store: "PV-Überschuss und günstiger Strom", legionella: "Legionellenschutz", cooling: "Sommer-Nachtkühlung",
      season: "Sommer/Winter automatisch", night: "Nachtabsenkung", heating: "Heizen",
      IntensivlueftungsDauer: "Dauer der Intensivlüftung", GrenzwertCO2: "Grenzwert CO₂", GrenzwertFeuchte: "Grenzwert Feuchte",
      ZeitprogrammAktiv: "Wochenprogramm an", Urlaubsmodus: "Urlaubsmodus", UrlaubAb: "Abreise", UrlaubBis: "Rückkehr",
      UrlaubVorlauf: "Vor der Rückkehr aufwärmen", UrlaubsplanLoeschen: "Urlaubsplan löschen", SollWassertemperatur: "Solltemperatur",
      T300Betriebsart: "Wärmepumpe", "E-Heizstab": "Heizstab freigegeben", "Soll-E-Heizstab-Temperatur": "Heizstab bis",
      Legionellenfunktion: "Legionellenschaltung der Anlage", WarmwasserBoost: "Boost an", BoostGrenze: "Boost unter",
      SolarWarmwasser: "Mit PV-Überschuss heizen", SolarSchwelle: "Überschuss ab", PreisWarmwasser: "Mit günstigem Strom heizen",
      PreisSchwelle: "Strompreis unter", SpeicherTemperatur: "Speichern bis", LegionellenSonne: "Legionellenschutz mit Sonne",
      LegionellenZeit: "Ohne Sonne um", LegionellenGeplant: "Legionellenschutz planen", LegionellenTag: "Tag",
      LegionellenPlanZeit: "Uhrzeit", Nachtkuehlung: "Nachtkühlung an", KuehlWunsch: "Wunschtemperatur innen", KuehlStufe: "Kühlstufe",
      SaisonAutomatik: "Automatisch umschalten", SaisonWinterUnter: "Winter unter", SaisonSommerUeber: "Sommer über",
      NachtabsenkungAktiv: "Nachtabsenkung an", NachtabsenkungTemperatur: "Nachttemperatur", NachtabsenkungStart: "Beginn",
      NachtabsenkungEnde: "Ende", WaermeelementeAlle: "Wärmeelemente aller Räume",
    }, levelAuto: "Im ECO-Komfortbetrieb und während der Intensivlüftung wählt die Anlage die Stufe selbst.",
    fn: {
      holiday: ["Urlaubsmodus", "Lüftung Stufe 1, Räume kühler", "bis {d}"],
      solar: ["PV-Überschuss", "heizt das Warmwasser auf {t} °C"],
      price: ["Günstiger Strom", "heizt das Warmwasser auf {t} °C"],
      boostww: ["Warmwasser-Boost", "Heizstab an, bis {t} °C erreicht sind"],
      legionella: ["Legionellenschutz", "heizt das Warmwasser auf 60 °C"],
      cooling: ["Nachtkühlung", "kühlt mit Stufe {l}"],
    },
  },
  en: {
    title: "Home", outside: "Outside", op: "Mode", ok: "All good", fault: "Fault", filter: "Filter change soon",
    unit: "Ventilation unit", boost: "Boost ventilation", left: "{m} min left", level: "Level", levelBoost: "4 (boost)",
    tapUnit: "tap to adjust", fresh: "Fresh air", supply: "Supply", extract: "Extract", exhaust: "Exhaust",
    out: "Outside", house: "House", fanSupply: "Supply fan", fanExhaust: "Extract fan", recovery: "Heat recovery",
    water: "Hot water", shower: "Enough for about {m} min of showering", middle: "Middle", min: "min",
    litersSub: "of warm water in the tank", showerSub: "of showering at 40 °C", bottom: "Bottom", target: "Target", charge: "Charge",
    floors: { "0": "Ground floor", "1": "Upper floor", "-1": "Basement" }, rooms: "Rooms", sent: "✓ sent", allEl: "Heating elements of all rooms", allOn: "{a} of {b} rooms on",
    allOff: "Heating elements of all rooms off", allOnDone: "Heating elements of all rooms on",
    element: { off: "Heating panel off", ready: "Heating panel ready", heating: "Heating panel heating" },
    ventilation: "Ventilation", mode: "Operating mode", boostSub: "runs {m} minutes, then back", waterTarget: "Target temperature",
    pump: "Heat pump", pumpSub: "heats the water efficiently", heater: "Immersion heater", heaterSub: "faster, uses more power",
    now: "Now", range: "{a} to {b} °C in {s} °C steps", released: "Heating panel enabled",
    releasedSub: "heats electrically when the room is too cold", dragHint: "Quicker on the tile: drag it sideways.",
    more: "All values", device: "Open the device in Home Assistant", groups: { temp: "Temperatures", meas: "Readings", state: "States", set: "Settings" },
    close: "Close", warmer: "Warmer", colder: "Colder", off: "{f} off", undo: "Undo",
    end: "End {f}", unavailable: "unavailable", home: "Home", settings: "Settings", status: "Status",
    days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], phase: "Phase {n}", from: "from", to: "to", lvl: "level",
    daysShort: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    hint: {
      GrenzwertCO2: "Above it the unit ventilates more in ECO comfort mode (only with a CO₂ sensor).",
      GrenzwertFeuchte: "Below it the unit ventilates less in ECO comfort mode, so the air doesn't get too dry.",
      LegionellenGeplant: "Heats to 60 °C every week on the chosen day at the chosen time, sun or not.",
      LegionellenSonne: "Heats to 60 °C once a week, preferably with solar surplus.",
    },
    copyWeekdays: "Monday → Tuesday to Friday", copyAll: "Monday → every day", sure: "Sure? Tap again", empty: "no phase",
    s: {
      vent: "Ventilation", schedule: "Weekly ventilation schedule", holiday: "Holiday", water: "Hot water", boost: "Hot-water boost",
      store: "Solar surplus and cheap power", legionella: "Legionella protection", cooling: "Summer night cooling",
      season: "Summer/winter automatic", night: "Night setback", heating: "Heating",
      IntensivlueftungsDauer: "Boost duration", GrenzwertCO2: "CO₂ limit", GrenzwertFeuchte: "Humidity limit",
      ZeitprogrammAktiv: "Weekly schedule on", Urlaubsmodus: "Holiday mode", UrlaubAb: "Departure", UrlaubBis: "Return",
      UrlaubVorlauf: "Warm up before the return", UrlaubsplanLoeschen: "Clear holiday plan", SollWassertemperatur: "Target temperature",
      T300Betriebsart: "Heat pump", "E-Heizstab": "Immersion heater enabled", "Soll-E-Heizstab-Temperatur": "Heater up to",
      Legionellenfunktion: "Unit's legionella function", WarmwasserBoost: "Boost on", BoostGrenze: "Boost below",
      SolarWarmwasser: "Heat with solar surplus", SolarSchwelle: "Surplus from", PreisWarmwasser: "Heat with cheap power",
      PreisSchwelle: "Price below", SpeicherTemperatur: "Store up to", LegionellenSonne: "Legionella protection with solar",
      LegionellenZeit: "Without sun at", LegionellenGeplant: "Plan legionella protection", LegionellenTag: "Day",
      LegionellenPlanZeit: "Time", Nachtkuehlung: "Night cooling on", KuehlWunsch: "Wanted indoor temperature", KuehlStufe: "Cooling level",
      SaisonAutomatik: "Switch automatically", SaisonWinterUnter: "Winter below", SaisonSommerUeber: "Summer above",
      NachtabsenkungAktiv: "Night setback on", NachtabsenkungTemperatur: "Night temperature", NachtabsenkungStart: "Start",
      NachtabsenkungEnde: "End", WaermeelementeAlle: "Heating elements of all rooms",
    }, levelAuto: "In ECO comfort mode and during boost ventilation the unit chooses the level itself.",
    fn: {
      holiday: ["Holiday mode", "ventilation level 1, rooms cooler", "until {d}"],
      solar: ["Solar surplus", "heating the hot water to {t} °C"],
      price: ["Cheap power", "heating the hot water to {t} °C"],
      boostww: ["Hot-water boost", "heater on until {t} °C"],
      legionella: ["Legionella protection", "heating the hot water to 60 °C"],
      cooling: ["Night cooling", "cooling at level {l}"],
    },
  },
};
const fill = (s, v) => s.replace(/\{(\w)\}/g, (_, k) => (v[k] ?? ""));

// the automatic functions: shown while they run; their switch ends them
const FUNCS = [
  { k: "holiday", sw: "Urlaubsmodus", run: st => st.state === "on", tint: "--fresh",
    icon: "M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M4 7h16v12H4zM9 7v12M15 7v12" },
  { k: "solar", sw: "SolarWarmwasser", run: st => st.attributes.status === "heating_solar", tint: "--supply", temp: "SpeicherTemperatur",
    icon: "M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z" },
  { k: "price", sw: "PreisWarmwasser", run: st => st.attributes.status === "heating_price", tint: "--fine", temp: "SpeicherTemperatur",
    icon: "M12 3v18M17 7.5C17 5.6 14.8 4.5 12 4.5S7 5.7 7 7.6c0 4.8 10 2.6 10 7.8 0 2-2.2 3.1-5 3.1s-5-1.2-5-3.1" },
  { k: "boostww", sw: "WarmwasserBoost", run: st => st.attributes.status === "heating", tint: "--warm", temp: "BoostGrenze",
    icon: "M13 2L4 14h7l-1 8 9-12h-7z" },
  { k: "legionella", sw: "LegionellenStatus", off: ["LegionellenSonne", "LegionellenGeplant"], run: st => String(st.state || "").startsWith("heating"), tint: "--water-hot",
    icon: "M12 3c3 4 6 6.5 6 10a6 6 0 0 1-12 0c0-3.5 3-6 6-10zM10 14a2 2 0 0 0 2 2" },
  { k: "cooling", sw: "Nachtkuehlung", run: st => ["cooling", "heat_protection"].includes(st.attributes.status), tint: "--cold",
    icon: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" },
];

// the settings tab: sections of rows (shown when their entities exist); a status sensor says what the function is doing
const SETTINGS = [
  { id: "vent", rows: [["num", "IntensivlueftungsDauer"], ["num", "GrenzwertCO2"], ["num", "GrenzwertFeuchte"]] },
  { id: "schedule", rows: [["switch", "ZeitprogrammAktiv"], ["days"]] },
  { id: "holiday", rows: [["switch", "Urlaubsmodus"], ["datetime", "UrlaubAb"], ["datetime", "UrlaubBis"], ["num", "UrlaubVorlauf"], ["button", "UrlaubsplanLoeschen"]] },
  { id: "water", rows: [["num", "SollWassertemperatur"], ["switch", "T300Betriebsart"], ["switch", "E-Heizstab"], ["num", "Soll-E-Heizstab-Temperatur"], ["switch", "Legionellenfunktion"]] },
  { id: "boost", status: "BoostStatus", rows: [["switch", "WarmwasserBoost"], ["num", "BoostGrenze"]] },
  { id: "store", status: "Energiemanager", rows: [["switch", "SolarWarmwasser"], ["num", "SolarSchwelle"], ["switch", "PreisWarmwasser"], ["num", "PreisSchwelle"], ["num", "SpeicherTemperatur"]] },
  { id: "legionella", status: "LegionellenStatus", rows: [["switch", "LegionellenSonne"], ["time", "LegionellenZeit"],
    ["switch", "LegionellenGeplant"], ["select", "LegionellenTag"], ["time", "LegionellenPlanZeit"]] },
  { id: "cooling", status: "NachtkuehlungStatus", rows: [["switch", "Nachtkuehlung"], ["num", "KuehlWunsch"], ["num", "KuehlStufe"]] },
  { id: "season", status: "SaisonStatus", rows: [["switch", "SaisonAutomatik"], ["num", "SaisonWinterUnter"], ["num", "SaisonSommerUeber"]] },
  { id: "night", rows: [["switch", "NachtabsenkungAktiv"], ["num", "NachtabsenkungTemperatur"], ["time", "NachtabsenkungStart"], ["time", "NachtabsenkungEnde"]] },
];

// ---------------- springs ----------------
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
const activeSprings = new Set();
let ticking = false, lastFrame = 0;
function frame(t) {
  const dt = Math.min(0.05, (t - lastFrame) / 1000 || 1 / 60); lastFrame = t;
  const n = Math.max(1, Math.ceil(dt / (1 / 240)));
  for (const s of [...activeSprings]) for (let i = 0; i < n && activeSprings.has(s); i++) s.step(dt / n);
  if (activeSprings.size) requestAnimationFrame(frame); else ticking = false;
}
class Spring {
  constructor(x, onUpdate) { this.x = x; this.v = 0; this.target = x; this.onUpdate = onUpdate; this.onRest = null; }
  to(target, { damping = 1, response = 0.35, velocity, onRest } = {}) {
    this.target = target; this.damping = damping; this.response = response; this.onRest = onRest || null;
    if (velocity !== undefined) this.v = velocity;
    if (reduceMotion.matches) { this.set(target); if (onRest) onRest(); return; }
    activeSprings.add(this);
    if (!ticking) { ticking = true; lastFrame = performance.now(); requestAnimationFrame(frame); }
  }
  set(x) { this.x = x; this.v = 0; this.target = x; activeSprings.delete(this); this.onUpdate(x); }
  step(dt) {
    const k = (2 * Math.PI / this.response) ** 2, c = 4 * Math.PI * this.damping / this.response;
    this.v += (-k * (this.x - this.target) - c * this.v) * dt; this.x += this.v * dt;
    if (Math.abs(this.v) < 0.005 && Math.abs(this.x - this.target) < 0.0005) {
      this.x = this.target; this.v = 0; activeSprings.delete(this); this.onUpdate(this.x); if (this.onRest) this.onRest(); return;
    }
    this.onUpdate(this.x);
  }
}
const project = (v, d = 0.998) => (v / 1000) * d / (1 - d);  // Apple's momentum projection
const SETTING = 0.99;  // deceleration for targets and levels: a flick moves a step or two, not to the end
const rubber = (over, dim, c = 0.55) => (over * dim * c) / (dim + c * Math.abs(over));
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

// A value set by dragging sideways (room and hot-water tiles, the sliders in sheets and settings): 1:1 with the finger,
// a rubber band past the ends, a short momentum, a spring into the nearest step, sent when it rests. On a tile the whole
// tile is the handle and a move that starts vertical stays a scroll; on a slider the knob jumps to the finger.
// o: range() -> {min, max, step} or null, value() -> the value to show at rest, show(v, snapped, range) on every frame,
// commit(v), tile (bool).
function dragValue(handle, track, o) {
  let start = null, dragging = false, hist = [], dragged = false, held = false;
  const snap = (v, r) => clamp(Math.round(v / r.step) * r.step, r.min, r.max);
  const pos = new Spring(0, v => { const r = o.range(); if (r) o.show(v, snap(v, r), r); });
  const per = r => track.clientWidth / Math.max(1e-9, r.max - r.min);
  const at = (x, r) => r.min + (x - track.getBoundingClientRect().left) / per(r);
  const settle = (target, velocity) => pos.to(target, { damping: velocity ? 0.8 : 1, response: 0.35, velocity,
    onRest: () => { held = false; o.commit(target); } });
  const band = (v, r) => (v > r.max ? r.max + rubber(v - r.max, (r.max - r.min) * 0.15) : v < r.min ? r.min - rubber(r.min - v, (r.max - r.min) * 0.15) : v);
  handle.addEventListener("pointerdown", e => {
    const r = o.range(); if (!r || (e.button !== undefined && e.button > 0)) return;
    start = { x: e.clientX, y: e.clientY, v: pos.x, id: e.pointerId, moved: false }; hist = [{ x: e.clientX, t: e.timeStamp }];
    if (o.tile) { dragging = false; handle.classList.add("pressed"); return; }
    dragging = true; held = true; try { handle.setPointerCapture(e.pointerId); } catch (_) { /* not a real pointer */ }
    pos.set(band(at(e.clientX, r), r));
  });
  handle.addEventListener("pointermove", e => {
    if (!start || e.pointerId !== start.id) return;
    const r = o.range(); if (!r) return;
    const dx = e.clientX - start.x, dy = e.clientY - start.y;
    if (!dragging) {
      if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) { start = null; handle.classList.remove("pressed"); return; }  // a scroll
      if (Math.abs(dx) < 10) return;
      dragging = true; held = true; handle.classList.remove("pressed"); handle.classList.add("dragging");
      try { handle.setPointerCapture(e.pointerId); } catch (_) { /* not a real pointer */ }
    }
    start.moved = true;
    hist.push({ x: e.clientX, t: e.timeStamp }); if (hist.length > 6) hist.shift();
    pos.set(band(o.tile ? start.v + dx / per(r) : at(e.clientX, r), r));
  });
  const end = () => {
    handle.classList.remove("pressed");
    if (!start) return;
    const r = o.range();
    if (dragging && r) {
      const a = hist[0], b = hist[hist.length - 1], vel = start.moved ? (b.x - a.x) / Math.max(1, b.t - a.t) * 1000 / per(r) : 0;
      // momentum carries at most two steps past where the finger let go: a flick nudges a setting, it never throws it
      const carry = clamp(project(vel * per(r), SETTING) / per(r), -2 * r.step, 2 * r.step);
      settle(snap(pos.x + carry, r), vel ? clamp(vel, -8 * r.step / 0.35, 8 * r.step / 0.35) : undefined);
      handle.classList.remove("dragging");
      if (o.tile) { dragged = true; setTimeout(() => { dragged = false; }, 0); }  // the click that ends a drag opens nothing
    }
    start = null; dragging = false;
  };
  handle.addEventListener("pointerup", end); handle.addEventListener("pointercancel", end);
  // drawn again when the track gets its width (first layout, rotation, a sheet opening)
  if (window.ResizeObserver) new ResizeObserver(() => { if (o.range() && !activeSprings.has(pos)) pos.set(pos.x); }).observe(track);
  handle.addEventListener("keydown", e => {
    const d = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key], r = o.range();
    if (!d || !r) return; e.preventDefault(); held = true;
    settle(snap((activeSprings.has(pos) ? pos.target : o.value()) + d * r.step, r));
  });
  return {
    pos, dragged: () => dragged,
    sync() { if (!held && !activeSprings.has(pos) && o.range()) pos.set(o.value()); },  // follow the entity while untouched
    back(v) { held = false; pos.to(v, { damping: 1, response: 0.35 }); },  // a write that failed: back to what the unit has
  };
}

const STYLE = `
:host {
  --bg: #eef1f4; --surface: rgba(255,255,255,.78); --surface-solid: #fff; --line: rgba(20,32,45,.08); --fg: #14202d; --fg-2: #586675;
  --fg-3: #8a96a3; --accent: #1d8a7a; --fresh: #3b8fd9; --supply: #e08a3c; --extract: #c26d7e; --exhaust: #8b97a4; --cold: #3b82d6;
  --fine: #1f9d6c; --warm: #d8602f; --flame: #ff6a2b; --water-hot: #f07a3a; --water-cool: #f6c79a; --danger: #d64545;
  --scrim: rgba(10,18,28,.32); --shadow: 0 1px 2px rgba(20,32,45,.06), 0 8px 24px rgba(20,32,45,.06); --sheet-shadow: 0 -10px 40px rgba(10,18,28,.18);
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, sans-serif;
  --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, "Segoe UI", Roboto, sans-serif;
  --glass: rgba(255,255,255,.55); --glass-strong: rgba(255,255,255,.78); --edge: rgba(255,255,255,.85); --edge-low: rgba(20,32,45,.07);
  --blob-a: #ffb27a; --blob-b: #8fc3ff; --blob-c: #b9e6d3;
  display: block; min-height: 100%; background: var(--bg); color: var(--fg); font: 16px/1.45 var(--font); -webkit-tap-highlight-color: transparent;
}
:host([dark]) {
  --bg: #0e1318; --surface: rgba(28,35,43,.78); --surface-solid: #1c232b; --line: rgba(255,255,255,.07); --fg: #eef2f5; --fg-2: #a3afbb;
  --fg-3: #6f7c89; --accent: #3cc3ab; --fresh: #5aa8ec; --supply: #f0a056; --extract: #d98a9a; --exhaust: #7d8a97; --cold: #5c9ceb;
  --fine: #3cc08a; --warm: #f07b4a; --flame: #ff7a3d; --water-hot: #f58a4c; --water-cool: #7a5236; --danger: #f06a6a;
  --scrim: rgba(0,0,0,.5); --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.25); --sheet-shadow: 0 -10px 40px rgba(0,0,0,.5);
  --glass: rgba(34,42,52,.55); --glass-strong: rgba(40,49,60,.82); --edge: rgba(255,255,255,.16); --edge-low: rgba(255,255,255,.05);
  --blob-a: #7a3a14; --blob-b: #14365c; --blob-c: #134437;
  color-scheme: dark;
}
* { box-sizing: border-box; }
button { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 12px; }
.num { font-variant-numeric: tabular-nums; }
/* liquid glass: translucent surfaces over a soft coloured backdrop, a bright edge where light catches them, a highlight on top */
.backdrop { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.backdrop i { position: absolute; border-radius: 50%; filter: blur(80px); opacity: .5; }
.backdrop i:nth-child(1) { width: 46vw; height: 46vw; left: -8vw; top: 4vh; background: var(--blob-a); }
.backdrop i:nth-child(2) { width: 40vw; height: 40vw; right: -10vw; top: 36vh; background: var(--blob-b); }
.backdrop i:nth-child(3) { width: 34vw; height: 34vw; left: 22vw; bottom: -10vh; background: var(--blob-c); }
.card, .chip, .fn, .toast { background: var(--glass) !important; border: 0 !important; backdrop-filter: blur(30px) saturate(180%); -webkit-backdrop-filter: blur(30px) saturate(180%); }
.chip, .fn { position: relative; }
.card::before, .chip::before, .fn::before, .toast::before, .sheet::before { content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1px; pointer-events: none;
  background: linear-gradient(160deg, var(--edge), var(--edge-low) 40%, var(--edge-low) 70%, var(--edge));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; }
.card::after, .fn::after { content: ""; position: absolute; inset: 0 0 60% 0; border-radius: inherit; pointer-events: none;
  background: linear-gradient(180deg, rgba(255,255,255,.14), transparent); }
.card { border-radius: 28px !important; }
.page { position: relative; z-index: 1; max-width: 1120px; margin: 0 auto; display: grid; gap: 20px; padding: 20px max(16px, env(safe-area-inset-right, 0px)) 48px max(16px, env(safe-area-inset-left, 0px)); }
.head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px; }
.head h1 { font: 700 1.6rem/1.1 var(--font-display); letter-spacing: -.02em; margin: 0 auto 0 0; display: flex; align-items: center; gap: 6px; }
.tabs { display: flex; gap: 2px; padding: 3px; border-radius: 12px; background: var(--line); }
.tabs button { border: 0; background: transparent; padding: 7px 14px; border-radius: 9px; font-size: .9375rem; font-weight: 600; color: var(--fg-2); cursor: pointer; }
.tabs button[aria-selected="true"] { background: var(--surface-solid); color: var(--fg); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.view { display: grid; gap: 20px; }
.status { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.group { display: grid; gap: 6px; }
.group h2 { font: 600 .8125rem/1.2 var(--font); letter-spacing: .02em; text-transform: uppercase; color: var(--fg-2); margin: 0 4px; }
.group .card { padding: 0 16px; }
.group .card > :first-child { border-top: 0; }
.group .foot { font-size: .8125rem; color: var(--fg-3); margin: 0 4px; }
.sgrid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr)); gap: 20px; align-items: start; }
.tin { font: 600 1rem var(--font); color: var(--fg); background: var(--line); border: 0; border-radius: 10px; padding: 8px 10px; min-width: 0; }
.day { display: flex; justify-content: space-between; align-items: center; gap: 12px; width: 100%; border: 0; border-top: 1px solid var(--line);
  background: none; padding: 13px 0; text-align: left; cursor: pointer; }
.day span:last-child { margin-left: auto; color: var(--fg-2); font-size: .875rem; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.day::after { content: "›"; color: var(--fg-3); font-size: 1.2rem; margin-left: 4px; }
.textbtn { width: 100%; text-align: left; border: 0; border-top: 1px solid var(--line); background: none; padding: 14px 0; color: var(--accent); font-weight: 600; cursor: pointer; }
.textbtn.warn { color: var(--danger); }
.phase { padding: 12px 0; border-top: 1px solid var(--line); display: grid; gap: 10px; }
.phase-times { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--fg-2); }
.menu { width: 40px; height: 40px; border: 0; border-radius: 12px; background: none; cursor: pointer; display: grid; place-items: center; margin-left: -8px; }
.menu svg { width: 24px; height: 24px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; background: var(--surface); border: 1px solid var(--line);
  font-size: .875rem; color: var(--fg-2); backdrop-filter: blur(20px) saturate(160%); -webkit-backdrop-filter: blur(20px) saturate(160%); }
.chip b { color: var(--fg); font-weight: 600; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--fine); }
.top { display: grid; grid-template-columns: minmax(0,3fr) minmax(0,2fr); gap: 20px; }
@media (max-width: 820px) { .top { grid-template-columns: minmax(0,1fr); } }
.card { position: relative; background: var(--surface); border: 1px solid var(--line); border-radius: 22px; box-shadow: var(--shadow);
  backdrop-filter: blur(24px) saturate(160%); -webkit-backdrop-filter: blur(24px) saturate(160%); padding: 18px 18px 16px; text-align: left;
  width: 100%; display: block; }
button.card { cursor: pointer; touch-action: manipulation; transition: transform 120ms ease-out; }
button.card:active, .card.pressed { transform: scale(.985); }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.label { font-size: .8125rem; font-weight: 600; letter-spacing: .02em; color: var(--fg-2); text-transform: uppercase; }
.hint { font-size: .8125rem; color: var(--fg-3); }
.unit-tap { display: block; width: 100%; border: 0; background: none; padding: 0; text-align: left; cursor: pointer; border-radius: 14px;
  transition: transform 120ms ease-out; touch-action: manipulation; }
.unit-tap:active { transform: scale(.99); }
.pill-switch { display: inline-flex; align-items: center; gap: 10px; padding: 5px 6px 5px 12px; border-radius: 999px; border: 1px solid var(--line);
  background: var(--surface-solid); cursor: pointer; font-size: .875rem; font-weight: 600; transition: transform 100ms ease-out; }
.pill-switch:active { transform: scale(.96); }
.pill-switch small { font-weight: 500; color: var(--fg-3); }
.switch { position: relative; width: 52px; height: 32px; border-radius: 16px; border: 0; background: var(--line); cursor: pointer; flex: none; transition: background 200ms ease; }
.switch::after { content: ""; position: absolute; top: 3px; left: 3px; width: 26px; height: 26px; border-radius: 50%; background: #fff;
  box-shadow: 0 2px 6px rgba(0,0,0,.2); transition: transform 320ms cubic-bezier(.3,1.4,.5,1); }
.switch[aria-checked="true"] { background: var(--accent); }
.switch[aria-checked="true"]::after { transform: translateX(20px); }
.pill-switch .switch { width: 44px; height: 26px; pointer-events: none; }
.pill-switch .switch::after { width: 20px; height: 20px; }
.pill-switch .switch[aria-checked="true"]::after { transform: translateX(18px); }
svg.diagram { display: block; width: 100%; max-width: 640px; margin: 6px auto 0; height: auto; overflow: visible; }
.duct { fill: none; stroke-width: 14; stroke-linecap: round; stroke-linejoin: round; opacity: .18; }
.t-name { font: 600 10.5px var(--font); letter-spacing: .04em; text-transform: uppercase; fill: var(--fg-2); }
.t-val { font: 700 22px var(--font-display); letter-spacing: -.02em; fill: var(--fg); }
.t-small { font: 500 10.5px var(--font); fill: var(--fg-3); }
.box { fill: var(--surface-solid); stroke: var(--line); stroke-width: 1.5; }
.hx { fill: none; stroke: var(--fg-3); stroke-width: 1.2; opacity: .55; }
.zone { font: 600 10px var(--font); letter-spacing: .08em; text-transform: uppercase; fill: var(--fg-3); }
.unit-meta { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 8px; font-size: .875rem; color: var(--fg-2); }
.unit-meta b { color: var(--fg); font-weight: 600; }
#water { container-type: inline-size; }
.a-body { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 24px; align-items: center; margin-top: 12px; }
.tankA { position: relative; width: 132px; height: 290px; }
.tankA svg { width: 100%; height: 100%; overflow: visible; }
.sensor { position: absolute; left: 100%; display: flex; align-items: center; gap: 8px; white-space: nowrap; transform: translateY(-50%);
  font-size: .8125rem; color: var(--fg-2); }
.sensor::before { content: ""; width: 16px; height: 1px; background: var(--fg-3); }
.sensor b { color: var(--fg); font-weight: 600; }
.a-facts { display: grid; gap: 16px; padding-left: 112px; min-width: 0; }
.fact { min-width: 0; }
.fact .huge { display: block; font: 700 2.5rem/1.05 var(--font-display); letter-spacing: -.03em; }
.fact > span:not(.huge) { color: var(--fg-2); font-size: .9375rem; }
.fact b { color: var(--fg); font-weight: 600; }
/* narrower card: the two sensor values sit on the tank itself */
@container (max-width: 500px) {
  .a-facts { padding-left: 0; }
  .tankA { width: 112px; height: 250px; }
  .sensor { left: 50%; transform: translate(-50%, -50%); flex-direction: column; gap: 0; color: rgba(255,255,255,.88); text-shadow: 0 1px 2px rgba(0,0,0,.3); font-size: .75rem; }
  .sensor::before { display: none; }
  .sensor b { color: #fff; }
  .fact .huge { font-size: 2rem; }
}
@container (max-width: 300px) { .a-body { grid-template-columns: 1fr; justify-items: center; } .a-facts { justify-items: center; text-align: center; } }
.card-head .working { margin-top: 0; }
.working { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; padding: 5px 10px; border-radius: 999px;
  background: color-mix(in srgb, var(--water-hot) 14%, transparent); font-size: .8125rem; font-weight: 600; }
.water-set { display: flex; justify-content: space-between; align-items: baseline; margin-top: 14px; font-size: .875rem; color: var(--fg-2); position: relative; }
.water-set b { color: var(--fg); font-weight: 600; }
#water { touch-action: pan-y; user-select: none; -webkit-user-select: none; }
.srow { padding: 14px 0 6px; border-top: 1px solid var(--line); }
.srow-head { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.sval { font: 700 1.25rem var(--font-display); letter-spacing: -.02em; white-space: nowrap; }
.slider { position: relative; height: 44px; margin: 2px 14px 0; touch-action: none; cursor: pointer; }
.s-rail, .s-fill { position: absolute; left: 0; top: 19px; height: 6px; border-radius: 6px; }
.s-rail { right: 0; background: var(--line); }
.s-fill { background: var(--accent); width: 0; }
.s-knob { position: absolute; top: 8px; left: 0; width: 28px; height: 28px; margin-left: -14px; border-radius: 50%; background: var(--surface-solid);
  box-shadow: 0 2px 10px rgba(0,0,0,.22), 0 0 0 1px var(--line); transition: scale 120ms ease-out; }
.slider.dragging .s-knob { scale: 1.12; }
.s-ends { display: flex; justify-content: space-between; font-size: .75rem; color: var(--fg-3); margin: -4px 0 4px; }
.active-wrap { overflow: hidden; margin: -6px; padding: 6px; }
.active { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 260px), 1fr)); gap: 12px; }
.fn { display: flex; align-items: center; gap: 12px; padding: 12px 12px 12px 14px; border-radius: 18px; background: var(--surface); border: 1px solid var(--line);
  box-shadow: var(--shadow); backdrop-filter: blur(24px) saturate(160%); -webkit-backdrop-filter: blur(24px) saturate(160%); min-width: 0; }
.fn-icon { flex: none; width: 36px; height: 36px; border-radius: 11px; display: grid; place-items: center; }
.fn-icon svg { width: 20px; height: 20px; }
.fn-text { flex: 1; min-width: 0; }
.fn-title { font-weight: 600; font-size: .9375rem; }
.fn-detail { font-size: .8125rem; color: var(--fg-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
#floors { display: grid; gap: 20px; }
.allel { display: flex; align-items: center; gap: 12px; padding: 12px 12px 12px 16px; }
.allel .fn-text { flex: 1; min-width: 0; }
.floor { display: grid; gap: 10px; }
.floor h2 { font: 700 1.15rem/1.2 var(--font-display); letter-spacing: -.01em; margin: 6px 2px 0; }
.rooms { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 168px), 1fr)); gap: 12px; }
@media (max-width: 420px) { .rooms { grid-template-columns: repeat(2, minmax(0,1fr)); } }
.room { padding: 14px 14px 12px; touch-action: pan-y; user-select: none; -webkit-user-select: none; overflow: hidden; }
.room .state { position: absolute; inset: 0; border-radius: inherit; pointer-events: none; box-shadow: inset 0 0 0 2px var(--ring, transparent); opacity: .55; }
.room-name { font-size: .9375rem; font-weight: 600; display: flex; align-items: center; justify-content: space-between; gap: 6px; min-width: 0; }
.room-name span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.room-temp { font: 700 2.25rem/1.05 var(--font-display); letter-spacing: -.03em; margin-top: 8px; }
.room-temp small { font-size: 1.1rem; color: var(--fg-2); font-weight: 600; }
.room-target { position: relative; margin-top: 4px; font-size: .875rem; color: var(--fg-2); min-height: 1.3em; white-space: nowrap; }
.room-target b { color: var(--fg); font-weight: 600; }
.saved { position: absolute; right: 0; top: 0; color: var(--fine); font-weight: 600; opacity: 0; transition: opacity 200ms ease; }
.saved.show { opacity: 1; }
.track { position: relative; height: 4px; border-radius: 4px; background: var(--line); margin-top: 12px; }
.mark { position: absolute; top: 50%; left: 0; width: 14px; height: 14px; margin: -7px 0 0 -7px; border-radius: 50%; background: var(--fg); box-shadow: 0 1px 4px rgba(0,0,0,.2); }
.now-mark { position: absolute; top: -3px; width: 2px; height: 10px; margin-left: -1px; border-radius: 2px; background: var(--fg-3); }
.dragging .mark { background: var(--accent); }
.elem { width: 20px; height: 20px; flex: none; }
.elem.off { opacity: .28; }
.scrim { position: fixed; inset: 0; background: var(--scrim); opacity: 0; pointer-events: none; z-index: 20; }
.sheet { position: fixed; left: 50%; bottom: 0; z-index: 21; width: min(560px, 100%); max-height: 86%; overflow: auto; transform: translate(-50%, 110%);
  background: var(--glass-strong); backdrop-filter: blur(40px) saturate(180%); -webkit-backdrop-filter: blur(40px) saturate(180%); border-radius: 26px 26px 0 0; box-shadow: var(--sheet-shadow); touch-action: none; overscroll-behavior: contain;
  padding: 8px max(20px, env(safe-area-inset-right, 0px)) calc(24px + env(safe-area-inset-bottom, 0px)) max(20px, env(safe-area-inset-left, 0px)); }
.grabber { width: 40px; height: 5px; border-radius: 3px; background: var(--fg-3); opacity: .5; margin: 4px auto 14px; }
.sheet h3 { font: 700 1.4rem/1.15 var(--font-display); letter-spacing: -.02em; margin: 0 0 4px; }
.sub { color: var(--fg-2); font-size: .9375rem; margin: 0 0 18px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 0; border-top: 1px solid var(--line); flex-wrap: wrap; }
.row-label { font-weight: 600; flex: 1 1 140px; min-width: 0; }
.row > .switch { flex: none; }
.row-label small { display: block; font-weight: 400; color: var(--fg-3); font-size: .8125rem; }
.close { position: absolute; top: 14px; right: max(16px, env(safe-area-inset-right, 0px)); width: 32px; height: 32px; border-radius: 50%; border: 0;
  background: var(--line); cursor: pointer; font-size: 1rem; color: var(--fg-2); }
.stepper { display: inline-flex; align-items: center; gap: 4px; }
.stepper button { width: 40px; height: 40px; border-radius: 50%; border: 0; background: var(--line); font-size: 1.3rem; cursor: pointer; transition: transform 100ms ease-out; }
.stepper button:active { transform: scale(.92); }
.stepper output { min-width: 72px; text-align: center; font: 700 1.4rem var(--font-display); letter-spacing: -.02em; }
.seg { display: flex; flex-wrap: wrap; gap: 4px; padding: 3px; border-radius: 12px; background: var(--line); }
.seg button { border: 0; background: transparent; padding: 7px 11px; border-radius: 9px; font-size: .875rem; cursor: pointer; color: var(--fg-2); }
.seg button[aria-pressed="true"] { background: var(--surface-solid); color: var(--fg); font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.level { position: relative; height: 56px; margin: 6px 4px 4px; touch-action: none; cursor: grab; }
.level.auto { opacity: .45; pointer-events: none; }
.level-note { font-size: .8125rem; color: var(--fg-3); margin: 0 0 6px; }
.rail, .rail-fill { position: absolute; left: 0; top: 26px; height: 4px; border-radius: 4px; }
.rail { right: 0; background: var(--line); }
.rail-fill { background: var(--accent); }
.tick { position: absolute; top: 40px; transform: translateX(-50%); font-size: .8125rem; color: var(--fg-3); font-weight: 600; }
.tick.on { color: var(--fg); }
.knob { position: absolute; top: 14px; left: 0; width: 28px; height: 28px; margin-left: -14px; border-radius: 50%; background: var(--surface-solid);
  box-shadow: 0 2px 10px rgba(0,0,0,.22), 0 0 0 1px var(--line); }
.link { border: 0; background: none; color: var(--accent); font-weight: 600; cursor: pointer; padding: 14px 0 0; }
.toast { position: fixed; left: 50%; bottom: calc(20px + env(safe-area-inset-bottom, 0px)); z-index: 30; display: flex; align-items: center; gap: 14px;
  padding: 10px 10px 10px 16px; border-radius: 16px; background: var(--surface); border: 1px solid var(--line); box-shadow: var(--sheet-shadow);
  backdrop-filter: blur(24px) saturate(160%); -webkit-backdrop-filter: blur(24px) saturate(160%); transform: translate(-50%, 160%); max-width: calc(100% - 32px);
  font-size: .9375rem; font-weight: 600; }
.toast span { overflow: hidden; text-overflow: ellipsis; }
.toast button { flex: none; border: 0; background: var(--line); padding: 7px 12px; border-radius: 10px; font-weight: 600; color: var(--accent); cursor: pointer; }
[hidden] { display: none !important; }
@media (prefers-reduced-transparency: reduce) {
  .card, .chip, .fn, .toast, .sheet { background: var(--surface-solid) !important; backdrop-filter: none; -webkit-backdrop-filter: none; }
  .backdrop { display: none; }
}
@media (prefers-reduced-motion: reduce) { button.card, .switch::after, .stepper button, .unit-tap, .pill-switch { transition: none; } }
`;

const FAN = '<circle r="12" fill="var(--surface-solid)" stroke="var(--line)"/><path d="M0-8C3-8 4-3 0 0 -4-3-3-8 0-8ZM8 0C8 3 3 4 0 0 3-4 8-3 8 0ZM0 8C-3 8-4 3 0 0 4 3 3 8 0 8ZM-8 0C-8-3-3-4 0 0-3 4-8 3-8 0Z" fill="var(--fg-2)"/>';
const FLAME = '<path d="M14 0C20 12 28 16 26 28 24 37 4 37 2 28 0 19 8 14 14 0Z" fill="var(--flame)"/><path d="M14 13C16 19 21 22 19 28 18 32 10 32 9 28 8 23 13 20 14 13Z" fill="#ffd166"/>';
const RADIATOR = '<path d="M5 6v12M9.5 6v12M14 6v12M18.5 6v12M3 8h18M3 16h18" stroke="var(--fg-2)" stroke-width="1.8" fill="none" stroke-linecap="round"/>';
const svgNS = "http://www.w3.org/2000/svg";
const TANK_L = 300;  // the hot-water heat pump T300 holds 300 litres

class ProxonPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._built = false; this._rooms = new Map(); this._fnCards = new Map(); this._pending = new Map();
    this._ending = new Map();  // functions switched off here, until the unit reports them off (holiday mode takes a moment)
  }
  set panel(p) { this._config = (p && p.config) || {}; if (this._hass) this._update(); }
  set narrow(n) { this._narrow = n; if (this._built) this.$("menu").hidden = !n; }
  set hass(h) {
    this._hass = h;
    if (!this._built) this._build();
    this._update();
  }
  get t() { return TEXT[(this._hass && this._hass.language || "en").startsWith("de") ? "de" : "en"]; }
  connectedCallback() { if (this._built) this._startAir(); }
  disconnectedCallback() { cancelAnimationFrame(this._air); this._air = 0; }

  // ---------- helpers ----------
  $(id) { return this.shadowRoot.getElementById(id); }
  id(key) { return ((this._config || {}).entities || {})[key]; }
  st(key) { const e = this.id(key); return e ? this._hass.states[e] : undefined; }
  num(key) { const s = this.st(key); const v = s ? parseFloat(s.state) : NaN; return Number.isFinite(v) ? v : null; }
  fmt(v, d = 1) { return v === null || v === undefined ? "–" : Number(v).toLocaleString(this._hass.language || undefined, { minimumFractionDigits: d, maximumFractionDigits: d }); }
  call(domain, service, data) {  // a failure is shown by Home Assistant itself; the caller only puts its view back
    return this._hass.callService(domain, service, data);
  }
  moreInfo(entityId) { this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true })); }

  // ---------- build once ----------
  _build() {
    this._built = true;
    const t = this.t;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <div class="backdrop" aria-hidden="true"><i></i><i></i><i></i></div>
      <div class="page">
        <header class="head">
          <h1><button class="menu" id="menu" aria-label="Menu" ${this._narrow ? "" : "hidden"}><svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button><span id="h-title">${t.home}</span></h1>
          <div class="tabs" role="tablist"><button role="tab" id="tab-home" aria-selected="true">${t.home}</button><button role="tab" id="tab-settings" aria-selected="false">${t.settings}</button></div>
        </header>
        <div class="view" id="v-home">
        <div class="status">
          <span class="chip">${t.outside} <b class="num" id="c-out">–</b></span>
          <span class="chip" id="c-op-wrap">${t.op} <b id="c-op">–</b></span>
          <span class="chip"><span class="dot" id="c-dot"></span><b id="c-ok">${t.ok}</b></span>
        </div>
        <div class="active-wrap" id="active-wrap"><div class="active" id="active" aria-live="polite"></div></div>
        <section class="top">
          <section class="card" aria-label="${t.unit}">
            <div class="card-head"><span class="label">${t.unit}</span>
              <button class="pill-switch" id="boost">${t.boost} <small id="boost-left" hidden></small><span class="switch" id="boost-sw" aria-hidden="true" aria-checked="false"></span></button></div>
            <button class="unit-tap" id="unit">
              <div class="hint" style="margin-top:4px">${t.level} <b class="num" id="u-level">–</b> · ${t.tapUnit}</div>
              <svg class="diagram" viewBox="0 0 400 236" aria-hidden="true">
                <text class="zone" x="0" y="118">${t.out}</text><text class="zone" x="400" y="118" text-anchor="end">${t.house}</text>
                <path id="p-fresh" class="duct" stroke="var(--fresh)" d="M 44 70 L 150 70 L 200 118"/>
                <path id="p-supply" class="duct" stroke="var(--supply)" d="M 200 118 L 250 70 L 356 70"/>
                <path id="p-extract" class="duct" stroke="var(--extract)" d="M 356 166 L 250 166 L 200 118"/>
                <path id="p-exhaust" class="duct" stroke="var(--exhaust)" d="M 200 118 L 150 166 L 44 166"/>
                <rect class="box" x="134" y="52" width="132" height="132" rx="20"/>
                <path class="hx" d="M 200 92 L 226 118 L 200 144 L 174 118 Z M 187 105 L 213 131 M 213 105 L 187 131"/>
                <g id="particles"></g>
                <g transform="translate(306 70)"><g id="fan-s">${FAN}</g></g><g transform="translate(94 166)"><g id="fan-e">${FAN}</g></g>
                <text class="t-name" x="44" y="30">${t.fresh}</text><text class="t-val num" id="v-fresh" x="44" y="54">–</text>
                <text class="t-name" x="356" y="30" text-anchor="end">${t.supply}</text><text class="t-val num" id="v-supply" x="356" y="54" text-anchor="end">–</text>
                <text class="t-name" x="356" y="200" text-anchor="end">${t.extract}</text><text class="t-val num" id="v-extract" x="356" y="224" text-anchor="end">–</text>
                <text class="t-name" x="44" y="200">${t.exhaust}</text><text class="t-val num" id="v-exhaust" x="44" y="224">–</text>
                <text class="t-small num" id="rpm-s-t" x="306" y="98" text-anchor="middle"></text>
                <text class="t-small num" id="rpm-e-t" x="94" y="146" text-anchor="middle"></text>
              </svg>
              <div class="unit-meta"><span>${t.fanSupply} <b class="num" id="rpm-s">–</b> U/min</span><span>${t.fanExhaust} <b class="num" id="rpm-e">–</b> U/min</span>
                <span id="rec-wrap">${t.recovery} <b class="num" id="rec">–</b></span></div>
            </button>
          </section>
          <button class="card" id="water" aria-label="${t.water}">
            <div class="card-head"><span class="label">${t.water}</span>
              <span class="working" id="w-working" hidden><svg width="14" height="14" viewBox="0 0 28 37" aria-hidden="true">${FLAME}</svg><span id="w-who"></span></span>
              <span class="hint" id="w-hint">${t.tapUnit}</span></div>
            <div class="a-body">
              <div class="tankA">
                <svg viewBox="0 0 150 330" aria-hidden="true">
                  <defs><clipPath id="tank-clip"><rect x="6" y="6" width="138" height="318" rx="56"/></clipPath>
                    <linearGradient id="wg" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="var(--water-cool)"/><stop offset=".55" stop-color="var(--supply)"/><stop offset="1" stop-color="var(--water-hot)"/></linearGradient>
                    <linearGradient id="wglass" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".18" stop-color="#fff" stop-opacity=".05"/>
                      <stop offset=".82" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".22"/></linearGradient></defs>
                  <rect x="6" y="6" width="138" height="318" rx="56" fill="var(--line)"/>
                  <g clip-path="url(#tank-clip)"><path id="w-wave" fill="url(#wg)"/></g>
                  <rect x="6" y="6" width="138" height="318" rx="56" fill="url(#wglass)"/>
                  <rect x="6.5" y="6.5" width="137" height="317" rx="55.5" fill="none" stroke="var(--edge)" stroke-width="1.2"/>
                  <text x="75" y="40" text-anchor="middle" font-size="12" font-weight="700" fill="#fff" opacity=".85">${TANK_L} l</text>
                </svg>
                <span class="sensor" style="top: 50%">${t.middle} <b class="num" id="w-mid">–</b></span>
                <span class="sensor" style="top: 84%">${t.bottom} <b class="num" id="w-bottom">–</b></span>
              </div>
              <div class="a-facts">
                <div class="fact" id="w-liters-wrap"><span class="huge num" id="w-liters">–</span><span>${t.litersSub}</span></div>
                <div class="fact" id="w-shower-wrap"><span class="huge num" id="w-shower">–</span><span>${t.showerSub}</span></div>
                <div class="fact"><span class="huge num" id="w-temp">–</span><span>${t.middle}<span id="w-charge-wrap"> · ${t.charge} <b class="num" id="w-charge">–</b></span></span></div>
              </div>
            </div>
            <div id="w-set-wrap"><div class="water-set"><span>${t.target} <b class="num" id="w-target">–</b></span><span class="saved" id="w-saved">${t.sent}</span></div>
              <div class="track" id="w-track" aria-hidden="true"><span class="now-mark" id="w-now"></span><span class="mark" id="w-mark"></span></div></div>
          </button>
        </section>
        <div id="floors"></div>
        </div>
        <div class="view" id="v-settings" hidden></div>
      </div>
      <div class="toast" id="toast" role="status" hidden><span id="toast-text"></span><button id="toast-undo">${t.undo}</button></div>
      <div class="scrim" id="scrim"></div>
      <div class="sheet" id="sheet" role="dialog" aria-modal="true" hidden><div class="grabber"></div>
        <button class="close" id="sheet-close" aria-label="${t.close}">✕</button><div id="sheet-body"></div></div>`;
    this.$("menu").addEventListener("click", () => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    this.$("boost").addEventListener("click", () => this._toggle("Intensivlueftung"));
    this._viewIn = new Spring(1, v => { const el = this._shownView; if (el) { el.style.opacity = clamp(v, 0, 1).toFixed(3); el.style.translate = `${((1 - v) * this._viewDir * 24).toFixed(1)}px 0`; } });
    this.$("tab-home").addEventListener("click", () => this._tab("home"));
    this.$("tab-settings").addEventListener("click", () => this._tab("settings"));
    this.$("unit").addEventListener("click", e => this._sheetVentilation(e.currentTarget));
    this.$("water").addEventListener("click", e => { if (!this._wCtl.dragged()) this._sheetWater(e.currentTarget); });
    this._wCtl = this._numberDrag(this.$("water"), this.$("w-track"), "SollWassertemperatur", {
      tile: true,
      show: (v, snapped, r) => {
        this.$("w-mark").style.transform = `translateX(${((v - r.min) / (r.max - r.min) * this.$("w-track").clientWidth).toFixed(1)}px)`;
        this.$("w-target").textContent = `${this.fmt(snapped, 0)}°`;
      },
      done: () => { const s = this.$("w-saved"); s.classList.add("show"); setTimeout(() => s.classList.remove("show"), 1400); },
    });
    this._fill = new Spring(0, () => {});  // the level of the tank; its surface is drawn with the air (one loop)
    this._wrapH = new Spring(0, v => { this.$("active-wrap").style.height = `${v.toFixed(1)}px`; });
    this._buildSheet();
    this._buildToast();
    this._buildAir();
    this._startAir();
    let tab = "home"; try { tab = sessionStorage.getItem("proxon-tab") || "home"; } catch (_) { /* no storage */ }
    if (tab === "settings") this._tab("settings", true);
  }

  // ---------- tabs: home and settings; the new one slides in from its side ----------
  _tab(name, instant) {
    const home = name === "home";
    if (this._current === name) return;
    this._current = name;
    try { sessionStorage.setItem("proxon-tab", name); } catch (_) { /* no storage */ }
    this.$("tab-home").setAttribute("aria-selected", home); this.$("tab-settings").setAttribute("aria-selected", !home);
    this.$("h-title").textContent = home ? this.t.home : this.t.settings;
    if (!home && !this._settingsBuilt) this._buildSettings();
    this.$("v-home").hidden = !home; this.$("v-settings").hidden = home;
    this._shownView = this.$(home ? "v-home" : "v-settings"); this._viewDir = home ? -1 : 1;
    if (instant) this._viewIn.set(1); else { this._viewIn.set(0); this._viewIn.to(1, { damping: 1, response: 0.35 }); }
    if (!home) this._updateSettings();
  }

  // ---------- live values ----------
  _update() {
    if (!this._built || !this._hass) return;
    const t = this.t, dark = this._hass.themes && this._hass.themes.darkMode;
    this.toggleAttribute("dark", !!dark);
    const deg = key => { const v = this.num(key); return v === null ? "–" : `${this.fmt(v)}°`; };
    this.$("c-out").textContent = deg("T3Frischluft");
    const op = this.st("AktuellerBetrieb");
    this.$("c-op-wrap").hidden = !op;
    if (op) this.$("c-op").textContent = this._hass.formatEntityState ? this._hass.formatEntityState(op) : op.state;
    const fault = (this.st("Stoerung") || {}).state === "on", filter = (this.st("FilterRestStunden_warning") || {}).state === "on";
    this.$("c-ok").textContent = fault ? t.fault : filter ? t.filter : t.ok;
    this.$("c-dot").style.background = fault ? "var(--danger)" : filter ? "var(--warm)" : "var(--fine)";
    // unit
    [["v-fresh", "T3Frischluft"], ["v-supply", "T1Zuluft"], ["v-extract", "T7Abluft"], ["v-exhaust", "T4Fortluft"]].forEach(([el, k]) => { this.$(el).textContent = deg(k); });
    const rs = this.num("DrehzahlZuluft"), re = this.num("DrehzahlAbluft");
    const rpm = v => v === null ? "–" : Math.round(v).toLocaleString(this._hass.language || undefined);
    this.$("rpm-s").textContent = rpm(rs); this.$("rpm-e").textContent = rpm(re);
    this.$("rpm-s-t").textContent = rs === null ? "" : `${rpm(rs)} U/min`; this.$("rpm-e-t").textContent = re === null ? "" : `${rpm(re)} U/min`;
    this._rpm = rs || 0;
    const boost = (this.st("Intensivlueftung") || {}).state === "on";
    this.$("boost").hidden = !this.st("Intensivlueftung");
    this.$("boost").setAttribute("aria-pressed", boost); this.$("boost-sw").setAttribute("aria-checked", boost);
    const left = this.num("IntensivlueftungsRestDauer");
    this.$("boost-left").hidden = !(boost && left); this.$("boost-left").textContent = fill(t.left, { m: left });
    const lvl = this.num("IstLuefterstufe") ?? this.num("Luefterstufe");
    this.$("u-level").textContent = boost ? t.levelBoost : lvl === null ? "–" : Math.round(lvl);
    const rec = this.num("Waermerueckgewinnung");
    this.$("rec-wrap").hidden = rec === null; this.$("rec").textContent = `${this.fmt(rec, 0)} %`;
    // hot water
    const hasWater = !!this.st("WarmwasserIstTemperatur");
    this.$("water").hidden = !hasWater;
    if (hasWater) {
      const w = this.num("WarmwasserIstTemperatur");
      this.$("w-temp").textContent = w === null ? "–" : `${this.fmt(w)}°`;
      this.$("w-mid").textContent = w === null ? "–" : `${this.fmt(w)}°`;
      const sh = this.num("WarmwasserDuschminuten");
      this.$("w-shower-wrap").hidden = sh === null; this.$("w-shower").textContent = `${this.fmt(sh, 0)} ${t.min}`;
      this.$("w-bottom").textContent = deg("WarmwasserUntenTemperatur");
      const wt = this.num("SollWassertemperatur"), wn = this.st("SollWassertemperatur");
      this.$("w-set-wrap").hidden = !wn;
      if (wn && w !== null) this.$("w-now").style.left = `${(clamp((w - wn.attributes.min) / (wn.attributes.max - wn.attributes.min), 0, 1) * 100).toFixed(1)}%`;
      this._wCtl.sync();
      const ch = this.num("WarmwasserLadezustand");
      this.$("w-charge-wrap").hidden = ch === null; this.$("w-charge").textContent = `${this.fmt(ch, 0)} %`;
      this.$("w-liters-wrap").hidden = ch === null; this.$("w-liters").textContent = `≈ ${this.fmt(Math.round(TANK_L * ch / 100 / 10) * 10, 0)} l`;
      const level = ch !== null ? ch / 100 : w !== null && wt ? clamp((w - 20) / Math.max(1, wt - 20), 0, 1) : 0;
      if (Math.abs((this._fill.target || 0) - level) > 0.001) this._fill.to(level, { damping: 1, response: 0.8 });
    }
    this._updateFunctions();
    this._updateRooms();
    if (this._sheetRefresh) this._sheetRefresh();
    if (this._settingsBuilt && this._current === "settings") this._updateSettings();
  }

  // ---------- the air: particles along the ducts at the speed of the fans ----------
  _buildAir() {
    const g = this.$("particles");
    this._ducts = [["p-fresh", "--fresh"], ["p-supply", "--supply"], ["p-extract", "--extract"], ["p-exhaust", "--exhaust"]].map(([id, color]) => {
      const path = this.$(id), len = path.getTotalLength(), n = Math.round(len / 18);
      const dots = Array.from({ length: n }, (_, i) => {
        const c = document.createElementNS(svgNS, "circle"); c.setAttribute("r", "2.6"); c.setAttribute("fill", `var(${color})`); g.appendChild(c);
        return { el: c, s: i / n * len };
      });
      return { path, len, dots };
    });
    this._speed = new Spring(0, () => {}); this._angle = 0;
  }
  _startAir() {
    if (this._air || !this._ducts) return;
    let last = performance.now();
    const step = t => {
      const dt = Math.min(0.05, (t - last) / 1000); last = t;
      if (Math.abs(this._speed.target - (this._rpm || 0)) > 1) this._speed.to(this._rpm || 0, { damping: 1, response: 0.9 });
      const moving = !reduceMotion.matches, v = moving ? this._speed.x / 1580 * 34 : 0;
      for (const d of this._ducts) for (const p of d.dots) {
        p.s = (p.s + v * dt) % d.len;
        const pt = d.path.getPointAtLength(p.s);
        p.el.setAttribute("cx", pt.x.toFixed(1)); p.el.setAttribute("cy", pt.y.toFixed(1));
        p.el.setAttribute("opacity", Math.min(1, Math.min(p.s, d.len - p.s) / 14).toFixed(2));
      }
      if (moving) this._angle = (this._angle + this._speed.x / 60 * 360 * dt * 0.08) % 360;
      this.$("fan-s").setAttribute("transform", `rotate(${this._angle.toFixed(1)})`);
      this.$("fan-e").setAttribute("transform", `rotate(${this._angle.toFixed(1)})`);
      const lvl = clamp(this._fill.x, 0, 1), top = 324 - 318 * lvl, amp = moving && lvl > 0.02 ? 2 : 0, ts = t / 1000;
      let d = `M0 ${top.toFixed(1)}`;
      for (let x = 0; x <= 150; x += 6) d += ` L${x} ${(top + Math.sin(x / 22 + ts * 1.4) * amp + Math.sin(x / 9 - ts) * amp * 0.4).toFixed(1)}`;
      this.$("w-wave").setAttribute("d", `${d} L150 330 L0 330 Z`);
      this._air = requestAnimationFrame(step);
    };
    this._air = requestAnimationFrame(step);
  }

  // ---------- running functions: a card each, springing in and out ----------
  _updateFunctions() {
    const t = this.t;
    let who = "";
    for (const f of FUNCS) {
      const st = this.st(f.sw), card = this._fnCards.get(f.k);
      let running = !!st && f.run(st);
      if (!running) this._ending.delete(f.k);
      else if (Date.now() - (this._ending.get(f.k) || 0) < 20000) running = false;
      if (running && ["solar", "price", "boostww", "legionella"].includes(f.k) && !who) who = t.fn[f.k][0];
      if (running && !card) this._showFn(f);
      else if (!running && card && !card.leaving) this._hideFn(f.k);
      if (running) this._fnDetail(f);
    }
    this.$("w-working").hidden = !who; this.$("w-who").textContent = who; this.$("w-hint").hidden = !!who;
  }
  _fnDetail(f) {
    const card = this._fnCards.get(f.k); if (!card) return;
    const t = this.t.fn[f.k];
    let detail = t[1];
    if (f.k === "holiday") {
      const off = (this.st("Urlaubsmodus").attributes || {}).plan_off_at;
      if (off) detail = fill(t[2], { d: new Date(off).toLocaleString(this._hass.language || undefined, { weekday: "short", day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit" }) });
    } else if (f.temp) detail = fill(t[1], { t: this.fmt(this.num(f.temp), 0) });
    else if (f.k === "cooling") detail = fill(t[1], { l: this.fmt(this.num("KuehlStufe"), 0) });
    card.querySelector(".fn-detail").textContent = detail;
  }
  _relayout(change) {
    const wrap = this.$("active-wrap"), before = new Map([...this._fnCards.values()].map(el => [el, el.getBoundingClientRect()]));
    const h0 = wrap.offsetHeight;
    change();
    wrap.style.height = "auto";
    const h1 = wrap.offsetHeight;
    this._wrapH.set(h0); this._wrapH.to(h1, { damping: 1, response: 0.4, onRest: () => { wrap.style.height = "auto"; } });
    for (const [el, r] of before) {
      if (!el.isConnected || el.leaving) continue;
      const n = el.getBoundingClientRect(), dx = r.left - n.left, dy = r.top - n.top;
      if (!dx && !dy) continue;
      const sp = el.flip || (el.flip = new Spring(0, v => { el.style.translate = `${(el.fdx * v).toFixed(1)}px ${(el.fdy * v).toFixed(1)}px`; }));
      el.fdx = dx; el.fdy = dy; sp.set(1); sp.to(0, { damping: 1, response: 0.4 });
    }
  }
  _showFn(f) {
    const t = this.t, el = document.createElement("div");
    el.className = "fn";
    el.innerHTML = `<span class="fn-icon" style="background: color-mix(in srgb, var(${f.tint}) 16%, transparent)"><svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="${f.icon}" fill="none" stroke="var(${f.tint})" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
      <span class="fn-text"><div class="fn-title">${t.fn[f.k][0]}</div><div class="fn-detail"></div></span>
      <button class="switch" role="switch" aria-checked="true" aria-label="${fill(t.end, { f: t.fn[f.k][0] })}"></button>`;
    el.querySelector(".switch").addEventListener("click", () => {
      const entity = this.id((f.off || [f.sw]).find(k => (this.st(k) || {}).state === "on") || f.sw);
      this._ending.set(f.k, Date.now());
      this.call("switch", "turn_off", { entity_id: entity }).then(
        () => this._toast(fill(t.off, { f: t.fn[f.k][0] }), () => { this._ending.delete(f.k); return this.call("switch", "turn_on", { entity_id: entity }); }),
        () => { this._ending.delete(f.k); this._update(); });
      this._hideFn(f.k);
    });
    el.appear = new Spring(0, v => { el.style.opacity = clamp(v, 0, 1).toFixed(3); el.style.scale = (0.92 + 0.08 * v).toFixed(4); });
    el.appear.set(0);
    this._relayout(() => {
      const order = FUNCS.map(x => x.k), next = order.slice(order.indexOf(f.k) + 1).map(k => this._fnCards.get(k)).find(c => c && !c.leaving);
      this.$("active").insertBefore(el, next || null);
      this._fnCards.set(f.k, el);
    });
    el.appear.to(1, { damping: 0.8, response: 0.4 });
  }
  _hideFn(k) {
    const el = this._fnCards.get(k); if (!el || el.leaving) return;
    el.leaving = true; this._fnCards.delete(k);
    el.querySelector(".switch").setAttribute("aria-checked", "false");
    el.appear.to(0, { damping: 1, response: 0.28, onRest: () => this._relayout(() => el.remove()) });
  }

  // ---------- rooms ----------
  _updateRooms() {
    const rooms = (this._config || {}).rooms || [];
    const key = rooms.map(r => `${r.n}:${r.floor}`).join(",");
    if (key !== this._roomKey) {  // the rooms or their floors changed: build the tiles anew
      this._roomKey = key; this._rooms.clear();
      const box = this.$("floors"); box.innerHTML = "";
      const floors = [0, 1, -1].filter(f => rooms.some(r => r.floor === f)), several = floors.length > 1;
      if (this.id("WaermeelementeAlle")) {  // the heating panels of all rooms at once, right above the rooms
        const row = document.createElement("div"); row.className = "card allel";
        row.innerHTML = `<span class="fn-icon" style="background: color-mix(in srgb, var(--flame) 14%, transparent)"><svg class="elem" viewBox="0 0 24 24" aria-hidden="true">${RADIATOR}</svg></span>
          <span class="fn-text"><div class="fn-title">${this.t.allEl}</div><div class="fn-detail" id="allel-sum"></div></span>
          <button class="switch" role="switch" id="allel-sw" aria-label="${this.t.allEl}" aria-checked="false"></button>`;
        box.appendChild(row);
        row.querySelector("#allel-sw").addEventListener("click", () => this._allElements());
      }
      for (const f of floors) {
        const sec = document.createElement("section"); sec.className = "floor";
        sec.innerHTML = `<h2>${several ? this.t.floors[String(f)] : this.t.rooms}</h2><div class="rooms"></div>`;
        box.appendChild(sec);
        for (const r of rooms.filter(x => x.floor === f)) {
          if (!this.id(`NBE${r.n}Thermostat`)) continue;
          const tile = this._roomTile(r.n); sec.querySelector(".rooms").appendChild(tile.el); this._rooms.set(r.n, tile);
        }
      }
    }
    for (const tile of this._rooms.values()) tile.render();
    const sw = this.shadowRoot.getElementById("allel-sw");
    if (sw) {
      const all = this.st("WaermeelementeAlle"), list = [...this._rooms.keys()].map(n => this._room(n)).filter(Boolean);
      const on = list.filter(r => r.mode === "heat").length;
      if (!this._allBusy) sw.setAttribute("aria-checked", (all && all.state === "on") || false);
      this.shadowRoot.getElementById("allel-sum").textContent = fill(this.t.allOn, { a: on, b: list.length });
    }
  }
  // switches every room's heating panel at once; undo puts each room back as it was (also when only some were on)
  _allElements() {
    const t = this.t, sw = this.shadowRoot.getElementById("allel-sw"), all = this.st("WaermeelementeAlle");
    const turnOn = !(all && all.state === "on");
    const before = [...this._rooms.keys()].map(n => this._room(n)).filter(Boolean).map(r => ({ entity: r.entity, mode: r.mode }));
    this._allBusy = true; sw.setAttribute("aria-checked", turnOn);
    this.call("switch", turnOn ? "turn_on" : "turn_off", { entity_id: this.id("WaermeelementeAlle") }).then(() => {
      this._allBusy = false;
      this._toast(turnOn ? t.allOnDone : t.allOff, () => Promise.all(before
        .filter(b => (b.mode === "heat" || b.mode === "auto") && b.mode !== (turnOn ? "heat" : "auto"))  // only rooms that changed
        .map(b => this.call("climate", "set_hvac_mode", { entity_id: b.entity, hvac_mode: b.mode }))));
    }, () => { this._allBusy = false; this._update(); });
  }
  _room(n) {
    const c = this.st(`NBE${n}Thermostat`); if (!c) return null;
    const a = c.attributes, el = this.st(`NBE${n}Waermeelement`);
    const pend = this._pending.get(n);
    if (pend && (Math.abs(a.temperature - pend.v) < 0.01 || Date.now() - pend.at > 8000)) this._pending.delete(n);
    return {
      name: (a.friendly_name || `NBE${n}`).replace(/^Proxon\s+/, ""), temp: a.current_temperature, target: this._pending.has(n) ? this._pending.get(n).v : a.temperature,
      min: a.min_temp, max: a.max_temp, step: a.target_temp_step || 0.5, mode: c.state, available: c.state !== "unavailable",
      element: el ? el.state : c.state === "heat" ? "ready" : "off", entity: c.entity_id,
    };
  }
  _roomTile(n) {
    const t = this.t, el = document.createElement("button");
    el.className = "card room";
    el.innerHTML = `<span class="state"></span><div class="room-name"><span class="nm"></span><span class="icon"></span></div>
      <div class="room-temp num"></div><div class="room-target"><span>${t.target} <b class="num tv"></b></span><span class="saved">${t.sent}</span></div>
      <div class="track" aria-hidden="true"><span class="now-mark"></span><span class="mark"></span></div>`;
    const $ = s => el.querySelector(s), track = $(".track"), mark = $(".mark");
    let r = null, shown = null;
    const frac = v => r ? (v - r.min) / (r.max - r.min) : 0;
    const digits = () => (r && r.step < 1 ? 1 : 0);
    const ctl = dragValue(el, track, {
      tile: true, range: () => r && { min: r.min, max: r.max, step: r.step }, value: () => r.target,
      show: (v, snapped) => {
        mark.style.transform = `translateX(${(frac(v) * track.clientWidth).toFixed(1)}px)`;
        if (snapped !== shown) { shown = snapped; $(".tv").textContent = `${this.fmt(snapped, digits())}°`; }
      },
      commit: v => commit(v),
    });
    const ring = x => { const d = x.temp - x.target; return d < -1 ? "var(--cold)" : d > 1 ? "var(--warm)" : "var(--fine)"; };
    const render = () => {
      r = this._room(n); if (!r) return;
      $(".nm").textContent = r.name;
      $(".icon").innerHTML = r.element === "heating" ? `<svg class="elem" viewBox="0 0 28 37" aria-hidden="true">${FLAME}</svg>`
        : `<svg class="elem ${r.element === "off" ? "off" : ""}" viewBox="0 0 24 24" aria-hidden="true">${RADIATOR}</svg>`;
      $(".icon").title = t.element[r.element] || "";
      $(".room-temp").innerHTML = r.temp === undefined || r.temp === null ? "–" : `${this.fmt(r.temp)}<small>°</small>`;
      $(".state").style.setProperty("--ring", r.available && r.temp != null ? ring(r) : "transparent");
      $(".now-mark").style.left = `${(clamp(frac(r.temp), 0, 1) * 100).toFixed(1)}%`;
      el.setAttribute("aria-label", `${r.name}: ${this.fmt(r.temp)} °C, ${t.target} ${this.fmt(r.target, digits())} °C, ${t.element[r.element] || ""}`);
      ctl.sync();
    };
    const commit = v => {
      if (!r || v === r.target) return;
      this._pending.set(n, { v, at: Date.now() });
      this.call("climate", "set_temperature", { entity_id: r.entity, temperature: v }).then(() => {
        const s = $(".saved"); s.classList.add("show"); setTimeout(() => s.classList.remove("show"), 1400);
      }, () => { this._pending.delete(n); render(); ctl.back(this._room(n).target); });
    };
    el.addEventListener("click", () => { if (!ctl.dragged() && r) this._sheetRoom(n, el); });
    return { el, render };
  }

  // ---------- a number entity set by dragging (tile or slider); what was sent shows until the unit reports it ----------
  _numberDrag(handle, track, key, { tile = false, show, done } = {}) {
    const pend = this._pendingNum || (this._pendingNum = new Map());
    const range = () => {
      const st = this.st(key); if (!st || st.state === "unavailable") return null;
      const a = st.attributes, min = Number(a.min), max = Number(a.max), step = Number(a.step) || 1;
      let eff = step;  // a slider with more than ~120 positions gets coarser steps (e.g. a duration in minutes)
      for (const f of [1, 2, 5, 10, 15, 30, 60]) { eff = step * f; if ((max - min) / eff <= 120) break; }
      return { min, max, step: eff };
    };
    const value = () => {
      const p = pend.get(key), cur = this.num(key);
      if (p && (cur === p.v || Date.now() - p.at > 8000)) pend.delete(key);
      return pend.has(key) ? pend.get(key).v : cur ?? range().min;
    };
    const ctl = dragValue(handle, track, {
      tile, range, value, show,
      commit: v => {
        if (v === this.num(key)) return;
        pend.set(key, { v, at: Date.now() });
        this.call("number", "set_value", { entity_id: this.id(key), value: v }).then(() => done && done(),
          () => { pend.delete(key); ctl.back(this.num(key) ?? v); });
      },
    });
    return ctl;
  }
  _sliderRow(id, label, sub) {
    return `<div class="srow" id="${id}"><div class="srow-head"><span class="row-label">${label}${sub ? `<small>${sub}</small>` : ""}</span><b class="num sval"></b></div>
      <div class="slider" tabindex="0" role="slider" aria-label="${label}"><div class="s-rail"></div><div class="s-fill"></div><div class="s-knob"></div></div>
      <div class="s-ends num"><span class="s-min"></span><span class="s-max"></span></div></div>`;
  }
  _sliderShow(row, format) {  // how a slider row shows a value
    const sl = row.querySelector(".slider"), knob = row.querySelector(".s-knob"), fillEl = row.querySelector(".s-fill");
    return (v, snapped, r) => {
      const x = clamp((v - r.min) / (r.max - r.min), -0.04, 1.04) * sl.clientWidth;
      knob.style.transform = `translateX(${x.toFixed(1)}px)`; fillEl.style.width = `${clamp(x, 0, sl.clientWidth).toFixed(1)}px`;
      row.querySelector(".sval").textContent = format(snapped);
      row.querySelector(".s-min").textContent = format(r.min); row.querySelector(".s-max").textContent = format(r.max);
      sl.setAttribute("aria-valuenow", snapped); sl.setAttribute("aria-valuetext", format(snapped));
    };
  }
  _numberSlider(row, key, format) {  // a slider row for a number entity
    const ctl = this._numberDrag(row.querySelector(".slider"), row.querySelector(".slider"), key, { show: this._sliderShow(row, format) });
    requestAnimationFrame(() => ctl.sync());
    return ctl;
  }
  _unit(key, d = 0) {  // "46 °C", "1.500 W", "30 min": the number entity's own unit
    const u = ((this.st(key) || {}).attributes || {}).unit_of_measurement || "";
    return v => `${this.fmt(v, d)}${u ? (u === "°C" || u === "%" ? (u === "%" ? " %" : "°") : ` ${u}`) : ""}`;
  }

  // ---------- settings: grouped like iOS settings, every row an entity of this unit ----------
  _label(key) { const s = this.st(key); return this.t.s[key] || (s ? (s.attributes.friendly_name || key).replace(/^Proxon\s+/, "") : key); }
  _buildSettings() {
    this._settingsBuilt = true; this._settingCtl = [];
    const t = this.t, has = k => !!this.id(k);
    const html = SETTINGS.map(sec => {
      const rows = sec.rows.filter(r => r[0] === "days" ? has("Zeitprogramm0") : has(r[1]));
      if (!rows.length) return "";
      const body = rows.map(([kind, key]) => {
        const hint = (t.hint || {})[key];
        if (kind === "switch") return this._sw(`set-${key}`, this._label(key), hint);
        if (kind === "select") {
          const st = this.st(key), opts = st ? st.attributes.options || [] : [];
          const label = (o, i) => key === "LegionellenTag" ? t.daysShort[i] : (this._hass.formatEntityState ? this._hass.formatEntityState(st, o) : o);
          return `<div class="row"><span class="row-label">${this._label(key)}</span><div class="seg" id="sel-${key}">${opts.map((o, i) => `<button data-o="${o}">${label(o, i)}</button>`).join("")}</div></div>`;
        }
        if (kind === "num" && this._isLong(key)) return `<div class="row"><span class="row-label">${this._label(key)}</span>
          <div class="stepper"><button id="dn-${key}" aria-label="−">−</button><output class="num" id="out-${key}"></output><button id="up-${key}" aria-label="+">+</button></div></div>`;
        if (kind === "num") return this._sliderRow(`num-${key}`, this._label(key), hint);
        if (kind === "time") return `<div class="row"><span class="row-label">${this._label(key)}</span><input class="tin num" type="time" step="60" id="time-${key}" aria-label="${this._label(key)}"></div>`;
        if (kind === "datetime") return `<div class="row"><span class="row-label">${this._label(key)}</span><input class="tin num" type="datetime-local" id="dt-${key}" aria-label="${this._label(key)}"></div>`;
        if (kind === "button") return `<button class="textbtn warn" id="btn-${key}">${this._label(key)}</button>`;
        return t.days.map((name, d) => `<button class="day" id="day-${d}"><span>${name}</span><span class="num" id="day-sum-${d}"></span></button>`).join("");
      }).join("");
      const status = sec.status && has(sec.status) ? `<p class="foot" id="foot-${sec.id}"></p>` : "";
      return `<section class="group"><h2>${t.s[sec.id]}</h2><div class="card">${body}</div>${status}</section>`;
    }).join("");
    this.$("v-settings").innerHTML = `<div class="sgrid">${html}</div>`;
    const v = this.$("v-settings");
    for (const sec of SETTINGS) for (const [kind, key] of sec.rows) {
      if (kind === "switch" && v.querySelector(`#set-${CSS.escape(key)}`)) v.querySelector(`#set-${CSS.escape(key)}`).addEventListener("click", () => this._toggle(key));
      if (kind === "num" && v.querySelector(`#out-${CSS.escape(key)}`)) this._wireStepper(key);
      if (kind === "num" && v.querySelector(`#num-${CSS.escape(key)}`)) {
        const st = this.st(key), d = st && Number(st.attributes.step) < 1 ? 1 : 0;
        this._settingCtl.push(this._numberSlider(v.querySelector(`#num-${CSS.escape(key)}`), key, this._unit(key, d)));
      }
      const time = v.querySelector(`#time-${CSS.escape(key)}`);
      if (kind === "time" && time) time.addEventListener("change", () => { if (time.value) this.call("time", "set_value", { entity_id: this.id(key), time: `${time.value}:00` }).catch(() => this._updateSettings()); });
      const dt = v.querySelector(`#dt-${CSS.escape(key)}`);
      if (kind === "datetime" && dt) dt.addEventListener("change", () => { if (dt.value) this.call("datetime", "set_value", { entity_id: this.id(key), datetime: new Date(dt.value).toISOString() }).catch(() => this._updateSettings()); });
      if (kind === "select") v.querySelectorAll(`#sel-${CSS.escape(key)} button`).forEach(b => b.addEventListener("click", () =>
        this.call("select", "select_option", { entity_id: this.id(key), option: b.dataset.o }).catch(() => {})));
      const btn = v.querySelector(`#btn-${CSS.escape(key)}`);
      if (kind === "button" && btn) this._confirmButton(btn, () => this.call("button", "press", { entity_id: this.id(key) }).catch(() => {}));
    }
    for (let d = 0; d < 7; d++) { const b = v.querySelector(`#day-${d}`); if (b) b.addEventListener("click", () => this._sheetDay(d, b)); }
  }
  _isLong(key) { const a = (this.st(key) || {}).attributes || {}; return (a.max - a.min) / (Number(a.step) || 1) > 200; }
  _wireStepper(key) {  // taps in a row are sent once, 0.6 s after the last
    const v = this.$("v-settings"), out = v.querySelector(`#out-${CSS.escape(key)}`), fmt = this._unit(key, 0);
    const a = this.st(key).attributes, step = (Number(a.step) || 1) * 5;
    let want = null, timer = 0;
    const show = () => { out.textContent = fmt(want ?? this.num(key)); };
    const go = d => {
      want = clamp(Math.round(((want ?? this.num(key)) + d * step) / step) * step || Number(a.min), Number(a.min), Number(a.max)); show();
      clearTimeout(timer);
      timer = setTimeout(() => { const x = want; this.call("number", "set_value", { entity_id: this.id(key), value: x }).then(() => { want = null; show(); }, () => { want = null; show(); }); }, 600);
    };
    v.querySelector(`#dn-${CSS.escape(key)}`).addEventListener("click", () => go(-1));
    v.querySelector(`#up-${CSS.escape(key)}`).addEventListener("click", () => go(1));
    this._settingCtl.push({ sync: () => { if (want === null) show(); } });
  }
  _confirmButton(btn, act) {  // asks once, inline: a second tap within 4 s does it
    const label = btn.textContent; let armed = 0;
    btn.addEventListener("click", () => {
      if (Date.now() - armed < 4000) { armed = 0; btn.textContent = label; act(); return; }
      armed = Date.now(); btn.textContent = this.t.sure;
      setTimeout(() => { if (armed && Date.now() - armed >= 4000) { armed = 0; btn.textContent = label; } }, 4100);
    });
  }
  _updateSettings() {
    const v = this.$("v-settings"); if (!v) return;
    const focused = this.shadowRoot.activeElement;
    for (const sec of SETTINGS) {
      for (const [kind, key] of sec.rows) {
        const st = this.st(key);
        if (kind === "switch") { const b = v.querySelector(`#set-${CSS.escape(key)}`); if (b && st) b.setAttribute("aria-checked", st.state === "on"); }
        if (kind === "select") v.querySelectorAll(`#sel-${CSS.escape(key)} button`).forEach(b => b.setAttribute("aria-pressed", !!st && b.dataset.o === st.state));
        if (kind === "time") {
          const i = v.querySelector(`#time-${CSS.escape(key)}`);
          if (i && st && i !== focused) i.value = /^\d\d:\d\d/.test(st.state) ? st.state.slice(0, 5) : "";
        }
        if (kind === "datetime") {
          const i = v.querySelector(`#dt-${CSS.escape(key)}`);
          if (i && st && i !== focused) {
            const d = new Date(st.state);
            i.value = isNaN(d) ? "" : new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
          }
        }
      }
      const foot = v.querySelector(`#foot-${sec.id}`), st = sec.status && this.st(sec.status);
      if (foot && st) foot.textContent = `${this.t.status}: ${this._hass.formatEntityState ? this._hass.formatEntityState(st) : st.state}`;
    }
    for (let d = 0; d < 7; d++) {
      const el = v.querySelector(`#day-sum-${d}`);
      if (el) el.textContent = this._daySummary(d);
    }
    (this._settingCtl || []).forEach(c => c.sync());
  }
  _daySummary(d) {
    const st = this.st(`Zeitprogramm${d}`); if (!st) return this.t.empty;
    const a = st.attributes || {}, parts = [1, 2, 3].map(i => a[`phase_${i}`]).filter(p => p && p.active && p.level > 0)
      .map(p => `${p.start}–${p.end} ${this.t.lvl} ${p.level}`);
    return parts.length ? parts.join(" · ") : this.t.empty;
  }
  _sheetDay(d, from) {
    const t = this.t;
    const phase = p => {
      const sel = this.st(`ZP${d}_${p}_stufe`), opts = sel ? sel.attributes.options || [] : [];
      return `<div class="phase"><span class="row-label">${fill(t.phase, { n: p + 1 })}</span>
        <div class="phase-times"><input class="tin num" type="time" step="60" id="ph-${p}-start" aria-label="${fill(t.phase, { n: p + 1 })} ${t.from}">
          <span>–</span><input class="tin num" type="time" step="60" id="ph-${p}-end" aria-label="${fill(t.phase, { n: p + 1 })} ${t.to}"></div>
        ${sel ? `<div class="seg" id="ph-${p}-lvl">${opts.map(o => `<button data-o="${o}">${this._hass.formatEntityState ? this._hass.formatEntityState(sel, o) : o}</button>`).join("")}</div>` : ""}</div>`;
    };
    const copy = d === 0 ? ["ZeitprogrammMoDiFr", "ZeitprogrammMoAlle"].filter(k => this.id(k)) : [];
    this._openSheet(`<h3>${t.days[d]}</h3><p class="sub" id="day-sub"></p>${[0, 1, 2].map(phase).join("")}
      ${copy.map(k => `<button class="textbtn" id="cp-${k}">${k.endsWith("MoDiFr") ? t.copyWeekdays : t.copyAll}</button>`).join("")}`, from, () => {
      for (let p = 0; p < 3; p++) {
        for (const w of ["start", "end"]) {
          const i = this.$(`ph-${p}-${w}`);
          i.addEventListener("change", () => { if (i.value) this.call("time", "set_value", { entity_id: this.id(`ZP${d}_${p}_${w}`), time: `${i.value}:00` }).catch(() => this._sheetRefresh && this._sheetRefresh()); });
        }
        this.shadowRoot.querySelectorAll(`#ph-${p}-lvl button`).forEach(b => b.addEventListener("click", () =>
          this.call("select", "select_option", { entity_id: this.id(`ZP${d}_${p}_stufe`), option: b.dataset.o }).catch(() => {})));
      }
      copy.forEach(k => this._confirmButton(this.$(`cp-${k}`), () => this.call("button", "press", { entity_id: this.id(k) }).catch(() => {})));
    }, () => {
      this.$("day-sub").textContent = this._daySummary(d);
      const focused = this.shadowRoot.activeElement;
      for (let p = 0; p < 3; p++) {
        for (const w of ["start", "end"]) {
          const i = this.$(`ph-${p}-${w}`), st = this.st(`ZP${d}_${p}_${w}`);
          if (i && i !== focused) i.value = st && /^\d\d:\d\d/.test(st.state) ? st.state.slice(0, 5) : "";
        }
        const sel = this.st(`ZP${d}_${p}_stufe`);
        this.shadowRoot.querySelectorAll(`#ph-${p}-lvl button`).forEach(b => b.setAttribute("aria-pressed", !!sel && b.dataset.o === sel.state));
      }
    });
  }

  // ---------- sheet ----------
  _buildSheet() {
    const sheet = this.$("sheet"), scrim = this.$("scrim");
    this._sheetY = new Spring(1, v => { sheet.style.transform = `translate(-50%, ${(v * 110).toFixed(2)}%)`; scrim.style.opacity = clamp(1 - v, 0, 1).toFixed(3); });
    this.$("sheet-close").addEventListener("click", () => this._closeSheet());
    scrim.addEventListener("click", () => this._closeSheet());
    this.shadowRoot.addEventListener("keydown", e => { if (e.key === "Escape" && !sheet.hidden) this._closeSheet(); });
    let sd = null;
    sheet.addEventListener("pointerdown", e => {
      if (e.target.closest("button, input, .level, .slider") || sheet.scrollTop > 0) return;
      sd = { y: e.clientY, v: this._sheetY.x, h: sheet.offsetHeight, hist: [{ y: e.clientY, t: e.timeStamp }] }; sheet.setPointerCapture(e.pointerId);
    });
    sheet.addEventListener("pointermove", e => {
      if (!sd) return;
      sd.hist.push({ y: e.clientY, t: e.timeStamp }); if (sd.hist.length > 6) sd.hist.shift();
      let v = sd.v + (e.clientY - sd.y) / (sd.h * 1.1); if (v < 0) v = -rubber(-v, 0.3);
      this._sheetY.set(v);
    });
    const up = () => {
      if (!sd) return;
      const a = sd.hist[0], b = sd.hist[sd.hist.length - 1], vel = (b.y - a.y) / Math.max(1, b.t - a.t) * 1000, rel = vel / (sd.h * 1.1);
      if (this._sheetY.x + project(vel) / (sd.h * 1.1) > 0.45) this._closeSheet(rel); else this._sheetY.to(0, { damping: 0.8, response: 0.3, velocity: rel });
      sd = null;
    };
    sheet.addEventListener("pointerup", up); sheet.addEventListener("pointercancel", up);
  }
  _openSheet(html, from, wire, refresh) {
    this._opener = from; this._sheetCtl = []; this.$("sheet-body").innerHTML = html; this.$("sheet").hidden = false; this.$("scrim").style.pointerEvents = "auto";
    wire(); this._sheetRefresh = refresh || null; if (refresh) refresh();
    this._sheetY.to(0, { damping: 0.8, response: 0.3 });
    requestAnimationFrame(() => this.$("sheet-close").focus());
  }
  _closeSheet(velocity) {
    this.$("scrim").style.pointerEvents = "none"; this._sheetRefresh = null;
    this._sheetY.to(1, { damping: 1, response: 0.3, velocity, onRest: () => { this.$("sheet").hidden = true; } });
    if (this._opener) this._opener.focus();
  }
  _sw(id, label, sub) {
    return `<div class="row"><span class="row-label">${label}${sub ? `<small>${sub}</small>` : ""}</span><button class="switch" role="switch" id="${id}" aria-label="${label}" aria-checked="false"></button></div>`;
  }
  _toggle(key) { const e = this.id(key); if (e) this.call("switch", "toggle", { entity_id: e }).catch(() => {}); }

  _sheetVentilation(from) {
    const t = this.t, sel = this.st("Betriebsart"), opts = sel ? sel.attributes.options || [] : [];
    const label = o => (this._hass.formatEntityState ? this._hass.formatEntityState(sel, o) : o);
    const hasLevel = !!this.id("Luefterstufe");
    this._openSheet(`<h3>${t.ventilation}</h3><p class="sub" id="v-sub"></p>
      ${hasLevel ? `<div class="row-label">${t.level}</div><div class="level" id="level" role="slider" tabindex="0" aria-label="${t.level}" aria-valuemin="1" aria-valuemax="4">
        <div class="rail"></div><div class="rail-fill"></div>${[1, 2, 3, 4].map(n => `<span class="tick" data-n="${n}">${n}</span>`).join("")}<div class="knob"></div></div>
        <p class="level-note" id="level-note" hidden>${t.levelAuto}</p>` : ""}
      ${sel ? `<div class="row"><span class="row-label">${t.mode}</span><div class="seg" id="mode">${opts.map(o => `<button data-o="${o}">${label(o)}</button>`).join("")}</div></div>` : ""}
      ${this.id("Intensivlueftung") ? this._sw("s-boost", t.boost, this.num("IntensivlueftungsDauer") ? fill(t.boostSub, { m: this.fmt(this.num("IntensivlueftungsDauer"), 0) }) : "") : ""}
      <button class="link" id="v-more">${t.more}</button>`, from, () => {
      this.$("v-more").addEventListener("click", () => this._sheetAll("unit", from));
      const sb = this.$("s-boost"); if (sb) sb.addEventListener("click", () => this._toggle("Intensivlueftung"));
      this.shadowRoot.querySelectorAll("#mode button").forEach(b => b.addEventListener("click", () => {
        this.call("select", "select_option", { entity_id: this.id("Betriebsart"), option: b.dataset.o }).catch(() => {});
      }));
      if (hasLevel) this._wireLevel();
    }, () => {
      this.$("v-sub").textContent = `${t.supply} ${this.$("v-supply").textContent} · ${t.extract} ${this.$("v-extract").textContent} · ${this.$("rpm-s").textContent} U/min`;
      const m = this.st("Betriebsart"); this.shadowRoot.querySelectorAll("#mode button").forEach(b => b.setAttribute("aria-pressed", !!m && b.dataset.o === m.state));
      const sb = this.$("s-boost"); if (sb) sb.setAttribute("aria-checked", (this.st("Intensivlueftung") || {}).state === "on");
      const auto = (m && m.state === "eco_comfort") || (this.st("Intensivlueftung") || {}).state === "on";
      const lv = this.$("level"); if (lv) { lv.classList.toggle("auto", auto); lv.setAttribute("aria-disabled", auto); this.$("level-note").hidden = !auto; }
      if (this._levelSync) this._levelSync();
    });
  }
  _wireLevel() {
    const lv = this.$("level"), knob = lv.querySelector(".knob"), fillEl = lv.querySelector(".rail-fill");
    const xOf = n => (n - 1) / 3 * lv.clientWidth;
    const shownLevel = () => this.num("IstLuefterstufe") ?? this.num("Luefterstufe");
    const k = new Spring(shownLevel() || 1, v => {
      const x = clamp(xOf(v), -12, lv.clientWidth + 12);
      knob.style.transform = `translateX(${x.toFixed(1)}px)`; fillEl.style.width = `${clamp(x, 0, lv.clientWidth).toFixed(1)}px`;
    });
    let chosen = null, d = null;
    requestAnimationFrame(() => { lv.querySelectorAll(".tick").forEach(t => { t.style.left = `${xOf(+t.dataset.n)}px`; }); k.set(k.x); });
    const mark = n => { lv.setAttribute("aria-valuenow", n); lv.querySelectorAll(".tick").forEach(t => t.classList.toggle("on", +t.dataset.n === n)); };
    const choose = (n, velocity) => {
      n = clamp(n, 1, 4); chosen = n; mark(n);
      k.to(n, { damping: velocity ? 0.8 : 1, response: 0.3, velocity });
      if (n !== this.num("Luefterstufe")) this.call("number", "set_value", { entity_id: this.id("Luefterstufe"), value: n }).catch(() => {
        chosen = null; const cur = this.num("Luefterstufe") || 1; mark(cur); k.to(cur, { damping: 1, response: 0.35 });  // back to what the unit has
      });
    };
    this._levelSync = () => {  // follows the unit, except while a choice is on its way
      const cur = shownLevel(); if (cur === null || d) return;
      if (chosen !== null && cur !== chosen) return;
      chosen = null; mark(cur); if (!activeSprings.has(k)) k.set(cur);
    };
    lv.addEventListener("pointerdown", e => {
      lv.setPointerCapture(e.pointerId);
      d = { grab: e.clientX - lv.getBoundingClientRect().left - xOf(k.x), hist: [{ x: e.clientX, t: e.timeStamp }], moved: false, x0: e.clientX };
    });
    lv.addEventListener("pointermove", e => {
      if (!d) return;
      if (Math.abs(e.clientX - d.x0) > 4) d.moved = true;
      d.hist.push({ x: e.clientX, t: e.timeStamp }); if (d.hist.length > 6) d.hist.shift();
      let v = 1 + (e.clientX - lv.getBoundingClientRect().left - d.grab) / lv.clientWidth * 3;
      if (v > 4) v = 4 + rubber(v - 4, 1); if (v < 1) v = 1 - rubber(1 - v, 1);
      k.set(v);
    });
    const up = e => {
      if (!d) return;
      const dd = d; d = null;
      if (!dd.moved) { choose(Math.round(1 + (e.clientX - lv.getBoundingClientRect().left) / lv.clientWidth * 3)); return; }
      const a = dd.hist[0], b = dd.hist[dd.hist.length - 1], vel = (b.x - a.x) / Math.max(1, b.t - a.t) * 1000 / lv.clientWidth * 3;
      choose(Math.round(k.x + clamp(project(vel * 100, SETTING) / 100, -1, 1)), clamp(vel, -12, 12));
    };
    lv.addEventListener("pointerup", up); lv.addEventListener("pointercancel", up);
    lv.addEventListener("keydown", e => { const s = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key]; if (s) { e.preventDefault(); choose((chosen || this.num("Luefterstufe") || 1) + s); } });
  }
  _sheetWater(from) {
    const t = this.t, n = this.st("SollWassertemperatur");
    this._openSheet(`<h3>${t.water}</h3><p class="sub" id="w-sub"></p>
      ${n ? this._sliderRow("wt-row", t.waterTarget) : ""}
      ${this.id("T300Betriebsart") ? this._sw("s-pump", t.pump, t.pumpSub) : ""}${this.id("E-Heizstab") ? this._sw("s-heater", t.heater, t.heaterSub) : ""}
      <button class="link" id="w-more">${t.more}</button>`, from, () => {
      this._sheetCtl = n ? [this._numberSlider(this.$("wt-row"), "SollWassertemperatur", v => `${this.fmt(v, 0)} °C`)] : [];
      ["s-pump", "s-heater"].forEach((id, i) => { const b = this.$(id); if (b) b.addEventListener("click", () => this._toggle(i ? "E-Heizstab" : "T300Betriebsart")); });
      this.$("w-more").addEventListener("click", () => this._sheetAll("water", from));
    }, () => {
      this.$("w-sub").textContent = `${this.$("w-temp").textContent} · ${t.bottom} ${this.$("w-bottom").textContent}`;
      (this._sheetCtl || []).forEach(c => c.sync());
      [["s-pump", "T300Betriebsart"], ["s-heater", "E-Heizstab"]].forEach(([id, k]) => { const b = this.$(id); if (b) b.setAttribute("aria-checked", (this.st(k) || {}).state === "on"); });
    });
  }
  _sheetRoom(n, from) {
    const t = this.t, r = this._room(n), d = r.step < 1 ? 1 : 0;
    this._openSheet(`<h3>${r.name}</h3><p class="sub" id="r-sub"></p>
      ${this._sliderRow("rt-row", t.target, fill(t.range, { a: this.fmt(r.min, 0), b: this.fmt(r.max, 0), s: this.fmt(r.step, d) }))}
      ${this._sw("s-elem", t.released, t.releasedSub)}<p class="hint">${t.dragHint}</p><button class="link" id="r-more">${t.more}</button>`, from, () => {
      const row = this.$("rt-row"), sl = row.querySelector(".slider");
      const ctl = dragValue(sl, sl, {
        range: () => { const c = this._room(n); return c && { min: c.min, max: c.max, step: c.step }; },
        value: () => this._room(n).target, show: this._sliderShow(row, v => `${this.fmt(v, d)} °C`),
        commit: v => {
          const cur = this._room(n); if (v === cur.target) return;
          this._pending.set(n, { v, at: Date.now() }); this._updateRooms();
          this.call("climate", "set_temperature", { entity_id: cur.entity, temperature: v }).catch(() => { this._pending.delete(n); this._update(); ctl.back(this._room(n).target); });
        },
      });
      this._sheetCtl = [ctl]; requestAnimationFrame(() => ctl.sync());
      this.$("s-elem").addEventListener("click", () => {
        const cur = this._room(n);
        this.call("climate", "set_hvac_mode", { entity_id: cur.entity, hvac_mode: cur.mode === "heat" ? "auto" : "heat" }).catch(() => {});
      });
      this.$("r-more").addEventListener("click", () => { this._closeSheet(); this.moreInfo(r.entity); });
    }, () => {
      const cur = this._room(n); if (!cur) return;
      this.$("r-sub").textContent = `${t.now} ${this.fmt(cur.temp)}° · ${t.element[cur.element] || ""}`;
      (this._sheetCtl || []).forEach(c => c.sync());
      this.$("s-elem").setAttribute("aria-checked", cur.mode === "heat");
    });
  }

  // ---------- all values of the unit or the hot water: every entity of that part, grouped, live; tap for its history ----------
  _sheetAll(kind, from) {
    const t = this.t, ents = (this._config || {}).entities || {};
    const skip = /^(NBE\d|ZP\d|Zeitprogramm|Urlaub|Waermeelemente|Bild|Saison|Nachtkuehl|Kuehl|Nachtabsenkung|Stromkosten|Energie|Leistung)/;
    const water = /^(Warmwasser|T300|E-Heizstab|Soll-E-Heizstab|SollWasser|Legionell|PVSignal|PVFreigabe|Speicher|Solar|Preis|Boost|Energiemanager|FirmwareT300|Heizstab)/;
    const keys = Object.keys(ents).filter(k => !skip.test(k) && (kind === "water" ? water.test(k) : !water.test(k)) && this._hass.states[ents[k]]);
    const domain = k => ents[k].split(".")[0];
    const group = k => {
      const st = this._hass.states[ents[k]], d = domain(k);
      if (d === "sensor" && (st.attributes.unit_of_measurement || "") === "°C") return "temp";
      if (d === "sensor") return "meas";
      if (d === "binary_sensor") return "state";
      return ["button", "image"].includes(d) ? null : "set";
    };
    const name = k => (this._hass.states[ents[k]].attributes.friendly_name || k).replace(/^Proxon\s+/, "");
    const groups = ["temp", "meas", "state", "set"].map(g => [g, keys.filter(k => group(k) === g).sort((a, b) => name(a).localeCompare(name(b)))]).filter(([, l]) => l.length);
    const device = (this._config || {}).device_id;
    this._openSheet(`<h3>${kind === "water" ? t.water : t.unit}</h3><p class="sub">${t.more}</p>
      ${groups.map(([g, list]) => `<div class="label" style="margin-top:14px">${t.groups[g]}</div>
        ${list.map(k => `<button class="day" data-e="${ents[k]}"><span>${name(k)}</span><span class="num" data-v="${ents[k]}"></span></button>`).join("")}`).join("")}
      ${device ? `<button class="link" id="all-device">${t.device}</button>` : ""}`, from, () => {
      this.shadowRoot.querySelectorAll("#sheet-body [data-e]").forEach(b => b.addEventListener("click", () => this.moreInfo(b.dataset.e)));
      const dev = this.$("all-device");
      if (dev) dev.addEventListener("click", () => {
        this._closeSheet();
        history.pushState(null, "", `/config/devices/device/${device}`);
        window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
      });
    }, () => {
      this.shadowRoot.querySelectorAll("#sheet-body [data-v]").forEach(el => {
        const st = this._hass.states[el.dataset.v];
        el.textContent = !st ? "–" : this._hass.formatEntityState ? this._hass.formatEntityState(st) : st.state;
      });
    });
  }

  // ---------- undo toast ----------
  _buildToast() {
    const el = this.$("toast");
    this._toastY = new Spring(1.6, v => { el.style.transform = `translate(-50%, ${(v * 100).toFixed(1)}%)`; });
    this.$("toast-undo").addEventListener("click", () => { const u = this._undo; this._hideToast(); if (u) u().catch(() => {}); });
  }
  _toast(text, undo) {
    this.$("toast-text").textContent = text; this._undo = undo; this.$("toast-undo").hidden = !undo; this.$("toast").hidden = false;
    this._toastY.to(0, { damping: 0.85, response: 0.35 });
    clearTimeout(this._toastTimer); this._toastTimer = setTimeout(() => this._hideToast(), 5000);
  }
  _hideToast() { this._undo = null; this._toastY.to(1.6, { damping: 1, response: 0.3, onRest: () => { this.$("toast").hidden = true; } }); }
}

if (!customElements.get("proxon-panel")) customElements.define("proxon-panel", ProxonPanel);
