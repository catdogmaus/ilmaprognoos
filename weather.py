# In /custom_components/ilmaprognoos/weather.py

from datetime import datetime
from homeassistant.components.weather import (
    WeatherEntity, WeatherEntityFeature, Forecast
)
from homeassistant.const import (
    UnitOfPressure, UnitOfSpeed, UnitOfTemperature
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.sun import is_up
from homeassistant.util import dt as dt_util

from .const import DOMAIN, CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the weather platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([IlmaprognoosWeather(coordinator)])


class IlmaprognoosWeather(CoordinatorEntity, WeatherEntity):
    """Representation of a weather entity for Ilmaprognoos."""
    _attr_has_entity_name = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_pressure_unit = UnitOfPressure.HPA
    _attr_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_attribution = "Andmed: ilmateenistus.ee"

    def __init__(self, coordinator):
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_weather"
        self._attr_device_info = { "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)}, "name": coordinator.config_entry.title, "manufacturer": "Ilmaprognoos", "entry_type": "service", "model": "Ilmateenistus API", }
        self._attr_supported_features = (WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    def _get_sun_aware_condition(self, condition: str, timestamp: datetime) -> str:
        """Return sunny or clear-night based on sun state at a given time."""
        if condition == "clear":
            return "sunny" if is_up(self.hass, timestamp) else "clear-night"
        return condition

    @property
    def name(self): return "Ilm"

    @property
    def condition(self):
        """Return the current condition, with a comprehensive warning override."""
        use_warning_override = self.coordinator.config_entry.options.get(CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE)
        warnings = self.coordinator.data.get("warnings", [])
        
        if use_warning_override and warnings:
            # --- THIS IS THE EXPANDED LOGIC ---
            warning_type = warnings[0].get("warningEng", "").lower()
            if "thunderstorm" in warning_type: return "lightning-rainy"
            if "rain" in warning_type: return "rainy"
            if "wind" in warning_type: return "windy"
            if "snow" in warning_type or "blizzard" in warning_type: return "snowy"
            if "sleet" in warning_type or "freezing_rain" in warning_type: return "snowy-rainy"
            if "fog" in warning_type: return "fog"
            if "frost" in warning_type or "cold" in warning_type or "heat" in warning_type: return "exceptional"
            # Fallback for any other unknown warning type
            return "exceptional"

        # If no override, proceed with the precise hourly/daily logic
        hourly_forecast = self.coordinator.data.get("hourly", [])
        if hourly_forecast:
            now = dt_util.now()
            for hour in hourly_forecast:
                try:
                    forecast_time = dt_util.as_local(datetime.fromisoformat(hour["datetime"]))
                    if forecast_time >= now:
                        return self._get_sun_aware_condition(hour.get("condition"), forecast_time)
                except (ValueError, KeyError): continue
            if hourly_forecast:
                last_forecast_time = dt_util.as_local(datetime.fromisoformat(hourly_forecast[-1]["datetime"]))
                return self._get_sun_aware_condition(hourly_forecast[-1].get("condition"), last_forecast_time)

        daily_forecast = self.coordinator.data.get("daily", [])
        if daily_forecast:
            return self._get_sun_aware_condition(daily_forecast[0].get("condition"), dt_util.now())
        return None

    # ... (all other properties and functions remain unchanged) ...
    @property
    def native_temperature(self): return self.coordinator.data.get("current", {}).get("temperature")
    @property
    def native_pressure(self):
        pressure_str = self.coordinator.data.get("current", {}).get("ohurohk", "0 hPa")
        try: return float(pressure_str.split(" ")[0])
        except (ValueError, IndexError): return None
    @property
    def humidity(self):
        humidity_str = self.coordinator.data.get("current", {}).get("ohuniiskus", "0%")
        try: return float(humidity_str.replace("%", ""))
        except ValueError: return None
    @property
    def native_wind_speed(self):
        wind_ms = self.coordinator.data.get("current", {}).get("wind_speed", 0)
        if wind_ms is not None: return round(wind_ms * 3.6, 1)
        return None
    @property
    def wind_bearing(self):
        wind_string = self.coordinator.data.get("current", {}).get("tuul", "")
        if " " in wind_string: return " ".join(wind_string.split(" ")[0:-2])
        return wind_string
    async def async_forecast_daily(self) -> list[Forecast] | None:
        daily_data = self.coordinator.data.get("daily")
        if not daily_data: return None
        forecast = []
        for item in daily_data:
            forecast_date = dt_util.parse_date(item.get("datetime"))
            forecast_time = dt_util.as_local(datetime.combine(forecast_date, datetime.min.time()))
            forecast.append({"datetime": item.get("datetime"), "native_temperature": item.get("temperature"), "native_templow": item.get("templow"), "condition": self._get_sun_aware_condition(item.get("condition"), forecast_time), "native_precipitation_value": item.get("precipitation"),})
        return forecast
    async def async_forecast_hourly(self) -> list[Forecast] | None:
        hourly_data = self.coordinator.data.get("hourly")
        if not hourly_data: return None
        forecast = []
        for item in hourly_data:
            forecast_time = dt_util.as_local(datetime.fromisoformat(item.get("datetime")))
            forecast.append({"datetime": item.get("datetime"), "native_temperature": item.get("temperature"), "condition": self._get_sun_aware_condition(item.get("condition"), forecast_time), "native_precipitation_value": item.get("precipitation"), "native_wind_speed": round(item.get("wind_speed", 0) * 3.6, 1), "wind_bearing": item.get("wind_bearing"), "native_pressure": item.get("pressure"),})
        return forecast