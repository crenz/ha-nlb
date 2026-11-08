"""Tests for the pure loan-data computation."""

from __future__ import annotations

from datetime import date

from custom_components.nlb.api import Loan
from custom_components.nlb.coordinator import compute_data

TODAY = date(2026, 11, 8)


def _loan(item_id: str, due: date, *, renewable: bool = True) -> Loan:
    return Loan(
        item_id=item_id, title=f"Book {item_id}", due_date=due, renewable=renewable
    )


def test_no_loans_gives_zero_counts_and_unknown_days() -> None:
    data = compute_data([], TODAY)

    assert data.loans == 0
    assert data.overdue_loans == 0
    assert data.days_until_next_due is None


def test_counts_all_loans() -> None:
    loans = [_loan("a", date(2026, 11, 20)), _loan("b", date(2026, 11, 25))]

    assert compute_data(loans, TODAY).loans == 2


def test_all_overdue_has_no_next_due_date() -> None:
    loans = [_loan("a", date(2026, 11, 1)), _loan("b", date(2026, 11, 7))]

    data = compute_data(loans, TODAY)

    assert data.overdue_loans == 2
    assert data.days_until_next_due is None


def test_loan_due_today_is_not_overdue_and_is_zero_days() -> None:
    data = compute_data([_loan("a", TODAY)], TODAY)

    assert data.overdue_loans == 0
    assert data.days_until_next_due == 0


def test_mixed_loans_ignore_overdue_for_next_due() -> None:
    loans = [
        _loan("late", date(2026, 11, 1)),
        _loan("soon", date(2026, 11, 11)),
        _loan("later", date(2026, 11, 30)),
    ]

    data = compute_data(loans, TODAY)

    assert data.loans == 3
    assert data.overdue_loans == 1
    assert data.days_until_next_due == 3


def test_tied_due_dates_report_that_date() -> None:
    loans = [_loan("a", date(2026, 11, 12)), _loan("b", date(2026, 11, 12))]

    assert compute_data(loans, TODAY).days_until_next_due == 4
