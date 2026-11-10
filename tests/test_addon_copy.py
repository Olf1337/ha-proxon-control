"""The bridge add-on ships its own copies of the shared files; they must stay identical."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_addon_uses_same_code() -> None:
    for name in ("nabto.py", "registers.py"):
        a = (ROOT / "custom_components" / "proxon_control" / name).read_text(encoding="utf-8")
        b = (ROOT / "proxon_bridge" / name).read_text(encoding="utf-8")
        assert a == b, f"proxon_bridge/{name} differs - copy it again"
