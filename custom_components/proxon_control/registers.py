"""Values of the ventilation unit: object/address numbers and conversions (see app/MECHANICS.md).

No Home Assistant imports: the bridge add-on uses this file too.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

QUERY_SET_READ = "setpointReadListValue"
QUERY_DATA_READ = "datapointReadListValue"
QUERY_WRITE = "setpointWriteValue"

# room panels: NBE0 (living room, always there) and NBE1 .. NBE20, as far as the unit reports them connected
ROOM_COUNT = 21
# rooms assumed when a unit doesn't report its connected-rooms bit field (behaviour of earlier versions)
FALLBACK_ROOMS = range(1, 5)

# operating modes (Betriebsart)
MODE_OFF, MODE_SUMMER, MODE_WINTER, MODE_COMFORT, MODE_HOLIDAY = 0, 1, 2, 3, 5
MODE_KEYS = {MODE_OFF: "off", MODE_SUMMER: "summer", MODE_WINTER: "winter", MODE_COMFORT: "eco_comfort", MODE_HOLIDAY: "holiday"}
# the original's mode menu offers these (holiday is only shown)
MODE_CHOICES = [MODE_COMFORT, MODE_WINTER, MODE_SUMMER, MODE_OFF]

# clock of the unit: summer time flag, minute, hour, ISO weekday (1 = Monday), day, month, year (two digits)
CLOCK_KEYS = ("UhrSommerzeit", "UhrMinute", "UhrStunde", "UhrWochentag", "UhrTag", "UhrMonat", "UhrJahr")

# weekly ventilation schedule
SCHEDULE_PHASES = 3
SCHEDULE_FIELDS = ("start_h", "start_m", "end_h", "end_m", "level")  # level 0 = phase not active, 1..4


def schedule_index(day: int, phase: int, field: int) -> int:
    return 15 * day + 5 * phase + field


def schedule_key(day: int, phase: int, field: int) -> str:
    return f"ZP{day}_{phase}_{SCHEDULE_FIELDS[field]}"


FILTER_INTERVAL_MONTHS = 6
HOURS_PER_MONTH = 24 * 30


@dataclass(frozen=True)
class Reg:
    key: str
    set_point: bool  # True: set point list, False: data point list
    read: tuple[int, int]
    write: tuple[int, int] | None = None
    conv: str = "raw"  # raw | div10 | div100 | bool | signed | x2 | u16x2 | text
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
        Reg("IntensivlueftungsDauer", True, (0, 186)),
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
        d = decode(g.conv, nums[0])
        if d is not None:
            out[g.key] = d
    return out


def read_all(client) -> dict[str, float | str]:
    """Read every value: two list queries for the unit, then two for the connected rooms (client: anything with invoke(query, request))."""
    out: dict[str, float | str] = {}
    for query, regs in read_requests():
        out.update(parse_values(regs, client.invoke(query, list_request(regs))))
    # then only the rooms the unit reports connected (up to 20), so the queries stay small
    rooms = connected_rooms(out)
    room_regs = [g for n in rooms for g in ROOM_REGISTERS[n]]
    for query, regs in read_requests(room_regs):
        if regs:
            out.update(parse_values(regs, client.invoke(query, list_request(regs))))
    # derived values the original shows
    if "NBEverbunden0" in out and "NBEverbunden1" in out:
        for n in range(1, ROOM_COUNT):
            out[f"NBE{n}Verbunden"] = 1.0 if n in rooms else 0.0
    if "LaufzeitFilter" in out:
        out["FilterRestStunden"] = max(0.0, FILTER_INTERVAL_MONTHS * HOURS_PER_MONTH - out["LaufzeitFilter"])
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
    "SollWassertemperatur": 60,
    "E-Heizstab": 60,
    "Soll-E-Heizstab-Temperatur": 60,
    "T300Betriebsart": 90,
}
# the unit takes a few seconds to take over schedule fields
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


def room_write(values: dict, i: int, target: float) -> tuple[str, float]:
    """Which value to write for a new room target. Other rooms store a whole-degree offset to their own base value."""
    if i == 0:
        return "NBE0MittelTemperatur", target
    base = values.get(f"NBE{i}MittelTemperatur", 20.0)
    return f"NBE{i}OffsetTemperatur", float(round(target - base))
