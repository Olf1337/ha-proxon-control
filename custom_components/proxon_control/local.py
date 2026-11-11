"""Direct connection to the unit in the home network (Nabto v4 / uNabto over UDP port 5570), in plain Python.

No Nabto library, no helper program and no internet needed while running - so it works on any system, including a Raspberry Pi.
The unit only accepts clients whose certificate was signed by the Proxon portal (local_cert.py fetches one once); in the
handshake the client sends the certificate's truncated SHA-256 fingerprint. Data is not encrypted on the home network (the
unit uses Nabto's NULL crypto suite locally), so this is meant for the trusted home network only.

The client offers the same `invoke(query, request)` interface as the cloud client, for the three queries this integration
uses, so registers.py works unchanged on both ways:
  setpointReadListValue  -> uNabto query 42 (list of set points)
  datapointReadListValue -> uNabto query 45 (list of data points)
  setpointWriteValue     -> uNabto query 43 (one set point; the unit acknowledges with 1)

The packet format below follows the ha-lan-proxon project, where it was worked out and verified on a real unit:
  Copyright (c) 2026 Fummy1990 - MIT License (full text in THIRD_PARTY_NOTICES.md).
No Home Assistant imports.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import logging
import secrets
import socket
import struct
import time

_LOGGER = logging.getLogger(__name__)

PORT = 5570

PKT_U_CONNECT = b"\x83"
PKT_DATA = b"\x16"
PL_NOTIFY = 0x34
PL_IPX = 0x35
PL_CRYPT = 0x36
PL_CP_ID = 0x3F
PL_FP = 0x4B
CRYPT_NULL = 0x000A
NOTIFY_CONNECT_OK = 0x0001
FP_TYPE_SHA256_TRUNCATED = 0x01
FP_LENGTH = 16

QUERY_SP_LIST = 42
QUERY_SP_WRITE = 43
QUERY_DP_LIST = 45

# the query names used by registers.py (same as for the cloud client)
SET_READ = "setpointReadListValue"
DATA_READ = "datapointReadListValue"
WRITE = "setpointWriteValue"

MAX_RPCS_PER_SESSION = 150  # the unit allows 160 per session; a new session is opened before that
MAX_POINTS_PER_QUERY = 40  # longer lists are split into several queries
MIN_SEND_INTERVAL = 0.25  # the unit wants a short pause between packets
CONNECT_TIMEOUT = 3.0
RPC_TIMEOUT = 2.0


class LocalError(Exception):
    """The unit could not be reached in the home network, or answered unexpectedly."""


class LocalRejected(LocalError):
    """The unit refused the connection (certificate not accepted)."""


class WriteNotAcknowledged(LocalError):
    def __init__(self, status: int) -> None:
        super().__init__(f"the unit did not acknowledge the write (status {status}, expected 1)")
        self.status = status


@dataclass
class Found:
    host: str
    port: int


def fingerprint(cert_pem: str | bytes) -> bytes:
    """Truncated SHA-256 (16 bytes) of the certificate (DER)."""
    text = cert_pem.decode() if isinstance(cert_pem, bytes) else cert_pem
    der = base64.b64decode("".join(line.strip() for line in text.splitlines() if line.strip() and not line.startswith("-----")))
    return hashlib.sha256(der).digest()[:FP_LENGTH]


def user_email(device_id: str) -> str:
    return f"user-{device_id.strip()}@phc.proxon.de"


# ---------------- packets ----------------
def _payload(ptype: int, data: bytes) -> bytes:
    return struct.pack("!BBH", ptype, 0, 4 + len(data)) + data


def _ipx() -> bytes:
    return _payload(PL_IPX, b"\x00" * 12 + b"\x80")


def _cp_id(email: bytes) -> bytes:
    return _payload(PL_CP_ID, b"\x01" + email)


def _fp(fp: bytes) -> bytes:
    return _payload(PL_FP, bytes([FP_TYPE_SHA256_TRUNCATED]) + fp)


def crypt_null(data: bytes) -> bytes:
    """Data wrapped in the NULL crypto payload: padded to an even length (pad bytes carry the pad length)."""
    pad = ((len(data) // 2) + 1) * 2 - len(data)
    body = data + bytes([pad]) * pad
    return struct.pack("!BBH", PL_CRYPT, 0, 4 + 2 + len(body) + 2) + struct.pack("!H", CRYPT_NULL) + body


def packet(client_id: bytes, server_id: bytes, ptype: bytes, seq: int, payloads: bytes, checksum: bool, flags: int = 0) -> bytes:
    length = 16 + len(payloads) + (2 if checksum else 0)
    pkt = client_id + server_id + ptype + b"\x02\x00" + bytes([flags]) + seq.to_bytes(2, "big") + length.to_bytes(2, "big") + payloads
    if checksum:
        pkt += (sum(pkt) & 0xFFFF).to_bytes(2, "big")
    return pkt


def unwrap_data(data: bytes) -> bytes:
    """The answer inside a DATA packet (NULL crypto, padding removed)."""
    if len(data) < 22 or data[16] != PL_CRYPT:
        raise LocalError("answer without data")
    plen = struct.unpack("!H", data[18:20])[0]
    if struct.unpack("!H", data[20:22])[0] != CRYPT_NULL:
        raise LocalError("unexpected crypto suite in the answer")
    raw = data[22:16 + plen - 2]
    if not raw:
        raise LocalError("empty answer")
    pad = raw[-1]
    if not 1 <= pad <= 2 or raw[-pad:] != bytes([pad]) * pad:
        raise LocalError("bad padding in the answer")
    return raw[:-pad]


# ---------------- finding the unit ----------------
def discover(port: int = PORT, timeout: float = 3.0, broadcast: str = "255.255.255.255") -> list[Found]:
    """Units answering a broadcast in the home network."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    client_id = secrets.token_bytes(4)
    found: dict[str, Found] = {}
    try:
        sock.bind(("", 0))
        sock.sendto(packet(client_id, b"\x00" * 4, PKT_U_CONNECT, 1, _ipx() + _cp_id(b"discover@probe"), False), (broadcast, port))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            sock.settimeout(max(0.05, deadline - time.monotonic()))
            try:
                data, addr = sock.recvfrom(4096)
            except (TimeoutError, OSError):
                break
            if len(data) >= 16 and data[:4] == client_id:
                found.setdefault(addr[0], Found(addr[0], port))
    except OSError as err:
        _LOGGER.debug("Discovery failed: %s", err)
    finally:
        sock.close()
    return list(found.values())


# ---------------- the client ----------------
class LocalClient:
    """Talks to the unit at host:port. Opens a session when needed; `close()` ends it (call it after each task).
    Blocking - Home Assistant runs it in its executor."""

    def __init__(self, host: str, port: int, device_id: str, fp: bytes) -> None:
        if len(fp) != FP_LENGTH:
            raise ValueError("fingerprint must be 16 bytes")
        self.host, self.port = host, port
        self.email = user_email(device_id).encode()
        self.fp = fp
        self._sock: socket.socket | None = None
        self._client_id = b""
        self._server_id = b""
        self._seq = 0
        self._rpcs = 0
        self._last_send = 0.0
        self.last_rtt: float | None = None  # seconds, quickest answer of the current task

    # -- sending / receiving --
    def _pace(self) -> None:
        wait = MIN_SEND_INTERVAL - (time.monotonic() - self._last_send)
        if wait > 0:
            time.sleep(wait)
        self._last_send = time.monotonic()

    def _recv(self, timeout: float, want: bytes, seq: int | None) -> bytes:
        assert self._sock is not None
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._sock.settimeout(min(0.25, max(0.02, deadline - time.monotonic())))
            try:
                data, _ = self._sock.recvfrom(4096)
            except TimeoutError:
                continue
            if len(data) < 16 or data[:4] != self._client_id or data[8:9] != want:
                continue
            if seq is not None and struct.unpack("!H", data[12:14])[0] != seq:
                continue
            return data
        raise LocalError(f"no answer from {self.host}:{self.port}")

    # -- session --
    @property
    def connected(self) -> bool:
        return self._sock is not None and bool(self._server_id)

    def connect(self) -> None:
        self.close()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("", 0))
        self._client_id = secrets.token_bytes(4)
        self._server_id, self._seq, self._rpcs = b"", 0, 0
        try:
            self._pace()
            self._sock.sendto(packet(self._client_id, b"\x00" * 4, PKT_U_CONNECT, 1, _ipx() + _cp_id(self.email) + _fp(self.fp), False),
                              (self.host, self.port))
            data = self._recv(CONNECT_TIMEOUT, PKT_U_CONNECT, None)
        except (OSError, LocalError) as err:
            self.close()
            raise LocalError(f"the unit at {self.host} does not answer: {err}") from err
        notify, session = None, None
        pos = 16
        while pos + 4 <= len(data):
            ptype, plen = data[pos], struct.unpack("!H", data[pos + 2:pos + 4])[0]
            if plen < 4:
                break
            body = data[pos + 4:pos + plen]
            if ptype == PL_NOTIFY and len(body) >= 8:
                notify, session = struct.unpack("!I", body[:4])[0], body[4:8]
            pos += plen
        if notify != NOTIFY_CONNECT_OK or not session or session == b"\x00" * 4:
            self.close()
            raise LocalRejected(f"the unit refused the connection (code {notify})")
        self._server_id = session

    def close(self) -> None:
        """End the session (with the close frame, so the unit frees it right away)."""
        if self._sock is None:
            return
        if self._server_id and self._rpcs:
            try:
                self._seq += 1
                body = b"\x00\x03" + crypt_null(b"\x00\x00\x00\x03")
                self._pace()
                self._sock.sendto(packet(self._client_id, self._server_id, PKT_DATA, self._seq, body, True, flags=0x40), (self.host, self.port))
                self._recv(0.5, PKT_DATA, self._seq)
            except (OSError, LocalError):
                pass
        try:
            self._sock.close()
        finally:
            self._sock, self._server_id = None, b""

    def _rpc(self, query: bytes) -> bytes:
        if not self.connected or self._rpcs >= MAX_RPCS_PER_SESSION:
            self.connect()
        assert self._sock is not None
        self._seq += 1
        self._rpcs += 1
        self._pace()
        start = time.monotonic()
        try:
            self._sock.sendto(packet(self._client_id, self._server_id, PKT_DATA, self._seq, crypt_null(query), True), (self.host, self.port))
            data = self._recv(RPC_TIMEOUT, PKT_DATA, self._seq)
        except OSError as err:
            self.close()
            raise LocalError(str(err)) from err
        rtt = time.monotonic() - start
        self.last_rtt = rtt if self.last_rtt is None else min(self.last_rtt, rtt)
        return unwrap_data(data)

    # -- the three queries --
    def read_set_points(self, points: list[tuple[int, int]]) -> list[int]:
        out: list[int] = []
        for i in range(0, len(points), MAX_POINTS_PER_QUERY):
            part = points[i:i + MAX_POINTS_PER_QUERY]
            q = struct.pack("!IH", QUERY_SP_LIST, len(part)) + b"".join(struct.pack("!BH", o, a) for o, a in part) + b"\x01"
            resp = self._rpc(q)
            if len(resp) < 3 or resp[0] != 0:
                raise LocalError(f"set point list: status {resp[0] if resp else None}")
            n = struct.unpack("!H", resp[1:3])[0]
            if n != len(part) or len(resp) < 3 + 2 * n:
                raise LocalError("set point list: short answer")
            out += [struct.unpack("!h", resp[3 + 2 * k:5 + 2 * k])[0] for k in range(n)]
        return out

    def read_data_points(self, points: list[tuple[int, int]]) -> list[int]:
        out: list[int] = []
        for i in range(0, len(points), MAX_POINTS_PER_QUERY):
            part = points[i:i + MAX_POINTS_PER_QUERY]
            q = struct.pack("!IH", QUERY_DP_LIST, len(part)) + b"".join(struct.pack("!BI", o, a) for o, a in part) + b"\x01"
            resp = self._rpc(q)
            if len(resp) < 2:
                raise LocalError("data point list: short answer")
            n = struct.unpack("!H", resp[0:2])[0]  # this answer has no status byte
            if n != len(part) or len(resp) < 2 + 2 * n:
                raise LocalError("data point list: short answer")
            out += [struct.unpack("!h", resp[2 + 2 * k:4 + 2 * k])[0] for k in range(n)]
        return out

    def write(self, obj: int, address: int, value: int) -> None:
        resp = self._rpc(struct.pack("!IHBIH", QUERY_SP_WRITE, 1, obj, address, value & 0xFFFF) + b"\x01")
        if len(resp) != 1:
            raise LocalError(f"unexpected answer to a write: {resp.hex()}")
        if resp[0] != 1:
            raise WriteNotAcknowledged(resp[0])

    # -- the interface registers.py uses (same as the cloud client) --
    def invoke(self, query: str, request: dict) -> dict:
        items = request.get("list") or []
        if query == WRITE:
            item = items[0]
            self.write(int(item["obj"]), int(item["address"]), int(item["value"]))
            return {"response": {"status": 1}}
        points = [(int(i["obj"]), int(i["address"])) for i in items]
        if query == SET_READ:
            values = self.read_set_points(points)
        elif query == DATA_READ:
            values = self.read_data_points(points)
        else:
            raise LocalError(f"query {query} is not available locally")
        return {"response": {"data": [{"value": v} for v in values]}}
