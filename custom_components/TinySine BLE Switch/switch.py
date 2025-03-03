import asyncio
from bleak import BleakClient
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the TinySine BLE Switch platform."""
    config = hass.data[DOMAIN][config_entry.entry_id]["config"]
    switch = TinySineBLESwitch(config["name"], config["mac"], config_entry.entry_id)
    async_add_entities([switch])

class TinySineBLESwitch(SwitchEntity):
    """Representation of a TinySine BLE Switch."""

    def __init__(self, name, mac_address, entry_id):
        """Initialize the switch."""
        self._name = name
        self._mac_address = mac_address
        self._entry_id = entry_id
        self._state = False
        self._attr_unique_id = f"{mac_address}_switch"

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def is_on(self):
        """Return true if switch is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        await self._send_command(b'\x65')
        self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        await self._send_command(b'\x6F')
        self._state = False
        self.async_write_ha_state()

    async def _send_command(self, command):
        """Send command to the BLE device and disconnect."""
        try:
            async with BleakClient(self._mac_address) as client:
                await client.connect()
                await client.write_gatt_char(CHARACTERISTIC_UUID, command)
                await client.disconnect()
        except Exception as e:
            _LOGGER.error(f"Error sending command to {self._mac_address}: {e}")