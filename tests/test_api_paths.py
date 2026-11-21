"""The connection classes on their own: logging in through the Proxon server, losing and renewing a session, the home
network's certificate and search, and the bridge's error answers, each with stand-ins instead of the real unit."""
from __future__ import annotations

import io
import json
import urllib.error

import pytest

from custom_components.proxon_control import api, local, local_cert
from custom_components.proxon_control.api import AuthError, BridgeApi, DirectApi, LocalApi, ProxonError, TokenError, WriteNotAccepted
from custom_components.proxon_control.nabto import NabtoError


class Client:
    def __init__(self, login_error: Exception | None = None) -> None:
        self.login_error, self.closed = login_error, 0

    def login(self, device_id: str, password: str) -> None:
        if self.login_error:
            raise self.login_error

    def close(self) -> None:
        self.closed += 1


@pytest.mark.parametrize(("error", "raised", "text"), [
    (NabtoError("portal said no", 7), AuthError, "portal said no"),
    (NabtoError("unreachable", 3), ProxonError, "unreachable"),
    (OSError("disk full"), ProxonError, "Download der Nabto-Dateien fehlgeschlagen: disk full"),
])
def test_login_through_the_proxon_server_refused(monkeypatch, tmp_path, error, raised, text) -> None:
    monkeypatch.setattr(api, "create_client", lambda d: Client(error))
    with pytest.raises(raised, match=text):
        DirectApi("01ABC", "pw", str(tmp_path)).read_schedule()


def test_lost_session_logs_in_again_once(monkeypatch, tmp_path) -> None:
    clients: list[Client] = []
    monkeypatch.setattr(api, "create_client", lambda d: clients.append(Client()) or clients[-1])
    d = DirectApi("01ABC", "pw", str(tmp_path))
    answers = iter([NabtoError("session lost", 4), {"ok": 1}])

    def fn(client):
        a = next(answers)
        if isinstance(a, Exception):
            raise a
        return a

    assert d._call(fn) == {"ok": 1} and len(clients) == 2 and clients[0].closed == 1
    # lost twice in a row: given up
    with pytest.raises(ProxonError, match="still lost"):
        d._call(lambda c: (_ for _ in ()).throw(NabtoError("still lost", 4)))
    d.close()


def test_home_network_certificate_refused(monkeypatch, tmp_path) -> None:
    def portal(*_):
        raise local_cert.PortalRejected("wrong password")

    monkeypatch.setattr(local_cert, "ensure", portal)
    with pytest.raises(AuthError, match="Proxon-Portal: wrong password"):
        LocalApi("01ABC", "pw", str(tmp_path), host="10.0.0.5")._certificate()

    def broken(*_):
        raise local_cert.CertificateError("no answer")

    monkeypatch.setattr(local_cert, "ensure", broken)
    with pytest.raises(ProxonError, match="Zertifikat für die lokale Verbindung: no answer"):
        LocalApi("01ABC", "pw", str(tmp_path), host="10.0.0.5")._certificate()


def test_unit_not_found_in_the_home_network(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(local, "discover", lambda port: [])
    with pytest.raises(ProxonError, match="nicht gefunden"):
        LocalApi("01ABC", "pw", str(tmp_path))._address()


class Reply(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_error(code: int, body: bytes) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://bridge", code, "error", {}, io.BytesIO(body))


@pytest.mark.parametrize(("code", "body", "raised", "text"), [
    (401, b'{"error": "bad password"}', AuthError, "bad password"),
    (403, b'{"error": "access key"}', TokenError, "access key"),
    (500, b"not json at all", ProxonError, "error"),
    (502, b'{"error": "unit unreachable"}', ProxonError, "unit unreachable"),
])
def test_bridge_error_answers(monkeypatch, code, body, raised, text) -> None:
    def urlopen(req, timeout):
        raise _http_error(code, body)

    monkeypatch.setattr(api.urllib.request, "urlopen", urlopen)
    with pytest.raises(raised, match=text):
        BridgeApi("bridge.local", 8765, token="t").read()


def test_bridge_write_not_taken_over(monkeypatch) -> None:
    body = json.dumps({"error": "x", "key": "GrenzwertCO2", "wanted": 900, "got": 800, "values": {"GrenzwertCO2": 800}}).encode()
    monkeypatch.setattr(api.urllib.request, "urlopen", lambda req, timeout: (_ for _ in ()).throw(_http_error(409, body)))
    with pytest.raises(WriteNotAccepted) as err:
        BridgeApi("http://bridge.local", 8765).write("GrenzwertCO2", 900)
    assert (err.value.key, err.value.wanted, err.value.got) == ("GrenzwertCO2", 900.0, 800)


def test_bridge_unreachable_and_its_address(monkeypatch) -> None:
    monkeypatch.setattr(api.urllib.request, "urlopen", lambda req, timeout: (_ for _ in ()).throw(urllib.error.URLError("refused")))
    with pytest.raises(ProxonError, match="Bridge nicht erreichbar"):
        BridgeApi("bridge.local", 8765).read()
    assert BridgeApi("http://[fd00::1]:9000", 8765).base == "http://[fd00::1]:9000"
    sent: list = []
    monkeypatch.setattr(api.urllib.request, "urlopen", lambda req, timeout: sent.append(req) or Reply(b""))
    assert BridgeApi("bridge.local/", 8765, token=" key ")._req("/x") == {}
    assert sent[0].full_url == "http://bridge.local:8765/x" and sent[0].get_header("Authorization") == "Bearer key"
