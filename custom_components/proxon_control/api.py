"""The two ways the integration reaches the unit. Both are blocking; Home Assistant runs them in its executor.

DirectApi  - logs in to the Proxon server itself (needs the Nabto library to load on this system).
BridgeApi  - talks to the "Proxon Bridge" add-on over the home network (for Home Assistant OS).
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from . import registers
from .nabto import NabtoError, create_client


class ProxonError(Exception):
    """Could not talk to the unit."""


class AuthError(ProxonError):
    """Device ID or password rejected."""


class WriteNotAccepted(ProxonError):
    """The unit was written to, but reports another value when read back. `values` holds what it reports."""

    def __init__(self, key: str, wanted: float, got: float | None, values: dict) -> None:
        super().__init__(f"{key}: wanted {wanted}, the unit reports {got}")
        self.key, self.wanted, self.got, self.values = key, wanted, got, values


class DirectApi:
    def __init__(self, device_id: str, password: str, storage_dir: str) -> None:
        self.device_id = device_id.strip()
        self._password = password
        self._dir = storage_dir
        self._client = None
        self._lock = threading.Lock()

    def _connect(self):
        try:
            client = create_client(self._dir)
            client.login(self.device_id, self._password)
        except NabtoError as err:
            if err.status in (5, 6, 7, 8):  # certificate / portal login problems
                raise AuthError(str(err)) from err
            raise ProxonError(str(err)) from err
        except OSError as err:
            raise ProxonError(f"Download der Nabto-Dateien fehlgeschlagen: {err}") from err
        return client

    def _call(self, fn):
        with self._lock:
            for attempt in range(2):
                if self._client is None:
                    self._client = self._connect()
                try:
                    return fn(self._client)
                except NabtoError as err:
                    # session lost: log in again once
                    self._client.close()
                    self._client = None
                    if attempt == 1:
                        raise ProxonError(str(err)) from err
        raise ProxonError("unreachable")

    def test(self) -> dict[str, float]:
        return self.read()

    def read(self) -> dict[str, float]:
        return self._call(registers.read_all)

    def write(self, key: str, value: float) -> dict:
        """Write and read back; returns the values the unit reports afterwards."""
        try:
            return self._call(lambda c: registers.write_and_verify(c, key, value))
        except registers.WriteMismatch as err:
            raise WriteNotAccepted(key, err.wanted, err.got, err.values) from err

    def close(self) -> None:
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None


class BridgeApi:
    def __init__(self, host: str, port: int) -> None:
        h = host.strip().rstrip("/")
        if not h.startswith(("http://", "https://")):
            h = f"http://{h}"
        self.base = f"{h}:{port}" if h.count(":") < 2 else h

    def _req(self, path: str, body: dict | None = None, timeout: float = 30) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - local add-on address
                out = json.loads(resp.read().decode() or "{}")
        except urllib.error.HTTPError as err:
            body: dict = {}
            try:
                body = json.loads(err.read().decode())
                msg = body.get("error", str(err))
            except ValueError:
                msg = str(err)
            if err.code == 401:
                raise AuthError(msg) from err
            if err.code == 409:  # the unit did not take over the written value
                raise WriteNotAccepted(
                    str(body.get("key", "")), float(body.get("wanted", 0)), body.get("got"), body.get("values", {})
                ) from err
            raise ProxonError(msg) from err
        except (urllib.error.URLError, OSError, ValueError) as err:
            raise ProxonError(f"Bridge nicht erreichbar: {err}") from err
        return out

    def test(self) -> dict[str, float]:
        return self.read()

    def read(self) -> dict[str, float]:
        return {k: (v if isinstance(v, str) else float(v)) for k, v in self._req("/values").get("values", {}).items()}

    def write(self, key: str, value: float) -> dict:
        """The add-on writes and reads back; returns the values the unit reports afterwards."""
        # the add-on may wait up to 90 s for the hot-water module to take over a value
        return self._req("/write", {"key": key, "value": value}, timeout=150).get("values", {})

    def close(self) -> None:
        pass
