# In /custom_components/ilmateenistus/sensor.py

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [
        IlmaprognoosWarningsSensor(coordinator),
        IlmaprognoosPrecipitationSensor(coordinator),
    ]
    async_add_entities(sensors)


class IlmaprognoosWarningsSensor(CoordinatorEntity, SensorEntity):
    """Representation of a warnings sensor."""
    _attr_has_entity_name = True
    _attr_icon = "mdi:alert-outline"

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_warnings"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
        }
    
    @property
    def name(self):
        """Return the name of the sensor."""
        return "Hoiatused" # Warnings

    @property
    def state(self):
        """Return the state of the sensor."""
        warnings = self.coordinator.data.get("warnings", [])
        if not warnings:
            return "Hoiatusi pole" # No warnings
        
        descriptions = [w.get("description") for w in warnings]
        return "\n".join(descriptions)

    @property
    def extra_state_attributes(self):
        """Return other attributes."""
        warnings = self.coordinator.data.get("warnings", [])
        return {
            "warnings_count": len(warnings),
            "raw_warnings": warnings
        }


class IlmaprognoosPrecipitationSensor(CoordinatorEntity, SensorEntity):
    """Representation of a precipitation sensor."""
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "mm/h"
    _attr_icon = "mdi:weather-pouring"
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_precipitation"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
        }

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Sademed" # Precipitation

    @property
    def native_value(self):
        """Return the state of the sensor."""
        precip_str = self.coordinator.data.get("current", {}).get("sademed", "0 mm/h")
        try:
            return float(precip_str.split(" ")[0])
        except (ValueError, IndexError):
            return 0