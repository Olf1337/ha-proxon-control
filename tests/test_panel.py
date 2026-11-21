"""The "Proxon" page in the sidebar: registered with this unit's entities and rooms, removed with the entry."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.core import HomeAssistant

from custom_components.proxon_control import panel as P

from .test_integration import eid, setup


async def test_panel_config(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    config = P.panel_config(hass, entry)
    entities = config["entities"]
    assert entities["T1Zuluft"] == eid(hass, "sensor", "T1Zuluft")
    assert entities["Intensivlueftung"] == eid(hass, "switch", "Intensivlueftung")
    assert entities["NBE4Thermostat"] == eid(hass, "climate", "NBE4Thermostat")
    assert entities["Urlaubsmodus"] == eid(hass, "switch", "Urlaubsmodus")
    # rooms with their floor: living room and bath downstairs, bedroom upstairs (guessed from the names)
    assert config["rooms"] == [{"n": 0, "floor": 0}, {"n": 1, "floor": 1}, {"n": 4, "floor": 0}]
    assert config["device_id"] == entry.runtime_data.device_id and config["device_id"]
    assert config["price"] is None  # no fixed tariff: costs from the cost sensors


async def test_panel_registered_and_removed(hass: HomeAssistant, device) -> None:
    hass.config.components.add("frontend")
    with patch("homeassistant.components.panel_custom.async_register_panel", new=AsyncMock()) as register, \
         patch("homeassistant.components.frontend.async_remove_panel") as remove, \
         patch.object(P, "_async_serve_files", new=AsyncMock()) as serve, patch.object(hass, "http", MagicMock()):
        entry = await setup(hass)
        register.assert_awaited_once()
        kwargs = register.await_args.kwargs
        assert kwargs["frontend_url_path"] == "proxon" and kwargs["webcomponent_name"] == "proxon-panel"
        assert kwargs["sidebar_title"] == "Proxon" and kwargs["require_admin"] is False
        assert kwargs["module_url"].startswith("/proxon_control_static/proxon-panel.js?v=")
        assert kwargs["module_url"].endswith(P._fingerprint()) and len(P._fingerprint()) == 10  # changes with the script
        assert kwargs["config"]["version"]
        assert kwargs["config"]["entities"]["T3Frischluft"] == eid(hass, "sensor", "T3Frischluft")
        serve.assert_awaited_once()
        # the page is refreshed on a reload (entity IDs may change), the files are served once
        assert await hass.config_entries.async_reload(entry.entry_id)
        assert register.await_count == 2 and serve.await_count == 1
        remove.reset_mock()
        assert await hass.config_entries.async_unload(entry.entry_id)
        remove.assert_called_with(hass, "proxon", warn_if_unknown=False)


async def test_no_panel_without_the_web_interface(hass: HomeAssistant, device) -> None:
    with patch("homeassistant.components.panel_custom.async_register_panel", new=AsyncMock()) as register:
        await setup(hass)
    register.assert_not_awaited()


async def test_files_are_served(hass: HomeAssistant) -> None:
    hass.http = MagicMock(async_register_static_paths=AsyncMock())
    await P._async_serve_files(hass)
    static = hass.http.async_register_static_paths.await_args.args[0][0]
    assert static.url_path == "/proxon_control_static" and static.path.endswith("frontend")


def test_panel_script_is_shipped() -> None:
    script = (P.FRONTEND_DIR / "proxon-panel.js").read_text(encoding="utf-8")
    assert 'customElements.define("proxon-panel"' in script
    # every entity the page reads is one the integration has (by its unique-id suffix)
    for key in ("T1Zuluft", "T3Frischluft", "T4Fortluft", "T7Abluft", "DrehzahlZuluft", "DrehzahlAbluft", "Intensivlueftung",
                "WarmwasserLadezustand", "WarmwasserDuschminuten", "SollWassertemperatur", "Urlaubsmodus", "SolarWarmwasser"):
        assert f'"{key}"' in script


async def test_look_of_the_page(hass: HomeAssistant, device) -> None:
    """The page's look comes from the options: liquid glass unless "soft" was chosen; only a choice other than glass is kept."""
    from homeassistant.data_entry_flow import FlowResultType

    entry = await setup(hass)
    assert P.panel_config(hass, entry)["look"] == "glass"
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    schema = {str(k): k for k in flow["data_schema"].schema}
    assert schema["panel_look"].default() == "glass"
    result = await hass.config_entries.options.async_configure(flow["flow_id"], {"scan_interval": 10, "panel_look": "soft"})
    assert result["type"] is FlowResultType.CREATE_ENTRY and entry.options["panel_look"] == "soft"
    await hass.async_block_till_done()
    assert P.panel_config(hass, entry)["look"] == "soft"
    flow = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(flow["flow_id"], {"scan_interval": 10, "panel_look": "glass"})
    assert "panel_look" not in entry.options
