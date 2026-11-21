"""Košice Public Transport – DPMK: departures at a chosen stop or place, with live delays."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from .api import DpmkApi
from .const import CARD_URL, DOMAIN
from .coordinator import DpmkCoordinator, LiveFeed, cache_store
from .stops import load_catalog

PLATFORMS = ["sensor"]
_LOGGER = logging.getLogger(__name__)


def _card_version(card: Path) -> str:
    """Cache-busting token: the version from manifest.json plus a hash of the card file.

    The version lives only in manifest.json; the hash makes the URL change whenever the file
    does, so a browser can never keep an old copy of the card after an update.
    """
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))
    return f"{manifest['version']}-{hashlib.sha1(card.read_bytes()).hexdigest()[:8]}"


def _resources(hass: HomeAssistant):
    """The dashboard resources, when they are stored (not defined in YAML); otherwise None."""
    lovelace = hass.data.get("lovelace")
    resources = lovelace.get("resources") if isinstance(lovelace, dict) else getattr(lovelace, "resources", None)
    return resources if hasattr(resources, "async_create_item") else None


async def _ensure_resource(hass: HomeAssistant, url: str) -> None:
    """Keep the card in the dashboard resources.

    The frontend loads these before it draws any card, so the card is known even when a page is
    opened right after a restart, before this integration has started. Without it the card relies
    on the extra module URL alone, which a page built too early does not contain.
    """
    try:
        resources = _resources(hass)
        if resources is None:
            return
        if not getattr(resources, "loaded", True):
            await resources.async_load()
        wanted = {"res_type": "module", "url": url}
        for item in resources.async_items():
            if item["url"].split("?")[0] == CARD_URL:
                if item["url"] != url or item.get("res_type") != "module":
                    await resources.async_update_item(item["id"], wanted)
                return
        await resources.async_create_item(wanted)
    except Exception as err:  # the extra module URL still loads the card
        _LOGGER.debug("Could not add the card to the dashboard resources: %s", err)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the Lovelace card and load it on every dashboard."""
    card = Path(__file__).parent / "www" / "dpmk-departures-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(card), False)])
    url = f"{CARD_URL}?v={await hass.async_add_executor_job(_card_version, card)}"
    add_extra_js_url(hass, url)

    async def add_resource(_hass: HomeAssistant) -> None:
        await _ensure_resource(hass, url)

    async_at_started(hass, add_resource)  # the dashboards are up by then
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = hass.data.setdefault(DOMAIN, {})
    if "live" not in store:
        store["live"] = LiveFeed(DpmkApi(async_get_clientsession(hass)))
    if "catalog" not in store:  # the bundled stop list: a local file, read once
        store["catalog"] = await hass.async_add_executor_job(load_catalog)
    coordinator = DpmkCoordinator(hass, entry, store["live"], store["catalog"])
    await coordinator.async_config_entry_first_refresh()
    store[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_reload))
    return True


async def _reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the saved timetables of a removed entry, and the card resource with the last one."""
    await cache_store(hass, entry.entry_id).async_remove()
    if any(e.entry_id != entry.entry_id for e in hass.config_entries.async_entries(DOMAIN)):
        return
    try:
        resources = _resources(hass)
        if resources is not None and hasattr(resources, "async_delete_item"):
            for item in list(resources.async_items()):
                if item["url"].split("?")[0] == CARD_URL:
                    await resources.async_delete_item(item["id"])
    except Exception as err:  # a leftover resource is harmless
        _LOGGER.debug("Could not remove the card from the dashboard resources: %s", err)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
