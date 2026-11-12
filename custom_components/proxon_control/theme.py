"""The "Proxon Glas" theme: frosted-glass cards on a deep blue-violet gradient, the look of the ready-made dashboard.

Home Assistant loads themes only from YAML files: configuration.yaml → `frontend: themes: !include_dir_merge_named themes`
(the default configuration has that line). The action "Install glass theme" writes the theme into that folder, reloads the
themes and switches the dashboard pictures to dark, so their texts read well on the dark glass. The dashboard's tabs name the
theme; as long as it isn't installed they simply keep the normal look.
"""
from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant

THEME_NAME = "Proxon Glas"
THEME_FILE = "proxon_control.yaml"
THEME_YAML = """\
# Written by the Proxon Control integration (action "Install glass theme"); written anew when the action runs again.
Proxon Glas:
  # background: deep blue to violet, a teal glow at the bottom left, a magenta glow at the top right
  lovelace-background: >-
    radial-gradient(circle at 12% 88%, rgba(28, 111, 134, 0.45), transparent 38%) fixed,
    radial-gradient(circle at 88% 10%, rgba(138, 42, 92, 0.5), transparent 36%) fixed,
    linear-gradient(135deg, #101a33 0%, #1b1733 55%, #3a1630 100%) fixed
  primary-background-color: "#121a31"
  secondary-background-color: "#1c2442"
  # cards: frosted glass
  ha-card-background: "rgba(255, 255, 255, 0.07)"
  ha-card-backdrop-filter: "blur(18px) saturate(140%)"
  ha-card-border-color: "rgba(255, 255, 255, 0.14)"
  ha-card-border-width: "1px"
  ha-card-border-radius: "18px"
  ha-card-box-shadow: "0 8px 30px rgba(0, 0, 0, 0.22)"
  # dialogs and menus stay solid
  card-background-color: "#1a2240"
  ha-dialog-surface-background: "#1a2240"
  mdc-theme-surface: "#1a2240"
  # texts and accents
  primary-text-color: "#f3f5ff"
  secondary-text-color: "#aab3d6"
  disabled-text-color: "#6f789c"
  text-primary-color: "#ffffff"
  divider-color: "rgba(255, 255, 255, 0.12)"
  primary-color: "#7fe0d8"
  accent-color: "#f6b27a"
  state-icon-color: "#d5dbf5"
  paper-item-icon-color: "#d5dbf5"
  switch-checked-color: "#7fe0d8"
  input-fill-color: "rgba(255, 255, 255, 0.06)"
  input-ink-color: "#f3f5ff"
  input-label-ink-color: "#aab3d6"
  # header and sidebar (when the theme is chosen for the whole device, e.g. a wall tablet)
  app-header-background-color: "#121a31"
  app-header-text-color: "#f3f5ff"
  sidebar-background-color: "#111830"
  sidebar-text-color: "#d5dbf5"
  sidebar-icon-color: "#aab3d6"
  sidebar-selected-text-color: "#7fe0d8"
  sidebar-selected-icon-color: "#7fe0d8"
"""


def _write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(THEME_YAML, encoding="utf-8")


def theme_names(hass: HomeAssistant) -> list[str]:
    """The themes Home Assistant knows (its frontend's list; older versions only keep them in hass.data)."""
    from homeassistant.components import frontend  # noqa: PLC0415 - loaded with Home Assistant, not needed before

    names = getattr(frontend, "async_get_theme_names", None)
    return list(names(hass)) if names else sorted(hass.data.get("frontend_themes", {}))


async def async_install_theme(hass: HomeAssistant) -> bool:
    """Write the theme into the themes folder and reload the themes. Returns whether Home Assistant knows it now (it
    doesn't when configuration.yaml doesn't load the themes folder)."""
    await hass.async_add_executor_job(_write, Path(hass.config.path("themes", THEME_FILE)))
    if hass.services.has_service("frontend", "reload_themes"):
        await hass.services.async_call("frontend", "reload_themes", blocking=True)
    return THEME_NAME in theme_names(hass)
