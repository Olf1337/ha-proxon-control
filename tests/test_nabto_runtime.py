"""The glibc runtime for the helper program (Home Assistant OS): only the pinned Debian packages, checked by SHA-256, from
Debian's mirror or else snapshot.debian.org; never a newer file found by looking around."""
from __future__ import annotations

import hashlib
import urllib.error

import pytest

from custom_components.proxon_control import nabto as N


def test_every_package_is_pinned_with_a_snapshot_copy() -> None:
    for name, urls, sha, wanted in N.RUNTIME_PACKAGES:
        assert len(sha) == 64 and wanted
        assert urls[0].startswith(N.DEBIAN_POOL) and urls[0].endswith(name)
        assert any(u.startswith("https://snapshot.debian.org/archive/debian/") for u in urls)
        assert all(u.startswith("https://") for u in urls)


def test_fetch_takes_the_next_place_and_checks_the_sum(monkeypatch) -> None:
    good = b"the package"
    sha = hashlib.sha256(good).hexdigest()
    asked: list[str] = []

    def download(url: str) -> bytes:
        asked.append(url)
        if url == "https://a/x.deb":
            raise urllib.error.HTTPError(url, 404, "gone", None, None)  # type: ignore[arg-type]
        return good

    monkeypatch.setattr(N, "_download", download)
    assert N._fetch_deb("x.deb", ["https://a/x.deb", "https://b/x.deb"], sha) == good
    assert asked == ["https://a/x.deb", "https://b/x.deb"]


def test_fetch_refuses_a_wrong_checksum(monkeypatch) -> None:
    monkeypatch.setattr(N, "_download", lambda url: b"something else")
    with pytest.raises(N.NabtoError, match="Prüfsumme"):
        N._fetch_deb("x.deb", ["https://a/x.deb", "https://b/x.deb"], hashlib.sha256(b"the package").hexdigest())


def test_fetch_fails_clearly_when_no_place_has_it(monkeypatch) -> None:
    def download(url: str) -> bytes:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(N, "_download", download)
    with pytest.raises(N.NabtoError, match="ließ sich nicht herunterladen"):
        N._fetch_deb("x.deb", ["https://a/x.deb"], "0" * 64)
