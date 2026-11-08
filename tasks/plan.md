# Implementation Plan: NLB Home Assistant Integration

Source: [SPEC.md](../SPEC.md) · Issue: https://github.com/crenz/ha-nlb/issues/1
Tasks: [tasks/todo.md](todo.md)

## Overview
Build the `nlb` HACS custom component in thin vertical slices. Each task ends with a green test/lint/type run. The NLB client is a stub behind the `NlbClient` protocol, so everything is testable offline.

## Dependency Graph
```
tooling + CI (T1)
   └── loadable integration (T2)
          └── client protocol + stub + data computation (T3)
                 └── coordinator + sensors, one account (T4)
                        ├── config flow: add accounts, multi-account (T5)
                        │      ├── options flow: poll interval (T7)
                        │      └── reauth flow (T8)
                        └── service nlb.renew_all (T6)
                                 └── (all) docs + final gates (T9)
```
T6 uses MockConfigEntry from T4 so it does not need T5. T6, T7, T8 are independent of each other after their parents.

## Architecture Decisions
- **One config entry per account**: multi-account falls out of HA's model; Device and unique IDs derive from the normalised user ID.
- **All NLB knowledge in `api.py`**: protocol + `StubNlbClient` + one factory; real client later changes only this file.
- **Pure computation**: loan counts and days-to-next-due are a pure function with `today` injected, unit-tested without HA.
- **`entry.runtime_data`** holds client + coordinator (no `hass.data`).
- **Service registered in `async_setup`** (once, domain-level), `SupportsResponse.OPTIONAL`.
- **Tests first** per task (red, green, refactor); the fake client is a fixture in `conftest.py`.

## Phases
- **Phase 1 Foundation:** T1-T3
- **Phase 2 Core slice (one account, visible sensors):** T4
- **Phase 3 Features:** T5-T8
- **Phase 4 Finish:** T9

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| `pytest-homeassistant-custom-component` pins an HA version that needs a specific Python | High | T1 pins versions and proves one trivial test runs in CI before any feature work (fail fast) |
| Service response data / device targeting API details differ by HA version | Med | T6 checks current HA docs before coding (source-driven); keep logic in a helper unit-tested separately |
| Stub behaviour drifts from what real NLB returns | Med | Keep `Loan` / `RenewItemResult` minimal; real client work is a separate issue that may extend the protocol (ask first) |
| Changing unique-ID scheme later breaks installs | Med | Fixed in T4/T5 and listed under "Ask first" in the spec |
| hassfest/HACS validation rejects metadata | Low | Added to CI in T1, goes green at T2 |

## Open Questions
None. Deferred: NLB logo/brand images; the real NLB client.

## Task Summary
| # | Task | Size |
|---|---|---|
| T1 | Tooling and CI | S |
| T2 | Loadable empty integration | S |
| T3 | Client protocol, stub, data computation | M |
| T4 | Coordinator and sensors for one account | M |
| T5 | Config flow, multi-account | M |
| T6 | `nlb.renew_all` service | M |
| T7 | Options flow: poll interval | S |
| T8 | Reauth flow | S |
| T9 | README and final gates | S |

Checkpoints after T3, T5, and T8/T9 (see todo.md).
