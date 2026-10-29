"""Next-departure sensor; its attributes feed the Lovelace card."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_STOP_ID, DOMAIN
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
    # These change on every refresh and are large: stored, they would add ~20-30 MB a day per sensor
    # to the Home Assistant database. The state itself (the next departure) is still recorded.
    _unrecorded_attributes = frozenset({"departures", "vehicles", "stops", "lines", "live_vehicles"})

    def __init__(self, coordinator: DpmkCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        # A single stop keeps the ids it always had; a place is identified by its config entry.
        key = entry.entry_id if coordinator.is_place else entry.data[CONF_STOP_ID]
        self._attr_unique_id = f"{key}_next_departure"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, key)},
            # "DPMK " in front gives every sensor the id sensor.dpmk_<name>_next_departure
            name=f"DPMK {coordinator.display_name}",
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
            "stop_name": data["name"],
            "stops": data["stops"],
            "multi_stop": data["multi_stop"],
            "is_default": data["is_default"],
            "departures": data["departures"],
            "vehicles": [
                {
                    k: v[k]
                    for k in (
                        "line", "type", "bg", "fg", "movement", "distance", "dx", "dy", "eta", "serves", "stop"
                    )
                }
                | {"id": v["id"], "delay_min": round(v["delay"] / 60)}
                for v in data["vehicles"]
            ],
            "radius": data["radius"],
            "language": data["language"],
            "lines": data["lines"],
            "live_vehicles": data["live_vehicles"],
        }
