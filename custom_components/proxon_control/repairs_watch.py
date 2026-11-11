"""Notices under Settings → Repairs: filter change due soon, a fault of the unit, and a unit clock that is off.

They appear and disappear by themselves with the unit's values; there is nothing to "fix" in Home Assistant.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .registers import active_faults, t300_fault_texts

# same limit as the binary sensor "Filter change soon" (30 days)
FILTER_WARN_HOURS = 30 * 24
# the unit's clock can only be set at the unit (or in the app); the weekly schedule runs on it
CLOCK_WARN_MINUTES = 10
# a compressor starting this often a day is short-cycling (an inverter heat pump normally runs long and steadily)
CYCLING_STARTS_PER_DAY = 30


def _issue_ids(entry: ConfigEntry) -> tuple[str, str, str, str]:
    return (f"filter_change_{entry.entry_id}", f"unit_fault_{entry.entry_id}", f"clock_drift_{entry.entry_id}",
            f"compressor_cycling_{entry.entry_id}")


def _fault_words(hass: HomeAssistant, data: dict, faults: dict[str, int]) -> str:
    words = ", ".join(f"{k} = 0x{v:04X}" for k, v in faults.items())
    if texts := t300_fault_texts(data, hass.config.language):
        hot_water = "Warmwasser-Modul" if (hass.config.language or "").startswith("de") else "hot-water module"
        words += f"; {hot_water}: " + ", ".join(texts)
    return words


@callback
def update_issues(hass: HomeAssistant, entry: ConfigEntry, data: dict | None) -> None:
    filter_id, fault_id, clock_id, cycling_id = _issue_ids(entry)
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
            translation_placeholders={"words": _fault_words(hass, data, faults)},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, fault_id)
    drift = data.get("UhrAbweichung")
    if isinstance(drift, (int, float)) and abs(drift) >= CLOCK_WARN_MINUTES:
        ir.async_create_issue(
            hass, DOMAIN, clock_id, is_fixable=False, is_persistent=False, severity=ir.IssueSeverity.WARNING,
            translation_key="clock_drift",
            translation_placeholders={"minutes": str(abs(int(drift))), "direction": "+" if drift > 0 else "-"},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, clock_id)
    starts = data.get("KompressorStartsHeute")
    if isinstance(starts, (int, float)) and starts >= CYCLING_STARTS_PER_DAY:
        ir.async_create_issue(
            hass, DOMAIN, cycling_id, is_fixable=False, is_persistent=False, severity=ir.IssueSeverity.WARNING,
            translation_key="compressor_cycling", translation_placeholders={"starts": str(int(starts))},
        )
    elif isinstance(starts, (int, float)):
        ir.async_delete_issue(hass, DOMAIN, cycling_id)


@callback
def remove_issues(hass: HomeAssistant, entry: ConfigEntry) -> None:
    for issue_id in _issue_ids(entry):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
