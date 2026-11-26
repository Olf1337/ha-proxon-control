"""The "Proxon" page in the sidebar: our own interface (frontend/proxon-panel.js), drawn in the browser from the live
entities, with the unit's air paths, hot water and every room. Registered when the integration starts, refreshed on every
start (entity IDs and rooms may have changed), removed when the unit's entry goes away. One page for the first unit; a
second unit keeps its ready-made dashboard.

The page gets as its configuration the entity IDs of this unit (by their unique-id suffix, like the ready-made dashboard)
and its rooms with their floor; all values come live from Home Assistant, and everything it changes goes through the
normal actions of these entities.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import CONF_FIXED_PRICE, CONF_PANEL_LOOK, DEFAULT_PANEL_LOOK, DOMAIN
from .dashboard import entity_ids
from .entity import house_rooms, room_floors

_LOGGER = logging.getLogger(__name__)

PANEL_PATH = "proxon"
STATIC_URL = "/proxon_control_static"
COMPONENT = "proxon-panel"
FRONTEND_DIR = Path(__file__).parent / "frontend"
_OWNER = f"{DOMAIN}_panel_owner"
_STATIC = f"{DOMAIN}_panel_static"


def panel_config(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coordinator = getattr(entry, "runtime_data", None)
    data: dict = getattr(coordinator, "data", None) or {}
    rooms = house_rooms(data)
    floors = room_floors(entry.options, data, rooms)
    return {
        "entities": entity_ids(hass, entry),
        "rooms": [{"n": i, "floor": f} for i, f in zip(rooms, floors)],
        "device_id": getattr(coordinator, "device_id", None),  # for "open the device in Home Assistant"
        # a fixed tariff (ct/kWh): the costs of every period are worked out from the consumption (the cost sensors only count
        # from when a price was set)
        "price": entry.options.get(CONF_FIXED_PRICE),
        "look": entry.options.get(CONF_PANEL_LOOK, DEFAULT_PANEL_LOOK),  # liquid glass, soft or tile wall
        "static": STATIC_URL,  # the page's own files (the tile wall's font)
    }


async def async_register(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Show the page in the sidebar (only where the web interface runs; the first unit owns it)."""
    if "frontend" not in hass.config.components or hass.http is None:
        return
    owner = hass.data.get(_OWNER)
    if owner and owner != entry.entry_id and hass.config_entries.async_get_entry(owner):
        return
    from homeassistant.components import frontend, panel_custom

    if not hass.data.get(_STATIC):  # a static path can be registered only once per run of Home Assistant
        await _async_serve_files(hass)
        hass.data[_STATIC] = True
    version = (await async_get_integration(hass, DOMAIN)).version
    # the script's address carries a fingerprint of its content: after an update the browser loads the new script instead
    # of one it kept (the version alone isn't enough when files change without a new version, or a cache holds on)
    fingerprint = await hass.async_add_executor_job(_fingerprint)
    frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
    await panel_custom.async_register_panel(
        hass, frontend_url_path=PANEL_PATH, webcomponent_name=COMPONENT, sidebar_title="Proxon",
        sidebar_icon="mdi:home-thermometer-outline", module_url=f"{STATIC_URL}/{COMPONENT}.js?v={version}-{fingerprint}",
        config={**panel_config(hass, entry), "version": version}, require_admin=False, handle_safe_area=True,
    )
    hass.data[_OWNER] = entry.entry_id
    # the ready-made dashboard was called "Proxon" too: renamed, so the sidebar doesn't show the name twice
    from .dashboard_store import OLD_TITLE, TITLE, async_retitle
    from .services import DASHBOARD_URL

    await async_retitle(hass, DASHBOARD_URL, TITLE, only_from=OLD_TITLE)
    async_dashboard_notice(hass)


DEPRECATED_ISSUE = "dashboard_deprecated"


def async_dashboard_notice(hass: HomeAssistant) -> None:
    """The ready-made dashboard is deprecated (the page "Proxon" replaces it; it goes in 2.0): a notice under Repairs while
    one exists, gone when it was deleted."""
    from homeassistant.helpers import issue_registry as ir

    from .dashboard_store import stored_url_paths
    from .services import DASHBOARD_URL

    urls = [u for u in stored_url_paths(hass) if u == DASHBOARD_URL or u.startswith(f"{DASHBOARD_URL}-")]
    if urls:
        ir.async_create_issue(hass, DOMAIN, DEPRECATED_ISSUE, is_fixable=False, is_persistent=False, severity=ir.IssueSeverity.WARNING,
                              translation_key=DEPRECATED_ISSUE, translation_placeholders={"url": f"/{urls[0]}"},
                              learn_more_url="https://github.com/Olf1337/ha-proxon-control#die-seite-proxon")
    else:
        ir.async_delete_issue(hass, DOMAIN, DEPRECATED_ISSUE)


def _fingerprint() -> str:
    return hashlib.sha256((FRONTEND_DIR / f"{COMPONENT}.js").read_bytes()).hexdigest()[:10]


async def _async_serve_files(hass: HomeAssistant) -> None:
    """The page's script, served by Home Assistant's web server."""
    from homeassistant.components.http import StaticPathConfig

    await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=False)])


def async_unregister(hass: HomeAssistant, entry: ConfigEntry) -> None:
    if hass.data.get(_OWNER) != entry.entry_id:
        return
    hass.data.pop(_OWNER, None)
    if "frontend" in hass.config.components:
        from homeassistant.components import frontend

        frontend.async_remove_panel(hass, PANEL_PATH, warn_if_unknown=False)
