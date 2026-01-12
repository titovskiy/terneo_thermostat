"""Button platform for Terneo/Welrok thermostat."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .thermostat import TerneoThermostat

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Terneo button entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    thermostat = data["thermostat"]

    async_add_entities([TerneoRestartButton(coordinator, thermostat, entry)])


class TerneoRestartButton(CoordinatorEntity, ButtonEntity):
    """Terneo restart button entity."""

    _attr_has_entity_name = True
    _attr_name = "Restart"
    _attr_icon = "mdi:restart"
    _attr_device_class = ButtonDeviceClass.RESTART

    def __init__(
        self,
        coordinator,
        thermostat: TerneoThermostat,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._thermostat = thermostat
        self._entry = entry
        
        self._attr_unique_id = f"{thermostat.sn}_restart"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, thermostat.sn)},
            "name": entry.title,
            "manufacturer": MANUFACTURER,
            "model": "OZ" if thermostat.is_new_version else "OZ (Legacy)",
            "serial_number": thermostat.sn,
        }

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._thermostat.available

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.hass.async_add_executor_job(self._thermostat.restart)
