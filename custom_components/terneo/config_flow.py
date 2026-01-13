"""Config flow for Terneo/Welrok thermostat integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import requests

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_SERIAL,
    CONF_DEVICE_TYPE,
    DEVICE_TYPE_OLD,
    DEVICE_TYPE_NEW,
    DEFAULT_NAME,
    DEFAULT_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def validate_connection(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    host = data[CONF_HOST]
    serial = data[CONF_SERIAL]
    
    base_url = f"http://{host}"
    
    # Try to connect and get device info
    try:
        response = await hass.async_add_executor_job(
            lambda: requests.get(f"{base_url}/api.html", timeout=5)
        )
        if response.status_code != 200:
            raise CannotConnect("Cannot connect to device")
    except requests.RequestException as err:
        _LOGGER.error("Connection error: %s", err)
        raise CannotConnect("Cannot connect to device") from err
    
    # Try to get device parameters and detect version
    try:
        response = await hass.async_add_executor_job(
            lambda: requests.post(
                f"{base_url}/api.cgi",
                json={"cmd": 1, "sn": serial},
                timeout=5
            )
        )
        result = response.json()
        
        if "sn" not in result:
            raise CannotConnect("Invalid device response - check serial number")
        
        # Verify serial matches
        if result["sn"] != serial:
            raise CannotConnect("Serial number mismatch")
        
        # Detect device type by checking parameters
        # New version has parameters like 4 (manualAir), 6 (awayAir), etc.
        params = {p[0]: p for p in result.get("par", [])}
        
        # Check for new version specific parameters
        has_air_sensor = 4 in params or 6 in params or 33 in params
        
        device_type = DEVICE_TYPE_NEW if has_air_sensor else DEVICE_TYPE_OLD
        
        return {
            "serial": serial,
            "device_type": device_type,
            "title": f"terneo_{serial}",
        }
        
    except requests.RequestException as err:
        _LOGGER.error("Error getting device info: %s", err)
        raise CannotConnect("Cannot get device info") from err
    except (KeyError, ValueError) as err:
        _LOGGER.error("Invalid response from device: %s", err)
        raise CannotConnect("Invalid device response") from err


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class TerneoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Terneo thermostat."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_info: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_connection(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Check if already configured
                await self.async_set_unique_id(info["serial"])
                self._abort_if_unique_id_configured()

                # Store data for next step
                self._discovered_info = {
                    **user_input,
                    CONF_SERIAL: info["serial"],
                    CONF_DEVICE_TYPE: info["device_type"],
                    "title": info["title"],
                }
                
                return await self.async_step_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_SERIAL): str,
                }
            ),
            errors=errors,
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the options step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Combine with discovered info
            data = {
                **self._discovered_info,
                CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
            }
            
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, self._discovered_info.get("title", DEFAULT_NAME)),
                data=data,
            )

        device_type_label = (
            "Новая версия (с датчиком воздуха)" 
            if self._discovered_info.get(CONF_DEVICE_TYPE) == DEVICE_TYPE_NEW 
            else "Старая версия (без датчика воздуха)"
        )

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NAME, 
                        default=self._discovered_info.get("title", DEFAULT_NAME)
                    ): str,
                }
            ),
            description_placeholders={
                "serial": self._discovered_info.get(CONF_SERIAL, "Unknown"),
                "device_type": device_type_label,
            },
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return TerneoOptionsFlowHandler()


class TerneoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Terneo thermostat."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "scan_interval",
                        default=self.config_entry.options.get("scan_interval", 30),
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                    vol.Optional(
                        "timeout",
                        default=self.config_entry.options.get("timeout", DEFAULT_TIMEOUT),
                    ): vol.All(vol.Coerce(int), vol.Range(min=3, max=120)),
                    vol.Optional(
                        "show_advanced_sensors",
                        default=self.config_entry.options.get("show_advanced_sensors", False),
                    ): bool,
                }
            ),
        )
