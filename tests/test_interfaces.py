"""What users build on stays put: the entities (by unique ID, which keeps their entity IDs), the actions and their
fields, the options, the blueprints (imported by their address). Automations, dashboards and blueprints refer to these;
from 1.0 on, removing or renaming one is a breaking change that needs a new major version.

The expected lists are in tests/interfaces.json. A test fails when something is gone or renamed (that is the point), and
also when something is new, so the list stays complete: after adding an entity, action or option on purpose, write the
list anew with  UPDATE_INTERFACES=1 pytest tests/test_interfaces.py  and commit it with the change.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import yaml

from custom_components.proxon_control import const
from custom_components.proxon_control.const import DOMAIN

from .test_integration import setup

FILE = Path(__file__).parent / "interfaces.json"
COMPONENT = Path(__file__).parents[1] / "custom_components" / DOMAIN


def _current_entities(hass: HomeAssistant, prefix: str) -> list[str]:
    entries = er.async_entries_for_config_entry(er.async_get(hass), hass.config_entries.async_entries(DOMAIN)[0].entry_id)
    return sorted(f"{e.domain}.{e.unique_id.removeprefix(prefix)}" for e in entries)


def _current_actions() -> dict[str, list[str]]:
    spec = yaml.safe_load((COMPONENT / "services.yaml").read_text(encoding="utf-8")) or {}
    return {name: sorted((body or {}).get("fields", {})) for name, body in sorted(spec.items())}


def _current_options() -> list[str]:
    return sorted(v for k, v in vars(const).items() if k.startswith("CONF_") and isinstance(v, str))


def _current_blueprints() -> list[str]:  # imported by their address in this repository
    root = Path(__file__).parents[1]
    return sorted(str(f.relative_to(root)) for f in (root / "blueprints").rglob("*.yaml"))


def _check(name: str, current, expected: dict) -> None:
    if os.environ.get("UPDATE_INTERFACES"):
        expected[name] = current
        return
    want = expected.get(name)
    if isinstance(current, dict):
        gone = sorted(set(want) - set(current)) + sorted(f"{k}.{f}" for k in set(want) & set(current) for f in set(want[k]) - set(current[k]))
        new = sorted(set(current) - set(want)) + sorted(f"{k}.{f}" for k in set(want) & set(current) for f in set(current[k]) - set(want[k]))
    else:
        gone, new = sorted(set(want) - set(current)), sorted(set(current) - set(want))
    assert not gone, f"{name}: removed or renamed (breaks automations and dashboards): {gone}"
    assert not new, f"{name}: new, not yet in tests/interfaces.json (run with UPDATE_INTERFACES=1): {new}"


async def test_interfaces_stay_put(hass: HomeAssistant, device) -> None:
    entry = await setup(hass)
    expected = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    _check("entities", _current_entities(hass, f"{entry.unique_id}_"), expected)
    _check("actions", _current_actions(), expected)
    _check("options", _current_options(), expected)
    _check("blueprints", _current_blueprints(), expected)
    if os.environ.get("UPDATE_INTERFACES"):
        FILE.write_text(json.dumps(expected, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
