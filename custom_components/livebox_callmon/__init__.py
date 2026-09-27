"""Livebox Call Monitor — setup, services, and bundled-card registration."""

from __future__ import annotations

import logging
import os

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_COUNTRY_PREFIX,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_POLL_INTERVAL,
    CONF_USERNAME,
    DEFAULT_COUNTRY_PREFIX,
    DEFAULT_HISTORY_LEN,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    SERVICE_ADD_CONTACT,
    SERVICE_DELETE_CONTACT,
    SERVICE_EDIT_CONTACT,
    TAGS,
)
from .contacts import ContactStore
from .coordinator import LiveboxCoordinator
from .livebox import LiveboxClient

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # NOTE: do NOT use HA's shared session — it uses a safe cookie jar that
    # drops cookies from IP-address hosts (192.168.1.1), breaking the Livebox
    # session cookie. The client builds its own aiohttp session with
    # CookieJar(unsafe=True) when passed None.
    country = entry.data.get(CONF_COUNTRY_PREFIX, DEFAULT_COUNTRY_PREFIX)

    client = LiveboxClient(
        None,
        entry.data[CONF_HOST],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )
    contacts = ContactStore(hass, country)
    await contacts.load()

    coordinator = LiveboxCoordinator(
        hass,
        client,
        contacts,
        entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        DEFAULT_HISTORY_LEN,
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "contacts": contacts,
        "client": client,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass, contacts, coordinator)
    _register_frontend_card(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def _register_services(hass: HomeAssistant, contacts: ContactStore, coordinator) -> None:
    """Register add/edit/delete_contact services."""

    async def _refresh():
        # re-enrich history after a contact change and push new state
        for c in coordinator.history:
            m = contacts.lookup(c["number"])
            if m:
                if m.get("name"):
                    c["name"] = m["name"]
                    c["display"] = m["name"]
                c["tag"] = m.get("tag", "other")
        await coordinator.async_request_refresh()

    async def add_contact(call: ServiceCall) -> None:
        await contacts.add(
            call.data["number"],
            call.data["name"],
            call.data.get("tag", "other"),
            call.data.get("notes", ""),
        )
        await _refresh()

    async def edit_contact(call: ServiceCall) -> None:
        await contacts.edit(
            call.data["number"],
            name=call.data.get("name"),
            tag=call.data.get("tag"),
            notes=call.data.get("notes"),
            new_number=call.data.get("new_number"),
        )
        await _refresh()

    async def delete_contact(call: ServiceCall) -> None:
        await contacts.delete(call.data["number"])
        await _refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_CONTACT, add_contact,
        schema=vol.Schema({
            vol.Required("number"): cv.string,
            vol.Required("name"): cv.string,
            vol.Optional("tag", default="other"): vol.In(TAGS),
            vol.Optional("notes", default=""): cv.string,
        }),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_EDIT_CONTACT, edit_contact,
        schema=vol.Schema({
            vol.Required("number"): cv.string,
            vol.Optional("name"): cv.string,
            vol.Optional("tag"): vol.In(TAGS),
            vol.Optional("notes"): cv.string,
            vol.Optional("new_number"): cv.string,
        }),
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_CONTACT, delete_contact,
        schema=vol.Schema({vol.Required("number"): cv.string}),
    )


def _register_frontend_card(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card at /livebox_callmon/card.js."""
    card = os.path.join(os.path.dirname(__file__), "..", "..", "www", "livebox-callmon-card.js")
    card = os.path.normpath(card)
    local = os.path.join(os.path.dirname(__file__), "livebox-callmon-card.js")
    path = card if os.path.exists(card) else local
    try:
        hass.http.register_static_path(f"/{DOMAIN}/card.js", path, cache_headers=False)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not register card static path: %s", err)
