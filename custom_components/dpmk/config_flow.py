"""Config flow: add a stop from the bundled list, or a place made of several stops; options."""

from __future__ import annotations

from collections import Counter
from uuid import uuid4

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    LocationSelector,
    LocationSelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import DpmkApi
from .const import (
    CONF_AUTO_LOCATION,
    CONF_IS_DEFAULT,
    CONF_LANGUAGE,
    CONF_LOCATION,
    CONF_MAP_RADIUS,
    CONF_MAP_SCOPE,
    CONF_MAX_DEPARTURES,
    CONF_PLACE_LOCATION,
    CONF_PLACE_NAME,
    CONF_PLACE_RADIUS,
    CONF_ROUTES,
    CONF_SCHOOL_MODE,
    CONF_STOP_ID,
    CONF_STOP_IDS,
    CONF_STOP_NAME,
    CONF_STOP_NUMBER,
    CONF_UPDATE_INTERVAL,
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_DEPARTURES,
    DEFAULT_PLACE_RADIUS,
    DEFAULT_RADIUS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    LANG_AUTO,
    LANG_EN,
    LANG_SK,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    PLACE_CANDIDATE_RADIUS,
    SCHOOL_AUTO,
    SCHOOL_HOLIDAYS,
    SCHOOL_SCHOOL,
    SCOPE_ALL,
    SCOPE_SERVING,
)
from .stops import Catalog, StopInfo, load_catalog

PLACE_PRETICKED = 8  # a place preselects at most this many stops (the nearest ones)
PLACE_REACH = 800  # metres: stops this close are offered even when the radius is smaller


def format_distance(metres: float) -> str:
    return f"{round(metres, -1):.0f} m" if metres < 1000 else f"{metres / 1000:.1f} km"


def stop_options(
    catalog: Catalog, lat: float, lng: float, only: list[StopInfo] | None = None
) -> list[SelectOptionDict]:
    """Pick-list entries: nearest first when the position is in town, with the distance shown.

    The two stops that share a name also show their stop number.
    """
    ordered = catalog.sorted_for(lat, lng)
    if only is not None:
        keep = {s.stop_id for s in only}
        ordered = [item for item in ordered if item[0].stop_id in keep]
    counts = Counter(s.label for s, _ in ordered)
    options = []
    for stop, distance in ordered:
        label = f"{stop.label} (#{stop.stop_id})" if counts[stop.label] > 1 else stop.label
        if distance is not None and distance < 30_000:
            label = f"{label} · {format_distance(distance)}"
        options.append(SelectOptionDict(value=stop.stop_id, label=label))
    return options


class DpmkConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._catalog: Catalog | None = None
        self._place: dict = {}

    async def _load_catalog(self) -> Catalog:
        if self._catalog is None:  # a local file, read once
            self._catalog = await self.hass.async_add_executor_job(load_catalog)
        return self._catalog

    async def async_step_user(self, user_input=None):
        return self.async_show_menu(step_id="user", menu_options=["stop", "place"])

    # ---- one stop ----------------------------------------------------------------------------

    async def async_step_stop(self, user_input=None):
        catalog = await self._load_catalog()
        errors: dict[str, str] = {}
        if user_input is not None:
            number = str(user_input.get(CONF_STOP_NUMBER) or "").strip()
            stop_id = number or user_input.get(CONF_STOP_ID)
            name = None
            if not stop_id:
                errors["base"] = "choose_stop"
            elif (info := catalog.get(stop_id)) is not None:
                name = info.label
            else:  # a stop number that is not in the bundled list: ask dpmk.sk
                try:
                    stop = await DpmkApi(async_get_clientsession(self.hass)).get_stop(stop_id)
                except Exception:
                    errors["base"] = "cannot_connect"
                else:
                    if stop.routes:
                        name = stop.name
                    else:
                        errors["base"] = "unknown_stop"
            if not errors:
                await self.async_set_unique_id(stop_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name, data={CONF_STOP_ID: stop_id, CONF_STOP_NAME: name}
                )
        options = stop_options(catalog, self.hass.config.latitude, self.hass.config.longitude)
        schema = vol.Schema(
            {
                vol.Optional(CONF_STOP_ID): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                ),
                vol.Optional(CONF_STOP_NUMBER): str,
            }
        )
        return self.async_show_form(step_id="stop", data_schema=schema, errors=errors)

    # ---- a place: several stops near one spot --------------------------------------------------

    async def async_step_place(self, user_input=None):
        catalog = await self._load_catalog()
        errors: dict[str, str] = {}
        if user_input is not None:
            spot = user_input[CONF_LOCATION]
            radius = float(spot.get("radius") or DEFAULT_PLACE_RADIUS)
            # look further than the radius: the stops just outside it are offered too (unticked)
            found = catalog.near(spot["latitude"], spot["longitude"], max(radius * 2, PLACE_REACH))
            if found:
                self._place = {
                    "name": user_input[CONF_PLACE_NAME].strip() or "Place",
                    "lat": spot["latitude"],
                    "lng": spot["longitude"],
                    "radius": radius,
                    "found": found,
                }
                return await self.async_step_place_stops()
            errors["base"] = "no_stops_nearby"
        default_spot = {
            "latitude": self.hass.config.latitude,
            "longitude": self.hass.config.longitude,
            "radius": DEFAULT_PLACE_RADIUS,
        }
        schema = vol.Schema(
            {
                vol.Required(CONF_PLACE_NAME, default=self.hass.config.location_name or "Home"): str,
                vol.Required(CONF_LOCATION, default=default_spot): LocationSelector(
                    LocationSelectorConfig(radius=True)
                ),
            }
        )
        return self.async_show_form(step_id="place", data_schema=schema, errors=errors)

    async def async_step_place_stops(self, user_input=None):
        place = self._place
        found: list[tuple[StopInfo, float]] = place["found"]
        errors: dict[str, str] = {}
        inside = [s.stop_id for s, d in found if d <= place["radius"]][:PLACE_PRETICKED]
        ticked = inside or [found[0][0].stop_id]  # nothing inside the radius: offer the nearest one
        if user_input is not None:
            ids = user_input.get(CONF_STOP_IDS) or []
            if not ids:
                errors["base"] = "choose_stop"
            else:
                await self.async_set_unique_id(f"place_{uuid4().hex[:12]}")
                return self.async_create_entry(
                    title=place["name"],
                    data={
                        CONF_PLACE_NAME: place["name"],
                        CONF_STOP_IDS: list(ids),
                        CONF_PLACE_LOCATION: {"latitude": place["lat"], "longitude": place["lng"]},
                        CONF_PLACE_RADIUS: place["radius"],
                    },
                )
        counts = Counter(s.label for s, _ in found)
        options = [
            SelectOptionDict(
                value=s.stop_id,
                label=(f"{s.label} (#{s.stop_id})" if counts[s.label] > 1 else s.label)
                + f" · {format_distance(d)}",
            )
            for s, d in found
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_STOP_IDS, default=ticked): SelectSelector(
                    SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.LIST)
                )
            }
        )
        return self.async_show_form(
            step_id="place_stops",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "count": str(len(found)),
                "inside": str(len(inside)),
                "radius": str(round(place["radius"])),
            },
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return DpmkOptionsFlow()


class DpmkOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        entry = self.config_entry
        coordinator = self.hass.data.get(DOMAIN, {}).get(entry.entry_id)
        opts = entry.options
        is_place = CONF_STOP_IDS in entry.data
        catalog = await self.hass.async_add_executor_job(load_catalog)

        # the lines of the stop(s): read from what the coordinator already loaded, else ask dpmk.sk
        routes = coordinator.all_routes if coordinator and coordinator.routes_by_stop else []
        if not routes:
            api = DpmkApi(async_get_clientsession(self.hass))
            ids = list(entry.data.get(CONF_STOP_IDS) or [entry.data[CONF_STOP_ID]])
            routes = [(sid, r) for sid in ids for r in (await api.get_stop(sid)).routes]
        route_labels: dict[str, str] = {}
        for _, route in routes:
            route_labels.setdefault(route.key, f"{route.line} → {route.destination}")
        route_opts = [SelectOptionDict(value=k, label=v) for k, v in route_labels.items()]

        lat, lng, radius = (
            coordinator.location
            if coordinator
            else (self.hass.config.latitude, self.hass.config.longitude, DEFAULT_RADIUS)
        )
        has_chosen_spot = bool(opts.get(CONF_LOCATION))
        fields: dict = {}

        if is_place:  # which stops make up the place
            current = [str(i) for i in (opts.get(CONF_STOP_IDS) or entry.data[CONF_STOP_IDS])]
            near = [s for s, _ in catalog.near(lat, lng, PLACE_CANDIDATE_RADIUS)]
            candidates = near + [s for i in current if (s := catalog.get(i)) and s not in near]
            fields[vol.Required(CONF_STOP_IDS, default=current)] = SelectSelector(
                SelectSelectorConfig(
                    options=stop_options(catalog, lat, lng, candidates),
                    multiple=True,
                    mode=SelectSelectorMode.LIST,
                )
            )
        fields[vol.Optional(CONF_ROUTES, default=opts.get(CONF_ROUTES, []))] = SelectSelector(
            SelectSelectorConfig(options=route_opts, multiple=True)
        )
        fields[vol.Optional(CONF_LANGUAGE, default=opts.get(CONF_LANGUAGE, DEFAULT_LANGUAGE))] = SelectSelector(
            SelectSelectorConfig(options=[LANG_AUTO, LANG_SK, LANG_EN], translation_key="language")
        )
        fields[
            vol.Optional(CONF_UPDATE_INTERVAL, default=opts.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        ] = NumberSelector(
            NumberSelectorConfig(
                min=MIN_UPDATE_INTERVAL,
                max=MAX_UPDATE_INTERVAL,
                step=1,
                unit_of_measurement="s",
                mode=NumberSelectorMode.BOX,
            )
        )
        fields[vol.Optional(CONF_MAP_SCOPE, default=opts.get(CONF_MAP_SCOPE, SCOPE_SERVING))] = SelectSelector(
            SelectSelectorConfig(options=[SCOPE_SERVING, SCOPE_ALL], translation_key="map_scope")
        )
        if not is_place:  # a single stop can follow its own position, or sit where you put it
            fields[vol.Optional(CONF_AUTO_LOCATION, default=opts.get(CONF_AUTO_LOCATION, not has_chosen_spot))] = BooleanSelector()
        fields[vol.Optional(CONF_LOCATION, default={"latitude": lat, "longitude": lng})] = LocationSelector(
            LocationSelectorConfig(radius=False)
        )
        fields[vol.Optional(CONF_MAP_RADIUS, default=radius)] = NumberSelector(
            NumberSelectorConfig(
                min=200, max=5000, step=50, unit_of_measurement="m", mode=NumberSelectorMode.BOX
            )
        )
        fields[
            vol.Optional(CONF_MAX_DEPARTURES, default=opts.get(CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES))
        ] = NumberSelector(NumberSelectorConfig(min=1, max=20, step=1))
        fields[vol.Optional(CONF_SCHOOL_MODE, default=opts.get(CONF_SCHOOL_MODE, SCHOOL_AUTO))] = SelectSelector(
            SelectSelectorConfig(
                options=[SCHOOL_AUTO, SCHOOL_SCHOOL, SCHOOL_HOLIDAYS], translation_key="school_mode"
            )
        )
        fields[vol.Optional(CONF_IS_DEFAULT, default=bool(opts.get(CONF_IS_DEFAULT, False)))] = BooleanSelector()
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
