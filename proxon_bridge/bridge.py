"""Proxon Bridge add-on: logs in to the Proxon server (Nabto) and offers the values on port 8765.

GET  /values  -> {"device_id": "...", "values": {...}, "error": null}
POST /write   <- {"key": "Luefterstufe", "value": 3}
The Proxon Control integration reads and writes through this when it can't load the Nabto library itself.
"""
from __future__ import annotations

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
POLL_SECONDS = 10


class Bridge:
    def __init__(self, device_id: str, password: str) -> None:
        self.device_id = device_id.strip()
        self.password = password
        self.values: dict[str, float] = {}
        self.error: str | None = "starting"
        self.auth_failed = False
        self.client: NabtoClient | None = None
        self.lock = threading.Lock()

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
            self.values = self._run(registers.read_all)
            self.error = None
            self.auth_failed = False
        except NabtoError as err:
            self.error = str(err)
            log.warning("read failed: %s", err)

    def write(self, key: str, value: float) -> None:
        self._run(lambda c: registers.write_value(c, key, value))
        self.values[key] = float(value)


def make_handler(bridge: Bridge):
    class Handler(BaseHTTPRequestHandler):
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
            if self.path.rstrip("/") != "/values":
                return self._send(404, {"error": "not found"})
            if bridge.error and not bridge.values:
                return self._send(401 if bridge.auth_failed else 503, {"error": bridge.error})
            self._send(200, {"device_id": bridge.device_id, "values": bridge.values, "error": bridge.error})

        def do_POST(self):
            if self.path.rstrip("/") != "/write":
                return self._send(404, {"error": "not found"})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                key, value = body["key"], float(body["value"])
                if key not in registers.BY_KEY or registers.BY_KEY[key].write is None:
                    return self._send(400, {"error": f"{key} kann nicht geschrieben werden"})
                bridge.write(key, value)
            except (KeyError, ValueError, TypeError) as err:
                return self._send(400, {"error": f"ungültige Anfrage: {err}"})
            except NabtoError as err:
                return self._send(502, {"error": str(err)})
            self._send(200, {"ok": True})

    return Handler


def main() -> None:
    with open(OPTIONS, encoding="utf-8") as f:
        opts = json.load(f)
    if not opts.get("device_id") or not opts.get("password"):
        log.error("Bitte Device ID und Passwort in der Add-on-Konfiguration eintragen.")
    bridge = Bridge(opts.get("device_id", ""), opts.get("password", ""))

    def loop() -> None:
        while True:
            if bridge.device_id and bridge.password:
                bridge.poll()
            time.sleep(POLL_SECONDS)

    threading.Thread(target=loop, daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", PORT), make_handler(bridge))  # noqa: S104 - add-on port
    log.info("Proxon Bridge listening on port %s", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
