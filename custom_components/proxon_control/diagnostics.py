"""Diagnostics download (Settings → Devices & services → Proxon Control → ⋮ → Download diagnostics).

Holds the raw values of the last query, so problems on other units or firmware versions can be looked at. The values
"Pruefwert_DP0_n" are data points from Proxon's Modbus list whose meaning over the network is still being checked.
Device ID, password, address of the bridge add-on and the room names are removed.
"""
from __future__ import annotations

import platform
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import ProxonConfigEntry
from .const import CONF_CONNECTION, CONF_DEVICE_ID, CONF_HOST, CONF_PASSWORD

REDACTED = "**REDACTED**"
TO_REDACT = {CONF_DEVICE_ID, CONF_PASSWORD, CONF_HOST}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ProxonConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    values = dict(coordinator.data or {})
    # room names are chosen by the user and may contain names of people
    for key in values:
        if key.endswith("name"):
            values[key] = REDACTED
    return {
        "entry": {
            "title": REDACTED,  # contains the Device ID
            "version": entry.version,
            "connection": entry.data.get(CONF_CONNECTION),
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "system": {"machine": platform.machine(), "system": platform.system()},
        "coordinator": {
            "update_interval_seconds": coordinator.update_interval.total_seconds() if coordinator.update_interval else None,
            "last_update_success": coordinator.last_update_success,
            "last_exception": repr(coordinator.last_exception) if coordinator.last_exception else None,
        },
        "values": dict(sorted(values.items())),
    }
