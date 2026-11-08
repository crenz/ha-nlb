# NLB Singapore for Home Assistant

A Home Assistant custom integration that represents each **National Library Board (NLB) Singapore** member account as a **Device**, so you can watch your library loans and renew them from Home Assistant.

> **Status: scaffold.** The integration is complete, but it currently talks to a **stub client** that returns deterministic fake loans. It does not contact NLB yet. A real client is planned as a follow-up (all NLB-specific code lives in `custom_components/nlb/api.py`).

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/crenz/ha-nlb` as an *Integration*.
2. Install **NLB Singapore** and restart Home Assistant.
3. **Settings → Devices & services → Add integration → NLB Singapore**.

Requires Home Assistant 2026.10 or newer.

## Accounts

Enter an NLB user ID and password. Add the integration again for each additional account; every account becomes its own Device. The same user ID cannot be added twice. With the stub client, an empty password or the password `invalid` is rejected.

If NLB later rejects the stored password, Home Assistant asks you to re-authenticate.

## Entities (per account)

| Entity | Description |
|---|---|
| `Loans` | Number of items currently on loan |
| `Overdue loans` | Number of loans whose due date is before today |
| `Days until next due` | Days until the earliest due date among loans that are not yet overdue (`unknown` if there are none) |

## Options

**Update interval** per account: 1-168 hours, default 12. Change it under the integration's *Configure* button.

## Action: `nlb.renew_all`

Renews every renewable loan. Pick one or more NLB devices as the target, or call it without a target to renew **all** accounts. It returns per-item results; items that cannot be renewed are reported as failed and do not raise an error.

```yaml
action: nlb.renew_all
target:
  device_id: <your NLB device>
response_variable: renewal
```

```yaml
# renewal
NLB alice:
  renewed: 2
  failed: 1
  items:
    - item_id: alice-0
      title: Stub Book 1
      success: true
      new_due_date: "2026-11-25"
      message: null
    - item_id: alice-2
      title: Stub Book 3
      success: false
      new_due_date: null
      message: Item cannot be renewed
```

Example automation: renew when something is due soon.

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.nlb_alice_days_until_next_due
    below: 3
actions:
  - action: nlb.renew_all
    target:
      device_id: <your NLB device>
```

## Development

Python 3.14 is required (managed with [uv](https://docs.astral.sh/uv/)).

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements_test.txt

.venv/bin/pytest                              # tests + coverage (>= 95%)
.venv/bin/ruff check . && .venv/bin/ruff format --check .
.venv/bin/mypy custom_components/nlb
```

See [SPEC.md](SPEC.md) for the specification and [tasks/plan.md](tasks/plan.md) for the plan.

## Not yet done

- The real NLB client (login, loans, renewals).
- Logo / brand images.
