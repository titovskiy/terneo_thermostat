"""The Terneo/Welrok thermostat integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_SERIAL,
    CONF_DEVICE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_TYPE_OLD,
)
from .thermostat import TerneoThermostat

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_SET_FLOOR_LIMITS = "set_floor_limits"
SERVICE_SET_AIR_LIMITS = "set_air_limits"
SERVICE_RESTART = "restart"

SERVICE_FLOOR_LIMITS_SCHEMA = vol.Schema(
    {
        vol.Required("lower"): vol.All(vol.Coerce(int), vol.Range(min=5, max=40)),
        vol.Required("upper"): vol.All(vol.Coerce(int), vol.Range(min=10, max=45)),
    }
)

SERVICE_AIR_LIMITS_SCHEMA = vol.Schema(
    {
        vol.Required("lower"): vol.All(vol.Coerce(int), vol.Range(min=5, max=30)),
        vol.Required("upper"): vol.All(vol.Coerce(int), vol.Range(min=10, max=35)),
    }
)

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Terneo thermostat from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create thermostat instance
    try:
        thermostat = await hass.async_add_executor_job(
            lambda: TerneoThermostat(
                serial_number=entry.data[CONF_SERIAL],
                host=entry.data[CONF_HOST],
                device_type=entry.data.get(CONF_DEVICE_TYPE, DEVICE_TYPE_OLD),
            )
        )
    except Exception as err:
        _LOGGER.error("Failed to connect to Terneo thermostat: %s", err)
        return False

    # Get scan interval from options
    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)

    # Create update coordinator
    async def async_update_data():
        """Fetch data from API."""
        try:
            success = await hass.async_add_executor_job(thermostat.update)
            if not success:
                raise UpdateFailed("Failed to update thermostat data")
            return thermostat
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"Terneo {entry.data[CONF_SERIAL]}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=scan_interval),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and thermostat
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "thermostat": thermostat,
    }

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_register_services(hass)

    # Register update listener for options
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    
    async def handle_set_floor_limits(call: ServiceCall) -> None:
        """Handle set_floor_limits service call."""
        lower = call.data["lower"]
        upper = call.data["upper"]
        
        for entry_id, data in hass.data[DOMAIN].items():
            thermostat = data["thermostat"]
            await hass.async_add_executor_job(
                thermostat.set_floor_limits, lower, upper
            )
            await data["coordinator"].async_request_refresh()

    async def handle_set_air_limits(call: ServiceCall) -> None:
        """Handle set_air_limits service call."""
        lower = call.data["lower"]
        upper = call.data["upper"]
        
        for entry_id, data in hass.data[DOMAIN].items():
            thermostat = data["thermostat"]
            if thermostat.is_new_version:
                await hass.async_add_executor_job(
                    thermostat.set_air_limits, lower, upper
                )
                await data["coordinator"].async_request_refresh()

    # Only register services if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_SET_FLOOR_LIMITS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_FLOOR_LIMITS,
            handle_set_floor_limits,
            schema=SERVICE_FLOOR_LIMITS_SCHEMA,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SET_AIR_LIMITS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SET_AIR_LIMITS,
            handle_set_air_limits,
            schema=SERVICE_AIR_LIMITS_SCHEMA,
        )

    async def handle_restart(call: ServiceCall) -> None:
        """Handle restart service call."""
        for entry_id, data in hass.data[DOMAIN].items():
            thermostat = data["thermostat"]
            await hass.async_add_executor_job(thermostat.restart)

    if not hass.services.has_service(DOMAIN, SERVICE_RESTART):
        hass.services.async_register(
            DOMAIN,
            SERVICE_RESTART,
            handle_restart,
        )


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
