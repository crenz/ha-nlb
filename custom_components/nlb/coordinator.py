"""Data coordination for the NLB integration."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import Loan, NlbAuthError, NlbClient, NlbConnectionError
from .const import CONF_POLL_HOURS, DEFAULT_POLL_HOURS, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NlbData:
    """Values exposed by the sensors of one account."""

    loans: int
    overdue_loans: int
    days_until_next_due: int | None


def compute_data(loans: Iterable[Loan], today: date) -> NlbData:
    """Summarise loans: totals, overdue count and days to the next due date."""
    loan_list = list(loans)
    upcoming = [
        (loan.due_date - today).days for loan in loan_list if loan.due_date >= today
    ]
    return NlbData(
        loans=len(loan_list),
        overdue_loans=len(loan_list) - len(upcoming),
        days_until_next_due=min(upcoming, default=None),
    )


@dataclass(slots=True)
class NlbRuntimeData:
    """Objects kept per config entry while it is loaded."""

    client: NlbClient
    coordinator: NlbCoordinator


type NlbConfigEntry = ConfigEntry[NlbRuntimeData]


def poll_interval(entry: ConfigEntry) -> timedelta:
    """Poll interval configured for an entry."""
    return timedelta(hours=entry.options.get(CONF_POLL_HOURS, DEFAULT_POLL_HOURS))


class NlbCoordinator(DataUpdateCoordinator[NlbData]):
    """Fetches the loans of one NLB account."""

    config_entry: NlbConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: NlbConfigEntry, client: NlbClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=poll_interval(entry),
        )
        self.client = client

    async def _async_update_data(self) -> NlbData:
        try:
            loans = await self.client.get_loans()
        except NlbAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except NlbConnectionError as err:
            raise UpdateFailed(str(err)) from err
        return compute_data(loans, dt_util.now().date())
