# In /custom_components/ilmaprognoos/binary_sensor.py

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import EntityCategory

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([IlmaprognoosStatusSensor(coordinator)])


class IlmaprognoosStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an update status binary sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Uuendamise staatus"

    @property
    def available(self) -> bool:
        """Always return True so the user can see the error state."""
        return True

    @property
    def is_on(self):
        """Return true if the coordinator has an error."""
        if not self.coordinator.last_update_success:
            return True
        return getattr(self.coordinator, "api_fetch_error", False)

    @property
    def extra_state_attributes(self):
        """Return extra state attributes, including the exact error message."""
        attrs = {
            "last_successful_update": getattr(self.coordinator, "last_update_success_timestamp", None)
        }
        
        # --- NEW: Show exact error message if an error occurred ---
        if error_reason := getattr(self.coordinator, "last_error_reason", None):
            attrs["veateade"] = error_reason
            
        return attrs
