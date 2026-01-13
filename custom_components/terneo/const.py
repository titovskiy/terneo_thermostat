"""Constants for Terneo/Welrok thermostat integration."""
from enum import IntEnum

DOMAIN = "terneo"
MANUFACTURER = "Welrok/Terneo"

# Configuration keys
CONF_SERIAL = "serial"
CONF_DEVICE_TYPE = "device_type"

# Device types
DEVICE_TYPE_OLD = "old"  # oz без датчика воздуха (до июня 2025)
DEVICE_TYPE_NEW = "new"  # oz с датчиком воздуха (от июня 2025) / az

# Default values
DEFAULT_NAME = "Terneo"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_TIMEOUT = 5

# API Commands
CMD_GET_PARAMS = 1
CMD_GET_STATUS = 4

# Parameter numbers (common for both versions)
class ParamNum(IntEnum):
    """Parameter numbers for API."""
    START_AWAY_TIME = 0
    END_AWAY_TIME = 1
    MODE = 2
    CONTROL_TYPE = 3
    MANUAL_AIR = 4  # Only new version (°C*10)
    MANUAL_FLOOR = 5  # Old: °C, New: °C*10
    AWAY_AIR = 6  # Only new version (°C*10)
    AWAY_FLOOR = 7  # Old: °C, New: °C*10
    MIN_TEMP_ADVANCED = 14  # Only new version
    MAX_TEMP_ADVANCED = 15  # Only new version
    POWER = 17
    SENSOR_TYPE = 18
    HYSTERESIS = 19
    AIR_CORRECTION = 20  # Only new version
    FLOOR_CORRECTION = 21
    BRIGHTNESS = 23
    PROP_KOEF = 25
    UPPER_LIMIT = 26
    LOWER_LIMIT = 27
    MAX_SCHEDULE_PERIOD = 28
    TEMP_TEMPERATURE = 29  # Old: °C, New: °C*10
    SET_TEMPERATURE = 31  # Old: °C, New: °C*10
    UPPER_AIR_LIMIT = 33  # Only new version
    LOWER_AIR_LIMIT = 34  # Only new version
    BLE_SENSOR_INTERVAL = 35  # Only new version
    BLE_SENSOR_BIND = 36  # Only new version
    NIGHT_BRIGHT_START = 52
    NIGHT_BRIGHT_END = 53
    RELAY_ON_TIME_LIMIT = 55
    UPPER_WARNING_TEMP = 62  # Only new version
    LOWER_WARNING_TEMP = 63  # Only new version
    TIMER_PERIOD = 64  # Only new version
    TIMER_TEMPERATURE = 65  # Only new version
    START_AWAY_TIME_UTC = 66  # Only new version
    END_AWAY_TIME_UTC = 67  # Only new version
    BUTTON_MINUS_COR = 80
    BUTTON_MENU_COR = 81
    BUTTON_PLUS_COR = 82
    OFF_BUTTON_LOCK = 109
    LAN_BLOCK = 114
    CLOUD_BLOCK = 115
    NC_CONTACT_CONTROL = 117
    COOLING_CONTROL_WAY = 118
    USE_NIGHT_BRIGHT = 120
    PRE_CONTROL = 121
    WINDOW_OPEN_CONTROL = 122  # Only new version
    CHILDREN_LOCK = 124
    POWER_OFF = 125


# Control types
class ControlType(IntEnum):
    """Control type modes."""
    FLOOR = 0
    AIR = 1
    AIR_WITH_FLOOR_LIMIT = 2


# Operation modes
class OperationMode(IntEnum):
    """Operation modes."""
    SCHEDULE = 0
    MANUAL = 3
    AWAY = 4  # When away times are set


# Sensor types (resistance values)
SENSOR_TYPES = {
    0: "4.7 kΩ",
    1: "6.8 kΩ",
    2: "10 kΩ",
    3: "12 kΩ",
    4: "15 kΩ",
    5: "33 kΩ",
    6: "47 kΩ",
}

# Data types for parameters
class DataType(IntEnum):
    """Data types for API parameters."""
    CSTRING = 0
    INT8 = 1
    UINT8 = 2
    INT16 = 3
    UINT16 = 4
    INT32 = 5
    UINT32 = 6
    BOOL = 7


# Status response keys (for cmd:4)
STATUS_KEYS = {
    "t.1": "floor_temperature_raw",  # Temperature * 16
    "t.5": "setpoint_raw",  # Setpoint * 16
    "m.1": "mode",  # Operation mode
    "f.0": "relay_state",  # 0=off, 1=on
    "f.16": "power_state",  # 0=on, 1=off (firmware 2.4+)
}

# Platforms to setup
PLATFORMS = ["climate", "sensor", "switch", "number", "select"]
