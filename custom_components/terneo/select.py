"""Select platform for Terneo/Welrok thermostat."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, ControlType, SENSOR_TYPES
from .thermostat import TerneoThermostat

_LOGGER = logging.getLogger(__name__)


# Control type mappings
CONTROL_TYPE_OPTIONS = {
    "floor": ControlType.FLOOR,
    "air": ControlType.AIR,
    "air_with_floor_limit": ControlType.AIR_WITH_FLOOR_LIMIT,
}

CONTROL_TYPE_NAMES = {
    ControlType.FLOOR: "floor",
    ControlType.AIR: "air",
    ControlType.AIR_WITH_FLOOR_LIMIT: "air_with_floor_limit",
}

# Sensor type mappings
SENSOR_TYPE_OPTIONS = {
    "4.7k": 0,
    "6.8k": 1,
    "10k": 2,
    "12k": 3,
    "15k": 4,
    "33k": 5,
    "47k": 6,
}

SENSOR_TYPE_NAMES = {
    0: "4.7k",
    1: "6.8k",
    2: "10k",
    3: "12k",
    4: "15k",
    5: "33k",
    6: "47k",
}


@dataclass(frozen=True, kw_only=True)
class TerneoSelectEntityDescription(SelectEntityDescription):
    """Describes Terneo select entity."""
    
    value_fn: Callable[[TerneoThermostat], str | None]
    set_fn: Callable[[TerneoThermostat, str], bool]
    options_fn: Callable[[TerneoThermostat], list[str]]
    new_version_only: bool = False


def get_control_type_value(thermostat: TerneoThermostat) -> str | None:
    """Get current control type as string."""
    control_type = thermostat.control_type
    if control_type is not None:
        return CONTROL_TYPE_NAMES.get(control_type, "floor")
    return None


def set_control_type_value(thermostat: TerneoThermostat, value: str) -> bool:
    """Set control type from string."""
    control_type = CONTROL_TYPE_OPTIONS.get(value, ControlType.FLOOR)
    return thermostat.set_control_type(control_type)


def get_control_type_options(thermostat: TerneoThermostat) -> list[str]:
    """Get available control type options."""
    if thermostat.is_new_version:
        return ["floor", "air", "air_with_floor_limit"]
    return ["floor"]


def get_sensor_type_value(thermostat: TerneoThermostat) -> str | None:
    """Get current sensor type as string."""
    sensor_type = thermostat.sensor_type
    if sensor_type is not None:
        return SENSOR_TYPE_NAMES.get(sensor_type, "10k")
    return None


def set_sensor_type_value(thermostat: TerneoThermostat, value: str) -> bool:
    """Set sensor type from string."""
    sensor_type = SENSOR_TYPE_OPTIONS.get(value, 2)  # Default to 10k
    return thermostat.set_sensor_type(sensor_type)


def get_sensor_type_options(thermostat: TerneoThermostat) -> list[str]:
    """Get available sensor type options."""
    return ["4.7k", "6.8k", "10k", "12k", "15k", "33k", "47k"]


SELECT_DESCRIPTIONS: tuple[TerneoSelectEntityDescription, ...] = (
    TerneoSelectEntityDescription(
        key="control_type",
        translation_key="control_type",
        name="Control Type",
        icon="mdi:thermostat",
        options=[],  # Will be set dynamically
        value_fn=get_control_type_value,
        set_fn=set_control_type_value,
        options_fn=get_control_type_options,
    ),
    TerneoSelectEntityDescription(
        key="sensor_type",
        translation_key="sensor_type",
        name="Sensor Type",
        icon="mdi:thermometer",
        options=[],  # Will be set dynamically
        value_fn=get_sensor_type_value,
        set_fn=set_sensor_type_value,
        options_fn=get_sensor_type_options,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Terneo select entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    thermostat = data["thermostat"]

    entities = []
    for description in SELECT_DESCRIPTIONS:
        # Skip new version only selects for old devices
        if description.new_version_only and not thermostat.is_new_version:
            continue
        
        entities.append(TerneoSelectEntity(coordinator, thermostat, entry, description))

    async_add_entities(entities)


class TerneoSelectEntity(CoordinatorEntity, SelectEntity):
    """Terneo select entity."""

    _attr_has_entity_name = True
    entity_description: TerneoSelectEntityDescription

    def __init__(
        self,
        coordinator,
        thermostat: TerneoThermostat,
        entry: ConfigEntry,
        description: TerneoSelectEntityDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._thermostat = thermostat
        self._entry = entry
        self.entity_description = description
        
        self._attr_unique_id = f"{thermostat.sn}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, thermostat.sn)},
            "name": entry.title,
            "manufacturer": MANUFACTURER,
            "model": "OZ" if thermostat.is_new_version else "OZ (Legacy)",
            "serial_number": thermostat.sn,
        }
        
        # Set options dynamically
        self._attr_options = description.options_fn(thermostat)

    @property
    def current_option(self) -> str | None:
        """Return the current option."""
        return self.entity_description.value_fn(self._thermostat)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._thermostat.available

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.hass.async_add_executor_job(
            self.entity_description.set_fn, self._thermostat, option
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
