"""Shared fixtures for the NLB integration tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from custom_components.nlb.api import (
    Loan,
    NlbAuthError,
    NlbConnectionError,
    RenewItemResult,
)

TODAY = date(2026, 11, 8)


class FakeNlbClient:
    """Scriptable stand-in for NlbClient."""

    def __init__(self, user_id: str = "alice", password: str = "secret") -> None:
        self.user_id = user_id
        self.password = password
        self.loans: list[Loan] = [
            Loan("a", "Overdue Book", TODAY - timedelta(days=2), True),
            Loan("b", "Soon Book", TODAY + timedelta(days=3), True),
            Loan("c", "Later Book", TODAY + timedelta(days=10), False),
        ]
        self.auth_error = False
        self.connection_error = False
        self.renew_calls = 0
        self.renew_results: list[RenewItemResult] = []

    async def authenticate(self) -> None:
        self._maybe_fail()

    async def get_loans(self) -> list[Loan]:
        self._maybe_fail()
        return list(self.loans)

    async def renew_all(self) -> list[RenewItemResult]:
        self._maybe_fail()
        self.renew_calls += 1
        return list(self.renew_results)

    def _maybe_fail(self) -> None:
        if self.auth_error:
            raise NlbAuthError("bad credentials")
        if self.connection_error:
            raise NlbConnectionError("offline")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load the custom integration under test."""


@pytest.fixture
def clients() -> Generator[dict[str, FakeNlbClient]]:
    """Patch the client factory; yields the created fake clients by user ID."""
    created: dict[str, FakeNlbClient] = {}

    def factory(user_id: str, password: str) -> FakeNlbClient:
        client = created.setdefault(user_id, FakeNlbClient(user_id, password))
        client.password = password
        return client

    with (
        patch("custom_components.nlb.create_client", side_effect=factory),
        patch("custom_components.nlb.config_flow.create_client", side_effect=factory),
    ):
        yield created
