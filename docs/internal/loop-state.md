# Kitchen Loop — Shared State

This file is **shared mutable state** across all phases (ideate / execute / regress)
of the Kitchen Loop. Re-read before editing; do not rely on a stale in-memory copy.

## Current Iteration

- **Iteration**: 1
- **Mode**: strategy
- **Base branch**: main
- **Worktree**: `.claude/worktrees/kitchen-iter-1`
- **Started**: 2026-05-15

## Latest Regress Result (Iteration 1)

- **Pre-flight**: ruff `All checks passed` (via `uvx ruff check .`)
- **L1/L2 (full pytest)**: 12 passed, 0 failed, 0 skipped — pass rate **100%**
- **L3 smoke (`tests/smoke/`)**: 3/3 passed — **PASS**
- **New failures**: none
- **Stop conditions**: all clear

## Coverage Snapshot

From `.kitchenloop/coverage-matrix.yaml` (worktree-local; root copy lacks
`backlog.json`):

- Total combos in spec surface: **120**
- Combos tested so far (per matrix `tested_combos`): **1**
- Coverage: **0.83%**

Note: the matrix is stale relative to the iteration-1 report, which exercised
3 additional `(subcommand × duration × mode × state_condition)` combos
(`stats × — × — × first_ever_session`, `stats × — × — × active_streak`,
`start × 1min × breath_pacing × first_ever_session`) plus three for `history`
exercised by the new `test_history_readonly_contract.py`. Ideate phase should
reconcile the matrix on the next iteration.

## Iteration History

| Iter | Mode     | L1/L2 (passed/total) | L3 Smoke | Pass Rate | Notes |
|------|----------|----------------------|----------|-----------|-------|
| 1    | strategy | 12 / 12              | PASS     | 100%      | Bootstrapped L3 + T2 stats composition + history read-only contract. |

## Blocked / Known Issues

- **IMP-1** (filed in iter-1 report): `pytest` from system Python `ModuleNotFoundError`
  unless `pip install -e .` is run into the active interpreter (the project venv at
  the repo root is not auto-activated inside this worktree). Regress phase had to
  install `mindful` editable into the pyenv python before tests could run.
- **IMP-2**: missing `mindful_home` pytest fixture — every L4 test re-implements
  the `HOME`/`PYTHONPATH`/`MINDFUL_FAST_TICK` setup.
- **IMP-3**: `completion_rate_30d` zero-denominator (`0/0 → 0.00`) is implemented
  but unspec'd.

## New Blocked Combos Discovered This Iteration

None. All combos exercised behaved as the spec describes.
