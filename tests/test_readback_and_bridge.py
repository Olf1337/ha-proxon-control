"""Writing with read-back: the rule itself, and the same behaviour through the add-on's local interface."""
from __future__ import annotations

import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from custom_components.proxon_control import registers as R
from custom_components.proxon_control.api import BridgeApi, WriteNotAccepted

from .conftest import FakeDevice  # noqa: F401  (documented here: the simulated unit)


def test_expected_values_follow_the_units_resolution() -> None:
    assert R.expected_value("NBE0MittelTemperatur", 20.456) == 20.46  # hundredths
    assert R.expected_value("SollWassertemperatur", 34.04) == 34.0  # tenths
    assert R.expected_value("NBE4OffsetTemperatur", -1) == -1.0  # signed
    assert R.expected_value("Intensivlueftung", 5) == 1.0  # on/off


def test_write_and_verify_returns_what_the_unit_holds(device) -> None:
    got = R.write_and_verify(device, "Luefterstufe", 3)
    assert got == {"Luefterstufe": 3.0}


def test_boost_reads_back_the_related_values(device) -> None:
    got = R.write_and_verify(device, "Intensivlueftung", 1)
    assert set(got) == {"Intensivlueftung", "IntensivlueftungsRestDauer", "IntensivlueftungsDauer"}


def test_a_slow_unit_is_read_again(device) -> None:
    device.apply_delay = 2
    assert R.write_and_verify(device, "GrenzwertCO2", 900, attempts=4) == {"GrenzwertCO2": 900.0}


def test_a_value_that_is_not_taken_is_reported_with_what_the_unit_holds(device) -> None:
    device.ignore_writes = True
    with pytest.raises(R.WriteMismatch) as err:
        R.write_and_verify(device, "Luefterstufe", 4)
    assert (err.value.key, err.value.wanted, err.value.got, err.value.values) == ("Luefterstufe", 4.0, 2.0, {"Luefterstufe": 2.0})


@pytest.fixture
def bridge_api(device, socket_enabled):  # a local port on this computer only
    """The add-on's own code, talking to the simulated unit, served on a local port."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "proxon_bridge"))
    try:
        import bridge as addon  # noqa: PLC0415 - the add-on's module, not part of the integration
    finally:
        sys.path.pop(0)
    b = addon.Bridge("abc123", "pw")
    b.client = device
    b.poll()
    server = ThreadingHTTPServer(("127.0.0.1", 0), addon.make_handler(b))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield BridgeApi("127.0.0.1", server.server_address[1])
    finally:
        server.shutdown()
        server.server_close()


def test_bridge_write_is_verified_too(bridge_api, device) -> None:
    assert bridge_api.read()["Luefterstufe"] == 2.0
    got = bridge_api.write("Luefterstufe", 3)
    assert got == {"Luefterstufe": 3.0}
    assert bridge_api.read()["Luefterstufe"] == 3.0
    assert bridge_api.read()["NBE0name"] == "Wohnzimmer"  # text values survive the trip


def test_bridge_reports_a_value_the_unit_does_not_take(bridge_api, device) -> None:
    device.ignore_writes = True
    with pytest.raises(WriteNotAccepted) as err:
        bridge_api.write("Luefterstufe", 4)
    assert (err.value.key, err.value.wanted, err.value.got) == ("Luefterstufe", 4.0, 2.0)
    assert err.value.values == {"Luefterstufe": 2.0}


def test_bridge_includes_the_weekly_schedule(bridge_api, device) -> None:
    values = bridge_api.read()
    assert values["ZP1_0_start_h"] == 6.0 and values["ZP1_1_level"] == 3.0
    assert bridge_api.read_schedule() == {}  # the add-on reads the schedule itself and includes it in /values
    bridge_api.write("ZP1_0_level", 4)
    assert bridge_api.read()["ZP1_0_level"] == 4.0  # written schedule values stay in the add-on's copy
