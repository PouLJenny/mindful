# Unbeatable Tests — mindful

> **Why this file exists**: The "unbeatable test" concept defines what L3
> integration looks like for *this* project. Without it, the regression gate
> only runs L1/L2 unit tests, which can pass while the real CLI is broken.

## Definition of L3 for `mindful`

An L3 test is one that:

1. Invokes the **installed `mindful` console script** (or `python -c "from
   mindful.cli import main; main()"` as a fallback) via **subprocess**.
2. Runs against a **real, isolated `~/.mindful/` directory** (a temp `HOME`),
   not a mock.
3. Asserts on the **state delta on disk** (`sessions.json`, `streak.json`),
   not just on stdout.

Mocking the filesystem, mocking subprocess, or asserting only on return values
of internal Python functions are explicitly **insufficient** for L3.

## The 4-layer pattern

Every L3 test must verify all four layers:

| Layer       | What it proves                              | Failure means                        |
|-------------|---------------------------------------------|--------------------------------------|
| 1. Compile  | Package + module imports cleanly            | Syntax error, missing dep            |
| 2. Execute  | Subprocess returns exit code 0              | CLI crashed or rejected valid input  |
| 3. Parse    | stdout has the expected token (session_id)  | Output contract drift                |
| 4. State    | Files on disk reflect the action            | Persistence broken — silent dataloss |

A passing L1+L2 unit test for `record_session()` proves **none** of these
end-to-end. That is the failure mode this file exists to prevent.

## Current smoke test

**Path**: `tests/smoke/test_smoke.py`
**Runs**: `pytest tests/smoke/ -x` (configured as `verification.oracle.quick_command` /
`smoke_command` in `kitchenloop.yaml`).

**Scenario covered**:
- `mindful start --duration 1 --mode bell_only` on a brand-new home
  (`state_condition=first_ever_session`)
- Verifies session is recorded with `status=completed`, correct `duration`
  and `mode`.

**Fast-tick contract** (must be honored by the implementation):

```
MINDFUL_FAST_TICK=1   # CLI treats `--duration N` minutes as N seconds
```

This contract is what makes the smoke test runnable as part of `pytest`
(seconds, not minutes). The implementation MUST gate this behind an env
variable so production users still get real minutes.

## What's still uncovered (file as L4 tickets)

- `mindful start` with `--mode voice_guide` and `--mode breath_pacing`
- Ctrl+C mid-session → `status=interrupted` and streak NOT advanced
- `mindful start` with `duration > 120` → exit code 1
- Non-writable `~/.mindful/` → exit code 3
- Concurrent `mindful start` while another `in_progress` exists → reject
- `mindful note` against most-recent completed session
- `mindful stats` on zero / corrupt / valid `sessions.json`
- `mindful history --last N`
- `mindful config --bell-sound X`

Each of these is a candidate L4 (single-feature scenario) test for future
iterations. The smoke test in this file deliberately covers only the **most
important happy path** so that it stays fast and is always run.
