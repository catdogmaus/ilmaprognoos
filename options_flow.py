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

    # --- THIS IS THE FIX ---
    # The __init__ method is restored to its correct and required form.
    # It MUST accept the config_entry to work correctly.
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        is_forecast_only = False
        if self.config_entry.data.get("location") == MANUAL_LOCATION_ID:
            if self.config_entry.data.get("station_id") == FORECAST_ONLY_STATION_ID:
                is_forecast_only = True

        forecast_interval = self.config_entry.options.get(
            "forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60
        )
        warning_override = self.config_entry.options.get(
            CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE
        )

        schema_fields = {}

        if not is_forecast_only:
            current_interval = self.config_entry.options.get(
                "current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60
            )
            schema_fields[vol.Required("current_interval", default=current_interval)] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=1440, step=1, unit_of_measurement="minutes")
            )

        schema_fields[vol.Required("forecast_interval", default=forecast_interval)] = selector.NumberSelector(
            selector.NumberSelectorConfig(min=15, max=1440, step=1, unit_of_measurement="minutes")
        )
        schema_fields[vol.Required(CONF_WARNING_OVERRIDE, default=warning_override)] = selector.BooleanSelector()
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields)
        )