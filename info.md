## About This Integration
[![GitHub](https://img.shields.io/github/license/catdogmaus/ha-estweather?color=green)](https://github.com/catdogmaus/ha-estweather/blob/main/LICENSE)  
**Ilmateenistus** allows you to monitor your Estonian local weather in Home Assistant.
This integration uses available open data but is not in any way related to official Keskkonnaagentuur or ilmateenistus.ee services.

**Key Features:**

*   Current weather
*   Daily and Hourly forecast
*   Weather warnings

### Installation

1. Add this repository as a custom repository in HACS.
2. Install the integration from HACS → Integrations.
3. Restart Home Assistant. (This is crucial for Home Assistant to recognize the new integration).
4. Add via Settings → Devices & Services. 

### Configuration

This integration uses the config flow UI. No YAML required.
In Devices clik `add integration`, search for Ilmateenistus and follow config flow.

**Having Issues?**

If the integration does not show up:
- Check logs for errors 
- Ensure the integration is installed in `custom_components/ilmateenistus`
- Make sure you restarted HA after integration installation thru HACS

---

For more details, visit the [GitHub repository](https://github.com/catdogmaus/ha-estweather).
