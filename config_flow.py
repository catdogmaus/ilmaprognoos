# In /custom_components/ilmaprognoos/config_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
import logging

from .const import (
    DOMAIN,
    LOCATIONS,
    MANUAL_LOCATION_ID,
    LOGGER,
    DEFAULT_CURRENT_INTERVAL,
    DEFAULT_FORECAST_INTERVAL,
    CONF_WARNING_OVERRIDE,
    DEFAULT_WARNING_OVERRIDE,
    FORECAST_ONLY_STATION_ID,
)
from homeassistant.util import slugify

_LOGGER = logging.getLogger(__name__)


class IlmaprognoosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the main config flow for Ilmaprognoos."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self.manual_data = {}

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        # --- THIS IS THE FIX ---
        # Call the handler with NO arguments, as required.
        return IlmaprognoosOptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        
        options = list(LOCATIONS.keys())
        options.append("Sisestan asukoha käsitsi")
        schema = vol.Schema({vol.Required("location"): selector.SelectSelector(selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN))})

        if user_input is not None:
            selection = user_input["location"]
            if selection == "Sisestan asukoha käsitsi":
                return await self.async_step_manual_name()
            else:
                final_data = {"location": selection, "slug": slugify(selection)}
                return self.async_create_entry(title=selection, data=final_data)

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_manual_name(self, user_input=None):
        if user_input is not None:
            self.manual_data["name"] = user_input["name"]
            return await self.async_step_manual_coords()
        return self.async_show_form(step_id="manual_name", data_schema=vol.Schema({vol.Required("name"): selector.TextSelector()}))

    async def async_step_manual_coords(self, user_input=None):
        if user_input is not None:
            self.manual_data["coords"] = user_input["coords"]
            return await self.async_step_manual_ticker()
        return self.async_show_form(step_id="manual_coords", data_schema=vol.Schema({vol.Required("coords"): selector.TextSelector()}))

    async def async_step_manual_ticker(self, user_input=None):
        if user_input is not None:
            station_id_float = user_input["station_id"]
            station_id_int = int(station_id_float)
            station_id_str = str(station_id_int)
            
            title = self.manual_data["name"]
            
            final_data = {
                "location": MANUAL_LOCATION_ID,
                "name": self.manual_data["name"],
                "coords": self.manual_data["coords"],
                "station_id": station_id_str,
                "slug": slugify(title)
            }
            
            _LOGGER.debug(f"[config_flow] Creating manual entry: {final_data}")
            return self.async_create_entry(title=title, data=final_data)

        return self.async_show_form(step_id="manual_ticker", data_schema=vol.Schema({vol.Required("station_id"): selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=999, mode=selector.NumberSelectorMode.BOX))}))


class IlmaprognoosOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Ilmaprognoos."""

    # There is no __init__ method here, as correctly determined before.
    # It receives no arguments when created.

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        is_forecast_only = False
        if self.config_entry.data.get("location") == MANUAL_LOCATION_ID:
            if self.config_entry.data.get("station_id") == FORECAST_ONLY_STATION_ID:
                is_forecast_only = True

        forecast_interval = self.config_entry.options.get("forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60)
        warning_override = self.config_entry.options.get(CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE)
        schema_fields = {}

        if not is_forecast_only:
            current_interval = self.config_entry.options.get("current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60)
            schema_fields[vol.Required("current_interval", default=current_interval)] = selector.NumberSelector(selector.NumberSelectorConfig(min=5, max=1440, step=1, unit_of_measurement="minutes"))

        schema_fields[vol.Required("forecast_interval", default=forecast_interval)] = selector.NumberSelector(selector.NumberSelectorConfig(min=15, max=1440, step=1, unit_of_measurement="minutes"))
        schema_fields[vol.Required(CONF_WARNING_OVERRIDE, default=warning_override)] = selector.BooleanSelector()
        
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_fields))