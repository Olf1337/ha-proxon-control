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
    water: "Warmwasser", shower: "Reicht für ca. {m} Min. Duschen", bottom: "Unten", target: "Soll", charge: "Ladezustand",
    floors: { "0": "Erdgeschoss", "1": "Obergeschoss", "-1": "Keller" }, rooms: "Räume", sent: "✓ gesendet",
    element: { off: "Heizpanel aus", ready: "Heizpanel bereit", heating: "Heizpanel heizt" },
    ventilation: "Lüftung", mode: "Betriebsart", boostSub: "läuft {m} Minuten, dann zurück", waterTarget: "Solltemperatur",
    pump: "Wärmepumpe", pumpSub: "heizt das Wasser sparsam", heater: "Heizstab", heaterSub: "schneller, braucht mehr Strom",
    now: "Jetzt", range: "{a} bis {b} °C in {s}-°C-Schritten", released: "Heizpanel freigegeben",
    releasedSub: "heizt elektrisch zu, wenn der Raum zu kalt ist", dragHint: "Auf der Kachel geht es schneller: zur Seite ziehen.",
    more: "Alle Werte", close: "Schließen", warmer: "Wärmer", colder: "Kälter", off: "{f} aus", undo: "Rückgängig",
    end: "{f} beenden", unavailable: "nicht erreichbar", levelAuto: "Im ECO-Komfortbetrieb und während der Intensivlüftung wählt die Anlage die Stufe selbst.",
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
    water: "Hot water", shower: "Enough for about {m} min of showering", bottom: "Bottom", target: "Target", charge: "Charge",
    floors: { "0": "Ground floor", "1": "Upper floor", "-1": "Basement" }, rooms: "Rooms", sent: "✓ sent",
    element: { off: "Heating panel off", ready: "Heating panel ready", heating: "Heating panel heating" },
    ventilation: "Ventilation", mode: "Operating mode", boostSub: "runs {m} minutes, then back", waterTarget: "Target temperature",
    pump: "Heat pump", pumpSub: "heats the water efficiently", heater: "Immersion heater", heaterSub: "faster, uses more power",
    now: "Now", range: "{a} to {b} °C in {s} °C steps", released: "Heating panel enabled",
    releasedSub: "heats electrically when the room is too cold", dragHint: "Quicker on the tile: drag it sideways.",
    more: "All values", close: "Close", warmer: "Warmer", colder: "Colder", off: "{f} off", undo: "Undo",
    end: "End {f}", unavailable: "unavailable", levelAuto: "In ECO comfort mode and during boost ventilation the unit chooses the level itself.",
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
  { k: "legionella", sw: "LegionellenSonne", run: st => String(st.attributes.status || "").startsWith("heating"), tint: "--water-hot",
    icon: "M12 3c3 4 6 6.5 6 10a6 6 0 0 1-12 0c0-3.5 3-6 6-10zM10 14a2 2 0 0 0 2 2" },
  { k: "cooling", sw: "Nachtkuehlung", run: st => ["cooling", "heat_protection"].includes(st.attributes.status), tint: "--cold",
    icon: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" },
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

const STYLE = `
:host {
  --bg: #eef1f4; --surface: rgba(255,255,255,.78); --surface-solid: #fff; --line: rgba(20,32,45,.08); --fg: #14202d; --fg-2: #586675;
  --fg-3: #8a96a3; --accent: #1d8a7a; --fresh: #3b8fd9; --supply: #e08a3c; --extract: #c26d7e; --exhaust: #8b97a4; --cold: #3b82d6;
  --fine: #1f9d6c; --warm: #d8602f; --flame: #ff6a2b; --water-hot: #f07a3a; --water-cool: #f6c79a; --danger: #d64545;
  --scrim: rgba(10,18,28,.32); --shadow: 0 1px 2px rgba(20,32,45,.06), 0 8px 24px rgba(20,32,45,.06); --sheet-shadow: 0 -10px 40px rgba(10,18,28,.18);
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, sans-serif;
  --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, "Segoe UI", Roboto, sans-serif;
  display: block; min-height: 100%; background: var(--bg); color: var(--fg); font: 16px/1.45 var(--font); -webkit-tap-highlight-color: transparent;
}
:host([dark]) {
  --bg: #0e1318; --surface: rgba(28,35,43,.78); --surface-solid: #1c232b; --line: rgba(255,255,255,.07); --fg: #eef2f5; --fg-2: #a3afbb;
  --fg-3: #6f7c89; --accent: #3cc3ab; --fresh: #5aa8ec; --supply: #f0a056; --extract: #d98a9a; --exhaust: #7d8a97; --cold: #5c9ceb;
  --fine: #3cc08a; --warm: #f07b4a; --flame: #ff7a3d; --water-hot: #f58a4c; --water-cool: #7a5236; --danger: #f06a6a;
  --scrim: rgba(0,0,0,.5); --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 24px rgba(0,0,0,.25); --sheet-shadow: 0 -10px 40px rgba(0,0,0,.5);
  color-scheme: dark;
}
* { box-sizing: border-box; }
button { font: inherit; color: inherit; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 12px; }
.num { font-variant-numeric: tabular-nums; }
.page { max-width: 1120px; margin: 0 auto; display: grid; gap: 20px; padding: 20px max(16px, env(safe-area-inset-right, 0px)) 48px max(16px, env(safe-area-inset-left, 0px)); }
.status { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; }
.status h1 { font: 700 1.6rem/1.1 var(--font-display); letter-spacing: -.02em; margin: 0 auto 0 0; display: flex; align-items: center; gap: 6px; }
.menu { width: 40px; height: 40px; border: 0; border-radius: 12px; background: none; cursor: pointer; display: grid; place-items: center; margin-left: -8px; }
.menu svg { width: 24px; height: 24px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; background: var(--surface); border: 1px solid var(--line);
  font-size: .875rem; color: var(--fg-2); backdrop-filter: blur(20px) saturate(160%); -webkit-backdrop-filter: blur(20px) saturate(160%); }
.chip b { color: var(--fg); font-weight: 600; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--fine); }
.top { display: grid; grid-template-columns: minmax(0,2fr) minmax(0,1fr); gap: 20px; }
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
.water-body { display: flex; gap: 18px; align-items: center; margin-top: 10px; }
.tank { flex: none; width: 74px; height: 170px; }
.water-big { font: 700 3rem/1 var(--font-display); letter-spacing: -.03em; }
.water-big small { font-size: 1.4rem; font-weight: 600; color: var(--fg-2); }
.water-lines { display: grid; gap: 6px; margin-top: 10px; font-size: .875rem; color: var(--fg-2); }
.water-lines b { color: var(--fg); font-weight: 600; }
.working { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; padding: 5px 10px; border-radius: 999px;
  background: color-mix(in srgb, var(--water-hot) 14%, transparent); font-size: .8125rem; font-weight: 600; }
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
  background: var(--surface-solid); border-radius: 26px 26px 0 0; box-shadow: var(--sheet-shadow); touch-action: none; overscroll-behavior: contain;
  padding: 8px max(20px, env(safe-area-inset-right, 0px)) calc(24px + env(safe-area-inset-bottom, 0px)) max(20px, env(safe-area-inset-left, 0px)); }
.grabber { width: 40px; height: 5px; border-radius: 3px; background: var(--fg-3); opacity: .5; margin: 4px auto 14px; }
.sheet h3 { font: 700 1.4rem/1.15 var(--font-display); letter-spacing: -.02em; margin: 0 0 4px; }
.sub { color: var(--fg-2); font-size: .9375rem; margin: 0 0 18px; }
.row { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 14px 0; border-top: 1px solid var(--line); flex-wrap: wrap; }
.row-label { font-weight: 600; }
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
@media (prefers-reduced-transparency: reduce) { .card, .chip, .fn, .toast { background: var(--surface-solid); backdrop-filter: none; -webkit-backdrop-filter: none; } }
@media (prefers-reduced-motion: reduce) { button.card, .switch::after, .stepper button, .unit-tap, .pill-switch { transition: none; } }
`;

const FAN = '<circle r="12" fill="var(--surface-solid)" stroke="var(--line)"/><path d="M0-8C3-8 4-3 0 0 -4-3-3-8 0-8ZM8 0C8 3 3 4 0 0 3-4 8-3 8 0ZM0 8C-3 8-4 3 0 0 4 3 3 8 0 8ZM-8 0C-8-3-3-4 0 0-3 4-8 3-8 0Z" fill="var(--fg-2)"/>';
const FLAME = '<path d="M14 0C20 12 28 16 26 28 24 37 4 37 2 28 0 19 8 14 14 0Z" fill="var(--flame)"/><path d="M14 13C16 19 21 22 19 28 18 32 10 32 9 28 8 23 13 20 14 13Z" fill="#ffd166"/>';
const RADIATOR = '<path d="M5 6v12M9.5 6v12M14 6v12M18.5 6v12M3 8h18M3 16h18" stroke="var(--fg-2)" stroke-width="1.8" fill="none" stroke-linecap="round"/>';
const svgNS = "http://www.w3.org/2000/svg";

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
      <div class="page">
        <header class="status">
          <h1><button class="menu" id="menu" aria-label="Menu" ${this._narrow ? "" : "hidden"}><svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg></button>${t.title}</h1>
          <span class="chip">${t.outside} <b class="num" id="c-out">–</b></span>
          <span class="chip" id="c-op-wrap">${t.op} <b id="c-op">–</b></span>
          <span class="chip"><span class="dot" id="c-dot"></span><b id="c-ok">${t.ok}</b></span>
        </header>
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
            <div class="card-head"><span class="label">${t.water}</span><span class="hint">${t.tapUnit}</span></div>
            <div class="water-body">
              <svg class="tank" viewBox="0 0 74 170" aria-hidden="true">
                <defs><clipPath id="tank-clip"><rect x="4" y="4" width="66" height="162" rx="30"/></clipPath>
                  <linearGradient id="wg" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="var(--water-cool)"/><stop offset="1" stop-color="var(--water-hot)"/></linearGradient></defs>
                <rect x="4" y="4" width="66" height="162" rx="30" fill="var(--line)"/>
                <g clip-path="url(#tank-clip)"><rect id="w-fill" x="0" y="170" width="74" height="170" fill="url(#wg)"/></g>
              </svg>
              <div><div class="water-big num" id="w-temp">–</div>
                <div class="water-lines"><span id="w-shower"></span><span>${t.bottom} <b class="num" id="w-bottom">–</b> · ${t.target} <b class="num" id="w-target">–</b></span>
                  <span id="w-charge-wrap">${t.charge} <b class="num" id="w-charge">–</b></span></div>
                <span class="working" id="w-working" hidden><svg width="14" height="14" viewBox="0 0 28 37" aria-hidden="true">${FLAME}</svg><span id="w-who"></span></span></div>
            </div>
          </button>
        </section>
        <div id="floors"></div>
      </div>
      <div class="toast" id="toast" role="status" hidden><span id="toast-text"></span><button id="toast-undo">${t.undo}</button></div>
      <div class="scrim" id="scrim"></div>
      <div class="sheet" id="sheet" role="dialog" aria-modal="true" hidden><div class="grabber"></div>
        <button class="close" id="sheet-close" aria-label="${t.close}">✕</button><div id="sheet-body"></div></div>`;
    this.$("menu").addEventListener("click", () => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    this.$("boost").addEventListener("click", () => this._toggle("Intensivlueftung"));
    this.$("unit").addEventListener("click", e => this._sheetVentilation(e.currentTarget));
    this.$("water").addEventListener("click", e => this._sheetWater(e.currentTarget));
    this._fill = new Spring(0, v => this.$("w-fill").setAttribute("y", (170 * (1 - v)).toFixed(1)));
    this._wrapH = new Spring(0, v => { this.$("active-wrap").style.height = `${v.toFixed(1)}px`; });
    this._buildSheet();
    this._buildToast();
    this._buildAir();
    this._startAir();
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
      this.$("w-temp").innerHTML = w === null ? "–" : `${this.fmt(w)}<small>°</small>`;
      const sh = this.num("WarmwasserDuschminuten");
      this.$("w-shower").hidden = sh === null; this.$("w-shower").innerHTML = fill(t.shower, { m: `<b class="num">${this.fmt(sh, 0)}</b>` });
      this.$("w-bottom").textContent = deg("WarmwasserUntenTemperatur");
      const wt = this.num("SollWassertemperatur"); this.$("w-target").textContent = wt === null ? "–" : `${this.fmt(wt, 0)}°`;
      const ch = this.num("WarmwasserLadezustand");
      this.$("w-charge-wrap").hidden = ch === null; this.$("w-charge").textContent = `${this.fmt(ch, 0)} %`;
      const level = ch !== null ? ch / 100 : w !== null && wt ? clamp((w - 20) / Math.max(1, wt - 20), 0, 1) : 0;
      if (Math.abs((this._fill.target || 0) - level) > 0.001) this._fill.to(level, { damping: 1, response: 0.8 });
    }
    this._updateFunctions();
    this._updateRooms();
    if (this._sheetRefresh) this._sheetRefresh();
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
    this.$("w-working").hidden = !who; this.$("w-who").textContent = who;
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
      const entity = this.id(f.sw);
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
    let r = null, shown = null, dragging = false, start = null, hist = [], dragged = false;
    const frac = v => r ? (v - r.min) / (r.max - r.min) : 0;
    const digits = () => (r && r.step < 1 ? 1 : 0);
    const pos = new Spring(0, v => {
      mark.style.transform = `translateX(${(frac(v) * track.clientWidth).toFixed(1)}px)`;
      if (!r) return;
      const snapped = clamp(Math.round(v / r.step) * r.step, r.min, r.max);
      if (snapped !== shown) { shown = snapped; $(".tv").textContent = `${this.fmt(snapped, digits())}°`; }
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
      if (!dragging && !activeSprings.has(pos)) { shown = null; pos.set(r.target); }
    };
    const commit = v => {
      if (!r || v === r.target) return;
      this._pending.set(n, { v, at: Date.now() });
      this.call("climate", "set_temperature", { entity_id: r.entity, temperature: v }).then(() => {
        const s = $(".saved"); s.classList.add("show"); setTimeout(() => s.classList.remove("show"), 1400);
      }, () => { this._pending.delete(n); render(); pos.to(this._room(n).target, { damping: 1, response: 0.35 }); });
    };
    el.addEventListener("pointerdown", e => {
      if (!r) return;
      start = { x: e.clientX, y: e.clientY, v: pos.x, id: e.pointerId }; dragging = false; hist = [{ x: e.clientX, t: e.timeStamp }];
      el.classList.add("pressed");
    });
    el.addEventListener("pointermove", e => {
      if (!start || e.pointerId !== start.id) return;
      const dx = e.clientX - start.x, dy = e.clientY - start.y;
      if (!dragging) {
        if (Math.abs(dy) > 10 && Math.abs(dy) > Math.abs(dx)) { start = null; el.classList.remove("pressed"); return; }
        if (Math.abs(dx) < 10) return;
        dragging = true; el.setPointerCapture(e.pointerId); el.classList.add("dragging"); el.classList.remove("pressed");
      }
      hist.push({ x: e.clientX, t: e.timeStamp }); if (hist.length > 6) hist.shift();
      const per = track.clientWidth / (r.max - r.min);
      let v = start.v + dx / per;
      if (v > r.max) v = r.max + rubber(v - r.max, 1.2); if (v < r.min) v = r.min - rubber(r.min - v, 1.2);
      pos.set(v);
    });
    const end = () => {
      el.classList.remove("pressed");
      if (!start) return;
      if (dragging) {
        const a = hist[0], b = hist[hist.length - 1], per = track.clientWidth / (r.max - r.min);
        const vel = (b.x - a.x) / Math.max(1, b.t - a.t) * 1000 / per;
        const target = clamp(Math.round((pos.x + project(vel * per, SETTING) / per) / r.step) * r.step, r.min, r.max);
        pos.to(target, { damping: 0.8, response: 0.35, velocity: vel, onRest: () => commit(target) });
        el.classList.remove("dragging");
        dragged = true; setTimeout(() => { dragged = false; }, 0);
      }
      start = null; dragging = false;
    };
    el.addEventListener("pointerup", end); el.addEventListener("pointercancel", end);
    el.addEventListener("click", () => { if (!dragged && r) this._sheetRoom(n, el); });
    el.addEventListener("keydown", e => {
      const d = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key];
      if (!d || !r) return; e.preventDefault();
      const v = clamp(r.target + d * r.step, r.min, r.max);
      pos.to(v, { damping: 1, response: 0.3, onRest: () => commit(v) });
    });
    return { el, render };
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
      if (e.target.closest("button, .level") || sheet.scrollTop > 0) return;
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
    this._opener = from; this.$("sheet-body").innerHTML = html; this.$("sheet").hidden = false; this.$("scrim").style.pointerEvents = "auto";
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
      this.$("v-more").addEventListener("click", () => { this._closeSheet(); this.moreInfo(this.id("Lueftung") || this.id("Luefterstufe")); });
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
      choose(Math.round(k.x + project(vel * 100, SETTING) / 100), vel);
    };
    lv.addEventListener("pointerup", up); lv.addEventListener("pointercancel", up);
    lv.addEventListener("keydown", e => { const s = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key]; if (s) { e.preventDefault(); choose((chosen || this.num("Luefterstufe") || 1) + s); } });
  }
  _sheetWater(from) {
    const t = this.t, n = this.st("SollWassertemperatur");
    const lo = n ? n.attributes.min : 20, hi = n ? n.attributes.max : 55;
    this._openSheet(`<h3>${t.water}</h3><p class="sub" id="w-sub"></p>
      ${n ? `<div class="row"><span class="row-label">${t.waterTarget}<small>${lo} – ${hi} °C</small></span>
        <div class="stepper"><button id="wt-minus" aria-label="${t.colder}">−</button><output class="num" id="wt"></output><button id="wt-plus" aria-label="${t.warmer}">+</button></div></div>` : ""}
      ${this.id("T300Betriebsart") ? this._sw("s-pump", t.pump, t.pumpSub) : ""}${this.id("E-Heizstab") ? this._sw("s-heater", t.heater, t.heaterSub) : ""}
      <button class="link" id="w-more">${t.more}</button>`, from, () => {
      let want = null;
      const set = d => {
        want = clamp((want ?? this.num("SollWassertemperatur")) + d, lo, hi); this.$("wt").textContent = `${want}°`;
        clearTimeout(this._wtTimer);  // several taps in a row are sent once
        this._wtTimer = setTimeout(() => { const v = want; want = null; this.call("number", "set_value", { entity_id: this.id("SollWassertemperatur"), value: v }).catch(() => {}); }, 600);
      };
      if (n) { this.$("wt-minus").addEventListener("click", () => set(-1)); this.$("wt-plus").addEventListener("click", () => set(1)); this._wtWant = () => want; }
      ["s-pump", "s-heater"].forEach((id, i) => { const b = this.$(id); if (b) b.addEventListener("click", () => this._toggle(i ? "E-Heizstab" : "T300Betriebsart")); });
      this.$("w-more").addEventListener("click", () => { this._closeSheet(); this.moreInfo(this.id("Warmwasser") || this.id("WarmwasserIstTemperatur")); });
    }, () => {
      this.$("w-sub").textContent = `${this.$("w-temp").textContent} · ${t.bottom} ${this.$("w-bottom").textContent}`;
      if (n && this._wtWant() === null) this.$("wt").textContent = `${this.fmt(this.num("SollWassertemperatur"), 0)}°`;
      [["s-pump", "T300Betriebsart"], ["s-heater", "E-Heizstab"]].forEach(([id, k]) => { const b = this.$(id); if (b) b.setAttribute("aria-checked", (this.st(k) || {}).state === "on"); });
    });
  }
  _sheetRoom(n, from) {
    const t = this.t, r = this._room(n), d = r.step < 1 ? 1 : 0;
    this._openSheet(`<h3>${r.name}</h3><p class="sub" id="r-sub"></p>
      <div class="row"><span class="row-label">${t.target}<small>${fill(t.range, { a: this.fmt(r.min, 0), b: this.fmt(r.max, 0), s: this.fmt(r.step, d) })}</small></span>
        <div class="stepper"><button id="rt-minus" aria-label="${t.colder}">−</button><output class="num" id="rt"></output><button id="rt-plus" aria-label="${t.warmer}">+</button></div></div>
      ${this._sw("s-elem", t.released, t.releasedSub)}<p class="hint">${t.dragHint}</p><button class="link" id="r-more">${t.more}</button>`, from, () => {
      const step = s => {
        const cur = this._room(n), v = clamp(cur.target + s * cur.step, cur.min, cur.max);
        this._pending.set(n, { v, at: Date.now() }); this._updateRooms(); this._sheetRefresh();
        clearTimeout(this._rtTimer);
        this._rtTimer = setTimeout(() => this.call("climate", "set_temperature", { entity_id: cur.entity, temperature: v }).catch(() => { this._pending.delete(n); this._update(); }), 600);
      };
      this.$("rt-minus").addEventListener("click", () => step(-1)); this.$("rt-plus").addEventListener("click", () => step(1));
      this.$("s-elem").addEventListener("click", () => {
        const cur = this._room(n);
        this.call("climate", "set_hvac_mode", { entity_id: cur.entity, hvac_mode: cur.mode === "heat" ? "auto" : "heat" }).catch(() => {});
      });
      this.$("r-more").addEventListener("click", () => { this._closeSheet(); this.moreInfo(r.entity); });
    }, () => {
      const cur = this._room(n); if (!cur) return;
      this.$("r-sub").textContent = `${t.now} ${this.fmt(cur.temp)}° · ${t.element[cur.element] || ""}`;
      this.$("rt").textContent = `${this.fmt(cur.target, d)}°`;
      this.$("s-elem").setAttribute("aria-checked", cur.mode === "heat");
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
