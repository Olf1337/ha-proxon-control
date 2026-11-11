"""Home network connection: the uNabto client against a simulated unit on UDP, the certificate from the portal, and the
choice between home network and Proxon server."""
from __future__ import annotations

import base64
import os
import socket
import struct
import threading
from unittest.mock import MagicMock, patch

import pytest

from custom_components.proxon_control import api as A, local as L, local_cert as C, registers as R

from .conftest import FakeDevice

CERT = "-----BEGIN CERTIFICATE-----\n" + base64.b64encode(b"a certificate signed by the portal").decode() + "\n-----END CERTIFICATE-----\n"
FP = L.fingerprint(CERT)
DEVICE_ID = "abc123"


class FakeUnit:
    """A Proxon unit in the home network: answers uNabto connect requests and queries 42 / 43 / 45 over UDP on 127.0.0.1."""

    def __init__(self, device: FakeDevice, accepted_fp: bytes = FP) -> None:
        self.device = device
        self.accepted_fp = accepted_fp
        self.write_status = 1
        self.silent = False
        self.sessions = 0
        self.closes = 0
        self.queries: list[tuple[int, int]] = []  # (query, number of points)
        self.emails: list[str] = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.05)
        self.port = self.sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(2)
        self.sock.close()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self.sock.recvfrom(4096)
            except (socket.timeout, OSError):
                continue
            if self.silent or len(data) < 16:
                continue
            answer = self._answer(data)
            if answer:
                self.sock.sendto(answer, addr)

    def _answer(self, data: bytes) -> bytes | None:
        client_id, ptype, flags, seq = data[:4], data[8:9], data[11], struct.unpack("!H", data[12:14])[0]
        if ptype == L.PKT_U_CONNECT:
            fp, pos = None, 16
            while pos + 4 <= len(data):
                t, n = data[pos], struct.unpack("!H", data[pos + 2:pos + 4])[0]
                body = data[pos + 4:pos + n]
                if t == L.PL_FP:
                    fp = body[1:]
                elif t == L.PL_CP_ID:
                    self.emails.append(body[1:].decode())
                pos += n
            ok = fp == self.accepted_fp
            if ok:
                self.sessions += 1
            notify = struct.pack("!I", L.NOTIFY_CONNECT_OK if ok else 0x0002) + (b"\x00\x00\x00\x07" if ok else b"\x00" * 4)
            return L.packet(client_id, b"\x00" * 4, L.PKT_U_CONNECT, 1, L._payload(L.PL_NOTIFY, notify), False)
        if ptype != L.PKT_DATA:
            return None
        assert (sum(data[:-2]) & 0xFFFF).to_bytes(2, "big") == data[-2:], "bad checksum"
        server_id = data[4:8]
        if flags & 0x40:  # close frame
            self.closes += 1
            return L.packet(client_id, server_id, L.PKT_DATA, seq, L.crypt_null(b"\x00"), True)
        query = L.unwrap_data(data)
        number = struct.unpack("!I", query[:4])[0]
        if number == L.QUERY_SP_WRITE:
            _, n, obj, address, value = struct.unpack("!IHBIH", query[:13])
            self.queries.append((number, 1))
            if self.write_status == 1:
                self.device.invoke(R.QUERY_WRITE, {"list": [{"obj": obj, "address": address, "value": value}]})
            out = bytes([self.write_status])
        else:
            n = struct.unpack("!H", query[4:6])[0]
            self.queries.append((number, n))
            if number == L.QUERY_SP_LIST:
                points = [struct.unpack("!BH", query[6 + 3 * k:9 + 3 * k]) for k in range(n)]
                name = R.QUERY_SET_READ
            else:
                points = [struct.unpack("!BI", query[6 + 5 * k:11 + 5 * k]) for k in range(n)]
                name = R.QUERY_DATA_READ
            values = self.device.invoke(name, {"list": [{"obj": o, "address": a} for o, a in points]})["response"]["data"]
            packed = b"".join(struct.pack("!h", v["value"]) for v in values)
            out = (b"\x00" if number == L.QUERY_SP_LIST else b"") + struct.pack("!H", n) + packed
        return L.packet(client_id, server_id, L.PKT_DATA, seq, L.crypt_null(out), True)


@pytest.fixture
def unit(socket_enabled):
    u = FakeUnit(FakeDevice())
    with patch.object(L, "MIN_SEND_INTERVAL", 0):
        yield u
    u.stop()


@pytest.fixture
def stored_cert(tmp_path):
    folder = tmp_path / "local" / DEVICE_ID
    folder.mkdir(parents=True)
    (folder / "certificate.pem").write_text(CERT)
    (folder / "key.pem").write_text("key")
    return tmp_path


class CloudClient:
    """The cloud client's view of the same unit (FakeDevice answers like the Nabto RPC interface)."""

    def __init__(self, device: FakeDevice) -> None:
        self.invoke = device.invoke


# ---------------- packets ----------------
def test_packets() -> None:
    pkt = L.packet(b"CCCC", b"SSSS", L.PKT_DATA, 7, L.crypt_null(b"\x01\x02\x03"), True)
    assert pkt[:9] == b"CCCCSSSS\x16" and struct.unpack("!H", pkt[12:14])[0] == 7
    assert struct.unpack("!H", pkt[14:16])[0] == len(pkt)
    assert (sum(pkt[:-2]) & 0xFFFF).to_bytes(2, "big") == pkt[-2:]
    assert L.unwrap_data(pkt) == b"\x01\x02\x03"
    assert L.unwrap_data(L.packet(b"CCCC", b"SSSS", L.PKT_DATA, 1, L.crypt_null(b"\x01\x02"), True)) == b"\x01\x02"
    assert L.user_email(" abc123 ") == "user-abc123@phc.proxon.de"
    assert len(L.fingerprint(CERT)) == 16


# ---------------- the client against the simulated unit ----------------
def test_reads_the_same_values_as_through_the_cloud(unit: FakeUnit) -> None:
    client = L.LocalClient("127.0.0.1", unit.port, DEVICE_ID, FP)
    try:
        local = R.read_all(client)
    finally:
        client.close()
    cloud = R.read_all(CloudClient(unit.device))
    assert {k: v for k, v in local.items() if k != "Antwortzeit"} == {k: v for k, v in cloud.items() if k != "Antwortzeit"}
    assert local["T3Frischluft"] == 17.5 and local["NBE1name"] == "Schlafzimmer"
    assert 0 < local["Antwortzeit"] < 1000  # measured on the wire
    assert unit.emails == ["user-abc123@phc.proxon.de"] and unit.sessions == 1 and unit.closes == 1
    assert {q for q, _ in unit.queries} == {L.QUERY_SP_LIST, L.QUERY_DP_LIST}
    assert max(n for _, n in unit.queries) <= L.MAX_POINTS_PER_QUERY  # long lists split up


def test_new_session_before_the_units_limit(unit: FakeUnit) -> None:
    client = L.LocalClient("127.0.0.1", unit.port, DEVICE_ID, FP)
    with patch.object(L, "MAX_RPCS_PER_SESSION", 3):
        for _ in range(7):
            client.read_set_points([(1, 0)])
        client.close()
    assert unit.sessions == 3 and len(unit.queries) == 7


def test_write_and_read_back(unit: FakeUnit) -> None:
    client = L.LocalClient("127.0.0.1", unit.port, DEVICE_ID, FP)
    try:
        values = R.write_and_verify(client, "SollWassertemperatur", 48)
    finally:
        client.close()
    assert values["SollWassertemperatur"] == 48.0
    assert unit.device.writes == [{"obj": 1, "address": 0, "value": 480}]


def test_write_not_acknowledged(unit: FakeUnit) -> None:
    unit.write_status = 0
    client = L.LocalClient("127.0.0.1", unit.port, DEVICE_ID, FP)
    with pytest.raises(L.WriteNotAcknowledged):
        client.write(1, 0, 480)
    client.close()
    assert unit.device.writes == []


def test_unknown_certificate_is_refused(unit: FakeUnit) -> None:
    client = L.LocalClient("127.0.0.1", unit.port, DEVICE_ID, b"\x01" * 16)
    with pytest.raises(L.LocalRejected):
        client.read_set_points([(1, 0)])


def test_no_answer(unit: FakeUnit) -> None:
    unit.silent = True
    client = L.LocalClient("127.0.0.1", unit.port, DEVICE_ID, FP)
    with patch.object(L, "CONNECT_TIMEOUT", 0.2), pytest.raises(L.LocalError) as err:
        client.read_set_points([(1, 0)])
    assert not isinstance(err.value, L.LocalRejected)


def test_discover(unit: FakeUnit) -> None:
    found = L.discover(unit.port, timeout=0.5, broadcast="127.0.0.1")
    assert [f.host for f in found] == ["127.0.0.1"]


# ---------------- certificate from the portal ----------------
def test_portal_answer() -> None:
    assert C.parse_answer("0\nOK\n" + CERT + "trailing") == CERT
    with pytest.raises(C.PortalRejected, match="wrong password"):
        C.parse_answer("1\nwrong password\n")
    with pytest.raises(C.CertificateError):
        C.parse_answer("0\nOK\nno certificate here")


def test_fetch_signs_a_new_key(tmp_path) -> None:
    sent = {}

    def urlopen(req, timeout):
        sent["url"], sent["body"] = req.full_url, req.data.decode()
        resp = MagicMock()
        resp.__enter__.return_value.read.return_value = ("0\nOK\n" + CERT).encode()
        return resp

    with patch.object(C.urllib.request, "urlopen", urlopen):
        assert C.ensure(str(tmp_path), DEVICE_ID, "secret") == CERT
    assert sent["url"] == C.PORTAL_SIGN_URL
    assert "password=secret" in sent["body"] and "email=user-abc123%40phc.proxon.de" in sent["body"]
    assert "BEGIN+CERTIFICATE+REQUEST" in sent["body"]
    key = tmp_path / "local" / DEVICE_ID / "key.pem"
    assert key.exists() and "PRIVATE KEY" in key.read_text() and (os.stat(key).st_mode & 0o777) == 0o600
    assert C.load(str(tmp_path), DEVICE_ID) == CERT
    with patch.object(C.urllib.request, "urlopen", side_effect=AssertionError("asked again")):
        assert C.ensure(str(tmp_path), DEVICE_ID, "secret") == CERT  # kept: the portal is asked only once
    C.forget(str(tmp_path), DEVICE_ID)
    assert C.load(str(tmp_path), DEVICE_ID) is None


# ---------------- home network API ----------------
def test_local_api(unit: FakeUnit, stored_cert) -> None:
    api = A.LocalApi(DEVICE_ID, "secret", str(stored_cert), "127.0.0.1", unit.port)
    data = api.read()
    assert data[A.PATH_KEY] == "local" and data["SollWassertemperatur"] == 34.0
    assert api.write("SollWassertemperatur", 47)["SollWassertemperatur"] == 47.0
    assert unit.sessions == unit.closes == 2  # one session per task, closed afterwards


def test_local_api_renews_a_refused_certificate_at_most_daily(unit: FakeUnit, stored_cert) -> None:
    unit.accepted_fp = b"\x02" * 16
    api = A.LocalApi(DEVICE_ID, "secret", str(stored_cert), "127.0.0.1", unit.port)
    with pytest.raises(A.ProxonError, match="noch nicht"):
        api.read()
    assert C.load(str(stored_cert), DEVICE_ID) == CERT  # just fetched: kept, the unit learns it while online
    cert = stored_cert / "local" / DEVICE_ID / "certificate.pem"
    old = cert.stat().st_mtime - A.CERT_RENEW_AFTER - 60
    os.utime(cert, (old, old))
    with pytest.raises(A.ProxonError, match="neues Zertifikat"):
        api.read()
    assert C.load(str(stored_cert), DEVICE_ID) is None  # fetched anew next time


def test_local_api_wrong_password_at_the_portal(tmp_path) -> None:
    with patch.object(C, "fetch", side_effect=C.PortalRejected("wrong password")):
        with pytest.raises(A.AuthError):
            A.LocalApi(DEVICE_ID, "x", str(tmp_path), "127.0.0.1").read()


def test_local_api_write_not_taken_over(unit: FakeUnit, stored_cert) -> None:
    unit.device.ignore_writes = True
    api = A.LocalApi(DEVICE_ID, "secret", str(stored_cert), "127.0.0.1", unit.port)
    with pytest.raises(A.WriteNotAccepted):
        api.write("SollWassertemperatur", 47)


# ---------------- home network first, Proxon server as fallback ----------------
class Way:
    def __init__(self, name: str, error: Exception | None = None) -> None:
        self.name, self.error, self.calls = name, error, 0

    def read(self) -> dict:
        self.calls += 1
        if self.error:
            raise self.error
        return {"T3Frischluft": 1.0, "Antwortzeit": 5.0}

    def write(self, key, value) -> dict:
        return self.read()

    def close(self) -> None:
        pass


def test_auto_uses_the_home_network_first() -> None:
    local, cloud = Way("local"), Way("cloud")
    api = A.HybridApi(A.MODE_AUTO, local, cloud)
    assert api.read()[A.PATH_KEY] == "local" and cloud.calls == 0


def test_auto_falls_back_and_tries_again_later() -> None:
    local, cloud = Way("local", A.ProxonError("not found")), Way("cloud")
    api = A.HybridApi(A.MODE_AUTO, local, cloud)
    assert api.read()[A.PATH_KEY] == "cloud" and local.calls == 1
    assert api.read()[A.PATH_KEY] == "cloud" and local.calls == 1  # paused: not tried every time
    local.error = None
    with patch.object(A.time, "monotonic", return_value=A.time.monotonic() + A.LOCAL_RETRY + 1):
        assert api.read()[A.PATH_KEY] == "local" and local.calls == 2


def test_auto_certificate_refused_but_cloud_works() -> None:
    api = A.HybridApi(A.MODE_AUTO, Way("local", A.AuthError("portal")), Way("cloud"))
    assert api.read()[A.PATH_KEY] == "cloud"


def test_wrong_password_everywhere_asks_to_log_in_again() -> None:
    api = A.HybridApi(A.MODE_AUTO, Way("local", A.ProxonError("not found")), Way("cloud", A.AuthError("bad")))
    with pytest.raises(A.AuthError):
        api.read()


def test_a_value_the_unit_refuses_is_not_written_again_through_the_cloud() -> None:
    cloud = Way("cloud")
    api = A.HybridApi(A.MODE_AUTO, Way("local", A.WriteNotAccepted("x", 1, 0, {})), cloud)
    with pytest.raises(A.WriteNotAccepted):
        api.write("x", 1)
    assert cloud.calls == 0


def test_local_only_never_uses_the_cloud() -> None:
    cloud = Way("cloud")
    api = A.HybridApi(A.MODE_LOCAL, Way("local", A.ProxonError("not found")), cloud)
    with pytest.raises(A.ProxonError):
        api.read()
    assert cloud.calls == 0


def test_connect_without_nabto_library_is_home_network_only(tmp_path) -> None:
    api = A.connect(DEVICE_ID, "secret", str(tmp_path), A.MODE_CLOUD, None, cloud_possible=False)
    assert api.cloud is None and isinstance(api.local, A.LocalApi)
    api = A.connect(DEVICE_ID, "secret", str(tmp_path), A.MODE_AUTO, " 192.168.1.50 ")
    assert isinstance(api.cloud, A.DirectApi) and api.local.host == "192.168.1.50"
    api = A.connect(DEVICE_ID, "secret", str(tmp_path), A.MODE_CLOUD)
    assert api.local is None
