"""Config flow for the NLB integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import probatio as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import NlbAuthError, NlbConnectionError, create_client
from .const import (
    CONF_PASSWORD,
    CONF_POLL_HOURS,
    CONF_USER_ID,
    DEFAULT_POLL_HOURS,
    DOMAIN,
    MAX_POLL_HOURS,
    MIN_POLL_HOURS,
    normalise_user_id,
)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USER_ID): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT, autocomplete="username")
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)


REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD, autocomplete="current-password"
            )
        ),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_POLL_HOURS, default=DEFAULT_POLL_HOURS): vol.All(
            NumberSelector(
                NumberSelectorConfig(
                    min=MIN_POLL_HOURS,
                    max=MAX_POLL_HOURS,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Coerce(int),
        )
    }
)


class NlbConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for an NLB account. One entry per account."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> NlbOptionsFlow:
        """Return the options flow."""
        return NlbOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the NLB credentials and add the account."""
        errors: dict[str, str] = {}
        if user_input is not None:
            user_id = normalise_user_id(user_input[CONF_USER_ID])
            await self.async_set_unique_id(user_id)
            self._abort_if_unique_id_configured()

            errors = await self._validate(user_id, user_input[CONF_PASSWORD])
            if not errors:
                return self.async_create_entry(
                    title=f"NLB {user_id}",
                    data={
                        CONF_USER_ID: user_id,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA,
                {CONF_USER_ID: user_input[CONF_USER_ID]} if user_input else None,
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start re-authentication after NLB rejected the stored password."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new password; the user ID cannot be changed."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await self._validate(
                entry.data[CONF_USER_ID], user_input[CONF_PASSWORD]
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            description_placeholders={"user_id": entry.data[CONF_USER_ID]},
            errors=errors,
        )

    @staticmethod
    async def _validate(user_id: str, password: str) -> dict[str, str]:
        """Check credentials; return form errors (empty when valid)."""
        try:
            await create_client(user_id, password).authenticate()
        except NlbAuthError:
            return {"base": "invalid_auth"}
        except NlbConnectionError:
            return {"base": "cannot_connect"}
        return {}


class NlbOptionsFlow(OptionsFlowWithReload):
    """Options for one NLB account; the entry reloads when they change."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set the poll interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )
