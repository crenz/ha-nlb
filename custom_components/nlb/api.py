"""NLB client boundary.

Everything that knows how to talk to NLB lives in this module. The rest of the
integration only depends on :class:`NlbClient`. Until the real client exists,
:func:`create_client` returns a deterministic in-memory :class:`StubNlbClient`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Protocol

RENEWAL_EXTENSION = timedelta(days=14)
NOT_RENEWABLE_MESSAGE = "Item cannot be renewed"


class NlbError(Exception):
    """Base class for NLB client errors."""


class NlbAuthError(NlbError):
    """Credentials were rejected."""


class NlbConnectionError(NlbError):
    """NLB could not be reached or returned an unusable response."""


@dataclass(frozen=True, slots=True)
class Loan:
    """A single item on loan."""

    item_id: str
    title: str
    due_date: date
    renewable: bool


@dataclass(frozen=True, slots=True)
class RenewItemResult:
    """Outcome of trying to renew one loan."""

    item_id: str
    title: str
    success: bool
    new_due_date: date | None
    message: str | None


class NlbClient(Protocol):
    """What the integration needs from NLB."""

    async def authenticate(self) -> None:
        """Validate the credentials. Raises NlbAuthError / NlbConnectionError."""

    async def get_loans(self) -> list[Loan]:
        """Return current loans. Raises NlbAuthError / NlbConnectionError."""

    async def renew_all(self) -> list[RenewItemResult]:
        """Try to renew every loan. Raises NlbAuthError / NlbConnectionError."""


class StubNlbClient:
    """Deterministic in-memory client used until real NLB access exists.

    Loans are derived from a hash of the user ID. An empty password or the
    password ``invalid`` is rejected, which lets flows be exercised by hand.
    """

    def __init__(
        self,
        user_id: str,
        password: str,
        *,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._user_id = user_id
        self._password = password
        self._today = today
        self._loans: list[Loan] | None = None

    async def authenticate(self) -> None:
        if not self._password or self._password == "invalid":
            raise NlbAuthError("Invalid credentials")

    async def get_loans(self) -> list[Loan]:
        return list(self._ensure_loans())

    async def renew_all(self) -> list[RenewItemResult]:
        results: list[RenewItemResult] = []
        renewed: list[Loan] = []
        for loan in self._ensure_loans():
            if loan.renewable:
                new_due = loan.due_date + RENEWAL_EXTENSION
                renewed.append(replace(loan, due_date=new_due))
                results.append(
                    RenewItemResult(loan.item_id, loan.title, True, new_due, None)
                )
            else:
                renewed.append(loan)
                results.append(
                    RenewItemResult(
                        loan.item_id, loan.title, False, None, NOT_RENEWABLE_MESSAGE
                    )
                )
        self._loans = renewed
        return results

    def _ensure_loans(self) -> list[Loan]:
        if self._loans is None:
            self._loans = self._generate_loans()
        return self._loans

    def _generate_loans(self) -> list[Loan]:
        digest = hashlib.sha256(self._user_id.encode()).digest()
        today = self._today()
        return [
            Loan(
                item_id=f"{self._user_id}-{i}",
                title=f"Stub Book {i + 1}",
                due_date=today + timedelta(days=digest[i + 1] % 30 - 5),
                renewable=digest[i + 8] % 4 != 0,
            )
            for i in range(digest[0] % 5 + 1)
        ]


def create_client(user_id: str, password: str) -> NlbClient:
    """Build the client for an account. The single swap point for the real client."""
    return StubNlbClient(user_id, password)
