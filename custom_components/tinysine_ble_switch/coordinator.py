import asyncio
from bleak import BleakClient
from bleak.exc import BleakError
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
import logging

_LOGGER = logging.getLogger(__name__)

CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
CMD_VERSION = b"\x5A"
CMD_STATE = b"\x5B"
CMD_ON = b"\x65"
CMD_OFF = b"\x6F"
CMD_VOLTAGE = b"\x92"

class BtBeeCoordinator:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.data = {"switch": False, "voltage": 0.0, "version": "unknown"}
        self._callbacks = set()
        self._available = False
        self._lock = asyncio.Lock()  # Prevent concurrent connections

    @property
    def available(self) -> bool:
        """Return if the device is available."""
        return self._available

    async def _connect_and_execute(self, command: bytes, key: str = None):
        """Connect, execute command, and disconnect."""
        async with self._lock:
            client = None
            try:
                _LOGGER.debug("Connecting to %s for command", self.entry.unique_id)
                client = BleakClient(self.entry.unique_id)
                await client.connect(timeout=10.0)
                
                if key:  # For read commands
                    await client.start_notify(CHAR_UUID, self._data_characteristic_callback)
                    await client.write_gatt_char(CHAR_UUID, command)
                    await asyncio.sleep(0.1)  # Give time for notification
                else:  # For write-only commands (switch)
                    await client.write_gatt_char(CHAR_UUID, command)
                
                self._available = True
                _LOGGER.debug("Command executed successfully for %s", self.entry.unique_id)
                
            except BleakError as e:
                self._available = False
                _LOGGER.error("BLE connection error for %s: %s", self.entry.unique_id, e)
                raise
            except Exception as e:
                self._available = False
                _LOGGER.error("Unexpected error for %s: %s", self.entry.unique_id, e)
                raise
            finally:
                if client and client.is_connected:
                    await client.disconnect()
                    _LOGGER.debug("Disconnected from %s", self.entry.unique_id)

    async def async_connect(self):
        """Initial connection to update all values."""
        await self._update_all()

    async def _update_all(self):
        """Update all sensor values."""
        await self._connect_and_execute(CMD_STATE, "switch")
        await self._connect_and_execute(CMD_VOLTAGE, "voltage")
        await self._connect_and_execute(CMD_VERSION, "version")
        for cb in self._callbacks:
            cb()

    def _data_characteristic_callback(self, sender, data):
        """Handle notification data."""
        try:
            if data.startswith(b"ST"):
                self.data["switch"] = bool(int(data[2:]))
            elif data.startswith(b"VO"):
                self.data["voltage"] = float(data[2:]) / 100
            elif data.startswith(b"VE"):
                self.data["version"] = data[2:].decode("utf-8")
            
            self._available = True
            for callback in self._callbacks:
                callback()
        except Exception as e:
            _LOGGER.error("Error processing BLE callback: %s", e)
            self._available = False

    async def async_set_switch(self, state: bool):
        """Set switch state."""
        await self._connect_and_execute(CMD_ON if state else CMD_OFF)
        # Update state after command
        await self._connect_and_execute(CMD_STATE, "switch")
        for cb in self._callbacks:
            cb()

    @callback
    def add_callback(self, callback):
        """Add a callback for state updates."""
        self._callbacks.add(callback)

    @callback
    def remove_callback(self, callback):
        """Remove a callback."""
        self._callbacks.discard(callback)

    async def async_stop(self):
        """Stop the coordinator."""
        pass  # No persistent connection to cleanup