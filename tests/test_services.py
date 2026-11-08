"""Tests for the nlb.renew_all service."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nlb.api import Loan, RenewItemResult
from custom_components.nlb.const import CONF_PASSWORD, CONF_USER_ID, DOMAIN

from .conftest import TODAY, FakeNlbClient

NEW_DUE = date(2026, 11, 25)


async def _add_account(hass: HomeAssistant, user_id: str) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"NLB {user_id}",
        unique_id=user_id,
        data={CONF_USER_ID: user_id, CONF_PASSWORD: "secret"},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _device_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.unique_id), entry.entry_id
    )
    assert device is not None
    return device.id


async def _renew(hass: HomeAssistant, data: dict | None = None) -> dict:
    response = await hass.services.async_call(
        DOMAIN, "renew_all", data or {}, blocking=True, return_response=True
    )
    assert response is not None
    return response


@pytest.fixture(autouse=True)
def _freeze_today(freezer: FrozenDateTimeFactory) -> None:
    freezer.move_to(f"{TODAY.isoformat()} 12:00:00")


@pytest.fixture
async def accounts(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> dict[str, MockConfigEntry]:
    for user_id in ("alice", "bob"):
        clients[user_id] = FakeNlbClient(user_id)
        clients[user_id].renew_results = [
            RenewItemResult("a", "Soon Book", True, NEW_DUE, None),
            RenewItemResult("c", "Later Book", False, None, "Item cannot be renewed"),
        ]
    return {u: await _add_account(hass, u) for u in ("alice", "bob")}


async def test_device_target_renews_only_that_account(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    accounts: dict[str, MockConfigEntry],
) -> None:
    response = await _renew(hass, {"device_id": _device_id(hass, accounts["alice"])})

    assert clients["alice"].renew_calls == 1
    assert clients["bob"].renew_calls == 0
    assert set(response) == {"NLB alice"}


async def test_no_target_renews_every_account(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    accounts: dict[str, MockConfigEntry],
) -> None:
    response = await _renew(hass)

    assert clients["alice"].renew_calls == 1
    assert clients["bob"].renew_calls == 1
    assert set(response) == {"NLB alice", "NLB bob"}


async def test_response_reports_per_item_results(
    hass: HomeAssistant, accounts: dict[str, MockConfigEntry]
) -> None:
    response = await _renew(hass, {"device_id": _device_id(hass, accounts["bob"])})

    assert response["NLB bob"] == {
        "renewed": 1,
        "failed": 1,
        "items": [
            {
                "item_id": "a",
                "title": "Soon Book",
                "success": True,
                "new_due_date": "2026-11-25",
                "message": None,
            },
            {
                "item_id": "c",
                "title": "Later Book",
                "success": False,
                "new_due_date": None,
                "message": "Item cannot be renewed",
            },
        ],
    }


async def test_unknown_device_is_a_validation_error(
    hass: HomeAssistant, accounts: dict[str, MockConfigEntry]
) -> None:
    with pytest.raises(ServiceValidationError, match="does not match"):
        await _renew(hass, {"device_id": "does-not-exist"})


@pytest.mark.parametrize("failure", ["auth_error", "connection_error"])
async def test_client_errors_raise_home_assistant_error(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    accounts: dict[str, MockConfigEntry],
    failure: str,
) -> None:
    setattr(clients["alice"], failure, True)

    with pytest.raises(HomeAssistantError):
        await _renew(hass, {"device_id": _device_id(hass, accounts["alice"])})


async def test_coordinator_refreshes_after_renewal(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    accounts: dict[str, MockConfigEntry],
) -> None:
    coordinator = accounts["alice"].runtime_data.coordinator
    assert coordinator.data.overdue_loans == 1
    clients["alice"].loans = [Loan("b", "Soon Book", TODAY + timedelta(days=3), True)]

    await _renew(hass, {"device_id": _device_id(hass, accounts["alice"])})

    assert coordinator.data.loans == 1
    assert coordinator.data.overdue_loans == 0
