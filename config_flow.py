# In /custom_components/ilmaprognoos/config_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
import logging

from .const import DOMAIN, LOCATIONS, MANUAL_LOCATION_ID, LOGGER
from .options_flow import IlmaprognoosOptionsFlowHandler

_LOGGER = logging.getLogger(__name__)

class IlmaprognoosConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ilmaprognoos."""

    VERSION = 1
    
    def __init__(self):
        """Initialize the config flow."""
        self.manual_data = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step where the user chooses a location type."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        
        options = list(LOCATIONS.keys())
        options.append("Sisestan asukoha käsitsi")
        
        schema = vol.Schema({
            vol.Required("location"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options, mode=selector.SelectSelectorMode.DROPDOWN)
            )
        })

        if user_input is not None:
            if user_input["location"] == "Sisestan asukoha käsitsi":
                return await self.async_step_manual_name()
            else:
                return self.async_create_entry(title=user_input["location"], data={"location": user_input["location"]})

        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_manual_name(self, user_input=None):
        """Handle the step for entering a manual location name."""
        if user_input is not None:
            self.manual_data["name"] = user_input["name"]
            return await self.async_step_manual_coords()
            
        return self.async_show_form(
            step_id="manual_name", 
            data_schema=vol.Schema({
                vol.Required("name"): selector.TextSelector()
            })
        )

    async def async_step_manual_coords(self, user_input=None):
        """Handle the step for entering forecast coordinates."""
        if user_input is not None:
            self.manual_data["coords"] = user_input["coords"]
            return await self.async_step_manual_ticker()
            
        return self.async_show_form(
            step_id="manual_coords", 
            data_schema=vol.Schema({
                vol.Required("coords"): selector.TextSelector()
            })
        )

    async def async_step_manual_ticker(self, user_input=None):
        """Handle the step for entering the ticker station ID."""
        if user_input is not None:
            station_id_float = user_input["station_id"]
            station_id_int = int(station_id_float)
            station_id_str = str(station_id_int)
            
            title = self.manual_data["name"]
            final_data = {
                "location": MANUAL_LOCATION_ID,
                "name": self.manual_data["name"],
                "coords": self.manual_data["coords"],
                "station_id": station_id_str
            }
            
            _LOGGER.debug(f"[config_flow] Creating manual entry with final_data: {final_data}")
            
            return self.async_create_entry(title=title, data=final_data)

        return self.async_show_form(
            step_id="manual_ticker", 
            data_schema=vol.Schema({
                vol.Required("station_id"): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=999, mode=selector.NumberSelectorMode.BOX)
                )
            })
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return IlmaprognoosOptionsFlowHandler(config_entry)