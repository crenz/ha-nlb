"""Constants for the NLB integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "nlb"

CONF_USER_ID: Final = "user_id"
CONF_PASSWORD: Final = "password"
CONF_POLL_HOURS: Final = "poll_hours"

DEFAULT_POLL_HOURS: Final = 12
MIN_POLL_HOURS: Final = 1
MAX_POLL_HOURS: Final = 168
DEFAULT_SCAN_INTERVAL: Final = timedelta(hours=DEFAULT_POLL_HOURS)

PLATFORMS: Final = [Platform.SENSOR]


def normalise_user_id(user_id: str) -> str:
    """Return the canonical form of an NLB user ID (used for IDs and uniqueness)."""
    return user_id.strip().lower()
