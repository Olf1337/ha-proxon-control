"""Put the ready-made dashboard into Home Assistant: a dashboard "Proxon" in the sidebar, created on the first run and
written anew on every further run.

Home Assistant has no interface for integrations to create dashboards. The frontend creates them with the websocket
command "lovelace/dashboards/create"; its handler belongs to the dashboards collection, which is reached through that
command here (the same collection the frontend uses, so nothing gets out of step). Writing the views goes through the
dashboard's own save, like the frontend's raw configuration editor. Should a future version of Home Assistant change any
of this, the action says so and the dashboard can still be pasted by hand (the action's "paste only" option).
"""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

CREATE_COMMAND = "lovelace/dashboards/create"
ICON = "mdi:home-thermometer-outline"


class DashboardStoreError(Exception):
    """The dashboard couldn't be put into Home Assistant; the reason is a short key for the message."""


def _dashboards_collection(hass: HomeAssistant) -> Any:
    """The collection behind the frontend's "create dashboard", found through its websocket command (or None)."""
    handlers = hass.data.get("websocket_api") or {}
    handler = (handlers.get(CREATE_COMMAND) or (None,))[0]
    for _ in range(10):  # the command is the collection's method inside a few decorators
        if handler is None or hasattr(handler, "__self__"):
            break
        handler = getattr(handler, "__wrapped__", None)
    return getattr(getattr(handler, "__self__", None), "storage_collection", None)


async def async_store_dashboard(hass: HomeAssistant, url_path: str, title: str, config: dict[str, Any]) -> bool:
    """Write the dashboard at url_path (created first if it isn't there). Returns whether it was created."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA  # noqa: PLC0415 - only when the action runs
    except ImportError as err:
        raise DashboardStoreError("no_dashboards") from err
    lovelace = hass.data.get(LOVELACE_DATA)
    if lovelace is None:
        raise DashboardStoreError("no_dashboards")
    board = lovelace.dashboards.get(url_path)
    created = False
    if board is None:
        collection = _dashboards_collection(hass)
        if collection is None:
            raise DashboardStoreError("no_dashboards")
        await collection.async_create_item(
            {"url_path": url_path, "title": title, "icon": ICON, "show_in_sidebar": True, "require_admin": False, "mode": "storage"}
        )
        board, created = lovelace.dashboards.get(url_path), True
    if board is None:
        raise DashboardStoreError("no_dashboards")
    if getattr(board, "mode", None) != "storage":  # a dashboard of that name set up in YAML: not written over
        raise DashboardStoreError("yaml")
    await board.async_save(config)
    return created
