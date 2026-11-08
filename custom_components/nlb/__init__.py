"""The NLB Singapore integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS

type NlbConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: NlbConfigEntry) -> bool:
    """Set up an NLB account from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NlbConfigEntry) -> bool:
    """Unload an NLB config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
