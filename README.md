# Home Assistant Ilmaprognoos (Estonian Weather Forecast) Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
<span class="badge-buymeacoffee">
<a href="https://ko-fi.com/catdog58928" title="Donate to this project using Ko-Fi"><img src="https://img.shields.io/badge/Buy_me_coffee_and_biscuits-donate-yellow.svg?logo=kofi" alt="Buy Me A Coffee donate button" /></a>
</span><br/> 
This is a custom integration for Home Assistant to provide detailed weather information and forecasts from the Estonian national weather service (ilmateenistus.ee). This weather forecast is intended **only** for Estonian weather and will not work for any other country.<br/> 
This integration uses available open data but **is not in any way related to official Keskkonnaagentuur or ilmateenistus.ee services.**

Since sharing weather service forecast data with users in ilmateenistus is generally rubbish, it can only be guaranteed to work until things get even worse in terms of proper weather data sharing. So don't keep your hopes too high with this.

## Installation

The easiest way to install this integration is with the [Home Assistant Community Store (HACS)](https://hacs.xyz/).

1. Go to HACS
2. Click the `⋮` button in corner
3. Add this repository as a **custom repository** `https://github.com/catdogmaus/ilmaprognoos`
4. Select "Integration"
5. Restart Home Assistant
6. Go **Devices and services** and click **Add Integration**. Search for **Ilmaprognoos** and follow configuration flow.

## How it works
Key Features:

Current weather<br/>
Daily and Hourly forecast<br/>
Weather warnings<br/>

The integration creates also an additional weather warnings sensor, which is not currently supported by HA weather. Therefore, the logic of the Forecast frontend is such that if a weather warning for the region comes with the forecast, it overrides the regular forecast. The warning icons and information are visible as long as the warning exists in the initial weather service information. This can get a bit annoying, especially if the warnings last for several days. However, this does not affect the temperature, humidity, and overall forecast data, and there is also option in the integration settings to turn off this behaviour. If you like to use more verbose warning data you can always use separate warnings sensor together with conditional card in you dashboard.<br/>

For some coastal areas, separate sensors for water level and water temperature will be created.<br/>

For those who use solar for heat or electricity "Hours of sunshine" sensors in forecast are created. This is **not** official data, but calculated based on an existing forecast. With "clear" and "cloudy" forecast everything is clear, but with "few clouds" and "partly cloudy" things get bit fuzzy. Therefore, it is inevitably an approximate calculation but still useful to get approximate forecast for upcoming solar energy production.

By default, the integration uses two different data sources, but with manual configuration it is possible to revert to only the main one. In that case however, you will lose some datapoints in the output.

## Problems 

As far as I know none!<br/>
Dont ask for more datapoints.   It is possible only to give data that is initially available.
