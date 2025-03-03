import asyncio
from bleak import BleakClient
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)
CHARACTERISTIC_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"
VOLTAGE_COMMAND = b'\x92'

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the TinySine BLE Voltage Sensor platform."""
    config = hass.data[DOMAIN][config_entry.entry_id]["config"]
    sensor = TinySineBLEVoltageSensor(config["name"], config["mac"], config_entry.entry_id)
    async_add_entities([sensor])
    # Schedule periodic voltage updates
    hass.async_create_task(sensor.async_update_voltage())

class TinySineBLEVoltageSensor(SensorEntity):
    """Representation of a BLE Voltage Sensor."""

    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "V"

    def __init__(self, name, mac_address, entry_id):
        """Initialize the sensor."""
        self._name = f"{name} Voltage"
        self._mac_address = mac_address
        self._entry_id = entry_id
        self._state = None
        self._attr_unique_id = f"{mac_address}_voltage"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._state

    async def data_characteristic_callback(self, sender, data):
        """Handle received BLE notification data."""
        if len(data) >= 2:
#            voltage = int.from_bytes(data[0:2], byteorder='little') / 100.0
            voltage = data.decode()
            self._state = voltage
            self.async_write_ha_state()

    async def async_update_voltage(self):
        """Periodically update voltage reading."""
        while True:
            try:
                async with BleakClient(self._mac_address) as client:
                    await client.connect()
                    await client.start_notify(CHARACTERISTIC_UUID, self.data_characteristic_callback)
                    await client.write_gatt_char(CHARACTERISTIC_UUID, VOLTAGE_COMMAND)
                    # Wait briefly for notification
                    await asyncio.sleep(1)
                    await client.disconnect()
            except Exception as e:
                _LOGGER.error(f"Error reading voltage from {self._mac_address}: {e}")
            
            # Wait before next reading (e.g., 60 seconds)
            await asyncio.sleep(60)