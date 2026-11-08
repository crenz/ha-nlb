"""Tests for the NLB sensors and device."""

from __future__ import annotations

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nlb.const import CONF_PASSWORD, CONF_USER_ID, DOMAIN

from .conftest import TODAY, FakeNlbClient


async def _setup(hass: HomeAssistant, user_id: str = "alice") -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=user_id,
        data={CONF_USER_ID: user_id, CONF_PASSWORD: "secret"},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, user_id: str, key: str) -> str:
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{user_id}_{key}")
    assert entity_id is not None, f"no entity for {key}"
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


async def test_account_creates_one_device_with_three_sensors(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(f"{TODAY.isoformat()} 12:00:00")
    entry = await _setup(hass)

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "alice"), entry.entry_id
    )
    assert device is not None
    assert device.name == "NLB alice"
    entries = er.async_entries_for_device(er.async_get(hass), device.id)
    assert {e.unique_id for e in entries} == {
        "alice_loans",
        "alice_overdue_loans",
        "alice_days_until_next_due",
    }


async def test_sensor_values_follow_loans(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(f"{TODAY.isoformat()} 12:00:00")
    await _setup(hass)

    assert _state(hass, "alice", "loans") == "3"
    assert _state(hass, "alice", "overdue_loans") == "1"
    assert _state(hass, "alice", "days_until_next_due") == "3"


async def test_days_until_next_due_is_unknown_without_upcoming_loans(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(f"{TODAY.isoformat()} 12:00:00")
    client = clients.setdefault("alice", FakeNlbClient("alice"))
    client.loans = []

    await _setup(hass)

    assert _state(hass, "alice", "loans") == "0"
    assert _state(hass, "alice", "days_until_next_due") == "unknown"


async def test_unload_removes_entity_state(
    hass: HomeAssistant,
    clients: dict[str, FakeNlbClient],
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(f"{TODAY.isoformat()} 12:00:00")
    entry = await _setup(hass)
    assert _state(hass, "alice", "loans") == "3"

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    assert _state(hass, "alice", "loans") == "unavailable"
