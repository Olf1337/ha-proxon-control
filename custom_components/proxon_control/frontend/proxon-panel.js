// Proxon Control: the "Proxon" page in the sidebar. A web component without a build step and without libraries.
// It reads the unit's entities live from Home Assistant (`hass`) and changes them only through their normal actions.
// Motion follows Apple's fluid-interface rules: springs (damping ratio + response) that start from the value on screen,
// 1:1 dragging with momentum projection and rubber-banding, and no animation at all with "reduce motion".
// The page's configuration (entity IDs by unique-id suffix, rooms with their floor) comes from panel.py.

const TEXT = {
  de: {
    title: "Zuhause", outside: "Außen", op: "Betrieb", ok: "Alles in Ordnung", fault: "Störung", filter: "Filter bald wechseln",
    heroOk: "Alles läuft.", heroFault: "Störung.", heroFilter: "Filter wechseln.", heroLevel: "Stufe {n}", heroOut: "außen {v}",
    unit: "Lüftungsanlage", boost: "Intensivlüftung", left: "noch {m} Min.", leftSoon: "endet gleich", level: "Stufe", levelBoost: "4 (Intensiv)",
    tapUnit: "antippen zum Einstellen", fresh: "Frischluft", supply: "Zuluft", extract: "Abluft", exhaust: "Fortluft",
    out: "Außen", house: "Haus", fanSupply: "Zuluftlüfter", fanExhaust: "Abluftlüfter", recovery: "Wärmerückgewinnung",
    hx: "Wärmetauscher", heatPump: "Wärmepumpe", hpHeats: "Wärmepumpe heizt", hpCools: "Wärmepumpe kühlt", hpIdle: "Wärmepumpe aus",
    compressor: "Kompressor", compOff: "aus", humidity: "Feuchte",
    water: "Warmwasser", shower: "Reicht für ca. {m} Min. Duschen", middle: "Mitte", min: "Min.",
    litersSub: "warmes Wasser im Speicher", showerSub: "Duschen bei 40 °C", bottom: "Unten", target: "Soll", charge: "Ladezustand",
    floors: { "0": "Erdgeschoss", "1": "Obergeschoss", "-1": "Keller" }, rooms: "Räume", sent: "✓ gesendet", allEl: "Wärmeelemente aller Räume", allOn: "{a} von {b} Räumen an",
    allOff: "Wärmeelemente aller Räume aus", allOnDone: "Wärmeelemente aller Räume an",
    element: { off: "Heizpanel aus", ready: "Heizpanel bereit", heating: "Heizpanel heizt" },
    ventilation: "Lüftung", mode: "Betriebsart", boostSub: "läuft {m} Minuten, dann zurück", waterTarget: "Solltemperatur",
    pump: "Wärmepumpe", pumpSub: "heizt das Wasser sparsam", heater: "Heizstab", heaterSub: "schneller, braucht mehr Strom",
    now: "Jetzt", range: "{a} bis {b} °C in {s}-°C-Schritten", released: "Heizpanel freigegeben",
    releasedSub: "heizt elektrisch zu, wenn der Raum zu kalt ist",
    more: "Alle Werte", device: "Gerät in Home Assistant öffnen", groups: { temp: "Temperaturen", meas: "Messwerte", state: "Zustände", set: "Einstellungen" },
    close: "Schließen", warmer: "Wärmer", colder: "Kälter", undo: "Rückgängig",
    unavailable: "nicht erreichbar", nowLabel: "Jetzt", switchingOn: "wird eingeschaltet …", switchingOff: "wird ausgeschaltet …",
    holidayNeedsPlan: "Bitte zuerst Abreise und Rückkehr eintragen, dann lässt sich der Urlaubsmodus einschalten.",
    holidayReturnPast: "Die Rückkehr liegt in der Vergangenheit. Bitte eine neue Rückkehr eintragen.",
    holidayOrder: "Die Rückkehr liegt vor der Abreise. Bitte die Daten prüfen.", home: "Zuhause", energy: "Energie", settings: "Einstellungen", status: "Status",
    e: { usage: "Verbrauch", today: "Heute", week: "Diese Woche", runtime: "Laufzeit heute", per: { week: "Woche", month: "Monat", year: "Jahr" },
      earlier: "Früher", later: "Später", csv: "Als CSV herunterladen", csvDate: "Datum", csvMonth: "Monat", csvTotal: "Summe", failed: "Die Statistik von Home Assistant ist gerade nicht erreichbar. Gleich noch einmal versuchen.", cost: "Kosten", running: "Bisher", expected: "Voraussichtlich", fc: "{p} (Hochrechnung)",
      avgMonth: "Im Schnitt pro Monat", ofWater: "davon Warmwasser {v}",
      noPrice: "Für die Kosten unter Einstellungen → Geräte & Dienste → Proxon Control → Konfigurieren einen Strompreis eintragen (fest oder als Sensor).", none: "Für diesen Zeitraum gibt es noch keine Werte. Home Assistant speichert sie erst, seit es die Energie-Zähler gibt.", yesterday: "gestern {v}", forecast: "Hochrechnung {v}",
      comp: "Kompressor", vent: "Lüftung & Elektronik", water: "Warmwasser (geschätzt)", pump: "Warmwasser-Wärmepumpe", heater: "Heizstab",
      start: "1 Start", starts: "{n} Starts", prev: "Jahr davor", next: "Jahr danach", sofar: "bisher",
      empty: "Für {y} gibt es noch keine Werte. Home Assistant speichert sie erst, seit es die Energie-Zähler gibt.",
      note: "Kompressor und Lüftung misst die Anlage. Warmwasser ist geschätzt: Laufzeit von Wärmepumpe und Heizstab × ihre Leistung laut Datenblatt (einstellbar unter Konfigurieren)." },
    days: ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], phase: "Phase {n}", from: "von", to: "bis", lvl: "Stufe",
    daysShort: ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    hint: {
      GrenzwertCO2: "Darüber lüftet die Anlage im ECO-Komfortbetrieb stärker (nur mit CO₂-Fühler).",
      GrenzwertFeuchte: "Darunter lüftet die Anlage im ECO-Komfortbetrieb schwächer, damit die Luft nicht zu trocken wird.",
      LegionellenGeplant: "Heizt jede Woche am gewählten Tag zur gewählten Uhrzeit auf 60 °C, mit oder ohne Sonne.",
      LegionellenSonne: "Heizt einmal pro Woche auf 60 °C, bevorzugt mit Solarüberschuss.",
    },
    copyWeekdays: "Montag → Dienstag bis Freitag", copyAll: "Montag → alle Tage", span: "{a} bis {b}", sure: "Wirklich? Nochmal tippen", empty: "keine Phase",
    failed: "Das hat nicht geklappt ({a}).", yes: "An", no: "Aus", noPlan: "Kein Plan", planned: "Geplant: {a} – {b}", onUntil: "An · bis {d}", nOn: "{a} von {b} an", sections: "Bereiche",
    s: {
      auto: "Automatiken", vent: "Lüftung", schedule: "Wochenprogramm Lüftung", holiday: "Urlaub", water: "Warmwasser", boost: "Warmwasser-Boost",
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
      season: ["Sommer/Winter automatisch"],
    }, fnOn: "eingeschaltet", fnPlanned: "geplant ab {d}", fnNext: "{s} · nächster Lauf {d}",
    chip: { holiday: "Urlaub", season: "Sommer/Winter", heat: "heizt auf {t}°", boost: "heizt bis {t}°", cool: "kühlt, Stufe {l}", hot: "heizt auf 60°", from: "ab {d}", until: "bis {d}" },
  },
  en: {
    title: "Home", outside: "Outside", op: "Mode", ok: "All good", fault: "Fault", filter: "Filter change soon",
    heroOk: "All good.", heroFault: "Fault.", heroFilter: "Change the filter.", heroLevel: "level {n}", heroOut: "outside {v}",
    unit: "Ventilation unit", boost: "Boost ventilation", left: "{m} min left", leftSoon: "ending now", level: "Level", levelBoost: "4 (boost)",
    tapUnit: "tap to adjust", fresh: "Fresh air", supply: "Supply", extract: "Extract", exhaust: "Exhaust",
    out: "Outside", house: "House", fanSupply: "Supply fan", fanExhaust: "Extract fan", recovery: "Heat recovery",
    hx: "Heat exchanger", heatPump: "Heat pump", hpHeats: "Heat pump heating", hpCools: "Heat pump cooling", hpIdle: "Heat pump off",
    compressor: "Compressor", compOff: "off", humidity: "Humidity",
    water: "Hot water", shower: "Enough for about {m} min of showering", middle: "Middle", min: "min",
    litersSub: "of warm water in the tank", showerSub: "of showering at 40 °C", bottom: "Bottom", target: "Target", charge: "Charge",
    floors: { "0": "Ground floor", "1": "Upper floor", "-1": "Basement" }, rooms: "Rooms", sent: "✓ sent", allEl: "Heating elements of all rooms", allOn: "{a} of {b} rooms on",
    allOff: "Heating elements of all rooms off", allOnDone: "Heating elements of all rooms on",
    element: { off: "Heating panel off", ready: "Heating panel ready", heating: "Heating panel heating" },
    ventilation: "Ventilation", mode: "Operating mode", boostSub: "runs {m} minutes, then back", waterTarget: "Target temperature",
    pump: "Heat pump", pumpSub: "heats the water efficiently", heater: "Immersion heater", heaterSub: "faster, uses more power",
    now: "Now", range: "{a} to {b} °C in {s} °C steps", released: "Heating panel enabled",
    releasedSub: "heats electrically when the room is too cold",
    more: "All values", device: "Open the device in Home Assistant", groups: { temp: "Temperatures", meas: "Readings", state: "States", set: "Settings" },
    close: "Close", warmer: "Warmer", colder: "Colder", undo: "Undo",
    unavailable: "unavailable", nowLabel: "Now", switchingOn: "switching on …", switchingOff: "switching off …",
    holidayNeedsPlan: "Please enter departure and return first, then holiday mode can be switched on.",
    holidayReturnPast: "The return is in the past. Please enter a new return.",
    holidayOrder: "The return is before the departure. Please check the dates.", home: "Home", energy: "Energy", settings: "Settings", status: "Status",
    e: { usage: "Consumption", today: "Today", week: "This week", runtime: "Running time today", per: { week: "Week", month: "Month", year: "Year" },
      earlier: "Earlier", later: "Later", csv: "Download as CSV", csvDate: "Date", csvMonth: "Month", csvTotal: "Total", failed: "Home Assistant's statistics can't be reached right now. Try again in a moment.", cost: "Cost", running: "So far", expected: "Expected", fc: "{p} (forecast)",
      avgMonth: "On average per month", ofWater: "of which hot water {v}",
      noPrice: "For the cost, enter an electricity price under Settings → Devices & services → Proxon Control → Configure (fixed or as a sensor).", none: "There are no values for this period yet. Home Assistant keeps them only since the energy counters exist.", yesterday: "yesterday {v}", forecast: "Forecast {v}",
      comp: "Compressor", vent: "Ventilation & electronics", water: "Hot water (estimated)", pump: "Hot-water heat pump", heater: "Immersion heater",
      start: "1 start", starts: "{n} starts", prev: "Year before", next: "Year after", sofar: "so far",
      empty: "There are no values for {y} yet. Home Assistant keeps them only since the energy counters exist.",
      note: "The unit measures the compressor and the ventilation. Hot water is estimated: running time of heat pump and heater × their power from the datasheet (adjustable under Configure)." },
    days: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], phase: "Phase {n}", from: "from", to: "to", lvl: "level",
    daysShort: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    hint: {
      GrenzwertCO2: "Above it the unit ventilates more in ECO comfort mode (only with a CO₂ sensor).",
      GrenzwertFeuchte: "Below it the unit ventilates less in ECO comfort mode, so the air doesn't get too dry.",
      LegionellenGeplant: "Heats to 60 °C every week on the chosen day at the chosen time, sun or not.",
      LegionellenSonne: "Heats to 60 °C once a week, preferably with solar surplus.",
    },
    copyWeekdays: "Monday → Tuesday to Friday", copyAll: "Monday → every day", span: "{a} to {b}", sure: "Sure? Tap again", empty: "no phase",
    failed: "That did not work ({a}).", yes: "On", no: "Off", noPlan: "No plan", planned: "Planned: {a} – {b}", onUntil: "On · until {d}", nOn: "{a} of {b} on", sections: "Sections",
    s: {
      auto: "Automations", vent: "Ventilation", schedule: "Weekly ventilation schedule", holiday: "Holiday", water: "Hot water", boost: "Hot-water boost",
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
      season: ["Summer/winter automatically"],
    }, fnOn: "switched on", fnPlanned: "planned from {d}", fnNext: "{s} · next run {d}",
    chip: { holiday: "Holiday", season: "Summer/winter", heat: "heating to {t}°", boost: "heating up to {t}°", cool: "cooling, level {l}", hot: "heating to 60°", from: "from {d}", until: "until {d}" },
  },
};
const fill = (s, v) => s.replace(/\{(\w)\}/g, (_, k) => (v[k] ?? ""));

// the automatic functions: a hint at the top of "Home" while one is switched on (or holiday mode is planned); it shows what
// the function is doing and is lit while it works; a tap opens its settings. on: its switches, status: its status sensor,
// run(st of the first switch, panel): working now, sec: its section in the settings.
const FUNCS = [
  { k: "holiday", on: ["Urlaubsmodus"], sec: "holiday", run: st => st.state === "on", tint: "--fresh",
    icon: "M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M4 7h16v12H4zM9 7v12M15 7v12" },
  { k: "solar", on: ["SolarWarmwasser"], status: "Energiemanager", sec: "store", run: st => st.attributes.status === "heating_solar", tint: "--supply", temp: "SpeicherTemperatur",
    icon: "M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z" },
  { k: "price", on: ["PreisWarmwasser"], status: "Energiemanager", sec: "store", run: st => st.attributes.status === "heating_price", tint: "--fine", temp: "SpeicherTemperatur",
    icon: "M12 3v18M17 7.5C17 5.6 14.8 4.5 12 4.5S7 5.7 7 7.6c0 4.8 10 2.6 10 7.8 0 2-2.2 3.1-5 3.1s-5-1.2-5-3.1" },
  { k: "boostww", on: ["WarmwasserBoost"], status: "BoostStatus", sec: "boost", run: st => st.attributes.status === "heating", tint: "--warm", temp: "BoostGrenze",
    icon: "M13 2L4 14h7l-1 8 9-12h-7z" },
  { k: "legionella", on: ["LegionellenSonne", "LegionellenGeplant"], status: "LegionellenStatus", sec: "legionella",
    run: (st, p) => String((p.st("LegionellenStatus") || {}).state || "").startsWith("heating"), tint: "--water-hot",
    icon: "M12 3c3 4 6 6.5 6 10a6 6 0 0 1-12 0c0-3.5 3-6 6-10zM10 14a2 2 0 0 0 2 2" },
  { k: "cooling", on: ["Nachtkuehlung"], status: "NachtkuehlungStatus", sec: "cooling", run: st => ["cooling", "heat_protection"].includes(st.attributes.status), tint: "--cold",
    icon: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" },
  { k: "season", on: ["SaisonAutomatik"], status: "SaisonStatus", sec: "season", run: () => false, tint: "--exhaust",
    icon: "M12 3v18M4 7l16 10M20 7L4 17" },
];

// the energy tab: what the consumption is made of (each its own colour everywhere), and the running times of today.
// The unit measures compressor and ventilation; the hot-water module is estimated (heat pump + heater).
const ENERGY_PARTS = [
  { k: "comp", keys: ["EnergieKompressor"], power: ["LeistungKompressor"], color: "--e-comp" },
  { k: "vent", keys: ["EnergieLueftung"], power: ["LeistungLueftung"], color: "--e-vent" },
  { k: "water", keys: ["EnergieWarmwasserWP", "EnergieHeizstab"], power: ["LeistungWarmwasserWP", "LeistungHeizstab"], color: "--e-water" },
];
const RUNTIMES = [["comp", "KompressorLaufzeitHeute", "KompressorStartsHeute"], ["pump", "WarmwasserKompressorLaufzeitHeute", "WarmwasserKompressorStartsHeute"],
  ["heater", "HeizstabLaufzeitHeute", "HeizstabStartsHeute"]];

// limits shown with the value measured now (CO2 only with a CO2 sensor that delivers values)
const NOW_OF = { GrenzwertFeuchte: "LuftfeuchteRel", GrenzwertCO2: "CurrentCO2" };

// the settings tab, like the iPad's settings: a list of sections on the left, the chosen one on the right (on a phone the
// list, and a section pushed over it). Sections hold rows (shown when their entities exist); the automatic functions are
// one section ("auto"), each a row with its status that opens its limits in place; `main` is the switch in that row.
const ICONS = {
  vent: "M12 12c0-4 1-7 4-7s3 4-4 7zm0 0c4 0 7 1 7 4s-4 3-7-4zm0 0c0 4-1 7-4 7s-3-4 4-7zm0 0c-4 0-7-1-7-4s4-3 7 4z",
  schedule: "M4 6h16v14H4zM4 10h16M8 3v4M16 3v4M8 14h3M13 14h3M8 17h3",
  holiday: "M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M4 7h16v12H4zM9 7v12M15 7v12",
  water: "M12 3c3 4 6 6.5 6 10a6 6 0 0 1-12 0c0-3.5 3-6 6-10z",
  auto: "M13 2L4 14h7l-1 8 9-12h-7z",
  boost: "M13 2L4 14h7l-1 8 9-12h-7z",
  store: "M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z",
  legionella: "M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6z",
  cooling: "M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z",
  season: "M12 3v18M4 7l16 10M20 7L4 17",
  night: "M3 17h18M7 13a5 5 0 0 1 10 0M12 4v2",
};
const SETTINGS = [
  { id: "vent", color: "#3b8fd9", rows: [["num", "IntensivlueftungsDauer"], ["num", "GrenzwertCO2"], ["num", "GrenzwertFeuchte"]] },
  { id: "schedule", color: "#5856d6", rows: [["switch", "ZeitprogrammAktiv"], ["days"]] },
  { id: "holiday", color: "#ff9f0a", rows: [["switch", "Urlaubsmodus"], ["datetime", "UrlaubAb"], ["datetime", "UrlaubBis"], ["num", "UrlaubVorlauf"], ["button", "UrlaubsplanLoeschen"]] },
  { id: "water", color: "#f07a3a", rows: [["num", "SollWassertemperatur"], ["switch", "T300Betriebsart"], ["switch", "E-Heizstab"], ["num", "Soll-E-Heizstab-Temperatur"], ["switch", "Legionellenfunktion"]] },
  { id: "boost", auto: true, color: "#e9772f", main: "WarmwasserBoost", status: "BoostStatus", rows: [["switch", "WarmwasserBoost"], ["num", "BoostGrenze"]] },
  { id: "store", auto: true, color: "#e5a000", status: "Energiemanager", rows: [["switch", "SolarWarmwasser"], ["num", "SolarSchwelle"], ["switch", "PreisWarmwasser"], ["num", "PreisSchwelle"], ["num", "SpeicherTemperatur"]] },
  { id: "legionella", auto: true, color: "#c26d7e", status: "LegionellenStatus", rows: [["switch", "LegionellenSonne"], ["time", "LegionellenZeit"],
    ["switch", "LegionellenGeplant"], ["select", "LegionellenTag"], ["time", "LegionellenPlanZeit"]] },
  { id: "cooling", auto: true, color: "#5aa0e6", main: "Nachtkuehlung", status: "NachtkuehlungStatus", rows: [["switch", "Nachtkuehlung"], ["num", "KuehlWunsch"], ["num", "KuehlStufe"]] },
  { id: "season", auto: true, color: "#8e8e93", main: "SaisonAutomatik", status: "SaisonStatus", rows: [["switch", "SaisonAutomatik"], ["num", "SaisonWinterUnter"], ["num", "SaisonSommerUeber"]] },
  { id: "night", color: "#6e6ad6", rows: [["switch", "NachtabsenkungAktiv"], ["num", "NachtabsenkungTemperatur"], ["time", "NachtabsenkungStart"], ["time", "NachtabsenkungEnde"]] },
];
const AUTO_COLOR = "#1d8a7a";
const icon = (id, color) => `<span class="ico" style="background:${color}" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="${ICONS[id]}"/></svg></span>`;

// ---------------- springs ----------------
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
// text that comes from Home Assistant (entity names, states, options) and goes into markup: never as markup. Anyone who can
// rename an entity could otherwise put HTML into the page of every user
const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ESC[c]);
let tileFontLoaded = false;
function loadTileFont(base) {
  if (tileFontLoaded || !base) return;
  tileFontLoaded = true;
  const style = document.createElement("style");
  style.textContent = `@font-face { font-family: "Antonio"; font-weight: 400 700; font-display: swap; src: url("${base}/fonts/antonio-latin.woff2") format("woff2"); }`;
  document.head.appendChild(style);
}
// a tile's colour from its temperature: cool blue-grey (17 °C and below) to warm amber (24 °C and above), quiet enough for text
function tempTint(temp, dark) {
  if (typeof temp !== "number") return "";
  const k = Math.round(Math.max(0, Math.min(1, (temp - 17) / 7)) * 100);  // a straight blend, no greens on the way
  return dark ? `color-mix(in oklab, #1b2533, #4a3116 ${k}%)` : `color-mix(in oklab, #e1eaf4, #f6dfc2 ${k}%)`;
}
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
const rubber = (over, dim, c = 0.55) => (over * dim * c) / (dim + c * Math.abs(over));
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

const STYLE = `
:host {
  --bg: #eef1f4; --surface: rgba(255,255,255,.78); --surface-solid: #fff; --line: rgba(20,32,45,.08); --fg: #14202d; --fg-2: #586675;
  --fg-3: #5f6b77; --accent: #1d8a7a; --fresh: #3b8fd9; --supply: #e08a3c; --extract: #c26d7e; --exhaust: #8b97a4; --cold: #3b82d6;
  --fine: #1f9d6c; --warm: #d8602f; --flame: #ff6a2b; --water-hot: #f07a3a; --water-cool: #f6c79a; --danger: #d64545;
  --tank-deep: #1c64ad; --tank-mid: #3a8fd6; --tank-top: #6cb8ea;
  --scrim: rgba(10,18,28,.32); --shadow: 0 1px 2px rgba(20,32,45,.06), 0 8px 24px rgba(20,32,45,.06); --sheet-shadow: 0 -10px 40px rgba(10,18,28,.18);
  --font: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, "Segoe UI", Roboto, sans-serif;
  --font-display: -apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, "Segoe UI", Roboto, sans-serif;
  --glass: rgba(255,255,255,.55); --glass-strong: rgba(255,255,255,.78); --edge: rgba(255,255,255,.85); --edge-low: rgba(20,32,45,.07);
  --blob-a: #ffb27a; --blob-b: #8fc3ff; --blob-c: #b9e6d3;
  display: block; min-height: 100%; background: var(--bg); color: var(--fg); font: 16px/1.45 var(--font); -webkit-tap-highlight-color: transparent;
}
:host([dark]) {
  --bg: #0e1318; --surface: rgba(28,35,43,.78); --surface-solid: #1c232b; --line: rgba(255,255,255,.07); --fg: #eef2f5; --fg-2: #a3afbb;
  --fg-3: #8d99a6; --accent: #3cc3ab; --fresh: #5aa8ec; --supply: #f0a056; --extract: #d98a9a; --exhaust: #7d8a97; --cold: #5c9ceb;
  --fine: #3cc08a; --warm: #f07b4a; --flame: #ff7a3d; --water-hot: #f58a4c; --water-cool: #7a5236; --danger: #f06a6a;
  --tank-deep: #123f6e; --tank-mid: #2466a3; --tank-top: #4a95d2;
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
.card, .chip, .fchip, .toast { background: var(--glass) !important; border: 0 !important; backdrop-filter: blur(30px) saturate(180%); -webkit-backdrop-filter: blur(30px) saturate(180%); }
.chip, .fchip { position: relative; }
.card::before, .chip::before, .fchip::before, .toast::before, .sheet::before { content: ""; position: absolute; inset: 0; border-radius: inherit; padding: 1px; pointer-events: none;
  background: linear-gradient(160deg, var(--edge), var(--edge-low) 40%, var(--edge-low) 70%, var(--edge));
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude; }
.card::after { content: ""; position: absolute; inset: 0 0 60% 0; border-radius: inherit; pointer-events: none;
  background: linear-gradient(180deg, rgba(255,255,255,.14), transparent); }
.card { border-radius: 28px !important; }
.page { position: relative; z-index: 1; max-width: 1120px; margin: 0 auto; display: grid; gap: 20px;
  padding: calc(20px + env(safe-area-inset-top, 0px)) max(16px, env(safe-area-inset-right, 0px)) calc(48px + env(safe-area-inset-bottom, 0px)) max(16px, env(safe-area-inset-left, 0px)); }
.head { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px; }
.head h1 { font: 700 1.6rem/1.1 var(--font-display); letter-spacing: -.02em; margin: 0 auto 0 0; display: flex; align-items: center; gap: 6px; }
.tabs { display: flex; gap: 2px; padding: 3px; border-radius: 12px; background: var(--line); }
.tabs button { border: 0; background: transparent; padding: 7px 14px; border-radius: 9px; font-size: .9375rem; font-weight: 600; color: var(--fg-2); cursor: pointer; }
.tabs button[aria-selected="true"] { background: var(--surface-solid); color: var(--fg); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
/* energy: one colour per part of the consumption */
:host { --e-comp: #8e6fd6; --e-vent: #3b8fd9; --e-water: #f07a3a; }
:host([dark]) { --e-comp: #a98cf0; --e-vent: #5aa8ec; --e-water: #f58a4c; }
.e-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 16px; align-items: start; }
.e-card { display: grid; gap: 10px; align-content: start; }
.e-big { font: 700 2.6rem/1 var(--font-display); letter-spacing: -.03em; }
.e-big small, .e-mid small { font-size: 1.05rem; color: var(--fg-2); font-weight: 600; margin-left: 4px; letter-spacing: 0; }
.e-mid { font: 700 1.45rem/1.15 var(--font-display); letter-spacing: -.02em; }
.e-key { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: .8125rem; color: var(--fg-2); }
.e-key i { display: inline-block; width: 9px; height: 9px; border-radius: 3px; margin-right: 6px; }
.e-key b { color: var(--fg); font-weight: 600; }
.e-run { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-top: 1px solid var(--line); }
.e-run:first-child { border-top: 0; padding-top: 0; }
.e-run b { font-weight: 600; white-space: nowrap; }
.e-note { font-size: .8125rem; color: var(--fg-3); margin: 0 4px; }
.e-cost-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr)); gap: 10px 28px; }
.e-cost-grid > div > .sub { display: block; margin-bottom: 2px; }
.e-run small { display: block; font-size: .75rem; color: var(--fg-3); }
/* stacked columns: one per day (week, month) or month (year), drawn with boxes so the text stays sharp at any width */
.e-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.e-nav { display: inline-flex; align-items: center; gap: 2px; }
.e-nav button { width: 34px; height: 32px; border: 0; border-radius: 9px; background: var(--line); font-size: 1.15rem; cursor: pointer; color: var(--fg); }
.e-nav button:disabled { opacity: .3; cursor: default; }
.e-nav button svg { display: block; margin: auto; }
.e-chart { position: relative; height: 190px; margin: 8px 0 0 34px; }
.e-grid-l { position: absolute; left: 0; right: 0; border-top: 1px dashed var(--line); }
.e-grid-l span { position: absolute; right: calc(100% + 6px); top: -.6em; font-size: .6875rem; color: var(--fg-3); white-space: nowrap; }
.e-cols { position: absolute; inset: 0; display: flex; align-items: flex-end; justify-content: space-between; gap: var(--gap, 4px); }
.e-col { flex: 1 1 0; min-width: 0; max-width: 44px; height: 100%; display: flex; flex-direction: column-reverse; border: 0; padding: 0; background: none; cursor: pointer; border-radius: 4px 4px 0 0; }
.e-col span { display: block; width: 100%; }
.e-col span:last-child { border-radius: 4px 4px 0 0; }
.e-col.sel { background: color-mix(in srgb, var(--fg) 7%, transparent); }
.e-col.future { opacity: .35; }
.e-xl { display: flex; justify-content: space-between; gap: var(--gap, 4px); margin-left: 34px; font-size: .6875rem; color: var(--fg-3); }
.e-xl span { flex: 1 1 0; min-width: 0; max-width: 44px; text-align: center; white-space: nowrap; overflow: visible; }
.e-detail { min-height: 1.4em; font-size: .875rem; color: var(--fg-2); }
.e-detail b { color: var(--fg); }
.tabs svg { display: none; width: 22px; height: 22px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
/* on a phone the tabs are a bar at the bottom, where the thumb is (the top is under the status bar and out of reach) */
@media (max-width: 600px) {
  .page { padding-bottom: calc(112px + env(safe-area-inset-bottom, 0px)); }
  .tabs { position: fixed; z-index: 15; left: 50%; bottom: calc(14px + env(safe-area-inset-bottom, 0px)); transform: translateX(-50%); gap: 4px; padding: 5px;
    border-radius: 999px; background: var(--glass-strong); box-shadow: var(--sheet-shadow); backdrop-filter: blur(30px) saturate(180%); -webkit-backdrop-filter: blur(30px) saturate(180%); }
  .tabs button { display: grid; justify-items: center; gap: 2px; min-width: 92px; padding: 7px 12px 6px; border-radius: 999px; font-size: .6875rem; }
  .tabs button[aria-selected="true"] { color: var(--accent); }
  .tabs svg { display: block; }
  .toast { bottom: calc(92px + env(safe-area-inset-bottom, 0px)) !important; }
  /* the unit's picture shrinks with the screen: its small labels go, the four air temperatures stand large below it */
  svg.diagram .t-val, svg.diagram .t-name, svg.diagram .t-small, svg.diagram .zone { display: none; }
  :host .unit-temps { display: grid; }
}
.unit-temps { display: none; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
.unit-temps div { padding: 10px 12px; border-radius: 14px; background: var(--line); min-width: 0; }
.unit-temps span { display: block; font-size: .75rem; font-weight: 600; letter-spacing: .04em; text-transform: uppercase; color: var(--fg-2); }
.unit-temps b { display: block; font: 700 1.5rem/1.15 var(--font-display); letter-spacing: -.02em; margin-top: 2px; }
.view { display: grid; gap: 20px; }
.status { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.group { display: grid; gap: 6px; }
.group h2 { font: 600 .8125rem/1.2 var(--font); letter-spacing: .02em; text-transform: uppercase; color: var(--fg-2); margin: 0 4px; }
.group .card { padding: 0 16px; }
.group .card > :first-child { border-top: 0; }
.group .foot { font-size: .8125rem; color: var(--fg-3); margin: 0 4px; }
.group .card { min-width: 0; }
/* settings: the list of sections and the chosen one */
#v-settings { container-type: inline-size; }
.sa { display: grid; grid-template-columns: 300px minmax(0, 1fr); gap: 20px; align-items: start; }
/* the list keeps its column: a long summary is cut with "…" instead of widening its row over the section beside it */
.sa-list.card { padding: 8px; display: grid; grid-template-columns: minmax(0, 1fr); gap: 2px; position: sticky; top: calc(16px + env(safe-area-inset-top, 0px)); }
.sa-item { min-width: 0; display: flex; align-items: center; gap: 12px; width: 100%; border: 0; background: none; padding: 9px 10px; border-radius: 18px; text-align: left; cursor: pointer; }
.sa-item[aria-current="true"] { background: var(--glass-strong); box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.sa-item::after { content: "›"; color: var(--fg-3); font-size: 1.2rem; }
.sa-t { flex: 1; min-width: 0; }
.sa-t b { display: block; font-weight: 600; }
.sa-t small { display: block; color: var(--fg-2); font-size: .8125rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sa-detail { min-width: 0; display: grid; grid-template-columns: minmax(0, 1fr); gap: 6px; }
.group h2.sa-h { display: flex; align-items: center; gap: 12px; font: 700 1.5rem/1.15 var(--font-display); letter-spacing: -.02em; text-transform: none; color: var(--fg); margin: 4px 4px 8px; }
.sa-back { display: none; justify-self: start; border: 0; background: none; color: var(--accent); font-weight: 600; font-size: 1.0625rem; padding: 2px 0 6px; cursor: pointer; }
.ico { flex: none; width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; color: #fff; }
.ico svg { width: 19px; height: 19px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.auto { border-top: 1px solid var(--line); }
.auto-head { display: flex; align-items: center; gap: 12px; padding: 12px 0; cursor: pointer; }
.auto-l { flex: 1; min-width: 0; font-weight: 600; }
.auto-l small { display: block; font-weight: 400; color: var(--fg-2); font-size: .8125rem; }
.tag { flex: none; padding: 3px 10px; border-radius: 999px; font-size: .75rem; font-weight: 600; background: var(--line); color: var(--fg-2); }
.tag.on { background: color-mix(in srgb, var(--accent) 18%, transparent); color: var(--accent); }
.disc { flex: none; color: var(--fg-3); font-size: 1.2rem; transition: transform 250ms ease; }
.auto-head[aria-expanded="true"] .disc { transform: rotate(90deg); }
.auto-more { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 320ms cubic-bezier(.2,.9,.25,1); }
.auto-more.open { grid-template-rows: 1fr; }
.auto-more > div { min-height: 0; overflow: hidden; }
@container (min-width: 520px) { .auto-more > div { padding-left: 46px; } }
@container (max-width: 700px) {
  .sa { grid-template-columns: minmax(0, 1fr); }
  .sa:not(.open) .sa-detail, .sa.open .sa-list { display: none; }
  .sa-list.card { position: static; }
  .sa-back { display: block; }
  .sa-item[aria-current="true"] { background: none; box-shadow: none; }
}
.version { margin: 28px 0 0; text-align: center; font-size: .75rem; color: var(--fg-3); }  /* a section never grows wider than its column (long texts wrap inside it) */
/* a weekday: its name, the phases below it (wrapping), the chevron on the right */
.day.sched { display: grid; grid-template-columns: minmax(0, 1fr) auto; column-gap: 12px; row-gap: 2px; align-items: center; }
.day.sched > span:first-child { grid-column: 1; grid-row: 1; }
.day.sched > span:last-child { grid-column: 1; grid-row: 2; margin: 0; text-align: left; white-space: normal; overflow: visible; font-size: .8125rem; color: var(--fg-2); }
.day.sched::after { grid-column: 2; grid-row: 1 / span 2; }
.tin { font: 600 1rem var(--font); color: var(--fg); background: var(--line); border: 0; border-radius: 10px; padding: 8px 10px; min-width: 0; }
.day { display: flex; justify-content: space-between; align-items: center; gap: 12px; width: 100%; border: 0; border-top: 1px solid var(--line);
  background: none; padding: 13px 0; text-align: left; cursor: pointer; }
.day > span:first-child { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
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
button.card:active { transform: scale(.985); }
.card-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.label { font-size: .8125rem; font-weight: 600; letter-spacing: .02em; color: var(--fg-2); text-transform: uppercase; }
.hint { font-size: .8125rem; color: var(--fg-3); }
.unit-tap { display: block; width: 100%; border: 0; background: none; padding: 0; text-align: left; cursor: pointer; border-radius: 14px;
  transition: transform 120ms ease-out; touch-action: manipulation; }
.unit-tap:active { transform: scale(.99); }
.pill-switch { display: inline-flex; align-items: center; gap: 10px; padding: 5px 6px 5px 12px; border-radius: 999px; border: 1px solid var(--line);
  background: var(--surface-solid); cursor: pointer; font-size: .875rem; font-weight: 600; transition: transform 100ms ease-out; }
.pill-switch:active { transform: scale(.96); }
.pill-text { display: flex; flex-direction: column; align-items: flex-start; line-height: 1.15; }
.pill-text small { font-size: .75rem; font-weight: 500; color: var(--fg-2); font-variant-numeric: tabular-nums; }
.switch { position: relative; width: 52px; height: 32px; border-radius: 16px; border: 0; background: var(--line); cursor: pointer; flex: none; transition: background 200ms ease; }
.switch::after { content: ""; position: absolute; top: 3px; left: 3px; width: 26px; height: 26px; border-radius: 50%; background: #fff;
  box-shadow: 0 2px 6px rgba(0,0,0,.2); transition: transform 280ms cubic-bezier(.22,1,.36,1); }
.switch[aria-checked="true"] { background: var(--accent); }
.switch[aria-busy="true"] { opacity: .55; cursor: progress; }
.row-label small.pend { color: var(--accent); font-weight: 600; }
.switch[aria-checked="true"]::after { transform: translateX(20px); }
.pill-switch .switch { width: 44px; height: 26px; pointer-events: none; }
.pill-switch .switch::after { width: 20px; height: 20px; }
.pill-switch .switch[aria-checked="true"]::after { transform: translateX(18px); }
svg.diagram { display: block; width: 100%; max-width: 760px; margin: 6px auto 0; height: auto; overflow: visible; --glowc: var(--water-hot); }
.tube { fill: none; stroke-width: 22; stroke-linecap: round; stroke-linejoin: round; opacity: .62; }
.flow { fill: none; stroke: #fff; stroke-width: 3.2; stroke-linecap: round; stroke-dasharray: 2 14; opacity: .85; }
.unit-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
.chip.soft { font-weight: 500; color: var(--fg-2); background: var(--glass-strong) !important; backdrop-filter: none; -webkit-backdrop-filter: none; }
.chip.soft b { color: var(--fg); font-weight: 600; }
.t-name { font: 600 12px var(--font); letter-spacing: .05em; text-transform: uppercase; fill: var(--fg-2); }
.t-val { font: 700 30px var(--font-display); letter-spacing: -.03em; fill: var(--fg); }
.t-small { font: 500 12px var(--font); fill: var(--fg-3); }
.box { fill: var(--surface-solid); stroke: var(--line); stroke-width: 1.5; }
.hx { fill: none; stroke: var(--fg-3); stroke-width: 1.2; opacity: .55; }
.zone { font: 600 11px var(--font); letter-spacing: .08em; text-transform: uppercase; fill: var(--fg-3); }
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
.water-set { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line); font-size: .9375rem; color: var(--fg-2); }
.w-set-l { display: flex; align-items: center; gap: 10px; }
.w-set-l .saved { position: static; }
.card.tap { cursor: pointer; transition: transform 120ms ease-out; -webkit-user-select: none; user-select: none; }
.card.tap:active:not(:has(button:active)) { transform: scale(.985); }
.stepper button:disabled { opacity: .35; cursor: default; }
.row:has(> .stepper) .row-label { flex-basis: 80px; }
.row.stepped { display: grid; grid-template-columns: minmax(0, 1fr) auto; row-gap: 2px; }  /* label and − value + on one line, the explanation below across the row */
.row-sub { grid-column: 1 / -1; font-size: .8125rem; color: var(--fg-3); }  /* − value + stays on the label's line, also on a phone */
.row-label small.now-val { color: var(--fg); font-weight: 600; }
/* a switched-on function in the status row: icon, short name, what it does; tinted with a pulsing dot while it works */
.fchip { display: inline-flex; align-items: center; gap: 7px; max-width: 100%; min-width: 0; padding: 4px 12px 4px 4px; border-radius: 999px; font-size: .875rem;
  cursor: pointer; transition: transform 120ms ease-out; touch-action: manipulation; }
.fchip:active { transform: scale(.96); }
.fchip .fi { flex: none; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--tint) 16%, transparent); }
.fchip .fi svg { width: 15px; height: 15px; }
.fchip b { font-weight: 600; white-space: nowrap; }
.fchip .ft { color: var(--fg-2); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fchip.run { background: color-mix(in srgb, var(--tint) 20%, var(--glass)) !important; }
.fchip.run .ft { color: var(--fg); }
.live { flex: none; width: 7px; height: 7px; border-radius: 50%; background: var(--tint); animation: live 1.8s ease-out infinite; }
@keyframes live { 0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--tint) 55%, transparent); } 100% { box-shadow: 0 0 0 7px transparent; } }
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
.room { padding: 14px 14px 12px; overflow: hidden; }
.room-step { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-top: 10px; }
.rs-btn { flex: none; width: 38px; height: 38px; border-radius: 50%; border: 0; background: var(--line); font-size: 1.25rem; cursor: pointer; transition: transform 100ms ease-out; }
.rs-btn:active { transform: scale(.92); }
.rs-btn:disabled { opacity: .35; cursor: default; }
.rs-v { display: grid; justify-items: center; line-height: 1.15; min-width: 0; }
.rs-v small { font-size: .75rem; color: var(--fg-2); }
.rs-v b { font-weight: 600; transition: color 200ms ease; }
.rs-v.ok b { color: var(--fine); }
.room .state { position: absolute; inset: 0; border-radius: inherit; pointer-events: none; box-shadow: inset 0 0 0 2px var(--ring, transparent); opacity: .55; }
.room-name { font-size: .9375rem; font-weight: 600; display: flex; align-items: center; justify-content: space-between; gap: 6px; min-width: 0; }
.room-name span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.room-temp { font: 700 2.25rem/1.05 var(--font-display); letter-spacing: -.03em; margin-top: 8px; }
.room-temp small { font-size: 1.1rem; color: var(--fg-2); font-weight: 600; }
.room-target { position: relative; margin-top: 4px; font-size: .875rem; color: var(--fg-2); min-height: 1.3em; white-space: nowrap; }
.room-target b { color: var(--fg); font-weight: 600; }
.saved { position: absolute; right: 0; top: 0; color: var(--fine); font-weight: 600; opacity: 0; transition: opacity 200ms ease; }
.saved.show { opacity: 1; }
.elem { width: 20px; height: 20px; flex: none; }
.elem.off { opacity: .28; }
.scrim { position: fixed; inset: 0; background: var(--scrim); opacity: 0; pointer-events: none; z-index: 20; }
.sheet { position: fixed; left: 50%; bottom: 0; z-index: 21; width: min(560px, 100%); max-height: 86%; overflow: auto; transform: translate(-50%, 110%);
  background: var(--glass-strong); backdrop-filter: blur(40px) saturate(180%); -webkit-backdrop-filter: blur(40px) saturate(180%); border-radius: 26px 26px 0 0; box-shadow: var(--sheet-shadow); touch-action: none; overscroll-behavior: contain;
  padding: 8px max(20px, env(safe-area-inset-right, 0px)) calc(24px + env(safe-area-inset-bottom, 0px)) max(20px, env(safe-area-inset-left, 0px)); }
/* a sheet longer than the screen scrolls; then only the handle and the title drag it closed */
.sheet.scrolls { touch-action: pan-y; }
.sheet.scrolls .grabber, .sheet.scrolls h3, .sheet.scrolls .sub { touch-action: none; }
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
.stepper button { -webkit-user-select: none; user-select: none; -webkit-touch-callout: none; touch-action: manipulation; width: 40px; height: 40px; border-radius: 50%; border: 0; background: var(--line); font-size: 1.3rem; cursor: pointer; transition: transform 100ms ease-out; }
.stepper button:active { transform: scale(.92); }
.stepper output { min-width: 72px; text-align: center; font: 700 1.4rem var(--font-display); letter-spacing: -.02em; }
.seg { display: flex; flex-wrap: wrap; gap: 4px; padding: 3px; border-radius: 12px; background: var(--line); }
.seg button { border: 0; background: transparent; padding: 7px 11px; border-radius: 9px; font-size: .875rem; cursor: pointer; color: var(--fg-2); }
.seg button[aria-pressed="true"] { background: var(--surface-solid); color: var(--fg); font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.level-seg { display: grid; grid-template-columns: repeat(4, 1fr); margin: 6px 0 10px; }
.level-seg button { padding: 10px 0; font-size: 1.0625rem; font-weight: 600; }
.level-seg button:disabled { opacity: .45; cursor: default; }
.level-note { font-size: .8125rem; color: var(--fg-3); margin: 0 0 6px; }
.link { border: 0; background: none; color: var(--accent); font-weight: 600; cursor: pointer; padding: 14px 0 0; }
.toast { position: fixed; left: 50%; bottom: calc(20px + env(safe-area-inset-bottom, 0px)); z-index: 30; display: flex; align-items: center; gap: 14px;
  padding: 10px 10px 10px 16px; border-radius: 16px; background: var(--surface); border: 1px solid var(--line); box-shadow: var(--sheet-shadow);
  backdrop-filter: blur(24px) saturate(160%); -webkit-backdrop-filter: blur(24px) saturate(160%); transform: translate(-50%, 160%); max-width: calc(100% - 32px);
  font-size: .9375rem; font-weight: 600; }
.toast span { overflow: hidden; text-overflow: ellipsis; }
.toast button { flex: none; border: 0; background: var(--line); padding: 7px 12px; border-radius: 10px; font-weight: 600; color: var(--accent); cursor: pointer; }
[hidden] { display: none !important; }
/* ---------- the look "Soft" (option): one calm surface colour, cards raised by a light and a dark shadow from the top
   left, buttons and switches pressed in; full-contrast text, a fine edge and coloured states stay as in the glass look ---------- */
:host([softui]) {
  --bg: #e7ecf1; --s-hi: #ffffff; --s-lo: #c2cad3; --edge: rgba(20,32,45,.07); --edge-low: rgba(20,32,45,.07);
  --glass: var(--bg); --glass-strong: var(--bg); --surface: var(--bg);
  --shadow: 6px 6px 14px var(--s-lo), -6px -6px 14px var(--s-hi);
  --raised: 3px 3px 7px var(--s-lo), -3px -3px 7px var(--s-hi);
  --pressed: inset 3px 3px 7px var(--s-lo), inset -3px -3px 7px var(--s-hi);
}
:host([softui][dark]) { --bg: #272e36; --s-hi: #343d47; --s-lo: #161a1f; --edge: rgba(255,255,255,.05); --edge-low: rgba(255,255,255,.05);
  --shadow: 8px 8px 18px var(--s-lo), -6px -6px 16px var(--s-hi); }
:host([softui]) .backdrop { display: none; }
:host([softui]) .card, :host([softui]) .chip, :host([softui]) .fchip, :host([softui]) .toast, :host([softui]) .sheet {
  background: var(--bg) !important; backdrop-filter: none; -webkit-backdrop-filter: none; box-shadow: var(--shadow); }
:host([softui]) .sheet { box-shadow: 0 -8px 24px var(--s-lo); }
:host([softui]) .chip, :host([softui]) .fchip { box-shadow: var(--raised); }
:host([softui]) .fchip.run { background: color-mix(in srgb, var(--tint) 16%, var(--bg)) !important; }
:host([softui]) .card::after { display: none; }
/* buttons stand out and press in */
:host([softui]) .stepper button, :host([softui]) .rs-btn, :host([softui]) .e-nav button, :host([softui]) .close, :host([softui]) .toast button {
  background: var(--bg); box-shadow: var(--raised); transition: box-shadow 120ms ease; }
:host([softui]) .stepper button:active, :host([softui]) .rs-btn:active, :host([softui]) .e-nav button:active { box-shadow: var(--pressed); transform: none; }
:host([softui]) .stepper button:disabled, :host([softui]) .rs-btn:disabled { box-shadow: none; }
/* wells: segmented controls, the tabs, the switch's track, the chart */
:host([softui]) .seg, :host([softui]) .tabs, :host([softui]) .e-chart { background: var(--bg); box-shadow: var(--pressed); }
:host([softui]) .e-chart { border-radius: 14px; }
:host([softui]) .seg button[aria-pressed="true"], :host([softui]) .tabs button[aria-selected="true"] { background: var(--bg); box-shadow: var(--raised); }
:host([softui]) .switch { background: var(--bg); box-shadow: var(--pressed); }
:host([softui]) .switch[aria-checked="true"] { background: var(--accent); box-shadow: inset 2px 2px 5px rgba(0,0,0,.25); }
:host([softui]) .pill-switch { background: var(--bg); box-shadow: var(--raised); border-color: transparent; }
:host([softui]) .sa-item[aria-current="true"] { background: var(--bg); box-shadow: var(--pressed); }
@media (max-width: 600px) { :host([softui]) .tabs { box-shadow: var(--shadow); } :host([softui]) .tabs button[aria-selected="true"] { box-shadow: var(--pressed); } }
@media (prefers-reduced-transparency: reduce) {
  .card, .chip, .fchip, .toast, .sheet { background: var(--surface-solid) !important; backdrop-filter: none; -webkit-backdrop-filter: none; }
  .backdrop { display: none; }
}
@media (prefers-reduced-motion: reduce) { .live { animation: none; } button.card, .card.tap, .rs-btn, .fchip, .switch::after, .stepper button, .unit-tap, .pill-switch, .auto-more, .disc { transition: none; } }
/* third look "Kachelwand" (tile wall): a calm wall of tiles in rows per job, numbers and headings in a condensed face, one
   amber accent; rooms tinted by their own temperature, the tapped room grows and shows its target, the others step back */
.hero { display: none; }
:host([tiles]) {
  --bg: #eceef1; --surface: #ffffff; --surface-solid: #ffffff; --line: rgba(18,22,28,.09); --fg: #12161c; --fg-2: #3f4855; --fg-3: #5a6472;
  --accent: #a8620e; --glass: #ffffff; --glass-strong: #ffffff; --edge: transparent; --edge-low: transparent; --tile-line: rgba(18,22,28,.1);
  --shadow: none; --font-display: "Antonio", "Oswald", "Roboto Condensed", "Arial Narrow", sans-serif;
}
:host([tiles][dark]) {
  --bg: #0c0f14; --surface: #12171e; --surface-solid: #12171e; --line: rgba(255,255,255,.08); --fg: #e9edf2; --fg-2: #c3cad4; --fg-3: #aeb7c4;
  --accent: #e8a33d; --glass: #12171e; --glass-strong: #161c25; --tile-line: #1f2836;
}
:host([tiles]) .backdrop { display: none; }
:host([tiles]) .card, :host([tiles]) .chip, :host([tiles]) .fchip, :host([tiles]) .toast {
  background: var(--surface) !important; border: 1px solid var(--tile-line) !important; backdrop-filter: none; -webkit-backdrop-filter: none; box-shadow: none; }
:host([tiles]) .card::before, :host([tiles]) .chip::before, :host([tiles]) .fchip::before, :host([tiles]) .toast::before, :host([tiles]) .sheet::before,
:host([tiles]) .card::after { display: none; }
:host([tiles]) .card { border-radius: 16px !important; }
:host([tiles]) .sheet { background: var(--surface-solid); backdrop-filter: none; -webkit-backdrop-filter: none; }
:host([tiles]) .head h1, :host([tiles]) .floor h2 { font-family: var(--font-display); text-transform: uppercase; letter-spacing: .01em; font-weight: 700; }
:host([tiles]) .head h1 { font-size: 2.1rem; }
:host([tiles]) .floor h2 { font-size: 1.7rem; font-weight: 600; }
:host([tiles]) .label { letter-spacing: .14em; }
:host([tiles]) .room-temp, :host([tiles]) .fact .huge, :host([tiles]) .e-big, :host([tiles]) .e-mid, :host([tiles]) .unit-temps b, :host([tiles]) .rs-v b,
:host([tiles]) .stepper output { font-family: var(--font-display); letter-spacing: 0; }
:host([tiles]) .fchip.run { background: color-mix(in srgb, var(--accent) 22%, var(--surface)) !important; border-color: color-mix(in srgb, var(--accent) 55%, transparent) !important; }
:host([tiles]) .hero { display: grid; gap: 8px; }
:host([tiles]) .hero h2 { margin: 0; font: 700 clamp(3rem, 7.5vw, 5.5rem)/.92 var(--font-display); text-transform: uppercase; }
:host([tiles]) .hero p { margin: 0; font-size: 1.1rem; color: var(--fg-2); }
:host([tiles]) .status > .chip { display: none; }  /* outside, mode and status are in the headline; the function pills stay */
/* the unit: its four air temperatures as tiles instead of the drawn picture */
:host([tiles]) svg.diagram { display: none; }
:host([tiles]) .unit-temps { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
@media (max-width: 600px) { :host([tiles]) .unit-temps { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
:host([tiles]) .unit-temps div { background: var(--rt, var(--line)); border: 1px solid var(--tile-line); padding: 14px; }
:host([tiles]) .unit-temps b { font-size: 2.2rem; font-weight: 700; }
/* rooms: a row to swipe through, each tile in its own temperature; the tapped one grows and shows - and + */
:host([tiles]) .rooms { display: flex; gap: 12px; overflow-x: auto; scroll-snap-type: x proximity; padding: 2px 2px 10px; scrollbar-width: thin; }
:host([tiles]) .rooms > .room { flex: 0 0 172px; scroll-snap-align: start; background: var(--rt, var(--surface)) !important; min-height: 168px;
  display: flex; flex-direction: column; justify-content: space-between; transition: flex-basis 260ms cubic-bezier(.22,1,.36,1), opacity 200ms ease-out; }
:host([tiles]) .rooms > .room.open { flex-basis: 300px; border: 2px solid var(--accent) !important; }
:host([tiles]) .rooms:has(.open) > .room:not(.open) { opacity: .7; }
:host([tiles]) .room .state { display: none; }
:host([tiles]) .room-temp { font-size: 3.2rem; font-weight: 700; line-height: 1; }
:host([tiles]) .room:not(.open) .rs-btn { display: none; }
:host([tiles]) .room.open .room-name .nm::after { content: " ›"; color: var(--accent); }
:host([tiles]) .room:not(.open) .room-step { justify-content: flex-start; margin-top: 6px; }
:host([tiles]) .room:not(.open) .rs-v { display: flex; gap: 6px; align-items: baseline; }
:host([tiles]) .room:not(.open) .rs-v b { font: 600 .9375rem/1.2 var(--font); }
:host([tiles]) .room .rs-btn { width: 48px; height: 48px; }
/* wide screens: the tabs as a bar on the left */
@media (min-width: 821px) {
  :host([tiles]) .page { max-width: 1320px; grid-template-columns: 176px minmax(0, 1fr); column-gap: 36px; align-items: start; }
  :host([tiles]) .page > .head { grid-row: 1 / span 20; position: sticky; top: 20px; flex-direction: column; align-items: stretch; gap: 26px; }
  :host([tiles]) .page > :not(.head) { grid-column: 2; }
  :host([tiles]) .head h1 { margin: 0; }
  :host([tiles]) .tabs { flex-direction: column; background: transparent; padding: 0; gap: 6px; }
  :host([tiles]) .tabs button { display: flex; align-items: center; gap: 12px; height: 46px; padding: 0 14px; border-radius: 10px; border: 1px solid transparent;
    text-transform: uppercase; letter-spacing: .14em; font-size: .8125rem; text-align: left; color: var(--fg-2); }
  :host([tiles]) .tabs button[aria-selected="true"] { border-color: var(--accent); color: var(--accent); background: transparent; box-shadow: none; }
  :host([tiles]) .tabs svg { display: block; width: 20px; height: 20px; }
}
@media (prefers-reduced-motion: reduce) { :host([tiles]) .rooms > .room { transition: none; } }
`;
const FAN_BLADES = '<path d="M0-12C4-12 5-4 0 0-5-4-4-12 0-12ZM12 0C12 4 4 5 0 0 4-5 12-4 12 0ZM0 12C-4 12-5 4 0 0 5 4 4 12 0 12ZM-12 0C-12-4-4-5 0 0-4 5-12 4-12 0Z" fill="var(--fg-2)"/>';
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
  // an action of an entity; a failure (e.g. "solar surplus needs a sensor") is shown in the page's own toast, like its
  // other hints, instead of Home Assistant's; the caller only puts its view back
  call(domain, service, data) {
    return this._hass.callService(domain, service, data, undefined, false).catch(async err => {
      this._toast(await this._errorText(err, domain, service), null);
      throw err;
    });
  }
  async _errorText(err, domain, service) {
    const e = err || {};
    if (e.translation_domain && e.translation_key && this._hass.loadBackendTranslation) {
      try {
        const text = (await this._hass.loadBackendTranslation("exceptions", e.translation_domain))(
          `component.${e.translation_domain}.exceptions.${e.translation_key}.message`, e.translation_placeholders);
        if (text) return text;
      } catch (_) { /* fall back to the message the server sent */ }
    }
    return e.message || fill(this.t.failed, { a: `${domain}.${service}` });
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
          <div class="tabs" role="tablist"><button role="tab" id="tab-home" aria-selected="true"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 11l8-7 8 7v9h-5v-6H9v6H4z"/></svg>${t.home}</button><button role="tab" id="tab-energy" aria-selected="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2L4 14h7l-1 8 9-12h-7z"/></svg>${t.energy}</button><button role="tab" id="tab-settings" aria-selected="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h10M18 7h2M4 17h2M10 17h10M16 4.5v5M8 14.5v5"/></svg>${t.settings}</button></div>
        </header>
        <div class="view" id="v-home">
        <div class="hero" id="hero"><h2 id="hero-h"></h2><p class="num" id="hero-sub"></p></div>
        <div class="status" id="status">
          <span class="chip">${t.outside} <b class="num" id="c-out">–</b></span>
          <span class="chip" id="c-op-wrap">${t.op} <b id="c-op">–</b></span>
          <span class="chip"><span class="dot" id="c-dot"></span><b id="c-ok">${t.ok}</b></span>
        </div>
        <section class="top">
          <section class="card" aria-label="${t.unit}">
            <div class="card-head"><span class="label">${t.unit}</span>
              <button class="pill-switch" id="boost"><span class="pill-text">${t.boost}<small id="boost-left" hidden></small></span><span class="switch" id="boost-sw" aria-hidden="true" aria-checked="false"></span></button></div>
            <button class="unit-tap" id="unit">
              <div class="hint" style="margin-top:4px">${t.level} <b class="num" id="u-level">–</b> · ${t.tapUnit}</div>
              <svg class="diagram" viewBox="0 0 720 360" aria-hidden="true">
                <defs>
                  <linearGradient id="g-fresh" x1="1" x2="0"><stop id="gf0" offset="0"/><stop id="gf1" offset="1"/></linearGradient>
                  <linearGradient id="g-supply" x1="1" x2="0"><stop id="gs0" offset="0"/><stop id="gs1" offset="1"/></linearGradient>
                  <linearGradient id="g-extract" x1="0" x2="1"><stop id="ge0" offset="0"/><stop id="ge1" offset="1"/></linearGradient>
                  <linearGradient id="g-exhaust" x1="0" x2="1"><stop id="gx0" offset="0"/><stop id="gx1" offset="1"/></linearGradient>
                  <radialGradient id="g-glow"><stop offset="0" stop-color="var(--glowc)" stop-opacity=".55"/><stop offset="1" stop-color="var(--glowc)" stop-opacity="0"/></radialGradient>
                  <linearGradient id="g-box" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".3"/><stop offset="1" stop-color="#fff" stop-opacity=".06"/></linearGradient>
                </defs>
                <!-- as the unit is built: house side left (extract air in at the top, supply air out at the bottom), outside right
                     (fresh air in at the top, exhaust air out at the bottom); the two paths cross in the heat exchanger -->
                <text class="zone" x="8" y="186">${t.house}</text><text class="zone" x="712" y="186" text-anchor="end">${t.out}</text>
                <rect x="190" y="36" width="340" height="288" rx="34" fill="url(#g-box)" stroke="var(--edge)" stroke-width="1.2"/>
                <path class="tube" d="M 660 96 L 490 96 Q 460 96 440 116 L 380 176" stroke="url(#g-fresh)"/>
                <path class="tube" d="M 340 184 L 280 244 Q 260 264 230 264 L 60 264" stroke="url(#g-supply)"/>
                <path class="tube" d="M 60 96 L 230 96 Q 260 96 280 116 L 340 176" stroke="url(#g-extract)"/>
                <path class="tube" d="M 380 184 L 440 244 Q 460 264 490 264 L 660 264" stroke="url(#g-exhaust)"/>
                <path class="flow" d="M 660 96 L 490 96 Q 460 96 440 116 L 380 176"/>
                <path class="flow" d="M 340 184 L 280 244 Q 260 264 230 264 L 60 264"/>
                <path class="flow" d="M 60 96 L 230 96 Q 260 96 280 116 L 340 176"/>
                <path class="flow" d="M 380 184 L 440 244 Q 460 264 490 264 L 660 264"/>
                <rect x="326" y="146" width="68" height="68" rx="10" transform="rotate(45 360 180)" fill="var(--glass-strong)" stroke="var(--edge)"/>
                <path d="M 345 165 L 375 195 M 375 165 L 345 195 M 360 155 L 360 205 M 335 180 L 385 180" stroke="var(--fg-3)" stroke-width="1" opacity=".6"/>
                <text class="t-small" x="360" y="236" text-anchor="middle">${t.hx}</text>
                <circle cx="250" cy="264" r="44" fill="url(#g-glow)" id="hp-glow"/>
                <rect x="238" y="240" width="24" height="48" rx="6" id="hp-supply"/>
                <rect x="458" y="240" width="24" height="48" rx="6" id="hp-exhaust"/>
                <text class="t-small" x="250" y="306" text-anchor="middle" id="hp-label">${t.heatPump}</text>
                <g transform="translate(140 264)"><circle r="17" fill="var(--glass-strong)" stroke="var(--edge)"/><g id="fan-s">${FAN_BLADES}</g></g>
                <g transform="translate(580 264)"><circle r="17" fill="var(--glass-strong)" stroke="var(--edge)"/><g id="fan-e">${FAN_BLADES}</g></g>
                <text class="t-small num" id="rpm-s-t" x="140" y="234" text-anchor="middle"></text>
                <text class="t-small num" id="rpm-e-t" x="580" y="234" text-anchor="middle"></text>
                <text class="t-name" x="60" y="44">${t.extract}</text><text class="t-val num" id="v-extract" x="60" y="76">–</text>
                <text class="t-name" x="660" y="44" text-anchor="end">${t.fresh}</text><text class="t-val num" id="v-fresh" x="660" y="76" text-anchor="end">–</text>
                <text class="t-name" x="660" y="312" text-anchor="end">${t.exhaust}</text><text class="t-val num" id="v-exhaust" x="660" y="344" text-anchor="end">–</text>
                <text class="t-name" x="60" y="312">${t.supply}</text><text class="t-val num" id="v-supply" x="60" y="344">–</text>
              </svg>
              <div class="unit-temps">
                <div><span>${t.extract}</span><b class="num" id="m-extract">–</b></div><div><span>${t.fresh}</span><b class="num" id="m-fresh">–</b></div>
                <div><span>${t.supply}</span><b class="num" id="m-supply">–</b></div><div><span>${t.exhaust}</span><b class="num" id="m-exhaust">–</b></div>
              </div>
              <div class="unit-chips">
                <span class="chip soft" id="ch-comp">${t.compressor} <b class="num" id="comp">–</b></span>
                <span class="chip soft" id="rec-wrap">${t.recovery} <b class="num" id="rec">–</b></span>
                <span class="chip soft" id="co2-wrap">CO₂ <b class="num" id="co2">–</b></span>
                <span class="chip soft" id="hum-wrap">${t.humidity} <b class="num" id="hum">–</b></span>
              </div>
            </button>
          </section>
          <div class="card tap" id="water" role="button" tabindex="0" aria-label="${t.water}">
            <div class="card-head"><span class="label">${t.water}</span>
              <span class="working" id="w-working" hidden><svg width="14" height="14" viewBox="0 0 28 37" aria-hidden="true">${FLAME}</svg><span id="w-who"></span></span>
              <span class="hint" id="w-hint">${t.tapUnit}</span></div>
            <div class="a-body">
              <div class="tankA">
                <svg viewBox="0 0 150 330" aria-hidden="true">
                  <defs><clipPath id="tank-clip"><rect x="6" y="6" width="138" height="318" rx="56"/></clipPath>
                    <linearGradient id="wg" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="var(--tank-deep)"/><stop offset=".55" stop-color="var(--tank-mid)"/><stop offset="1" stop-color="var(--tank-top)"/></linearGradient>
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
            <div class="water-set" id="w-set-wrap"><span class="w-set-l">${t.target}<span class="saved" id="w-saved">${t.sent}</span></span>
              <div class="stepper"><button id="w-dn" aria-label="${t.colder}">−</button><output class="num" id="w-target">–</output><button id="w-up" aria-label="${t.warmer}">+</button></div></div>
          </div>
        </section>
        <div id="floors"></div>
        </div>
        <div class="view" id="v-energy" hidden></div>
        <div class="view" id="v-settings" hidden></div>
      </div>
      <div class="toast" id="toast" role="status" hidden><span id="toast-text"></span><button id="toast-undo">${t.undo}</button></div>
      <div class="scrim" id="scrim"></div>
      <div class="sheet" id="sheet" role="dialog" aria-modal="true" hidden><div class="grabber"></div>
        <button class="close" id="sheet-close" aria-label="${t.close}">✕</button><div id="sheet-body"></div></div>`;
    this.$("menu").addEventListener("click", () => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    this.$("boost").addEventListener("click", () => this._toggle("Intensivlueftung"));
    this.$("tab-home").addEventListener("click", () => this._tab("home"));
    this.$("tab-energy").addEventListener("click", () => this._tab("energy"));
    this.$("tab-settings").addEventListener("click", () => this._tab("settings"));
    this.$("unit").addEventListener("click", e => this._sheetVentilation(e.currentTarget));
    // the card opens the sheet; the target changes only with − and + (a swipe over the card while scrolling changed it)
    const water = this.$("water");
    water.addEventListener("click", e => { if (!e.target.closest(".stepper")) this._sheetWater(water); });
    water.addEventListener("keydown", e => { if (e.target === water && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); this._sheetWater(water); } });
    this._wStep = this._stepper(this.$("w-dn"), this.$("w-up"), this.$("w-target"), "SollWassertemperatur", {
      fmt: v => `${this.fmt(v, 0)}°`,
      done: () => { const s = this.$("w-saved"); s.classList.add("show"); setTimeout(() => s.classList.remove("show"), 1400); },
    });
    this._fill = new Spring(0, () => {});  // the level of the tank; its surface is drawn with the air (one loop)
    this._buildSheet();
    this._buildToast();
    this._buildAir();
    this._startAir();
    let tab = "home"; try { tab = sessionStorage.getItem("proxon-tab") || "home"; } catch (_) { /* no storage */ }
    if (tab === "settings" || tab === "energy") this._tab(tab, true);
  }

  // ---------- tabs: home and settings; the new one slides in from its side ----------
  _tab(name, instant) {
    if (this._current === name) { if (name === "settings") this._closeSection(); return; }  // the tab again: back to the list
    const order = ["home", "energy", "settings"], from = order.indexOf(this._current || "home");
    this._current = name;
    try { sessionStorage.setItem("proxon-tab", name); } catch (_) { /* no storage */ }
    for (const n of order) { this.$(`tab-${n}`).setAttribute("aria-selected", n === name); this.$(`v-${n}`).hidden = n !== name; }
    this.$("h-title").textContent = this.t[name];
    if (name === "settings" && !this._settingsBuilt) this._buildSettings();
    if (name === "energy" && !this._energyBuilt) this._buildEnergy();
    this._slideIn(this.$(`v-${name}`), order.indexOf(name) < from ? -1 : 1, instant);
    if (name === "settings") this._updateSettings();
    if (name === "energy") this._updateEnergy();
  }

  // a view slides in from its side (a tab, a settings section on a phone); each view has its own spring, so starting
  // one never leaves another stopped half-way (shifted sideways)
  _slideIn(el, dir, instant) {
    const sp = el._in || (el._in = new Spring(1, v => { el.style.opacity = clamp(v, 0, 1).toFixed(3); el.style.translate = `${((1 - v) * el._dir * 24).toFixed(1)}px 0`; }));
    el._dir = dir;
    if (instant) sp.set(1); else { sp.set(0); sp.to(1, { damping: 1, response: 0.35 }); }
  }

  // ---------- live values ----------
  _update() {
    if (!this._built || !this._hass) return;
    const t = this.t, dark = this._hass.themes && this._hass.themes.darkMode;
    this.toggleAttribute("dark", !!dark);
    const look = (this._config || {}).look;  // the look chosen in the options
    this.toggleAttribute("softui", look === "soft");
    this.toggleAttribute("tiles", look === "tiles");
    if (look === "tiles") loadTileFont((this._config || {}).static);
    const deg = key => { const v = this.num(key); return v === null ? "–" : `${this.fmt(v)}°`; };
    this.$("c-out").textContent = deg("T3Frischluft");
    const op = this.st("AktuellerBetrieb");
    this.$("c-op-wrap").hidden = !op;
    if (op) this.$("c-op").textContent = this._hass.formatEntityState ? this._hass.formatEntityState(op) : op.state;
    const fault = (this.st("Stoerung") || {}).state === "on", filter = (this.st("FilterRestStunden_warning") || {}).state === "on";
    this.$("c-ok").textContent = fault ? t.fault : filter ? t.filter : t.ok;
    this.$("c-dot").style.background = fault ? "var(--danger)" : filter ? "var(--warm)" : "var(--fine)";
    // unit
    [["fresh", "T3Frischluft"], ["supply", "T1Zuluft"], ["extract", "T7Abluft"], ["exhaust", "T4Fortluft"]].forEach(([el, k]) => {
      this.$(`v-${el}`).textContent = deg(k); this.$(`m-${el}`).textContent = deg(k);
      this.$(`m-${el}`).parentElement.style.setProperty("--rt", tempTint(this.num(k), this.hasAttribute("dark")));
    });
    const rs = this.num("DrehzahlZuluft"), re = this.num("DrehzahlAbluft");
    const rpm = v => v === null ? "–" : Math.round(v).toLocaleString(this._hass.language || undefined);
    this.$("rpm-s-t").textContent = rs === null ? "" : `${rpm(rs)} U/min`; this.$("rpm-e-t").textContent = re === null ? "" : `${rpm(re)} U/min`;
    this._rpm = rs || 0; this._rpmS = rs || 0; this._rpmE = re || 0;
    // the tubes coloured by temperature: inlet and outlet of each air path (the exchanger in the middle)
    const tc = this._tempColor.bind(this), tF = this.num("T3Frischluft"), tZ = this.num("T1Zuluft"), tA = this.num("T7Abluft"), tO = this.num("T4Fortluft");
    const mid = (a, b) => (a !== null && b !== null ? (a + b) / 2 : a ?? b);
    [["gf0", tF], ["gf1", mid(tF, tZ)], ["gs0", mid(tF, tZ)], ["gs1", tZ], ["ge0", tA], ["ge1", mid(tA, tO)], ["gx0", mid(tA, tO)], ["gx1", tO]]
      .forEach(([id, v]) => this.$(id).setAttribute("stop-color", tc(v)));
    // the heat pump: heating (warm on the supply side), cooling (cold on the supply side) or off
    const comp = this.num("DrehzahlKompressor"), opSt = this.st("AktuellerBetrieb"), mode = opSt ? opSt.state : null;
    const runs = (comp || 0) > 0, cooling = mode === "cooling";
    this.$("hp-supply").setAttribute("fill", runs ? (cooling ? "var(--cold)" : "var(--water-hot)") : "var(--fg-3)");
    this.$("hp-exhaust").setAttribute("fill", runs ? (cooling ? "var(--water-hot)" : "var(--cold)") : "var(--fg-3)");
    this.$("hp-glow").style.display = runs ? "" : "none";
    this.shadowRoot.querySelector("svg.diagram").style.setProperty("--glowc", cooling ? "var(--cold)" : "var(--water-hot)");
    this.$("hp-label").textContent = runs ? (cooling ? t.hpCools : t.hpHeats) : t.hpIdle;
    this.$("ch-comp").hidden = comp === null;
    this.$("comp").textContent = runs ? `${rpm(comp)} U/min` : t.compOff;
    const co2 = this.num("CurrentCO2"), hum = this.num("LuftfeuchteRel");
    this.$("co2-wrap").hidden = !co2; this.$("co2").textContent = `${this.fmt(co2, 0)} ppm`;
    this.$("hum-wrap").hidden = hum === null; this.$("hum").textContent = `${this.fmt(hum, 0)} %`;
    const boost = (this.st("Intensivlueftung") || {}).state === "on";
    this.$("boost").hidden = !this.st("Intensivlueftung");
    this.$("boost").setAttribute("aria-pressed", this.swOn("Intensivlueftung")); this.$("boost-sw").setAttribute("aria-checked", this.swOn("Intensivlueftung"));
    this.$("boost-sw").setAttribute("aria-busy", this.swBusy("Intensivlueftung"));
    const left = this.num("IntensivlueftungsRestDauer");
    // the time left, small below the name, while boost ventilation runs
    this.$("boost-left").hidden = !boost || left === null;
    this.$("boost-left").textContent = left > 0 ? fill(t.left, { m: this.fmt(left, 0) }) : t.leftSoon;
    const lvl = this.num("IstLuefterstufe") ?? this.num("Luefterstufe");
    this.$("u-level").textContent = boost ? t.levelBoost : lvl === null ? "–" : Math.round(lvl);
    // the tile wall's headline: is everything running, and the unit in one line
    this.$("hero-h").textContent = fault ? t.heroFault : filter ? t.heroFilter : t.heroOk;
    this.$("hero-sub").textContent = [op ? this.$("c-op").textContent : null, boost ? t.levelBoost : lvl === null ? null : fill(t.heroLevel, { n: Math.round(lvl) }),
      this.num("T3Frischluft") === null ? null : fill(t.heroOut, { v: deg("T3Frischluft") })].filter(Boolean).join(" · ");
    const rec = this.num("Waermerueckgewinnung");
    this.$("rec-wrap").hidden = rec === null; this.$("rec").textContent = `${this.fmt(rec, 0)} %`;
    this._level = boost ? 4.5 : (lvl || 0);
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
      const wn = this.st("SollWassertemperatur");
      this.$("w-set-wrap").hidden = !wn;
      this._wStep.sync();
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
    if (this._energyBuilt && this._current === "energy") this._updateEnergy();
  }

  // ---------- the air: flowing along the tubes with the level, the fans turning by their speed ----------
  _buildAir() {
    this._flows = [...this.shadowRoot.querySelectorAll(".flow")];
    this._speed = new Spring(0, () => {}); this._angleS = 0; this._angleE = 0; this._flowOff = 0;
  }
  _tempColor(v) {  // cold blue below 5 °C, a neutral grey around 20 °C, warm orange from 35 °C
    if (v === null || v === undefined) return "#9aa6b2";
    const mix = (a, b, f) => `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * f)).join(",")})`;
    const cold = [90, 160, 230], mid = [176, 184, 192], warm = [242, 112, 44];
    return v <= 20 ? mix(cold, mid, clamp((v - 5) / 15, 0, 1)) : mix(mid, warm, clamp((v - 20) / 15, 0, 1));
  }
  _startAir() {
    if (this._air || !this._flows) return;
    let last = performance.now();
    const step = t => {
      const dt = Math.min(0.05, (t - last) / 1000); last = t;
      // the air flows faster with a higher level (it stops with the fans); the fans turn by their own speed
      const want = (this._rpmS || this._rpmE) ? (this._level || 1) : 0;
      if (Math.abs(this._speed.target - want) > 0.01) this._speed.to(want, { damping: 1, response: 0.9 });
      const moving = !reduceMotion.matches;
      if (moving) this._flowOff -= dt * 12 * this._speed.x;
      this._flows.forEach(f => f.setAttribute("stroke-dashoffset", this._flowOff.toFixed(1)));
      const fanStep = rpm => (moving ? clamp(rpm, 0, 3000) / 60 * 360 * dt * 0.12 : 0);
      this._angleS = (this._angleS + fanStep(this._rpmS || 0)) % 360; this._angleE = (this._angleE + fanStep(this._rpmE || 0)) % 360;
      this.$("fan-s").setAttribute("transform", `rotate(${this._angleS.toFixed(1)})`);
      this.$("fan-e").setAttribute("transform", `rotate(${this._angleE.toFixed(1)})`);
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
      const sts = f.on.map(k => this.st(k)).filter(Boolean), on = sts.some(st => st.state === "on");
      const planned = f.k === "holiday" && !on && !!(sts[0] && sts[0].attributes.plan_on_at);
      const shown = on || planned, running = on && f.run(sts.find(st => st.state === "on"), this);
      if (running && ["solar", "price", "boostww", "legionella"].includes(f.k) && !who) who = t.fn[f.k][0];
      const card = this._fnCards.get(f.k);
      if (shown && !card) this._showFn(f);
      else if (!shown && card && !card.leaving) this._hideFn(f.k);
      if (shown) this._fnDetail(f, running, planned);
    }
    this.$("w-working").hidden = !who; this.$("w-who").textContent = who; this.$("w-hint").hidden = !!who;
  }
  _fnDetail(f, running, planned) {
    const card = this._fnCards.get(f.k); if (!card) return;
    const t = this.t, words = t.fn[f.k], c = t.chip, lang = this._hass.language || undefined;
    const when = iso => new Date(iso).toLocaleString(lang, { weekday: "short", day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit" });
    const soon = iso => {  // short: the weekday and time within the next six days, else the date
      const d = new Date(iso);
      return d - Date.now() < 6 * 86400000 ? d.toLocaleString(lang, { weekday: "short", hour: "2-digit", minute: "2-digit" }) : d.toLocaleDateString(lang, { day: "numeric", month: "numeric" });
    };
    const status = f.status && this.st(f.status), said = status ? (this._hass.formatEntityState ? this._hass.formatEntityState(status) : status.state) : t.fnOn;
    let full = said, short = said;
    if (f.k === "holiday") {
      const a = (this.st("Urlaubsmodus") || {}).attributes || {};
      if (planned) { full = fill(t.fnPlanned, { d: when(a.plan_on_at) }); short = fill(c.from, { d: soon(a.plan_on_at) }); }
      else if (a.plan_off_at) { full = fill(words[2], { d: when(a.plan_off_at) }); short = fill(c.until, { d: soon(a.plan_off_at) }); }
      else full = short = words[1];
    } else if (running && f.temp) {
      full = fill(words[1], { t: this.fmt(this.num(f.temp), 0) }); short = fill(f.k === "boostww" ? c.boost : c.heat, { t: this.fmt(this.num(f.temp), 0) });
    } else if (running && f.k === "cooling") {
      full = fill(words[1], { l: this.fmt(this.num("KuehlStufe"), 0) }); short = fill(c.cool, { l: this.fmt(this.num("KuehlStufe"), 0) });
    } else if (running && f.k === "legionella") { full = words[1]; short = c.hot; }
    else if (f.k === "legionella" && status && status.attributes.planned_next) {
      full = fill(t.fnNext, { s: said, d: when(status.attributes.planned_next) }); short = soon(status.attributes.planned_next);
    }
    card.querySelector(".ft").textContent = short;
    card.classList.toggle("run", !!running);
    card.querySelector(".live").hidden = !running;
    const name = words[0];
    card.title = `${name}: ${full}`; card.setAttribute("aria-label", `${name}: ${full}`);
  }
  _showFn(f) {  // a chip in the status row, a hint and not a switch: a tap opens the function's settings
    const t = this.t, el = document.createElement("button");
    el.className = "fchip"; el.style.setProperty("--tint", `var(${f.tint})`);
    el.innerHTML = `<span class="fi"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${f.icon}" fill="none" stroke="var(${f.tint})" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
      <b>${t.chip[f.k] || t.fn[f.k][0]}</b><span class="ft num"></span><span class="live" hidden></span>`;
    el.addEventListener("click", () => this._openSetting(f.sec));
    el.appear = new Spring(0, v => { el.style.opacity = clamp(v, 0, 1).toFixed(3); el.style.scale = (0.85 + 0.15 * v).toFixed(4); });
    el.appear.set(0);
    const order = FUNCS.map(x => x.k), next = order.slice(order.indexOf(f.k) + 1).map(k => this._fnCards.get(k)).find(x => x && !x.leaving);
    this.$("status").insertBefore(el, next || null);
    this._fnCards.set(f.k, el);
    el.appear.to(1, { damping: 0.75, response: 0.35 });
  }
  _hideFn(k) {
    const el = this._fnCards.get(k); if (!el || el.leaving) return;
    el.leaving = true; this._fnCards.delete(k);
    el.appear.to(0, { damping: 1, response: 0.25, onRest: () => el.remove() });
  }
  // the settings of a function: its section, an automatic function opened in place
  _openSetting(sec) {
    if (this._current !== "settings") this._tab("settings");
    const auto = SETTINGS.some(x => x.id === sec && x.auto);
    this._showSection(auto ? "auto" : sec, true);
    const head = auto && this.$(`ah-${sec}`);
    if (head) {
      if (head.getAttribute("aria-expanded") !== "true") head.click();
      requestAnimationFrame(() => head.scrollIntoView({ block: "center", behavior: reduceMotion.matches ? "auto" : "smooth" }));
    }
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
  _roomTile(n) {  // the tile opens the room's sheet; its target changes only with − and + (a swipe just scrolls)
    const t = this.t, el = document.createElement("div");
    el.className = "card room tap"; el.setAttribute("role", "button"); el.tabIndex = 0;
    el.innerHTML = `<span class="state"></span><div class="room-name"><span class="nm"></span><span class="icon"></span></div>
      <div class="room-temp num"></div>
      <div class="room-step"><button class="rs-btn" data-d="-1" aria-label="${t.colder}">−</button>
        <span class="rs-v"><small>${t.target}</small><b class="num tv"></b></span><button class="rs-btn" data-d="1" aria-label="${t.warmer}">+</button></div>`;
    const $ = s => el.querySelector(s), [dn, up] = el.querySelectorAll(".rs-btn");
    let r = null;
    const digits = () => (r && r.step < 1 ? 1 : 0);
    const ring = x => (x.element === "heating" ? "var(--warm)" : x.temp - x.target < -1 ? "var(--cold)" : "transparent");
    const render = () => {
      r = this._room(n); if (!r) return;
      $(".nm").textContent = r.name;
      $(".icon").innerHTML = r.element === "heating" ? `<svg class="elem" viewBox="0 0 28 37" aria-hidden="true">${FLAME}</svg>`
        : `<svg class="elem ${r.element === "off" ? "off" : ""}" viewBox="0 0 24 24" aria-hidden="true">${RADIATOR}</svg>`;
      $(".icon").title = t.element[r.element] || "";
      $(".room-temp").innerHTML = r.temp === undefined || r.temp === null ? "–" : `${this.fmt(r.temp)}<small>°</small>`;
      $(".state").style.setProperty("--ring", r.available && r.temp != null ? ring(r) : "transparent");
      el.style.setProperty("--rt", tempTint(r.temp, this.hasAttribute("dark")));
      $(".tv").textContent = `${this.fmt(r.target, digits())}°`;
      dn.disabled = !r.available || r.target <= r.min; up.disabled = !r.available || r.target >= r.max;
      el.setAttribute("aria-label", `${r.name}: ${this.fmt(r.temp)} °C, ${t.target} ${this.fmt(r.target, digits())} °C, ${t.element[r.element] || ""}`);
    };
    const saved = () => { const v = $(".rs-v"); v.classList.add("ok"); setTimeout(() => v.classList.remove("ok"), 1400); };
    [dn, up].forEach(btn => btn.addEventListener("click", e => { e.stopPropagation(); this._roomStep(n, Number(btn.dataset.d), saved); }));
    el.addEventListener("click", e => {
      if (e.target.closest(".rs-btn") || !r) return;
      // the tile wall: a tap opens the tile (- and +), another tap closes it again; the name of an open tile opens the details
      if (this.hasAttribute("tiles")) {
        if (!el.classList.contains("open")) {
          el.parentElement.querySelectorAll(".room.open").forEach(o => o.classList.remove("open"));
          el.classList.add("open");
          return;
        }
        if (!e.target.closest(".room-name")) { el.classList.remove("open"); return; }
      }
      this._sheetRoom(n, el);
    });
    el.addEventListener("keydown", e => { if (e.target === el && r && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); this._sheetRoom(n, el); } });
    return { el, render };
  }
  // one step of a room's target: shown at once (tile and sheet); taps in a row are sent once, 0.6 s after the last
  _roomStep(n, d, done) {
    const r = this._room(n); if (!r || !r.available) return;
    const v = clamp(Math.round((r.target + d * r.step) / r.step) * r.step, r.min, r.max);
    this._pending.set(n, { v, at: Date.now() }); this._update();
    const timers = this._roomTimers || (this._roomTimers = new Map());
    clearTimeout(timers.get(n));
    timers.set(n, setTimeout(() => {
      timers.delete(n);
      const cur = this._room(n), p = this._pending.get(n);
      if (!cur || !p) return;  // back where it was: nothing to send
      this._pending.set(n, { v: p.v, at: Date.now() });
      this.call("climate", "set_temperature", { entity_id: cur.entity, temperature: p.v }).then(() => done && done(), () => { this._pending.delete(n); this._update(); });
    }, 600));
  }

  _unit(key, d = 0) {  // "46 °C", "1.500 W", "30 min": the number entity's own unit
    const u = ((this.st(key) || {}).attributes || {}).unit_of_measurement || "";
    return v => `${this.fmt(v, d)}${u ? (u === "°C" || u === "%" ? (u === "%" ? " %" : "°") : ` ${u}`) : ""}`;
  }

  // ---------- energy: stacked columns per day (week, month) or month (year), from Home Assistant's statistics; today and
  // the running month live from the sensors. Back and forth through weeks, months and years. ----------
  _buildEnergy() {
    this._energyBuilt = true; this._ePer = "week"; this._eOff = 0; this._eSel = null; this._eStats = {};
    const t = this.t, e = t.e;
    this.$("v-energy").innerHTML = `<section class="card e-card">
        <div class="e-head"><div style="display:grid;gap:4px"><span class="label" id="e-title"></span><div class="e-big num" id="e-total"></div><div class="sub num" id="e-sub"></div></div>
          <div style="display:grid;gap:8px;justify-items:end"><div class="seg" id="e-per">${["week", "month", "year"].map(p => `<button data-p="${p}">${e.per[p]}</button>`).join("")}</div>
            <div class="e-nav"><button id="e-csv" aria-label="${e.csv}" title="${e.csv}"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14"/></svg></button><button id="e-prev" aria-label="${e.earlier}">‹</button><button id="e-next" aria-label="${e.later}">›</button></div></div></div>
        <div class="e-chart" id="e-chart" role="img"><div id="e-gridl"></div><div class="e-cols" id="e-cols"></div></div>
        <div class="e-xl" id="e-xl"></div>
        <div class="e-detail num" id="e-detail"></div>
        <div class="e-key" id="e-key"></div><p class="hint" id="e-empty" hidden>${e.none}</p><p class="hint" id="e-failed" hidden>${e.failed}</p></section>
      <section class="card e-card" id="e-cost"><span class="label">${e.cost}</span>
        <div class="e-cost-grid"><div><span class="sub">${e.running}</span><div id="e-cost-run"></div></div>
          <div id="e-cost-fc-wrap"><span class="sub">${e.expected}</span><div id="e-cost-fc"></div></div></div>
        <p class="hint" id="e-cost-none" hidden>${e.noPrice}</p></section>
      <div class="e-grid"><section class="card e-card"><span class="label">${t.now}</span><div class="e-mid num" id="e-now"></div><div class="e-key" id="e-now-key"></div></section>
        <section class="card e-card" id="e-run-card"><span class="label">${e.runtime}</span><div id="e-run"></div></section></div>
      <p class="e-note">${e.note}</p>`;
    this.$("v-energy").querySelectorAll("#e-per button").forEach(b => b.addEventListener("click", () => {
      this._ePer = b.dataset.p; this._eOff = 0; this._eSel = null; this._updateEnergy();
    }));
    this.$("e-prev").addEventListener("click", () => { this._eOff -= 1; this._eSel = null; this._updateEnergy(); });
    this.$("e-csv").addEventListener("click", () => this._eCsv());
    this.$("e-next").addEventListener("click", () => { this._eOff = Math.min(0, this._eOff + 1); this._eSel = null; this._updateEnergy(); });
    this.$("e-cols").addEventListener("click", ev => { const c = ev.target.closest(".e-col"); if (c) { this._eSel = +c.dataset.i; this._updateEnergy(); } });
  }
  _eParts() { return ENERGY_PARTS.filter(p => this.id(p.keys[0])); }
  _eSum(keys, suffix = "") { const v = keys.map(k => this.num(k + suffix)).filter(x => x !== null); return v.length ? v.reduce((a, b) => a + b, 0) : null; }
  _kwh(v) { return v === null ? "–" : this.fmt(v, v >= 100 ? 0 : v >= 10 ? 1 : 2); }
  _money(v) {
    if (v === null || !Number.isFinite(v)) return "";
    try { return v.toLocaleString(this._hass.language || undefined, { style: "currency", currency: (this._hass.config || {}).currency || "EUR" }); } catch (_) { return this.fmt(v, 2); }
  }
  // what a period cost: the unit's cost sensor, the estimated hot water at the same average price
  // Home Assistant's time zone: days, weeks, months and years follow it, not the browser's (a phone abroad shows the home's days)
  _tz() { return (this._hass.config || {}).time_zone || Intl.DateTimeFormat().resolvedOptions().timeZone; }
  // a moment as a calendar day in that time zone (as a UTC date, for day arithmetic and names), and its wall-clock time
  _civil(t) {
    const tz = this._tz();
    if (!this._tzFmt || this._tzZone !== tz) {
      this._tzZone = tz;
      this._tzFmt = new Intl.DateTimeFormat("en-US", { timeZone: tz, year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric", second: "numeric", hourCycle: "h23" });
    }
    const o = {}; for (const p of this._tzFmt.formatToParts(t)) o[p.type] = Number(p.value);
    return { day: new Date(Date.UTC(o.year, o.month - 1, o.day)), wall: Date.UTC(o.year, o.month - 1, o.day, o.hour % 24, o.minute, o.second) };
  }
  _midnight(day) {  // the moment a calendar day begins in that time zone
    let t = day.getTime();
    for (let i = 0; i < 2; i++) t = day.getTime() - (this._civil(new Date(t)).wall - t);
    return new Date(t);
  }
  // where the running day / week / month / year began (and ends)
  _eBounds(suffix) {
    const d = this._civil(new Date()).day, y = d.getUTCFullYear(), m = d.getUTCMonth(), day = d.getUTCDate(), wd = (d.getUTCDay() + 6) % 7;
    const [a, b] = { Heute: [[y, m, day], [y, m, day + 1]], Woche: [[y, m, day - wd], [y, m, day - wd + 7]], Monat: [[y, m, 1], [y, m + 1, 1]],
      Jahr: [[y, 0, 1], [y + 1, 0, 1]] }[suffix];
    return [this._midnight(new Date(Date.UTC(...a))), this._midnight(new Date(Date.UTC(...b)))];
  }
  // a fixed tariff (€/kWh), or null with a dynamic one
  _ePrice() { const ct = Number((this._config || {}).price); return ct > 0 ? ct / 100 : null; }
  // whether a cost sensor has counted the whole running period (it only counts from when a price was set)
  _eCostComplete(suffix) {
    const since = ((this.st(`Stromkosten${suffix}`) || {}).attributes || {}).counting_since;
    return !!since && new Date(since) - this._eBounds(suffix)[0] <= 60000;
  }
  // what the running period cost: the cost sensor where it counted the whole period (at the price of its time), else the
  // consumption at the fixed price; the estimated hot water at the same average price
  _eCost(suffix, water) {
    const cost = this.num(`Stromkosten${suffix}`), unit = this.num(`EnergieGesamt${suffix}`), fixed = this._ePrice();
    if (fixed !== null && !(cost !== null && this._eCostComplete(suffix))) return unit === null ? null : (unit + (water || 0)) * fixed;
    if (cost === null) return null;
    return cost + (water && unit > 0.01 ? water * cost / unit : 0);
  }
  // the forecast of the running month / year: the unit's own, plus the hot water extended at the same rate (and its cost at
  // the same average price)
  _eForecast(fs) {
    const fc = this.num(`EnergieGesamt${fs}Prognose`); if (fc === null) return null;
    const water = this._eSum(["EnergieWarmwasserWP", "EnergieHeizstab"].filter(k => this.id(k)), fs) || 0, now = new Date(), end = this._eBounds(fs)[1];
    const since = ((this.st(`EnergieWarmwasserWP${fs}`) || {}).attributes || {}).counting_since;
    let wfc = 0;
    if (water && since) { const done = now - new Date(since); if (done > (fs === "Monat" ? 12 : 72) * 3600000) wfc = water * (end - new Date(since)) / done; }
    const fixed = this._ePrice(), fcCost = this.num(`Stromkosten${fs}Prognose`);
    if (fixed !== null && !(fcCost !== null && this._eCostComplete(fs))) return { kwh: fc + wfc, cost: (fc + wfc) * fixed, waterCost: wfc * fixed };
    const unitE = this.num(`EnergieGesamt${fs}`), c = this.num(`Stromkosten${fs}`);
    const price = c !== null && unitE > 0.01 ? c / unitE : null;
    return { kwh: fc + wfc, cost: fcCost === null ? null : fcCost + (price ? wfc * price : 0), waterCost: price ? wfc * price : null };
  }
  // the shown period as a CSV file: one row per day (week, month) or month (year), kWh per part and the total. German files use
  // ";" and a decimal comma, so a spreadsheet opens them as numbers
  _eCsv() {
    const L = this._eLast; if (!L || L.empty) return;
    const e = this.t.e, de = (this._hass.language || "").startsWith("de"), sep = de ? ";" : ",";
    const num = v => (Math.round(v * 1000) / 1000).toFixed(3).replace(".", de ? "," : ".");
    const day = d => d.toISOString().slice(0, L.P.gran === "month" ? 7 : 10);
    const head = [L.P.gran === "month" ? e.csvMonth : e.csvDate, ...L.parts.map(p => `${e[p.k]} (kWh)`), `${e.csvTotal} (kWh)`];
    const rows = L.cols.filter(c => !c.future).map(c => [day(c.d), ...c.values.map(num), num(c.total)]);
    const text = [head, ...rows].map(r => r.map(v => (String(v).includes(sep) || /["\n]/.test(v) ? `"${String(v).replace(/"/g, '""')}"` : v)).join(sep)).join("\r\n") + "\r\n";
    const url = URL.createObjectURL(new Blob(["\ufeff" + text], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url; a.download = `proxon-energie-${day(L.cols[0].d)}.csv`;
    this.shadowRoot.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  _eKey(parts, values, unit = "kWh", fmt = v => this._kwh(v)) {
    return parts.map((p, i) => `<span><i style="background:var(${p.color})"></i>${this.t.e[p.k]} <b class="num">${fmt(values[i])} ${unit}</b></span>`).join("");
  }
  // the period shown: its start and end (moments), its columns (calendar days or months, as UTC dates) and how they are named
  _ePeriod() {
    const today = this._civil(new Date()).day, per = this._ePer, off = this._eOff, lang = this._hass.language || undefined;
    const Y = today.getUTCFullYear(), M = today.getUTCMonth(), D = today.getUTCDate(), wd = (today.getUTCDay() + 6) % 7;
    const cd = (y, m, d) => new Date(Date.UTC(y, m, d)), name = (d, o) => d.toLocaleDateString(lang, { ...o, timeZone: "UTC" });
    let from, to, cols = [], label, title;
    if (per === "week") {
      from = cd(Y, M, D - wd + 7 * off); to = cd(Y, M, D - wd + 7 * off + 7);
      for (let i = 0; i < 7; i++) cols.push(cd(Y, M, D - wd + 7 * off + i));
      label = d => this.t.daysShort[(d.getUTCDay() + 6) % 7];
      title = off === 0 ? this.t.e.week : `${name(from, { day: "numeric", month: "short" })} – ${name(cols[6], { day: "numeric", month: "short" })}`;
    } else if (per === "month") {
      from = cd(Y, M + off, 1); to = cd(Y, M + off + 1, 1);
      for (let d = from; d < to; d = cd(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate() + 1)) cols.push(d);
      label = d => ([1, 5, 10, 15, 20, 25, 30].includes(d.getUTCDate()) ? String(d.getUTCDate()) : "");
      title = name(from, { month: "long", year: "numeric" });
    } else {
      from = cd(Y + off, 0, 1); to = cd(Y + off + 1, 0, 1);
      for (let m = 0; m < 12; m++) cols.push(cd(Y + off, m, 1));
      label = d => name(d, { month: "narrow" });
      title = String(Y + off);
    }
    return { per, start: this._midnight(from), end: this._midnight(to), cols, label, title, name, today, gran: per === "year" ? "month" : "day", current: off === 0 };
  }
  // Home Assistant's long-term statistics: each counter's rise per day / month in a period (only rows that exist count:
  // a period before the counters existed stays empty). Kept per period; the running one is fetched again every hour (the
  // finished days of it change only then), a failed query is tried again after half a minute.
  _eFetch(tag, start, end, gran) {
    const old = this._eStats[tag];
    if (old && !(old.failed && Date.now() > old.retryAt)) return old.done ? old : null;
    const entry = this._eStats[tag] = { done: false, failed: false, rows: {} };
    const keys = [...this._eParts().flatMap(p => p.keys), "EnergieGesamt", "Stromkosten"].filter(k => this.id(k));
    const finish = (res, failed) => {
      keys.forEach(k => { entry.rows[k] = ((res || {})[this.id(k)] || []).map(r => ({ start: new Date(r.start), change: Number.isFinite(r.change) ? r.change : 0 })); });
      entry.done = true; entry.failed = !!failed; entry.retryAt = Date.now() + 30000;
      if (this._current === "energy") this._updateEnergy();
    };
    if (!this._hass.callWS || !keys.length) finish({});
    else this._hass.callWS({ type: "recorder/statistics_during_period", start_time: start.toISOString(), end_time: end.toISOString(),
      statistic_ids: keys.map(k => this.id(k)), period: gran, types: ["change"] }).then(r => finish(r), () => finish({}, true));
    return entry.done ? entry : null;
  }
  // costs: what today, this week, month and year cost so far, and what the month and the year will probably cost
  _updateCosts(parts) {
    const e = this.t.e, lang = this._hass.language || undefined, today = this._civil(new Date()).day, has = !!this.id("Stromkosten") || this._ePrice() !== null;
    this.$("e-cost-none").hidden = has;
    this.$("v-energy").querySelector(".e-cost-grid").hidden = !has;
    if (!has) return;
    const waterKeys = ["EnergieWarmwasserWP", "EnergieHeizstab"].filter(k => this.id(k)), all = parts.flatMap(p => p.keys);
    const row = (label, cost, kwh) => `<div class="e-run"><span>${label}${kwh === null ? "" : `<small class="num">${this._kwh(kwh)} kWh</small>`}</span><b class="num">${this._money(cost) || "–"}</b></div>`;
    const month = today.toLocaleDateString(lang, { month: "long", timeZone: "UTC" }), year = String(today.getUTCFullYear());
    this.$("e-cost-run").innerHTML = [["Heute", e.today], ["Woche", e.week], ["Monat", month], ["Jahr", year]].map(([sfx, label]) =>
      row(label, this._eCost(sfx, this._eSum(waterKeys, sfx) || 0), this._eSum(all, sfx))).join("");
    const fm = this._eForecast("Monat"), fy = this._eForecast("Jahr");
    this.$("e-cost-fc-wrap").hidden = !fm && !fy;
    this.$("e-cost-fc").innerHTML = [
      fm ? row(fill(e.fc, { p: month }), fm.cost, fm.kwh) : "",
      fy ? row(fill(e.fc, { p: year }), fy.cost, fy.kwh) : "",
      fy && fy.cost !== null ? row(e.avgMonth, fy.cost / 12, null) : "",
      fy && fy.waterCost ? `<p class="hint">${fill(e.ofWater, { v: this._money(fy.waterCost) })}</p>` : "",
    ].join("");
  }
  _updateEnergy() {
    if (!this._energyBuilt) return;
    const t = this.t, e = t.e, parts = this._eParts(), P = this._ePeriod();
    this.$("v-energy").querySelectorAll("#e-per button").forEach(b => b.setAttribute("aria-pressed", b.dataset.p === P.per));
    this.$("e-next").disabled = P.current;
    const stats = this._eFetch(`${P.per}${P.start.getTime()}${P.current ? `@${Math.floor(Date.now() / 3600000)}` : ""}`, P.start, P.end, P.gran);
    // a row belongs to the column of its day / month in Home Assistant's time zone
    const sameBucket = (a, b) => a.getUTCFullYear() === b.getUTCFullYear() && a.getUTCMonth() === b.getUTCMonth() && (P.gran === "month" || a.getUTCDate() === b.getUTCDate());
    const dayOf = r => r.day || (r.day = this._civil(r.start).day);
    const liveSuffix = P.gran === "month" ? "Monat" : "Heute";
    // the columns: each part's rise per day / month; the running day / month comes live from the sensors
    const inCol = (k, d) => (stats ? (stats.rows[k] || []).filter(r => sameBucket(dayOf(r), d)) : []);
    const cols = P.cols.map(d => {
      const live = P.current && sameBucket(d, P.today), future = d > P.today && !live;
      const values = parts.map(p => (future ? 0 : live ? this._eSum(p.keys, liveSuffix) || 0 : p.keys.reduce((a, k) => a + inCol(k, d).reduce((x, r) => x + r.change, 0), 0)));
      return { d, values, total: values.reduce((a, b) => a + b, 0), future, live };
    });
    const hasRows = !!stats && parts.some(p => p.keys.some(k => (stats.rows[k] || []).length));
    const failed = !!stats && stats.failed, empty = !!stats && !failed && !P.current && !hasRows;
    this.$("e-prev").disabled = empty || this._eOff <= -60;
    this.$("e-empty").hidden = !empty; this.$("e-failed").hidden = !failed;
    // the period's totals: live sensors for the running period, the statistics for earlier ones
    const suffix = { week: "Woche", month: "Monat", year: "Jahr" }[P.per];
    const totals = P.current ? parts.map(p => this._eSum(p.keys, suffix) || 0) : parts.map((p, i) => cols.reduce((a, c) => a + c.values[i], 0));
    const sum = totals.reduce((a, b) => a + b, 0), wi = parts.findIndex(p => p.k === "water"), water = wi >= 0 ? totals[wi] : 0;
    // an earlier period's cost, column by column: what the cost sensor counted then (at the price of its time, the hot water at
    // the same average price), else - before there was a cost sensor - the consumption at the fixed price
    let cost = null;
    if (P.current) cost = this._eCost(suffix, water);
    else if (hasRows) {
      const fixed = this._ePrice();
      cost = cols.reduce((a, c) => {
        const cr = inCol("Stromkosten", c.d), w = wi >= 0 ? c.values[wi] : 0;
        if (cr.length) {
          const cc = cr.reduce((x, r) => x + r.change, 0), u = inCol("EnergieGesamt", c.d).reduce((x, r) => x + r.change, 0);
          return (a ?? 0) + cc + (w && u > 0.01 ? w * cc / u : 0);
        }
        return fixed !== null ? (a ?? 0) + c.total * fixed : a;
      }, null);
    }
    this.$("e-title").textContent = P.title;
    this.$("e-total").innerHTML = empty || failed ? "" : `${this._kwh(sum)}<small>kWh</small>`;
    let fcText = "";
    if (P.current && P.per !== "week") {
      const f = this._eForecast(P.per === "month" ? "Monat" : "Jahr");
      if (f) fcText = fill(e.forecast, { v: `${this._kwh(f.kwh)} kWh` }) + (f.cost !== null ? ` · ${this._money(f.cost)}` : "");
    }
    this.$("e-sub").textContent = empty ? "" : [this._money(cost), fcText].filter(Boolean).join(" · ");
    // the chart: a scale that ends on a round number, three lines
    const top = Math.max(...cols.map(c => c.total), 0);
    const step = top > 0 ? (() => { const raw = top / 2, mag = 10 ** Math.floor(Math.log10(raw)); return [1, 2, 2.5, 5, 10].map(m => m * mag).find(v => v >= raw); })() : 1;
    const max = step * 2;
    this.$("e-gridl").innerHTML = empty ? "" : [0, 1, 2].map(i => `<div class="e-grid-l" style="bottom:${(i / 2 * 100).toFixed(1)}%"><span>${this.fmt(step * i, Number.isInteger(step) ? 0 : 1)}</span></div>`).join("");
    const sel = this._eSel ?? cols.findIndex(c => c.live);
    this.$("e-chart").style.setProperty("--gap", cols.length > 12 ? "2px" : "6px");
    this.$("e-xl").style.setProperty("--gap", cols.length > 12 ? "2px" : "6px");
    this.$("e-cols").innerHTML = empty ? "" : cols.map((c, i) => `<button class="e-col${i === sel ? " sel" : ""}${c.future ? " future" : ""}" data-i="${i}" aria-label="${P.name(c.d, P.gran === "month" ? { month: "long", year: "numeric" } : { day: "numeric", month: "numeric", year: "numeric" })}: ${this._kwh(c.total)} kWh">${
      parts.map((p, j) => (c.values[j] > 0 ? `<span style="height:${(c.values[j] / max * 100).toFixed(2)}%;background:var(${p.color})"></span>` : "")).join("")}</button>`).join("");
    this.$("e-xl").innerHTML = empty ? "" : cols.map(c => `<span>${P.label(c.d)}</span>`).join("");
    this.$("e-chart").setAttribute("aria-label", `${P.title}: ${this._kwh(sum)} kWh`);
    const s = cols[sel];
    this.$("e-detail").innerHTML = !empty && s ? `${s.live ? (P.gran === "month" ? P.name(s.d, { month: "long" }) : e.today)
      : P.name(s.d, P.gran === "month" ? { month: "long" } : { weekday: "short", day: "numeric", month: "numeric" })}: <b>${this._kwh(s.total)} kWh</b>${
      s.total > 0 ? " · " + parts.map((p, j) => `${e[p.k].replace(/ \(.*\)$/, "")} ${this._kwh(s.values[j])}`).join(" · ") : ""}` : "";
    this.$("e-key").innerHTML = empty ? "" : this._eKey(parts, totals);
    this._eLast = { P, parts, cols, empty }; this.$("e-csv").disabled = empty || failed;
    this._updateCosts(parts);
    // now
    const power = parts.map(p => this._eSum(p.power));
    this.$("e-now").innerHTML = `${this.fmt(power.reduce((a, b) => a + (b || 0), 0), 0)}<small>W</small>`;
    this.$("e-now-key").innerHTML = this._eKey(parts, power, "W", v => (v === null ? "–" : this.fmt(v, 0)));
    // running time today
    const rows = RUNTIMES.filter(([, h]) => this.st(h));
    this.$("e-run-card").hidden = !rows.length;
    this.$("e-run").innerHTML = rows.map(([k, h, n]) => {
      const starts = this.num(n);
      return `<div class="e-run"><span>${e[k]}</span><b class="num">${this.fmt(this.num(h) || 0, 1)} h${starts === null ? "" : ` · ${starts === 1 ? e.start : fill(e.starts, { n: this.fmt(starts, 0) })}`}</b></div>`;
    }).join("");
  }

  // ---------- settings: grouped like iOS settings, every row an entity of this unit ----------
  _label(key) { const s = this.st(key); return esc(this.t.s[key] || (s ? (s.attributes.friendly_name || key).replace(/^Proxon\s+/, "") : key)); }
  _buildSettings() {
    this._settingsBuilt = true; this._settingCtl = [];
    const t = this.t, has = k => !!this.id(k);
    const body = rows => rows.map(([kind, key]) => {
      const hint = (t.hint || {})[key];
      if (kind === "switch") return this._sw(`set-${key}`, this._label(key), hint);
      if (kind === "select") {
        const st = this.st(key), opts = st ? st.attributes.options || [] : [];
        const label = (o, i) => key === "LegionellenTag" ? t.daysShort[i] : (this._hass.formatEntityState ? this._hass.formatEntityState(st, o) : o);
        return `<div class="row"><span class="row-label">${this._label(key)}</span><div class="seg" id="sel-${key}">${opts.map((o, i) => `<button data-o="${esc(o)}">${esc(label(o, i))}</button>`).join("")}</div></div>`;
      }
      if (kind === "num") return `<div class="row stepped"><span class="row-label">${this._label(key)}${NOW_OF[key] ? `<small class="now-val num" id="nowv-${key}" hidden></small>` : ""}</span>
        <div class="stepper"><button id="dn-${key}" aria-label="−">−</button><output class="num" id="out-${key}"></output><button id="up-${key}" aria-label="+">+</button></div><small class="row-sub">${hint ? `${hint}<br>` : ""}<span class="num" id="rng-${key}"></span></small></div>`;
      if (kind === "time") return `<div class="row"><span class="row-label">${this._label(key)}</span><input class="tin num" type="time" step="60" id="time-${key}" aria-label="${this._label(key)}"></div>`;
      if (kind === "datetime") return `<div class="row"><span class="row-label">${this._label(key)}</span><input class="tin num" type="datetime-local" id="dt-${key}" aria-label="${this._label(key)}"></div>`;
      if (kind === "button") return `<button class="textbtn warn" id="btn-${key}">${this._label(key)}</button>`;
      return t.days.map((name, d) => `<button class="day sched" id="day-${d}"><span>${name}</span><span class="num" id="day-sum-${d}"></span></button>`).join("");
    }).join("");
    // the pages: one per section, the automatic functions together on one
    const pages = [], autos = [];
    this._autoSecs = [];
    for (const sec of SETTINGS) {
      const rows = sec.rows.filter(r => r[0] === "days" ? has("Zeitprogramm0") : has(r[1]));
      if (!rows.length) continue;
      if (!sec.auto) {
        const status = sec.status && has(sec.status) ? `<p class="foot" id="foot-${sec.id}"></p>` : "";
        pages.push({ id: sec.id, color: sec.color, html: `<div class="card">${body(rows)}</div>${status}` });
        continue;
      }
      if (!autos.length) pages.push({ id: "auto", color: AUTO_COLOR });
      const main = sec.main && has(sec.main) ? sec.main : null;
      this._autoSecs.push({ sec, main, rows });
      autos.push(`<div class="auto"><div class="auto-head" role="button" tabindex="0" aria-expanded="false" id="ah-${sec.id}">${icon(sec.id, sec.color)}
          <span class="auto-l">${t.s[sec.id]}<small id="foot-${sec.id}"></small></span>
          ${main ? `<button class="switch" role="switch" id="set-${main}" aria-label="${this._label(main)}" aria-checked="false"></button>` : `<span class="tag" id="tag-${sec.id}"></span>`}
          <span class="disc" aria-hidden="true">›</span></div>
        <div class="auto-more" id="am-${sec.id}" inert><div>${body(rows.filter(r => r[1] !== main))}</div></div></div>`);
    }
    const auto = pages.find(p => p.id === "auto");
    if (auto) auto.html = `<div class="card">${autos.join("")}</div>`;
    const ver = (this._config || {}).version;
    this.$("v-settings").innerHTML = `<div class="sa" id="sa">
        <nav class="card sa-list" aria-label="${t.sections}">${pages.map(p => `<button class="sa-item" data-p="${p.id}" aria-current="false">${icon(p.id, p.color)}
          <span class="sa-t"><b>${t.s[p.id]}</b><small id="navsum-${p.id}"></small></span></button>`).join("")}</nav>
        <div class="sa-detail"><button class="sa-back" id="sa-back">‹ ${t.settings}</button>
          ${pages.map(p => `<section class="group sa-page" id="page-${p.id}" hidden><h2 class="sa-h">${icon(p.id, p.color)}${t.s[p.id]}</h2>${p.html}</section>`).join("")}</div>
      </div>${ver ? `<p class="version num">Proxon Control ${ver}</p>` : ""}`;
    const v = this.$("v-settings");
    for (const sec of SETTINGS) for (const [kind, key] of sec.rows) {
      if (kind === "switch" && v.querySelector(`#set-${CSS.escape(key)}`)) v.querySelector(`#set-${CSS.escape(key)}`).addEventListener("click", () => this._toggle(key));
      if (kind === "num" && v.querySelector(`#out-${CSS.escape(key)}`)) {
        const q = id => v.querySelector(`#${id}-${CSS.escape(key)}`), a = this.st(key).attributes, fmt = this._unit(key, Number(a.step) < 1 ? 1 : 0);
        q("rng").textContent = fill(t.span, { a: fmt(Number(a.min)), b: fmt(Number(a.max)) });
        this._settingCtl.push(this._stepper(q("dn"), q("up"), q("out"), key, { factor: this._isLong(key) ? 5 : 1, fmt }));
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
    // an automatic function opens its limits in place (its switch only switches)
    for (const { sec } of this._autoSecs) {
      const head = this.$(`ah-${sec.id}`), more = this.$(`am-${sec.id}`);
      const flip = () => { const open = head.getAttribute("aria-expanded") !== "true"; head.setAttribute("aria-expanded", open); more.classList.toggle("open", open); more.inert = !open; };
      head.addEventListener("click", e => { if (!e.target.closest(".switch")) flip(); });
      head.addEventListener("keydown", e => { if (e.target === head && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); flip(); } });
    }
    v.querySelectorAll(".sa-item").forEach(b => b.addEventListener("click", () => this._showSection(b.dataset.p, true)));
    this.$("sa-back").addEventListener("click", () => this._closeSection());
    let sec = null; try { sec = sessionStorage.getItem("proxon-sec"); } catch (_) { /* no storage */ }
    this._showSection(sec, false);
  }
  _narrowSettings() { const b = this.$("sa-back"); return !!b && getComputedStyle(b).display !== "none"; }
  _showSection(id, open) {  // the chosen section on the right; on a phone it is pushed over the list
    const sa = this.$("sa"); if (!sa) return;
    if (!id || !this.$(`page-${id}`)) id = sa.querySelector(".sa-item").dataset.p;
    this._section = id;
    try { sessionStorage.setItem("proxon-sec", id); } catch (_) { /* no storage */ }
    sa.querySelectorAll(".sa-item").forEach(b => b.setAttribute("aria-current", b.dataset.p === id));
    sa.querySelectorAll(".sa-page").forEach(p => { p.hidden = p.id !== `page-${id}`; });
    if (!open) return;
    const push = this._narrowSettings() && !sa.classList.contains("open");
    sa.classList.add("open");
    if (push) {
      this.shadowRoot.querySelector(".page").scrollIntoView({ block: "start" });
      this._slideIn(sa.querySelector(".sa-detail"), 1);
      requestAnimationFrame(() => this.$("sa-back").focus());
    }
  }
  _closeSection() {
    const sa = this.$("sa"); if (!sa || !sa.classList.contains("open")) return;
    const narrow = this._narrowSettings();
    sa.classList.remove("open");
    if (!narrow) return;
    this._slideIn(sa.querySelector(".sa-list"), -1);
    const item = sa.querySelector(`.sa-item[data-p="${this._section}"]`); if (item) item.focus();
  }
  // the line under a section in the list: what matters at a glance
  _secSummary(id) {
    const t = this.t, on = k => this.swOn(k), yn = k => (on(k) ? t.yes : t.no), deg = k => { const v = this.num(k); return v === null ? "–" : `${this.fmt(v, 0)}°`; };
    const lang = this._hass.language || undefined;
    if (id === "vent") {
      const co2 = this.num("CurrentCO2"), hum = this.num("LuftfeuchteRel"), parts = [];
      if (co2 !== null && co2 > 0) parts.push(`CO₂ ${this.fmt(co2, 0)} ppm`);
      if (hum !== null) parts.push(`${t.humidity} ${this.fmt(hum, 0)} %`);
      return parts.length ? `${t.nowLabel}: ${parts.join(" · ")}` : "";
    }
    if (id === "schedule") {
      const mon = this._daySummary(0), day = mon === t.empty ? "" : `${t.daysShort[0]} ${mon}`;
      return [this.id("ZeitprogrammAktiv") ? yn("ZeitprogrammAktiv") : "", day].filter(Boolean).join(" · ");
    }
    if (id === "holiday") {
      const at = k => { const st = this.st(k); const d = st ? new Date(st.state) : null; return d && !isNaN(d) ? d : null; };
      const day = d => d.toLocaleDateString(lang, { day: "numeric", month: "short" }), from = at("UrlaubAb"), to = at("UrlaubBis");
      if (on("Urlaubsmodus")) return to ? fill(t.onUntil, { d: day(to) }) : t.yes;
      return from && to && to > new Date() ? fill(t.planned, { a: day(from), b: day(to) }) : t.noPlan;
    }
    if (id === "water") return [`${t.target} ${deg("SollWassertemperatur")}`, this.id("T300Betriebsart") ? `${t.pump} ${yn("T300Betriebsart").toLowerCase()}` : ""].filter(Boolean).join(" · ");
    if (id === "auto") {
      const n = (this._autoSecs || []).filter(a => this._autoOn(a)).length;
      return fill(t.nOn, { a: n, b: (this._autoSecs || []).length });
    }
    if (id === "night") {
      if (!on("NachtabsenkungAktiv")) return t.no;
      const tm = k => { const st = this.st(k); return st && /^\d\d:\d\d/.test(st.state) ? st.state.slice(0, 5) : ""; };
      return [t.yes, deg("NachtabsenkungTemperatur"), tm("NachtabsenkungStart") && `${tm("NachtabsenkungStart")}–${tm("NachtabsenkungEnde")}`].filter(Boolean).join(" · ");
    }
    return "";
  }
  _autoOn({ main, rows }) { return main ? this.swOn(main) : rows.some(([kind, key]) => kind === "switch" && this.swOn(key)); }
  _isLong(key) { const a = (this.st(key) || {}).attributes || {}; return (a.max - a.min) / (Number(a.step) || 1) > 200; }
  // − and +: a tap moves the value on screen at once; taps in a row are sent once, 0.6 s after the last. Until the unit
  // reports the new value (at most 8 s) the sent one stays on screen. factor: steps per tap (5 for long ranges).
  _stepper(dn, up, out, key, { factor = 1, fmt, done } = {}) {
    let want = null, sent = null, timer = 0;
    const attrs = () => (this.st(key) || {}).attributes || {};
    const value = () => {
      if (sent && (this.num(key) === sent.v || Date.now() - sent.at > 8000)) sent = null;
      return want ?? (sent ? sent.v : this.num(key));
    };
    const show = () => {
      const v = value(), a = attrs();
      out.textContent = v === null ? "–" : fmt(v);
      dn.disabled = v === null || v <= Number(a.min); up.disabled = v === null || v >= Number(a.max);
    };
    const go = d => {
      const a = attrs(), step = (Number(a.step) || 1) * factor, base = value();
      if (base === null) return;
      want = clamp(Math.round((base + d * step) / step) * step, Number(a.min), Number(a.max)); show();
      clearTimeout(timer);
      timer = setTimeout(() => {
        const v = want; want = null;
        if (v === this.num(key)) { show(); return; }
        sent = { v, at: Date.now() }; show();
        this.call("number", "set_value", { entity_id: this.id(key), value: v }).then(() => done && done(), () => { sent = null; show(); });
      }, 600);
    };
    let hold = 0, held = false;
    const stop = () => { clearTimeout(hold); hold = 0; };
    [[dn, -1], [up, 1]].forEach(([btn, d]) => {
      btn.addEventListener("click", e => { e.stopPropagation(); if (held) { held = false; return; } go(d); });
      btn.addEventListener("pointerdown", e => {
        if (e.button > 0) return;
        held = false; stop();
        let n = 0;
        const tick = () => { held = true; n += 1; go(n > 12 ? d * 5 : d); if (!btn.disabled) hold = setTimeout(tick, n > 12 ? 90 : 140); };
        hold = setTimeout(tick, 450);  // held, not tapped: repeat
      });
      ["pointerup", "pointerleave", "pointercancel"].forEach(ev => btn.addEventListener(ev, stop));
    });
    show();
    return { sync: () => { if (want === null) show(); } };
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
        if (kind === "switch" && st) this._swDraw(`set-${key}`, key);
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
      const said = st ? (this._hass.formatEntityState ? this._hass.formatEntityState(st) : st.state) : "";
      if (foot && st) foot.textContent = sec.auto ? said : `${this.t.status}: ${said}`;
    }
    // the value measured now, at the limits it is compared with
    for (const [limit, sensor] of Object.entries(NOW_OF)) {
      const val = v.querySelector(`#nowv-${limit}`);
      if (!val) continue;
      const cur = this.num(sensor), st = this.st(limit), a = st ? st.attributes : {};
      const has = cur !== null && !(sensor === "CurrentCO2" && cur <= 0);  // a CO2 reading of 0: no sensor delivering values
      val.hidden = !has;
      if (!has) continue;
      const unit = sensor === "CurrentCO2" ? " ppm" : " %";
      val.textContent = `${this.t.nowLabel} ${this.fmt(cur, 0)}${unit}`;
    }
    for (let d = 0; d < 7; d++) {
      const el = v.querySelector(`#day-sum-${d}`);
      if (el) el.textContent = this._daySummary(d);
    }
    for (const a of this._autoSecs || []) {
      const tag = this.$(`tag-${a.sec.id}`);  // a function without its own switch in the row: "on" while one of its switches is
      if (tag) { const on = this._autoOn(a); tag.textContent = (on ? this.t.yes : this.t.no).toLowerCase(); tag.classList.toggle("on", on); }
    }
    v.querySelectorAll(".sa-item").forEach(b => { const el = this.$(`navsum-${b.dataset.p}`); if (el) el.textContent = this._secSummary(b.dataset.p); });
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
        ${sel ? `<div class="seg" id="ph-${p}-lvl">${opts.map(o => `<button data-o="${esc(o)}">${esc(this._hass.formatEntityState ? this._hass.formatEntityState(sel, o) : o)}</button>`).join("")}</div>` : ""}</div>`;
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
      if (e.target.closest("button, input") || sheet.scrollTop > 0) return;
      if (sheet.classList.contains("scrolls") && !e.target.closest(".grabber, h3, .sub")) return;
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
    const sheet = this.$("sheet");
    requestAnimationFrame(() => { sheet.classList.toggle("scrolls", sheet.scrollHeight > sheet.clientHeight + 1); this.$("sheet-close").focus(); });
  }
  _closeSheet(velocity) {
    this.$("scrim").style.pointerEvents = "none"; this._sheetRefresh = null;
    this._sheetY.to(1, { damping: 1, response: 0.3, velocity, onRest: () => { this.$("sheet").hidden = true; } });
    if (this._opener) this._opener.focus();
  }
  _sw(id, label, sub) {
    return `<div class="row"><span class="row-label">${label}${sub ? `<small>${sub}</small>` : ""}<small class="pend" id="pend-${id}" hidden></small></span><button class="switch" role="switch" id="${id}" aria-label="${label}" aria-checked="false"></button></div>`;
  }
  _swDraw(id, key) {  // a switch row: its state, and "switching on …" while that is on its way
    const b = this.$(id), pend = this.$(`pend-${id}`); if (!b) return;
    const busy = this.swBusy(key), on = this.swOn(key);
    b.setAttribute("aria-checked", on); b.setAttribute("aria-busy", busy);
    if (pend) { pend.hidden = !busy; pend.textContent = on ? this.t.switchingOn : this.t.switchingOff; }
  }
  // a switch flips at once and shows "switching on …" until the unit reports it (holiday mode writes many values and takes
  // a while); a tap meanwhile is ignored, and the action sent is the state shown (never "toggle")
  swOn(key) {
    const st = this.st(key), on = !!st && st.state === "on", p = (this._swPending || new Map()).get(key);
    if (p && (on === p.want || Date.now() - p.at > 90000)) { this._swPending.delete(key); return on; }
    return p ? p.want : on;
  }
  swBusy(key) { this.swOn(key); return !!this._swPending && this._swPending.has(key); }
  _toggle(key) {
    const e = this.id(key); if (!e || this.swBusy(key)) return;
    const want = !this.swOn(key);
    if (want && key === "Urlaubsmodus" && !this._holidayPlanned()) return;
    (this._swPending || (this._swPending = new Map())).set(key, { want, at: Date.now() });
    this._update();
    this.call("switch", want ? "turn_on" : "turn_off", { entity_id: e }).catch(() => { this._swPending.delete(key); this._update(); });
  }
  // holiday mode only with departure and return (in the future): otherwise a hint, and the first missing date is offered
  _holidayPlanned() {
    const t = this.t, at = k => { const st = this.st(k); const d = st ? new Date(st.state) : null; return d && !isNaN(d) ? d : null; };
    const start = at("UrlaubAb"), end = at("UrlaubBis");
    const problem = !start || !end ? t.holidayNeedsPlan : end <= new Date() ? t.holidayReturnPast : end <= start ? t.holidayOrder : null;
    if (!problem) return true;
    this._toast(problem, null);
    if (this._current !== "settings") this._tab("settings");
    this._showSection("holiday", true);
    const i = this.$(`dt-${!start ? "UrlaubAb" : "UrlaubBis"}`);
    if (i) requestAnimationFrame(() => { i.scrollIntoView({ block: "center", behavior: reduceMotion.matches ? "auto" : "smooth" }); i.focus(); });
    return false;
  }

  _sheetVentilation(from) {
    const t = this.t, sel = this.st("Betriebsart"), opts = sel ? sel.attributes.options || [] : [];
    const label = o => (this._hass.formatEntityState ? this._hass.formatEntityState(sel, o) : o);
    const hasLevel = !!this.id("Luefterstufe");
    this._openSheet(`<h3>${t.ventilation}</h3><p class="sub" id="v-sub"></p>
      ${hasLevel ? `<div class="row-label">${t.level}</div><div class="seg level-seg num" id="level" role="group" aria-label="${t.level}">
        ${[1, 2, 3, 4].map(n => `<button data-n="${n}" aria-label="${t.level} ${n}">${n}</button>`).join("")}</div>
        <p class="level-note" id="level-note" hidden>${t.levelAuto}</p>` : ""}
      ${sel ? `<div class="row"><span class="row-label">${t.mode}</span><div class="seg" id="mode">${opts.map(o => `<button data-o="${esc(o)}">${esc(label(o))}</button>`).join("")}</div></div>` : ""}
      ${this.id("Intensivlueftung") ? this._sw("s-boost", t.boost, this.num("IntensivlueftungsDauer") ? fill(t.boostSub, { m: this.fmt(this.num("IntensivlueftungsDauer"), 0) }) : "") : ""}
      <button class="link" id="v-more">${t.more}</button>`, from, () => {
      this.$("v-more").addEventListener("click", () => this._sheetAll("unit", from));
      const sb = this.$("s-boost"); if (sb) sb.addEventListener("click", () => this._toggle("Intensivlueftung"));
      this.shadowRoot.querySelectorAll("#mode button").forEach(b => b.addEventListener("click", () => {
        this.call("select", "select_option", { entity_id: this.id("Betriebsart"), option: b.dataset.o }).catch(() => {});
      }));
      if (hasLevel) this._wireLevel();
    }, () => {
      this.$("v-sub").textContent = `${t.supply} ${this.$("v-supply").textContent} · ${t.extract} ${this.$("v-extract").textContent} · ${this.$("rpm-s-t").textContent}`;
      const m = this.st("Betriebsart"); this.shadowRoot.querySelectorAll("#mode button").forEach(b => b.setAttribute("aria-pressed", !!m && b.dataset.o === m.state));
      this._swDraw("s-boost", "Intensivlueftung");
      const auto = (m && m.state === "eco_comfort") || (this.st("Intensivlueftung") || {}).state === "on";
      const lv = this.$("level"); if (lv) { lv.querySelectorAll("button").forEach(b => { b.disabled = auto; }); this.$("level-note").hidden = !auto; }
      if (this._levelSync) this._levelSync();
    });
  }
  _wireLevel() {  // four buttons, one per level: a tap chooses it (nothing to drag by accident)
    const lv = this.$("level"), buttons = [...lv.querySelectorAll("button")];
    const shownLevel = () => this.num("IstLuefterstufe") ?? this.num("Luefterstufe");
    let chosen = null;
    const mark = n => buttons.forEach(b => b.setAttribute("aria-pressed", +b.dataset.n === n));
    buttons.forEach(b => b.addEventListener("click", () => {
      const n = +b.dataset.n; chosen = n; mark(n);
      if (n !== this.num("Luefterstufe")) this.call("number", "set_value", { entity_id: this.id("Luefterstufe"), value: n }).catch(() => {
        chosen = null; mark(shownLevel());  // back to what the unit has
      });
    }));
    this._levelSync = () => {  // follows the unit, except while a choice is on its way
      const cur = shownLevel(); if (cur === null) return;
      if (chosen !== null && cur !== chosen) return;
      chosen = null; mark(cur);
    };
    this._levelSync();
  }
  _sheetWater(from) {
    const t = this.t, n = this.st("SollWassertemperatur");
    this._openSheet(`<h3>${t.water}</h3><p class="sub" id="w-sub"></p>
      ${n ? `<div class="row"><span class="row-label">${t.waterTarget}</span><div class="stepper"><button id="wt-dn" aria-label="${t.colder}">−</button><output class="num" id="wt-out"></output><button id="wt-up" aria-label="${t.warmer}">+</button></div></div>` : ""}
      ${this.id("T300Betriebsart") ? this._sw("s-pump", t.pump, t.pumpSub) : ""}${this.id("E-Heizstab") ? this._sw("s-heater", t.heater, t.heaterSub) : ""}
      <button class="link" id="w-more">${t.more}</button>`, from, () => {
      this._sheetCtl = n ? [this._stepper(this.$("wt-dn"), this.$("wt-up"), this.$("wt-out"), "SollWassertemperatur", { fmt: v => `${this.fmt(v, 0)} °C` })] : [];
      ["s-pump", "s-heater"].forEach((id, i) => { const b = this.$(id); if (b) b.addEventListener("click", () => this._toggle(i ? "E-Heizstab" : "T300Betriebsart")); });
      this.$("w-more").addEventListener("click", () => this._sheetAll("water", from));
    }, () => {
      this.$("w-sub").textContent = `${this.$("w-temp").textContent} · ${t.bottom} ${this.$("w-bottom").textContent}`;
      (this._sheetCtl || []).forEach(c => c.sync());
      [["s-pump", "T300Betriebsart"], ["s-heater", "E-Heizstab"]].forEach(([id, k]) => this._swDraw(id, k));
    });
  }
  _sheetRoom(n, from) {
    const t = this.t, r = this._room(n), d = r.step < 1 ? 1 : 0;
    this._openSheet(`<h3>${esc(r.name)}</h3><p class="sub" id="r-sub"></p>
      <div class="row"><span class="row-label">${t.target}<small>${fill(t.range, { a: this.fmt(r.min, 0), b: this.fmt(r.max, 0), s: this.fmt(r.step, d) })}</small></span>
        <div class="stepper"><button id="rt-dn" aria-label="${t.colder}">−</button><output class="num" id="rt-out"></output><button id="rt-up" aria-label="${t.warmer}">+</button></div></div>
      ${this._sw("s-elem", t.released, t.releasedSub)}<button class="link" id="r-more">${t.more}</button>`, from, () => {
      this.$("rt-dn").addEventListener("click", () => this._roomStep(n, -1));
      this.$("rt-up").addEventListener("click", () => this._roomStep(n, 1));
      this.$("s-elem").addEventListener("click", () => {
        const cur = this._room(n);
        this.call("climate", "set_hvac_mode", { entity_id: cur.entity, hvac_mode: cur.mode === "heat" ? "auto" : "heat" }).catch(() => {});
      });
      this.$("r-more").addEventListener("click", () => { this._closeSheet(); this.moreInfo(r.entity); });
    }, () => {
      const cur = this._room(n); if (!cur) return;
      this.$("r-sub").textContent = `${t.now} ${this.fmt(cur.temp)}° · ${t.element[cur.element] || ""}`;
      this.$("rt-out").textContent = `${this.fmt(cur.target, d)} °C`;
      this.$("rt-dn").disabled = !cur.available || cur.target <= cur.min; this.$("rt-up").disabled = !cur.available || cur.target >= cur.max;
      this.$("s-elem").setAttribute("aria-checked", cur.mode === "heat");
    });
  }

  // ---------- all values of the unit or the hot water: every entity of that part, grouped, live; tap for its history ----------
  _sheetAll(kind, from) {
    const t = this.t, ents = (this._config || {}).entities || {};
    const skip = /^(NBE\d|ZP\d|Zeitprogramm|Urlaub|Waermeelemente|Saison|Nachtkuehl|Kuehl|Nachtabsenkung|Stromkosten|Energie|Leistung)/;
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
        ${list.map(k => `<button class="day" data-e="${esc(ents[k])}"><span>${esc(name(k))}</span><span class="num" data-v="${esc(ents[k])}"></span></button>`).join("")}`).join("")}
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
    clearTimeout(this._toastTimer); this._toastTimer = setTimeout(() => this._hideToast(), clamp(text.length * 60, 5000, 12000));  // long hints stay longer
  }
  _hideToast() { this._undo = null; this._toastY.to(1.6, { damping: 1, response: 0.3, onRest: () => { this.$("toast").hidden = true; } }); }
}

if (!customElements.get("proxon-panel")) customElements.define("proxon-panel", ProxonPanel);
