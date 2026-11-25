"""The way through the Proxon server: Nabto's library loaded directly (glibc Linux, macOS) and its download, with a stand-in
for the library, so the login, the queries and every refusal along the way are tested without the real library."""
from __future__ import annotations

import ctypes
import hashlib
import io
import json
import zipfile

import pytest

from custom_components.proxon_control import nabto
from custom_components.proxon_control.nabto import OK, NabtoClient, NabtoError


class Fn:
    def __init__(self, f) -> None:
        self.f = f

    def __call__(self, *args):
        return self.f(*args)


class FakeLib:
    """Nabto's C library as far as the client uses it. Replies are real C strings, so the client reads them as usual."""

    def __init__(self, startup: int = OK, certs: int = OK, open_session=(OK,), create: int = OK, interface: int = OK,
                 reply: tuple[int, str] = (OK, '{"response": {"x": 1}}')) -> None:
        self.startup, self.certs, self.open_results, self.create, self.interface, self.reply = startup, certs, list(open_session), create, interface, reply
        self.calls: list[str] = []
        self._keep: list = []  # the C strings handed out, alive until freed
        for name in dir(type(self)):  # like ctypes functions: callable, and they take argtypes/restype
            if name.startswith("nabto"):
                setattr(self, name, Fn(getattr(self, name)))

    def _hand_out(self, holder, text: str) -> None:
        buf = ctypes.create_string_buffer(text.encode())
        self._keep.append(buf)
        holder._obj.value = ctypes.addressof(buf)

    # the library's functions
    def nabtoStartup(self, home):  # noqa: N802 - the library's names
        self.calls.append("startup")
        return self.startup

    def nabtoInstallDefaultStaticResources(self, _):  # noqa: N802
        return self.certs

    def nabtoSetOption(self, *_):  # noqa: N802
        return OK

    def nabtoOpenSession(self, session, user, pw):  # noqa: N802
        self.calls.append("open")
        st = self.open_results.pop(0) if self.open_results else OK
        if st == OK:
            session._obj.value = 1234
        return st

    def nabtoCreateProfile(self, user, pw):  # noqa: N802
        self.calls.append("create")
        return self.create

    def nabtoRpcSetDefaultInterface(self, session, xml, err):  # noqa: N802
        if self.interface != OK:
            self._hand_out(err, "bad interface")
        return self.interface

    def nabtoRpcInvoke(self, session, url, out):  # noqa: N802
        self.calls.append("invoke:" + url.decode().split("/")[3].split(".json")[0])
        self._hand_out(out, self.reply[1])
        return self.reply[0]

    def nabtoFree(self, ptr):  # noqa: N802
        return OK

    def nabtoCloseSession(self, session):  # noqa: N802
        self.calls.append("close")
        return OK


@pytest.fixture(autouse=True)
def fresh_library_cache():
    NabtoClient._started.clear()
    yield
    NabtoClient._started.clear()


def client(monkeypatch, tmp_path, lib: FakeLib) -> NabtoClient:
    monkeypatch.setattr(nabto.ctypes, "CDLL", lambda path: lib)
    return NabtoClient(str(tmp_path / "libnabto.so"), str(tmp_path / "home"))


def test_login_query_and_close(monkeypatch, tmp_path) -> None:
    lib = FakeLib()
    c = client(monkeypatch, tmp_path, lib)
    c.login(" 01ABC ", "secret")
    assert c.invoke("datapointReadListValue", {"list": [1]}) == {"response": {"x": 1}}
    c.close()
    assert lib.calls == ["startup", "open", "invoke:datapointReadListValue", "close"]
    # the library is started once per process, the next client reuses it
    client(monkeypatch, tmp_path, lib)
    assert lib.calls.count("startup") == 1


def test_first_login_creates_the_profile(monkeypatch, tmp_path) -> None:
    lib = FakeLib(open_session=(nabto.FAILED_WITH_JSON_MESSAGE + 1, OK))
    c = client(monkeypatch, tmp_path, lib)
    c.login("01ABC", "secret")
    assert lib.calls[1:] == ["open", "create", "open"]


@pytest.mark.parametrize(("lib", "message"), [
    (FakeLib(open_session=(5,), create=7), "Anmeldung fehlgeschlagen"),
    (FakeLib(open_session=(5, 6)), "Sitzung konnte nicht geöffnet werden"),
    (FakeLib(interface=9), "Schnittstelle nicht akzeptiert"),
])
def test_login_refusals(monkeypatch, tmp_path, lib, message) -> None:
    c = client(monkeypatch, tmp_path, lib)
    with pytest.raises(NabtoError, match=message):
        c.login("01ABC", "secret")


def test_query_without_login_and_device_errors(monkeypatch, tmp_path) -> None:
    c = client(monkeypatch, tmp_path, FakeLib(reply=(OK, json.dumps({"error": {"body": "no access"}}))))
    with pytest.raises(NabtoError, match="Nicht angemeldet"):
        c.invoke("datapointReadListValue", {})
    c.login("01ABC", "secret")
    with pytest.raises(NabtoError, match="no access"):
        c.invoke("setpointWriteValue", {})


@pytest.mark.parametrize(("lib", "message"), [
    (FakeLib(startup=3), "Nabto-Start fehlgeschlagen"),
    (FakeLib(certs=3), "Zertifikate konnten nicht installiert werden"),
])
def test_library_start_refused(monkeypatch, tmp_path, lib, message) -> None:
    with pytest.raises(NabtoError, match=message):
        client(monkeypatch, tmp_path, lib)


def test_library_that_cannot_be_loaded(monkeypatch, tmp_path) -> None:
    def refuse(path):
        raise OSError("wrong architecture")

    monkeypatch.setattr(nabto.ctypes, "CDLL", refuse)
    with pytest.raises(NabtoError, match="lässt sich nicht laden: wrong architecture"):
        NabtoClient(str(tmp_path / "x.so"), str(tmp_path / "home"))
    assert nabto.direct_load_works(str(tmp_path / "x.so")) is False


def test_parse_rpc() -> None:
    assert nabto.parse_rpc(OK, "") == {}
    with pytest.raises(NabtoError, match="nicht erreichbar"):
        nabto.parse_rpc(1, "{}")
    with pytest.raises(NabtoError, match="Ungültige Antwort"):
        nabto.parse_rpc(OK, "not json")
    with pytest.raises(NabtoError, match="plain"):
        nabto.parse_rpc(OK, json.dumps({"error": "plain"}))
    assert nabto.status_name(999) == "999"


# ---- the library's download ----

def _zip(member: str, blob: bytes) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(member, blob)
    return out.getvalue()


class Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_library_download(monkeypatch, tmp_path) -> None:
    key = ("linux", "x86_64")
    url, member, name = nabto.LIB_RELEASES[key]
    blob = b"\x7fELF fake library"
    monkeypatch.setattr(nabto, "platform_key", lambda: key)
    monkeypatch.setitem(nabto.LIB_SHA256, name, hashlib.sha256(blob).hexdigest())
    fetched: list[str] = []
    monkeypatch.setattr(nabto.urllib.request, "urlopen", lambda u, timeout: fetched.append(u) or Reply(_zip(member, blob)))
    path = nabto.ensure_library(str(tmp_path / "lib"))
    assert open(path, "rb").read() == blob and fetched == [url]
    assert nabto.ensure_library(str(tmp_path / "lib")) == path and len(fetched) == 1  # kept, not fetched again


def test_library_download_with_a_wrong_checksum(monkeypatch, tmp_path) -> None:
    key = ("linux", "x86_64")
    _url, member, name = nabto.LIB_RELEASES[key]
    monkeypatch.setattr(nabto, "platform_key", lambda: key)
    monkeypatch.setitem(nabto.LIB_SHA256, name, "0" * 64)
    monkeypatch.setattr(nabto.urllib.request, "urlopen", lambda u, timeout: Reply(_zip(member, b"tampered")))
    with pytest.raises(NabtoError, match="Prüfsumme"):
        nabto.ensure_library(str(tmp_path / "lib"))
    assert not (tmp_path / "lib" / name).exists()


def test_no_library_for_this_system(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(nabto, "platform_key", lambda: ("linux", "riscv64"))
    assert nabto.library_supported() is False
    with pytest.raises(NabtoError, match="gibt es nicht für dieses System"):
        nabto.ensure_library(str(tmp_path))


def test_broken_debian_packages(tmp_path) -> None:
    with pytest.raises(NabtoError, match="Ungültiges Debian-Paket"):
        nabto.extract_deb(b"not an archive", {}, str(tmp_path))
    with pytest.raises(NabtoError, match="ohne Daten"):
        nabto.extract_deb(b"!<arch>\n", {}, str(tmp_path))
