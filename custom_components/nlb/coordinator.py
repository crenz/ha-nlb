"""Data coordination for the NLB integration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from .api import Loan


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
