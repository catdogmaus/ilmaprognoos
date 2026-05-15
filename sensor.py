# In /custom_components/ilmaprognoos/sensor.py

from homeassistant.components.sensor import (
    SensorEntity, SensorDeviceClass, SensorStateClass
)
from homeassistant.const import UnitOfTemperature, PERCENTAGE, UnitOfLength, UnitOfTime, UnitOfPrecipitationDepth
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
        
        if "wind_speed_max" in initial_data:
            sensors_to_add.append(IlmaprognoosWindGustSensor(coordinator))
        if "veetase" in initial_data:
            sensors_to_add.append(IlmaprognoosWaterLevelSensor(coordinator))
        if "veetase_eh2000" in initial_data:
            sensors_to_add.append(IlmaprognoosSeaLevelSensor(coordinator))
        if "veetemp" in initial_data:
            sensors_to_add.append(IlmaprognoosWaterTempSensor(coordinator))
        if "visibility" in initial_data:
            sensors_to_add.append(IlmaprognoosVisibilitySensor(coordinator))
        if "uvindex" in initial_data:
            sensors_to_add.append(IlmaprognoosUVIndexSensor(coordinator))
        if "sunshineduration" in initial_data:
            sensors_to_add.append(IlmaprognoosSunshineDurationSensor(coordinator))
        if "globalradiation" in initial_data:
            sensors_to_add.append(IlmaprognoosGlobalRadiationSensor(coordinator))

    if coordinator.data.get("sunshine"):
        sensors_to_add.extend([
            SunshineTodaySensor(coordinator),
            SunshineTomorrowSensor(coordinator),
            SunshineDay2Sensor(coordinator),
            SunshineDay3Sensor(coordinator),
        ])

    if coordinator.data.get("precipitation_forecast"):
        sensors_to_add.extend([
            PrecipitationTodaySensor(coordinator),
            PrecipitationTomorrowSensor(coordinator),
            PrecipitationDay2Sensor(coordinator),
            PrecipitationDay3Sensor(coordinator),
        ])

    async_add_entities(sensors_to_add)


class IlmaprognoosBaseSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_device_info = { "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)} }
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass(); self._handle_coordinator_update()
    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data is not None


class IlmaprognoosWarningsSensor(IlmaprognoosBaseSensor):
    _attr_icon = "mdi:alert-outline"; _attr_name = "Hoiatused"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_warnings"
    @property
    def state(self):
        warnings = self.coordinator.data.get("warnings",[])
        if not warnings: return "Hoiatusi pole"
        descriptions = [w.get("description") for w in warnings if w.get("description")]
        if not descriptions: return "Tundmatu hoiatus"
        full_text = "\n".join(descriptions)
        if len(full_text) <= 255: return full_text
        else:
            first_warning = descriptions[0]
            remaining_count = len(descriptions) - 1
            suffix = f"\n\n... ja veel {remaining_count} hoiatust." if remaining_count > 1 else "\n\n... ja veel 1 hoiatus."
            if len(first_warning) + len(suffix) > 255:
                truncate_at = 255 - len(suffix) - 3
                first_warning = first_warning[:truncate_at] + "..."
            return f"{first_warning}{suffix}"
    @property
    def extra_state_attributes(self):
        warnings = self.coordinator.data.get("warnings",[])
        descriptions = [w.get("description") for w in warnings if w.get("description")]
        return {"descriptions": "\n".join(descriptions), "warnings_count": len(descriptions), "raw_warnings": warnings}


class IlmaprognoosPrecipitationSensor(IlmaprognoosBaseSensor):
    _attr_name = "Sademed"; _attr_native_unit_of_measurement = "mm/h"; _attr_icon = "mdi:weather-pouring"; _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_precipitation"
    @property
    def native_value(self):
        val = self.coordinator.data.get("current", {}).get("sademed")
        if val is None: return 0.0
        if isinstance(val, (int, float)): return float(val)
        try: return float(str(val).split(" ")[0])
        except (ValueError, IndexError): return 0.0

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
        val = self.coordinator.data.get("current", {}).get("ohuniiskus")
        if val is None: return None
        if isinstance(val, (int, float)): return float(val)
        try: return float(str(val).replace("%", ""))
        except ValueError: return None


class IlmaprognoosWindGustSensor(IlmaprognoosBaseSensor):
    _attr_name = "Tuulepuhangud"
    _attr_native_unit_of_measurement = "m/s"
    _attr_icon = "mdi:weather-windy"
    _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_wind_gusts"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("wind_speed_max")

class IlmaprognoosVisibilitySensor(IlmaprognoosBaseSensor):
    _attr_name = "Nähtavus"
    _attr_native_unit_of_measurement = "km"
    _attr_icon = "mdi:eye"
    _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_visibility"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("visibility")

class IlmaprognoosWaterLevelSensor(IlmaprognoosBaseSensor):
    _attr_name = "Sisevete veetase"
    _attr_native_unit_of_measurement = "cm"
    _attr_icon = "mdi:waves-arrow-up"
    _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_water_level"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("veetase")

class IlmaprognoosSeaLevelSensor(IlmaprognoosBaseSensor):
    _attr_name = "Merevee tase"
    _attr_native_unit_of_measurement = "cm"
    _attr_icon = "mdi:waves-arrow-up"
    _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sea_level"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("veetase_eh2000")

class IlmaprognoosWaterTempSensor(IlmaprognoosBaseSensor):
    _attr_name = "Veetemperatuur"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer-water"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_water_temp"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("veetemp")

class IlmaprognoosUVIndexSensor(IlmaprognoosBaseSensor):
    _attr_name = "UV-indeks"
    _attr_icon = "mdi:weather-sunny-alert"
    _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_uvindex"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("uvindex")

class IlmaprognoosSunshineDurationSensor(IlmaprognoosBaseSensor):
    _attr_name = "Päikesepaiste kestus (mõõdetud)"
    # --- FIX: Changed to hours ---
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_icon = "mdi:timer-sand"
    _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshineduration"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("sunshineduration")

class IlmaprognoosGlobalRadiationSensor(IlmaprognoosBaseSensor):
    _attr_name = "Summaarne kiirgus"
    _attr_native_unit_of_measurement = "W/m²"
    _attr_icon = "mdi:white-balance-sunny"
    _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_globalradiation"
    @property
    def native_value(self): return self.coordinator.data.get("current", {}).get("globalradiation")


class IlmaprognoosSunshineSensor(IlmaprognoosBaseSensor):
    _attr_native_unit_of_measurement = UnitOfTime.HOURS; _attr_icon = "mdi:weather-sunny"; _attr_state_class = SensorStateClass.MEASUREMENT
    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("sunshine") is not None

class SunshineTodaySensor(IlmaprognoosSunshineSensor):
    _attr_name = "Päikesepaiste täna"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshine_today"
    @property
    def native_value(self): return self.coordinator.data.get("sunshine", {}).get("today")
class SunshineTomorrowSensor(IlmaprognoosSunshineSensor):
    _attr_name = "Päikesepaiste homme"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshine_tomorrow"
    @property
    def native_value(self): return self.coordinator.data.get("sunshine", {}).get("tomorrow")
class SunshineDay2Sensor(IlmaprognoosSunshineSensor):
    _attr_name = "Päikesepaiste (päev 2)"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshine_day_2"
    @property
    def native_value(self): return self.coordinator.data.get("sunshine", {}).get("day_2")
class SunshineDay3Sensor(IlmaprognoosSunshineSensor):
    _attr_name = "Päikesepaiste (päev 3)"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sunshine_day_3"
    @property
    def native_value(self): return self.coordinator.data.get("sunshine", {}).get("day_3")


class IlmaprognoosPrecipitationForecastSensor(IlmaprognoosBaseSensor):
    _attr_native_unit_of_measurement = UnitOfPrecipitationDepth.MILLIMETERS; _attr_icon = "mdi:water-percent"; _attr_state_class = SensorStateClass.MEASUREMENT
    @property
    def available(self) -> bool:
        return super().available and self.coordinator.data.get("precipitation_forecast") is not None

class PrecipitationTodaySensor(IlmaprognoosPrecipitationForecastSensor):
    _attr_name = "Sademed täna"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_precip_today"
    @property
    def native_value(self): return self.coordinator.data.get("precipitation_forecast", {}).get("today")
class PrecipitationTomorrowSensor(IlmaprognoosPrecipitationForecastSensor):
    _attr_name = "Sademed homme"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_precip_tomorrow"
    @property
    def native_value(self): return self.coordinator.data.get("precipitation_forecast", {}).get("tomorrow")
class PrecipitationDay2Sensor(IlmaprognoosPrecipitationForecastSensor):
    _attr_name = "Sademed (päev 2)"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_precip_day_2"
    @property
    def native_value(self): return self.coordinator.data.get("precipitation_forecast", {}).get("day_2")
class PrecipitationDay3Sensor(IlmaprognoosPrecipitationForecastSensor):
    _attr_name = "Sademed (päev 3)"
    def __init__(self, coordinator):
        super().__init__(coordinator); self._attr_unique_id = f"{coordinator.config_entry.entry_id}_precip_day_3"
    @property
    def native_value(self): return self.coordinator.data.get("precipitation_forecast", {}).get("day_3")