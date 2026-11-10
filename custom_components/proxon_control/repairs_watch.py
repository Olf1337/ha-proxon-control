"""Notices under Settings → Repairs: filter change due soon, and a fault of the unit.

They appear and disappear by themselves with the unit's values; there is nothing to "fix" in Home Assistant.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .registers import active_faults

# same limit as the binary sensor "Filter change soon" (30 days)
FILTER_WARN_HOURS = 30 * 24


def _issue_ids(entry: ConfigEntry) -> tuple[str, str]:
    return f"filter_change_{entry.entry_id}", f"unit_fault_{entry.entry_id}"


@callback
def update_issues(hass: HomeAssistant, entry: ConfigEntry, data: dict | None) -> None:
    filter_id, fault_id = _issue_ids(entry)
    data = data or {}
    hours = data.get("FilterRestStunden")
    if isinstance(hours, (int, float)) and hours <= FILTER_WARN_HOURS:
        ir.async_create_issue(
            hass, DOMAIN, filter_id, is_fixable=False, is_persistent=False, severity=ir.IssueSeverity.WARNING,
            translation_key="filter_change", translation_placeholders={"days": str(round(hours / 24))},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, filter_id)
    faults = active_faults(data)
    if faults:
        ir.async_create_issue(
            hass, DOMAIN, fault_id, is_fixable=False, is_persistent=False, severity=ir.IssueSeverity.ERROR,
            translation_key="unit_fault",
            translation_placeholders={"words": ", ".join(f"{k} = 0x{v:04X}" for k, v in faults.items())},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, fault_id)


@callback
def remove_issues(hass: HomeAssistant, entry: ConfigEntry) -> None:
    for issue_id in _issue_ids(entry):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
