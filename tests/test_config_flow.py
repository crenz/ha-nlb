"""Tests for the NLB config flow."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers import device_registry as dr

from custom_components.nlb.const import (
    CONF_PASSWORD,
    CONF_POLL_HOURS,
    CONF_USER_ID,
    DOMAIN,
)

from .conftest import FakeNlbClient


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def _submit(hass: HomeAssistant, flow_id: str, user_id: str, password: str):
    return await hass.config_entries.flow.async_configure(
        flow_id, {CONF_USER_ID: user_id, CONF_PASSWORD: password}
    )


async def test_user_flow_creates_entry(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await _submit(hass, result["flow_id"], "alice", "secret")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "NLB alice"
    assert result["data"] == {CONF_USER_ID: "alice", CONF_PASSWORD: "secret"}
    entry = result["result"]
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert entry.unique_id == "alice"


async def test_user_id_is_normalised(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    result = await _submit(hass, (await _start(hass))["flow_id"], "  Alice ", "secret")

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_USER_ID] == "alice"
    assert result["result"].unique_id == "alice"


async def test_invalid_auth_shows_error_then_recovers(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    clients["alice"] = FakeNlbClient("alice")
    clients["alice"].auth_error = True
    result = await _submit(hass, (await _start(hass))["flow_id"], "alice", "wrong")

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    clients["alice"].auth_error = False
    result = await _submit(hass, result["flow_id"], "alice", "secret")
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_connection_error_shows_cannot_connect(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    clients["alice"] = FakeNlbClient("alice")
    clients["alice"].connection_error = True

    result = await _submit(hass, (await _start(hass))["flow_id"], "alice", "secret")

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_account_is_rejected(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    first = await _submit(hass, (await _start(hass))["flow_id"], "alice", "secret")
    assert first["type"] is FlowResultType.CREATE_ENTRY

    second = await _submit(hass, (await _start(hass))["flow_id"], "ALICE", "other")

    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_configured"


async def test_two_accounts_create_two_devices(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    for user_id in ("alice", "bob"):
        result = await _submit(hass, (await _start(hass))["flow_id"], user_id, "pw")
        assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert {e.unique_id for e in entries} == {"alice", "bob"}
    registry = dr.async_get(hass)
    for entry in entries:
        assert registry.async_get_device_by_identifier(
            (DOMAIN, entry.unique_id), entry.entry_id
        )


async def _loaded_entry(hass: HomeAssistant, clients: dict[str, FakeNlbClient]):
    result = await _submit(hass, (await _start(hass))["flow_id"], "alice", "secret")
    await hass.async_block_till_done()
    return result["result"]


async def test_options_flow_changes_poll_interval(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient]
) -> None:
    entry = await _loaded_entry(hass, clients)
    assert entry.runtime_data.coordinator.update_interval == timedelta(hours=12)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_POLL_HOURS: 6}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_POLL_HOURS: 6}
    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.coordinator.update_interval == timedelta(hours=6)


@pytest.mark.parametrize("hours", [0, 169])
async def test_options_flow_rejects_out_of_range_interval(
    hass: HomeAssistant, clients: dict[str, FakeNlbClient], hours: int
) -> None:
    entry = await _loaded_entry(hass, clients)
    result = await hass.config_entries.options.async_init(entry.entry_id)

    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_POLL_HOURS: hours}
        )
