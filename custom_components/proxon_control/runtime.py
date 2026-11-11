"""Runtime statistics of today: how often and how long the compressor, the hot-water compressor and the immersion heater ran.

Counted in Home Assistant from the queried values (the unit itself only keeps lifetime hour counters). Short-cycling
(the compressor starting very often) is an early sign of trouble. No Home Assistant imports.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

# a gap between two queries longer than this (Home Assistant stopped, unit not reachable) isn't counted as running time
MAX_GAP_SECONDS = 15 * 60


def _on(key: str, positive: bool = False) -> Callable[[dict], bool | None]:
    def check(values: dict) -> bool | None:
        v = values.get(key)
        if not isinstance(v, (int, float)):
            return None
        return v > 0 if positive else bool(v)
    return check


# name -> how to tell it is running
ITEMS: dict[str, Callable[[dict], bool | None]] = {
    "Kompressor": _on("DrehzahlKompressor", positive=True),
    "WarmwasserKompressor": _on("T300RelaisKompressor"),
    "Heizstab": _on("T300RelaisHeizstab"),
}


@dataclass
class Counter:
    day: str = ""
    starts: int = 0
    seconds: float = 0.0
    on: bool | None = None
    seen: str | None = None  # time of the last query (ISO)
    starts_yesterday: int | None = None
    hours_yesterday: float | None = None


class RuntimeTracker:
    def __init__(self) -> None:
        self.counters: dict[str, Counter] = {}

    def load(self, data: dict) -> None:
        for name, d in (data or {}).items():
            if name in ITEMS and isinstance(d, dict):
                self.counters[name] = Counter(**{k: v for k, v in d.items() if k in Counter.__dataclass_fields__})

    def dump(self) -> dict:
        return {name: vars(c) for name, c in self.counters.items()}

    def update(self, values: dict, now: datetime, max_gap: float = MAX_GAP_SECONDS) -> dict[str, float]:
        """Count this query (now: local time). Returns the values for today (starts, hours) and yesterday."""
        out: dict[str, float] = {}
        day = now.date().isoformat()
        for name, check in ITEMS.items():
            running = check(values)
            c = self.counters.setdefault(name, Counter(day=day))
            if running is None:
                c.on, c.seen = None, None
                continue
            last = datetime.fromisoformat(c.seen) if c.seen else None
            counted = bool(c.on) and last is not None and 0 < (now - last).total_seconds() <= max_gap
            since = last
            if c.day != day:
                midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                if counted and last is not None and last < midnight:  # running time before midnight still belongs to the old day
                    c.seconds += (midnight - last).total_seconds()
                    since = midnight
                self._new_day(c, day)
            if counted and since is not None:
                c.seconds += max(0.0, (now - since).total_seconds())
            if running and c.on is False:
                c.starts += 1
            c.on, c.seen = running, now.isoformat()
            out[f"{name}StartsHeute"] = float(c.starts)
            out[f"{name}LaufzeitHeute"] = round(c.seconds / 3600, 2)
            if c.starts_yesterday is not None:
                out[f"{name}StartsGestern"] = float(c.starts_yesterday)
                out[f"{name}LaufzeitGestern"] = float(c.hours_yesterday or 0.0)
        return out

    @staticmethod
    def _new_day(c: Counter, day: str) -> None:
        if c.day and c.day != day:
            c.starts_yesterday, c.hours_yesterday = c.starts, round(c.seconds / 3600, 2)
        c.day, c.starts, c.seconds = day, 0, 0.0
