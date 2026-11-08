"""Base entity for the NLB integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_USER_ID, DOMAIN, normalise_user_id
from .coordinator import NlbConfigEntry, NlbCoordinator


class NlbEntity(CoordinatorEntity[NlbCoordinator]):
    """An entity belonging to one NLB account (Device)."""

    _attr_has_entity_name = True

    def __init__(self, entry: NlbConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        user_id = normalise_user_id(entry.data[CONF_USER_ID])
        self._attr_unique_id = f"{user_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, user_id)},
            name=f"NLB {user_id}",
            manufacturer="National Library Board Singapore",
            entry_type=DeviceEntryType.SERVICE,
        )
