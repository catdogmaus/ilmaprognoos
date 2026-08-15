# In /custom_components/ilmaprognoos/const.py

import logging
from datetime import timedelta

DOMAIN = "ilmaprognoos"
LOGGER = logging.getLogger(__package__)

DEFAULT_CURRENT_INTERVAL = timedelta(minutes=15)
DEFAULT_FORECAST_INTERVAL = timedelta(minutes=30)

CONF_WARNING_OVERRIDE = "warning_override"
DEFAULT_WARNING_OVERRIDE = True

# --- NEW: Warning Level Constants ---
CONF_WARNING_LEVELS = "warning_levels"
DEFAULT_WARNING_LEVELS = ["1", "2", "3"]

XML_OBSERVATIONS_URL = "https://www.ilmateenistus.ee/ilma_andmed/xml/observations.php"
FORECAST_URL_FORMAT = "https://www.ilmateenistus.ee/wp-content/themes/ilm2020/meteogram.php/?coordinates={coords}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    "Accept": "application/xml, text/xml, application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9,et;q=0.8",
}

FORECAST_ONLY_ID = "Ainult prognoos"
NO_SECONDARY_ID = "Puudub"
