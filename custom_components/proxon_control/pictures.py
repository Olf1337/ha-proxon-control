"""Dashboard pictures drawn from the unit's live values (SVG, no Home Assistant imports): the unit, the hot-water tank, the house.

* Transparent background: the picture sits on the dashboard card, whatever the theme. Texts and lines follow light / dark mode
  (automatically by the device's colour scheme, or fixed with the integration option).
* Animated (CSS inside the SVG, which also runs when the picture is shown as an image): the fans turn while the ventilation runs
  (faster at higher levels), the air moves through the ducts, the heat pump fan turns while the compressor runs, the immersion
  heater glows while it is on, and rooms with their heating element released show a flickering flame.
* The house is drawn isometric: ground floor in front, upper floor behind it (rooms on a grid per floor, the utility room with
  the unit and the T300 at the front left), supply and extract ducts from the unit; the T300 is drawn cut open.
* The layout helpers (`*_targets`, `house_layout`) tell the dashboard where things are, so tapping a room opens its thermostat.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
import math
import re
from xml.sax.saxutils import escape

TEXT = {
    "de": {
        "outside": "Außenluft", "supply": "Zuluft", "extract": "Abluft", "exhaust": "Fortluft", "level": "Stufe",
        "exchanger": "Kreuzstrom-Wärmetauscher", "heat_pump": "Wärmepumpe", "filter": "Filter", "days": "Tage",
        "tank": "Warmwasser", "target": "Soll", "actual": "Ist", "heater": "Heizstab", "on": "an", "off": "aus",
        "heater_target": "Heizstab-Soll", "house": "Haus", "unit": "Anlage", "rpm": "U/min",
        "modes": {0: "Aus", 1: "Sommer", 2: "Winter", 3: "ECO Komfort", 4: "Ofenbetrieb", 5: "Urlaub"},
        "doing": {"heat": "Heizen", "cool": "Kühlen", "vent": "Lüften", "off": "Steht"},
        "cold": "zu kalt", "fine": "passt", "warm": "zu warm", "fault": "Störung", "boost_vent": "Intensivlüftung",
        "solar": "Solar", "price": "Günstiger Strom", "boost": "Boost", "legionella": "Legionellenschutz: heizt auf 60 °C", "cooling": "Nachtkühlung", "tap": "antippen zum Einstellen",
        "ground": "Erdgeschoss", "upper": "Obergeschoss", "technik": "Technik", "charge": "Ladezustand", "shower": "reicht für ≈ {m} Min. Duschen", "middle": "Mitte",
        "bottom": "Unten", "supply_short": "Zuluft", "extract_short": "Abluft", "inside": "Innen", "vent_unit": "Lüftungsanlage",
        "floor_names": ["Erdgeschoss", "Obergeschoss"],
        "heats": "heizt",
        "status": {
            "off": "aus", "waiting": "wartet", "starting": "startet gleich", "heating_solar": "heizt", "heating_price": "heizt",
            "paused": "Pause", "blocked": "pausiert", "no_source": "kein Sensor", "idle": "bereit", "cooling": "kühlt",
            "heat_protection": "Hitzeschutz", "not_summer": "nur im Sommer", "heating": "heizt", "heater_on": "Heizstab an",
        },
    },
    "en": {
        "outside": "Outdoor air", "supply": "Supply air", "extract": "Extract air", "exhaust": "Exhaust air", "level": "Level",
        "exchanger": "Cross-flow heat exchanger", "heat_pump": "Heat pump", "filter": "Filter", "days": "days",
        "tank": "Hot water", "target": "Target", "actual": "Actual", "heater": "Immersion heater", "on": "on", "off": "off",
        "heater_target": "Heater target", "house": "House", "unit": "Unit", "rpm": "rpm",
        "modes": {0: "Off", 1: "Summer", 2: "Winter", 3: "ECO Comfort", 4: "Stove", 5: "Holiday"},
        "doing": {"heat": "Heating", "cool": "Cooling", "vent": "Ventilating", "off": "Stopped"},
        "cold": "too cold", "fine": "fine", "warm": "too warm", "fault": "Fault", "boost_vent": "Boost ventilation",
        "solar": "Solar", "price": "Cheap power", "boost": "Boost", "legionella": "Legionella protection: heating to 60 °C", "cooling": "Night cooling", "tap": "tap to adjust",
        "ground": "Ground floor", "upper": "Upper floor", "technik": "Utility room", "charge": "Charge", "shower": "≈ {m} min of showering", "middle": "Middle",
        "bottom": "Bottom", "supply_short": "Supply air", "extract_short": "Extract air", "inside": "Indoor", "vent_unit": "Ventilation unit",
        "floor_names": ["Ground floor", "Upper floor"],
        "heats": "heating",
        "status": {
            "off": "off", "waiting": "waiting", "starting": "starting", "heating_solar": "heating", "heating_price": "heating",
            "paused": "paused", "blocked": "paused", "no_source": "no sensor", "idle": "ready", "cooling": "cooling",
            "heat_protection": "heat protection", "not_summer": "summer only", "heating": "heating", "heater_on": "heater on",
        },
    },
}

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

LIGHT = (
    "--fg:#1f2933;--muted:#52606d;--line:#5f6b76;--chip:#e9edf1;--chipline:#cfd6dd;--case1:#fbfbfa;--case2:#dcdcd6;"
    "--casetop:#e6e8e5;--wall1:#b9b7ae;--wall2:#e2e0d9;--housewall:#fbfaf7;--houseline:#8a877e;--shell1:#cfd3d6;"
    "--shell2:#f8f9fa;--empty:#e8f1fb;--fanbg:#f4f6f8;--blade:#7c8590;--hub:#3d464f;"
    "--lbl:#ffffff;--lblline:#d5dbe1;--slab1:#9aa3a8;--slab2:#b8bfc3;--wallA:#eef0ee;--wallB:#e2e5e2;--sep:#ffffff;"
    "--tech:#e4e6e2;--cold:#dcebfb;--fine:#ddf3e9;--warm:#fde4d8;--none:#eef0f2;--tag:#1f2933;--tagtext:#ffffff"
)
DARK = (
    "--fg:#e6eaee;--muted:#a7b1bc;--line:#9aa6b2;--chip:#2c323a;--chipline:#454d57;--case1:#434a53;--case2:#2c3138;"
    "--casetop:#3a4048;--wall1:#4d5258;--wall2:#656b72;--housewall:#2a2f35;--houseline:#69717a;--shell1:#4a5057;"
    "--shell2:#79818a;--empty:#2b3642;--fanbg:#353b42;--blade:#b6bec7;--hub:#e1e6eb;"
    "--lbl:#262c33;--lblline:#3d4650;--slab1:#3a4148;--slab2:#4a525a;--wallA:#3a4046;--wallB:#30363c;--sep:#1b1f24;"
    "--tech:#353b42;--cold:#25405e;--fine:#1f4636;--warm:#5a3424;--none:#2f353c;--tag:#e6eaee;--tagtext:#1b1f24"
)

# picture sizes (viewBox); the dashboard needs them to place its tap areas
UNIT_W, UNIT_H = 800, 440
TANK_W, TANK_H = 440, 660


def _t(lang: str) -> dict:
    return TEXT["de" if (lang or "").startswith("de") else "en"]


def _num(data: dict, key: str) -> float | None:
    v = data.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _deg(v: float | None, digits: int = 1) -> str:
    """21,5° - rounded half up like Home Assistant shows values (22.25 -> 22,3°)."""
    if v is None:
        return "–"
    rounded = Decimal(repr(float(v))).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    return f"{rounded:.{digits}f}°".replace(".", ",")


def _svg(width: int, height: int, body: str, theme: str = "auto") -> str:
    palette = DARK if theme == "dark" else LIGHT
    dark = f"@media (prefers-color-scheme:dark){{svg{{{DARK}}}}}" if theme == "auto" else ""
    css = (
        f"svg{{{palette}}}{dark}text{{font-family:{FONT}}}"
        ".fg{fill:var(--fg)}.mu{fill:var(--muted)}.ln{stroke:var(--line)}.chip{fill:var(--chip);stroke:var(--chipline)}"
        ".s-case1{stop-color:var(--case1)}.s-case2{stop-color:var(--case2)}.casetop{fill:var(--casetop)}"
        ".s-wall1{stop-color:var(--wall1)}.s-wall2{stop-color:var(--wall2)}.hw{fill:var(--housewall);stroke:var(--houseline)}"
        ".s-shell1{stop-color:var(--shell1)}.s-shell2{stop-color:var(--shell2)}.empty{fill:var(--empty)}"
        ".fanbg{fill:var(--fanbg);stroke:var(--line)}.blade{fill:var(--blade)}.hub{fill:var(--hub)}"
        ".lbl{fill:var(--lbl);stroke:var(--lblline)}.sep{stroke:var(--sep)}.slab1{fill:var(--slab1)}.slab2{fill:var(--slab2)}"
        ".wallA{fill:var(--wallA);stroke:var(--lblline)}.wallB{fill:var(--wallB);stroke:var(--lblline)}.tech{fill:var(--tech)}"
        ".r-cold{fill:var(--cold)}.r-fine{fill:var(--fine)}.r-warm{fill:var(--warm)}.r-none{fill:var(--none)}"
        ".tag{fill:var(--tag)}.tagtext{fill:var(--tagtext)}"
        ".spin{transform-box:fill-box;transform-origin:center;animation:spin linear infinite}"
        "@keyframes spin{to{transform:rotate(360deg)}}"
        ".flow{stroke-dasharray:8 16;animation:flow 1.2s linear infinite}@keyframes flow{to{stroke-dashoffset:-24}}"
        ".glow{animation:glow 1.6s ease-in-out infinite alternate}@keyframes glow{from{opacity:.45}to{opacity:1}}"
        ".flame{transform-box:fill-box;transform-origin:50% 100%;animation:flick .9s ease-in-out infinite alternate}"
        "@keyframes flick{from{transform:scale(1,1)}to{transform:scale(.88,1.14)}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f"<style>{css}</style>{body}</svg>"
    )


def _chip_w(text: str, size: int) -> float:
    return len(text) * size * 0.58 + 26


def _chip(x: float, y: float, text: str, size: int = 15, fill: str | None = None, color: str | None = None, bold: bool = False) -> str:
    """A rounded label; (x, y) is its top left corner."""
    w, h = _chip_w(text, size), size + 14
    rect = f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h}" rx="{h / 2:.0f}" ' + (
        f'fill="{fill}" stroke="{fill}"/>' if fill else 'class="chip"/>'
    )
    txt_cls = f'fill="{color}"' if color else 'class="fg"'
    weight = ' font-weight="600"' if bold else ""
    return rect + f'<text x="{x + 13:.0f}" y="{y + h / 2 + size * 0.36:.0f}" font-size="{size}"{weight} {txt_cls}>{escape(text)}</text>'


def _chips_right(right: float, y: float, texts: list[str], size: int = 15) -> str:
    out, x = [], right
    for text in reversed(texts):
        x -= _chip_w(text, size)
        out.append(_chip(x, y, text, size))
        x -= 8
    return "".join(out)


def _chips_left(left: float, y: float, chips: list[tuple[str, str | None, str | None]], size: int = 15) -> str:
    out, x = [], left
    for text, fill, color in chips:
        out.append(_chip(x, y, text, size, fill, color))
        x += _chip_w(text, size) + 8
    return "".join(out)


def _fan(x: float, y: float, r: float, seconds: float | None) -> str:
    """A fan; turning when `seconds` (time per turn) is given."""
    blades = "".join(
        f'<path d="M0 0 C{r*.35:.1f} {-r*.8:.1f} {r*.8:.1f} {-r*.5:.1f} {r*.85:.1f} {-r*.15:.1f} Z" transform="rotate({a})" class="blade"/>'
        for a in (0, 72, 144, 216, 288)
    )
    spin = f' class="spin" style="animation-duration:{seconds:.2f}s"' if seconds else ""
    return (
        f'<g transform="translate({x},{y})"><circle r="{r+3}" class="fanbg" stroke-width="1.5"/>'
        f'<g{spin}>{blades}</g><circle r="{r*.18:.1f}" class="hub"/></g>'
    )


def _duct(path: str, color: str, light: str, moving: bool, reverse: bool = False) -> str:
    anim = f' class="flow" style="animation-direction:{"reverse" if reverse else "normal"}"' if moving else ""
    return (
        f'<path d="{path}" fill="none" stroke="{light}" stroke-width="22" stroke-linecap="round"/>'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="4"{anim} stroke-linecap="round"/>'
    )


def air_running(data: dict) -> bool:
    """The ventilation runs: unit on and a fan level."""
    mode = _num(data, "Betriebsart")
    return mode is not None and int(mode) != 0 and bool(_num(data, "IstLuefterstufe") or _num(data, "Luefterstufe"))


def _status(t: dict, key: str | None) -> str:
    return t["status"].get(key or "off", key or "")


# ---------------- the unit ----------------
def unit_targets() -> dict[str, tuple[float, float, float, float]]:
    """Tap areas in percent of the picture: centre x, centre y, width, height."""
    return {"unit": (50.0, 50.0, 300 / UNIT_W * 100, 280 / UNIT_H * 100)}


def unit_svg(data: dict, lang: str = "de", theme: str = "auto", cooling_status: str | None = None, fault: bool = False) -> str:
    """The ventilation unit: four air flows, cross-flow heat exchanger, two fans, filter, heat pump; status chips."""
    t = _t(lang)
    mode = _num(data, "Betriebsart")
    level = _num(data, "IstLuefterstufe") or _num(data, "Luefterstufe")
    running = air_running(data)
    fan_s = (2.4 / max(1.0, level)) if running and level else None
    rpm = _num(data, "DrehzahlKompressor") or 0
    cooling = bool(data.get("Kuehlbetrieb4Wegeventil"))
    doing = t["doing"]["cool" if cooling else "heat"] if rpm > 0 else (t["doing"]["vent"] if running else t["doing"]["off"])
    filter_h = _num(data, "FilterRestStunden")
    mode_txt = t["modes"].get(int(mode), "–") if mode is not None else "–"
    level_txt = f"{t['level']} {int(level)}" if level else f"{t['level']} –"

    bottom: list[tuple[str, str | None, str | None]] = [(f"{t['filter']} {round(filter_h / 24) if filter_h is not None else '–'} {t['days']}", None, None)]
    if cooling_status:
        active = cooling_status in ("cooling", "heat_protection")
        bottom.append((f"☾ {t['cooling']}: {_status(t, cooling_status)}", "#cfe3f8" if active else None, "#123c69" if active else None))
    if data.get("Intensivlueftung"):
        bottom.append((f"⟳ {t['boost_vent']}", "#fde4d8", "#6e2a10"))
    if fault:
        bottom.append((f"⚠ {t['fault']}", "#f7c1c1", "#791f1f"))

    def temp(x: float, y: float, label: str, key: str, anchor: str) -> str:
        return (
            f'<text x="{x}" y="{y}" font-size="19" class="mu" text-anchor="{anchor}">{label}</text>'
            f'<text x="{x}" y="{y + 34}" font-size="32" font-weight="600" class="fg" text-anchor="{anchor}">{_deg(_num(data, key))}</text>'
        )

    body = f"""
<defs>
<linearGradient id="case" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="s-case1"/><stop offset="1" class="s-case2"/></linearGradient>
<linearGradient id="hx" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#d6e8fb"/><stop offset="1" stop-color="#fbe0d6"/></linearGradient>
<linearGradient id="wall" x1="0" y1="0" x2="1" y2="0"><stop offset="0" class="s-wall1"/><stop offset="1" class="s-wall2"/></linearGradient>
<filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="4" stdDeviation="4" flood-opacity=".22"/></filter>
</defs>
<text x="24" y="40" font-size="28" font-weight="600" class="fg">{escape(t['unit'])}</text>
{_chips_right(UNIT_W - 20, 14, [mode_txt, doing, level_txt], 18)}
<rect x="24" y="70" width="30" height="300" rx="5" fill="url(#wall)" class="ln"/>
{''.join(f'<line x1="30" y1="{y}" x2="48" y2="{y}" class="ln" stroke-width="2"/>' for y in (122, 131, 140, 291, 300, 309))}
{_duct("M54 131 H250", "#2b7bd6", "#cfe3f8", running)}
{_duct("M54 300 H250", "#7b8794", "#dde1e5", running, reverse=True)}
{_duct("M550 131 H776", "#d1572b", "#f8d9cc", running)}
{_duct("M550 300 H776", "#c98a1a", "#f6e3bd", running, reverse=True)}
{temp(66, 78, t['outside'], 'T3Frischluft', 'start')}
{temp(66, 340, t['exhaust'], 'T4Fortluft', 'start')}
{temp(776, 78, t['supply'], 'T1Zuluft', 'end')}
{temp(776, 340, t['extract'], 'T7Abluft', 'end')}
<g filter="url(#sh)"><rect x="250" y="80" width="300" height="280" rx="12" fill="url(#case)" class="ln" stroke-width="1.5"/></g>
<path d="M262 80 H538 Q550 80 550 92 V104 H250 V92 Q250 80 262 80 Z" class="casetop"/>
<text x="264" y="97" font-size="12" class="mu" letter-spacing="1">PROXON FWT</text>
<text x="536" y="97" font-size="11" class="mu" text-anchor="end">{escape(t['exchanger'])}</text>
<g transform="translate(400,222) rotate(45)">
<rect x="-70" y="-70" width="140" height="140" fill="url(#hx)" stroke="#5f6b76" stroke-width="1.5"/>
{''.join(f'<line x1="-70" y1="{y}" x2="70" y2="{y}" stroke="#7fb0e6" stroke-width="1.6"/>' for y in range(-60, 70, 11))}
{''.join(f'<line x1="{x}" y1="-70" x2="{x}" y2="70" stroke="#ec9c7d" stroke-width="1.6" opacity=".85"/>' for x in range(-60, 70, 11))}
</g>
{_fan(512, 140, 22, fan_s)}
{_fan(290, 296, 22, fan_s)}
<rect x="264" y="330" width="60" height="18" rx="4" fill="#cfd3d6" stroke="#7b8794"/>
<text x="294" y="343" font-size="11" fill="#3d464f" text-anchor="middle">{t['filter']}</text>
<g transform="translate(396,300)"><rect width="142" height="50" rx="8" fill="#3d464f"/>
{_fan(24, 25, 14, 0.6 if rpm > 0 else None)}
<text x="44" y="21" font-size="14" fill="#e4e7eb">{t['heat_pump']}</text><text x="44" y="40" font-size="14" fill="#e4e7eb">{int(rpm)} {t['rpm']}</text></g>
{_chips_left(24, 394, bottom, 17)}
"""
    return _svg(UNIT_W, UNIT_H, body, theme)




# ---------------- the hot-water heat pump T300, in section ----------------
TANK_X, TANK_WIDTH, CAP_TOP, BODY_TOP, BODY_BOTTOM = 40, 150, 92, 200, 540


def tank_targets() -> dict[str, tuple[float, float, float, float]]:
    """Tap area of the T300 (percent: centre x, centre y, width, height)."""
    return {"tank": (
        (TANK_X + TANK_WIDTH / 2) / TANK_W * 100, (CAP_TOP + BODY_BOTTOM) / 2 / TANK_H * 100,
        (TANK_WIDTH + 30) / TANK_W * 100, (BODY_BOTTOM - CAP_TOP + 40) / TANK_H * 100,
    )}


# water colour by temperature: cold blue - lukewarm - warm orange - hot red
_WATER = ((15.0, (79, 134, 189)), (28.0, (127, 176, 214)), (36.0, (242, 166, 108)), (45.0, (239, 125, 64)), (55.0, (226, 73, 47)))


def _water_color(temp: float | None) -> str:
    if temp is None:
        return "#c9d6e2"
    rgb: tuple[int, ...] = _WATER[0][1] if temp <= _WATER[0][0] else _WATER[-1][1]
    for (t0, c0), (t1, c1) in zip(_WATER, _WATER[1:]):
        if t0 <= temp <= t1:
            k = (temp - t0) / (t1 - t0)
            rgb = tuple(round(a + (b - a) * k) for a, b in zip(c0, c1))
            break
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _on(data: dict, key: str) -> bool | None:
    """A relay or switch: True / False, None when the unit does not report it."""
    v = data.get(key)
    return bool(v) if isinstance(v, (int, float)) else None


def tank_svg(
    data: dict, lang: str = "de", boost_limit: float | None = None, theme: str = "auto",
    energy_status: str | None = None, boost_status: str | None = None, legionella_heating: bool = False,
) -> str:
    """The T300 in section: the heat pump on top (display, fan turning while the compressor runs), the tank cut open with
    the water coloured by its measured temperatures, the condenser coil, the immersion heater (glowing while it heats), the
    two sensors; target, actual, charge and heater next to it; status chips of the hot-water functions below."""
    t = _t(lang)
    actual = _num(data, "WarmwasserIstTemperatur")
    bottom_t = _num(data, "WarmwasserUntenTemperatur")
    target = _num(data, "SollWassertemperatur")
    heater_on = bool(data.get("E-Heizstab"))  # released
    relay = _on(data, "T300RelaisHeizstab")
    heating = relay if relay is not None else heater_on  # the rod glows while it heats
    pump = _on(data, "T300RelaisKompressor")
    fan_rpm = _num(data, "T300LuefterDrehzahl")
    heater_target = _num(data, "Soll-E-Heizstab-Temperatur")
    charge = _num(data, "WarmwasserLadezustand")
    shower = _num(data, "WarmwasserDuschminuten")
    x, w = TANK_X, TANK_WIDTH
    cap_top, body_top, body_bottom = CAP_TOP, BODY_TOP, BODY_BOTTOM
    # the cut: right half of the tank, insulation (yellow), then the water
    ix, iw = x + w / 2, w / 2 - 8
    iy, ih = body_top + 14, body_bottom - body_top - 26
    mid_c = _water_color(actual)
    low_c = _water_color(bottom_t) if bottom_t is not None else mid_c
    coil = f"M{ix + 8:.0f} {iy + ih * 0.62:.0f}" + "".join(
        f" L{(ix + 8 if k % 2 else ix + iw - 8):.0f} {iy + ih * 0.62 + (ih * 0.34) * k / 8:.0f}" for k in range(1, 9)
    )
    t21_y, rod_y, t20_y = iy + ih * 0.30, iy + ih * 0.50, iy + ih * 0.86
    glow = (
        f'<g class="glow"><ellipse cx="{ix + iw * 0.45:.0f}" cy="{rod_y:.0f}" rx="{iw * 0.75:.0f}" ry="18" fill="url(#heat)"/></g>'
        if heating else ""
    )
    grille = "".join(
        f'<line x1="{x + w * 0.12:.0f}" y1="{cap_top + 18 + i * 8}" x2="{x + w * 0.88:.0f}" y2="{cap_top + 18 + i * 8}" '
        'stroke="#5c656b" stroke-width="1.4" opacity=".5"/>'
        for i in range(6)
    )
    lx = x + w + 36  # the texts on the right
    rows = [
        f'<text x="{lx}" y="112" font-size="13" class="mu">{t["target"]}</text>'
        f'<text x="{lx}" y="138" font-size="22" font-weight="600" class="fg">{_deg(target, 0)}</text>',
        f'<text x="{lx}" y="172" font-size="13" class="mu">{t["actual"]}</text>'
        f'<text x="{lx}" y="208" font-size="34" font-weight="600" class="fg">{_deg(actual)}</text>',
    ]
    if charge is not None:
        bw = TANK_W - lx - 24
        rows.append(
            f'<text x="{lx}" y="236" font-size="13" class="mu">{t["charge"]} {round(charge)} %</text>'
            f'<rect x="{lx}" y="244" width="{bw}" height="10" rx="5" class="chip"/>'
            f'<rect x="{lx}" y="244" width="{max(10.0, bw * max(0.0, min(1.0, charge / 100))):.0f}" height="10" rx="5" fill="#f0884a"/>'
        )
    if shower is not None:
        rows.append(f'<text x="{lx}" y="273" font-size="13" class="fg">{t["shower"].format(m=round(shower))}</text>')

    def pointer(y: float, name: str, value: str) -> str:
        """A line from a point in the tank to its text."""
        return (f'<line x1="{ix + iw + 6:.0f}" y1="{y:.0f}" x2="{lx - 8}" y2="{y:.0f}" class="ln" stroke-dasharray="3 4" opacity=".6"/>'
                f'<text x="{lx}" y="{y - 5:.0f}" font-size="13" class="mu">{name}</text>'
                f'<text x="{lx}" y="{y + 17:.0f}" font-size="18" font-weight="600" class="fg">{value}</text>')

    rows.append(pointer(t21_y, t["middle"], _deg(actual)))
    if bottom_t is not None:
        rows.append(pointer(t20_y, t["bottom"], _deg(bottom_t)))
    rows.append(
        f'<line x1="{ix + iw * 0.72 + 8:.0f}" y1="{rod_y:.0f}" x2="{lx - 8}" y2="{rod_y:.0f}" class="ln" stroke-dasharray="3 4" opacity=".6"/>'
        f'<text x="{lx}" y="{rod_y - 5:.0f}" font-size="15" font-weight="600" class="fg">{t["heater"]} {t["on"] if heater_on else t["off"]}'
        + (f' <tspan fill="#d8602f">· {t["heats"]}</tspan>' if relay else "")
        + f'</text><text x="{lx}" y="{rod_y + 15:.0f}" font-size="13" class="mu">{t["heater_target"]} '
        f'<tspan class="fg" font-weight="600">{_deg(heater_target, 0)}</tspan></text>'
    )
    chips: list[tuple[str, str | None, str | None]] = []
    if legionella_heating:
        chips.append((f"♨ {t['legionella']}", "#fde4d8", "#6e2a10"))
    if energy_status:
        on = energy_status in ("heating_solar", "heating_price")
        name = t["price"] if energy_status == "heating_price" else t["solar"]
        chips.append((f"☀ {name}: {_status(t, energy_status)}", "#fff1c2" if on else None, "#6b4a00" if on else None))
    if boost_status:
        on = boost_status == "heating"
        text = f"♨ {t['boost']}: {_status(t, boost_status)}" + (f" (< {_deg(boost_limit, 0)})" if boost_limit is not None else "")
        chips.append((text, "#fde4d8" if on else None, "#6e2a10" if on else None))
    chip_rows = "".join(_chip(20, 586 + i * 36, text, 14, fill, color) for i, (text, fill, color) in enumerate(chips[:2]))
    sub = "T300" + (f" · {t['heat_pump']} {t['on'] if pump else t['off']}" if pump is not None else "")
    spinning = bool(pump) or bool(fan_rpm)
    body = f"""
<defs>
<linearGradient id="cyl" x1="0" x2="1"><stop offset="0" class="s-shell1"/><stop offset=".42" class="s-shell2"/><stop offset="1" class="s-shell1"/></linearGradient>
<linearGradient id="cap" x1="0" x2="1"><stop offset="0" stop-color="#7d868c"/><stop offset=".3" stop-color="#c3c9cd"/>
<stop offset=".46" stop-color="#d9dde0"/><stop offset=".8" stop-color="#a3abb0"/><stop offset="1" stop-color="#737c82"/></linearGradient>
<linearGradient id="duct" x1="0" x2="1"><stop offset="0" stop-color="#8b9399"/><stop offset=".5" stop-color="#d7dbde"/><stop offset="1" stop-color="#868e94"/></linearGradient>
<linearGradient id="water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{mid_c}"/><stop offset=".5" stop-color="{mid_c}"/><stop offset="1" stop-color="{low_c}"/></linearGradient>
<radialGradient id="heat"><stop offset="0" stop-color="#ffb347" stop-opacity=".95"/><stop offset="1" stop-color="#ff6a2a" stop-opacity="0"/></radialGradient>
</defs>
<text x="20" y="38" font-size="24" font-weight="600" class="fg">{escape(t['tank'])}</text>
<text x="20" y="60" font-size="14" class="mu">{escape(sub)}</text>
<ellipse cx="{x + w / 2:.0f}" cy="{body_bottom + 24}" rx="{w * 0.62:.0f}" ry="9" fill="#000" opacity=".16"/>
<rect x="{x + w * 0.16:.0f}" y="{cap_top - 20}" width="{w * 0.22:.0f}" height="24" fill="url(#duct)"/>
<rect x="{x + w * 0.6:.0f}" y="{cap_top - 20}" width="{w * 0.22:.0f}" height="24" fill="url(#duct)"/>
<path d="M{x} {body_top} V{cap_top + 18} Q{x} {cap_top} {x + 18} {cap_top} H{x + w - 18} Q{x + w} {cap_top} {x + w} {cap_top + 18} V{body_top} Z" fill="url(#cap)"/>
{grille}
<rect x="{x + w * 0.24:.0f}" y="{cap_top + 70}" width="{w * 0.52:.0f}" height="26" rx="4" fill="#0b161b"/>
<text x="{x + w / 2:.0f}" y="{cap_top + 89}" font-size="15" font-weight="600" fill="#7fe0d8" text-anchor="middle">{_deg(actual, 0)}</text>
{_fan(x + w - 26, cap_top + 46, 13, 0.7 if spinning else None)}
<rect x="{x}" y="{body_top}" width="{w}" height="{body_bottom - body_top}" fill="url(#cyl)"/>
<rect x="{x}" y="{body_top - 2}" width="{w}" height="4" fill="#8d959b"/>
<rect x="{x}" y="{body_bottom}" width="{w}" height="12" rx="3" fill="#59626a"/>
<rect x="{ix:.0f}" y="{iy:.0f}" width="{iw + 4:.0f}" height="{ih:.0f}" fill="#e8c55a"/>
<rect x="{ix + 4:.0f}" y="{iy + 4:.0f}" width="{iw - 4:.0f}" height="{ih - 8:.0f}" fill="url(#water)"/>
<path d="{coil}" fill="none" stroke="#c6d3dc" stroke-width="2.4" opacity=".85"/>
{glow}
<rect x="{ix + 4:.0f}" y="{rod_y - 3:.0f}" width="{iw * 0.72:.0f}" height="6" rx="3" fill="{'#ffcf7a' if heating else '#9aa4ab'}"/>
<line x1="{ix:.0f}" y1="{iy:.0f}" x2="{ix:.0f}" y2="{iy + ih:.0f}" stroke="#7d868c" stroke-width="1.4"/>
<circle cx="{ix + iw:.0f}" cy="{t21_y:.0f}" r="4.5" fill="#ffffff" stroke="#1f2933" stroke-width="1.5"/>
{'' if bottom_t is None else f'<circle cx="{ix + iw:.0f}" cy="{t20_y:.0f}" r="4.5" fill="#ffffff" stroke="#1f2933" stroke-width="1.5"/>'}
{''.join(rows)}
{chip_rows}
"""
    return _svg(TANK_W, TANK_H, body, theme)


# ---------------- the house: isometric, ground floor in front, upper floor behind ----------------
@dataclass
class Room:
    name: str
    actual: float | None
    target: float | None
    heating: bool  # the room's heating element heats
    floor: int = 0  # 0 ground floor, 1 upper floor


FOOT_W, FOOT_D = 10.0, 8.0  # footprint of a floor (units)
UPPER_SHIFT, UPPER_LIFT = -(FOOT_D + 1.8), 1.4  # the upper floor stands behind the ground floor, a little higher
WALL_H, SLAB, RISER = 1.1, 0.45, 2.7
SCALES = (36.0, 44.0, 52.0, 60.0)  # pixels per unit: larger only when many rooms need more room for their labels
_COS30 = 0.8660254
HEADER_H, LEGEND_H = 64, 70
# room labels, richest first: style, width, height, size of the temperature
LABELS = (("full", 160.0, 54.0, 20), ("compact", 116.0, 44.0, 18), ("mini", 86.0, 34.0, 14))
# room names that usually lie upstairs (the house picture's default until the floors are chosen in the options)
_UPPER = re.compile(r"schlaf|kind|eltern|ankleide|ober|dach|oben|\bog\b|\bdg\b|bed|kid|child|nursery|upstairs|upper|attic|loft", re.I)


def guess_floor(name: str) -> int:
    """1 for rooms that usually lie upstairs (bedrooms, children's rooms, "… oben"), else 0."""
    return 1 if _UPPER.search(name or "") else 0


@dataclass
class HouseLayout:
    width: int
    height: int
    origin: tuple[float, float]
    cells: list[tuple[int, tuple[float, float, float, float]]]  # per room: floor, (x0, y0, x1, y1)
    technik: tuple[float, float, float, float]  # cell of the utility room (ground floor)
    unit: tuple[float, float, float, float]  # the ventilation unit's box on the floor: x, y, width, depth
    labels: list[tuple[float, float, float, float]]  # per room: label box x, y, w, h (pixels)
    style: str  # label style
    floors: tuple[int, ...]  # floors drawn
    scale: float  # pixels per unit

    def iso(self, x: float, y: float, z: float, floor: int = 0) -> tuple[float, float]:
        """Picture position of a point of a floor (x, y on the floor, z up)."""
        return _iso(x, y, z, floor, self.origin, self.scale)


def _iso(x: float, y: float, z: float, floor: int, origin: tuple[float, float], scale: float) -> tuple[float, float]:
    if floor:
        y, z = y + UPPER_SHIFT, z + UPPER_LIFT
    return origin[0] + (x - y) * _COS30 * scale, origin[1] + (x + y) * 0.5 * scale - z * scale


def _grid(n: int, rows: int) -> list[tuple[float, float, float, float]]:
    """n cells in `rows` rows on the footprint; the back rows take the extra cells."""
    base, extra = divmod(n, rows)
    out = []
    for r in range(rows):
        k = base + (1 if r < extra else 0)
        y0, y1 = FOOT_D * r / rows, FOOT_D * (r + 1) / rows
        out += [(FOOT_W * c / k, y0, FOOT_W * (c + 1) / k, y1) for c in range(k)]
    return out


def _squareness(cells: list[tuple[float, float, float, float]]) -> float:
    return sum(abs(math.log((x1 - x0) / (y1 - y0))) for x0, y0, x1, y1 in cells) / max(1, len(cells))


def _overlap(a: tuple[float, float, float, float], b: tuple[float, float, float, float], gap: float = 3.0) -> bool:
    return a[0] < b[0] + b[2] + gap and b[0] < a[0] + a[2] + gap and a[1] < b[1] + b[3] + gap and b[1] < a[1] + a[3] + gap


def _boxes(centres: list[tuple[float, float]], w: float, h: float) -> list[tuple[float, float, float, float]]:
    return [(x - w / 2, y - h / 2, w, h) for x, y in centres]


def _text_w(text: str, size: float) -> float:
    return len(text) * size * 0.56


def _fit(text: str, size: float, width: float) -> str:
    """The text, shortened with … to fit the width."""
    n = int(width / (size * 0.56))
    return text if len(text) <= n else text[: max(1, n - 1)].rstrip() + "…"


def house_layout(floors: list[int]) -> HouseLayout:
    """Where everything lies: the rooms of each floor on a grid (the utility room with the unit takes the front left cell
    of the ground floor), the room labels (as rich as the room sizes allow without overlapping; also the tap areas), and the
    picture size. Only the number of rooms per floor counts, so the dashboard gets the same boxes as the picture."""
    ground = [i for i, f in enumerate(floors) if not f]
    upper = [i for i, f in enumerate(floors) if f]
    drawn = (0, 1) if upper else (0,)
    # every way to put the rooms on the floors: rows on the ground floor (plus the utility room) x rows upstairs
    grids = []
    for r0 in range(1, len(ground) + 2):
        g0 = _grid(len(ground) + 1, r0)
        front = max(c[1] for c in g0)
        tech = next(c for c in g0 if c[1] == front)
        rest = [c for c in g0 if c is not tech]
        for r1 in range(1, len(upper) + 1) if upper else (1,):
            g1 = _grid(len(upper), r1) if upper else []
            grids.append((dict(zip(ground, rest)) | dict(zip(upper, g1)), tech, _squareness(g0) + _squareness(g1)))

    def label_boxes(cells: dict, scale: float, w: float, h: float) -> list[tuple[float, float, float, float]]:
        centres = [_iso((cells[i][0] + cells[i][2]) / 2, (cells[i][1] + cells[i][3]) / 2, 0.05, floors[i], (0.0, 0.0), scale)
                   for i in range(len(floors))]
        return _boxes(centres, w, h)

    # the most legible picture (the largest temperature for the picture's size) where no label covers another;
    # among those grids the one with the squarest rooms
    best: tuple | None = None
    for scale, rank in sorted(((sc, r) for sc in SCALES for r in range(len(LABELS))), key=lambda c: -LABELS[c[1]][3] / c[0]):
        _style, w, h, _size = LABELS[rank]
        for cells, tech, square in grids:
            boxes = label_boxes(cells, scale, w, h)
            if not any(_overlap(a, b) for k, a in enumerate(boxes) for b in boxes[k + 1:]) and (best is None or square < best[0]):
                best = (square, scale, rank, cells, tech)
        if best is not None:
            break
    if best is None:  # more rooms than fit: the largest picture, the smallest labels
        cells, tech, square = min(grids, key=lambda g: g[2])
        best = (square, SCALES[-1], len(LABELS) - 1, cells, tech)
    _square, scale, rank, cells, tech = best
    style, lw, lh, _size = LABELS[rank]
    x0, y0, x1, y1 = tech
    side = min(1.8, 0.5 * min(x1 - x0, y1 - y0))
    unit = (x0 + (x1 - x0) * 0.12, y0 + (y1 - y0) * 0.2, side, side)
    # extents: floors, labels, the unit's name tag
    pts = [_iso(x, y, z, f, (0.0, 0.0), scale) for f in drawn for x in (0, FOOT_W) for y in (0, FOOT_D) for z in (WALL_H, -SLAB)]
    boxes = label_boxes(cells, scale, lw, lh)
    pts += [(x, y) for x, y, w, h in boxes] + [(x + w, y + h) for x, y, w, h in boxes]
    tx, ty = _iso(unit[0], unit[1] + unit[3], 1.7, 0, (0.0, 0.0), scale)
    pts += [(tx - 6 - 130, ty - 34)]  # the unit's name tag
    min_x, max_x = min(p[0] for p in pts), max(p[0] for p in pts)
    min_y, max_y = min(p[1] for p in pts), max(p[1] for p in pts)
    top = HEADER_H + 20
    origin = (24 - min_x, top - min_y)
    return HouseLayout(
        width=int(max_x - min_x + 48), height=int(max_y - min_y + top + 24 + LEGEND_H), origin=origin,
        cells=[(floors[i], cells[i]) for i in range(len(floors))], technik=tech, unit=unit,
        labels=[(x + origin[0], y + origin[1], w, h) for x, y, w, h in boxes], style=style, floors=drawn, scale=scale,
    )


def house_targets(floors: list[int]) -> list[tuple[float, float, float, float]]:
    """Tap areas of the rooms' labels, in percent of the picture: centre x, centre y, width, height."""
    lay = house_layout(floors)
    return [((x + w / 2) / lay.width * 100, (y + h / 2) / lay.height * 100, w / lay.width * 100, h / lay.height * 100)
            for x, y, w, h in lay.labels]


def _room_state(r: Room) -> tuple[str, str]:
    """(floor colour class, dot colour) by how the room is doing against its target."""
    if r.actual is None or r.target is None:
        return "r-none", "#9aa3ab"
    diff = r.actual - r.target
    if diff < -1:
        return "r-cold", "#3b82d6"  # too cold
    if diff > 1:
        return "r-warm", "#d8602f"  # too warm
    return "r-fine", "#1f9d6c"  # fine


def _flame(x: float, y: float, size: float = 1.0) -> str:
    # positioned by an outer group: the flicker animation's transform replaces a transform on its own element
    return (f'<g transform="translate({x:.0f},{y:.0f}) scale({size})"><g class="flame">'
            '<path d="M14 0 C20 12 28 16 26 28 C24 37 4 37 2 28 C0 19 8 14 14 0 Z" fill="#ff6a2b"/>'
            '<path d="M14 13 C16 19 21 22 19 28 C18 32 10 32 9 28 C8 23 13 20 14 13 Z" fill="#ffd166"/></g></g>')


def _label(r: Room, box: tuple[float, float, float, float], style: str, t: dict) -> str:
    x, y, w, h = box
    dot = _room_state(r)[1]
    name_size, temp_size = {"full": (12.5, 20), "compact": (12, 18), "mini": (10.5, 14)}[style]
    pad = 9 if style == "mini" else 11
    flame = 0.5 if style == "mini" else 0.6
    name = _fit(r.name, name_size, w - pad - 12 - 8)
    target = (f'<tspan dx="6" font-size="11" font-weight="400" class="mu">{t["target"]} {_deg(r.target)}</tspan>'
              if style == "full" else "")
    return (
        f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="{10 if style == "mini" else 12}" class="lbl" stroke-width="1"/>'
        f'<circle cx="{x + pad + 2:.0f}" cy="{y + name_size + 1:.0f}" r="{3.5 if style == "mini" else 4}" fill="{dot}"/>'
        f'<text x="{x + pad + 10:.0f}" y="{y + name_size + 5:.0f}" font-size="{name_size}" font-weight="600" class="mu">{escape(name)}</text>'
        f'<text x="{x + pad:.0f}" y="{y + h - (6 if style == "mini" else 10):.0f}" font-size="{temp_size}" font-weight="600" class="fg">'
        f'{_deg(r.actual)}{target}</text>'
        + (_flame(x + w - 8 - 28 * flame, y + h - 6 - 37 * flame, flame) if r.heating else "")
    )


def house_svg(rooms: list[Room], outside: float | None, lang: str = "de", theme: str = "auto", running: bool = True) -> str:
    """The house as an isometric picture: ground floor in front, upper floor behind it; every room coloured by actual vs
    target, with its temperature and a flame while its heating element heats; in the utility room the ventilation unit and
    the T300, from there the supply air ducts into the rooms and the extract duct back (moving while the ventilation runs)."""
    t = _t(lang)
    lay = house_layout([r.floor for r in rooms])

    def pts(corners: list[tuple[float, float, float]], f: int) -> str:
        return " ".join(f"{a:.1f},{b:.1f}" for a, b in (lay.iso(x, y, z, f) for x, y, z in corners))

    def poly(corners: list[tuple[float, float, float]], f: int, attrs: str) -> str:
        return f'<polygon points="{pts(corners, f)}" {attrs}/>'

    def duct(path: list[tuple[float, float, float]], f: int, supply: bool = True) -> str:
        p = pts(path, f)
        color, light = ("#f08a4b", "#ffe1c9") if supply else ("#7fb0d6", "#e3f1fb")
        anim = (' class="flow"' + ("" if supply else ' style="animation-direction:reverse"')) if running else ""
        return (f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<polyline points="{p}" fill="none" stroke="{light}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"{anim}/>')

    def floor_base(f: int) -> str:
        W, D = FOOT_W, FOOT_D
        out = poly([(W, 0, 0), (W, D, 0), (W, D, -SLAB), (W, 0, -SLAB)], f, 'class="slab1"')
        out += poly([(0, D, 0), (W, D, 0), (W, D, -SLAB), (0, D, -SLAB)], f, 'class="slab2"')
        out += poly([(0, 0, WALL_H), (W, 0, WALL_H), (W, 0, 0), (0, 0, 0)], f, 'class="wallA" stroke-width="1"')
        out += poly([(0, 0, WALL_H), (0, D, WALL_H), (0, D, 0), (0, 0, 0)], f, 'class="wallB" stroke-width="1"')
        if len(lay.floors) > 1:  # the floor's name at the top left of its drawing
            lx, _ly = lay.iso(0, D, 0, f)
            _tx, ty = lay.iso(0, 0, WALL_H, f)
            out += f'<text x="{lx:.0f}" y="{ty + 4:.0f}" font-size="15" font-weight="600" class="mu">{t["upper" if f else "ground"]}</text>'
        return out

    def cell_poly(cell: tuple[float, float, float, float], f: int, cls: str) -> str:
        x0, y0, x1, y1 = cell
        return poly([(x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0)], f, f'class="{cls} sep" stroke-width="3"')

    def centre(i: int) -> tuple[float, float]:
        x0, y0, x1, y1 = lay.cells[i][1]
        return (x0 + x1) / 2, (y0 + y1) / 2

    ground = [i for i, (f, _c) in enumerate(lay.cells) if not f]
    upper = [i for i, (f, _c) in enumerate(lay.cells) if f]
    tech = lay.technik
    bx, by, bw, bd = lay.unit
    bh = 1.7
    ux, uy = bx + bw / 2, by + bd / 2
    body: list[str] = []
    if upper:  # upper floor first: it stands behind
        land = FOOT_D - 0.5  # where the riser arrives on the upper floor
        body.append(floor_base(1))
        body += [cell_poly(lay.cells[i][1], 1, _room_state(rooms[i])[0]) for i in upper]
        for i in upper:
            cx, cy = centre(i)
            body.append(duct([(ux, land, 0.05), (ux, cy, 0.05), (cx, cy, 0.05)], 1))
        # the riser: up from the unit, over the walls to the upper floor (in ground floor units)
        body.append(duct([(ux, uy, RISER), (ux, land + UPPER_SHIFT, RISER), (ux, land + UPPER_SHIFT, UPPER_LIFT + 0.05)], 0))
    body.append(floor_base(0))
    body += [cell_poly(lay.cells[i][1], 0, _room_state(rooms[i])[0]) for i in ground]
    body.append(cell_poly(tech, 0, "tech"))
    if ground:  # extract air: from the front room furthest away back to the unit
        fx, fy = centre(max(ground, key=lambda i: (centre(i)[1], centre(i)[0])))
        body.append(duct([(fx, fy, 0.55), (fx, uy + bd * 0.3, 0.55), (bx + bw, uy + bd * 0.3, 0.55)], 0, supply=False))
    # the ventilation unit (a box), the supply ducts, the T300 beside it
    body.append(poly([(bx, by, bh), (bx + bw, by, bh), (bx + bw, by + bd, bh), (bx, by + bd, bh)], 0, 'fill="#f4f6f7" stroke="#9aa3a8"'))
    body.append(poly([(bx + bw, by, bh), (bx + bw, by + bd, bh), (bx + bw, by + bd, 0), (bx + bw, by, 0)], 0, 'fill="#cfd5d8" stroke="#9aa3a8"'))
    body.append(poly([(bx, by + bd, bh), (bx + bw, by + bd, bh), (bx + bw, by + bd, 0), (bx, by + bd, 0)], 0, 'fill="#e3e7e9" stroke="#9aa3a8"'))
    for i in ground:
        cx, cy = centre(i)
        body.append(duct([(ux, uy, bh), (ux, uy, 0.95), (ux, cy, 0.95), (cx, cy, 0.95)], 0))
    if upper:
        body.append(duct([(ux, uy, bh), (ux, uy, RISER)], 0))
    x0, y0, x1, y1 = tech
    tx, ty = lay.iso(x0 + (x1 - x0) * 0.8, y0 + (y1 - y0) * 0.78, 0)
    tw, th = lay.scale * min(0.95, 0.3 * (x1 - x0)), lay.scale * min(2.2, 0.7 * (y1 - y0))
    body.append(
        f'<g transform="translate({tx - tw / 2:.0f},{ty - th:.0f})">'
        f'<rect x="0" y="{th * 0.2:.0f}" width="{tw:.0f}" height="{th * 0.8:.0f}" rx="3" fill="#eef1f3" stroke="#9aa3a8"/>'
        f'<rect x="0" y="0" width="{tw:.0f}" height="{th * 0.24:.0f}" rx="4" fill="#a8b0b5" stroke="#8d959b"/>'
        f'<rect x="{tw * 0.24:.0f}" y="{th * 0.08:.0f}" width="{tw * 0.52:.0f}" height="{th * 0.08:.0f}" rx="1" fill="#0b161b"/></g>'
    )
    px, py = lay.iso(bx, by + bd, bh)
    tag = t["vent_unit"]
    pw = _text_w(tag, 11.5) + 20
    body.append(f'<rect x="{px - pw - 6:.0f}" y="{py - 34:.0f}" width="{pw:.0f}" height="22" rx="11" class="tag"/>'
                f'<text x="{px - pw / 2 - 6:.0f}" y="{py - 19:.0f}" font-size="11.5" class="tagtext" text-anchor="middle">{escape(tag)}</text>')
    nx, ny = lay.iso(x0 + 0.2, y1 - 0.1, 0)
    body.append(f'<text x="{nx:.0f}" y="{ny + 4:.0f}" font-size="12" class="mu">{t["technik"]}</text>')
    body += [_label(rooms[i], box, lay.style, t) for i, box in enumerate(lay.labels)]
    legend, lx = [], 24.0  # the room colours, as the floors show them (light / dark)
    for text, cls in ((t["cold"], "r-cold"), (t["fine"], "r-fine"), (t["warm"], "r-warm")):
        w = _chip_w(text, 14)
        legend.append(f'<rect x="{lx:.0f}" y="{lay.height - 50}" width="{w:.0f}" height="28" rx="14" class="{cls}"/>'
                      f'<text x="{lx + 13:.0f}" y="{lay.height - 31}" font-size="14" class="fg">{escape(text)}</text>')
        lx += w + 8
    right = lay.width - 24
    ducts = (
        f'<line x1="{right - 236}" y1="{lay.height - 58}" x2="{right - 214}" y2="{lay.height - 58}" stroke="#f08a4b" stroke-width="5" stroke-linecap="round"/>'
        f'<text x="{right - 206}" y="{lay.height - 53}" font-size="13" class="mu">{t["supply_short"]}</text>'
        f'<line x1="{right - 118}" y1="{lay.height - 58}" x2="{right - 96}" y2="{lay.height - 58}" stroke="#7fb0d6" stroke-width="5" stroke-linecap="round"/>'
        f'<text x="{right - 88}" y="{lay.height - 53}" font-size="13" class="mu">{t["extract_short"]}</text>'
    )
    hint = f'<text x="{right}" y="{lay.height - 22}" font-size="14" class="mu" text-anchor="end">{escape(t["tap"])} ›</text>'
    known = [r.actual for r in rooms if r.actual is not None]
    chips = [f"{t['outside']} {_deg(outside)}"] + ([f"{t['inside']} {_deg(sum(known) / len(known))}"] if known else [])
    header = (f'<text x="24" y="40" font-size="28" font-weight="600" class="fg">{escape(t["house"])}</text>'
              + _chips_right(lay.width - 20, 14, chips, 16))
    return _svg(lay.width, lay.height, header + "".join(body) + "".join(legend) + ducts + hint, theme)


# ---------------- the floor plan from above (start page on tablet / desktop) ----------------
PLAN_M = 47.0  # units per metre
PLAN_W_M, PLAN_H_M = 13.0, 10.0  # the plan in metres (wider than deep: fits a tablet screen)
PLAN_PAD = 14.0
PLAN_W = int(PLAN_W_M * PLAN_M + 2 * PLAN_PAD)
PLAN_H = int(PLAN_H_M * PLAN_M + 2 * PLAN_PAD)
# what a room is by its name: kind, share of the plan, floor covering (first match counts)
_KINDS = (
    ("wc", re.compile(r"\bwc\b|toilette|\bklo", re.I), 0.5, "tile"),
    ("bath", re.compile(r"bad|dusche|bath|shower", re.I), 0.85, "tile"),
    ("kitchen", re.compile(r"küche|kueche|kitchen|\bkoch", re.I), 1.2, "tile"),
    ("living", re.compile(r"wohn|living|lounge|stube", re.I), 2.2, "wood"),
    ("dining", re.compile(r"\bess|dining", re.I), 1.1, "wood"),
    ("bedroom", re.compile(r"schlaf|eltern|bedroom|master", re.I), 1.35, "wood"),
    ("child", re.compile(r"kind|\bkid|child|jugend|nursery|baby", re.I), 1.1, "wood"),
    ("guest", re.compile(r"gäste|gaeste|\bgast|guest", re.I), 1.0, "wood"),
    ("office", re.compile(r"büro|buero|arbeit|office|study|studio", re.I), 1.0, "wood"),
    ("hall", re.compile(r"diele|flur|eingang|gang|hall|corridor|entrance|treppe|stair|windfang", re.I), 0.8, "stone"),
    ("utility", re.compile(r"technik|hwr|hauswirt|keller|utility|laundry|wasch|abstell|speis", re.I), 0.7, "stone"),
)
PLAN_LABELS = (("full", 150.0, 58.0), ("compact", 104.0, 46.0), ("mini", 84.0, 36.0))


def room_kind(name: str) -> tuple[str, float, str]:
    """What a room probably is, by its name: kind, its share of the plan, floor covering."""
    for kind, pattern, weight, floor in _KINDS:
        if pattern.search(name or ""):
            return kind, weight, floor
    return "room", 1.0, "wood"


def _squarify(weights: list[float], x: float, y: float, w: float, h: float) -> list[tuple[float, float, float, float]]:
    """Rectangles with the weights' share of the area, as square as possible (squarified treemap), in the given order."""
    total = sum(weights) or 1.0
    areas = [wt * w * h / total for wt in weights]
    out: list[tuple[float, float, float, float]] = []

    def worst(row: list[float], side: float) -> float:
        s = sum(row)
        return max(max(side * side * a / (s * s), s * s / (side * side * a)) for a in row)

    def place(row: list[float], x: float, y: float, w: float, h: float) -> tuple[float, float, float, float]:
        s = sum(row)
        if w >= h:  # a column at the left
            cw, yy = s / h, y
            for a in row:
                out.append((x, yy, cw, a / cw))
                yy += a / cw
            return x + cw, y, w - cw, h
        rh, xx = s / w, x  # a row at the top
        for a in row:
            out.append((xx, y, a / rh, rh))
            xx += a / rh
        return x, y + rh, w, h - rh

    row: list[float] = []
    i = 0
    while i < len(areas):
        side = min(w, h)
        if not row or worst(row + [areas[i]], side) <= worst(row, side):
            row.append(areas[i])
            i += 1
        else:
            x, y, w, h = place(row, x, y, w, h)
            row = []
    if row:
        place(row, x, y, w, h)
    return out


@dataclass
class PlanLayout:
    width: int
    height: int
    rooms: list[tuple[float, float, float, float]]  # per room: x, y, w, h (to the middle of the walls)
    kinds: list[tuple[str, float, str]]
    labels: list[tuple[float, float, float, float]]
    styles: list[str]
    bands: list[tuple[int, float, float]]  # floor, top, bottom


def plan_layout(names: list[str], floors: list[int]) -> PlanLayout:
    """The rooms on a schematic plan: one band per floor (ground floor at the top), in each band the rooms as squarified
    rectangles sized by their kind (the living room large, a WC small); every room's label as large as its room allows.
    Only names and floors count, so the dashboard gets the same tap areas as the picture."""
    kinds = [room_kind(n) for n in names]
    x0, y0, w, h = PLAN_PAD, PLAN_PAD, PLAN_W_M * PLAN_M, PLAN_H_M * PLAN_M
    drawn = sorted(set(floors)) or [0]
    if len(drawn) > 1:
        weight = {f: sum(k[1] for k, fl in zip(kinds, floors) if fl == f) for f in drawn}
        share = min(0.67, max(0.33, weight[0] / (weight[0] + weight[1])))
        bands = [(0, y0, y0 + h * share), (1, y0 + h * share, y0 + h)]
    else:
        bands = [(drawn[0], y0, y0 + h)]
    rooms: list[tuple[float, float, float, float]] = [(x0, y0, w, h)] * len(names)
    for floor, top, bottom in bands:
        order = sorted((i for i, f in enumerate(floors) if f == floor), key=lambda i: -kinds[i][1])
        for i, rect in zip(order, _squarify([kinds[i][1] for i in order], x0, top, w, bottom - top)):
            rooms[i] = rect
    labels, styles = [], []
    for rx, ry, rw, rh in rooms:
        style, lw, lh = next(((st, a, b) for st, a, b in PLAN_LABELS if a <= rw - 18 and b <= rh - 18), PLAN_LABELS[-1])
        labels.append((rx + rw / 2 - lw / 2, ry + rh / 2 - lh / 2, lw, lh))
        styles.append(style)
    return PlanLayout(PLAN_W, PLAN_H, rooms, kinds, labels, styles, bands)


def plan_targets(names: list[str], floors: list[int]) -> list[tuple[float, float, float, float]]:
    """Tap areas: every room's floor, in percent of the picture (centre x, centre y, width, height)."""
    lay = plan_layout(names, floors)
    return [((x + w / 2) / lay.width * 100, (y + h / 2) / lay.height * 100, (w - 8) / lay.width * 100, (h - 8) / lay.height * 100)
            for x, y, w, h in lay.rooms]


_PLAN_DEFS = (
    '<pattern id="wood" width="84" height="14" patternUnits="userSpaceOnUse"><rect width="84" height="14" fill="#a0703f"/>'
    '<rect width="42" height="7" fill="#a87849"/><rect x="42" y="7" width="42" height="7" fill="#9a6a3a"/>'
    '<rect y="6.5" width="84" height=".8" fill="#7a5129"/><rect y="13.5" width="84" height=".8" fill="#7a5129"/>'
    '<rect x="42" width=".8" height="7" fill="#7a5129"/><rect x="18" y="7" width=".8" height="7" fill="#7a5129"/></pattern>'
    '<pattern id="tile" width="20" height="20" patternUnits="userSpaceOnUse"><rect width="20" height="20" fill="#cfd5d6"/>'
    '<path d="M20 0H0V20" fill="none" stroke="#aab2b4" stroke-width="1"/></pattern>'
    '<pattern id="stone" width="34" height="34" patternUnits="userSpaceOnUse"><rect width="34" height="34" fill="#b9ad9b"/>'
    '<path d="M34 0H0V34" fill="none" stroke="#9c907e" stroke-width="1.2"/></pattern>'
    '<filter id="sh" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="2" dy="3" stdDeviation="2.2" '
    'flood-color="#000" flood-opacity=".42"/></filter>'
    '<radialGradient id="light" cx=".45" cy=".4" r=".75"><stop offset="0" stop-color="#fff" stop-opacity=".14"/>'
    '<stop offset=".7" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".34"/></radialGradient>'
)
_BLANKETS = {"bedroom": "#8aa0b8", "child": "#c7845a", "guest": "#6f9a76"}


def _furniture(kind: str, name: str, x: float, y: float, w: float, h: float) -> str:
    """Schematic furniture by the kind of room, placed against the walls; pieces that don't fit are left out."""
    m = PLAN_M
    W, H = w / m, h / m  # room size in metres
    out: list[str] = []

    def box(px: float, py: float, pw: float, ph: float, fill: str, rx: float = 3, shadow: bool = True) -> None:
        if px < 0.1 or py < 0.1 or px + pw > W - 0.1 or py + ph > H - 0.1 or pw <= 0 or ph <= 0:
            return
        out.append(f'<rect x="{x + px * m:.1f}" y="{y + py * m:.1f}" width="{pw * m:.1f}" height="{ph * m:.1f}" rx="{rx}" '
                   f'fill="{fill}"' + (' filter="url(#sh)"' if shadow else "") + "/>")

    def disc(cx: float, cy: float, r: float, fill: str, shadow: bool = True) -> None:
        if cx - r < 0.1 or cy - r < 0.1 or cx + r > W - 0.1 or cy + r > H - 0.1:
            return
        out.append(f'<circle cx="{x + cx * m:.1f}" cy="{y + cy * m:.1f}" r="{r * m:.1f}" fill="{fill}"'
                   + (' filter="url(#sh)"' if shadow else "") + "/>")

    def table(cx: float, cy: float, tw: float, th: float) -> None:
        if cx - tw / 2 - 0.55 < 0.1 or cy - th / 2 - 0.55 < 0.1 or cx + tw / 2 + 0.55 > W - 0.1 or cy + th / 2 + 0.55 > H - 0.1:
            return
        box(cx - tw / 2, cy - th / 2, tw, th, "#c49a63", 4)
        for k in range(3 if tw > 1.4 else 2):
            px = cx - tw / 2 + tw * (k + 0.5) / (3 if tw > 1.4 else 2)
            disc(px, cy - th / 2 - 0.3, 0.22, "#3d4148")
            disc(px, cy + th / 2 + 0.3, 0.22, "#3d4148")

    def bed(px: float, py: float, bw: float, blanket: str) -> None:
        if px + bw > W - 0.1 or py + 2.0 > H - 0.1 or px < 0.1:
            return
        box(px, py, bw, 2.0, "#eef0f2", 4)
        pillows = 2 if bw >= 1.3 else 1
        for k in range(pillows):
            box(px + 0.1 + k * (bw - 0.2) / pillows, py + 0.1, (bw - 0.2) / pillows - 0.08, 0.36, "#ffffff", 3, False)
        box(px, py + 0.62, bw, 1.38, blanket, 4, False)

    if kind == "living":
        sofa = min(2.8, W - 1.4)
        if sofa >= 1.6:
            out.append(f'<ellipse cx="{x + 1.9 * m:.1f}" cy="{y + 1.75 * m:.1f}" rx="{1.3 * m:.1f}" ry="{0.9 * m:.1f}" '
                       'fill="#d9cfc0" opacity=".85"/>' if W >= 3.4 and H >= 2.9 else "")
            box(0.3, 0.3, sofa, 0.9, "#4a4f57", 6)
            box(0.3, 1.2, 0.9, min(1.8, H - 1.7), "#4a4f57", 6)
            box(0.45, 0.42, sofa - 0.3, 0.42, "#5b616a", 4, False)
            box(1.6, 1.5, 1.0, 0.6, "#e9e3d8", 3)
        box(W - 0.65, 0.5, 0.35, min(1.8, H - 1.0), "#2e3137", 2)
        if W >= 4.6 and H >= 4.4:
            table(W - 2.0, H - 1.45, 1.8, 0.9)
    elif kind == "kitchen":
        box(0.15, 0.15, W - 0.3, 0.62, "#e7e9ea", 2)
        box(W - 0.77, 0.77, 0.62, min(2.4, H - 1.1), "#e7e9ea", 2)
        disc(0.75, 0.46, 0.15, "#9aa4ab", False)
        disc(1.15, 0.46, 0.15, "#9aa4ab", False)
        box(W - 1.9, 0.24, 0.7, 0.44, "#c9d0d4", 3, False)
        if H >= 3.2 and W >= 2.6:
            table(W / 2 - 0.3, H - 1.3, 1.4, 0.8)
    elif kind == "dining":
        table(W / 2, H / 2, min(2.0, W - 1.6), min(1.0, H - 1.6))
    elif kind in ("bath", "wc"):
        if kind == "bath":
            if H >= 2.2:
                box(0.2, 0.2, 0.8, min(1.7, H - 0.4), "#f4f6f7", 8)
            else:
                box(0.2, 0.2, 0.9, 0.9, "#f4f6f7", 4)
        box(W - 0.65, 0.2, 0.45, 0.55, "#f4f6f7", 6)
        disc(W - 0.5, H - 0.5, 0.28, "#f4f6f7")
    elif kind in ("bedroom", "child", "guest"):
        width = 1.6 if kind == "bedroom" else 1.4 if kind == "guest" else 0.9
        width = min(width, W - 0.9)
        if kind == "bedroom":
            bx = (W - width) / 2
            bed(bx, 0.2, width, _BLANKETS[kind])
            box(bx - 0.5, 0.25, 0.4, 0.4, "#d8c3a2", 2)
            box(bx + width + 0.1, 0.25, 0.4, 0.4, "#d8c3a2", 2)
            if H >= 3.4:
                box(0.15, H - 0.75, min(2.4, W - 0.3), 0.6, "#5a4636", 2)
        else:
            bed(0.2, 0.2, width, _BLANKETS[kind])
            if kind == "child":
                box(W - 1.4, H - 0.75, 1.2, 0.6, "#d8c3a2", 2)
                disc(W - 0.8, H - 1.05, 0.22, "#3d4148")
            else:
                disc(W - 0.7, H - 0.7, 0.3, "#5b616a")
    elif kind == "office":
        box(W / 2 - 0.8, 0.2, 1.6, 0.7, "#d8c3a2", 2)
        disc(W / 2, 1.25, 0.24, "#3d4148")
        box(0.15, H - 0.5, min(2.0, W - 0.3), 0.35, "#5a4636", 2)
    elif kind == "hall":
        box(0.15, 0.3, 0.45, min(1.8, H - 0.6), "#5a4636", 2)
        if re.search(r"treppe|stair", name, re.I) and W >= 1.6 and H >= 2.4:
            sx, sw = W - 1.1, 0.9
            box(sx, 0.3, sw, H - 0.6, "#d8d2c6", 2)
            steps = int((H - 0.6) / 0.28)
            for k in range(1, steps):
                out.append(f'<line x1="{x + sx * m:.1f}" y1="{y + (0.3 + k * 0.28) * m:.1f}" x2="{x + (sx + sw) * m:.1f}" '
                           f'y2="{y + (0.3 + k * 0.28) * m:.1f}" stroke="#a69d8e" stroke-width="1.2"/>')
    elif kind == "utility":
        for k in range(2):
            box(0.2 + k * 0.7, 0.2, 0.6, 0.6, "#f4f6f7", 3)
            disc(0.5 + k * 0.7, 0.5, 0.18, "#9aa4ab", False)
    else:
        table(W / 2, H / 2, min(1.2, W - 1.6), min(0.8, H - 1.6))
    return "".join(out)


def plan_svg(rooms: list[Room], lang: str = "de", theme: str = "auto") -> str:
    """The rooms as a schematic floor plan from above: floors (wood, tiles, stone) and furniture by the kind of room,
    walls with doors and windows; on every room its temperature, target and a flame while its heating element heats,
    tinted blue while too cold and orange while too warm. Two floors: ground floor at the top, upper floor below."""
    t = _t(lang)
    lay = plan_layout([r.name for r in rooms], [r.floor for r in rooms])
    x0, y0, W, H = PLAN_PAD, PLAN_PAD, PLAN_W_M * PLAN_M, PLAN_H_M * PLAN_M
    body = [f'<defs>{_PLAN_DEFS}</defs>',
            f'<rect x="{x0 - 8}" y="{y0 - 8}" width="{W + 16}" height="{H + 16}" rx="6" fill="#000" opacity=".35"/>']
    for (rx, ry, rw, rh), (_kind, _w, cover) in zip(lay.rooms, lay.kinds):
        body.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" fill="url(#{cover})"/>')
    if not rooms:
        body.append(f'<rect x="{x0}" y="{y0}" width="{W}" height="{H}" fill="url(#wood)"/>')
    for r, (rx, ry, rw, rh) in zip(rooms, lay.rooms):  # too cold / too warm: tinted, with a coloured edge
        tint = {"r-cold": "#4f97e8", "r-warm": "#f07a3a"}.get(_room_state(r)[0])
        if tint:
            body.append(f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" fill="{tint}" opacity=".16"/>'
                        f'<rect x="{rx + 7:.1f}" y="{ry + 7:.1f}" width="{rw - 14:.1f}" height="{rh - 14:.1f}" rx="4" fill="none" '
                        f'stroke="{tint}" stroke-width="3" opacity=".85"/>')
    for r, (rx, ry, rw, rh), (kind, _w, _f) in zip(rooms, lay.rooms, lay.kinds):
        body.append(_furniture(kind, r.name, rx + 3, ry + 3, rw - 6, rh - 6))
    body.append(_plan_walls(lay))
    body.append(f'<rect x="{x0}" y="{y0}" width="{W}" height="{H}" fill="url(#light)"/>')
    names = t["floor_names"]
    for r, box, style in zip(rooms, lay.labels, lay.styles):
        body.append(_plan_label(r, box, style, t))
    if len(lay.bands) > 1:
        for floor, top, _bottom in lay.bands:
            text = names[floor]
            tw = _text_w(text, 11) + 22
            body.append(f'<rect x="{x0 + 10}" y="{top + 10:.0f}" width="{tw:.0f}" height="22" rx="11" fill="#12162a" fill-opacity=".8" '
                        f'stroke="#ffffff" stroke-opacity=".18"/><text x="{x0 + 21}" y="{top + 25:.0f}" font-size="11" '
                        f'font-weight="600" fill="#e8ecff">{escape(text)}</text>')
    return _svg(lay.width, lay.height, "".join(body), theme)


def _plan_walls(lay: PlanLayout) -> str:
    """Outer walls with windows, inner walls with a door from every room to a neighbour on the same floor (the hall if
    there is one, else the largest), a thick wall between the floors."""
    x0, y0, W, H = PLAN_PAD, PLAN_PAD, PLAN_W_M * PLAN_M, PLAN_H_M * PLAN_M
    eps, door_w = 0.6, 0.9 * PLAN_M
    floor_of = {}
    for i, rect in enumerate(lay.rooms):
        for floor, top, bottom in lay.bands:
            if top - eps <= rect[1] < bottom - eps:
                floor_of[i] = floor

    def shared(a: tuple, b: tuple) -> tuple[str, float, float, float] | None:
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        for xa, xb in ((ax + aw, bx), (bx + bw, ax)):
            if abs(xa - xb) < eps:
                lo, hi = max(ay, by), min(ay + ah, by + bh)
                if hi - lo > 0:
                    return "v", xa, lo, hi
        for ya, yb in ((ay + ah, by), (by + bh, ay)):
            if abs(ya - yb) < eps:
                lo, hi = max(ax, bx), min(ax + aw, bx + bw)
                if hi - lo > 0:
                    return "h", ya, lo, hi
        return None

    doors: list[tuple[str, float, float, float]] = []
    for i, a in enumerate(lay.rooms):
        options = []
        for j, b in enumerate(lay.rooms):
            if i == j or floor_of.get(i) != floor_of.get(j):
                continue
            edge = shared(a, b)
            if edge and edge[3] - edge[2] >= door_w + 0.5 * PLAN_M:
                rank = (lay.kinds[j][0] != "hall", -lay.kinds[j][1], -(edge[3] - edge[2]))
                options.append((rank, edge))
        if options:
            _rank, (orient, pos, lo, hi) = min(options)
            mid = (lo + hi) / 2
            door = (orient, pos, mid - door_w / 2, mid + door_w / 2)
            if not any(d[0] == orient and abs(d[1] - pos) < eps and abs(d[2] - door[2]) < eps for d in doors):
                doors.append(door)

    def wall(orient: str, pos: float, lo: float, hi: float, width: float) -> str:
        cuts = sorted((d[2], d[3]) for d in doors if d[0] == orient and abs(d[1] - pos) < eps and d[3] > lo and d[2] < hi)
        parts, start = [], lo
        for a, b in cuts:
            if a > start:
                parts.append((start, a))
            start = max(start, b)
        if start < hi:
            parts.append((start, hi))
        out = []
        for a, b in parts:
            if b - a < 1:
                continue
            x1, y1, x2, y2 = (pos, a, pos, b) if orient == "v" else (a, pos, b, pos)
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#22252b" stroke-width="{width}" '
                       'stroke-linecap="square"/>')
        return "".join(out)

    out = [f'<rect x="{x0}" y="{y0}" width="{W}" height="{H}" fill="none" stroke="#22252b" stroke-width="10"/>']
    band_lines = {round(top, 1) for _f, top, _b in lay.bands[1:]}
    for x, y, w, h in lay.rooms:
        if x + w < x0 + W - eps:
            out.append(wall("v", x + w, y, y + h, 6))
        if y + h < y0 + H - eps:
            out.append(wall("h", y + h, x, x + w, 10 if round(y + h, 1) in band_lines else 6))
    # windows: one in every outer wall of a room
    for x, y, w, h in lay.rooms:
        for orient, pos, lo, hi, outer in (("h", y, x, x + w, abs(y - y0) < eps), ("h", y + h, x, x + w, abs(y + h - y0 - H) < eps),
                                           ("v", x, y, y + h, abs(x - x0) < eps), ("v", x + w, y, y + h, abs(x + w - x0 - W) < eps)):
            length = hi - lo
            if not outer or length < 1.5 * PLAN_M:
                continue
            win = min(0.45 * length, 2.2 * PLAN_M)
            start, end = lo + (length - win) / 2, lo + (length + win) / 2
            x1, y1, x2, y2 = (start, pos, end, pos) if orient == "h" else (pos, start, pos, end)
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#a9d6ee" stroke-width="4"/>')
    return "".join(out)


_PLAN_DOTS = {"r-cold": "#8fc3f0", "r-warm": "#f6b27a", "r-fine": "#9be3a6", "r-none": "#aab3c0"}


def _plan_label(r: Room, box: tuple[float, float, float, float], style: str, t: dict) -> str:
    x, y, w, h = box
    name_size, temp_size = {"full": (12.5, 22), "compact": (11.5, 18), "mini": (10, 14)}[style]
    pad = 9 if style == "mini" else 11
    flame = 0.45 if style == "mini" else 0.55
    name = _fit(r.name, name_size, w - pad - 12 - (18 if r.heating else 6))
    goal = "–" if r.target is None else _deg(r.target, 0 if float(r.target).is_integer() else 1)
    target = (f'<text x="{x + w - 10:.0f}" y="{y + h - 12:.0f}" font-size="12" fill="#9aa3c8" text-anchor="end">'
              f'{t["target"]} {goal}</text>' if style == "full" else "")
    return (
        f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="12" fill="#12162a" fill-opacity=".8" '
        f'stroke="#ffffff" stroke-opacity=".18"/>'
        f'<circle cx="{x + pad + 2:.0f}" cy="{y + name_size + 1:.0f}" r="{3.5 if style == "mini" else 4}" fill="{_PLAN_DOTS[_room_state(r)[0]]}"/>'
        f'<text x="{x + pad + 10:.0f}" y="{y + name_size + 5:.0f}" font-size="{name_size}" font-weight="500" fill="#c9cfe8">{escape(name)}</text>'
        f'<text x="{x + pad:.0f}" y="{y + h - (8 if style == "mini" else 11):.0f}" font-size="{temp_size}" font-weight="600" '
        f'fill="#ffffff">{_deg(r.actual)}</text>{target}'
        + (_flame(x + w - 6 - 28 * flame, y + 5, flame) if r.heating else "")
    )
