"""Config flow — UI setup: host + password (+ options)."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_COUNTRY_PREFIX,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DEFAULT_COUNTRY_PREFIX,
    DEFAULT_HOST,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
)
from .livebox import LiveboxAuthError, LiveboxClient, LiveboxError


class LiveboxCallmonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}
        if user_input is not None:
            client = LiveboxClient(
                None,
                user_input[CONF_HOST],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )
            try:
                await client.login()
            except LiveboxAuthError:
                errors["base"] = "invalid_auth"
            except LiveboxError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="Livebox Call Monitor", data=user_input
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): int,
                vol.Optional(CONF_COUNTRY_PREFIX, default=DEFAULT_COUNTRY_PREFIX): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
