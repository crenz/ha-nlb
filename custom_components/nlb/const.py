"""Constants for the NLB integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "nlb"

CONF_USER_ID: Final = "user_id"
CONF_PASSWORD: Final = "password"
CONF_POLL_HOURS: Final = "poll_hours"

DEFAULT_POLL_HOURS: Final = 12
MIN_POLL_HOURS: Final = 1
MAX_POLL_HOURS: Final = 168
DEFAULT_SCAN_INTERVAL: Final = timedelta(hours=DEFAULT_POLL_HOURS)

PLATFORMS: Final[list[str]] = []
