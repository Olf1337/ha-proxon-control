"""Constants for the Proxon Control integration."""
from __future__ import annotations

DOMAIN = "proxon_control"

# parts per million: UnitOfRatio from Home Assistant 2026.10 on, the old constant (deprecated, removed in 2027.8) before
PPM: str
try:
    from homeassistant.const import UnitOfRatio

    PPM = UnitOfRatio.PARTS_PER_MILLION
except (ImportError, AttributeError):  # older Home Assistant: the same unit text as its CONCENTRATION_PARTS_PER_MILLION
    PPM = "ppm"
MANUFACTURER = "Proxon"
MODEL = "Frischluft-Wärmetechnik"
ROOM_MODEL = "Raumbedienelement"

CONF_CONNECTION = "connection"
CONF_DEVICE_ID = "device_id"
CONF_PASSWORD = "password"
CONF_HOST = "host"
CONF_PORT = "port"
# hot water as a store for solar surplus / cheap electricity: which sensors to use (options of the integration)
CONF_SURPLUS_SENSOR = "surplus_sensor"
CONF_FEED_IN_NEGATIVE = "feed_in_negative"
CONF_PRICE_SENSOR = "price_sensor"
# dashboard pictures: follow the device's light/dark mode, or always light / dark
CONF_PICTURE_THEME = "picture_theme"
PICTURE_THEMES = ["auto", "light", "dark"]
DEFAULT_PICTURE_THEME = "auto"
# house picture: the rooms on the upper floor (room numbers; guessed from the names until chosen), the user's own house photo
CONF_UPPER_FLOOR = "upper_floor_rooms"
CONF_HOUSE_PHOTO = "house_photo"
CONF_TOKEN = "token"  # access key of the bridge (optional)
# how the integration reaches the unit when logged in with Device ID + password:
# "auto" = home network first, Proxon server as fallback; "local" = home network only; "cloud" = Proxon server only
CONF_MODE = "mode"
MODES = ["auto", "local", "cloud"]
DEFAULT_MODE = "auto"
CONF_LOCAL_HOST = "local_host"  # IP address of the unit in the home network (optional; found automatically otherwise)

CONNECTION_DIRECT = "direct"
CONNECTION_BRIDGE = "bridge"

DEFAULT_PORT = 8765
# how often the unit is asked for its values (seconds); adjustable under "Configure" of the integration
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 10
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 3600
# read only: all values are read, nothing is written to the unit (option of the integration, off by default)
CONF_READ_ONLY = "read_only"

DEFAULT_ROOM_NAMES = ["Wohnzimmer", "Schlafzimmer", "Kinderzimmer", "Küche", "Bad"]
