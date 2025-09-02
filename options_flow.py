# In /custom_components/ilmaprognoos/options_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DEFAULT_CURRENT_INTERVAL,
    DEFAULT_FORECAST_INTERVAL,
    CONF_WARNING_OVERRIDE,
    DEFAULT_WARNING_OVERRIDE,
    MANUAL_LOCATION_ID,
    FORECAST_ONLY_STATION_ID,
)

class IlmaprognoosOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Ilmaprognoos."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # --- THIS IS THE NEW DYNAMIC LOGIC ---
        # 1. Determine if this is a forecast-only setup
        is_forecast_only = False
        if self.config_entry.data.get("location") == MANUAL_LOCATION_ID:
            if self.config_entry.data.get("station_id") == FORECAST_ONLY_STATION_ID:
                is_forecast_only = True

        # 2. Get current values for all options to pre-fill the form
        forecast_interval = self.config_entry.options.get(
            "forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60
        )
        warning_override = self.config_entry.options.get(
            CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE
        )

        # 3. Build the form schema based on the setup mode
        schema_fields = {}

        if not is_forecast_only:
            # If we have a current weather source, add its interval option
            current_interval = self.config_entry.options.get(
                "current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60
            )
            schema_fields[vol.Required("current_interval", default=current_interval)] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=1440, step=1, unit_of_measurement="minutes")
            )

        # Add the options that are always present
        schema_fields[vol.Required("forecast_interval", default=forecast_interval)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=15, max=1440, step=1, unit_of_measurement="minutes")
        )
        schema_fields[vol.Required(CONF_WARNING_OVERRIDE, default=warning_override)] = selector.BooleanSelector()
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields)
        )