# In /custom_components/ilmaprognoos/sensor.py

from homeassistant.components.sensor import (
    SensorEntity, SensorDeviceClass, SensorStateClass
)
from homeassistant.const import UnitOfTemperature, PERCENTAGE, UnitOfLength, UnitOfTime
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors_to_add = [
        IlmaprognoosWarningsSensor(coordinator),
        IlmaprognoosPrecipitationSensor(coordinator),
        IlmaprognoosTemperatureSensor(coordinator),
    ]

    if not coordinator.is_forecast_only:
        sensors_to_add.append(IlmaprognoosHumiditySensor(coordinator))
        initial_data = coordinator.data.get("current", {})
        if "veetase" in initial_data:
            sensors_to_add.append(IlmaprognoosWaterLevelSensor(coordinator))
        if "veetemp" in initial_data:
            sensors_to_add.append(IlmaprognoosWaterTempSensor(coordinator))

    if coordinator.data.get("sunshine"):
        sensors_to_add.extend([
            # --- THIS IS THE NEW SENSOR ---
            SunshineTodaySensor(coordinator),
            SunshineTomorrowSensor(coordinator),
            SunshineDay2Sensor(coordinator),
            SunshineDay3Sensor(coordinator),
        ])

    async_add_entities(sensors_to_add)


class IlmaprognoosBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_device_info = { "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)} }
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()
    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("current") is not None

class IlmaprognoosWarningsSensor(IlmaprognoosBaseSensor):
    _attr_icon = "mdi:alert-outline"; _attr_name = "Hoiatused"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_warnings"
    @property
    def state(self):
        warnings = self.coordinator.data.get("warnings", []);
        if not warnings: return "Hoiatusi pole"
        return "\n".join([w.get("description") for w in warnings])
    @property
    def extra_state_attributes(self):
        warnings = self.coordinator.data.get("warnings", []); return {"warnings_count": len(warnings), "raw_warnings": warnings}
class IlmaprognoosPrecipitationSensor(IlmaprognoosBaseSensor):
    _attr_name = "Sademed"; _attr_native_unit_of_measurement = "mm/h"; _attr_icon = "mdi:weather-pouring"; _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_precipitation"
    @property
    def native_value(self):
        precip_str = self.coordinator.data.get("current", {}).get("sademed", "0 mm/h");
        try: return float(precip_str.split(" ")[0])
        except (ValueError, IndexError): return 0
class IlmaprognoosTemperatureSensor(IlmaprognoosBaseSensor):
    _attr_name = "Temperatuur"; _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS; _attr_device_class = SensorDeviceClass.TEMPERATURE; _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_temperature"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("temperature")
class IlmaprognoosHumiditySensor(IlmaprognoosBaseSensor):
    _attr_name = "Õhuniiskus"; _attr_native_unit_of_measurement = PERCENTAGE; _attr_device_class = SensorDeviceClass.HUMIDITY; _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_humidity"
    @property
    def native_value(self):
        humidity_str = self.coordinator.data.get("current", {}).get("ohuniiskus", "0%");
        try: return float(humidity_str.replace("%", ""))
        except ValueError: return None
class IlmaprognoosWaterLevelSensor(IlmaprognoosBaseSensor):
    _attr_name = "Veetase"; _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS; _attr_icon = "mdi:waves-arrow-up"; _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_water_level"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("veetase")
class IlmaprognoosWaterTempSensor(IlmaprognoosBaseSensor):
    _attr_name = "Veetemperatuur"; _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS; _attr_device_class = SensorDeviceClass.TEMPERATURE; _attr_state_class = SensorStateClass.MEASUREMENT; _attr_icon = "mdi:thermometer-water"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_water_temp"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("veetemp")

class IlmaprognoosSunshineSensor(IlmaprognoosBaseSensor):
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_icon = "mdi:weather-sunny"
    _attr_state_class = SensorStateClass.MEASUREMENT
    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("sunshine") is not None

# --- NEW SENSOR CLASS ---
class SunshineTodaySensor(IlmaprognoosSunshineSensor):
    _attr_name = "Päikesepaiste täna"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshine_today"
    @property
    def native_value(self):
        return self.coordinator.data.get("sunshine", {}).get("today")

class SunshineTomorrowSensor(IlmaprognoosSunshineSensor):
    _attr_name = "Päikesepaiste homme"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshine_tomorrow"
    @property
    def native_value(self):
        return self.coordinator.data.get("sunshine", {}).get("tomorrow")

class SunshineDay2Sensor(IlmaprognoosSunshineSensor):
    _attr_name = "Päikesepaiste (päev 2)"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshine_day_2"
    @property
    def native_value(self):
        return self.coordinator.data.get("sunshine", {}).get("day_2")

class SunshineDay3Sensor(IlmaprognoosSunshineSensor):
    _attr_name = "Päikesepaiste (päev 3)"
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshine_day_3"
    @property
    def native_value(self):
        return self.coordinator.data.get("sunshine", {}).get("day_3")