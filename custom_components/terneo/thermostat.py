"""Terneo/Welrok Thermostat API client."""
import logging
import time
from typing import Any

import requests

from .const import (
    ParamNum,
    ControlType,
    OperationMode,
    DataType,
    DEVICE_TYPE_OLD,
    DEVICE_TYPE_NEW,
    CMD_GET_PARAMS,
    CMD_GET_STATUS,
)

_LOGGER = logging.getLogger(__name__)


class TerneoThermostat:
    """
    A class for interacting with the Terneo/Welrok Thermostat's HTTP API.
    
    Supports both old (before June 2025) and new (from June 2025) versions.
    
    Parameters
    ----------
    serial_number : str
        Serial Number of device
    host : str
        Hostname or IP address.
    device_type : str, optional
        Device type: 'old' or 'new'
    """

    def __init__(
        self,
        serial_number: str,
        host: str,
        device_type: str = DEVICE_TYPE_OLD,
    ):
        """Initialize the thermostat."""
        self.sn = serial_number
        self.device_type = device_type
        self._is_new_version = device_type == DEVICE_TYPE_NEW
        
        self._base_url = f"http://{host}/{{endpoint}}.cgi"
        self._last_request = time.time()
        
        # Cached state
        self._available = False
        self._parameters: dict[int, Any] = {}
        self._status: dict[str, Any] = {}
        
        # Derived state
        self._setpoint: float | None = None
        self._floor_temperature: float | None = None
        self._air_temperature: float | None = None
        self._mode: int | None = None
        self._relay_state: bool | None = None
        self._power_on: bool | None = None
        
        # Verify connection
        try:
            r = requests.get(
                self._base_url.format(endpoint="api.html")[:-4],
                timeout=5
            )
            if r.status_code == 200:
                self._available = True
        except Exception as e:
            _LOGGER.error("Connection to Thermostat failed: %s", e)
            raise

    def _get_url(self, endpoint: str) -> str:
        """Get the full URL for an endpoint."""
        return self._base_url.format(endpoint=endpoint)

    def _post(self, endpoint: str = "api", **kwargs) -> dict | bool:
        """Perform a POST request with rate limiting."""
        kwergs = {}
        kwergs.update(kwargs)

        # Rate limiting
        start_time = time.time()
        if start_time - self._last_request < 1:
            time.sleep(1)

        try:
            r = requests.post(self._get_url(endpoint), timeout=5, **kwergs)
        except Exception as e:
            self._available = False
            self._last_request = time.time()
            _LOGGER.error("POST request failed: %s", e)
            return False
        
        self._last_request = time.time()
        
        try:
            content = r.json()
        except Exception as e:
            _LOGGER.error("Failed to parse JSON response: %s", e)
            return False

        if content.get("status") == "timeout":
            _LOGGER.warning("Terneo timeout for request: %s", kwargs.get("json", {}))
            return False
        
        self._available = True
        return content

    def get_parameters(self) -> dict | bool:
        """Get all parameters from the device."""
        result = self._post(json={"cmd": CMD_GET_PARAMS, "sn": self.sn})
        if result and "par" in result:
            self._parameters = {p[0]: (p[1], p[2]) for p in result["par"]}
            return result
        return False

    def set_parameters(self, params: list[list]) -> dict | bool:
        """Set parameters on the device."""
        return self._post(json={"sn": self.sn, "par": params})

    def get_status(self) -> dict | bool:
        """Get the status dictionary from the thermostat."""
        result = self._post(json={"cmd": CMD_GET_STATUS, "sn": self.sn})
        if result:
            self._status = result
        return result

    def restart(self) -> bool:
        """Restart the device."""
        result = self._post(endpoint="test", json={"cmd": "restart"})
        if result and result.get("success") == "true":
            _LOGGER.info("Device restart command sent successfully")
            return True
        _LOGGER.warning("Failed to send restart command")
        return False

    def _get_param_value(self, param_num: int) -> Any | None:
        """Get a parameter value from cache."""
        if param_num in self._parameters:
            data_type, value = self._parameters[param_num]
            return self._convert_value(value, data_type)
        return None

    @staticmethod
    def _convert_value(value: str, data_type: int) -> Any:
        """Convert string value to appropriate type."""
        if data_type == DataType.BOOL:
            return value == "1"
        elif data_type in (DataType.INT8, DataType.INT16, DataType.INT32):
            return int(value)
        elif data_type in (DataType.UINT8, DataType.UINT16, DataType.UINT32):
            return int(value)
        return value

    def _temperature_from_api(self, value: int, param_num: int) -> float:
        """Convert API temperature value to Celsius."""
        if self._is_new_version:
            # New version uses °C*10 for most temperature parameters
            return value / 10.0
        else:
            # Old version uses °C directly
            return float(value)

    def _temperature_to_api(self, value: float, param_num: int) -> str:
        """Convert Celsius to API temperature value."""
        if self._is_new_version:
            return str(int(value * 10))
        else:
            return str(int(value))

    # Properties

    @property
    def available(self) -> bool:
        """Return if device is available."""
        return self._available

    @property
    def is_new_version(self) -> bool:
        """Return if device is new version with air sensor."""
        return self._is_new_version

    @property
    def power_on(self) -> bool | None:
        """Return if device is powered on."""
        return self._power_on

    @property
    def floor_temperature(self) -> float | None:
        """Current floor temperature in Celsius."""
        return self._floor_temperature

    @property
    def air_temperature(self) -> float | None:
        """Current air temperature in Celsius (new version only)."""
        return self._air_temperature

    @property
    def setpoint(self) -> float | None:
        """Current temperature setpoint in Celsius."""
        return self._setpoint

    @property
    def mode(self) -> int | None:
        """Current operation mode."""
        return self._mode

    @property
    def relay_state(self) -> bool | None:
        """Current relay state (heating active)."""
        return self._relay_state

    @property
    def control_type(self) -> int | None:
        """Current control type (floor/air/air with floor limit)."""
        return self._get_param_value(ParamNum.CONTROL_TYPE)

    @property
    def hysteresis(self) -> float | None:
        """Current hysteresis value in Celsius."""
        value = self._get_param_value(ParamNum.HYSTERESIS)
        if value is not None:
            return value / 10.0
        return None

    @property
    def children_lock(self) -> bool | None:
        """Return if children lock is enabled."""
        return self._get_param_value(ParamNum.CHILDREN_LOCK)

    @property
    def cooling_mode(self) -> bool | None:
        """Return if cooling mode is enabled (vs heating)."""
        return self._get_param_value(ParamNum.COOLING_CONTROL_WAY)

    @property
    def upper_limit(self) -> int | None:
        """Maximum floor temperature setpoint."""
        return self._get_param_value(ParamNum.UPPER_LIMIT)

    @property
    def lower_limit(self) -> int | None:
        """Minimum floor temperature setpoint."""
        return self._get_param_value(ParamNum.LOWER_LIMIT)

    @property
    def upper_air_limit(self) -> int | None:
        """Maximum air temperature setpoint (new version only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.UPPER_AIR_LIMIT)
        return None

    @property
    def lower_air_limit(self) -> int | None:
        """Minimum air temperature setpoint (new version only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.LOWER_AIR_LIMIT)
        return None

    @property
    def brightness(self) -> int | None:
        """Display brightness (0-9)."""
        return self._get_param_value(ParamNum.BRIGHTNESS)

    @property
    def use_night_brightness(self) -> bool | None:
        """Return if night brightness mode is enabled."""
        return self._get_param_value(ParamNum.USE_NIGHT_BRIGHT)

    @property
    def pre_control(self) -> bool | None:
        """Return if pre-heating is enabled."""
        return self._get_param_value(ParamNum.PRE_CONTROL)

    @property
    def window_open_control(self) -> bool | None:
        """Return if window open detection is enabled (new version only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.WINDOW_OPEN_CONTROL)
        return None

    @property
    def lan_block(self) -> bool | None:
        """Return if LAN API changes are blocked."""
        return self._get_param_value(ParamNum.LAN_BLOCK)

    @property
    def cloud_block(self) -> bool | None:
        """Return if cloud changes are blocked."""
        return self._get_param_value(ParamNum.CLOUD_BLOCK)

    @property
    def power_watts(self) -> int | None:
        """Connected power in Watts."""
        value = self._get_param_value(ParamNum.POWER)
        if value is not None:
            if value <= 150:
                return value * 10
            else:
                return value * 20 - 1500
        return None

    @property
    def floor_correction(self) -> float | None:
        """Floor sensor correction in Celsius."""
        value = self._get_param_value(ParamNum.FLOOR_CORRECTION)
        if value is not None:
            return value / 10.0
        return None

    @property
    def air_correction(self) -> float | None:
        """Air sensor correction in Celsius (new version only)."""
        if self._is_new_version:
            value = self._get_param_value(ParamNum.AIR_CORRECTION)
            if value is not None:
                return value / 10.0
        return None

    @property
    def sensor_type(self) -> int | None:
        """Temperature sensor type (resistance)."""
        return self._get_param_value(ParamNum.SENSOR_TYPE)

    @property
    def prop_koef(self) -> int | None:
        """Proportional mode coefficient (minutes of load in 30-min cycle)."""
        return self._get_param_value(ParamNum.PROP_KOEF)

    @property
    def nc_contact_control(self) -> bool | None:
        """Return if relay is inverted (NC mode)."""
        return self._get_param_value(ParamNum.NC_CONTACT_CONTROL)

    @property
    def night_bright_start(self) -> int | None:
        """Night brightness start time (minutes from 00:00)."""
        return self._get_param_value(ParamNum.NIGHT_BRIGHT_START)

    @property
    def night_bright_end(self) -> int | None:
        """Night brightness end time (minutes from 00:00)."""
        return self._get_param_value(ParamNum.NIGHT_BRIGHT_END)

    @property
    def relay_on_time_limit(self) -> int | None:
        """Continuous heating time limit for alarm (hours, read-only)."""
        return self._get_param_value(ParamNum.RELAY_ON_TIME_LIMIT)

    @property
    def button_minus_cor(self) -> int | None:
        """Minus button sensitivity correction (-30 to 30)."""
        return self._get_param_value(ParamNum.BUTTON_MINUS_COR)

    @property
    def button_menu_cor(self) -> int | None:
        """Menu button sensitivity correction (-30 to 30)."""
        return self._get_param_value(ParamNum.BUTTON_MENU_COR)

    @property
    def button_plus_cor(self) -> int | None:
        """Plus button sensitivity correction (-30 to 30)."""
        return self._get_param_value(ParamNum.BUTTON_PLUS_COR)

    @property
    def off_button_lock(self) -> bool | None:
        """Return if automatic button lock is disabled (read-only)."""
        return self._get_param_value(ParamNum.OFF_BUTTON_LOCK)

    @property
    def min_temp_advanced(self) -> int | None:
        """Min floor temp limit in air control mode (new version only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.MIN_TEMP_ADVANCED)
        return None

    @property
    def max_temp_advanced(self) -> int | None:
        """Max floor temp limit in air control mode (new version only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.MAX_TEMP_ADVANCED)
        return None

    @property
    def ble_sensor_interval(self) -> int | None:
        """Wireless air sensor poll interval in minutes (new version only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.BLE_SENSOR_INTERVAL)
        return None

    @property
    def ble_sensor_bind(self) -> bool | None:
        """Return if wireless air sensor is connected (new version, read-only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.BLE_SENSOR_BIND)
        return None

    @property
    def upper_warning_temp(self) -> int | None:
        """Upper temperature threshold for alarm (new version only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.UPPER_WARNING_TEMP)
        return None

    @property
    def lower_warning_temp(self) -> int | None:
        """Lower temperature threshold for alarm (new version only)."""
        if self._is_new_version:
            return self._get_param_value(ParamNum.LOWER_WARNING_TEMP)
        return None

    @property
    def away_floor_temperature(self) -> float | None:
        """Away mode floor temperature setpoint."""
        value = self._get_param_value(ParamNum.AWAY_FLOOR)
        if value is not None:
            return self._temperature_from_api(value, ParamNum.AWAY_FLOOR)
        return None

    @property
    def away_air_temperature(self) -> float | None:
        """Away mode air temperature setpoint (new version only)."""
        if self._is_new_version:
            value = self._get_param_value(ParamNum.AWAY_AIR)
            if value is not None:
                return self._temperature_from_api(value, ParamNum.AWAY_AIR)
        return None

    @property
    def manual_floor_temperature(self) -> float | None:
        """Manual mode floor temperature setpoint."""
        value = self._get_param_value(ParamNum.MANUAL_FLOOR)
        if value is not None:
            return self._temperature_from_api(value, ParamNum.MANUAL_FLOOR)
        return None

    @property
    def manual_air_temperature(self) -> float | None:
        """Manual mode air temperature setpoint (new version only)."""
        if self._is_new_version:
            value = self._get_param_value(ParamNum.MANUAL_AIR)
            if value is not None:
                return self._temperature_from_api(value, ParamNum.MANUAL_AIR)
        return None

    # Setters

    def set_setpoint(self, temperature: float) -> bool:
        """Set target temperature."""
        control_type = self.control_type or ControlType.FLOOR
        
        if control_type == ControlType.FLOOR:
            param = ParamNum.MANUAL_FLOOR
        else:
            param = ParamNum.MANUAL_AIR if self._is_new_version else ParamNum.MANUAL_FLOOR
        
        temp_value = self._temperature_to_api(temperature, param)
        
        # Turn on, set manual mode, and set temperature
        result = self.set_parameters([
            [ParamNum.POWER_OFF, DataType.BOOL, "0"],
            [ParamNum.MODE, DataType.UINT8, str(OperationMode.MANUAL)],
            [param, DataType.INT8 if not self._is_new_version else DataType.INT16, temp_value],
        ])
        
        if result:
            self._setpoint = temperature
        return bool(result)

    def set_mode(self, mode: int) -> bool:
        """Set operation mode (0=schedule, 3=manual)."""
        if mode not in [OperationMode.SCHEDULE, OperationMode.MANUAL]:
            raise ValueError("Mode must be 0 (schedule) or 3 (manual)")
        
        # Map to API values: schedule=0, manual=1 for mode parameter
        api_mode = 0 if mode == OperationMode.SCHEDULE else 1
        
        result = self.set_parameters([
            [ParamNum.POWER_OFF, DataType.BOOL, "0"],
            [ParamNum.MODE, DataType.UINT8, str(api_mode)],
        ])
        return bool(result)

    def turn_on(self) -> bool:
        """Turn on the thermostat."""
        result = self.set_parameters([[ParamNum.POWER_OFF, DataType.BOOL, "0"]])
        if result:
            self._power_on = True
        return bool(result)

    def turn_off(self) -> bool:
        """Turn off the thermostat."""
        result = self.set_parameters([[ParamNum.POWER_OFF, DataType.BOOL, "1"]])
        if result:
            self._power_on = False
        return bool(result)

    def set_children_lock(self, enabled: bool) -> bool:
        """Set children lock."""
        result = self.set_parameters([
            [ParamNum.CHILDREN_LOCK, DataType.BOOL, "1" if enabled else "0"]
        ])
        return bool(result)

    def set_cooling_mode(self, enabled: bool) -> bool:
        """Set cooling mode (vs heating)."""
        result = self.set_parameters([
            [ParamNum.COOLING_CONTROL_WAY, DataType.BOOL, "1" if enabled else "0"]
        ])
        return bool(result)

    def set_control_type(self, control_type: int) -> bool:
        """Set control type (0=floor, 1=air, 2=air with floor limit)."""
        if control_type not in [0, 1, 2]:
            raise ValueError("Control type must be 0, 1, or 2")
        
        result = self.set_parameters([
            [ParamNum.CONTROL_TYPE, DataType.UINT8, str(control_type)]
        ])
        return bool(result)

    def set_hysteresis(self, value: float) -> bool:
        """Set hysteresis in Celsius."""
        api_value = int(value * 10)
        result = self.set_parameters([
            [ParamNum.HYSTERESIS, DataType.UINT8, str(api_value)]
        ])
        return bool(result)

    def set_brightness(self, value: int) -> bool:
        """Set display brightness (0-9)."""
        if not 0 <= value <= 9:
            raise ValueError("Brightness must be between 0 and 9")
        
        result = self.set_parameters([
            [ParamNum.BRIGHTNESS, DataType.UINT8, str(value)]
        ])
        return bool(result)

    def set_pre_control(self, enabled: bool) -> bool:
        """Set pre-heating mode."""
        result = self.set_parameters([
            [ParamNum.PRE_CONTROL, DataType.BOOL, "1" if enabled else "0"]
        ])
        return bool(result)

    def set_window_open_control(self, enabled: bool) -> bool:
        """Set window open detection (new version only)."""
        if not self._is_new_version:
            _LOGGER.warning("Window open control is only available on new version")
            return False
        
        result = self.set_parameters([
            [ParamNum.WINDOW_OPEN_CONTROL, DataType.BOOL, "1" if enabled else "0"]
        ])
        return bool(result)

    def set_use_night_brightness(self, enabled: bool) -> bool:
        """Set night brightness mode."""
        result = self.set_parameters([
            [ParamNum.USE_NIGHT_BRIGHT, DataType.BOOL, "1" if enabled else "0"]
        ])
        return bool(result)

    def set_floor_limits(self, lower: int, upper: int) -> bool:
        """Set floor temperature limits."""
        result = self.set_parameters([
            [ParamNum.LOWER_LIMIT, DataType.INT8, str(lower)],
            [ParamNum.UPPER_LIMIT, DataType.INT8, str(upper)],
        ])
        return bool(result)

    def set_air_limits(self, lower: int, upper: int) -> bool:
        """Set air temperature limits (new version only)."""
        if not self._is_new_version:
            _LOGGER.warning("Air limits are only available on new version")
            return False
        
        result = self.set_parameters([
            [ParamNum.LOWER_AIR_LIMIT, DataType.INT8, str(lower)],
            [ParamNum.UPPER_AIR_LIMIT, DataType.INT8, str(upper)],
        ])
        return bool(result)

    def set_sensor_type(self, sensor_type: int) -> bool:
        """Set temperature sensor type (0-6)."""
        if not 0 <= sensor_type <= 6:
            raise ValueError("Sensor type must be between 0 and 6")
        
        result = self.set_parameters([
            [ParamNum.SENSOR_TYPE, DataType.UINT8, str(sensor_type)]
        ])
        return bool(result)

    def set_prop_koef(self, value: int) -> bool:
        """Set proportional mode coefficient (minutes in 30-min cycle)."""
        if not 0 <= value <= 30:
            raise ValueError("Proportional coefficient must be between 0 and 30")
        
        result = self.set_parameters([
            [ParamNum.PROP_KOEF, DataType.UINT8, str(value)]
        ])
        return bool(result)

    def set_nc_contact_control(self, enabled: bool) -> bool:
        """Set relay inversion (NC mode)."""
        result = self.set_parameters([
            [ParamNum.NC_CONTACT_CONTROL, DataType.BOOL, "1" if enabled else "0"]
        ])
        return bool(result)

    def set_night_brightness_time(self, start_minutes: int, end_minutes: int) -> bool:
        """Set night brightness time range (minutes from 00:00)."""
        if not 0 <= start_minutes <= 1439 or not 0 <= end_minutes <= 1439:
            raise ValueError("Time must be between 0 and 1439 minutes")
        
        result = self.set_parameters([
            [ParamNum.NIGHT_BRIGHT_START, DataType.UINT16, str(start_minutes)],
            [ParamNum.NIGHT_BRIGHT_END, DataType.UINT16, str(end_minutes)],
        ])
        return bool(result)

    def set_button_corrections(self, minus: int, menu: int, plus: int) -> bool:
        """Set button sensitivity corrections (-30 to 30)."""
        for val in [minus, menu, plus]:
            if not -30 <= val <= 30:
                raise ValueError("Button correction must be between -30 and 30")
        
        result = self.set_parameters([
            [ParamNum.BUTTON_MINUS_COR, DataType.INT8, str(minus)],
            [ParamNum.BUTTON_MENU_COR, DataType.INT8, str(menu)],
            [ParamNum.BUTTON_PLUS_COR, DataType.INT8, str(plus)],
        ])
        return bool(result)

    def set_floor_correction(self, value: float) -> bool:
        """Set floor sensor correction in Celsius."""
        api_value = int(value * 10)
        if not -127 <= api_value <= 127:
            raise ValueError("Floor correction must be between -12.7 and 12.7")
        
        result = self.set_parameters([
            [ParamNum.FLOOR_CORRECTION, DataType.INT8, str(api_value)]
        ])
        return bool(result)

    def set_air_correction(self, value: float) -> bool:
        """Set air sensor correction in Celsius (new version only)."""
        if not self._is_new_version:
            _LOGGER.warning("Air correction is only available on new version")
            return False
        
        api_value = int(value * 10)
        if not -127 <= api_value <= 127:
            raise ValueError("Air correction must be between -12.7 and 12.7")
        
        result = self.set_parameters([
            [ParamNum.AIR_CORRECTION, DataType.INT8, str(api_value)]
        ])
        return bool(result)

    def set_lan_block(self, enabled: bool) -> bool:
        """Set LAN API block."""
        result = self.set_parameters([
            [ParamNum.LAN_BLOCK, DataType.BOOL, "1" if enabled else "0"]
        ])
        return bool(result)

    def set_cloud_block(self, enabled: bool) -> bool:
        """Set cloud block."""
        result = self.set_parameters([
            [ParamNum.CLOUD_BLOCK, DataType.BOOL, "1" if enabled else "0"]
        ])
        return bool(result)

    def set_advanced_floor_limits(self, min_temp: int, max_temp: int) -> bool:
        """Set floor temp limits for air control mode (new version only)."""
        if not self._is_new_version:
            _LOGGER.warning("Advanced floor limits are only available on new version")
            return False
        
        result = self.set_parameters([
            [ParamNum.MIN_TEMP_ADVANCED, DataType.INT8, str(min_temp)],
            [ParamNum.MAX_TEMP_ADVANCED, DataType.INT8, str(max_temp)],
        ])
        return bool(result)

    def set_ble_sensor_interval(self, minutes: int) -> bool:
        """Set wireless sensor poll interval in minutes (new version only)."""
        if not self._is_new_version:
            _LOGGER.warning("BLE sensor interval is only available on new version")
            return False
        
        if not 1 <= minutes <= 60:
            raise ValueError("BLE sensor interval must be between 1 and 60 minutes")
        
        result = self.set_parameters([
            [ParamNum.BLE_SENSOR_INTERVAL, DataType.UINT8, str(minutes)]
        ])
        return bool(result)

    def set_warning_temps(self, lower: int, upper: int) -> bool:
        """Set temperature warning thresholds (new version only)."""
        if not self._is_new_version:
            _LOGGER.warning("Warning temps are only available on new version")
            return False
        
        result = self.set_parameters([
            [ParamNum.LOWER_WARNING_TEMP, DataType.INT8, str(lower)],
            [ParamNum.UPPER_WARNING_TEMP, DataType.INT8, str(upper)],
        ])
        return bool(result)

    def set_away_temperature(self, floor_temp: float, air_temp: float | None = None) -> bool:
        """Set away mode temperatures."""
        params = [
            [ParamNum.AWAY_FLOOR, 
             DataType.INT8 if not self._is_new_version else DataType.INT16, 
             self._temperature_to_api(floor_temp, ParamNum.AWAY_FLOOR)]
        ]
        
        if self._is_new_version and air_temp is not None:
            params.append([
                ParamNum.AWAY_AIR, 
                DataType.INT16, 
                self._temperature_to_api(air_temp, ParamNum.AWAY_AIR)
            ])
        
        result = self.set_parameters(params)
        return bool(result)

    def set_power(self, watts: int) -> bool:
        """Set connected power in Watts."""
        # Convert watts to API value
        if watts <= 1500:
            api_value = watts // 10
        else:
            api_value = (watts + 1500) // 20
        
        result = self.set_parameters([
            [ParamNum.POWER, DataType.UINT16, str(api_value)]
        ])
        return bool(result)

    def update(self) -> bool:
        """Update all state from device."""
        # Get parameters
        params_result = self.get_parameters()
        if not params_result:
            return False
        
        # Get status
        status_result = self.get_status()
        if not status_result:
            return False
        
        # Parse status
        self._parse_status(status_result)
        
        # Update power state from parameters
        self._power_on = not self._get_param_value(ParamNum.POWER_OFF)
        
        return True

    def _parse_status(self, data: dict) -> None:
        """Parse status response."""
        # Floor temperature (t.1 = raw * 16)
        if "t.1" in data:
            self._floor_temperature = float(data["t.1"]) / 16.0
        
        # Air temperature (t.2 for new version)
        if self._is_new_version and "t.2" in data:
            self._air_temperature = float(data["t.2"]) / 16.0
        
        # Setpoint (t.5 = raw * 16)
        if "t.5" in data:
            self._setpoint = float(data["t.5"]) / 16.0
        
        # Mode
        if "m.1" in data:
            mode_value = int(data["m.1"])
            # Check power state
            if "f.16" in data:
                is_on = int(data["f.16"]) == 0
            else:
                is_on = not self._get_param_value(ParamNum.POWER_OFF)
            
            if not is_on:
                self._mode = -1  # Off
            else:
                self._mode = mode_value
        
        # Relay state
        if "f.0" in data:
            self._relay_state = int(data["f.0"]) == 1


# Backward compatibility alias
Thermostat = TerneoThermostat
