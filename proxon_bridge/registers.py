"""Values of the ventilation unit: object/address numbers and conversions (see app/MECHANICS.md).

No Home Assistant imports: the bridge add-on uses this file too.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time

QUERY_SET_READ = "setpointReadListValue"
QUERY_DATA_READ = "datapointReadListValue"
QUERY_WRITE = "setpointWriteValue"

# room panels: NBE0 (living room, always there) and NBE1 .. NBE20, as far as the unit reports them connected
ROOM_COUNT = 21
# rooms assumed when a unit doesn't report its connected-rooms bit field (behaviour of earlier versions)
FALLBACK_ROOMS = range(1, 5)

# operating modes (Betriebsart)
MODE_OFF, MODE_SUMMER, MODE_WINTER, MODE_COMFORT, MODE_STOVE, MODE_HOLIDAY = 0, 1, 2, 3, 4, 5
MODE_KEYS = {
    MODE_OFF: "off", MODE_SUMMER: "summer", MODE_WINTER: "winter", MODE_COMFORT: "eco_comfort", MODE_STOVE: "stove",
    MODE_HOLIDAY: "holiday",
}
# the original's mode menu offers these (holiday is only shown). Stove mode ("Ofenbetrieb": the unit keeps a slight
# overpressure so a fireplace doesn't draw smoke into the room) as documented by the ha-lan-proxon project (MIT).
MODE_CHOICES = [MODE_COMFORT, MODE_WINTER, MODE_SUMMER, MODE_STOVE, MODE_OFF]

# what the unit is doing right now: worked out from the compressor and the 4-way valve (see operation())
OPERATION_KEYS = {0: "ventilation", 1: "heating", 2: "cooling"}

# Data points named in Proxon's Modbus register list (FWT 2.0) whose meaning over the network isn't confirmed yet: read only
# into the diagnostics download, so a real unit's values can show what they hold (air volume, fault flag). (Confirmed on a
# real unit and now values of their own: the power figures. The COP figures of the list stay 0 there.)
PROBE_POINTS = (26, 47)

# operating hour counters (set point object 4), Modbus list S03-S13
HOUR_COUNTERS = {
    "StundenVorwaerme": 3, "StundenKompressorKuehlen": 6, "StundenKompressorHeizen": 7, "StundenAbtauen": 8,
    "StundenStufe1": 9, "StundenStufe2": 10, "StundenStufe3": 11, "StundenStufe4": 12,
}

# fault list of the hot-water module (data point 3:61), bit 15 first as in Proxon's Modbus list
T300_FAULT_BITS = {
    15: "modbus", 14: "filter", 13: "compressor", 12: "sensor_t9", 11: "sensor_t11", 10: "sensor_t13", 9: "sensor_t21",
    8: "sensor_t20", 7: "sensor_t6", 6: "sensor_t5", 5: "sensor_p19", 4: "sensor_p14", 3: "compressor_temperature", 2: "fan",
    1: "low_pressure", 0: "pressure_switch",
}


T300_FAULT_TEXT = {
    "de": {
        "modbus": "Verbindung zur Hauptanlage", "filter": "Filter wechseln", "compressor": "Kompressor", "sensor_t9": "Fühler T9 (extern)",
        "sensor_t11": "Fühler T11 (Sauggas)", "sensor_t13": "Fühler T13 (Kompressor)", "sensor_t21": "Fühler T21 (Speicher Mitte)",
        "sensor_t20": "Fühler T20 (Speicher unten)", "sensor_t6": "Fühler T6 (Verdampfer)", "sensor_t5": "Fühler T5 (vor Verdampfer)",
        "sensor_p19": "Drucksensor P19 (Abtauen)", "sensor_p14": "Drucksensor P14 (Niederdruck)",
        "compressor_temperature": "Kompressor zu heiß", "fan": "Ventilator", "low_pressure": "Niederdruck", "pressure_switch": "Pressostat",
    },
    "en": {
        "modbus": "Connection to the main unit", "filter": "Change filter", "compressor": "Compressor", "sensor_t9": "Sensor T9 (external)",
        "sensor_t11": "Sensor T11 (suction gas)", "sensor_t13": "Sensor T13 (compressor)", "sensor_t21": "Sensor T21 (tank middle)",
        "sensor_t20": "Sensor T20 (tank bottom)", "sensor_t6": "Sensor T6 (evaporator)", "sensor_t5": "Sensor T5 (before evaporator)",
        "sensor_p19": "Pressure sensor P19 (defrost)", "sensor_p14": "Pressure sensor P14 (low pressure)",
        "compressor_temperature": "Compressor too hot", "fan": "Fan", "low_pressure": "Low pressure", "pressure_switch": "Pressure switch",
    },
}


def t300_fault_texts(values: dict, language: str | None) -> list[str]:
    texts = T300_FAULT_TEXT["de" if (language or "").startswith("de") else "en"]
    return [texts[name] for name in t300_faults(values)]


def t300_faults(values: dict) -> list[str]:
    """What the hot-water module reports as faulty (keys of T300_FAULT_BITS)."""
    word = values.get("Fehlerwort3_61")
    if not isinstance(word, (int, float)):
        return []
    word = int(word) & 0xFFFF
    return [name for bit, name in T300_FAULT_BITS.items() if word >> bit & 1]

# clock of the unit: summer time flag, minute, hour, ISO weekday (1 = Monday), day, month, year (two digits)
CLOCK_KEYS = ("UhrSommerzeit", "UhrMinute", "UhrStunde", "UhrWochentag", "UhrTag", "UhrMonat", "UhrJahr")

# weekly ventilation schedule
SCHEDULE_PHASES = 3
SCHEDULE_FIELDS = ("start_h", "start_m", "end_h", "end_m", "level")  # level 0 = phase not active, 1..4


def schedule_index(day: int, phase: int, field: int) -> int:
    return 15 * day + 5 * phase + field


def schedule_key(day: int, phase: int, field: int) -> str:
    return f"ZP{day}_{phase}_{SCHEDULE_FIELDS[field]}"


# fault words of the unit (data points; any bit set = fault). Addresses as documented by the ha-lan-proxon project (MIT),
# found on a real unit. Some bits are known, harmless notices and are not counted as a fault.
FAULT_POINTS = ((0, 2), (0, 48), (0, 49), (0, 50), (0, 51), (1, 7), (2, 78), (2, 79), (2, 80), (3, 61))
# (the hot-water module's "change filter" bit is a maintenance reminder, not a fault: it is shown, but doesn't block anything)
TOLERATED_FAULT_BITS = {(0, 50): 64, (2, 79): 16, (3, 61): 1 << 14}


def fault_key(point: tuple[int, int]) -> str:
    return f"Fehlerwort{point[0]}_{point[1]}"


def active_faults(values: dict) -> dict[str, int]:
    """Fault words with bits set that count as a fault (key -> 16-bit word)."""
    out = {}
    for point in FAULT_POINTS:
        v = values.get(fault_key(point))
        if isinstance(v, (int, float)) and int(v) & 0xFFFF & ~TOLERATED_FAULT_BITS.get(point, 0):
            out[fault_key(point)] = int(v) & 0xFFFF
    return out


FILTER_INTERVAL_MONTHS = 6  # used when the unit doesn't report its filter lifetime
FILTER_LIFETIME_RANGE = (3, 8)  # months the unit's filter lifetime can be set to
HOURS_PER_MONTH = 24 * 30


def filter_months(values: dict) -> int:
    """The filter lifetime set at the unit (3-8 months), else the usual 6 months."""
    v = values.get("FilterStandzeit")
    if isinstance(v, (int, float)) and FILTER_LIFETIME_RANGE[0] <= v <= FILTER_LIFETIME_RANGE[1]:
        return int(v)
    return FILTER_INTERVAL_MONTHS


@dataclass(frozen=True)
class Reg:
    key: str
    set_point: bool  # True: set point list, False: data point list
    read: tuple[int, int]
    write: tuple[int, int] | None = None
    conv: str = "raw"  # raw | div10 | div100 | div1000 | bool | signed | x2 | u16x2 | text | water | t300
    length: int = 1  # number of consecutive addresses (text: 16-bit words, two characters each)


def _registers() -> list[Reg]:
    r = [
        Reg("Betriebsart", True, (0, 16), (0, 42)),
        Reg("GlobalKuehlungFreigabe", True, (0, 62), (0, 134), "bool"),
        Reg("Luefterstufe", True, (0, 22), (0, 54)),
        Reg("GrenzwertCO2", True, (0, 117), (0, 244)),
        Reg("GrenzwertFeuchte", True, (0, 118), (0, 246)),
        Reg("SollWassertemperatur", True, (7, 1), (1, 0), "div10"),
        Reg("E-Heizstab", True, (7, 2), (1, 1), "bool"),
        Reg("T300Betriebsart", True, (7, 3), (1, 2), "bool"),
        Reg("Soll-E-Heizstab-Temperatur", True, (7, 4), (1, 3), "div10"),
        Reg("LaufzeitFilter", True, (4, 2), None, "x2"),
        Reg("Betriebsstundenzaehler", True, (4, 0), None, "u16x2"),
        Reg("HasCO2", True, (0, 38), None, "bool"),
        Reg("Intensivlueftung", True, (0, 185), (0, 380), "bool"),
        Reg("IntensivlueftungsDauer", True, (0, 186), (0, 382)),
        Reg("IntensivlueftungsRestDauer", True, (0, 133)),
        Reg("NBE0MittelTemperatur", True, (0, 70), (0, 150), "div100"),
        Reg("NBE0PTC", True, (0, 187), (0, 384), "bool"),
        # which room panels are connected: two 16-bit words, bit order NBE2..NBE20, then NBE1
        Reg("NBEverbunden0", True, (1, 0)),
        Reg("NBEverbunden1", True, (1, 1)),
        Reg("NBE0Temperatur", False, (1, 113), None, "div100"),
        Reg("NBE0Status", False, (2, 4), None, "bool"),  # room is heating right now
        Reg("T1Zuluft", False, (1, 45), None, "div100"),
        Reg("T3Frischluft", False, (1, 48), None, "div100"),
        Reg("T4Fortluft", False, (1, 47), None, "div100"),
        Reg("T7Abluft", False, (1, 46), None, "div100"),
        Reg("DrehzahlZuluft", False, (0, 0)),
        Reg("DrehzahlAbluft", False, (0, 1)),
        Reg("DrehzahlKompressor", False, (1, 40)),
        Reg("CurrentCO2", False, (0, 21)),
        Reg("LuftfeuchteRel", False, (0, 22)),
        Reg("IstLuefterstufe", False, (1, 4)),
        Reg("Kuehlbetrieb4Wegeventil", False, (1, 73), None, "bool"),
        Reg("FirmwareVersion", False, (0, 5)),
        # hot-water heat pump (T300): (raw - 1000) / 10, 0 = no sensor
        Reg("WarmwasserIstTemperatur", False, (3, 14), None, "water"),
        Reg("T300VorVerdampfer", False, (3, 11), None, "t300"),
        Reg("T300Verdampfer", False, (3, 12), None, "t300"),
        Reg("T300Kompressor", False, (3, 15), None, "t300"),
        # clock of the unit (set point object 3): needed for the rules of the weekly schedule
        *[Reg(k, True, (3, 56 + i)) for i, k in enumerate(CLOCK_KEYS)],
        # weekly ventilation schedule switched on at the unit (read only)
        Reg("ZeitprogrammAktiv", True, (5, 106), None, "bool"),
        *[Reg(fault_key(p), False, p) for p in FAULT_POINTS],
        # Addresses below as documented by the ha-lan-proxon project (MIT), verified there on a real unit.
        Reg("FilterStandzeit", True, (0, 460)),  # filter lifetime set at the unit, months (3-8)
        Reg("Legionellenfunktion", True, (7, 26), (1, 25), "bool"),  # hot-water module: regular heating against legionella
        Reg("BedienpanelGesperrt", True, (0, 403), None, "bool"),  # the stored value is a code: only "locked or not" is kept
        Reg("PVFreigabe", True, (7, 11), None, "bool"),  # PV input of the hot-water module enabled
        *[Reg(f"Pruefwert_DP0_{n}", False, (0, n)) for n in PROBE_POINTS],
        # electrical power the unit draws (Modbus list: Power Total = PCB + FU, in tenths of a watt; checked on a real unit:
        # 60.9 W + 470.9 W = 531.8 W with the compressor running). The hot-water module isn't included.
        Reg("LeistungGesamt", False, (0, 25), None, "div10"),
        Reg("LeistungKompressor", False, (0, 20), None, "div10"),
        Reg("LeistungLueftung", False, (0, 19), None, "div10"),
        Reg("KompressorLeistung", False, (1, 21), None, "div100"),  # % of the compressor's power (Modbus 3x0171)
        Reg("HeizmodulRelais", False, (2, 4)),  # relays K1-K10 of the room heating module, one bit each (Modbus 3x0574)
        Reg("GeraeteTyp", True, (0, 18)),  # 0 heating only, 1 heating and cooling (Modbus 4x0018)
        # operating hour counters of the unit (set point object 4 = Modbus 467 + n, counting in 2-hour steps like the others)
        *[Reg(k, True, (4, n), None, "u16x2") for k, n in HOUR_COUNTERS.items()],
        # hot-water module: relays, and its own runtime counters in seconds (low word, high word; Modbus list 3x0847...)
        Reg("T300RelaisKompressor", False, (3, 24), None, "bool"),
        Reg("T300RelaisHeizstab", False, (3, 26), None, "bool"),
        Reg("T300StundenKompressor", False, (3, 47), None, "u32h", 2),
        Reg("T300StundenHeizstab", False, (3, 51), None, "u32h", 2),
        # night setback of the room temperature: its own time program at the unit (Modbus 614-619 = set point object 5, 107-112;
        # written like the weekly schedule to object 0, address 2 x Modbus + 10)
        Reg("NachtabsenkungStartH", True, (5, 107), (0, 1238)),
        Reg("NachtabsenkungStartM", True, (5, 108), (0, 1240)),
        Reg("NachtabsenkungEndeH", True, (5, 109), (0, 1242)),
        Reg("NachtabsenkungEndeM", True, (5, 110), (0, 1244)),
        Reg("NachtabsenkungTemperatur", True, (5, 111), (0, 1246), "div100"),
        Reg("NachtabsenkungAktiv", True, (5, 112), (0, 1248), "bool"),
        Reg("WarmwasserUntenTemperatur", False, (3, 13), None, "water"),
        Reg("PVSignalHeizstab", False, (3, 99), None, "bool"),
        Reg("PVSignalWaermepumpe", False, (3, 100), None, "bool"),
        Reg("Bypass", False, (1, 72), None, "bool"),
        Reg("Erdwaerme", False, (1, 70), None, "bool"),
        Reg("Magnetventil", False, (1, 71), None, "bool"),
        Reg("Schieberposition", False, (1, 9)),
        Reg("VentilHeizung", False, (1, 54)),
        Reg("VentilVorwaerme", False, (1, 55)),
        Reg("VentilKuehlung", False, (1, 53)),
        Reg("StatusKompressor", False, (1, 12)),
        Reg("StatusVentilatoren", False, (1, 2)),
        Reg("DruckVerdampfer", False, (1, 56), None, "div1000"),  # P14, bar
        Reg("T12VorKondensator", False, (1, 28), None, "div100"),
        Reg("T13Kompressor", False, (1, 30), None, "div100"),
        Reg("T14Sauggas", False, (1, 57), None, "div100"),
        Reg("T300Saugleitung", False, (3, 16), None, "t300"),
        Reg("T300LuefterDrehzahl", False, (3, 62)),
        Reg("FirmwareT300", False, (3, 81)),
    ]
    # room names are stored in the unit: ten 16-bit words per room (set point object 6, addresses 10n .. 10n+9)
    r.append(Reg("NBE0name", True, (6, 0), None, "text", 10))
    for n in range(1, ROOM_COUNT):
        r += _room_registers(n)
    return r


def _room_registers(n: int) -> list[Reg]:
    """Values of room panel n (n >= 1). Room names are stored in the unit: ten 16-bit words per room (set point object 6, addresses 10n .. 10n+9)."""
    return [
        Reg(f"NBE{n}name", True, (6, 10 * n), None, "text", 10),
        Reg(f"NBE{n}OffsetTemperatur", True, (1, 2 + n), (0, 434 + 2 * n), "signed"),
        Reg(f"NBE{n}MittelTemperatur", True, (1, 22 + n), (0, 474 + 2 * n)),
        Reg(f"NBE{n}PTC", True, (1, 42 + n), (0, 514 + 2 * n), "bool"),
        Reg(f"NBE{n}Temperatur", False, (2, 17 + 3 * n), None, "div10"),
        Reg(f"NBE{n}Status", False, (2, 15 + 3 * n), None, "bool"),
        # how the room stands against its target, as the panel's LED shows it: 6 too cold, 5 at target, 4 warmer
        # (Modbus list "NBE LEDsetpointlevel"; meaning found on a real unit by the ha-modbus-proxon project)
        Reg(f"NBE{n}LED", False, (2, 16 + 3 * n)),
    ]


def _schedule_registers() -> list[Reg]:
    """Weekly ventilation schedule: 7 days x 3 phases x 5 fields, field k = 15*day + 5*phase + f.
    Read from set point object 5 address 1+k, written to object 0 address 1026+2k (same as the original app)."""
    return [
        Reg(schedule_key(d, p, f), True, (5, 1 + schedule_index(d, p, f)), (0, 1026 + 2 * schedule_index(d, p, f)))
        for d in range(7) for p in range(SCHEDULE_PHASES) for f in range(len(SCHEDULE_FIELDS))
    ]


REGISTERS: list[Reg] = _registers() + _schedule_registers()
BY_KEY: dict[str, Reg] = {g.key: g for g in REGISTERS}
ROOM_REGISTERS: dict[int, list[Reg]] = {n: _room_registers(n) for n in range(1, ROOM_COUNT)}
_ROOM_KEYS = {g.key for regs in ROOM_REGISTERS.values() for g in regs}
SCHEDULE_REGISTERS: list[Reg] = _schedule_registers()
SCHEDULE_KEYS = frozenset(g.key for g in SCHEDULE_REGISTERS)
BASE_REGISTERS: list[Reg] = [g for g in REGISTERS if g.key not in _ROOM_KEYS and g.key not in SCHEDULE_KEYS]


def decode(conv: str, raw: float) -> float | None:
    """The device answers with signed 16-bit numbers."""
    if conv == "t300":
        return None if raw == 0 else round(raw - 1000) / 10
    if conv == "water":
        # (raw - 1000) / 10 as in the original; plain tenths accepted too (water is never below 0 °C, so the offset form is >= 1000)
        if raw == 0:
            return None
        return round(raw - 1000) / 10 if raw >= 1000 else raw / 10
    if conv == "div10":
        return raw / 10
    if conv == "div100":
        return raw / 100
    if conv == "div1000":
        return raw / 1000
    if conv == "bool":
        return 1.0 if raw else 0.0
    if conv == "x2":
        return raw * 2
    if conv == "u16x2":
        return (raw + 65536 if raw < 0 else raw) * 2
    return float(raw)


def encode(conv: str, value: float) -> int:
    """Values are written as unsigned 16-bit numbers."""
    if conv == "div10":
        v = round(value * 10)
    elif conv == "div100":
        v = round(value * 100)
    elif conv == "bool":
        v = 1 if value else 0
    else:
        v = round(value)
    return v % 65536


def read_requests(regs: list[Reg] | None = None) -> list[tuple[str, list[Reg]]]:
    regs = BASE_REGISTERS if regs is None else regs
    return [
        (QUERY_SET_READ, [g for g in regs if g.set_point]),
        (QUERY_DATA_READ, [g for g in regs if not g.set_point]),
    ]


def connected_rooms(values: dict) -> list[int]:
    """Room panels (n >= 1) the unit reports connected: two 16-bit words, bit order NBE2 .. NBE20, then NBE1."""
    if "NBEverbunden0" not in values or "NBEverbunden1" not in values:
        return list(FALLBACK_ROOMS)
    bits = (int(values["NBEverbunden0"]) & 0xFFFF) | ((int(values["NBEverbunden1"]) & 0xFFFF) << 16)
    return [n for n in range(1, ROOM_COUNT) if bits >> (19 if n == 1 else n - 2) & 1]


def list_request(regs: list[Reg]) -> dict:
    return {"list": [{"obj": g.read[0], "address": g.read[1] + k} for g in regs for k in range(g.length)]}


def decode_text(words: list[float]) -> str:
    """Room names: each 16-bit word holds two characters, first character in the high byte (the original's `string` helper)."""
    out = []
    for w in words:
        w = int(w) & 0xFFFF
        for b in (w >> 8, w & 0xFF):
            if b:
                out.append(chr(b))
    return "".join(out).strip()


def write_request(key: str, value: float) -> dict:
    g = BY_KEY[key]
    if g.write is None:
        raise ValueError(f"{key} is read-only")
    return {"list": [{"obj": g.write[0], "address": g.write[1], "value": encode(g.conv, value)}]}


def parse_values(regs: list[Reg], reply: dict) -> dict[str, float | str]:
    data = ((reply or {}).get("response") or {}).get("data") or []
    out: dict[str, float | str] = {}
    pos = 0
    for g in regs:
        items = data[pos:pos + g.length]
        pos += g.length
        nums: list[float] = []
        for item in items:
            v = item.get("value") if isinstance(item, dict) else None
            if isinstance(v, bool):
                v = int(v)
            if isinstance(v, (int, float)):
                nums.append(v)
        if len(nums) != g.length:
            continue
        if g.conv == "text":
            out[g.key] = decode_text(nums)
            continue
        if g.conv == "u32h":  # seconds in two 16-bit words (low, high) -> hours
            low, high = (int(n) & 0xFFFF for n in nums)
            out[g.key] = round(((high << 16) | low) / 3600, 1)
            continue
        d = decode(g.conv, nums[0])
        if d is not None:
            out[g.key] = d
    return out


def read_all(client, names: bool = True) -> dict[str, float | str]:
    """Read every value: two list queries for the unit, then two for the connected rooms (client: anything with invoke(query, request)).
    names=False leaves out the room names (they rarely change, see NameCache)."""
    out: dict[str, float | str] = {}
    times: list[float] = []
    if hasattr(client, "last_rtt"):
        client.last_rtt = None  # the client measures the time on the wire itself (without its pauses between packets)

    def ask(query: str, regs: list[Reg]) -> dict:
        t = time.monotonic()
        reply = client.invoke(query, list_request(regs))
        times.append(time.monotonic() - t)
        return reply

    base = BASE_REGISTERS if names else [g for g in BASE_REGISTERS if g.conv != "text"]
    for query, regs in read_requests(base):
        out.update(parse_values(regs, ask(query, regs)))
    # then only the rooms the unit reports connected (up to 20), so the queries stay small
    rooms = connected_rooms(out)
    room_regs = [g for n in rooms for g in ROOM_REGISTERS[n] if names or g.conv != "text"]
    for query, regs in read_requests(room_regs):
        if regs:
            out.update(parse_values(regs, ask(query, regs)))
    # response time of the unit: the quickest of these queries, in milliseconds
    rtt = getattr(client, "last_rtt", None)
    out["Antwortzeit"] = round((rtt if rtt is not None else min(times)) * 1000, 1)
    # derived values the original shows
    if "NBEverbunden0" in out and "NBEverbunden1" in out:
        for n in range(1, ROOM_COUNT):
            out[f"NBE{n}Verbunden"] = 1.0 if n in rooms else 0.0
    if (op := operation(out)) is not None:
        out["AktuellerBetrieb"] = op
    if (charge := water_charge(out)) is not None:
        out["WarmwasserLadezustand"] = charge
    if "LaufzeitFilter" in out:
        out["FilterRestStunden"] = max(0.0, filter_months(out) * HOURS_PER_MONTH - float(out["LaufzeitFilter"]))
    return out


def operation(values: dict) -> float | None:
    """0 ventilating, 1 heating, 2 cooling - from the compressor and the 4-way valve, like the status line of the original app.
    (The data point ha-lan-proxon documents for this turned out to stay 0 on a real unit while the compressor ran.)"""
    rpm = values.get("DrehzahlKompressor")
    mode = values.get("Betriebsart")
    if not isinstance(rpm, (int, float)) or (isinstance(mode, (int, float)) and int(mode) == MODE_OFF):
        return None
    if rpm > 0:
        return 2.0 if values.get("Kuehlbetrieb4Wegeventil") else 1.0
    return 0.0


COLD_WATER = 12.0  # °C of the water flowing into the tank, as assumed for the charge


def water_charge(values: dict) -> float | None:
    """How full the hot-water tank is (0-100 %): the middle and bottom sensors measured against cold water and the target.
    An estimate - the tank has no sensor at the top."""
    mid, bottom, target = values.get("WarmwasserIstTemperatur"), values.get("WarmwasserUntenTemperatur"), values.get("SollWassertemperatur")
    if not isinstance(mid, (int, float)) or not isinstance(bottom, (int, float)):
        return None
    target = float(target) if isinstance(target, (int, float)) and target > COLD_WATER + 5 else 50.0
    share = ((mid - COLD_WATER) + (bottom - COLD_WATER)) / (2 * (target - COLD_WATER))
    return float(round(min(1.0, max(0.0, share)) * 100))


MIN_RECOVERY_SPREAD = 5.0  # K between extract and outdoor air needed for a meaningful efficiency


def heat_recovery(values: dict) -> float | None:
    """Efficiency of the heat exchanger in %: how much of the difference between outdoor and extract air the supply air
    gains. Only meaningful while the heat pump is off and the bypass closed (otherwise the supply air is heated / bypassed)."""
    t_out, t_sup, t_ext = values.get("T3Frischluft"), values.get("T1Zuluft"), values.get("T7Abluft")
    if not isinstance(t_out, (int, float)) or not isinstance(t_sup, (int, float)) or not isinstance(t_ext, (int, float)):
        return None
    if values.get("DrehzahlKompressor") or values.get("Bypass") or int(values.get("Betriebsart", 0) or 0) == MODE_OFF:
        return None
    spread = t_ext - t_out
    if abs(spread) < MIN_RECOVERY_SPREAD:
        return None
    return float(round(min(1.0, max(0.0, (t_sup - t_out) / spread)) * 100))


# While the unit reports a fault, only harmless changes are written: switching something off, the unit off, the ventilation
# level and room temperatures. (Same idea as the write guard of the ha-lan-proxon project.)
_OFF_KEYS = {"Intensivlueftung", "E-Heizstab", "GlobalKuehlungFreigabe", "Legionellenfunktion", "T300Betriebsart", "Betriebsart",
             "NachtabsenkungAktiv"}
_HARMLESS_KEYS = {"Luefterstufe", "NBE0MittelTemperatur"}


def allowed_during_fault(key: str, value: float) -> bool:
    if key in _HARMLESS_KEYS or (key.startswith("NBE") and key.endswith("OffsetTemperatur")):
        return True
    return (key in _OFF_KEYS or (key.startswith("NBE") and key.endswith("PTC"))) and not value


class NameCache:
    """Reads the room names only every EVERY queries (and whenever a connected room has no name yet) - they are ten values
    per room and change about once in the life of a unit. The names from the last time are added in between."""

    EVERY = 30

    def __init__(self) -> None:
        self.names: dict[str, str] = {}
        self._count = 0

    def read(self, client) -> dict[str, float | str]:
        fresh = self._count % self.EVERY == 0 or not self.names
        self._count += 1
        out = read_all(client, names=fresh)
        if fresh:
            self.names = {k: v for k, v in out.items() if isinstance(v, str) and k.endswith("name")}
        else:
            out.update(self.names)
            if any(f"NBE{n}name" not in self.names for n in connected_rooms(out)):
                self._count = 0  # a newly connected room: names again next time
        return out


def write_value(client, key: str, value: float) -> None:
    client.invoke(QUERY_WRITE, write_request(key, value))


# ---- writing with read-back ----
# A write is only reported as done when the unit really holds the new value afterwards.

# values that change together with the written one and are read back as well
RELATED_KEYS: dict[str, list[str]] = {"Intensivlueftung": ["IntensivlueftungsRestDauer", "IntensivlueftungsDauer"]}


class WriteMismatch(Exception):
    """The unit did not take over the written value. `values` holds what it reports instead."""

    def __init__(self, key: str, wanted: float, got: float | None, values: dict) -> None:
        super().__init__(f"{key}: wanted {wanted}, the unit reports {got}")
        self.key, self.wanted, self.got, self.values = key, wanted, got, values


def expected_value(key: str, value: float) -> float:
    """What the unit will report after `value` was written (the value is rounded to the unit's resolution)."""
    g = BY_KEY[key]
    raw = encode(g.conv, value)
    if raw >= 32768:  # the unit answers with signed 16-bit numbers
        raw -= 65536
    out = decode(g.conv, raw)
    return float(out if out is not None else value)


def read_keys(client, keys: list[str]) -> dict[str, float | str]:
    """Read just these values."""
    regs = [BY_KEY[k] for k in dict.fromkeys(keys)]
    out: dict[str, float | str] = {}
    for query, group in ((QUERY_SET_READ, [g for g in regs if g.set_point]), (QUERY_DATA_READ, [g for g in regs if not g.set_point])):
        if group:
            out.update(parse_values(group, client.invoke(query, list_request(group))))
    return out


# The hot-water module (T300) takes over its values much more slowly than the ventilation part: it can take up to a minute
# (its operating mode up to a minute and a half). For these the read-back waits longer, and the same value is sent again
# twice in between (writing the same value again does no harm).
SLOW_WRITE_SECONDS: dict[str, float] = {
    "Legionellenfunktion": 60,
    "SollWassertemperatur": 60,
    "E-Heizstab": 60,
    "Soll-E-Heizstab-Temperatur": 60,
    "T300Betriebsart": 90,
}
# the unit takes a few seconds to take over schedule fields (also those of the night setback)
SLOW_WRITE_SECONDS.update({k: 10 for k in (
    "NachtabsenkungStartH", "NachtabsenkungStartM", "NachtabsenkungEndeH", "NachtabsenkungEndeM", "NachtabsenkungTemperatur",
    "NachtabsenkungAktiv",
)})
SLOW_WRITE_SECONDS.update({
    f"ZP{d}_{p}_{name}": 10
    for d in range(7) for p in range(SCHEDULE_PHASES) for name in SCHEDULE_FIELDS
})
SLOW_READ_INTERVAL = 2.0


def write_and_verify(
    client, key: str, value: float, *, attempts: int | None = None, delay: float | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, float | str]:
    """Write, then read the value back (a few times, the unit may need a moment). Returns the values read back;
    raises WriteMismatch if the unit still holds something else."""
    sleep = sleep or time.sleep
    slow = SLOW_WRITE_SECONDS.get(key)
    if delay is None:
        delay = SLOW_READ_INTERVAL if slow else 0.6
    if attempts is None:
        attempts = int(slow / delay) + 1 if slow else 3
    # slow values: send the same value again after a third and after two thirds of the waiting time
    rewrite_at = {attempts // 3, 2 * attempts // 3} - {0} if slow else set()
    write_value(client, key, value)
    want = expected_value(key, value)
    got: dict[str, float | str] = {}
    for i in range(attempts):
        got = read_keys(client, [key, *RELATED_KEYS.get(key, [])])
        have = got.get(key)
        if isinstance(have, (int, float)) and abs(have - want) < 0.006:
            return got
        if i < attempts - 1:
            if i + 1 in rewrite_at:
                write_value(client, key, value)
            sleep(delay)
    have = got.get(key)
    raise WriteMismatch(key, want, have if isinstance(have, (int, float)) else None, got)


def read_schedule(client) -> dict[str, float | str]:
    """Read the weekly schedule (105 values, in two queries). It changes rarely, so it is not part of every query."""
    out: dict[str, float | str] = {}
    for start in range(0, len(SCHEDULE_REGISTERS), 60):
        regs = SCHEDULE_REGISTERS[start:start + 60]
        out.update(parse_values(regs, client.invoke(QUERY_SET_READ, list_request(regs))))
    return out


def room_name_from_unit(values: dict, i: int) -> str | None:
    """The name stored in the unit for this room (None when empty)."""
    name = values.get(f"NBE{i}name")
    return name if isinstance(name, str) and name.strip() else None


def room_connected(values: dict, i: int) -> bool:
    """The living room panel always exists. The others only when the unit says so (bit field), like the original app's room list.
    If the unit's bit field isn't available, a room counts as connected when the unit holds a name for it."""
    if i == 0:
        return True
    flag = values.get(f"NBE{i}Verbunden")
    if flag is not None:
        return bool(flag)
    return room_name_from_unit(values, i) is not None


def room_target(values: dict, i: int) -> float | None:
    """Living room: its own target. Other rooms: their own base value (NBEnMittelTemperatur) + their own offset,
    exactly as the original's room screen shows it."""
    if i == 0:
        return values.get("NBE0MittelTemperatur")
    base = values.get(f"NBE{i}MittelTemperatur")
    if base is None:
        return None
    return base + (values.get(f"NBE{i}OffsetTemperatur") or 0)


def room_base(values: dict, i: int) -> float | None:
    """Value the ±3 °C limit of a room is measured from (its own base value)."""
    return values.get(f"NBE{i}MittelTemperatur")


LED_DEMAND = {6: "too_cold", 5: "at_target", 4: "warmer"}


def room_demand(values: dict, i: int) -> str | None:
    """Too cold / at target / warmer: from the room panel's LED level, for the central panel (no LED level) from its
    temperature against its target."""
    led = values.get(f"NBE{i}LED")
    if isinstance(led, (int, float)) and int(led) in LED_DEMAND:
        return LED_DEMAND[int(led)]
    temp, target = values.get(f"NBE{i}Temperatur"), room_target(values, i)
    if not isinstance(temp, (int, float)) or not isinstance(target, (int, float)):
        return None
    if temp < target - 0.3:
        return "too_cold"
    return "warmer" if temp > target + 0.3 else "at_target"


def room_heating(values: dict, i: int) -> bool:
    """The room's electric heating element is heating: released and the room too cold (as the original app shows it)."""
    return bool(values.get(f"NBE{i}PTC")) and room_demand(values, i) == "too_cold"


def element_state(values: dict, i: int) -> str | None:
    """The room's electric heating element: "off" (not released), "ready" (released, the room needs no heat) or "heating"
    (released and the room too cold - as the original app shows it; which relay really switches isn't known per room)."""
    if f"NBE{i}PTC" not in values:
        return None
    if not values.get(f"NBE{i}PTC"):
        return "off"
    return "heating" if room_heating(values, i) else "ready"


def heating_channels(values: dict) -> list[str]:
    """Relays K1-K10 of the room heating module that are switched on right now."""
    word = values.get("HeizmodulRelais")
    if not isinstance(word, (int, float)):
        return []
    return [f"K{b + 1}" for b in range(10) if int(word) >> b & 1]


def room_write(values: dict, i: int, target: float) -> tuple[str, float]:
    """Which value to write for a new room target. Other rooms store a whole-degree offset to their own base value."""
    if i == 0:
        return "NBE0MittelTemperatur", target
    base = values.get(f"NBE{i}MittelTemperatur", 20.0)
    return f"NBE{i}OffsetTemperatur", float(round(target - base))
