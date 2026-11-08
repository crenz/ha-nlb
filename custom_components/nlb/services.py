"""Services for the NLB integration."""

from __future__ import annotations

from typing import Any

import probatio as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.service import async_extract_config_entry_ids

from .api import NlbError, RenewItemResult
from .const import DOMAIN
from .coordinator import NlbConfigEntry

SERVICE_RENEW_ALL = "renew_all"
RENEW_ALL_SCHEMA = vol.Schema(cv.TARGET_SERVICE_FIELDS)


def _item_to_dict(item: RenewItemResult) -> dict[str, Any]:
    return {
        "item_id": item.item_id,
        "title": item.title,
        "success": item.success,
        "new_due_date": item.new_due_date.isoformat() if item.new_due_date else None,
        "message": item.message,
    }


async def _async_renew_all(call: ServiceCall) -> dict[str, Any]:
    hass = call.hass
    entries = await _async_select_entries(hass, call)

    response: dict[str, Any] = {}
    for entry in entries:
        try:
            results = await entry.runtime_data.client.renew_all()
        except NlbError as err:
            raise HomeAssistantError(
                f"Renewal failed for {entry.title}: {err}"
            ) from err
        await entry.runtime_data.coordinator.async_request_refresh()
        response[entry.title] = {
            "renewed": sum(item.success for item in results),
            "failed": sum(not item.success for item in results),
            "items": [_item_to_dict(item) for item in results],
        }
    return response


async def _async_select_entries(
    hass: HomeAssistant, call: ServiceCall
) -> list[NlbConfigEntry]:
    loaded = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if not any(key in call.data for key in cv.TARGET_SERVICE_FIELDS):
        return loaded

    targeted = await async_extract_config_entry_ids(call)
    selected = [entry for entry in loaded if entry.entry_id in targeted]
    if not selected:
        raise ServiceValidationError("The target does not match any NLB account")
    return selected


def async_register_services(hass: HomeAssistant) -> None:
    """Register the integration's services (once, at domain setup)."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_RENEW_ALL,
        _async_renew_all,
        schema=RENEW_ALL_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
