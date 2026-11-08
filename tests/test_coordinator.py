"""Tests for NlbCoordinator."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.nlb.const import (
    CONF_PASSWORD,
    CONF_USER_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

from .conftest import FakeNlbClient


def _entry(user_id: str = "alice") -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=user_id,
        data={CONF_USER_ID: user_id, CONF_PASSWORD: "secret"},
    )


async def test_default_poll_interval_is_twelve_hours(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.runtime_data.coordinator.update_interval == DEFAULT_SCAN_INTERVAL
    assert timedelta(hours=12) == DEFAULT_SCAN_INTERVAL


async def test_coordinator_polls_on_schedule(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    freezer: FrozenDateTimeFactory,
) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.runtime_data.coordinator.data.loans == 3

    clients["alice"].loans = clients["alice"].loans[:1]
    freezer.tick(DEFAULT_SCAN_INTERVAL + timedelta(minutes=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert entry.runtime_data.coordinator.data.loans == 1


async def test_auth_failure_on_setup_fails_the_entry(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    # The fake is created lazily by the factory, so pre-seed a failing one.
    clients["alice"] = FakeNlbClient("alice")
    clients["alice"].auth_error = True

    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_ERROR


async def test_connection_failure_on_setup_retries_later(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    entry = _entry()
    entry.add_to_hass(hass)
    clients["alice"] = FakeNlbClient("alice")
    clients["alice"].connection_error = True

    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY
