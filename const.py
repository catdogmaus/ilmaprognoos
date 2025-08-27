# In /custom_components/ilmateenistus/const.py

import logging
from datetime import timedelta

DOMAIN = "ilmateenistus"
LOGGER = logging.getLogger(__package__)

DEFAULT_CURRENT_INTERVAL = timedelta(minutes=15)
DEFAULT_FORECAST_INTERVAL = timedelta(minutes=30)

# --- NEW: A constant for the manual entry option in the dropdown ---
MANUAL_LOCATION_ID = "manual"

LOCATIONS = {
    "Tallinn": {"station_id": "14", "coords": "59.432438;24.744066"},
    "Tartu": {"station_id": "15", "coords": "58.380052;26.722116"},
    "Pärnu": {"station_id": "30", "coords": "58.382515;24.510179"},
    "Haapsalu": {"station_id": "1", "coords": "58.942082;23.540145"},
    "Narva": {"station_id": "8", "coords": "59.375786;28.196300"},
    "Kihnu": {"station_id": "4", "coords": "58.132441;23.982262"},
    "Ruhnu": {"station_id": "12", "coords": "57.806423;23.243857"},
    "Valga": {"station_id": "18", "coords": "57.776678;26.030958"},
    "Viljandi": {"station_id": "19", "coords": "58.362936;25.601667"},
    "Võru": {"station_id": "22", "coords": "57.8474053323272;26.9964042844775"},
}

TICKER_URL_FORMAT = "https://www.ilmateenistus.ee/ilma_andmed/ticker/vaatlused-html.php?jaam={station_id}&stiil=1"
FORECAST_URL_FORMAT = "https://www.ilmateenistus.ee/wp-content/themes/ilm2020/meteogram.php/?coordinates={coords}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Language": "en-US,en;q=0.9,et;q=0.8",
    "Referer": "https://www.ilmateenistus.ee/",
}