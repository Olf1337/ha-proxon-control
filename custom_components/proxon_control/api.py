"""The ways the integration reaches the unit. All are blocking; Home Assistant runs them in its executor.

LocalApi   - directly in the home network (plain Python, no cloud while running; a portal-signed certificate is fetched once).
DirectApi  - through the Proxon server / Nabto cloud (needs the Nabto library to load on this system).
HybridApi  - local first, the cloud when the unit can't be reached locally (and local again a few minutes later).
BridgeApi  - talks to the "Proxon Bridge" add-on over the home network.
"""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request

from . import local, local_cert, registers
from .nabto import NabtoError, create_client

_LOGGER = logging.getLogger(__name__)

# connection modes of a Device ID login
MODE_AUTO = "auto"  # home network first, cloud as fallback
MODE_LOCAL = "local"  # home network only
MODE_CLOUD = "cloud"  # Proxon server / Nabto cloud only
MODES = [MODE_AUTO, MODE_LOCAL, MODE_CLOUD]
LOCAL_RETRY = 600  # seconds: after a failed local attempt, the auto mode uses the cloud this long before trying again
CERT_RENEW_AFTER = 24 * 3600  # seconds: a refused certificate younger than this is kept
PATH_KEY = "Verbindung"  # value added to the data: "local" or "cloud"


class ProxonError(Exception):
    """Could not talk to the unit."""


class AuthError(ProxonError):
    """Device ID or password rejected."""


class TokenError(ProxonError):
    """The bridge wants another access key."""


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
        return {**self._call(registers.read_all), PATH_KEY: "cloud"}

    def read_schedule(self) -> dict[str, float]:
        return self._call(registers.read_schedule)

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


class LocalApi:
    """Directly in the home network. The certificate is fetched from the Proxon portal once (with Device ID and password),
    the unit is found by a broadcast unless its address is given. One session per task, closed afterwards."""

    def __init__(self, device_id: str, password: str, storage_dir: str, host: str | None = None, port: int = local.PORT) -> None:
        self.device_id = device_id.strip()
        self._password = password
        self._dir = storage_dir
        self._fixed_host = (host or "").strip() or None
        self.host = self._fixed_host
        self.port = port
        self._fp: bytes | None = None
        self._lock = threading.Lock()

    def _certificate(self) -> bytes:
        if self._fp is None:
            try:
                self._fp = local.fingerprint(local_cert.ensure(self._dir, self.device_id, self._password))
            except local_cert.PortalRejected as err:
                raise AuthError(f"Proxon-Portal: {err}") from err
            except local_cert.CertificateError as err:
                raise ProxonError(f"Zertifikat für die lokale Verbindung: {err}") from err
        return self._fp

    def _address(self) -> str:
        if not self.host:
            found = local.discover(self.port)
            if not found:
                raise ProxonError("Die Anlage wurde im Heimnetz nicht gefunden (UDP-Port 5570).")
            self.host = found[0].host
            _LOGGER.info("Proxon unit found in the home network at %s", self.host)
        return self.host

    def _call(self, fn):
        with self._lock:
            client = local.LocalClient(self._address(), self.port, self.device_id, self._certificate())
            try:
                return fn(client)
            except local.LocalRejected as err:
                # the unit doesn't know this certificate. A new one only helps if this one is older (the unit learns certificates
                # while online); renewed at most once a day, so the portal isn't asked again and again.
                age = local_cert.age(self._dir, self.device_id)
                if age is None or age > CERT_RENEW_AFTER:
                    local_cert.forget(self._dir, self.device_id)
                    self._fp = None
                    raise ProxonError(f"{err}. Ein neues Zertifikat wird beim nächsten Versuch geholt.") from err
                raise ProxonError(f"{err}. Die Anlage kennt das neue Zertifikat noch nicht - sie lernt es, wenn sie online ist.") from err
            except local.LocalError as err:
                if not self._fixed_host:
                    self.host = None  # the unit may have a new address: look again next time
                raise ProxonError(str(err)) from err
            finally:
                client.close()

    def test(self) -> dict[str, float]:
        return self.read()

    def read(self) -> dict[str, float]:
        return {**self._call(registers.read_all), PATH_KEY: "local"}

    def read_schedule(self) -> dict[str, float]:
        return self._call(registers.read_schedule)

    def write(self, key: str, value: float) -> dict:
        try:
            return self._call(lambda c: registers.write_and_verify(c, key, value))
        except registers.WriteMismatch as err:
            raise WriteNotAccepted(key, err.wanted, err.got, err.values) from err

    def close(self) -> None:
        pass


class HybridApi:
    """Home network first, the cloud as fallback (mode "auto"), or only one of them."""

    def __init__(self, mode: str, local_api: LocalApi | None, cloud_api: DirectApi | None) -> None:
        self.mode = mode
        self.local = local_api
        self.cloud = cloud_api
        self.path: str | None = None
        self._local_failed_at: float | None = None

    def _ways(self) -> list:
        if self.mode == MODE_LOCAL or self.cloud is None:
            return [self.local]
        if self.mode == MODE_CLOUD or self.local is None:
            return [self.cloud]
        local_paused = self._local_failed_at is not None and time.monotonic() - self._local_failed_at < LOCAL_RETRY
        return [self.cloud] if local_paused else [self.local, self.cloud]

    def _run(self, action):
        last: ProxonError | None = None
        ways = self._ways()
        for api in ways:
            try:
                result = action(api)
            except WriteNotAccepted:
                raise  # the unit answered but didn't take over the value: the other way wouldn't change that
            except ProxonError as err:
                if isinstance(err, AuthError) and api is ways[-1]:
                    raise  # Device ID / password wrong: Home Assistant asks to log in again
                last = err
                if api is self.local and self.mode == MODE_AUTO and self.cloud is not None:
                    if self._local_failed_at is None:
                        _LOGGER.warning("Proxon: home network connection failed (%s) - using the Proxon server for now", err)
                    self._local_failed_at = time.monotonic()
                continue
            if api is self.local:
                if self._local_failed_at is not None:
                    _LOGGER.info("Proxon: home network connection works again")
                self._local_failed_at = None
            self.path = "local" if api is self.local else "cloud"
            return result
        raise last or ProxonError("keine Verbindung")

    def test(self) -> dict[str, float]:
        return self._run(lambda api: api.test())

    def read(self) -> dict[str, float]:
        data = self._run(lambda api: api.read())
        return {**data, PATH_KEY: self.path or "cloud"}

    def read_schedule(self) -> dict[str, float]:
        return self._run(lambda api: api.read_schedule())

    def write(self, key: str, value: float) -> dict:
        return self._run(lambda api: api.write(key, value))

    def close(self) -> None:
        for api in (self.local, self.cloud):
            if api is not None:
                api.close()


class BridgeApi:
    def __init__(self, host: str, port: int, token: str | None = None) -> None:
        self._token = (token or "").strip()
        h = host.strip().rstrip("/")
        if not h.startswith(("http://", "https://")):
            h = f"http://{h}"
        self.base = f"{h}:{port}" if h.count(":") < 2 else h

    def _req(self, path: str, body: dict | None = None, timeout: float = 30) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        req = urllib.request.Request(self.base + path, data=data, headers=headers)
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
            if err.code == 403:  # access key of the bridge missing or wrong
                raise TokenError(msg) from err
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

    def read_schedule(self) -> dict[str, float]:
        """The add-on reads the weekly schedule itself (every few minutes) and includes it in /values."""
        return {}

    def write(self, key: str, value: float) -> dict:
        """The add-on writes and reads back; returns the values the unit reports afterwards."""
        # the add-on may wait up to 90 s for the hot-water module to take over a value
        return self._req("/write", {"key": key, "value": value}, timeout=150).get("values", {})

    def close(self) -> None:
        pass


def connect(device_id: str, password: str, storage_dir: str, mode: str = MODE_AUTO, host: str | None = None,
            cloud_possible: bool = True) -> HybridApi:
    """The way to the unit for a login with Device ID + password. Without Nabto's library (e.g. Raspberry Pi) only the
    home network is possible, whatever the mode says."""
    cloud = DirectApi(device_id, password, storage_dir) if mode != MODE_LOCAL and cloud_possible else None
    local_api = LocalApi(device_id, password, storage_dir, host) if mode != MODE_CLOUD or cloud is None else None
    return HybridApi(mode, local_api, cloud)
