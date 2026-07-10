# In /custom_components/ilmaprognoos/weather.py

from datetime import datetime
from homeassistant.components.weather import (
    WeatherEntity,
    WeatherEntityFeature,
    Forecast,
)
from homeassistant.const import (
    UnitOfPressure, 
    UnitOfSpeed, 
    UnitOfTemperature,
    UnitOfPrecipitationDepth,
    UnitOfLength # Added for visibility
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
    _attr_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_visibility_unit = UnitOfLength.KILOMETERS
    _attr_attribution = "Andmed: ilmateenistus.ee"

    def __init__(self, coordinator):
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_weather"
        
        coords = coordinator.config_entry.data.get("coords")
        config_url = f"https://www.ilmateenistus.ee/ilm/prognoosid/asukoha-prognoos/?coordinates={coords}" if coords else "https://www.ilmateenistus.ee"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.config_entry.entry_id)},
            "name": coordinator.config_entry.title,
            "manufacturer": "Ilmaprognoos",
            "entry_type": "service",
            "model": "Keskkonnaagentuur & ilmateenistus.ee",
            "configuration_url": config_url,
        }
        self._attr_supported_features = (WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    def _get_sun_aware_condition(self, condition: str, timestamp: datetime) -> str:
        if condition == "clear": return "sunny" if is_up(self.hass, timestamp) else "clear-night"
        return condition

    @property
    def name(self): return "Ilm"

    @property
    def condition(self):
        use_warning_override = self.coordinator.config_entry.options.get(CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE)
        warnings = self.coordinator.data.get("warnings",[])
        if use_warning_override and warnings:
            for w in warnings:
                if "thunderstorm" in w.get("warningEng", "").lower(): return "lightning-rainy"
            for w in warnings:
                w_type = w.get("warningEng", "").lower()
                if "snow" in w_type or "blizzard" in w_type: return "snowy"
                if "sleet" in w_type or "freezing_rain" in w_type: return "snowy-rainy"
            for w in warnings:
                w_type = w.get("warningEng", "").lower()
                if "rain" in w_type: return "rainy"
                if "wind" in w_type: return "windy"
                if "fog" in w_type: return "fog"
            return "exceptional"

        hourly_forecast = self.coordinator.data.get("hourly",[])
        if hourly_forecast:
            now = dt_util.now()
            for hour in hourly_forecast:
                try:
                    forecast_time = dt_util.as_local(datetime.fromisoformat(hour["datetime"]))
                    if forecast_time >= now: return self._get_sun_aware_condition(hour.get("condition"), forecast_time)
                except (ValueError, KeyError): continue
            if hourly_forecast:
                last_forecast_time = dt_util.as_local(datetime.fromisoformat(hourly_forecast[-1]["datetime"]))
                return self._get_sun_aware_condition(hourly_forecast[-1].get("condition"), last_forecast_time)

        daily_forecast = self.coordinator.data.get("daily",[])
        if daily_forecast: return self._get_sun_aware_condition(daily_forecast[0].get("condition"), dt_util.now())
        return None

    @property
    def native_temperature(self): return self.coordinator.data.get("current", {}).get("temperature")
    
    @property
    def native_pressure(self):
        val = self.coordinator.data.get("current", {}).get("ohurohk")
        if val is None: return None
        if isinstance(val, (int, float)): return float(val)
        try: return float(str(val).split(" ")[0])
        except (ValueError, IndexError): return None
        
    @property
    def humidity(self):
        val = self.coordinator.data.get("current", {}).get("ohuniiskus")
        if val is None: return None
        if isinstance(val, (int, float)): return float(val)
        try: return float(str(val).replace("%", ""))
        except ValueError: return None
        
    @property
    def native_wind_speed(self):
        wind_ms = self.coordinator.data.get("current", {}).get("wind_speed")
        if wind_ms is not None: 
            try: return round(float(wind_ms) * 3.6, 1)
            except ValueError: return None
        return None

    # --- NEW: Wind Gusts & Visibility ---
    @property
    def native_wind_gust_speed(self):
        wind_ms = self.coordinator.data.get("current", {}).get("wind_speed_max")
        if wind_ms is not None: 
            try: return round(float(wind_ms) * 3.6, 1)
            except ValueError: return None
        return None

    @property
    def native_visibility(self):
        val = self.coordinator.data.get("current", {}).get("visibility")
        if val is not None: return float(val)
        return None
        
    @property
    def wind_bearing(self):
        wb = self.coordinator.data.get("current", {}).get("wind_bearing")
        if isinstance(wb, (int, float)): return wb
        wind_string = self.coordinator.data.get("current", {}).get("tuul", "")
        if isinstance(wind_string, str) and " " in wind_string: 
            return " ".join(wind_string.split(" ")[0:-2])
        return wind_string

    @property
    def native_precipitation(self):
        val = self.coordinator.data.get("current", {}).get("sademed")
        if val is None: return 0.0
        if isinstance(val, (int, float)): return float(val)
        try: return float(str(val).split(" ")[0])
        except (ValueError, IndexError): return 0.0

    async def async_forecast_daily(self) -> list[Forecast] | None:
        daily_data = self.coordinator.data.get("daily")
        if not daily_data: return None
        result_list = list()
        for item in daily_data:
            try:
                forecast_date = dt_util.parse_date(item.get("datetime"))
                if not forecast_date: continue
                forecast_time = dt_util.as_local(datetime.combine(forecast_date, datetime.min.time()))
                day_data = dict()
                day_data["datetime"] = forecast_time.isoformat() 
                day_data["native_temperature"] = item.get("temperature")
                day_data["native_templow"] = item.get("templow")
                day_data["condition"] = self._get_sun_aware_condition(item.get("condition"), forecast_time)
                day_data["native_precipitation"] = item.get("precipitation") 
                result_list.append(day_data)
            except Exception: continue
        return result_list

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        hourly_data = self.coordinator.data.get("hourly")
        if not hourly_data: return None
        result_list = list()
        now = dt_util.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        for item in hourly_data:
            try:
                dt_str = item.get("datetime")
                if not dt_str: continue
                f_time = dt_util.as_local(datetime.fromisoformat(dt_str))
                if f_time < current_hour: continue
                
                hour_data = dict()
                hour_data["datetime"] = f_time.isoformat()
                hour_data["native_temperature"] = item.get("temperature")
                hour_data["condition"] = self._get_sun_aware_condition(item.get("condition"), f_time)
                hour_data["native_precipitation"] = item.get("precipitation")
                hour_data["native_wind_speed"] = item.get("wind_speed")
                hour_data["wind_bearing"] = item.get("wind_bearing")
                hour_data["native_pressure"] = item.get("pressure")
                result_list.append(hour_data)
            except Exception: continue
        return result_list
