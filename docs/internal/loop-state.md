# Kitchen Loop — Shared State

This file is shared mutable state across loop phases. Re-read before writing
in any phase — other phases may have modified it during the same iteration.

## Current Iteration

- **Iteration**: 2
- **Date**: 2026-05-15
- **Mode**: strategy
- **Tier**: T2 Composition
- **Base branch**: main
- **Branch**: kitchen/iter-2

## Test Results (this iteration)

- **Suite**: full (`PYTHONPATH=src pytest`)
- **Total**: 14
- **Passed**: 14
- **Failed**: 0
- **Skipped**: 0
- **Pass rate**: 100.0%
- **L3 smoke**: PASS (3/3 — `pytest tests/smoke/ -x`)
- **Lint**: PASS (`ruff check .`)

## Coverage Snapshot

- **Total combos in spec surface**: 120
- **Tested combos**: 5
- **Coverage**: 4.17%
- **New combos this iteration**: 4
  - `start × 1min × bell_only × active_streak`
  - `stats × N/A × N/A × first_ever_session`
  - `stats × N/A × N/A × active_streak`
  - `history × 1min × N/A × active_streak`

## Iteration History

| Iter | Date       | Mode     | Tier | Tests (L1/L2) | L3 Smoke | New Bugs       | Status |
|------|------------|----------|------|---------------|----------|----------------|--------|
| 1    | 2026-05-05 | strategy | T1   | 1/1 (RED→GREEN over phases) | bootstrapped | — | OK |
| 2    | 2026-05-15 | strategy | T2   | 14/14         | PASS     | BUG-3 (argparse exit code; fixed in #28) | OK |

## Blocked Combos

(none discovered this iteration)

## Stop Conditions

- Pass rate floor: ✅ 100% (well above any reasonable floor)
- Test count trend: ✅ growing (1 → 14)
- Consecutive failures: ✅ 0

## Environment Notes

- `pytest` alone (without `PYTHONPATH=src`) collides with a stale editable
  install in `.venv` pointing to a deleted worktree (`.claude/worktrees/pr-26`).
  All test invocations must use `PYTHONPATH=src` until the editable install
  is refreshed or replaced. Recorded in iter-1 and iter-2 reports; tracked
  in iter-1 as the "`pip install -e .` blocked by Manjaro PEP 668" friction.
