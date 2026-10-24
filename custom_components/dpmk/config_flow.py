"""Config flow: search a stop by name, pick it; options for lines etc."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
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
    CONF_LOCATION,
    CONF_MAP_SCOPE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_RADIUS,
    DEFAULT_UPDATE_INTERVAL,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    SCOPE_ALL,
    SCOPE_SERVING,
    CONF_MAX_DEPARTURES,
    CONF_ROUTES,
    CONF_SCHOOL_MODE,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    DEFAULT_MAX_DEPARTURES,
    DOMAIN,
    SCHOOL_AUTO,
    SCHOOL_HOLIDAYS,
    SCHOOL_SCHOOL,
)


class DpmkConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._found: dict[str, str] = {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            api = DpmkApi(async_get_clientsession(self.hass))
            try:
                self._found = await api.search_stops(user_input["query"])
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                if self._found:
                    return await self.async_step_pick()
                errors["base"] = "no_stops"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("query"): str}),
            errors=errors,
        )

    async def async_step_pick(self, user_input=None):
        if user_input is not None:
            stop_id = user_input[CONF_STOP_ID]
            await self.async_set_unique_id(stop_id)
            self._abort_if_unique_id_configured()
            name = self._found[stop_id]
            return self.async_create_entry(
                title=name, data={CONF_STOP_ID: stop_id, CONF_STOP_NAME: name}
            )
        options = [SelectOptionDict(value=i, label=n) for i, n in self._found.items()]
        return self.async_show_form(
            step_id="pick",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STOP_ID): SelectSelector(
                        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
                    )
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return DpmkOptionsFlow()


class DpmkOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        api = DpmkApi(async_get_clientsession(self.hass))
        stop = await api.get_stop(self.config_entry.data[CONF_STOP_ID])
        route_opts = [
            SelectOptionDict(value=r.key, label=f"{r.line} → {r.destination}") for r in stop.routes
        ]
        opts = self.config_entry.options
        coordinator = self.hass.data.get(DOMAIN, {}).get(self.config_entry.entry_id)
        lat, lng, radius = coordinator.location if coordinator else (
            self.hass.config.latitude, self.hass.config.longitude, DEFAULT_RADIUS
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_LOCATION,
                        default={"latitude": lat, "longitude": lng, "radius": radius},
                    ): LocationSelector(LocationSelectorConfig(radius=True)),
                    vol.Optional(CONF_ROUTES, default=opts.get(CONF_ROUTES, [])): SelectSelector(
                        SelectSelectorConfig(options=route_opts, multiple=True)
                    ),
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=opts.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_UPDATE_INTERVAL,
                            max=MAX_UPDATE_INTERVAL,
                            step=1,
                            unit_of_measurement="s",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Optional(
                        CONF_MAP_SCOPE, default=opts.get(CONF_MAP_SCOPE, SCOPE_SERVING)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[SCOPE_SERVING, SCOPE_ALL], translation_key="map_scope"
                        )
                    ),
                    vol.Optional(
                        CONF_MAX_DEPARTURES,
                        default=opts.get(CONF_MAX_DEPARTURES, DEFAULT_MAX_DEPARTURES),
                    ): NumberSelector(NumberSelectorConfig(min=1, max=20, step=1)),
                    vol.Optional(
                        CONF_SCHOOL_MODE, default=opts.get(CONF_SCHOOL_MODE, SCHOOL_AUTO)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[SCHOOL_AUTO, SCHOOL_SCHOOL, SCHOOL_HOLIDAYS],
                            translation_key="school_mode",
                        )
                    ),
                }
            ),
        )
