# Task List: NLB Home Assistant Integration

Plan: [plan.md](plan.md) · Spec: [../SPEC.md](../SPEC.md)
Commands: `pytest tests/ --cov=custom_components.nlb --cov-report=term-missing` · `ruff check . && ruff format --check .` · `mypy custom_components/nlb`

## Phase 1: Foundation

- [x] **T1: Tooling and CI** (S)
  - Acceptance:
    - `pyproject.toml` configures ruff, mypy (strict for `custom_components/nlb`), pytest (asyncio auto) and coverage threshold 95
    - `requirements_test.txt` pins `pytest-homeassistant-custom-component` and tooling
    - `.github/workflows/ci.yml` runs lint, types, tests, hassfest, HACS validation
    - `.gitignore` covers venv, caches, coverage
  - Verify: `uv venv --python 3.14` + `uv pip install -r requirements_test.txt` works; `ruff check .` passes; CI workflow YAML valid (`gh workflow` run after push, or `actionlint` if available)
  - Depends on: none
  - Files: `pyproject.toml`, `requirements_test.txt`, `.gitignore`, `.github/workflows/ci.yml`

- [x] **T2: Loadable empty integration** (S)
  - Acceptance:
    - `manifest.json` (domain `nlb`, `config_flow: true`, `iot_class: cloud_polling`, `requirements: []`), `hacs.json`, `const.py`
    - `async_setup_entry` / `async_unload_entry` succeed with a `MockConfigEntry` and no platforms
    - Smoke test proves the HA test harness works with Python 3.14
  - Verify: `pytest tests/test_init.py`; lint and mypy clean; hassfest + HACS jobs green in CI
  - Depends on: T1
  - Files: `custom_components/nlb/{manifest.json,const.py,__init__.py}`, `hacs.json`, `tests/{conftest.py,test_init.py}`

- [x] **T3: Client protocol, stub, data computation** (M)
  - Acceptance:
    - `api.py`: `Loan`, `RenewItemResult`, `NlbAuthError`, `NlbConnectionError`, `NlbClient` protocol, `StubNlbClient`, `create_client()` factory
    - Pure `compute_data(loans, today)` returns loans, overdue, days_until_next_due (next upcoming, overdue ignored, `None` if none)
    - Stub is deterministic per user ID, rejects an empty/"invalid" password, and records renewals
  - Verify: unit tests for none / all overdue / due today / mixed / ties and stub auth/renew; `pytest tests/test_api.py tests/test_data.py`; mypy clean
  - Depends on: T2
  - Files: `custom_components/nlb/api.py`, `custom_components/nlb/coordinator.py` (compute only), `tests/test_api.py`, `tests/test_data.py`

### Checkpoint: Foundation
- [x] All tests, lint, types pass locally (CI pending first push)
- [ ] Review with human before proceeding

## Phase 2: Core slice

- [x] **T4: Coordinator and sensors for one account** (M)
  - Acceptance:
    - `NlbCoordinator` fetches loans via the client (default interval 12 h), maps `NlbAuthError` to `ConfigEntryAuthFailed`, `NlbConnectionError` to `UpdateFailed`
    - Entry setup stores client + coordinator in `runtime_data` and forwards the sensor platform
    - Device `(DOMAIN, user_id)` with three sensors (`loans`, `overdue_loans`, `days_until_next_due`), translated names, unique IDs `<user_id>_<key>`
    - Unload removes entities cleanly
  - Verify: `pytest tests/test_coordinator.py tests/test_sensor.py` using `MockConfigEntry` and the fake client; states match computed data; auth failure fails setup (the reauth flow itself is T8)
  - Depends on: T3
  - Files: `coordinator.py`, `entity.py`, `sensor.py`, `__init__.py`, `strings.json`, `translations/en.json` (+ tests)

## Phase 3: Features

- [x] **T5: Config flow, multi-account** (M)
  - Acceptance:
    - User step takes user ID + password, validates via client, creates entry titled `NLB <user_id>`
    - Unique ID = normalised user ID; duplicate aborts `already_configured`
    - Second distinct account creates a second entry and Device
    - Errors `invalid_auth`, `cannot_connect` shown in form
  - Verify: `pytest tests/test_config_flow.py` (happy, invalid auth, cannot connect, duplicate, two accounts → two devices)
  - Depends on: T4
  - Files: `config_flow.py`, `strings.json`, `translations/en.json`, `tests/test_config_flow.py`

### Checkpoint: Core
- [ ] Add two accounts via the flow in tests; each has three correct sensors
- [ ] All gates green; review with human

- [x] **T6: `nlb.renew_all` service** (M)
  - Acceptance:
    - `services.yaml` with optional `device_id` target; registered once in `async_setup`, `SupportsResponse.OPTIONAL`
    - With device target renews only that account; without target renews all loaded accounts
    - Response keyed by device name with `renewed`, `failed`, and per-item `{item_id, title, success, new_due_date, message}`
    - Unknown / non-NLB device → `ServiceValidationError`; auth/connection errors → `HomeAssistantError`; per-item failures do not raise
    - Coordinator refreshed after renewal
  - Verify: `pytest tests/test_services.py` (single device, no target, bad target, partial failure, client error, refresh called)
  - Depends on: T4 (check current HA service-response docs before coding)
  - Files: `__init__.py`, `services.yaml`, `strings.json`, `translations/en.json`, `tests/test_services.py`

- [x] **T7: Options flow: poll interval** (S)
  - Acceptance:
    - Options flow sets interval in hours (1-168, default 12) per entry; invalid values rejected
    - Change applies without restart (update listener updates coordinator interval)
  - Verify: `pytest tests/test_config_flow.py -k options`; coordinator `update_interval` asserted
  - Depends on: T5
  - Files: `config_flow.py`, `coordinator.py` or `__init__.py`, `strings.json`, `translations/en.json`, tests

- [x] **T8: Reauth flow** (S)
  - Acceptance:
    - `ConfigEntryAuthFailed` surfaces a reauth flow asking for a new password
    - Valid password updates the entry and reloads; invalid shows `invalid_auth`; user ID cannot change
  - Verify: `pytest tests/test_config_flow.py -k reauth`
  - Depends on: T5, T4
  - Files: `config_flow.py`, `strings.json`, `translations/en.json`, tests

### Checkpoint: Features
- [ ] Spec acceptance criteria 1-7 each covered by a passing test
- [ ] Review with human

## Phase 4: Finish

- [x] **T9: README and final gates** (S)
  - Acceptance:
    - README covers HACS custom-repo install, setup, entities, service with example automation, options, stub-client limitation, deferred logo
    - Coverage ≥ 95%; ruff, mypy, hassfest, HACS validation all green in CI
    - Spec criterion 8 met; no credentials in repo or logs
  - Verify: full command set locally; CI green on the PR
  - Depends on: T6, T7, T8
  - Files: `README.md`, minor fixes

### Checkpoint: Complete
- [ ] All acceptance criteria in SPEC.md met
- [ ] Ready for review / merge, then open a follow-up issue for the real NLB client
