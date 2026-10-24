"""Next-departure sensor; its attributes feed the Lovelace card."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_STOP_ID, CONF_STOP_NAME, DOMAIN
from .coordinator import DpmkCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities([NextDepartureSensor(hass.data[DOMAIN][entry.entry_id])])


class NextDepartureSensor(CoordinatorEntity[DpmkCoordinator], SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:bus-clock"
    _attr_has_entity_name = True
    _attr_translation_key = "next_departure"

    def __init__(self, coordinator: DpmkCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_unique_id = f"{entry.data[CONF_STOP_ID]}_next_departure"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data[CONF_STOP_ID])},
            name=entry.data[CONF_STOP_NAME],
            manufacturer="DPMK Košice",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> datetime | None:
        deps = self.coordinator.data["departures"]
        return datetime.fromisoformat(deps[0]["expected"]) if deps else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        lat, lng, _ = self.coordinator.location
        return {
            "latitude": lat,
            "longitude": lng,
            "stop_name": self.coordinator.entry.data[CONF_STOP_NAME],
            "departures": data["departures"],
            "vehicles": [
                {
                    k: v[k]
                    for k in (
                        "line", "type", "bg", "fg", "movement", "distance", "dx", "dy", "eta", "serves"
                    )
                }
                | {"id": v["id"], "delay_min": round(v["delay"] / 60)}
                for v in data["vehicles"]
            ],
            "radius": data["radius"],
            "lines": data["lines"],
            "live_vehicles": data["live_vehicles"],
        }
