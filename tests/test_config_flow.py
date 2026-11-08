"""Tests for the NLB config flow."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr

from custom_components.nlb.const import CONF_PASSWORD, CONF_USER_ID, DOMAIN

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
