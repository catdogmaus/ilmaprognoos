# In /custom_components/ilmaprognoos/config_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
import logging
import math
import requests
import xml.etree.ElementTree as ET
from homeassistant.util import slugify

from .const import (
    DOMAIN, XML_OBSERVATIONS_URL, HEADERS, FORECAST_ONLY_ID, NO_SECONDARY_ID,
    DEFAULT_CURRENT_INTERVAL, DEFAULT_FORECAST_INTERVAL, CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE
)

_LOGGER = logging.getLogger(__name__)

def haversine(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on the earth."""
    R = 6371  # Radius of the earth in km
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dLon/2) * math.sin(dLon/2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

class IlmaprognoosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    
    def __init__(self):
        self.setup_data = {}
        self.top_stations = []

    @staticmethod
    def async_get_options_flow(config_entry):
        return IlmaprognoosOptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            if user_input["use_home"]:
                lat = self.hass.config.latitude
                lon = self.hass.config.longitude
                self.setup_data["coords"] = f"{lat};{lon}"
                return await self.async_step_name()
            else:
                return await self.async_step_coords()

        return self.async_show_form(
            step_id="user", 
            data_schema=vol.Schema({vol.Required("use_home", default=True): selector.BooleanSelector()})
        )

    async def async_step_coords(self, user_input=None):
        if user_input is not None:
            self.setup_data["coords"] = user_input["coords"]
            return await self.async_step_name()
        return self.async_show_form(step_id="coords", data_schema=vol.Schema({vol.Required("coords"): str}))

    async def async_step_name(self, user_input=None):
        if user_input is not None:
            self.setup_data["location_name"] = user_input["location_name"]
            
            try:
                lat_str, lon_str = self.setup_data["coords"].replace(',', '.').split(';')
                user_lat, user_lon = float(lat_str), float(lon_str)
                
                def fetch_xml():
                    res = requests.get(XML_OBSERVATIONS_URL, headers=HEADERS, timeout=15)
                    res.raise_for_status()
                    return res.text
                
                xml_text = await self.hass.async_add_executor_job(fetch_xml)
                root = ET.fromstring(xml_text)
                
                stations = []
                for station in root.findall('station'):
                    name = station.findtext('name')
                    s_lat_text = station.findtext('latitude')
                    s_lon_text = station.findtext('longitude')
                    
                    if name and s_lat_text and s_lon_text:
                        dist = haversine(user_lat, user_lon, float(s_lat_text), float(s_lon_text))
                        
                        # --- FIX 1: Calculate Data Richness ---
                        # Count how many data tags have actual text in them
                        data_count = sum(1 for child in station if child.text and child.text.strip() and child.tag not in ['name', 'latitude', 'longitude', 'wmocode'])
                        
                        stations.append({'name': name, 'dist': dist, 'data_count': data_count})
                
                # --- FIX 1: Sort by distance, take top 5, then rank by richness ---
                stations.sort(key=lambda x: x['dist'])
                top_5 = stations[:5]
                
                if top_5:
                    # max() keeps the first encountered item if there's a tie (meaning it prefers the closer one)
                    richest_station = max(top_5, key=lambda x: x['data_count'])
                    top_5.remove(richest_station)
                    top_5.insert(0, richest_station)
                
                self.top_stations = [s['name'] for s in top_5]
                
                return await self.async_step_primary_station()
            except Exception as e:
                _LOGGER.error(f"Failed to fetch or parse XML stations: {e}")
                return self.async_abort(reason="xml_fetch_failed")

        return self.async_show_form(step_id="name", data_schema=vol.Schema({vol.Required("location_name"): str}))

    async def async_step_primary_station(self, user_input=None):
        if user_input is not None:
            self.setup_data["primary_station"] = user_input["primary_station"]
            if self.setup_data["primary_station"] == FORECAST_ONLY_ID:
                self.setup_data["secondary_station"] = NO_SECONDARY_ID
                return self._create_final_entry()
            return await self.async_step_secondary_station()

        options = self.top_stations + [FORECAST_ONLY_ID]
        return self.async_show_form(
            step_id="primary_station",
            data_schema=vol.Schema({
                vol.Required("primary_station", default=options[0]): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
                )
            })
        )

    async def async_step_secondary_station(self, user_input=None):
        if user_input is not None:
            self.setup_data["secondary_station"] = user_input["secondary_station"]
            return self._create_final_entry()

        options = [s for s in self.top_stations if s != self.setup_data["primary_station"]]
        options.append(NO_SECONDARY_ID)
        
        return self.async_show_form(
            step_id="secondary_station",
            data_schema=vol.Schema({
                vol.Required("secondary_station", default=options[0]): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
                )
            })
        )

    def _create_final_entry(self):
        title = self.setup_data["location_name"]
        self.setup_data["slug"] = slugify(title)
        return self.async_create_entry(title=title, data=self.setup_data)


class IlmaprognoosOptionsFlowHandler(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        is_forecast_only = False
        if self.config_entry.data.get("primary_station") == FORECAST_ONLY_ID:
            is_forecast_only = True

        forecast_interval = self.config_entry.options.get("forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60)
        warning_override = self.config_entry.options.get(CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE)

        schema_fields = {}

        if not is_forecast_only:
            current_interval = self.config_entry.options.get("current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60)
            schema_fields[vol.Required("current_interval", default=current_interval)] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=30, step=1, unit_of_measurement="minutes")
            )

        schema_fields[vol.Required("forecast_interval", default=forecast_interval)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=15, max=90, step=1, unit_of_measurement="minutes")
        )
        schema_fields[vol.Required(CONF_WARNING_OVERRIDE, default=warning_override)] = selector.BooleanSelector()
        
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_fields))