# In /custom_components/ilmateenistus/weather.py

from homeassistant.components.weather import (
    WeatherEntity,
    WeatherEntityFeature,
    Forecast,
)
from homeassistant.const import (
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the weather platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([IlmateenistusWeather(coordinator)])


class IlmateenistusWeather(CoordinatorEntity, WeatherEntity):
    """Representation of a weather entity for Ilmateenistus."""

    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_pressure_unit = UnitOfPressure.HPA
    _attr_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    

    _attr_attribution = "Andmed: ilmateenistus.ee"

    def __init__(self, coordinator):
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_weather"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.config_entry.title, # Use the city name for the device
            "manufacturer": "Ilmateenistus",
            "entry_type": "service",
        }
        self._attr_supported_features = (
            WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        # Use Estonian name "Ilm" (Weather)
        return "Ilm"

    @property
    def condition(self):
        """Return the current condition."""
        warnings = self.coordinator.data.get("warnings", [])
        if warnings:
            warning_type = warnings[0].get("warningEng", "").lower()
            if "thunderstorm" in warning_type: return "lightning-rainy"
            if "rain" in warning_type: return "rainy"
            if "snow" in warning_type: return "snowy"
            if "wind" in warning_type: return "windy"
            if "fog" in warning_type: return "fog"
            return "exceptional"

        daily_forecast = self.coordinator.data.get("daily", [])
        if daily_forecast:
            return daily_forecast[0].get("condition")
        return None


    @property
    def native_temperature(self):
        """Return the temperature."""
        return self.coordinator.data.get("current", {}).get("temperature")

    @property
    def native_pressure(self):
        """Return the pressure."""
        pressure_str = self.coordinator.data.get("current", {}).get("ohurohk", "0 hPa")
        try:
            return float(pressure_str.split(" ")[0])
        except (ValueError, IndexError):
            return None

    @property
    def humidity(self):
        """Return the humidity."""
        humidity_str = self.coordinator.data.get("current", {}).get("ohuniiskus", "0%")
        try:
            return float(humidity_str.replace("%", ""))
        except ValueError:
            return None
            
    @property
    def native_wind_speed(self):
        """Return the wind speed in km/h."""
        wind_ms = self.coordinator.data.get("current", {}).get("wind_speed", 0)
        if wind_ms is not None:
            return round(wind_ms * 3.6, 1)
        return None

    @property
    def wind_bearing(self):
        """Return the wind bearing."""
        wind_string = self.coordinator.data.get("current", {}).get("tuul", "")
        if " " in wind_string:
            parts = wind_string.split(" ")
            return " ".join(parts[0:-2])
        return wind_string

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        daily_data = self.coordinator.data.get("daily")
        if not daily_data:
            return None
        
        forecast = []
        for item in daily_data:
            forecast.append(
                {
                    "datetime": item.get("datetime"),
                    "native_temperature": item.get("temperature"),
                    "native_templow": item.get("templow"),
                    "condition": item.get("condition"),
                    "native_precipitation_value": item.get("precipitation"),
                }
            )
        return forecast

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""
        hourly_data = self.coordinator.data.get("hourly")
        if not hourly_data:
            return None
            
        forecast = []
        for item in hourly_data:
            forecast.append(
                {
                    "datetime": item.get("datetime"),
                    "native_temperature": item.get("temperature"),
                    "condition": item.get("condition"),
                    "native_precipitation_value": item.get("precipitation"),
                    "native_wind_speed": round(item.get("wind_speed", 0) * 3.6, 1),
                    "wind_bearing": item.get("wind_bearing"),
                    "native_pressure": item.get("pressure"),
                }
            )
        return forecast