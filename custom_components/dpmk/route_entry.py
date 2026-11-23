"""A saved route (from one stop to another): its coordinator and its sensor."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ROUTE_COUNT,
    CONF_ROUTE_FROM,
    CONF_ROUTE_TO,
    CONF_ROUTE_WALK,
    DEFAULT_ROUTE_COUNT,
    DEFAULT_WALK_M,
    DOMAIN,
    ROUTE_UPDATE_SECONDS,
)
from .routing import Router, RoutingError

_LOGGER = logging.getLogger(__name__)


class RouteCoordinator(DataUpdateCoordinator[dict]):
    """Looks up the next connections of one saved route, once a minute."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, router: Router) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(seconds=ROUTE_UPDATE_SECONDS),
        )
        self.entry = entry
        self.router = router

    @property
    def from_id(self) -> str:
        return str(self.entry.options.get(CONF_ROUTE_FROM) or self.entry.data[CONF_ROUTE_FROM])

    @property
    def to_id(self) -> str:
        return str(self.entry.options.get(CONF_ROUTE_TO) or self.entry.data[CONF_ROUTE_TO])

    @property
    def count(self) -> int:
        return int(self.entry.options.get(CONF_ROUTE_COUNT, DEFAULT_ROUTE_COUNT))

    @property
    def walk(self) -> int:
        """Metres one may walk to a nearby stop at the start and the end (0 = off)."""
        return int(self.entry.options.get(CONF_ROUTE_WALK, DEFAULT_WALK_M))

    async def _async_update_data(self) -> dict:
        try:
            return await self.router.plan(self.from_id, self.to_id, "now", None, self.count, self.walk)
        except RoutingError as err:
            raise UpdateFailed(f"No route search possible: {err.code}") from err
        except Exception as err:
            raise UpdateFailed(f"Route search failed: {err}") from err


def _expected(connection: dict, key: str) -> datetime:
    """A time of the connection, moved by the live delay of its first vehicle when there is one."""
    when = datetime.fromisoformat(connection[key])
    delay = connection["legs"][0].get("delay_min")
    return when + timedelta(minutes=delay) if delay else when


class RouteSensor(CoordinatorEntity[RouteCoordinator], SensorEntity):
    """When the next connection leaves; the connections themselves are attributes."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:routes-clock"
    _attr_has_entity_name = True
    _attr_translation_key = "next_connection"
    _unrecorded_attributes = frozenset({"connections"})  # large and changing: not for the database

    def __init__(self, coordinator: RouteCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.entry
        self._attr_unique_id = f"{entry.entry_id}_next_connection"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"DPMK {entry.title}",
            manufacturer="DPMK Košice",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def _first(self) -> dict | None:
        connections = (self.coordinator.data or {}).get("connections") or []
        return connections[0] if connections else None

    @property
    def native_value(self) -> datetime | None:
        first = self._first
        return _expected(first, "depart") if first else None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        first = self._first
        attrs = {
            "from": data.get("from"),
            "to": data.get("to"),
            "connections": data.get("connections", []),
        }
        if first:
            attrs |= {
                "scheduled_departure": first["depart"],
                "arrival": _expected(first, "arrive").isoformat(),
                "duration": first["minutes"],
                "changes": len(first["changes"]),
                "walk_start": first.get("walk_start"),
                "walk_end": first.get("walk_end"),
                "lines": [leg["line"] for leg in first["legs"]],
                "live": first["legs"][0]["live"],
                "delay_min": first["legs"][0]["delay_min"],
            }
        return attrs
