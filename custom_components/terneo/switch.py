"""Switch platform for Terneo/Welrok thermostat."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .thermostat import TerneoThermostat

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TerneoSwitchEntityDescription(SwitchEntityDescription):
    """Describes Terneo switch entity."""
    
    value_fn: Callable[[TerneoThermostat], bool | None]
    turn_on_fn: Callable[[TerneoThermostat], bool]
    turn_off_fn: Callable[[TerneoThermostat], bool]
    new_version_only: bool = False


SWITCH_DESCRIPTIONS: tuple[TerneoSwitchEntityDescription, ...] = (
    TerneoSwitchEntityDescription(
        key="power",
        translation_key="power",
        name="Power",
        device_class=SwitchDeviceClass.SWITCH,
        value_fn=lambda t: t.power_on,
        turn_on_fn=lambda t: t.turn_on(),
        turn_off_fn=lambda t: t.turn_off(),
    ),
    TerneoSwitchEntityDescription(
        key="children_lock",
        translation_key="children_lock",
        name="Children Lock",
        icon="mdi:lock-outline",
        value_fn=lambda t: t.children_lock,
        turn_on_fn=lambda t: t.set_children_lock(True),
        turn_off_fn=lambda t: t.set_children_lock(False),
    ),
    TerneoSwitchEntityDescription(
        key="cooling_mode",
        translation_key="cooling_mode",
        name="Cooling Mode",
        icon="mdi:snowflake",
        value_fn=lambda t: t.cooling_mode,
        turn_on_fn=lambda t: t.set_cooling_mode(True),
        turn_off_fn=lambda t: t.set_cooling_mode(False),
    ),
    TerneoSwitchEntityDescription(
        key="pre_control",
        translation_key="pre_control",
        name="Pre-heating",
        icon="mdi:radiator",
        value_fn=lambda t: t.pre_control,
        turn_on_fn=lambda t: t.set_pre_control(True),
        turn_off_fn=lambda t: t.set_pre_control(False),
    ),
    TerneoSwitchEntityDescription(
        key="use_night_brightness",
        translation_key="use_night_brightness",
        name="Night Brightness",
        icon="mdi:brightness-4",
        value_fn=lambda t: t.use_night_brightness,
        turn_on_fn=lambda t: t.set_use_night_brightness(True),
        turn_off_fn=lambda t: t.set_use_night_brightness(False),
    ),
    TerneoSwitchEntityDescription(
        key="window_open_control",
        translation_key="window_open_control",
        name="Window Open Detection",
        icon="mdi:window-open-variant",
        value_fn=lambda t: t.window_open_control,
        turn_on_fn=lambda t: t.set_window_open_control(True),
        turn_off_fn=lambda t: t.set_window_open_control(False),
        new_version_only=True,
    ),
    TerneoSwitchEntityDescription(
        key="nc_contact_control",
        translation_key="nc_contact_control",
        name="Inverted Relay (NC)",
        icon="mdi:electric-switch",
        value_fn=lambda t: t.nc_contact_control,
        turn_on_fn=lambda t: t.set_nc_contact_control(True),
        turn_off_fn=lambda t: t.set_nc_contact_control(False),
        entity_registry_enabled_default=False,
    ),
    TerneoSwitchEntityDescription(
        key="lan_block",
        translation_key="lan_block",
        name="LAN API Block",
        icon="mdi:lan-disconnect",
        value_fn=lambda t: t.lan_block,
        turn_on_fn=lambda t: t.set_lan_block(True),
        turn_off_fn=lambda t: t.set_lan_block(False),
        entity_registry_enabled_default=False,
    ),
    TerneoSwitchEntityDescription(
        key="cloud_block",
        translation_key="cloud_block",
        name="Cloud Block",
        icon="mdi:cloud-off-outline",
        value_fn=lambda t: t.cloud_block,
        turn_on_fn=lambda t: t.set_cloud_block(True),
        turn_off_fn=lambda t: t.set_cloud_block(False),
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Terneo switch entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    thermostat = data["thermostat"]

    entities = []
    for description in SWITCH_DESCRIPTIONS:
        # Skip new version only switches for old devices
        if description.new_version_only and not thermostat.is_new_version:
            continue
        
        entities.append(TerneoSwitchEntity(coordinator, thermostat, entry, description))

    async_add_entities(entities)


class TerneoSwitchEntity(CoordinatorEntity, SwitchEntity):
    """Terneo switch entity."""

    _attr_has_entity_name = True
    entity_description: TerneoSwitchEntityDescription

    def __init__(
        self,
        coordinator,
        thermostat: TerneoThermostat,
        entry: ConfigEntry,
        description: TerneoSwitchEntityDescription,
    ) -> None:
        """Initialize the switch entity."""
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
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        return self.entity_description.value_fn(self._thermostat)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._thermostat.available

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self.hass.async_add_executor_job(
            self.entity_description.turn_on_fn, self._thermostat
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self.hass.async_add_executor_job(
            self.entity_description.turn_off_fn, self._thermostat
        )
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
