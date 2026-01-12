"""Sensor platform for Terneo/Welrok thermostat."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, SENSOR_TYPES
from .thermostat import TerneoThermostat

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TerneoSensorEntityDescription(SensorEntityDescription):
    """Describes Terneo sensor entity."""
    
    value_fn: Callable[[TerneoThermostat], float | int | str | None]
    available_fn: Callable[[TerneoThermostat], bool] = lambda t: True
    new_version_only: bool = False


def get_sensor_type_name(thermostat: TerneoThermostat) -> str | None:
    """Get sensor type name."""
    sensor_type = thermostat.sensor_type
    if sensor_type is not None:
        return SENSOR_TYPES.get(sensor_type, f"Unknown ({sensor_type})")
    return None


SENSOR_DESCRIPTIONS: tuple[TerneoSensorEntityDescription, ...] = (
    TerneoSensorEntityDescription(
        key="floor_temperature",
        translation_key="floor_temperature",
        name="Floor Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda t: t.floor_temperature,
    ),
    TerneoSensorEntityDescription(
        key="air_temperature",
        translation_key="air_temperature",
        name="Air Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda t: t.air_temperature,
        new_version_only=True,
    ),
    TerneoSensorEntityDescription(
        key="setpoint",
        translation_key="setpoint",
        name="Target Temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda t: t.setpoint,
    ),
    TerneoSensorEntityDescription(
        key="relay_on_time_limit",
        translation_key="relay_on_time_limit",
        name="Continuous Heating Limit",
        icon="mdi:timer-alert",
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda t: t.relay_on_time_limit,
        entity_registry_enabled_default=False,
    ),
    TerneoSensorEntityDescription(
        key="sensor_type",
        translation_key="sensor_type_display",
        name="Sensor Type",
        icon="mdi:thermometer",
        value_fn=get_sensor_type_name,
        entity_registry_enabled_default=False,
    ),
    TerneoSensorEntityDescription(
        key="ble_sensor_connected",
        translation_key="ble_sensor_connected",
        name="Wireless Sensor",
        icon="mdi:bluetooth-connect",
        value_fn=lambda t: "Connected" if t.ble_sensor_bind else "Not connected",
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
    TerneoSensorEntityDescription(
        key="manual_floor_temp",
        translation_key="manual_floor_temp",
        name="Manual Floor Setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda t: t.manual_floor_temperature,
        entity_registry_enabled_default=False,
    ),
    TerneoSensorEntityDescription(
        key="manual_air_temp",
        translation_key="manual_air_temp",
        name="Manual Air Setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda t: t.manual_air_temperature,
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Terneo sensor entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    thermostat = data["thermostat"]

    entities = []
    for description in SENSOR_DESCRIPTIONS:
        # Skip new version only sensors for old devices
        if description.new_version_only and not thermostat.is_new_version:
            continue
        
        entities.append(TerneoSensorEntity(coordinator, thermostat, entry, description))

    async_add_entities(entities)


class TerneoSensorEntity(CoordinatorEntity, SensorEntity):
    """Terneo sensor entity."""

    _attr_has_entity_name = True
    entity_description: TerneoSensorEntityDescription

    def __init__(
        self,
        coordinator,
        thermostat: TerneoThermostat,
        entry: ConfigEntry,
        description: TerneoSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
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

    @property
    def native_value(self) -> float | int | str | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self._thermostat)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self._thermostat.available:
            return False
        return self.entity_description.available_fn(self._thermostat)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
