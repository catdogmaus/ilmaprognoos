# In /custom_components/ilmateenistus/options_flow.py

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import DEFAULT_CURRENT_INTERVAL, DEFAULT_FORECAST_INTERVAL

class IlmateenistusOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Ilmateenistus."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            "current_interval", DEFAULT_CURRENT_INTERVAL.seconds // 60
        )
        forecast_interval = self.config_entry.options.get(
            "forecast_interval", DEFAULT_FORECAST_INTERVAL.seconds // 60
        )

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
        })

        return self.async_show_form(step_id="init", data_schema=schema)