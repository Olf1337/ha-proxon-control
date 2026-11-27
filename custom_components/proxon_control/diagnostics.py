"""Diagnostics download (Settings → Devices & services → Proxon Control → ⋮ → Download diagnostics).

Holds the raw values of the last query, so problems on other units or firmware versions can be looked at. The values
"Pruefwert_DP0_n" are data points from Proxon's Modbus list whose meaning over the network is still being checked.
Device ID, password, the addresses of the unit and of the bridge add-on, the house photo and the room names are removed.
"""
from __future__ import annotations

import platform
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import ProxonConfigEntry
from .api import ProxonError
from .const import CONF_CONNECTION, CONF_DEVICE_ID, CONF_HOST, CONF_HOUSE_PHOTO, CONF_LOCAL_HOST, CONF_PASSWORD
from .registers import scan_sessions

REDACTED = "**REDACTED**"
# the unit's address in the home network is in the setup data or (changed later) in the options
TO_REDACT = {CONF_DEVICE_ID, CONF_PASSWORD, CONF_HOST, CONF_LOCAL_HOST, CONF_HOUSE_PHOTO}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ProxonConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    values: dict[str, Any] = dict(coordinator.data or {})
    # room names are chosen by the user and may contain names of people
    for key in values:
        if key.endswith("name"):
            values[key] = REDACTED
    return {
        "raw_setpoints": await _raw_points(hass, coordinator, data=False),
        "raw_datapoints": await _raw_points(hass, coordinator, data=True),
        "entry": {
            "title": REDACTED,  # contains the Device ID
            "version": entry.version,
            "connection": entry.data.get(CONF_CONNECTION),
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "system": {"machine": platform.machine(), "system": platform.system()},
        "coordinator": {
            "update_interval_seconds": coordinator.update_interval.total_seconds() if coordinator.update_interval else None,
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception) if coordinator.last_exception else None,
        },
        "values": dict(sorted(values.items())),
    }


async def _raw_points(hass: HomeAssistant, coordinator, data: bool) -> dict[str, Any]:
    """The unit's set points (or data points), raw ("object:address"), to find a setting by comparing two downloads - e.g.
    one with a panel's key lock off and one with it on. Read only. Not over the bridge add-on."""
    api = coordinator.api
    if not hasattr(api, "read_raw"):
        return {"note": "not available over the bridge add-on"}
    values: dict[str, int | None] = {}
    errors: list[str] = []
    for chunks in scan_sessions(data):
        try:
            values.update(await hass.async_add_executor_job(api.read_raw, chunks, data))
        except ProxonError as err:  # one session failed: the rest still helps
            errors.append(f"{chunks[0][0][0]}:{chunks[0][0][1]}: {err}")
    return {"values": values, "errors": errors}
