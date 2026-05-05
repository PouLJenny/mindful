# Kitchen Loop State

> Shared mutable state across phases (ideate → triage → execute → polish →
> regress). Re-read before any write — phases mutate this between turns.

## Current Iteration

- **Iteration**: 1
- **Mode**: strategy
- **Branch**: `kitchen/iter-1`
- **Base**: `main`
- **Worktree**: `.claude/worktrees/kitchen-iter-1`
- **Last regress**: 2026-05-05

## Latest Regress Snapshot (iter 1)

- **Lint**: ruff WARN — 1× F401 (unused `pytest` import) in
  `tests/smoke/test_smoke.py:26`. Non-blocking.
- **Tests (L1/L2 + L3)**: 5 passed, 0 failed, 0 skipped, 5 total — pass
  rate 100% (floor 0.80, well above).
- **Smoke (L3)**: 3/3 PASS via `pytest tests/smoke/ -x`.
- **Security**: scan not configured (`verification.oracle.security_command`
  is empty).
- **Pass rate trend**: N/A (first iteration).

### CRITICAL FINDING — Cross-worktree contamination

The `mindful` package imported by pytest resolves to
`/home/poul/workspace/src/mindful/.claude/worktrees/pr-8/src/mindful/cli.py`,
**not** this worktree's `src/mindful/cli.py`.

```
$ /home/poul/workspace/src/mindful/.venv/bin/python -c \
    "import mindful, inspect; print(inspect.getsourcefile(mindful))"
/home/poul/workspace/src/mindful/.claude/worktrees/pr-8/src/mindful/__init__.py
```

Why: the shared `.venv` was created via `pip install -e` from the `pr-8`
worktree, so the editable-install link points there. This worktree's
`src/mindful/cli.py` is still a `NotImplementedError` stub. Tests pass
GREEN only because pr-8 happens to have a real implementation.

**Impact**: the regression gate is **not actually validating this branch's
code**. Any breakage introduced in `kitchen/iter-1` would not be caught by
`pytest`, because pytest is exercising pr-8's installed copy.

**How to apply**: ideate phase next iteration must surface this as a
top-priority infra bug. Recommended fix: each worktree should either
(a) get its own venv, or (b) re-run `pip install -e .` after entering the
worktree so the editable link is rewired. Until then, every pass on
this branch should be treated as suspect.

## Coverage

- **Total combos** (cartesian product of dimensions, minus blocked): 120
- **Tested combos**: 2 (1.67%)
- **New combos this iteration**: 2
  - `start` × `1min` × `bell_only` × `first_ever_session` (T1, smoke)
  - `stats` × N/A × N/A × `first_ever_session` (T1, integration)
- **Smoke (L3)**: configured (`pytest tests/smoke/ -x`); 1 scenario covered.

## Iteration History

| Iter | Mode      | L1/L2 | L3 smoke | Lint | New combos | Notes                                                       |
|------|-----------|-------|----------|------|------------|-------------------------------------------------------------|
| 1    | strategy  | 5/5   | 3/3 PASS | WARN | 2          | First iter; cross-worktree contamination flagged (see above) |

(No earlier iterations — this is the first regress run for the loop.)

## Stop Conditions Status

- Pass-rate floor (0.80): **OK** (1.00).
- Consecutive failures (max 3): **0**.
- Test-count trend declining: **N/A** (insufficient history).
- All clear → loop continues.

## Open Blocks / Carry-overs

- **Cross-worktree venv contamination** (this iteration's headline) — see
  CRITICAL FINDING above. Treat all green tests as suspect on this branch
  until rewired.
- **BUG-1**: `src/mindful/cli.py` in this worktree is a stub. Real
  implementation lives on `kitchen/fix-2-cli-implementation` /
  `pr-8` and is not merged here. Either merge or rewire venv.
- **IMP-3** (carry-over): pin `mindful stats` output format in
  `docs/spec.md`.
- **IMP-4** (carry-over): document read-only commands explicitly in
  `docs/spec.md`.
- **IMP-1, IMP-2** (carry-over): add `[tool.pytest.ini_options]` and
  `src/mindful/__main__.py` shim.

## Pointers

- Coverage matrix: `.kitchenloop/coverage-matrix.yaml`
- L3 contract: `.kitchenloop/unbeatable-tests.md`
- Iteration report: `docs/internal/reports/iteration-1-report.md`
- Patterns: `memory/codebase-patterns.md`
