# In /custom_components/ilmaprognoos/coordinator.py

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
    DOMAIN, LOGGER, LOCATIONS, TICKER_URL_FORMAT, FORECAST_URL_FORMAT,
    HEADERS, DEFAULT_CURRENT_INTERVAL, DEFAULT_FORECAST_INTERVAL,
    MANUAL_LOCATION_ID, FORECAST_ONLY_STATION_ID
)

class IlmaprognoosDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize."""
        self.config_entry = entry
        config_data = entry.data
        
        self.is_forecast_only = False
        station_id = None
        
        if config_data.get("location") == MANUAL_LOCATION_ID:
            station_id = config_data.get("station_id")
            coords = config_data.get("coords")
            self.location_name = entry.title 
        else:
            self.location_name = config_data.get("location")
            location_data = LOCATIONS.get(self.location_name, {})
            station_id = location_data.get("station_id")
            coords = location_data.get("coords")

        if station_id == FORECAST_ONLY_STATION_ID:
            self.is_forecast_only = True
            self.current_url = None
            LOGGER.info("Operating in forecast-only mode.")
        else:
            self.current_url = TICKER_URL_FORMAT.format(station_id=station_id)
        
        self.forecast_url = FORECAST_URL_FORMAT.format(coords=coords)
        
        super().__init__(hass, LOGGER, name=DOMAIN)
        self._update_interval_from_options()

    def _update_interval_from_options(self):
        """Set the update interval from the config entry options."""
        forecast_minutes = self.config_entry.options.get(
            "forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60
        )
        
        # --- THIS IS THE ROBUST FIX ---
        if self.is_forecast_only:
            # If we are in forecast-only mode, the update interval is just the forecast interval.
            final_interval = forecast_minutes
        else:
            # Otherwise, use the SHORTER of the two intervals to ensure data freshness.
            current_minutes = self.config_entry.options.get(
                "current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60
            )
            final_interval = min(current_minutes, forecast_minutes)

        self.update_interval = timedelta(minutes=final_interval)
        LOGGER.info(f"Coordinator update interval set to {self.update_interval}")

    async def async_update_intervals(self):
        """Update the intervals after an options change and trigger a refresh."""
        self._update_interval_from_options()
        await self.async_request_refresh()

    async def _async_update_data(self):
        """Fetch data and apply fallback logic."""
        try:
            forecast_json = await self._fetch_json(self.forecast_url)
            
            current_html = None
            if not self.is_forecast_only:
                try:
                    current_html = await self._fetch_text(self.current_url)
                except Exception as e:
                    LOGGER.warning(f"Could not fetch current conditions, will use fallback: {e}")

            hourly_forecast = self._process_hourly_forecast(forecast_json)
            
            current_data = {}
            if current_html:
                current_data = self._parse_current(current_html)

            final_current_data = self._merge_current_with_fallback(current_data, hourly_forecast)

            return {
                "current": final_current_data,
                "daily": self._process_daily_forecast(forecast_json),
                "hourly": hourly_forecast,
                "warnings": self._process_warnings(forecast_json),
                "location": self.location_name
            }
        except Exception as err:
            LOGGER.error(f"Unexpected error during data update: {err}")
            raise UpdateFailed(f"An unexpected error occurred: {err}")

    def _merge_current_with_fallback(self, current_data: dict, hourly_forecast: list) -> dict:
        """Merge current data with forecast fallback for missing values."""
        if not hourly_forecast: return current_data

        first_hour = hourly_forecast[0]
        final_data = current_data.copy()

        fallback_map = { "temperature": "temperature", "sademed": "precipitation", "wind_speed": "wind_speed", "ohurohk": "pressure" }

        for key, forecast_key in fallback_map.items():
            if final_data.get(key) is None or final_data.get(key) == 0:
                if forecast_key and first_hour.get(forecast_key) is not None:
                    LOGGER.debug(f"Fallback used for '{key}' from forecast.")
                    if key == "sademed": final_data[key] = f"{first_hour[forecast_key]} mm/h"
                    elif key == "ohurohk": final_data[key] = f"{first_hour[forecast_key]} hPa"
                    else: final_data[key] = first_hour[forecast_key]
        
        if final_data.get("tuul") is None:
            wind_dir_name = first_hour.get("wind_bearing_name")
            wind_speed_ms = first_hour.get("wind_speed")
            if wind_dir_name is not None and wind_speed_ms is not None:
                LOGGER.debug("Fallback used for 'tuul' from forecast.")
                final_data["tuul"] = f"{wind_dir_name} {wind_speed_ms} m/s"
        
        return final_data

    async def _fetch_text(self, url):
        return await self.hass.async_add_executor_job(self._do_fetch_text, url)

    def _do_fetch_text(self, url):
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.text

    async def _fetch_json(self, url):
        return await self.hass.async_add_executor_job(self._do_fetch_json, url)

    def _do_fetch_json(self, url):
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        return response.json()

    def _parse_current(self, html):
        try:
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            if not table: return {}
            def is_data_cell(cell):
                text = cell.get_text()
                return "Temperatuur" in text or "Tuul" in text or "Õhuniiskus" in text
            data_cell = next((cell for row in table.find_all('tr') if (cell := row.find('td')) and is_data_cell(cell)), None)
            if not data_cell:
                LOGGER.warning("Could not find a valid data cell in the ticker HTML.")
                return {}
            attributes = {}
            data_lines = data_cell.get_text(separator='\n', strip=True).split('\n')
            for line in data_lines:
                if ":" in line:
                    key, value = [x.strip() for x in line.split(':', 1)]
                    key_clean = key.lower().replace(" ", "_").replace("õ", "o").replace("ä", "a").replace("ü", "u")
                    try:
                        if "temperatuur" in key_clean and "vee" not in key_clean:
                            attributes["temperature"] = float(value.split(' ')[0].replace(',', '.'))
                            attributes[key_clean] = value
                        elif "veetemp" in key_clean: attributes["veetemp"] = float(value.split(' ')[0].replace(',', '.'))
                        elif "veetase" in key_clean: attributes["veetase"] = int(value.split(' ')[0].replace(',', '.'))
                        else: attributes[key_clean] = value
                    except (ValueError, IndexError):
                        LOGGER.warning(f"Could not parse value for '{key}'. Skipping.")
                        continue
            if attributes.get("tuul") and " " in attributes["tuul"]:
                try: attributes["wind_speed"] = float(attributes["tuul"].split(" ")[-2])
                except (ValueError, IndexError): pass
            LOGGER.debug(f"Successfully parsed current conditions: {attributes}")
            return attributes
        except Exception as e:
            LOGGER.warning(f"Failed to parse current weather HTML: {e}")
            return {}
            
    def _process_daily_forecast(self, api_data):
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
                forecast_day = {"datetime": date_iso, "temperature": max(data["temps"]), "templow": min(data["temps"]), "condition": self._map_condition(dominant_condition.lower()), "precipitation": sum(data["precip"])}
                final_forecast_list.append(forecast_day)
            return final_forecast_list
        except Exception as e:
            LOGGER.warning(f"Failed to process daily forecast: {e}")
            return []

    def _process_hourly_forecast(self, api_data):
        try:
            hourly_forecasts = api_data.get("forecast", {}).get("tabular", {}).get("time", [])
            if not hourly_forecasts: return []
            final_forecast_list = []
            for hour in hourly_forecasts:
                forecast_hour = {"datetime": hour["@attributes"]["from"], "temperature": float(hour["temperature"]["@attributes"]["value"]), "condition": self._map_condition(hour["phenomen"]["@attributes"]["et"].lower()), "precipitation": float(hour["precipitation"]["@attributes"]["value"]), "wind_speed": float(hour["windSpeed"]["@attributes"]["mps"]), "wind_bearing": float(hour["windDirection"]["@attributes"]["deg"]), "wind_bearing_name": hour["windDirection"]["@attributes"]["name"], "pressure": float(hour["pressure"]["@attributes"]["value"])}
                final_forecast_list.append(forecast_hour)
            return final_forecast_list
        except Exception as e:
            LOGGER.warning(f"Failed to process hourly forecast: {e}")
            return []
            
    def _process_warnings(self, api_data):
        try:
            warnings_string = api_data.get("warnings")
            if not warnings_string or warnings_string == "[]": return []
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
        """Map Estonian condition text to a generic Home Assistant condition."""
        # --- THIS IS THE CHANGE ---
        if "selge" in condition_text: return "clear" # No longer returns "sunny"
        
        if "vähene pilvisus" in condition_text: return "partlycloudy"
        if "pilves selgimistega" in condition_text: return "partlycloudy"
        if "vahelduv pilvisus" in condition_text: return "partlycloudy"
        if "pilves" in condition_text: return "cloudy"
        if "vihm" in condition_text: return "rainy"
        if "lumi" in condition_text: return "snowy"
        if "äike" in condition_text: return "lightning-rainy"
        if "udu" in condition_text: return "fog"
        return "cloudy"