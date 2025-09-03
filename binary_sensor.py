# In /custom_components/ilmaprognoos/binary_sensor.py

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([IlmaprognoosStatusSensor(coordinator)])


class IlmaprognoosStatusSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of an update status binary sensor."""

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

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
    def is_on(self):
        """Return true if the coordinator has an error."""
        return not self.coordinator.last_update_success

    @property
    def extra_state_attributes(self):
        """Return other attributes."""
        # --- THIS IS THE FIX ---
        # The attribute is on the coordinator itself.
        # It may be None on the very first run, so we add a fallback.
        return {
            "last_successful_update": getattr(self.coordinator, "last_update_success_timestamp", None)
        }