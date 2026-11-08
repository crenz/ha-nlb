"""Config flow for the NLB integration."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import NlbAuthError, NlbConnectionError, create_client
from .const import CONF_PASSWORD, CONF_USER_ID, DOMAIN, normalise_user_id

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


class NlbConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for an NLB account. One entry per account."""

    VERSION = 1

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
