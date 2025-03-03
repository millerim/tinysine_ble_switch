from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_MAC
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up BLE Switch from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # Store only config, we'll create clients on-demand
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, ["switch", "sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    await hass.config_entries.async_unload_platforms(entry, ["switch", "sensor"])
    del hass.data[DOMAIN][entry.entry_id]
    if not hass.data[DOMAIN]:
        del hass.data[DOMAIN]
    return True