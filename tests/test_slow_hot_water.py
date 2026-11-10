"""The hot-water module (T300) takes over values slowly: the read-back waits longer and sends the value again."""
from __future__ import annotations

import pytest

from homeassistant.core import HomeAssistant

from custom_components.proxon_control import registers as R

from .test_integration import call, eid, setup


def drop_first_writes(device, n: int) -> None:
    """The unit ignores the first `n` writes (as if the hot-water module was busy), then takes over values."""
    invoke = device.invoke
    state = {"left": n}

    def patched(query, request):
        if query == R.QUERY_WRITE and state["left"] > 0:
            state["left"] -= 1
            device.writes.append(request["list"][0])
            return {"response": {"status": 0}}
        return invoke(query, request)

    device.invoke = patched


def test_hot_water_gets_up_to_a_minute(device) -> None:
    device.apply_delay = 20  # shows up only after 20 reads (about 40 s)
    waits: list[float] = []
    got = R.write_and_verify(device, "SollWassertemperatur", 48, sleep=waits.append)
    assert got["SollWassertemperatur"] == 48.0
    assert set(waits) == {2.0}  # reads every 2 s


def test_hot_water_value_is_sent_again(device) -> None:
    drop_first_writes(device, 1)  # the first write gets lost
    got = R.write_and_verify(device, "SollWassertemperatur", 48, sleep=lambda s: None)
    assert got["SollWassertemperatur"] == 48.0
    assert [w["value"] for w in device.writes] == [480, 480]


def test_hot_water_gives_up_after_a_minute(device) -> None:
    device.ignore_writes = True
    reads = 0
    invoke = device.invoke

    def counting(query, request):
        nonlocal reads
        if query != R.QUERY_WRITE:
            reads += 1
        return invoke(query, request)

    device.invoke = counting
    waits: list[float] = []
    with pytest.raises(R.WriteMismatch) as err:
        R.write_and_verify(device, "SollWassertemperatur", 48, sleep=waits.append)
    assert err.value.got == 34.0
    assert sum(waits) == 60  # 31 reads, 2 s apart
    assert reads == 31
    assert len(device.writes) == 3  # first write plus two repeats


def test_operating_mode_of_the_hot_water_module_gets_longer(device) -> None:
    device.apply_delay = 40  # 80 s
    got = R.write_and_verify(device, "T300Betriebsart", 0, sleep=lambda s: None)
    assert got["T300Betriebsart"] == 0.0


def test_ventilation_values_stay_quick(device) -> None:
    device.ignore_writes = True
    waits: list[float] = []
    with pytest.raises(R.WriteMismatch):
        R.write_and_verify(device, "Luefterstufe", 3, sleep=waits.append)
    assert waits == [0.6, 0.6]
    assert len(device.writes) == 1  # no repeat for quick values


async def test_slow_hot_water_through_home_assistant(hass: HomeAssistant, device) -> None:
    await setup(hass)
    device.apply_delay = 10
    wh = eid(hass, "water_heater", "Warmwasser")
    await call(hass, "water_heater", "set_temperature", entity_id=wh, temperature=48)
    assert hass.states.get(wh).attributes["temperature"] == 48.0
    await call(hass, "number", "set_value", entity_id=eid(hass, "number", "SollWassertemperatur"), value=46)
    assert float(hass.states.get(eid(hass, "number", "SollWassertemperatur")).state) == 46.0
