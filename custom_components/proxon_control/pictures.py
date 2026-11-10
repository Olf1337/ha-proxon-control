"""Dashboard pictures drawn from the unit's live values (SVG, no Home Assistant imports): the unit, the hot-water tank, the house.

The pictures are animated (CSS inside the SVG, which also runs when the picture is shown as an image): the fans turn while the
ventilation runs (faster at higher levels), the air moves through the ducts, the heat pump fan turns while the compressor runs,
the immersion heater glows while it is on, and rooms with their heating element released show a flickering flame.
"""
from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

TEXT = {
    "de": {
        "outside": "Außenluft", "supply": "Zuluft", "extract": "Abluft", "exhaust": "Fortluft", "level": "Stufe",
        "exchanger": "Kreuzstrom-Wärmetauscher", "heat_pump": "Wärmepumpe", "filter": "Filter", "days": "Tage",
        "tank": "Warmwasser", "target": "Soll", "actual": "Ist", "heater": "Heizstab", "on": "an", "off": "aus",
        "heater_target": "Heizstab-Soll", "boost": "Boost unter", "house": "Haus", "heating": "Zuheizer an",
        "modes": {0: "Aus", 1: "Sommer", 2: "Winter", 3: "ECO Komfort", 5: "Urlaub"},
        "doing": {"heat": "Heizen", "cool": "Kühlen", "vent": "Lüften"}, "rpm": "U/min", "unit": "Anlage",
    },
    "en": {
        "outside": "Outdoor air", "supply": "Supply air", "extract": "Extract air", "exhaust": "Exhaust air", "level": "Level",
        "exchanger": "Cross-flow heat exchanger", "heat_pump": "Heat pump", "filter": "Filter", "days": "days",
        "tank": "Hot water", "target": "Target", "actual": "Actual", "heater": "Immersion heater", "on": "on", "off": "off",
        "heater_target": "Heater target", "boost": "Boost below", "house": "House", "heating": "Heating element on",
        "modes": {0: "Off", 1: "Summer", 2: "Winter", 3: "ECO Comfort", 5: "Holiday"},
        "doing": {"heat": "Heating", "cool": "Cooling", "vent": "Ventilating"}, "rpm": "rpm", "unit": "Unit",
    },
}

FONT = "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def _t(lang: str) -> dict:
    return TEXT["de" if (lang or "").startswith("de") else "en"]


def _num(data: dict, key: str) -> float | None:
    v = data.get(key)
    return float(v) if isinstance(v, (int, float)) else None


def _deg(v: float | None, digits: int = 1) -> str:
    if v is None:
        return "–"
    return f"{v:.{digits}f}°".replace(".", ",")


def _svg(width: int, height: int, body: str, style: str = "") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">'
        f"<style>text{{{FONT}}}.spin{{transform-box:fill-box;transform-origin:center;animation:spin linear infinite}}"
        f"@keyframes spin{{to{{transform:rotate(360deg)}}}}"
        f".flow{{stroke-dasharray:6 14;animation:flow 1.2s linear infinite}}@keyframes flow{{to{{stroke-dashoffset:-20}}}}"
        f".glow{{animation:glow 1.6s ease-in-out infinite alternate}}@keyframes glow{{from{{opacity:.45}}to{{opacity:1}}}}"
        f".flame{{transform-box:fill-box;transform-origin:50% 100%;animation:flick .9s ease-in-out infinite alternate}}"
        f"@keyframes flick{{from{{transform:scale(1,1)}}to{{transform:scale(.9,1.12)}}}}{style}</style>{body}</svg>"
    )


def _fan(x: float, y: float, r: float, seconds: float | None) -> str:
    """A fan; turning when `seconds` (time per turn) is given."""
    blades = "".join(
        f'<path d="M0 0 C{r*.35:.1f} {-r*.8:.1f} {r*.8:.1f} {-r*.5:.1f} {r*.85:.1f} {-r*.15:.1f} Z" transform="rotate({a})" fill="#7c8590"/>'
        for a in (0, 72, 144, 216, 288)
    )
    spin = f' class="spin" style="animation-duration:{seconds:.2f}s"' if seconds else ""
    return (
        f'<g transform="translate({x},{y})"><circle r="{r+3}" fill="#f4f6f8" stroke="#5f6b76" stroke-width="1.5"/>'
        f"<g{spin}>{blades}</g><circle r=\"{r*.18:.1f}\" fill=\"#3d464f\"/></g>"
    )


def _duct(path: str, color: str, light: str, moving: bool, reverse: bool = False) -> str:
    anim = f' class="flow" style="animation-direction:{"reverse" if reverse else "normal"}"' if moving else ""
    return (
        f'<path d="{path}" fill="none" stroke="{light}" stroke-width="18" stroke-linecap="round"/>'
        f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3"{anim} stroke-linecap="round"/>'
    )


def unit_svg(data: dict, lang: str = "de") -> str:
    """The ventilation unit: four air flows, cross-flow heat exchanger, two fans, filter, heat pump."""
    t = _t(lang)
    mode = _num(data, "Betriebsart")
    level = _num(data, "IstLuefterstufe") or _num(data, "Luefterstufe")
    running = mode is not None and int(mode) != 0 and bool(level)
    fan_s = (2.4 / max(1.0, level)) if running and level else None
    rpm = _num(data, "DrehzahlKompressor") or 0
    cooling = bool(data.get("Kuehlbetrieb4Wegeventil"))
    doing = t["doing"]["cool" if cooling else "heat"] if rpm > 0 else t["doing"]["vent"]
    filter_h = _num(data, "FilterRestStunden")
    mode_txt = t["modes"].get(int(mode), "–") if mode is not None else "–"
    head = f"{mode_txt} · {doing} · {t['level']} {int(level) if level else '–'}"
    body = f"""
<defs>
<linearGradient id="case" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fbfbfa"/><stop offset="1" stop-color="#dcdcd6"/></linearGradient>
<linearGradient id="hx" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#d6e8fb"/><stop offset="1" stop-color="#fbe0d6"/></linearGradient>
<linearGradient id="wall" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#b9b7ae"/><stop offset="1" stop-color="#e2e0d9"/></linearGradient>
<filter id="sh" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="3" stdDeviation="3" flood-opacity=".18"/></filter>
</defs>
<rect width="640" height="300" rx="14" fill="#eef1f4"/>
<text x="20" y="30" font-size="17" font-weight="600" fill="#1f2933">{escape(t['unit'])}</text>
<text x="620" y="30" font-size="13" fill="#52606d" text-anchor="end">{escape(head)}</text>
<rect x="18" y="52" width="26" height="200" rx="4" fill="url(#wall)" stroke="#8a877e"/>
{''.join(f'<line x1="23" y1="{y}" x2="39" y2="{y}" stroke="#8a877e" stroke-width="2"/>' for y in (78, 86, 94, 202, 210, 218))}
{_duct("M44 88 H190", "#2b7bd6", "#cfe3f8", running)}
{_duct("M44 210 H190", "#7b8794", "#dde1e5", running, reverse=True)}
{_duct("M450 88 H600", "#d1572b", "#f8d9cc", running)}
{_duct("M450 210 H600", "#c98a1a", "#f6e3bd", running, reverse=True)}
<text x="56" y="72" font-size="13" fill="#1f2933">{t['outside']} <tspan font-weight="600">{_deg(_num(data, 'T3Frischluft'))}</tspan></text>
<text x="56" y="240" font-size="13" fill="#1f2933">{t['exhaust']} <tspan font-weight="600">{_deg(_num(data, 'T4Fortluft'))}</tspan></text>
<text x="600" y="72" font-size="13" fill="#1f2933" text-anchor="end">{t['supply']} <tspan font-weight="600">{_deg(_num(data, 'T1Zuluft'))}</tspan></text>
<text x="600" y="240" font-size="13" fill="#1f2933" text-anchor="end">{t['extract']} <tspan font-weight="600">{_deg(_num(data, 'T7Abluft'))}</tspan></text>
<g filter="url(#sh)"><rect x="190" y="52" width="260" height="200" rx="10" fill="url(#case)" stroke="#5f6b76" stroke-width="1.5"/></g>
<rect x="190" y="52" width="260" height="20" rx="10" fill="#e4e6e3"/><text x="202" y="66" font-size="10" fill="#52606d" letter-spacing="1">PROXON FWT</text>
<g transform="translate(320,152) rotate(45)">
<rect x="-58" y="-58" width="116" height="116" fill="url(#hx)" stroke="#5f6b76" stroke-width="1.5"/>
{''.join(f'<line x1="-58" y1="{y}" x2="58" y2="{y}" stroke="#7fb0e6" stroke-width="1.4"/>' for y in range(-50, 58, 9))}
{''.join(f'<line x1="{x}" y1="-58" x2="{x}" y2="58" stroke="#ec9c7d" stroke-width="1.4" opacity=".85"/>' for x in range(-50, 58, 9))}
</g>
<text x="320" y="270" font-size="12" fill="#52606d" text-anchor="middle">{t['exchanger']}</text>
{_fan(418, 88, 17, fan_s)}
{_fan(222, 210, 17, fan_s)}
<rect x="210" y="234" width="46" height="12" rx="3" fill="#cfd3d6" stroke="#7b8794"/>
<text x="233" y="243" font-size="8" fill="#3d464f" text-anchor="middle">{t['filter']}</text>
<g transform="translate(328,198)"><rect width="114" height="44" rx="6" fill="#3d464f"/>
{_fan(20, 22, 12, 0.6 if rpm > 0 else None)}
<text x="40" y="19" font-size="10" fill="#e4e7eb">{t['heat_pump']}</text><text x="40" y="34" font-size="10" fill="#e4e7eb">{int(rpm)} {t['rpm']}</text></g>
<text x="20" y="290" font-size="12" fill="#52606d">{t['filter']}: {round(filter_h / 24) if filter_h is not None else '–'} {t['days']}</text>
"""
    return _svg(640, 300, body)


def tank_svg(data: dict, lang: str = "de", boost_limit: float | None = None) -> str:
    """The hot-water tank (T300) in section: temperature layers, target / actual, immersion heater, heat pump on top."""
    t = _t(lang)
    actual = _num(data, "WarmwasserIstTemperatur")
    target = _num(data, "SollWassertemperatur")
    heater_on = bool(data.get("E-Heizstab"))
    pump_on = bool(data.get("T300Betriebsart"))
    heater_target = _num(data, "Soll-E-Heizstab-Temperatur")
    # how "full" of heat the tank is: actual compared to target (as a share of the tank's height)
    share = 0.5 if actual is None or not target else max(0.12, min(1.0, (actual - 15) / max(1.0, target - 15)))
    top, bottom = 92, 330
    hot_y = bottom - (bottom - top) * share
    glow = ' class="glow"' if heater_on else ""
    boost_txt = f"{t['boost']} {_deg(boost_limit, 0)}" if boost_limit is not None else ""
    body = f"""
<defs>
<linearGradient id="water" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e5483b"/><stop offset=".55" stop-color="#f4a28c"/><stop offset="1" stop-color="#cfe3f8"/></linearGradient>
<linearGradient id="shell" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#cfd3d6"/><stop offset=".5" stop-color="#f8f9fa"/><stop offset="1" stop-color="#c4c8cc"/></linearGradient>
<clipPath id="inner"><path d="M66 {top} Q130 {top-14} 194 {top} V{bottom} Q130 {bottom+14} 66 {bottom} Z"/></clipPath>
</defs>
<rect width="300" height="380" rx="14" fill="#eef1f4"/>
<text x="20" y="30" font-size="17" font-weight="600" fill="#1f2933">{t['tank']}</text>
<g transform="translate(80,40)"><rect width="100" height="36" rx="6" fill="#d8dcdf" stroke="#5f6b76"/>
{''.join(f'<line x1="8" y1="{y}" x2="58" y2="{y}" stroke="#8a939c"/>' for y in (8, 14, 20, 26))}
{_fan(80, 18, 11, 0.8 if pump_on else None)}</g>
<text x="190" y="56" font-size="11" fill="#52606d">{t['heat_pump']}</text><text x="190" y="70" font-size="11" font-weight="600" fill="#1f2933">{t['on'] if pump_on else t['off']}</text>
<path d="M60 {top-4} Q130 {top-22} 200 {top-4} V{bottom+4} Q130 {bottom+22} 60 {bottom+4} Z" fill="url(#shell)" stroke="#5f6b76" stroke-width="1.5"/>
<g clip-path="url(#inner)"><rect x="60" y="{top-20}" width="140" height="{bottom-top+40}" fill="#e8f1fb"/>
<rect x="60" y="{hot_y:.0f}" width="140" height="{bottom-hot_y+20:.0f}" fill="url(#water)" transform="translate(0,0)"/>
<rect x="60" y="{hot_y:.0f}" width="140" height="3" fill="#ffffff" opacity=".6"/></g>
<g{glow}><rect x="78" y="{bottom-32}" width="104" height="9" rx="4" fill="{'#ff6a2b' if heater_on else '#9aa3ab'}"/></g>
<text x="130" y="{bottom-38}" font-size="10" fill="#3d464f" text-anchor="middle">{t['heater']} {t['on'] if heater_on else t['off']}</text>
<line x1="200" y1="{top+30}" x2="214" y2="{top+30}" stroke="#5f6b76"/><text x="218" y="{top+34}" font-size="13" fill="#1f2933">{t['target']} {_deg(target, 0)}</text>
<line x1="200" y1="{hot_y+20:.0f}" x2="214" y2="{hot_y+20:.0f}" stroke="#5f6b76"/>
<text x="218" y="{hot_y+18:.0f}" font-size="11" fill="#52606d">{t['actual']}</text><text x="218" y="{hot_y+36:.0f}" font-size="18" font-weight="600" fill="#1f2933">{_deg(actual)}</text>
<text x="20" y="362" font-size="11" fill="#52606d">{t['heater_target']} {_deg(heater_target, 0)}</text>
<text x="280" y="362" font-size="11" fill="#52606d" text-anchor="end">{boost_txt}</text>
"""
    return _svg(300, 380, body)


@dataclass
class Room:
    name: str
    actual: float | None
    target: float | None
    heating: bool  # heating element released


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


def house_svg(rooms: list[Room], outside: float | None, lang: str = "de") -> str:
    """The house in section; rooms laid out automatically (3 per row, 4 from ten rooms on)."""
    t = _t(lang)
    cols = 3 if len(rooms) <= 9 else 4
    rows = max(1, -(-len(rooms) // cols))
    w = 640
    room_w = (w - 80 - (cols - 1) * 10) / cols
    room_h = 96
    top = 150
    height = top + rows * (room_h + 10) + 30
    boxes = []
    for i, r in enumerate(rooms):
        x = 40 + (i % cols) * (room_w + 10)
        y = top + (i // cols) * (room_h + 10)
        fill, border, text = _room_colors(r)
        flame = (
            # position in an outer group: the animation's transform would replace a transform on the same element
            f'<g transform="translate({x + room_w - 34:.0f},{y + 10})"><g class="flame">'
            f'<path d="M12 0 C17 10 24 14 22 24 C20 32 4 32 2 24 C0 16 7 12 12 0 Z" fill="#ff6a2b"/>'
            f'<path d="M12 11 C14 16 18 19 16 24 C15 28 9 28 8 24 C7 20 11 17 12 11 Z" fill="#ffd166"/></g></g>'
            if r.heating else ""
        )
        target = f"{t['target']} {_deg(r.target, 1)}" + (f" · {t['heating']}" if r.heating else "")
        boxes.append(
            f'<rect x="{x:.0f}" y="{y}" width="{room_w:.0f}" height="{room_h}" rx="8" fill="{fill}" stroke="{border}" stroke-width="1.5"/>'
            f'<text x="{x + 12:.0f}" y="{y + 24}" font-size="13" fill="{text}">{escape(r.name)}</text>'
            f'<text x="{x + 12:.0f}" y="{y + 58}" font-size="26" font-weight="600" fill="{text}">{_deg(r.actual)}</text>'
            f'<text x="{x + 12:.0f}" y="{y + 82}" font-size="11" fill="{text}">{escape(target)}</text>{flame}'
        )
    roof = f"M20 {top-18} L{w/2:.0f} 52 L{w-20} {top-18}"
    body = f"""
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dbe9f6"/><stop offset="1" stop-color="#eef1f4"/></linearGradient></defs>
<rect width="{w}" height="{height}" rx="14" fill="url(#sky)"/>
<text x="20" y="30" font-size="17" font-weight="600" fill="#1f2933">{t['house']}</text>
<text x="{w-20}" y="30" font-size="13" fill="#52606d" text-anchor="end">{t['outside']} {_deg(outside)}</text>
<rect x="{w*0.7:.0f}" y="62" width="26" height="40" fill="#b9b7ae" stroke="#8a877e"/>
<rect x="30" y="{top-20}" width="{w-60}" height="{height-top+4}" fill="#fbfaf7" stroke="#8a877e" stroke-width="2"/>
<path d="{roof} Z" fill="#c8553d" stroke="#8f3a29" stroke-width="2"/>
<path d="{roof}" fill="none" stroke="#8f3a29" stroke-width="4" stroke-linejoin="round"/>
{''.join(boxes)}
"""
    return _svg(w, int(height), body)
