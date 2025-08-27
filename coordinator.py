# In /custom_components/ilmateenistus/coordinator.py

import async_timeout
from datetime import timedelta, datetime
from bs4 import BeautifulSoup
import json
from collections import defaultdict
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    LOGGER,
    LOCATIONS,
    TICKER_URL_FORMAT,
    FORECAST_URL_FORMAT,
    HEADERS,
    DEFAULT_CURRENT_INTERVAL,
    DEFAULT_FORECAST_INTERVAL,
    MANUAL_LOCATION_ID,
)

def fetch_data_sync(current_url, forecast_url, headers):
    """Fetch both URLs using the requests library."""
    current_response = requests.get(current_url, headers=headers, timeout=20)
    current_response.raise_for_status()
    
    forecast_response = requests.get(forecast_url, headers=headers, timeout=20)
    forecast_response.raise_for_status()
    
    return current_response.text, forecast_response.json()


class IlmateenistusDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize."""
        self.config_entry = entry
        
        # --- DEBUGGING LOG ---
        LOGGER.debug(f"[coordinator] Initializing with entry data: {entry.data}")
        
        config_data = entry.data
        
        if config_data.get("location") == MANUAL_LOCATION_ID:
            # This is a manually configured entry
            station_id = config_data.get("station_id")
            coords = config_data.get("coords")
            self.location_name = entry.title 
        else:
            # This is a pre-defined location
            self.location_name = config_data.get("location")
            location_data = LOCATIONS.get(self.location_name, {})
            station_id = location_data.get("station_id")
            coords = location_data.get("coords")

        self.current_url = TICKER_URL_FORMAT.format(station_id=station_id)
        self.forecast_url = FORECAST_URL_FORMAT.format(coords=coords)
        
        # --- DEBUGGING LOG ---
        LOGGER.debug(f"[coordinator] Constructed Current URL: {self.current_url}")
        LOGGER.debug(f"[coordinator] Constructed Forecast URL: {self.forecast_url}")
        
        super().__init__(hass, LOGGER, name=DOMAIN)
        self._update_interval_from_options()

    def _update_interval_from_options(self):
        """Set the update interval from the config entry options."""
        current_minutes = self.config_entry.options.get(
            "current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60
        )
        forecast_minutes = self.config_entry.options.get(
            "forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60
        )
        final_interval = min(current_minutes, forecast_minutes)
        self.update_interval = timedelta(minutes=final_interval)
        LOGGER.debug(f"Coordinator update interval set to {self.update_interval}")

    async def async_update_intervals(self):
        """Update the intervals after an options change and trigger a refresh."""
        self._update_interval_from_options()
        await self.async_request_refresh()

    async def _async_update_data(self):
        """Fetch data from API endpoint using requests in an executor."""
        try:
            current_html, forecast_json = await self.hass.async_add_executor_job(
                fetch_data_sync, self.current_url, self.forecast_url, HEADERS
            )

            processed_data = {
                "current": self._parse_current(current_html),
                "daily": self._process_daily_forecast(forecast_json),
                "hourly": self._process_hourly_forecast(forecast_json),
                "warnings": self._process_warnings(forecast_json),
                "location": self.location_name
            }
            return processed_data

        except requests.exceptions.HTTPError as err:
            LOGGER.error(f"HTTP Error fetching data: {err}")
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
            LOGGER.error(f"Unexpected error fetching data: {err}")
            raise UpdateFailed(f"An unexpected error occurred: {err}")

    def _parse_current(self, html):
        """Parse current conditions from HTML."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            if not table: return {}
            data_cell = next((cell for row in table.find_all('tr') if (cell := row.find('td')) and "Temperatuur" in cell.get_text()), None)
            
            if not data_cell: return {}
            attributes = {}
            main_state = "Unknown"
            
            data_lines = data_cell.get_text(separator='\n', strip=True).split('\n')
            for line in data_lines:
                if ":" in line:
                    key, value = [x.strip() for x in line.split(':', 1)]
                    key_clean = key.lower().replace(" ", "_").replace("õ", "o").replace("ä", "a").replace("ü", "u")
                    attributes[key_clean] = value
                    if "temperatuur" in key_clean:
                        main_state = value.split(' ')[0].replace(',', '.')
            
            if main_state != "Unknown":
                attributes["temperature"] = float(main_state)
            if attributes.get("tuul") and " " in attributes["tuul"]:
                attributes["wind_speed"] = float(attributes["tuul"].split(" ")[-2])
            return attributes
        except Exception as e:
            LOGGER.warning(f"Failed to parse current weather HTML: {e}")
            return {}

    def _process_daily_forecast(self, api_data):
        """Process hourly data into a daily forecast."""
        try:
            hourly_forecasts = api_data.get("forecast", {}).get("tabular", {}).get("time", [])
            if not hourly_forecasts: return []
            daily_data = defaultdict(lambda: {"temps": [], "conditions": [], "precip": []})
            for hour in hourly_forecasts:
                dt_object = datetime.fromisoformat(hour["@attributes"]["from"])
                date_key = dt_object.date().isoformat()
                daily_data[date_key]["temps"].append(float(hour["temperature"]["@attributes"]["value"]))
                daily_data[date_key]["conditions"].append(hour["phenomen"]["@attributes"]["et"])
                daily_data[date_key]["precip"].append(float(hour["precipitation"]["@attributes"]["value"]))
            final_forecast_list = []
            for date_iso, data in sorted(daily_data.items()):
                if not data["temps"]: continue
                day_conditions = [c for c in data["conditions"] if "selge" not in c.lower() and "vähene" not in c.lower()]
                if not day_conditions: day_conditions = data["conditions"]
                dominant_condition = max(set(day_conditions), key=day_conditions.count)
                forecast_day = {
                    "datetime": date_iso,
                    "temperature": max(data["temps"]),
                    "templow": min(data["temps"]),
                    "condition": self._map_condition(dominant_condition.lower()),
                    "precipitation": sum(data["precip"]),
                }
                final_forecast_list.append(forecast_day)
            return final_forecast_list
        except Exception as e:
            LOGGER.warning(f"Failed to process daily forecast: {e}")
            return []

    def _process_hourly_forecast(self, api_data):
        """Process hourly data."""
        try:
            hourly_forecasts = api_data.get("forecast", {}).get("tabular", {}).get("time", [])
            if not hourly_forecasts: return []
            final_forecast_list = []
            for hour in hourly_forecasts:
                forecast_hour = {
                    "datetime": hour["@attributes"]["from"],
                    "temperature": float(hour["temperature"]["@attributes"]["value"]),
                    "condition": self._map_condition(hour["phenomen"]["@attributes"]["et"].lower()),
                    "precipitation": float(hour["precipitation"]["@attributes"]["value"]),
                    "wind_speed": float(hour["windSpeed"]["@attributes"]["mps"]),
                    "wind_bearing": float(hour["windDirection"]["@attributes"]["deg"]),
                    "pressure": float(hour["pressure"]["@attributes"]["value"]),
                }
                final_forecast_list.append(forecast_hour)
            return final_forecast_list
        except Exception as e:
            LOGGER.warning(f"Failed to process hourly forecast: {e}")
            return []
        
    def _process_warnings(self, api_data):
        """Process warnings."""
        try:
            warnings_string = api_data.get("warnings")
            if not warnings_string or warnings_string == "[]":
                return []
            warnings_data = json.loads(warnings_string)
            final_warnings_list = []
            seen_descriptions = set()
            if isinstance(warnings_data, list):
                for warning in warnings_data:
                    description = warning.get("description")
                    if description and description not in seen_descriptions:
                        final_warnings_list.append(warning)
                        seen_descriptions.add(description)
            return final_warnings_list
        except Exception as e:
            LOGGER.warning(f"Failed to process warnings: {e}")
            return []

    def _map_condition(self, condition_text):
        """Map Estonian condition text to a Home Assistant condition."""
        if "selge" in condition_text: return "sunny"
        if "vähene pilvisus" in condition_text: return "partlycloudy"
        if "pilves selgimistega" in condition_text: return "partlycloudy"
        if "vahelduv pilvisus" in condition_text: return "partlycloudy"
        if "pilves" in condition_text: return "cloudy"
        if "vihm" in condition_text: return "rainy"
        if "lumi" in condition_text: return "snowy"
        if "äike" in condition_text: return "lightning-rainy"
        if "udu" in condition_text: return "fog"
        return "cloudy"