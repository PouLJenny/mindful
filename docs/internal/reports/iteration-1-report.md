# Kitchen Loop Report - Iteration 1

## Scenario: Bootstrap L3 Smoke Test — `mindful start --duration 1 --mode bell_only`
**Date**: 2026-05-05
**Mode**: strategy
**Tier**: T1 Foundation (Priority Zero — L3 smoke bootstrap)
**Features Exercised**: subcommands=start, duration=1min, mode=bell_only, state_condition=first_ever_session

## What I Did (as a user)

I approached this as a brand-new user trying to follow the `README.md` happy
path: install the tool and run `mindful start --duration 1 --mode bell_only`.

1. Read `README.md` and `docs/spec.md` — clear single-page spec, exit codes
   defined, ground truth defined per command. Good.
2. Checked the `kitchenloop.yaml` and confirmed `verification.oracle.smoke_command`
   was empty (`""`). Per the loop's Priority Zero rule, this means the entire
   iteration must focus on bootstrapping the L3 integration smoke test.
3. Tried to use the CLI:
   - `python -c "from mindful.cli import main; main()"` → `ModuleNotFoundError`
     (package not installed in system Python).
   - `pip install -e .` → externally-managed-environment error
     (Manjaro/PEP 668).
   - `.venv/bin/mindful` → ran, but only because the venv had it pre-installed.
     Output:
     ```
     NotImplementedError: mindful CLI not built yet — KitchenLoop will fill this in
     ```
4. Wrote `tests/smoke/test_smoke.py` covering all 4 layers (Compile / Execute /
   Parse / State Deltas) for the chosen scenario. Established the
   `MINDFUL_FAST_TICK=1` env contract so the test can run in seconds rather
   than waiting a real minute.
5. Ran `pytest tests/smoke/ -x` → as expected, layer 1 (compile) passes,
   layers 2–4 fail because the CLI is a stub. This is the desired RED state
   that the execute phase will turn GREEN.
6. Updated `kitchenloop.yaml` → `verification.oracle.smoke_command: "pytest tests/smoke/ -x"`.
7. Wrote `.kitchenloop/unbeatable-tests.md` documenting the L3 definition,
   the 4-layer pattern, the fast-tick contract, and a backlog of L4 scenarios.
8. Created `.kitchenloop/coverage-matrix.yaml` with the dimensional total and
   this iteration's covered combo.

## What Worked

- **Spec quality**. `docs/spec.md` is the right size: explicit ground truth
  per command, explicit exit codes, explicit failure modes, explicit
  non-goals. This is unusually good for a freshly-bootstrapped repo and
  made test design straightforward.
- **`pyproject.toml` is already wired**. `[project.scripts] mindful = "mindful.cli:main"`
  means once `cli.py` is implemented, the smoke test will pick up the
  console script automatically — no plumbing changes needed.
- **Layer 1 (compile) passes today**. The package imports cleanly, so we
  immediately get value from the smoke test even before the CLI is built:
  any future syntax error or import-time failure is caught by layer 1.

## Friction Points

- **No `tests/` directory at all** in the worktree skeleton. Pytest had no
  rootdir-anchored test tree. Created `tests/__init__.py` and
  `tests/smoke/__init__.py` to make this explicit.
- **No `pytest` configuration** in `pyproject.toml`. Pytest auto-discovered
  the rootdir but a `[tool.pytest.ini_options]` block with `testpaths = ["tests"]`
  would make the intent clearer. Filing as IMP-1.
- **No way to run the CLI under `pytest` in real time**. A `--duration 1`
  session is a 60-second wall-clock wait, which is incompatible with a
  fast smoke test. I had to invent a contract (`MINDFUL_FAST_TICK=1`) and
  document it in `unbeatable-tests.md` so the execute phase honors it.
  Filing as FEAT-1.
- **Single user-facing entrypoint is undocumented for testability**. There's
  no `python -m mindful` shim — the smoke test falls back to
  `python -c "from mindful.cli import main; main()"`, which is awkward.
  Filing as IMP-2.

## Bugs Found

**[BUG-1] `mindful` CLI is unimplemented — every command crashes with `NotImplementedError`**

Reproduction:
```
$ .venv/bin/mindful start --duration 1 --mode bell_only
Traceback (most recent call last):
  File ".../mindful/src/mindful/cli.py", line 2, in main
    raise NotImplementedError("mindful CLI not built yet — KitchenLoop will fill this in")
```

Severity: blocker (this is by design for the skeleton, but every documented
command in `README.md` and `docs/spec.md` is currently non-functional).
The bootstrap L3 smoke test (this iteration's deliverable) will turn from
RED → GREEN once execute phase implements the spec.

## Missing Features

**[FEAT-1] `MINDFUL_FAST_TICK` env var to compress test wall-clock**

Description: To run the L3 smoke test inside `pytest` (and thus inside the
regression gate), the implementation MUST honor an env var that compresses
N-minute durations to N-second durations. This is the standard "test clock"
pattern. Documented in `.kitchenloop/unbeatable-tests.md`. The execute phase
implementing `mindful start` should gate the sleep/timer logic on this env
var.

**[FEAT-2] `mindful` is missing every documented subcommand**

Description: `start`, `note`, `stats`, `history`, `config` are all spec'd in
`docs/spec.md` but none exist. Each is a future iteration. Backlog
candidates already enumerated in `.kitchenloop/unbeatable-tests.md` under
"What's still uncovered".

## Improvements

**[IMP-1] Add `[tool.pytest.ini_options]` section to `pyproject.toml`**

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
```

Makes pytest invocation reliable across CI/local without `--rootdir` games.

**[IMP-2] Add `src/mindful/__main__.py`** so users (and tests) can invoke
the CLI as `python -m mindful` without the awkward
`python -c "from mindful.cli import main; main()"` fallback. Two-line file:

```python
from mindful.cli import main
if __name__ == "__main__":
    main()
```

**[IMP-3] `.kitchenloop/` and `kitchenloop.yaml` are not in the worktree**

These live in the main repo dir and aren't tracked by git. The instructions
told me to update them, which I did — but a more disciplined setup would
either commit them (so iteration-to-iteration state is visible in PRs) or
keep them in a sibling `.kitchenloop/state/` that's clearly out-of-tree.
Not blocking, just a foot-gun for future maintainers.

## Tests Added

- `tests/__init__.py` (new, empty package marker)
- `tests/smoke/__init__.py` (new, empty package marker)
- `tests/smoke/test_smoke.py` (new, 3 tests):
  - `test_layer1_compile_package_imports` — currently PASSES
  - `test_layer234_start_session_end_to_end` — currently FAILS (RED, expected)
  - `test_cli_help_does_not_crash` — currently FAILS (RED, expected)

## Files Modified Outside the Worktree (KitchenLoop state)

- `/home/poul/workspace/src/mindful/kitchenloop.yaml` — set
  `verification.oracle.smoke_command: "pytest tests/smoke/ -x"`
- `/home/poul/workspace/src/mindful/.kitchenloop/unbeatable-tests.md` — new file
- `/home/poul/workspace/src/mindful/.kitchenloop/coverage-matrix.yaml` — new file

## Outcome

**SUCCESS** — Priority Zero deliverable complete:
1. ✓ L3 smoke test exists and is wired into `kitchenloop.yaml`.
2. ✓ The test follows the 4-layer pattern (Compile / Execute / Parse / State).
3. ✓ Layer 1 already passes today; layers 2–4 RED as expected, will turn
     GREEN once execute phase implements `mindful start`.
4. ✓ `unbeatable-tests.md` defines L3 for this project and lists L4 backlog.
5. ✓ Coverage matrix initialized with one iteration's coverage entry.

The regression gate (`pytest`) now meaningfully covers the
"38 passing unit tests, completely broken service" anti-pattern: any future
unit test passing while `mindful start` is broken end-to-end will be caught
by `tests/smoke/test_smoke.py`.

## TIER

TIER: T1
