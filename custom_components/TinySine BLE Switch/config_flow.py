import asyncio
from bleak import BleakScanner
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_MAC
from .const import DOMAIN

class TinySineBLESwitchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BLE Switch."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            # Validate the selected device
            await self.async_set_unique_id(user_input[CONF_MAC])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_MAC: user_input[CONF_MAC]
                }
            )

        # Scan for BLE devices
        devices = await self._discover_tinysine_ble_devices()
        
        if not devices:
            return self.async_show_form(
                step_id="user",
                errors={"base": "no_devices_found"}
            )

        # Create options for discovered devices
        device_options = {
            device.address: f"{device.name} ({device.address})"
            for device in devices
        }

        data_schema = vol.Schema({
            vol.Required(CONF_MAC): vol.In(device_options),
            vol.Optional(CONF_NAME): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def _discover_tinysine_ble_devices(self):
        """Discover TinySine BLE devices advertising with BT Bee*."""
        devices = await BleakScanner.discover(timeout=5.0)
        return [device for device in devices if device.name and "BT Bee" in device.name]