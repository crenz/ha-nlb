"""Tests for the NLB client layer and its stub implementation."""

from __future__ import annotations

from datetime import date

import pytest

from custom_components.nlb.api import (
    NlbAuthError,
    StubNlbClient,
    create_client,
)

TODAY = date(2026, 11, 8)


def _client(user_id: str = "alice", password: str = "secret") -> StubNlbClient:
    return StubNlbClient(user_id, password, today=lambda: TODAY)


async def test_authenticate_accepts_valid_credentials() -> None:
    await _client().authenticate()


@pytest.mark.parametrize("password", ["", "invalid"])
async def test_authenticate_rejects_bad_password(password: str) -> None:
    with pytest.raises(NlbAuthError):
        await _client(password=password).authenticate()


async def test_loans_are_deterministic_per_user() -> None:
    first = await _client("alice").get_loans()
    second = await _client("alice").get_loans()

    assert first == second
    assert first


async def test_different_users_get_different_loans() -> None:
    alice = await _client("alice").get_loans()
    bob = await _client("bob").get_loans()

    assert alice != bob


# "alice" has only renewable items; "dave" has one that is not renewable.
@pytest.mark.parametrize("user_id", ["alice", "dave"])
async def test_renew_all_extends_renewable_loans_only(user_id: str) -> None:
    client = _client(user_id)
    before = {loan.item_id: loan for loan in await client.get_loans()}

    results = await client.renew_all()
    assert (user_id == "dave") == any(not r.success for r in results)

    after = {loan.item_id: loan for loan in await client.get_loans()}
    assert {r.item_id for r in results} == set(before)
    for result in results:
        loan = before[result.item_id]
        assert result.success is loan.renewable
        if loan.renewable:
            assert result.new_due_date is not None
            assert result.new_due_date > loan.due_date
            assert after[result.item_id].due_date == result.new_due_date
            assert result.message is None
        else:
            assert result.new_due_date is None
            assert result.message == "Item cannot be renewed"
            assert after[result.item_id].due_date == loan.due_date


def test_create_client_returns_a_client() -> None:
    client = create_client("alice", "secret")

    assert isinstance(client, StubNlbClient)
