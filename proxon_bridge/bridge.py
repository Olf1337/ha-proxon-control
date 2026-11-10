"""Proxon Bridge add-on: logs in to the Proxon server (Nabto) and offers the values on port 8765.

GET  /values  -> {"device_id": "...", "values": {...}, "error": null}
With an access key set (add-on option "token" or PROXON_TOKEN), every request needs "Authorization: Bearer <key>", otherwise 403.
POST /write   <- {"key": "Luefterstufe", "value": 3}  -> {"ok": true, "values": {…read back…}}, or 409 if the unit did not take over the value
The Proxon Control integration reads and writes through this when it can't load the Nabto library itself.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import registers
from nabto import NabtoClient, NabtoError, ensure_library

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("proxon-bridge")

OPTIONS = os.environ.get("PROXON_OPTIONS", "/data/options.json")
DATA = os.environ.get("PROXON_DATA", "/data")
PORT = int(os.environ.get("PROXON_PORT", "8765"))
POLL_SECONDS = 10  # default; adjustable with the add-on option "poll_seconds"
SCHEDULE_SECONDS = 300  # the weekly schedule changes rarely: read it every 5 minutes


class Bridge:
    def __init__(self, device_id: str, password: str) -> None:
        self.device_id = device_id.strip()
        self.password = password
        self.values: dict[str, float] = {}
        self.error: str | None = "starting"
        self.auth_failed = False
        self.client: NabtoClient | None = None
        self.lock = threading.Lock()
        self.schedule: dict[str, float] = {}
        self.schedule_read_at: float | None = None

    def _client(self) -> NabtoClient:
        if self.client is None:
            c = NabtoClient(ensure_library(os.path.join(DATA, "lib")), os.path.join(DATA, "home"))
            c.login(self.device_id, self.password)
            self.client = c
            log.info("logged in to %s", self.device_id)
        return self.client

    def _run(self, fn):
        with self.lock:
            try:
                return fn(self._client())
            except NabtoError as err:
                if self.client:
                    self.client.close()
                self.client = None
                self.auth_failed = err.status in (5, 6, 7, 8)
                raise

    def poll(self) -> None:
        try:
            values = self._run(registers.read_all)
            if self.schedule_read_at is None or time.monotonic() - self.schedule_read_at >= SCHEDULE_SECONDS:
                try:
                    self.schedule = self._run(registers.read_schedule)
                    self.schedule_read_at = time.monotonic()
                except NabtoError as err:
                    log.warning("reading the weekly schedule failed: %s", err)
            self.values = {**values, **self.schedule}
            self.error = None
            self.auth_failed = False
        except NabtoError as err:
            self.error = str(err)
            log.warning("read failed: %s", err)

    def write(self, key: str, value: float) -> dict:
        """Write and read back; returns the values the unit reports afterwards (raises registers.WriteMismatch if it holds another value)."""
        try:
            got = self._run(lambda c: registers.write_and_verify(c, key, value))
        except registers.WriteMismatch as err:
            self.values.update(err.values)
            raise
        self.values.update(got)
        self.schedule.update({k: v for k, v in got.items() if k in registers.SCHEDULE_KEYS})
        return got


def make_handler(bridge: Bridge, token: str = ""):
    class Handler(BaseHTTPRequestHandler):
        def _allowed(self) -> bool:
            if not token:
                return True
            sent = self.headers.get("Authorization", "")
            if hmac.compare_digest(sent.encode(), f"Bearer {token}".encode()):
                return True
            self._send(403, {"error": "Zugriffsschlüssel fehlt oder ist falsch"})
            return False

        def log_message(self, fmt, *args):  # quieter log
            log.debug(fmt, *args)

        def _send(self, code: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self._allowed():
                return
            if self.path.rstrip("/") != "/values":
                return self._send(404, {"error": "not found"})
            if bridge.error and not bridge.values:
                return self._send(401 if bridge.auth_failed else 503, {"error": bridge.error})
            self._send(200, {"device_id": bridge.device_id, "values": bridge.values, "error": bridge.error})

        def do_POST(self):
            if not self._allowed():
                return
            if self.path.rstrip("/") != "/write":
                return self._send(404, {"error": "not found"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                key, value = body["key"], float(body["value"])
                if key not in registers.BY_KEY or registers.BY_KEY[key].write is None:
                    return self._send(400, {"error": f"{key} kann nicht geschrieben werden"})
                got = bridge.write(key, value)
            except (KeyError, ValueError, TypeError) as err:
                return self._send(400, {"error": f"ungültige Anfrage: {err}"})
            except registers.WriteMismatch as err:
                # the unit did not take over the value
                return self._send(409, {"error": str(err), "key": err.key, "wanted": err.wanted, "got": err.got, "values": err.values})
            except NabtoError as err:
                return self._send(502, {"error": str(err)})
            self._send(200, {"ok": True, "values": got})

    return Handler


def load_options() -> dict:
    """Options of the Home Assistant add-on, or - when run as a plain Docker container, e.g. on a NAS for a Raspberry Pi -
    the environment variables PROXON_DEVICE_ID, PROXON_PASSWORD, PROXON_POLL_SECONDS and PROXON_TOKEN."""
    if os.path.exists(OPTIONS):
        with open(OPTIONS, encoding="utf-8") as f:
            return json.load(f)
    return {
        "device_id": os.environ.get("PROXON_DEVICE_ID", ""),
        "password": os.environ.get("PROXON_PASSWORD", ""),
        "poll_seconds": os.environ.get("PROXON_POLL_SECONDS", POLL_SECONDS),
        "token": os.environ.get("PROXON_TOKEN", ""),
    }


def main() -> None:
    opts = load_options()
    os.makedirs(DATA, exist_ok=True)
    if not opts.get("device_id") or not opts.get("password"):
        log.error("Bitte Device ID und Passwort in der Add-on-Konfiguration eintragen.")
    bridge = Bridge(opts.get("device_id", ""), opts.get("password", ""))
    poll_seconds = max(5, min(3600, int(opts.get("poll_seconds", POLL_SECONDS))))

    def loop() -> None:
        while True:
            if bridge.device_id and bridge.password:
                bridge.poll()
            time.sleep(poll_seconds)

    threading.Thread(target=loop, daemon=True).start()
    token = str(opts.get("token") or "").strip()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), make_handler(bridge, token))  # noqa: S104 - add-on port
    log.info("Proxon Bridge listening on port %s (%s)", PORT, "with access key" if token else "without access key")
    server.serve_forever()


if __name__ == "__main__":
    main()
