"""Košice Public Transport – DPMK: departures at a chosen stop or place, with live delays."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import voluptuous as vol
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .api import DpmkApi
from .const import CARD_URL, CONF_ROUTE_FROM, DEFAULT_WALK_M, DOMAIN, MAX_WALK_M
from .coordinator import DpmkCoordinator, LiveFeed, cache_store
from .route_entry import RouteCoordinator
from .routing import Router, RoutingError
from .stops import load_catalog

PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)


def _resources(hass: HomeAssistant):
    """The dashboard resources, when they are stored (not defined in YAML); otherwise None."""
    lovelace = hass.data.get("lovelace")
    resources = lovelace.get("resources") if isinstance(lovelace, dict) else getattr(lovelace, "resources", None)
    return resources if hasattr(resources, "async_create_item") else None


async def _remove_resources(hass: HomeAssistant) -> None:
    """Remove the card from the dashboard resources.

    Versions 0.4.0 to 0.4.2 wrote it there; the card is loaded through the extra module URL only
    (as in 0.3.x), so a leftover entry would load the same file a second time.
    """
    try:
        resources = _resources(hass)
        if resources is None or not hasattr(resources, "async_delete_item"):
            return
        if not getattr(resources, "loaded", True):
            await resources.async_get_info()  # loads the stored list, as the frontend does
        for item in list(resources.async_items()):
            if item["url"].split("?")[0] == CARD_URL:
                await resources.async_delete_item(item["id"])
    except Exception as err:  # a leftover resource is harmless
        _LOGGER.debug("Could not remove the card from the dashboard resources: %s", err)


class CardView(HomeAssistantView):
    """Serves the card file so that the browser asks again every time (ETag, no stale copy).

    The address never changes, so a refreshed page loads a new card after an update without a
    restart of Home Assistant. Unchanged files answer 304 and cost almost nothing.
    """

    url = CARD_URL
    name = "dpmk:card"
    requires_auth = False  # a script tag cannot send the login token

    def __init__(self, path: Path) -> None:
        self._path = path

    async def get(self, request: web.Request) -> web.Response:
        data = await request.app["hass"].async_add_executor_job(self._path.read_bytes)
        headers = {"Cache-Control": "no-cache", "ETag": f'"{hashlib.sha1(data).hexdigest()[:16]}"'}
        if request.headers.get("If-None-Match") == headers["ETag"]:
            return web.Response(status=304, headers=headers)
        return web.Response(body=data, content_type="text/javascript", charset="utf-8", headers=headers)


async def _warm_network(hass: HomeAssistant) -> None:
    try:
        await hass.data[DOMAIN]["router"].network()
    except Exception as err:  # the first search tries again
        _LOGGER.debug("Could not prepare the line network: %s", err)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the Lovelace card and load it on every dashboard."""
    card = Path(__file__).parent / "www" / "dpmk-departures-card.js"
    hass.http.register_view(CardView(card))
    add_extra_js_url(hass, CARD_URL)

    async def started(_hass: HomeAssistant) -> None:
        await _remove_resources(hass)
        # build the line network now, so the first route search does not wait for it
        hass.async_create_background_task(_warm_network(hass), f"{DOMAIN} line network")

    async_at_started(hass, started)  # the dashboards are up by then

    # the shared pieces, also used by the route card (which works without a configured stop)
    store = hass.data.setdefault(DOMAIN, {})
    if "live" not in store:
        store["live"] = LiveFeed(DpmkApi(async_get_clientsession(hass)))
    if "catalog" not in store:
        store["catalog"] = await hass.async_add_executor_job(load_catalog)
    store["router"] = Router(hass, store["live"], store["catalog"])
    websocket_api.async_register_command(hass, ws_plan_route)
    websocket_api.async_register_command(hass, ws_stops)
    return True


@websocket_api.websocket_command(
    {
        vol.Required("type"): "dpmk/plan_route",
        vol.Required("from"): str,
        vol.Required("to"): str,
        vol.Optional("mode", default="now"): vol.In(["now", "depart", "arrive"]),
        vol.Optional("time"): str,
        vol.Optional("limit", default=4): vol.All(int, vol.Range(min=1, max=8)),
        vol.Optional("walk", default=DEFAULT_WALK_M): vol.All(int, vol.Range(min=0, max=MAX_WALK_M)),
    }
)
@websocket_api.async_response
async def ws_plan_route(hass: HomeAssistant, connection, msg: dict) -> None:
    """The next connections between two stops, for the route card."""
    try:
        result = await hass.data[DOMAIN]["router"].plan(
            msg["from"], msg["to"], msg["mode"], msg.get("time"), msg["limit"], msg.get("walk", DEFAULT_WALK_M)
        )
    except RoutingError as err:
        connection.send_error(msg["id"], err.code, err.code)
        return
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "dpmk/stops"})
@callback
def ws_stops(hass: HomeAssistant, connection, msg: dict) -> None:
    """Every stop, for the pick lists of the route card and its editor."""
    connection.send_result(msg["id"], {"stops": hass.data[DOMAIN]["router"].stop_list()})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = hass.data.setdefault(DOMAIN, {})
    if "live" not in store:
        store["live"] = LiveFeed(DpmkApi(async_get_clientsession(hass)))
    if "catalog" not in store:  # the bundled stop list: a local file, read once
        store["catalog"] = await hass.async_add_executor_job(load_catalog)
    if CONF_ROUTE_FROM in entry.data:  # a saved route: from one stop to another
        coordinator = RouteCoordinator(hass, entry, store["router"])
    else:
        coordinator = DpmkCoordinator(hass, entry, store["live"], store["catalog"])
    await coordinator.async_config_entry_first_refresh()
    store[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the saved timetables of a removed entry."""
    await cache_store(hass, entry.entry_id).async_remove()
    if any(e.entry_id != entry.entry_id for e in hass.config_entries.async_entries(DOMAIN)):
        return
    await _remove_resources(hass)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
