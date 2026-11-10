"""Constants for the Proxon Control integration."""
from __future__ import annotations

DOMAIN = "proxon_control"

# parts per million: UnitOfRatio from Home Assistant 2026.10 on, the old constant (deprecated, removed in 2027.8) before
try:
    from homeassistant.const import UnitOfRatio

    PPM = UnitOfRatio.PARTS_PER_MILLION
except (ImportError, AttributeError):  # older Home Assistant
    from homeassistant.const import CONCENTRATION_PARTS_PER_MILLION as PPM
MANUFACTURER = "Proxon"
MODEL = "Frischluft-Wärmetechnik"

CONF_CONNECTION = "connection"
CONF_DEVICE_ID = "device_id"
CONF_PASSWORD = "password"
CONF_HOST = "host"
CONF_PORT = "port"
# hot water as a store for solar surplus / cheap electricity: which sensors to use (options of the integration)
CONF_SURPLUS_SENSOR = "surplus_sensor"
CONF_FEED_IN_NEGATIVE = "feed_in_negative"
CONF_PRICE_SENSOR = "price_sensor"
CONF_TOKEN = "token"  # access key of the bridge (optional)

CONNECTION_DIRECT = "direct"
CONNECTION_BRIDGE = "bridge"

DEFAULT_PORT = 8765
# how often the unit is asked for its values (seconds); adjustable under "Configure" of the integration
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 3600

DEFAULT_ROOM_NAMES = ["Wohnzimmer", "Schlafzimmer", "Kinderzimmer", "Küche", "Bad"]
