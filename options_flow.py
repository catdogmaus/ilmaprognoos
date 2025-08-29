# In /custom_components/ilmaprognoos/options_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DEFAULT_CURRENT_INTERVAL,
    DEFAULT_FORECAST_INTERVAL,
    CONF_WARNING_OVERRIDE,
    DEFAULT_WARNING_OVERRIDE,
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

        # Get current values for all options to pre-fill the form
        current_interval = self.config_entry.options.get(
            "current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60
        )
        forecast_interval = self.config_entry.options.get(
            "forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60
        )
        warning_override = self.config_entry.options.get(
            CONF_WARNING_OVERRIDE, DEFAULT_WARNING_OVERRIDE
        )

        # Add the new boolean selector to the schema
        schema = vol.Schema({
            vol.Required(
                "current_interval", default=current_interval
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=5, max=1440, step=1, unit_of_measurement="minutes")
            ),
            vol.Required(
                "forecast_interval", default=forecast_interval
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=15, max=1440, step=1, unit_of_measurement="minutes")
            ),
            vol.Required(
                CONF_WARNING_OVERRIDE, default=warning_override
            ): selector.BooleanSelector(),
        })

        return self.async_show_form(step_id="init", data_schema=schema)