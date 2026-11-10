"""Constants for the Proxon Control integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "proxon_control"
MANUFACTURER = "Proxon"
MODEL = "Frischluft-Wärmetechnik"

CONF_CONNECTION = "connection"
CONF_DEVICE_ID = "device_id"
CONF_PASSWORD = "password"
CONF_HOST = "host"
CONF_PORT = "port"

CONNECTION_DIRECT = "direct"
CONNECTION_BRIDGE = "bridge"

DEFAULT_PORT = 8765
SCAN_INTERVAL = timedelta(seconds=10)

DEFAULT_ROOM_NAMES = ["Wohnzimmer", "Schlafzimmer", "Kinderzimmer", "Küche", "Bad"]
