"""Icons come from icons.json (translation keys), not from the code: every icon key matches an entity translation or a
service, and the entity code sets no icon of its own."""
from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).parents[1] / "custom_components" / "proxon_control"


def test_icons_json_matches_the_translations_and_services() -> None:
    icons = json.loads((ROOT / "icons.json").read_text(encoding="utf-8"))
    strings = json.loads((ROOT / "strings.json").read_text(encoding="utf-8"))
    for domain, keys in icons["entity"].items():
        for key, icon in keys.items():
            assert key in strings["entity"][domain], f"{domain}.{key} has an icon but no translation"
            assert icon["default"].startswith("mdi:")
            assert all(v.startswith("mdi:") for v in icon.get("state", {}).values())
    assert set(icons["services"]) == set(strings["services"])


def test_entities_set_no_icon_in_code() -> None:
    for path in ROOT.glob("*.py"):
        if path.name in ("dashboard.py", "dashboard_store.py", "panel.py"):  # dashboard cards and the sidebar entry name icons
            continue
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"mdi:|_attr_icon|\bicon=", text), f"{path.name} sets an icon in code"
