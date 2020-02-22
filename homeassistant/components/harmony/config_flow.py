"""Config flow for Logitech Harmony Hub integration."""
import logging
from urllib.parse import urlparse

import aioharmony.exceptions as harmony_exceptions
from aioharmony.harmonyapi import HarmonyAPI
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.components import ssdp
from homeassistant.const import CONF_HOST, CONF_NAME

from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str, vol.Optional(CONF_NAME): str})


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    harmony = HarmonyAPI(ip_address=data[CONF_HOST])

    try:
        if not await harmony.connect():
            await harmony.close()
            raise CannotConnect
    except harmony_exceptions.TimeOut:
        raise CannotConnect

    # Return info that you want to store in the config entry.
    return data


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Logitech Harmony Hub."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self):
        """Initialize the Harmony config flow."""
        self.hubs = []
        self.harmony_config = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            # Abort if already setup
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: user_input[CONF_HOST]}
            )
            try:
                info = await validate_input(self.hass, user_input)
                return self.async_create_entry(title=info[CONF_NAME], data=info)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Return form
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_ssdp(self, discovery_info):
        """Handle a discovered Harmony device."""
        parsed_url = urlparse(discovery_info[ssdp.ATTR_SSDP_LOCATION])
        friendly_name = discovery_info[ssdp.ATTR_UPNP_FRIENDLY_NAME]
        await self.async_set_unique_id(parsed_url.hostname)
        # Abort if already setup
        self._abort_if_unique_id_configured(updates={CONF_HOST: parsed_url.hostname})
        self.context["title_placeholders"] = {"name": friendly_name}

        self.harmony_config = {
            CONF_HOST: parsed_url.hostname,
            CONF_NAME: friendly_name,
        }

        return await self.async_step_link()

    async def async_step_link(self, user_input=None):
        """Attempt to link with the Harmony."""
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, self.harmony_config)
                return self.async_create_entry(title=info[CONF_NAME], data=info)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="link",
            errors=errors,
            description_placeholders={
                "name": self.harmony_config[CONF_NAME],
                "host": self.harmony_config[CONF_HOST],
            },
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
