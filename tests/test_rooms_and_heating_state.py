"""More than five rooms, reading only connected rooms, and what the thermostats say the unit is doing."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.proxon_control import registers as R

from .test_integration import call, eid, no_entity, setup


def connect_room_6(device) -> None:
    """Like the real unit from the diagnostics: rooms NBE1-4 and NBE6 connected (bit field 23 / 8)."""
    device.raw[(True, 1, 0)] = 23  # NBE2, NBE3, NBE4, NBE6
    for n in (2, 3, 6):
        device.raw[(True, 1, 22 + n)] = 21  # base value
        device.raw[(True, 1, 2 + n)] = 1  # offset
        device.raw[(False, 2, 17 + 3 * n)] = 225  # 22.5 °C
    device.set_name(2, "Kinderzimmer")
    device.set_name(3, "Arbeitszimmer")
    device.set_name(6, "Gästezimmer")


def test_connected_rooms_follow_the_bit_field() -> None:
    assert R.connected_rooms({"NBEverbunden0": 23, "NBEverbunden1": 8}) == [1, 2, 3, 4, 6]
    assert R.connected_rooms({"NBEverbunden0": 0, "NBEverbunden1": 0}) == []
    assert R.connected_rooms({"NBEverbunden0": 0, "NBEverbunden1": 1 << 2}) == [20]  # bit 18 = word 2, bit 2
    assert R.connected_rooms({}) == [1, 2, 3, 4]  # no bit field: rooms of earlier versions


def test_only_connected_rooms_are_read(device) -> None:
    requests: list[dict] = []
    invoke = device.invoke

    def recording(query, request):
        requests.append((query, request))
        return invoke(query, request)

    device.invoke = recording
    values = R.read_all(device)
    # set points and data points are separate address spaces
    asked = {(i["obj"], i["address"]) for q, r in requests if q == R.QUERY_SET_READ for i in r["list"]}
    assert (1, 2 + 1) in asked and (1, 2 + 4) in asked  # offsets of rooms 1 and 4
    assert (1, 2 + 2) not in asked and (1, 2 + 6) not in asked  # rooms 2 and 6 are not connected
    assert "NBE2Temperatur" not in values
    assert max(len(r["list"]) for q, r in requests) < 120  # queries stay small


async def test_sixth_room_shows_up(hass: HomeAssistant, device) -> None:
    connect_room_6(device)
    await setup(hass)
    for n in (0, 1, 2, 3, 4, 6):
        assert not no_entity(hass, "climate", f"NBE{n}Thermostat"), n
        assert not no_entity(hass, "sensor", f"NBE{n}Temperatur"), n
    assert no_entity(hass, "climate", "NBE5Thermostat")
    guest = hass.states.get(eid(hass, "climate", "NBE6Thermostat"))
    assert "Gästezimmer" in guest.attributes["friendly_name"]
    assert guest.attributes["temperature"] == 22.0  # 21 + 1
    assert guest.attributes["current_temperature"] == 22.5
    await call(hass, "climate", "set_temperature", entity_id=eid(hass, "climate", "NBE6Thermostat"), temperature=23)
    assert device.writes[-1] == {"obj": 0, "address": 434 + 12, "value": 2}
    await call(hass, "climate", "set_hvac_mode", entity_id=eid(hass, "climate", "NBE6Thermostat"), hvac_mode="heat")
    assert device.writes[-1] == {"obj": 0, "address": 514 + 12, "value": 1}


async def test_heating_state_comes_from_the_compressor(hass: HomeAssistant, device) -> None:
    device.raw[(False, 1, 73)] = 0  # 4-way valve: heating
    await setup(hass)
    living = eid(hass, "climate", "NBE0Thermostat")
    assert hass.states.get(living).attributes["hvac_action"] == "heating"
    coordinator = hass.config_entries.async_entries("proxon_control")[0].runtime_data
    # compressor stopped: only ventilating - even though the room's own status value says 1 (as on the real unit)
    coordinator.async_set_updated_data({**coordinator.data, "DrehzahlKompressor": 0.0, "NBE1Status": 1.0})
    await hass.async_block_till_done()
    assert hass.states.get(living).attributes["hvac_action"] == "fan"
    assert hass.states.get(eid(hass, "climate", "NBE1Thermostat")).attributes["hvac_action"] == "fan"
    await call(hass, "select", "select_option", entity_id=eid(hass, "select", "Betriebsart"), option="off")
    assert hass.states.get(living).attributes["hvac_action"] == "off"
