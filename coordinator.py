# In /custom_components/ilmaprognoos/coordinator.py

import async_timeout
from datetime import timedelta, datetime
import json
from collections import defaultdict
import requests
import xml.etree.ElementTree as ET

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.sun import is_up
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN, LOGGER, XML_OBSERVATIONS_URL, FORECAST_URL_FORMAT,
    HEADERS, DEFAULT_CURRENT_INTERVAL, DEFAULT_FORECAST_INTERVAL,
    FORECAST_ONLY_ID, NO_SECONDARY_ID
)

def fetch_data_sync(xml_url, forecast_url, headers):
    """Fetch data using requests."""
    xml_text = None
    if xml_url:
        xml_res = requests.get(xml_url, headers=headers, timeout=20)
        xml_res.raise_for_status()
        xml_text = xml_res.text
        
    forecast_res = requests.get(forecast_url, headers=headers, timeout=20)
    forecast_res.raise_for_status()
    
    return xml_text, forecast_res.json()


class IlmaprognoosDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize."""
        self.config_entry = entry
        config_data = entry.data
        
        self.location_name = config_data.get("location_name", "Unknown")
        self.primary_station = config_data.get("primary_station")
        self.secondary_station = config_data.get("secondary_station")
        self.coords = config_data.get("coords")
        
        self.is_forecast_only = (self.primary_station == FORECAST_ONLY_ID)
        self.xml_url = None if self.is_forecast_only else XML_OBSERVATIONS_URL
        self.forecast_url = FORECAST_URL_FORMAT.format(coords=self.coords)
        
        slug = config_data.get("slug", "unknown")
        self.weather_entity_id = f"weather.{slug}_ilm"
        self.status_entity_id = f"binary_sensor.{slug}_uuendamise_staatus"
        
        super().__init__(hass, LOGGER, name=DOMAIN)
        self._update_interval_from_options()

    def _update_interval_from_options(self):
        forecast_minutes = self.config_entry.options.get("forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60)
        if self.is_forecast_only: 
            final_interval = forecast_minutes
        else:
            current_minutes = self.config_entry.options.get("current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60)
            final_interval = min(current_minutes, forecast_minutes)
        self.update_interval = timedelta(minutes=final_interval)

    async def async_update_intervals(self):
        self._update_interval_from_options()
        await self.async_request_refresh()

    async def _async_update_data(self):
        last_success_time = getattr(self, "last_update_success_timestamp", None)
        if self.last_update_success and last_success_time and (dt_util.utcnow() - last_success_time < timedelta(seconds=60)):
            return self.data

        try:
            xml_text, forecast_json = await self.hass.async_add_executor_job(
                fetch_data_sync, self.xml_url, self.forecast_url, HEADERS
            )

            hourly_forecast = self._process_hourly_forecast(forecast_json)
            
            if not hourly_forecast and getattr(self, "data", None) is not None:
                raise UpdateFailed("Prognoosi andmed puuduvad (tühi JSON).")
            
            current_data = {}
            if xml_text:
                current_data = self._parse_xml_observations(xml_text)
            
            final_current_data = self._merge_current_with_forecast(current_data, hourly_forecast)
            
            sunshine_forecast = self._process_sunshine_forecast(hourly_forecast)
            precipitation_forecast = self._process_precipitation_forecast(hourly_forecast)

            self.hass.bus.async_fire("logbook_entry", {"message": "Uuendamine õnnestus", "entity_id": self.status_entity_id, "domain": DOMAIN})

            return {
                "current": final_current_data,
                "daily": self._process_daily_forecast(forecast_json),
                "hourly": hourly_forecast,
                "warnings": self._process_warnings(forecast_json),
                "location": self.location_name,
                "sunshine": sunshine_forecast,
                "precipitation_forecast": precipitation_forecast
            }
        except Exception as err:
            self.hass.bus.async_fire("logbook_entry", {"message": f"Uuendamine ebaõnnestus: {err}", "entity_id": self.status_entity_id, "domain": DOMAIN})
            
            if getattr(self, "data", None) is not None:
                LOGGER.warning(f"Data fetch failed: {err}. Persisting old data to prevent 'Unknown' state.")
                return self.data
                
            raise UpdateFailed(f"An unexpected error occurred: {err}")

    def _extract_station_data(self, station_element):
        """Extracts ALL data from the XML element."""
        data = {}
        mapping = {
            "temperature": "airtemperature",
            "wind_speed": "windspeed",
            "wind_speed_max": "windspeedmax",
            "wind_bearing": "winddirection",
            "ohuniiskus": "relativehumidity",
            "ohurohk": "airpressure",
            "sademed": "precipitations",
            "veetase": "waterlevel",
            "veetase_eh2000": "waterlevel_eh2000",
            "veetemp": "watertemperature",
            "visibility": "visibility",
            "uvindex": "uvindex",
            "sunshineduration": "sunshineduration",
            "globalradiation": "globalradiation"
        }
        for our_key, xml_key in mapping.items():
            val = station_element.findtext(xml_key)
            if val is not None and val.strip() != "":
                try: 
                    parsed_val = float(val)
                    if our_key == "sunshineduration":
                        data[our_key] = round(parsed_val / 60.0, 1) # Convert minutes to hours
                    else:
                        data[our_key] = parsed_val
                except ValueError: 
                    pass
                
        # Extract the English phenomenon string as text
        phenom = station_element.findtext("phenomenon")
        if phenom and phenom.strip():
            data["phenomenon"] = phenom.strip()

        return data

    def _parse_xml_observations(self, xml_text):
        """Finds primary and secondary stations and merges them."""
        try:
            root = ET.fromstring(xml_text)
            primary_data = {}
            secondary_data = {}
            
            for station in root.findall('station'):
                name = station.findtext('name')
                if name == self.primary_station:
                    primary_data = self._extract_station_data(station)
                elif name == self.secondary_station and self.secondary_station != NO_SECONDARY_ID:
                    secondary_data = self._extract_station_data(station)
            
            # Start with secondary data as a base, overwrite with primary data
            merged = secondary_data.copy()
            merged.update(primary_data)
            return merged
        except Exception as e:
            LOGGER.warning(f"Failed to parse XML: {e}")
            return {}

    def _merge_current_with_forecast(self, current_data: dict, hourly_forecast: list) -> dict:
        """Fallback to forecast if XML is missing critical data."""
        if not hourly_forecast: return current_data
        first_hour = hourly_forecast[0]
        final_data = current_data.copy()
        
        if final_data.get("temperature") is None: final_data["temperature"] = first_hour.get("temperature")
        if final_data.get("sademed") is None: final_data["sademed"] = first_hour.get("precipitation")
        if final_data.get("wind_speed") is None: final_data["wind_speed"] = first_hour.get("wind_speed")
        if final_data.get("wind_bearing") is None: final_data["wind_bearing"] = first_hour.get("wind_bearing")
        if final_data.get("ohurohk") is None: final_data["ohurohk"] = first_hour.get("pressure")
        if final_data.get("phenomenon") is None: final_data["phenomenon"] = first_hour.get("condition_text_et")
        
        if final_data.get("tuul") is None:
            wind_dir_name = first_hour.get("wind_bearing_name")
            wind_speed_ms = first_hour.get("wind_speed")
            if wind_dir_name is not None and wind_speed_ms is not None:
                final_data["tuul"] = f"{wind_dir_name} {wind_speed_ms} m/s"
        return final_data

    def _process_daily_forecast(self, api_data):
        try:
            hourly_forecasts = api_data.get("forecast", {}).get("tabular", {}).get("time",[])
            if not hourly_forecasts: return []
            daily_data = defaultdict(lambda: {"temps": [], "conditions":[], "precip":[]})
            for hour in hourly_forecasts:
                try:
                    dt_object = datetime.fromisoformat(hour.get("@attributes", {}).get("from", ""))
                    date_key = dt_object.date().isoformat()
                    
                    temp = hour.get("temperature", {}).get("@attributes", {}).get("value")
                    if temp is not None: daily_data[date_key]["temps"].append(float(temp))
                    
                    cond = hour.get("phenomen", {}).get("@attributes", {}).get("et")
                    if cond: daily_data[date_key]["conditions"].append(cond)
                    
                    precip = hour.get("precipitation", {}).get("@attributes", {}).get("value")
                    if precip is not None: daily_data[date_key]["precip"].append(float(precip))
                except Exception: continue

            final_forecast_list =[]
            for date_iso, data in sorted(daily_data.items()):
                if not data["temps"]: continue
                day_conditions = [c for c in data["conditions"] if "selge" not in c.lower() and "vähene" not in c.lower()]
                if not day_conditions: day_conditions = data["conditions"]
                dominant_condition = max(set(day_conditions), key=day_conditions.count) if day_conditions else ""
                
                forecast_day = {
                    "datetime": date_iso, 
                    "temperature": max(data["temps"]), 
                    "templow": min(data["temps"]), 
                    "condition": self._map_condition(dominant_condition.lower()), 
                    "precipitation": sum(data["precip"])
                }
                final_forecast_list.append(forecast_day)
            return final_forecast_list
        except Exception as e:
            LOGGER.warning(f"Failed to process daily forecast: {e}")
            return[]

    def _process_hourly_forecast(self, api_data):
        try:
            raw_hourly = api_data.get("forecast", {}).get("tabular", {}).get("time", [])
            if not raw_hourly: return []
            final_forecast_list =[]
            for hour in raw_hourly:
                try:
                    condition_text_et = hour.get("phenomen", {}).get("@attributes", {}).get("et", "")
                    forecast_hour = {
                        "datetime": hour.get("@attributes", {}).get("from"),
                        "temperature": float(hour.get("temperature", {}).get("@attributes", {}).get("value", 0)),
                        "condition": self._map_condition(condition_text_et.lower()),
                        "condition_text_et": condition_text_et.lower(),
                        "precipitation": float(hour.get("precipitation", {}).get("@attributes", {}).get("value", 0)),
                        "wind_speed": float(hour.get("windSpeed", {}).get("@attributes", {}).get("mps", 0)),
                        "wind_bearing": float(hour.get("windDirection", {}).get("@attributes", {}).get("deg", 0)),
                        "wind_bearing_name": hour.get("windDirection", {}).get("@attributes", {}).get("name", ""),
                        "pressure": float(hour.get("pressure", {}).get("@attributes", {}).get("value", 0))
                    }
                    if forecast_hour["datetime"]:
                        final_forecast_list.append(forecast_hour)
                except Exception: continue
            return final_forecast_list
        except Exception as e:
            LOGGER.warning(f"Failed to process hourly forecast: {e}")
            return[]

    def _process_sunshine_forecast(self, hourly_forecast: list) -> dict:
        sunshine_map = {"selge": 60, "vähene pilvisus": 45, "pilves selgimistega": 30, "vahelduv pilvisus": 30}
        daily_sunshine_minutes = defaultdict(int)
        for hour in hourly_forecast:
            try:
                timestamp = dt_util.as_local(datetime.fromisoformat(hour["datetime"]))
                if is_up(self.hass, timestamp):
                    condition = hour.get("condition_text_et", "")
                    sun_minutes = sunshine_map.get(condition, 0)
                    if sun_minutes > 0: daily_sunshine_minutes[timestamp.date()] += sun_minutes
            except (ValueError, KeyError): continue
            
        today = dt_util.now().date()
        return {
            "today": round(daily_sunshine_minutes.get(today, 0) / 60, 1),
            "tomorrow": round(daily_sunshine_minutes.get(today + timedelta(days=1), 0) / 60, 1),
            "day_2": round(daily_sunshine_minutes.get(today + timedelta(days=2), 0) / 60, 1),
            "day_3": round(daily_sunshine_minutes.get(today + timedelta(days=3), 0) / 60, 1),
        }

    def _process_precipitation_forecast(self, hourly_forecast: list) -> dict:
        daily_precipitation_mm = defaultdict(float)
        for hour in hourly_forecast:
            try:
                timestamp = dt_util.as_local(datetime.fromisoformat(hour["datetime"]))
                precipitation = hour.get("precipitation", 0.0)
                daily_precipitation_mm[timestamp.date()] += precipitation
            except (ValueError, KeyError): continue
            
        today = dt_util.now().date()
        return {
            "today": round(daily_precipitation_mm.get(today, 0.0), 1),
            "tomorrow": round(daily_precipitation_mm.get(today + timedelta(days=1), 0.0), 1),
            "day_2": round(daily_precipitation_mm.get(today + timedelta(days=2), 0.0), 1),
            "day_3": round(daily_precipitation_mm.get(today + timedelta(days=3), 0.0), 1),
        }

    def _process_warnings(self, api_data):
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
        except Exception: 
            return []
        
    def _map_condition(self, condition_text):
        """Map Estonian/English phenomenon string from XML/Forecast to HA condition."""
        if not condition_text: return "cloudy"
        c = condition_text.lower()
        if any(x in c for x in ["selge", "clear"]): return "clear"
        if any(x in c for x in ["vähene", "vahelduv", "few", "variable", "spells"]): return "partlycloudy"
        if any(x in c for x in ["pilves", "cloudy", "overcast"]): return "cloudy"
        if any(x in c for x in ["lörts", "sleet", "jäide", "glaze"]): return "snowy-rainy"
        if any(x in c for x in ["lumi", "snow"]): return "snowy"
        if any(x in c for x in ["vihm", "rain", "shower"]): return "rainy"
        if any(x in c for x in ["äike", "thunder", "hail", "rahe"]): return "lightning-rainy"
        if any(x in c for x in ["udu", "fog", "mist"]): return "fog"
        return "cloudy"
