"""The NLB Singapore integration."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .api import create_client
from .const import CONF_PASSWORD, CONF_USER_ID, PLATFORMS
from .coordinator import NlbConfigEntry, NlbCoordinator, NlbRuntimeData


async def async_setup_entry(hass: HomeAssistant, entry: NlbConfigEntry) -> bool:
    """Set up an NLB account from a config entry."""
    client = create_client(entry.data[CONF_USER_ID], entry.data[CONF_PASSWORD])
    coordinator = NlbCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = NlbRuntimeData(client=client, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NlbConfigEntry) -> bool:
    """Unload an NLB config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
