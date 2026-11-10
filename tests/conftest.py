"""Test helpers: a simulated Proxon unit that answers like the real device (signed 16-bit values)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from custom_components.proxon_control import registers as R

RAW_DEFAULT = {
    "Betriebsart": 3, "GlobalKuehlungFreigabe": 0, "Luefterstufe": 2, "GrenzwertCO2": 800, "GrenzwertFeuchte": 30,
    "SollWassertemperatur": 340, "E-Heizstab": 0, "T300Betriebsart": 1, "Soll-E-Heizstab-Temperatur": 560,
    "LaufzeitFilter": 2100, "Betriebsstundenzaehler": 500, "HasCO2": 1, "Intensivlueftung": 0, "IntensivlueftungsDauer": 15,
    "IntensivlueftungsRestDauer": 0, "NBE0MittelTemperatur": 2000, "NBE0PTC": 0, "NBE0Temperatur": 2250, "NBE0Status": 0, "T1Zuluft": 4600,
    "T3Frischluft": 1750, "T4Fortluft": -9, "T7Abluft": 2220, "DrehzahlZuluft": 2760, "DrehzahlAbluft": 2788,
    "DrehzahlKompressor": 4010, "CurrentCO2": 650, "LuftfeuchteRel": 45, "IstLuefterstufe": 2, "Kuehlbetrieb4Wegeventil": 1,
    "FirmwareVersion": 9936, "WarmwasserIstTemperatur": 1360, "T300VorVerdampfer": 949, "T300Verdampfer": 953,
    "T300Kompressor": 1287,
    # rooms 1 (Schlafzimmer) and 4 (Bad) connected: NBE4 -> bit 2 of word 0, NBE1 -> bit 19 (bit 3 of word 1)
    "NBEverbunden0": 4, "NBEverbunden1": 8,
    "NBE1OffsetTemperatur": 2, "NBE1MittelTemperatur": 20, "NBE1PTC": 1, "NBE1Temperatur": 210, "NBE1Status": 1,
    "NBE4OffsetTemperatur": -1, "NBE4MittelTemperatur": 20, "NBE4PTC": 1, "NBE4Temperatur": 190, "NBE4Status": 0,
}


class FakeDevice:
    """Answers setpointReadListValue / datapointReadListValue / setpointWriteValue."""

    def __init__(self) -> None:
        # set points and data points are separate address spaces on the device
        self.raw = {(R.BY_KEY[k].set_point, *R.BY_KEY[k].read): v for k, v in RAW_DEFAULT.items()}
        # room names are stored in the unit as text (two characters per 16-bit word)
        for n, name in {0: "Wohnzimmer", 1: "Schlafzimmer", 4: "Bad"}.items():
            self.set_name(n, name)
        self.writes: list[dict] = []
        self.ignore_writes = False  # simulates a unit that doesn't take over written values
        self.apply_delay = 0  # number of reads before a written value shows up (a unit that needs a moment)
        self._pending: list[list] = []

    def set_name(self, n: int, name: str) -> None:
        data = name.encode("latin-1").ljust(20, b"\0")
        for k in range(10):
            w = data[2 * k] * 256 + data[2 * k + 1]
            self.raw[(True, 6, 10 * n + k)] = w - 65536 if w >= 32768 else w  # the device answers signed 16-bit numbers

    def invoke(self, query: str, request: dict) -> dict:
        if query == R.QUERY_WRITE:
            item = request["list"][0]
            self.writes.append(item)
            if not self.ignore_writes:
                g = next(g for g in R.REGISTERS if g.write == (item["obj"], item["address"]))
                v = item["value"]
                self._pending.append([self.apply_delay, (True, *g.read), v - 65536 if v >= 32768 else v])
            return {"response": {"status": 0}}
        for p in list(self._pending):  # written values show up after `apply_delay` reads
            if p[0] <= 0:
                self.raw[p[1]] = p[2]
                self._pending.remove(p)
            else:
                p[0] -= 1
        sp = query == R.QUERY_SET_READ
        return {"response": {"data": [{"value": self.raw.get((sp, i["obj"], i["address"]), 0)} for i in request["list"]]}}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def no_waiting():
    """The read-back after a write waits a moment between attempts; not in tests."""
    with patch.object(R, "time", SimpleNamespace(sleep=lambda s: None)):
        yield


@pytest.fixture
def device():
    dev = FakeDevice()
    with patch("custom_components.proxon_control.api.DirectApi._call", lambda self, fn: fn(dev)), \
         patch("custom_components.proxon_control.api.DirectApi.close", lambda self: None), \
         patch("custom_components.proxon_control.config_flow.library_supported", return_value=True):
        yield dev
