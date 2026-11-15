"""The dashboard's themes: "Proxon Bento" (rounded tiles, light and dark following the device; the look of the ready-made
dashboard) and "Proxon Glas" (frosted glass on a deep blue-violet gradient, to choose in the profile).

Home Assistant loads themes only from YAML files: configuration.yaml → `frontend: themes: !include_dir_merge_named themes`
(the default configuration has that line). The action "Install glass theme" writes the theme into that folder, reloads the
themes and switches the dashboard pictures to dark, so their texts read well on the dark glass. The dashboard's tabs name the
theme; as long as it isn't installed they simply keep the normal look.
"""
from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant

THEME_NAME = "Proxon Bento"
GLASS_THEME_NAME = "Proxon Glas"
THEME_FILE = "proxon_control.yaml"
THEME_YAML = """\
# Written by the Proxon Control integration (action "Install dashboard theme"); written anew when the action runs again.
# "Proxon Bento": rounded tiles in light and dark - Home Assistant takes the mode of the device (or the one chosen in the
# profile). "Proxon Glas": frosted glass on a dark gradient, to choose in the profile.
Proxon Bento:
  ha-card-border-radius: "22px"
  ha-card-border-width: "0px"
  ha-tile-border-radius: "18px"
  modes:
    light:
      # background: a light grey with a hint of green; tiles: white, a soft shadow
      lovelace-background: "#eceee9"
      primary-background-color: "#eceee9"
      secondary-background-color: "#f4f5f1"
      ha-card-background: "#ffffff"
      card-background-color: "#ffffff"
      ha-dialog-surface-background: "#ffffff"
      mdc-theme-surface: "#ffffff"
      ha-card-box-shadow: "0 1px 2px rgba(20, 24, 18, 0.05)"
      # texts and accents: near black, green for what is on, orange for heating
      primary-text-color: "#16181a"
      secondary-text-color: "#6b7069"
      disabled-text-color: "#a3a8a0"
      text-primary-color: "#ffffff"
      divider-color: "rgba(22, 24, 26, 0.07)"
      primary-color: "#3f8f22"
      accent-color: "#e8890c"
      state-icon-color: "#3f8f22"
      switch-checked-color: "#5fbf3a"
      state-climate-heat-color: "#e8890c"
      state-water_heater-heat_pump-color: "#e8890c"
      state-fan-on-color: "#3f8f22"
      state-fan-active-color: "#3f8f22"
      state-switch-on-color: "#3f8f22"
      state-select-active-color: "#3f8f22"
      input-fill-color: "#f1f3ee"
      app-header-background-color: "#eceee9"
      app-header-text-color: "#16181a"
      sidebar-background-color: "#f4f5f1"
      sidebar-text-color: "#16181a"
      sidebar-icon-color: "#6b7069"
      sidebar-selected-text-color: "#3f8f22"
      sidebar-selected-icon-color: "#3f8f22"
    dark:
      # background: graphite; tiles: a shade lighter, no shadow
      lovelace-background: "#101210"
      primary-background-color: "#101210"
      secondary-background-color: "#151815"
      ha-card-background: "#1b1e1b"
      card-background-color: "#1b1e1b"
      ha-dialog-surface-background: "#1b1e1b"
      mdc-theme-surface: "#1b1e1b"
      ha-card-box-shadow: "none"
      primary-text-color: "#eef1ea"
      secondary-text-color: "#9aa196"
      disabled-text-color: "#5c6259"
      text-primary-color: "#121412"
      divider-color: "rgba(238, 241, 234, 0.08)"
      primary-color: "#a6e36d"
      accent-color: "#ffab3d"
      state-icon-color: "#a6e36d"
      switch-checked-color: "#a6e36d"
      state-climate-heat-color: "#ffab3d"
      state-water_heater-heat_pump-color: "#ffab3d"
      state-fan-on-color: "#a6e36d"
      state-fan-active-color: "#a6e36d"
      state-switch-on-color: "#a6e36d"
      state-select-active-color: "#a6e36d"
      input-fill-color: "#262a25"
      app-header-background-color: "#101210"
      app-header-text-color: "#eef1ea"
      sidebar-background-color: "#151815"
      sidebar-text-color: "#eef1ea"
      sidebar-icon-color: "#9aa196"
      sidebar-selected-text-color: "#a6e36d"
      sidebar-selected-icon-color: "#a6e36d"
Proxon Glas:
  # background: deep blue to violet, a teal glow at the bottom left, a magenta glow at the top right
  lovelace-background: >-
    radial-gradient(circle at 12% 88%, rgba(28, 111, 134, 0.45), transparent 38%) fixed,
    radial-gradient(circle at 88% 10%, rgba(138, 42, 92, 0.5), transparent 36%) fixed,
    linear-gradient(135deg, #101a33 0%, #1b1733 55%, #3a1630 100%) fixed
  primary-background-color: "#121a31"
  secondary-background-color: "#1c2442"
  ha-card-background: "rgba(255, 255, 255, 0.07)"
  ha-card-backdrop-filter: "blur(18px) saturate(140%)"
  ha-card-border-color: "rgba(255, 255, 255, 0.14)"
  ha-card-border-width: "1px"
  ha-card-border-radius: "18px"
  ha-card-box-shadow: "0 8px 30px rgba(0, 0, 0, 0.22)"
  card-background-color: "#1a2240"
  ha-dialog-surface-background: "#1a2240"
  mdc-theme-surface: "#1a2240"
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
