# ha-estweather
Estonian weather forecast for Homeassistant

This is a weather forecast that is intended **only** for Estonian weather and will not work for any other country. This integration uses available open data but is not in any way related to official Keskkonnaagentuur or ilmateenistus.ee services.

Since sharing weather service forecast data with users in ilmateenistus is generally rubbish, it can only be guaranteed to work until things get even worse in terms of proper weather data sharing. 

## Installation via HACS

1. Go to HACS
2. Click the `⋮` button in corner
3. Add this repository as a **custom repository** (`https://github.com/catdogmaus/ha-estweather`)
4. Select "Integration"
5. Restart Home Assistant
6. Go **Devices and services** and click **Add Integration**. Search for **Ilmateenistus** and follow configuration flow.

## How it works
Key Features:

Current weather<br/>
Daily and Hourly forecast<br/>
Weather warnings<br/>

The integration creates also an additional weather warnings sensor, which is not currently supported by HA weather. Therefore, the logic of the Forecast frontend is such that if a weather warning for the region comes with the forecast, it overrides the regular forecast. The warning icons and information are visible as long as the warning exists in the initial weather service information. However, this does not affect the temperature, humidity, and overall forecast data. If you like to use more verbose warning data you can use warnings sensor together with conditional card in you dashboard. However this will not affect above described HA weather behavior.

## Problems 

As far as I know none!<br/>
Dont ask for more datapoints.   It is possible only to give data that is initially available.
