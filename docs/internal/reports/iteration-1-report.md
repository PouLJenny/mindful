# Kitchen Loop Report - Iteration 1 (re-run)

## Scenario: `stats` reflects a just-completed `start` AND stays read-only on empty state
**Date**: 2026-05-15
**Mode**: strategy
**Tier**: T2 Composition
**Features Exercised**:
- `subcommands=start` × `duration=1min` × `mode=breath_pacing` × `state_condition=first_ever_session`
- `subcommands=stats` × `state_condition=active_streak` (just-completed session)
- `subcommands=stats` × `state_condition=first_ever_session` (zero state — read-only contract)

## Priority Zero Check
- `tests/smoke/test_smoke.py` already exists and is wired to `verification.oracle.smoke_command`.
- Confirmed `pytest tests/smoke/ -x` passes (3/3) using the project venv.
- L3 smoke bootstrap is already done — proceeded to a T2 scenario as the natural next step.

## What I Did (as a user)

1. **Verified the smoke test passes** with the existing implementation (`start` + `stats`
   already merged via commits `6e8f229`, `2330781`, `af47d77`).
2. **Hand-ran the empty-home stats case**:
   ```
   $ HOME=/tmp/xxx mindful stats
   current_streak:      0
   longest_streak:      0
   total_minutes:       0
   avg_minutes:         0.0
   completion_rate_30d: 0.00
   $ ls /tmp/xxx/
   (empty)   ← no ~/.mindful created. Read-only contract honored.
   ```
3. **Hand-ran the composition** `start --duration 1 --mode breath_pacing` followed by
   `stats`. With `MINDFUL_FAST_TICK=1`, the 1-minute session completes in ~1 second,
   and the next `stats` call reports:
   ```
   current_streak:      1
   longest_streak:      1
   total_minutes:       1
   avg_minutes:         1.0
   completion_rate_30d: 1.00
   ```
4. **Exercised three error edge cases** as a clumsy user would:
   - `--mode bell-only` (dash instead of underscore) → exit 1, clear message
   - `--duration 200` → exit 1, clear range message
   - `--duration 0` → exit 1, clear range message
5. **Exercised the corrupt-data branch**: planted `{not valid json` into
   `~/.mindful/sessions.json`, then ran `stats`. Got the expected warning to stderr,
   zero metrics to stdout, exit 0 — matches `docs/spec.md`'s "recover what's
   parseable" contract.
6. **Wrote four L4 tests** at `tests/scenarios/test_stats_compose.py` that pin the
   behavior verified by hand: zero state formatting, read-only contract,
   `start → stats` composition, and "stats does not mutate state on repeat".
7. Confirmed the full suite is green: **9 passed in 4.29s**.

## What Worked

- **Spec contract is precise enough to test directly.** `docs/spec.md` pins the
  metric names verbatim, the value formatting (1 decimal vs 2 decimal), the
  ordering, and the read-only contract — I translated each clause into an
  assertion without ambiguity.
- **`MINDFUL_FAST_TICK=1` is a sound test contract.** It lets a 1-minute session
  run inside `pytest` in ~1 second, which made the composition test cheap to
  iterate on.
- **`start` already writes to disk atomically** (via `_atomic_write` in
  `cli.py`), so I never observed a partially-written `sessions.json` even when
  killing the process between steps. Good defensive default for a CLI that may
  be `Ctrl+C`'d mid-session.
- **`stats` already honors the read-only contract.** It uses `path.exists()`
  guards instead of unconditional `mkdir` — exactly what the spec requires.

## Friction Points

- **`pytest` from system Python fails out of the box.** The smoke test installs
  `mindful` into `.venv` but `which pytest` points to a pyenv shim that doesn't
  see it. A new contributor running `pytest` will hit `ModuleNotFoundError: No
  module named 'mindful'`. The contract that works is "use the project venv's
  pytest" — but it's not documented anywhere. Filing as IMP-1.
- **No `~/.mindful/` cleanup helper for tests.** Every L4 test invents its own
  `tmp_path / "home"` boilerplate plus `HOME` env munging plus `PYTHONPATH`
  setup. A pytest fixture `mindful_home` would shrink each test by ~15 lines
  and centralize the "real CLI with isolated HOME" pattern. Filing as IMP-2.
- **`completion_rate_30d` is `0.00` on an empty home, but the spec describes
  it as `(completed within 30d) / (total within 30d)`.** That's `0/0` — the
  implementation chooses to return `0.0` for that edge case (reasonable), but
  the spec is silent on it. Filing as IMP-3 (spec clarification).

## Bugs Found

None — the composition and read-only contract both work as the spec describes.
The implementation matches the spec on every assertion I made.

## Missing Features

**[FEAT-1] `mindful` is missing the remaining documented subcommands.**
- `note "text"` — annotate the most recent completed session (spec'd, branch
  `kitchen/fix-14-note-cmd` exists, not merged)
- `history --last N` — list recent sessions (spec'd, branch `kitchen/fix-15-history-cmd`
  exists, not merged)
- `config --bell-sound X` — adjust preferences (spec'd, branch
  `kitchen/fix-16-config-cmd` exists, not merged)

These are visible as un-merged branches in `git branch -a`. Future iterations
can pick from this backlog directly. Once they land, the natural T2 composition
to cover next is `start → note → stats → history`.

## Improvements

**[IMP-1] Document the `pytest` invocation that actually works.**

Either:
- Add a `Makefile` / `task` target that wraps the venv'd pytest, OR
- Add a one-line "Running the tests" section to `README.md` that says
  `.venv/bin/pytest` (or `python -m pytest` after `pip install -e .` into the
  project venv).

Without this, a new contributor will hit `ModuleNotFoundError` and assume
the test harness is broken.

**[IMP-2] Add a `tests/conftest.py` with a `mindful_home` fixture.**

Suggested signature:
```python
@pytest.fixture
def mindful_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MINDFUL_FAST_TICK", "1")
    return home
```

Eliminates the duplicated `HOME` / `PYTHONPATH` setup boilerplate in every
L4 scenario test (smoke + the two scenarios files currently each re-invent it).

**[IMP-3] Pin `completion_rate_30d` zero-denominator behavior in `docs/spec.md`.**

The current implementation returns `0.00` when there are zero sessions in
the last 30 days. The spec should explicitly say so, otherwise a future
"clarification" PR could legitimately change it to `1.00` or `nan` and
silently break callers.

## Tests Added

- `tests/scenarios/test_stats_compose.py` (new, 4 tests, all GREEN):
  - `test_stats_on_empty_home_prints_zeros_in_pinned_order` — pins the
    5-metric output format on zero state (integer/1-decimal/2-decimal).
  - `test_stats_on_empty_home_does_not_create_mindful_dir` — Layer-4
    state-delta assertion: read-only contract on empty HOME.
  - `test_start_breath_pacing_then_stats_reflects_session` — the
    composition assertion: a 1-minute completed `breath_pacing` session
    produces `total_minutes=1`, `current_streak=1`, `completion_rate_30d=1.00`.
  - `test_stats_after_start_remains_read_only` — running `stats` twice
    after a `start` must not mutate `sessions.json` or `streak.json`.

Full suite: **9 passed in 4.29s**.

## Outcome

**SUCCESS** — T2 composition delivered. We now have:
- The pinned `stats` output format under regression coverage.
- The `mindful stats` read-only contract enforced by a Layer-4 disk assertion
  (the spec's most subtle invariant — easy to break, hard to notice).
- A second `mode` value (`breath_pacing`) exercised end-to-end, in addition
  to the smoke's `bell_only`.

Coverage matrix grew from 1 → 5 combos this iteration.

## TIER

TIER: T2
