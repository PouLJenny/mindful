# Kitchen Loop Report - Iteration 2

## Scenario: First-day round-trip — `stats` (empty) → `start` → `stats` (1 session) → `history`
**Date**: 2026-05-15
**Mode**: strategy
**Tier**: T2 Composition
**Features Exercised**:
- subcommand: `stats`, `start`, `history` (3/5)
- duration: `1min`
- mode: `bell_only`
- state_condition: `first_ever_session` → `active_streak`

## What I Did (as a user)

I approached this as a fresh user on day one — install the tool, look at my
stats before doing anything, then do a session, then check what changed.
This composes three subcommands across a state transition and pins the
stats output contract end-to-end for the first time.

Concrete steps (all run against a temp `$HOME` so they don't pollute the
real home directory):

1. **`mindful stats` on empty `$HOME`** — expected zeros, asserted the
   read-only contract (no `~/.mindful/` created):
   ```
   $ HOME=/tmp/x PYTHONPATH=src python3 -m mindful stats
   current_streak:      0
   longest_streak:      0
   total_minutes:       0
   avg_minutes:         0.0
   completion_rate_30d: 0.00
   $ ls /tmp/x          # still empty — good
   ```

2. **`mindful start --duration 1 --mode bell_only`** (under
   `MINDFUL_FAST_TICK=1` so the test takes a second, not a minute):
   ```
   starting 1min bell_only session — Ctrl+C to interrupt
   DING — session complete
   b9a7b930-2ac6-4ba9-8c57-bc65b9af78f6
   ```
   Confirmed `~/.mindful/sessions.json` and `streak.json` were created.

3. **`mindful stats` again** — expected the post-session state and got
   exactly the spec-pinned format:
   ```
   current_streak:      1
   longest_streak:      1
   total_minutes:       1
   avg_minutes:         1.0
   completion_rate_30d: 1.00
   ```

4. **`mindful history`** — expected the one session listed; got:
   ```
   2026-05-15T03:06:53.636214+00:00  1min  bell_only
   ```

5. **Probed a same-day second session**: ran `mindful start` a second
   time on the same calendar day and re-checked stats. `current_streak`
   stayed at `1` (correct — streaks count days, not sessions);
   `total_minutes` rose to `2`; `avg_minutes` stayed at `1.0`.

6. **Probed input-validation surface**:
   - `mindful stat` (typo) → argparse error + **exit 2**
   - `mindful note "hi"` (unimplemented) → exit 2 "invalid choice"
   - `mindful config --get foo` (unimplemented) → exit 2 "invalid choice"
   - `mindful` (no subcommand) → exit 0, prints help (friendly UX)

## What Worked

- **Stats output already matches the pinned spec format**. Both the zero
  state and the post-session state line up exactly with `docs/spec.md`
  "Output format (pinned)": metric order is correct, `avg_minutes` uses
  one decimal, `completion_rate_30d` uses two decimals and is a fraction
  in `[0, 1]` (not a percentage). The alignment padding after the colon
  is whitespace-only, which the spec explicitly tolerates.
- **The start → stats seam is correctly wired**. `streak.json` and the
  `sessions.json` envelope produced by `cmd_start` are read cleanly by
  `cmd_stats`; no schema drift between writer and reader. Same goes for
  `cmd_history`.
- **Same-day streak doesn't double-bump**. Two sessions on the same date
  leave `current_streak=1` (not 2). This behavior is now pinned by the
  new test — see "Implementation choices now pinned" below.
- **The L3 smoke test from iter-1 is still green** and the new L4
  scenario tests slot in cleanly alongside it (`pytest -x` → 10 passed).

## Friction Points

- **`mindful` is not on `PATH`**. Running the documented `mindful stats`
  command verbatim fails (`ModuleNotFoundError`); the test had to fall
  back to `python3 -m mindful` with `PYTHONPATH=src`. Already filed in
  iter-1 (`pip install -e .` blocked by Manjaro PEP 668). No action this
  iteration.
- **No shared `mindful_run` pytest fixture**. The new
  `test_first_day_round_trip.py` re-implements the same
  `_mindful_invocation()` + `_run()` helpers as
  `test_history_readonly_contract.py` and
  `test_start_emits_progress_signals.py`. That's the third copy. IMP-5
  (issue #17) already captures this; this iteration adds another
  duplicate to the tally.

## Bugs Found

**[BUG-3] argparse default exit code 2 contradicts `docs/spec.md` exit-code contract**

`docs/spec.md` § "Cross-cutting Constraints" pins exit codes:
> `0=success, 1=user error, 2=data error, 3=system error`

The implementation honors this only for *its own* validation paths
(`cmd_start` returns 1 for `--duration` out of range, 3 for unwritable
`~/.mindful/`). But every argparse-driven validation falls through to
argparse's default `SystemExit(2)`, which the spec reserves for *data
error*. A user-side typo is a USER error and should exit 1.

Reproduction (each below should be exit 1 per spec, but actually exits 2):
```
$ HOME=/tmp/x PYTHONPATH=src python3 -m mindful stat
usage: mindful [-h] COMMAND ...
mindful: error: argument COMMAND: invalid choice: 'stat' (choose from ...)
exit=2                               # spec says 1

$ HOME=/tmp/x PYTHONPATH=src python3 -m mindful start --duration abc --mode bell_only
mindful start: error: argument --duration: invalid int value: 'abc'
exit=2                               # spec says 1

$ HOME=/tmp/x PYTHONPATH=src python3 -m mindful start
mindful start: error: the following arguments are required: --duration, --mode
exit=2                               # spec says 1
```

Severity: low (machine-readability for downstream scripts; doesn't
affect interactive UX). Fix shape: subclass `argparse.ArgumentParser`
and override `error()` (and/or `exit()`) to `sys.exit(1)` instead of 2.
Apply to the top-level parser and each subparser. The fix is mechanical
but spans every `add_parser(...)` call, so it deserves a single
focused PR.

## Missing Features

**[FEAT-3 carry-over] `mindful note` subcommand**. Already filed as
issue #14. Confirmed by today's probe — `mindful note "hi"` falls
through argparse as "invalid choice". No new info; just confirming it's
still missing.

**[FEAT-5 carry-over] `mindful config` subcommand**. Already filed as
issue #16. Confirmed by today's probe — `mindful config --get foo` →
"invalid choice". No new info.

## Improvements

**[IMP-5 carry-over] Shared `mindful_run` pytest fixture**. Already
filed as issue #17. This iteration adds a third file
(`test_first_day_round_trip.py`) that re-implements the same
boilerplate. The duplication tax is now ~50 lines across three files
and growing.

## Implementation choices now pinned by the new test

A few decisions that the spec does NOT explicitly require but that
the implementation made — the new test now pins them so a future
"fix" doesn't silently break them:

- **Same-day sessions don't double-bump the streak.** The spec says
  "consecutive days with at least one completed session" but doesn't
  explicitly forbid a second same-day session from incrementing
  `current_streak`. The implementation skips the bump if
  `last_date == today`, which the new test now asserts.
  If the product later decides same-day sessions should each count
  as a streak day, this test would need to be updated.
- **`completion_rate_30d` denominator is the count of in-window
  sessions** (`completed` ÷ `started_in_last_30d`), not the count of
  *expected* sessions. Spec is silent; impl chose this; test pins it
  via the trivial `1/1 = 1.00` case but doesn't yet exercise a partial
  case (e.g., one completed + one interrupted in the window).

Both are reasonable defaults — flagging them as "now pinned" so future
PR reviewers know.

## Tests Added

- `tests/scenarios/test_first_day_round_trip.py` (new, 2 tests):
  - `test_first_day_round_trip` — composes
    `stats → start → stats → history → start (same-day) → stats`, asserts
    spec-pinned stats output at every step, the read-only contract for
    the first stats call, and the same-day no-double-bump behavior.
  - `test_stats_on_empty_home_is_read_only` — pins the read-only
    contract for `stats` across 3 repeated calls, mirroring the
    existing `test_history_readonly_contract.py` shape (and feeding
    the IMP-6 collapse target once it lands).

Run result:
```
$ PYTHONPATH=src pytest -x
Pytest: 10 passed
```
(All pre-existing 8 tests still pass; 2 new tests pass.)

The L3 smoke gate (`pytest tests/smoke/ -x`) also stays green:
```
$ PYTHONPATH=src pytest tests/smoke/ -x
Pytest: 3 passed
```

## Files Modified

- `tests/scenarios/test_first_day_round_trip.py` — new file (2 tests).
- `docs/internal/reports/iteration-2-report.md` — this report.
- `.kitchenloop/coverage-matrix.yaml` — added 4 new tested combos
  (start×active_streak, stats×first_ever_session, stats×active_streak,
  history×active_streak). `tested_combos: 1 → 5`, `coverage_pct: 0.83 → 4.17`.

## Outcome

**SUCCESS** — T2 composition scenario implemented, all tests green,
one new genuine bug found (BUG-3: argparse exit code violates spec).

Key value this iteration delivers:
1. **First L4 scenario that asserts the stats output contract
   end-to-end.** The spec format (one decimal for `avg_minutes`,
   two for `completion_rate_30d`, fraction not percentage, padded
   alignment after the colon) is now pinned by a regression test.
   Any future stats refactor that drifts will fail this test.
2. **First L4 that exercises the start → stats → history seam.** Up
   to now, each subcommand was tested in isolation; the seam was
   untested.
3. **First L4 that asserts the same-day no-double-bump streak
   behavior** — an implementation choice the spec is silent on.
4. **One real bug found** (BUG-3, argparse exit code 2 ≠ spec's
   exit code 1 for user errors). Independent of this scenario, would
   not have surfaced without manually probing the CLI as a user
   probably will.

## TIER

TIER: T2
