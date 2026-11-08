"""Config flow for the NLB integration (steps are added in a later task)."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class NlbConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for an NLB account."""

    VERSION = 1
