"""Sensor platform for phicomm_aircat (悟空 M1)."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    server = hass.data[DOMAIN][entry.entry_id]
    entities = [
        AirCatSensor(server, "temperature", "温度", "°C",
                     SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
        AirCatSensor(server, "humidity", "湿度", "%",
                     SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT),
        AirCatSensor(server, "pm25", "PM2.5", "µg/m³", None, SensorStateClass.MEASUREMENT),
        AirCatSensor(server, "hcho", "甲醛", "µg/m³", None, SensorStateClass.MEASUREMENT),
    ]
    server.entities = entities
    async_add_entities(entities)


class AirCatSensor(SensorEntity):
    """Single value sensor fed by AirCatServer data dict."""

    _attr_has_entity_name = True

    def __init__(self, server, key, name, unit, device_class, state_class):
        self._server = server
        self._key = key
        self._attr_name = name
        self._attr_unique_id = f"phicomm_m1_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "phicomm_m1")},
            "name": "斐讯悟空 M1 空气检测器",
            "manufacturer": "斐讯 Phicomm",
            "model": "悟空 M1 (AirCat)",
        }

    @property
    def native_value(self):
        return self._server.data.get(self._key)
