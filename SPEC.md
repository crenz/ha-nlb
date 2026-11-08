# Spec: Home Assistant Integration for NLB Accounts

Tracking issue: https://github.com/crenz/ha-nlb/issues/1

## Objective

A Home Assistant custom integration (HACS) that represents each **National Library Board (NLB) Singapore** member account as a **Device**, so library loans can be monitored and renewed from Home Assistant.

**Users:** NLB members (individuals, families with several cards) who run Home Assistant.

**Per-account Device exposes:**

| Entity | Type | Meaning |
|---|---|---|
| `Loans` | sensor (measurement, unit `loans`) | Number of items currently on loan |
| `Overdue loans` | sensor (measurement, unit `loans`) | Number of loans whose due date is before today |
| `Days until next due` | sensor (measurement, unit `d`) | Days from today to the earliest due date among non-overdue loans; `unknown` if there are none |

**Action:** `nlb.renew_all` renews every renewable loan for the targeted account(s).

**Multi-account:** the user can add the integration any number of times, once per NLB account. Each is an independent config entry and Device.

**Scope of this deliverable (decided):**
- Full scaffold with working logic: config flow, coordinator, sensors, the service, translations, tests, HACS metadata and CI.
- The NLB client is a **stub**: a defined interface (`NlbClient`) with a fake in-memory implementation. Real NLB access (login, scraping or API) is a later issue and must not change anything outside `api.py`.

### Acceptance criteria
1. Adding the integration through the UI with a user ID and password creates a config entry and one Device.
2. Adding it a second time with a different user ID creates a second, independent Device. A duplicate user ID is rejected (`already_configured`).
3. Each Device has the three sensors above, with values derived from the loans the client returns.
4. `nlb.renew_all` called with a device target renews only that account. Called with no target, it renews all configured accounts. It returns per-item results as response data (see Key Design). Afterwards the coordinator refreshes.
5. The options flow lets the user set the poll interval per account (hours, 1-168, default 12); changing it takes effect without restart.
6. Invalid credentials during setup show a form error. Credentials that expire later trigger the reauth flow.
7. Removing an entry removes its Device, entities and coordinator.
8. All tests and linters pass in CI.

## Assumptions
1. NLB Singapore; credentials are user ID plus password.
2. Latest Home Assistant (2026.10.x at time of writing), Python 3.14 (required by the current `pytest-homeassistant-custom-component`); Python is managed with `uv`, since the host has only 3.13 and no venv/pip.
3. Polling (`cloud_polling`), default every 12 hours (configurable via options flow, min 1 hour), no push.
4. Credentials are stored in the config entry (the standard HA approach).
5. Nothing is published to HACS or the HA brands repo in this iteration. No logo or brand images in this iteration (deferred).

## Tech Stack
- Python 3.14 (via `uv`), Home Assistant custom component, domain `nlb`
- `DataUpdateCoordinator`, `ConfigFlow` with `reauth`, `SensorEntity`, `DeviceInfo`, `runtime_data` on the config entry
- Tests: `pytest`, `pytest-homeassistant-custom-component`, `pytest-asyncio`
- Lint/format/type: `ruff`, `mypy` (strict on `custom_components/nlb`)
- CI: GitHub Actions (lint, tests, `hassfest`, HACS validation)
- Dependencies added for the scaffold: none at runtime (`manifest.json` `requirements: []`)

## Commands
```
Setup:   uv venv --python 3.14 .venv && uv pip install -r requirements_test.txt
Run:     prefix commands with `.venv/bin/` (or `source .venv/bin/activate`)
Test:    pytest tests/ --cov=custom_components.nlb --cov-report=term-missing
Lint:    ruff check . && ruff format --check .
Fix:     ruff check . --fix && ruff format .
Types:   mypy custom_components/nlb
```
A dev Home Assistant instance is out of scope; verify through tests.

## Project Structure
```
custom_components/nlb/
  __init__.py        → async_setup_entry / unload, service registration
  manifest.json      → domain, version, config_flow: true, iot_class: cloud_polling
  const.py           → DOMAIN, defaults, config keys
  api.py             → NlbClient protocol, models (Loan), errors, StubNlbClient
  coordinator.py     → NlbCoordinator, computes NlbData (counts, days to next due)
  config_flow.py     → user + reauth + options flow, unique_id = normalised user ID
  entity.py          → NlbEntity base, DeviceInfo
  sensor.py          → 3 sensor descriptions
  services.yaml      → renew_all schema
  strings.json
  translations/en.json
hacs.json
tests/
  conftest.py        → fixtures, enable_custom_integrations, fake client
  test_config_flow.py
  test_coordinator.py
  test_sensor.py
  test_services.py
.github/workflows/ci.yml
pyproject.toml       → ruff, mypy, pytest config
requirements_test.txt
README.md
SPEC.md
```

## Key Design

**Client boundary** (`api.py`) is the only place that knows about NLB:
```python
@dataclass(frozen=True, slots=True)
class Loan:
    title: str
    due_date: date
    renewable: bool
    item_id: str

@dataclass(frozen=True, slots=True)
class RenewItemResult:
    item_id: str
    title: str
    success: bool
    new_due_date: date | None
    message: str | None

class NlbClient(Protocol):
    async def authenticate(self) -> None: ...        # raises NlbAuthError
    async def get_loans(self) -> list[Loan]: ...     # raises NlbConnectionError
    async def renew_all(self) -> list[RenewItemResult]: ...
```
`StubNlbClient` returns deterministic sample loans (seeded from the user ID) and records renewals, so the flow works end to end without network access. The integration builds the client through one factory in `api.py`, which is the single swap point for the real client.

**Computation** (in `coordinator.py`, pure and unit-tested), with `today` injected for testability:
- `loans` = `len(loans)`
- `overdue` = count where `due_date < today`
- `days_until_next_due` = `min((due - today).days)` over loans with `due_date >= today`, or `None`

**Config entries / devices:** one entry per account. Device identifier is `(DOMAIN, user_id_normalised)`; name is `NLB <user_id>`. Entity unique IDs are `<user_id_normalised>_<key>`.

**Service `nlb.renew_all`:** optional `device_id` target (omitted = all accounts). It resolves devices to config entries, calls `renew_all`, then `async_request_refresh`. Registered with `SupportsResponse.OPTIONAL`; the response is keyed by device name: `{"NLB alice": {"renewed": 2, "failed": 1, "items": [{"item_id", "title", "success", "new_due_date", "message"}]}}`. Per-item failures (e.g. not renewable) do not raise; only auth/connection errors do. Unknown or non-NLB device raises `ServiceValidationError`. Client errors raise `HomeAssistantError`.

## Code Style
Home Assistant core conventions: fully typed, async, `from __future__ import annotations`, `ruff` defaults plus the HA rule set, double quotes, 88 columns. Sample:

```python
@dataclass(frozen=True, kw_only=True)
class NlbSensorDescription(SensorEntityDescription):
    value_fn: Callable[[NlbData], int | None]

SENSORS: tuple[NlbSensorDescription, ...] = (
    NlbSensorDescription(
        key="loans",
        translation_key="loans",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.loans,
    ),
    ...
)
```
Names come from translations (`has_entity_name = True`), never hard-coded. Logging uses `_LOGGER` and never includes passwords.

## Testing Strategy
- **Unit (pure logic):** `NlbData` computation covering no loans, all overdue, due today, mixed, and ties.
- **Integration (HA test harness):** config flow (happy path, invalid auth, cannot connect, duplicate, second account, reauth), sensor states per account, service (single device, no target, bad target, client failure), unload and remove.
- Tests use a fake `NlbClient`; no network.
- Coverage: ≥ 95% on `custom_components/nlb`. CI fails below that.
- TDD: write each failing test first (see `test-driven-development`).

## Boundaries
- **Always:** run the test, lint and type commands before committing; keep NLB-specific code in `api.py`; use translations for user-facing strings; validate and normalise user input; mask credentials in logs and diagnostics.
- **Ask first:** adding runtime dependencies; changing the entity set, service names or unique-ID scheme (breaks existing installs); changing the CI workflow; implementing the real NLB client or hitting NLB's servers.
- **Never:** commit credentials or real account data; log passwords; hard-code user IDs; skip or delete failing tests to get green; call the real NLB service from tests.

## Success Criteria
- Acceptance criteria 1-8 above are demonstrably met by automated tests.
- `pytest`, `ruff`, `mypy` all pass locally and in CI; `hassfest` and HACS validation pass.
- Swapping `StubNlbClient` for a real client requires edits in `api.py` only.
- README documents installation (HACS custom repository), configuration, entities, the service, and the stub-client limitation.

## Open Questions
Resolved: next upcoming due date (overdue ignored); no-target renews all accounts; per-item results returned; poll interval configurable, default 12 h; logo skipped for now.

None open. Deferred: NLB logo / brand images (`custom_components/nlb/brand/`), to be added later once a file and usage rights are sorted.
