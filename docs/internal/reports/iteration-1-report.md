# Kitchen Loop Report - Iteration 1

## Scenario: `mindful stats` on a brand-new home (zero-sessions happy path)
**Date**: 2026-05-05
**Mode**: strategy
**Tier**: T1 Foundation
**Features Exercised**: subcommands=stats, duration=N/A (blocked), mode=N/A (blocked), state_condition=first_ever_session

## Iteration context

Priority Zero (L3 smoke bootstrap) was satisfied by a previous run of this
iteration: `tests/smoke/test_smoke.py` exists and `kitchenloop.yaml` →
`verification.oracle.smoke_command` is wired to it. The smoke test currently
goes RED on layers 2-4 (CLI is a `NotImplementedError` stub) — that is
intended: execute phase will turn it GREEN.

This run picks up the **next-most-valuable** scenario for the regression
gate: a second L3-style integration test exercising a *different subcommand
and a different state-condition* than the smoke. That widens the safety net
before any production code exists, so when the execute phase implements
`mindful start` it cannot accidentally break `mindful stats` (and vice
versa). Both tests are deliberately RED until execute phase.

## What I Did (as a user)

I am a brand-new user who has just installed `mindful`. I have never
meditated with this tool. Per `docs/spec.md`, `mindful stats` is documented
as having **no preconditions** — "works with zero sessions, returns zeros".
That is a strong promise; the natural first thing a curious user does is
poke at the subcommands without sitting first. So I set out to exercise
exactly that.

1. Read `docs/spec.md` § `mindful stats`. Confirmed the spec says:
   - **Preconditions**: None — works with zero sessions, returns zeros.
   - **Ground truth**: stdout contains all 5 numeric metrics
     (`current_streak`, `longest_streak`, `total_minutes`, `avg_minutes`,
     `completion_rate_30d`).
   - **Exit code**: 0 (success) even with no data.
2. Tried to actually run it:
   ```
   $ HOME=/tmp/mindful-fresh-home /home/poul/workspace/src/mindful/.venv/bin/mindful stats
   Traceback (most recent call last):
     File ".../mindful/cli.py", line 2, in main
       raise NotImplementedError("mindful CLI not built yet — KitchenLoop will fill this in")
   NotImplementedError: mindful CLI not built yet — KitchenLoop will fill this in
   ```
   Exit code 1, no JSON files written. Same blocker as BUG-1 from the
   bootstrap report — the CLI is a stub.
3. Wrote `tests/integration/test_stats_zero_sessions.py` — a 4-layer L3
   test that codifies the spec's promise:
   - Layer 1 (Compile): `mindful.cli` imports.
   - Layer 2 (Execute): `mindful stats` exits 0 on a fresh `$HOME`.
   - Layer 3 (Parse): stdout mentions all 5 documented metric names.
   - Layer 4 (State): stats is read-only — `~/.mindful/sessions.json`
     and `~/.mindful/streak.json` are *not* created (or, if created,
     contain empty/zero state). This is a state-delta assertion of the
     "no preconditions, no side effects" property.
4. Ran `pytest -x` and confirmed the new test goes RED for the same
   reason as the smoke test — `NotImplementedError`. Layer 1 passes.
5. Updated `.kitchenloop/coverage-matrix.yaml` to add the new combo and
   re-counted the coverage percentage.

## What Worked

- **Spec is self-consistent and testable.** The "zero-sessions returns
  zeros" promise is precisely the kind of low-bar invariant that makes a
  great L3 test: easy to express, hard to silently regress.
- **`HOME` indirection works**. The smoke test's pattern of overriding
  `$HOME` to a `tmp_path` carries over verbatim, so the new test reuses
  the same fixture style with no plumbing changes.
- **`pyproject.toml` script entry already in place**, so the
  `shutil.which("mindful")` resolution works the moment `cli.py` is
  implemented.

## Friction Points

- **CLI is still a stub.** Same blocker as BUG-1 — every documented
  command crashes with `NotImplementedError`. Cannot smoke any scenario
  end-to-end until execute phase lands `mindful start` (and at least
  enough scaffolding to make `mindful stats` return zeros).
- **Spec doesn't pin the table format.** "Prints current_streak,
  longest_streak, total_minutes, avg_minutes, completion_rate_30d as a
  table" — but does not pin column ordering, separators, or whether
  metric names appear verbatim. I wrote the assertion as
  *"all five metric names appear somewhere in stdout"* (case-insensitive
  substring match), which is the loosest contract that still proves the
  table is complete. Filing as IMP-3 to tighten the spec.
- **Spec doesn't say what files the zero-sessions case is allowed to
  create.** Strict reading of "no preconditions" implies the command can
  run before `~/.mindful/` exists — but does it create the directory and
  empty `sessions.json` as a side effect? I assumed **no**:
  `mindful stats` should not mutate disk state. Documented this assumption
  in the test and as IMP-4 to clarify in the spec.
- **No `python -m mindful` shim still.** Carried over from prior
  iteration's IMP-2 — both smoke and integration tests fall back to
  `python -c "from mindful.cli import main; main()"` when `mindful`
  isn't on `PATH`.

## Bugs Found

**[BUG-1] (carry-over) `mindful` CLI is unimplemented — every command crashes with `NotImplementedError`**

Already filed in prior iteration's report. Re-confirmed: `mindful stats`,
`mindful start`, `mindful note`, `mindful history`, `mindful config` all
exit 1 with `NotImplementedError`. Will be cleared by execute phase.

## Missing Features

**[FEAT-3] `mindful stats` zero-state behavior**

When `~/.mindful/sessions.json` does not exist, `mindful stats` must:
- Exit 0.
- Print all five metrics (`current_streak`, `longest_streak`,
  `total_minutes`, `avg_minutes`, `completion_rate_30d`) with value `0`
  (or `0.0` for `completion_rate_30d`).
- Not create `sessions.json` or `streak.json` as a side effect (read-only
  command).

Spec says "works with zero sessions, returns zeros" but does not pin the
side-effect rule. This iteration codifies the no-side-effect interpretation
in `tests/integration/test_stats_zero_sessions.py`.

## Improvements

**[IMP-3] Pin `mindful stats` output format in the spec**

Currently `docs/spec.md` says only "as a table". To make the L3 test
contract robust against trivial UI changes, the spec should pin:
- Whether metric names appear verbatim or as labels (e.g.
  `current_streak: 0` vs `Current Streak │ 0`).
- The five metric names (already named — keep them).
- Whether `completion_rate_30d` is a percentage (`0.0%`) or a fraction
  (`0.0`).

**[IMP-4] Spec read-only commands explicitly**

`mindful stats`, `mindful history`, `mindful config --get` should be
documented as **read-only**: they must not create or modify files. This
makes Layer-4 state-delta assertions trivially pinable.

**[IMP-1, IMP-2] (carry-over)** Add `[tool.pytest.ini_options]` and
`src/mindful/__main__.py`. Still applicable.

## Tests Added

- `tests/integration/__init__.py` (new, empty package marker)
- `tests/integration/test_stats_zero_sessions.py` (new, 1 main test
  covering all 4 layers for `mindful stats` first-ever-session):
  - `test_stats_zero_sessions_all_four_layers` — currently RED, expected
    to turn GREEN once execute phase ships `mindful stats`.

The smoke test (`tests/smoke/test_smoke.py`) is unchanged.

## Coverage Delta

- Before this run: 1 / 120 combos (0.83%).
- After this run: 2 / 120 combos (1.67%).
- New combo: `subcommands=stats`, `duration=N/A`, `mode=N/A`,
  `state_condition=first_ever_session`.

## Outcome

**SUCCESS** — A second L3 integration test now exists in the regression
gate, broadening coverage from one (`start`/`bell_only`/`first_ever_session`)
to two distinct subcommand × state combos. Both tests are RED today,
which is the desired pre-execute state: each will turn GREEN
independently as the corresponding subcommand is implemented, and either
turning RED again later will fail the regression gate immediately.

## TIER

TIER: T1
