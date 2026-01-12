"""Number platform for Terneo/Welrok thermostat."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .thermostat import TerneoThermostat

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TerneoNumberEntityDescription(NumberEntityDescription):
    """Describes Terneo number entity."""
    
    value_fn: Callable[[TerneoThermostat], float | None]
    set_fn: Callable[[TerneoThermostat, float], bool]
    new_version_only: bool = False


NUMBER_DESCRIPTIONS: tuple[TerneoNumberEntityDescription, ...] = (
    TerneoNumberEntityDescription(
        key="brightness",
        translation_key="brightness",
        name="Display Brightness",
        icon="mdi:brightness-6",
        native_min_value=0,
        native_max_value=9,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda t: t.brightness,
        set_fn=lambda t, v: t.set_brightness(int(v)),
    ),
    TerneoNumberEntityDescription(
        key="hysteresis",
        translation_key="hysteresis",
        name="Hysteresis",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0.5,
        native_max_value=10.0,
        native_step=0.1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.hysteresis,
        set_fn=lambda t, v: t.set_hysteresis(v),
    ),
    TerneoNumberEntityDescription(
        key="floor_correction",
        translation_key="floor_correction",
        name="Floor Sensor Correction",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-12.7,
        native_max_value=12.7,
        native_step=0.1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.floor_correction,
        set_fn=lambda t, v: t.set_floor_correction(v),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="air_correction",
        translation_key="air_correction",
        name="Air Sensor Correction",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-12.7,
        native_max_value=12.7,
        native_step=0.1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.air_correction,
        set_fn=lambda t, v: t.set_air_correction(v),
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="prop_koef",
        translation_key="prop_koef",
        name="Proportional Coefficient",
        icon="mdi:percent",
        native_min_value=0,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda t: t.prop_koef,
        set_fn=lambda t, v: t.set_prop_koef(int(v)),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="upper_floor_limit",
        translation_key="upper_floor_limit",
        name="Max Floor Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=45,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.upper_limit,
        set_fn=lambda t, v: t.set_floor_limits(t.lower_limit or 5, int(v)),
    ),
    TerneoNumberEntityDescription(
        key="lower_floor_limit",
        translation_key="lower_floor_limit",
        name="Min Floor Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=40,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.lower_limit,
        set_fn=lambda t, v: t.set_floor_limits(int(v), t.upper_limit or 45),
    ),
    TerneoNumberEntityDescription(
        key="upper_air_limit",
        translation_key="upper_air_limit",
        name="Max Air Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=35,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.upper_air_limit,
        set_fn=lambda t, v: t.set_air_limits(t.lower_air_limit or 5, int(v)),
        new_version_only=True,
    ),
    TerneoNumberEntityDescription(
        key="lower_air_limit",
        translation_key="lower_air_limit",
        name="Min Air Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.lower_air_limit,
        set_fn=lambda t, v: t.set_air_limits(int(v), t.upper_air_limit or 35),
        new_version_only=True,
    ),
    TerneoNumberEntityDescription(
        key="min_temp_advanced",
        translation_key="min_temp_advanced",
        name="Min Floor Limit (Air Mode)",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=40,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.min_temp_advanced,
        set_fn=lambda t, v: t.set_advanced_floor_limits(int(v), t.max_temp_advanced or 45),
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="max_temp_advanced",
        translation_key="max_temp_advanced",
        name="Max Floor Limit (Air Mode)",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=45,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.max_temp_advanced,
        set_fn=lambda t, v: t.set_advanced_floor_limits(t.min_temp_advanced or 0, int(v)),
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="ble_sensor_interval",
        translation_key="ble_sensor_interval",
        name="Wireless Sensor Interval",
        icon="mdi:bluetooth",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=1,
        native_max_value=60,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.ble_sensor_interval,
        set_fn=lambda t, v: t.set_ble_sensor_interval(int(v)),
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="upper_warning_temp",
        translation_key="upper_warning_temp",
        name="Upper Warning Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=45,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.upper_warning_temp,
        set_fn=lambda t, v: t.set_warning_temps(t.lower_warning_temp or 5, int(v)),
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="lower_warning_temp",
        translation_key="lower_warning_temp",
        name="Lower Warning Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=40,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.lower_warning_temp,
        set_fn=lambda t, v: t.set_warning_temps(int(v), t.upper_warning_temp or 35),
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="power",
        translation_key="power",
        name="Connected Power",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=7500,
        native_step=10,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.power_watts,
        set_fn=lambda t, v: t.set_power(int(v)),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="night_bright_start",
        translation_key="night_bright_start",
        name="Night Mode Start",
        icon="mdi:weather-night",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=0,
        native_max_value=1439,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.night_bright_start,
        set_fn=lambda t, v: t.set_night_brightness_time(int(v), t.night_bright_end or 480),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="night_bright_end",
        translation_key="night_bright_end",
        name="Night Mode End",
        icon="mdi:weather-sunny",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=0,
        native_max_value=1439,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.night_bright_end,
        set_fn=lambda t, v: t.set_night_brightness_time(t.night_bright_start or 0, int(v)),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="button_minus_cor",
        translation_key="button_minus_cor",
        name="Minus Button Sensitivity",
        icon="mdi:gesture-tap-button",
        native_min_value=-30,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda t: t.button_minus_cor,
        set_fn=lambda t, v: t.set_button_corrections(int(v), t.button_menu_cor or 0, t.button_plus_cor or 0),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="button_menu_cor",
        translation_key="button_menu_cor",
        name="Menu Button Sensitivity",
        icon="mdi:gesture-tap-button",
        native_min_value=-30,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda t: t.button_menu_cor,
        set_fn=lambda t, v: t.set_button_corrections(t.button_minus_cor or 0, int(v), t.button_plus_cor or 0),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="button_plus_cor",
        translation_key="button_plus_cor",
        name="Plus Button Sensitivity",
        icon="mdi:gesture-tap-button",
        native_min_value=-30,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.SLIDER,
        value_fn=lambda t: t.button_plus_cor,
        set_fn=lambda t, v: t.set_button_corrections(t.button_minus_cor or 0, t.button_menu_cor or 0, int(v)),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="away_floor_temperature",
        translation_key="away_floor_temperature",
        name="Away Floor Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=45,
        native_step=1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.away_floor_temperature,
        set_fn=lambda t, v: t.set_away_temperature(v),
        entity_registry_enabled_default=False,
    ),
    TerneoNumberEntityDescription(
        key="away_air_temperature",
        translation_key="away_air_temperature",
        name="Away Air Temperature",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=35,
        native_step=0.1,
        mode=NumberMode.BOX,
        value_fn=lambda t: t.away_air_temperature,
        set_fn=lambda t, v: t.set_away_temperature(t.away_floor_temperature or 5, v),
        new_version_only=True,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Terneo number entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    thermostat = data["thermostat"]

    entities = []
    for description in NUMBER_DESCRIPTIONS:
        # Skip new version only numbers for old devices
        if description.new_version_only and not thermostat.is_new_version:
            continue
        
        entities.append(TerneoNumberEntity(coordinator, thermostat, entry, description))

    async_add_entities(entities)


class TerneoNumberEntity(CoordinatorEntity, NumberEntity):
    """Terneo number entity."""

    _attr_has_entity_name = True
    entity_description: TerneoNumberEntityDescription

    def __init__(
        self,
        coordinator,
        thermostat: TerneoThermostat,
        entry: ConfigEntry,
        description: TerneoNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
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
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.entity_description.value_fn(self._thermostat)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._thermostat.available

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.hass.async_add_executor_job(
            self.entity_description.set_fn, self._thermostat, value
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
