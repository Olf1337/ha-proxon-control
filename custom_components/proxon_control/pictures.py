"""Dashboard pictures drawn from the unit's live values (SVG, no Home Assistant imports): the unit, the hot-water tank, the house.

* Transparent background: the picture sits on the dashboard card, whatever the theme. Texts and lines follow light / dark mode
  (automatically by the device's colour scheme, or fixed with the integration option).
* Animated (CSS inside the SVG, which also runs when the picture is shown as an image): the fans turn while the ventilation runs
  (faster at higher levels), the air moves through the ducts, the heat pump fan turns while the compressor runs, the immersion
  heater glows while it is on, and rooms with their heating element released show a flickering flame.
* The layout helpers (`*_targets`) tell the dashboard where things are, so tapping a room opens its thermostat.
"""
from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

TEXT = {
    "de": {
        "outside": "Außenluft", "supply": "Zuluft", "extract": "Abluft", "exhaust": "Fortluft", "level": "Stufe",
        "exchanger": "Kreuzstrom-Wärmetauscher", "heat_pump": "Wärmepumpe", "filter": "Filter", "days": "Tage",
        "tank": "Warmwasser", "target": "Soll", "actual": "Ist", "heater": "Heizstab", "on": "an", "off": "aus",
        "heater_target": "Heizstab-Soll", "house": "Haus", "unit": "Anlage", "rpm": "U/min",
        "modes": {0: "Aus", 1: "Sommer", 2: "Winter", 3: "ECO Komfort", 5: "Urlaub"},
        "doing": {"heat": "Heizen", "cool": "Kühlen", "vent": "Lüften", "off": "Steht"},
        "cold": "zu kalt", "fine": "passt", "warm": "zu warm", "fault": "Störung", "boost_vent": "Intensivlüftung",
        "solar": "Solar", "price": "Günstiger Strom", "boost": "Boost", "cooling": "Nachtkühlung", "tap": "antippen zum Einstellen",
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
        "modes": {0: "Off", 1: "Summer", 2: "Winter", 3: "ECO Comfort", 5: "Holiday"},
        "doing": {"heat": "Heating", "cool": "Cooling", "vent": "Ventilating", "off": "Stopped"},
        "cold": "too cold", "fine": "fine", "warm": "too warm", "fault": "Fault", "boost_vent": "Boost ventilation",
        "solar": "Solar", "price": "Cheap power", "boost": "Boost", "cooling": "Night cooling", "tap": "tap to adjust",
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
    "--shell2:#f8f9fa;--empty:#e8f1fb;--fanbg:#f4f6f8;--blade:#7c8590;--hub:#3d464f"
)
DARK = (
    "--fg:#e6eaee;--muted:#a7b1bc;--line:#9aa6b2;--chip:#2c323a;--chipline:#454d57;--case1:#434a53;--case2:#2c3138;"
    "--casetop:#3a4048;--wall1:#4d5258;--wall2:#656b72;--housewall:#2a2f35;--houseline:#69717a;--shell1:#4a5057;"
    "--shell2:#79818a;--empty:#2b3642;--fanbg:#353b42;--blade:#b6bec7;--hub:#e1e6eb"
)

# picture sizes (viewBox); the dashboard needs them to place its tap areas
UNIT_W, UNIT_H = 800, 440
TANK_W, TANK_H = 384, 520
HOUSE_W = 800


def _t(lang: str) -> dict:
    return TEXT["de" if (lang or "").startswith("de") else "en"]


def _num(data: dict, key: str) -> float | None:
    v = data.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _deg(v: float | None, digits: int = 1) -> str:
    if v is None:
        return "–"
    return f"{v:.{digits}f}°".replace(".", ",")


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
    running = mode is not None and int(mode) != 0 and bool(level)
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


# ---------------- the hot-water tank ----------------
TANK_TOP, TANK_BOTTOM, TANK_X1, TANK_X2 = 132, 412, 92, 262


def tank_targets() -> dict[str, tuple[float, float, float, float]]:
    return {"tank": (
        (TANK_X1 + TANK_X2) / 2 / TANK_W * 100, (TANK_TOP + TANK_BOTTOM) / 2 / TANK_H * 100,
        (TANK_X2 - TANK_X1 + 20) / TANK_W * 100, (TANK_BOTTOM - TANK_TOP + 30) / TANK_H * 100,
    )}


def tank_svg(
    data: dict, lang: str = "de", boost_limit: float | None = None, theme: str = "auto",
    energy_status: str | None = None, boost_status: str | None = None,
) -> str:
    """The hot-water tank (T300) in section: temperature layers, target / actual, immersion heater, heat pump; status chips."""
    t = _t(lang)
    actual = _num(data, "WarmwasserIstTemperatur")
    target = _num(data, "SollWassertemperatur")
    heater_on = bool(data.get("E-Heizstab"))
    pump_on = bool(data.get("T300Betriebsart"))
    heater_target = _num(data, "Soll-E-Heizstab-Temperatur")
    top, bottom, x1, x2 = TANK_TOP, TANK_BOTTOM, TANK_X1, TANK_X2
    mid = (x1 + x2) / 2
    # how "full" of heat the tank is: actual compared to target (as a share of the tank's height)
    share = 0.5 if actual is None or not target else max(0.12, min(1.0, (actual - 15) / max(1.0, target - 15)))
    hot_y = bottom - (bottom - top) * share
    glow = ' class="glow"' if heater_on else ""
    # actual value next to the top of the hot water, but never on top of the target label
    ist_y = min(max(hot_y + 20, top + 52), bottom - 70)
    chips: list[tuple[str, str | None, str | None]] = []
    if energy_status:
        heating = energy_status in ("heating_solar", "heating_price")
        label = t["price"] if energy_status == "heating_price" else t["solar"]
        chips.append((f"☀ {label}: {_status(t, energy_status)}", "#fff1c2" if heating else None, "#6b4a00" if heating else None))
    if boost_status:
        heating = boost_status == "heating"
        txt = f"♨ {t['boost']}: {_status(t, boost_status)}" + (f" (< {_deg(boost_limit, 0)})" if boost_limit is not None else "")
        chips.append((txt, "#fde4d8" if heating else None, "#6e2a10" if heating else None))
    rows = "".join(_chip(20, 446 + i * 36, text, 14, fill, color) for i, (text, fill, color) in enumerate(chips[:2]))
    body = f"""
<defs>
<linearGradient id="water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e5483b"/><stop offset=".55" stop-color="#f4a28c"/><stop offset="1" stop-color="#cfe3f8"/></linearGradient>
<linearGradient id="shell" x1="0" y1="0" x2="1" y2="0"><stop offset="0" class="s-shell1"/><stop offset=".5" class="s-shell2"/><stop offset="1" class="s-shell1"/></linearGradient>
<clipPath id="inner"><path d="M{x1+6} {top} Q{mid} {top-16} {x2-6} {top} V{bottom} Q{mid} {bottom+16} {x1+6} {bottom} Z"/></clipPath>
</defs>
<text x="20" y="38" font-size="24" font-weight="600" class="fg">{escape(t['tank'])}</text>
<g transform="translate({mid - 62},56)"><rect width="124" height="46" rx="8" class="chip"/>
{''.join(f'<line x1="10" y1="{y}" x2="70" y2="{y}" class="ln"/>' for y in (12, 19, 26, 33))}
{_fan(98, 23, 14, 0.8 if pump_on else None)}</g>
<text x="{mid + 72}" y="74" font-size="13" class="mu">{t['heat_pump']}</text>
<text x="{mid + 72}" y="94" font-size="15" font-weight="600" class="fg">{t['on'] if pump_on else t['off']}</text>
<path d="M{x1} {top-4} Q{mid} {top-24} {x2} {top-4} V{bottom+4} Q{mid} {bottom+24} {x1} {bottom+4} Z" fill="url(#shell)" class="ln" stroke-width="1.5"/>
<g clip-path="url(#inner)"><rect x="{x1}" y="{top-24}" width="{x2-x1}" height="{bottom-top+48}" class="empty"/>
<rect x="{x1}" y="{hot_y:.0f}" width="{x2-x1}" height="{bottom-hot_y+24:.0f}" fill="url(#water)"/>
<rect x="{x1}" y="{hot_y:.0f}" width="{x2-x1}" height="3" fill="#ffffff" opacity=".6"/></g>
<g{glow}><rect x="{x1+18}" y="{bottom-36}" width="{x2-x1-36}" height="11" rx="5" fill="{'#ff6a2b' if heater_on else '#9aa3ab'}"/></g>
<text x="{mid}" y="{bottom-44}" font-size="14" fill="#3d464f" text-anchor="middle">{t['heater']} {t['on'] if heater_on else t['off']}</text>
<line x1="{x2}" y1="{top+14}" x2="{x2+14}" y2="{top+14}" class="ln"/>
<text x="{x2+18}" y="{top+19}" font-size="15" class="mu">{t['target']} <tspan font-weight="600" class="fg">{_deg(target, 0)}</tspan></text>
<line x1="{x2}" y1="{ist_y:.0f}" x2="{x2+14}" y2="{ist_y:.0f}" class="ln"/>
<text x="{x2+18}" y="{ist_y - 4:.0f}" font-size="13" class="mu">{t['actual']}</text>
<text x="{x2+18}" y="{ist_y + 24:.0f}" font-size="26" font-weight="600" class="fg">{_deg(actual)}</text>
<text x="{x2+18}" y="{bottom-6}" font-size="12" class="mu">{t['heater_target']}</text>
<text x="{x2+18}" y="{bottom+12}" font-size="15" font-weight="600" class="fg">{_deg(heater_target, 0)}</text>
{rows}
"""
    return _svg(TANK_W, TANK_H, body, theme)


# ---------------- the house ----------------
@dataclass
class Room:
    name: str
    actual: float | None
    target: float | None
    heating: bool  # heating element released


ROOM_H = 118
HOUSE_TOP = 150


def house_layout(count: int) -> tuple[int, list[tuple[float, float, float, float]]]:
    """Height of the picture and the rooms' boxes (x, y, w, h): 3 per row, 4 from ten rooms on."""
    cols = 3 if count <= 9 else 4
    rows = max(1, -(-count // cols))
    room_w = (HOUSE_W - 96 - (cols - 1) * 12) / cols
    boxes = [(48 + (i % cols) * (room_w + 12), HOUSE_TOP + (i // cols) * (ROOM_H + 12), room_w, ROOM_H) for i in range(count)]
    height = HOUSE_TOP + rows * (ROOM_H + 12) + 54
    return int(height), boxes


def house_targets(count: int) -> list[tuple[float, float, float, float]]:
    height, boxes = house_layout(count)
    return [((x + w / 2) / HOUSE_W * 100, (y + h / 2) / height * 100, w / HOUSE_W * 100, h / height * 100) for x, y, w, h in boxes]


def _room_colors(r: Room) -> tuple[str, str, str]:
    """(fill, border, text) by how the room is doing compared to its target."""
    if r.actual is None or r.target is None:
        return "#eef0f2", "#9aa3ab", "#3d464f"
    diff = r.actual - r.target
    if diff < -1:
        return "#dcebfb", "#3b82d6", "#123c69"  # too cold
    if diff > 1:
        return "#fde4d8", "#d8602f", "#6e2a10"  # too warm
    return "#ddf3e9", "#1f9d6c", "#0b4d33"  # fine


def house_svg(rooms: list[Room], outside: float | None, lang: str = "de", theme: str = "auto") -> str:
    """The house in section with all rooms, laid out automatically; colour by actual vs target, flame for the heating element."""
    t = _t(lang)
    height, layout = house_layout(len(rooms))
    boxes = []
    for r, (x, y, w, h) in zip(rooms, layout):
        fill, border, text = _room_colors(r)
        flame = (
            # position in an outer group: the animation's transform would replace a transform on the same element
            f'<g transform="translate({x + w - 40:.0f},{y + 12:.0f})"><g class="flame">'
            f'<path d="M14 0 C20 12 28 16 26 28 C24 37 4 37 2 28 C0 19 8 14 14 0 Z" fill="#ff6a2b"/>'
            f'<path d="M14 13 C16 19 21 22 19 28 C18 32 10 32 9 28 C8 23 13 20 14 13 Z" fill="#ffd166"/></g></g>'
            if r.heating else ""
        )
        boxes.append(
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h}" rx="12" fill="{fill}" stroke="{border}" stroke-width="2"/>'
            f'<text x="{x + 16:.0f}" y="{y + 32:.0f}" font-size="21" font-weight="600" fill="{text}">{escape(r.name)}</text>'
            f'<text x="{x + 16:.0f}" y="{y + 78:.0f}" font-size="42" font-weight="600" fill="{text}">{_deg(r.actual)}</text>'
            f'<text x="{x + 16:.0f}" y="{y + 106:.0f}" font-size="18" fill="{text}">{t["target"]} {_deg(r.target)}</text>'
            f'<path d="M{x + w - 26:.0f} {y + h - 34:.0f} l8 8 l-8 8" fill="none" stroke="{border}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f"{flame}"
        )
    roof = f"M24 {HOUSE_TOP - 22} L{HOUSE_W / 2:.0f} 66 L{HOUSE_W - 24} {HOUSE_TOP - 22}"
    legend = _chips_left(24, height - 40, [
        (t["cold"], "#dcebfb", "#123c69"), (t["fine"], "#ddf3e9", "#0b4d33"), (t["warm"], "#fde4d8", "#6e2a10"),
    ], 16)
    body = f"""
<text x="24" y="40" font-size="28" font-weight="600" class="fg">{escape(t['house'])}</text>
{_chips_right(HOUSE_W - 20, 14, [f"{t['outside']} {_deg(outside)}"], 18)}
<rect x="{HOUSE_W * 0.7:.0f}" y="72" width="30" height="44" fill="#b9b7ae" stroke="#8a877e"/>
<rect x="34" y="{HOUSE_TOP - 24}" width="{HOUSE_W - 68}" height="{height - HOUSE_TOP - 26}" class="hw" stroke-width="2.5"/>
<path d="{roof} Z" fill="#c8553d" stroke="#8f3a29" stroke-width="2"/>
<path d="{roof}" fill="none" stroke="#8f3a29" stroke-width="5" stroke-linejoin="round"/>
{''.join(boxes)}
{legend}
<text x="{HOUSE_W - 24}" y="{height - 18}" font-size="16" class="mu" text-anchor="end">{escape(t['tap'])} ›</text>
"""
    return _svg(HOUSE_W, height, body, theme)
