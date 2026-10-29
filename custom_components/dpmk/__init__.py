"""Košice Public Transport – DPMK: departures at a chosen stop or place, with live delays."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import DpmkApi
from .const import CARD_URL, DOMAIN
from .coordinator import DpmkCoordinator, LiveFeed, cache_store
from .stops import load_catalog

PLATFORMS = ["sensor"]


def _card_version(card: Path) -> str:
    """Cache-busting token: the version from manifest.json plus a hash of the card file.

    The version lives only in manifest.json; the hash makes the URL change whenever the file
    does, so a browser can never keep an old copy of the card after an update.
    """
    manifest = json.loads((Path(__file__).parent / "manifest.json").read_text(encoding="utf-8"))
    return f"{manifest['version']}-{hashlib.sha1(card.read_bytes()).hexdigest()[:8]}"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the Lovelace card and load it on every dashboard."""
    card = Path(__file__).parent / "www" / "dpmk-departures-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(card), False)])
    add_extra_js_url(hass, f"{CARD_URL}?v={await hass.async_add_executor_job(_card_version, card)}")
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
    """Delete the saved timetables of a removed entry."""
    await cache_store(hass, entry.entry_id).async_remove()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
