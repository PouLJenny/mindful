# Codebase Patterns — mindful

Patterns confirmed by 2+ iterations of the Kitchen Loop. Speculative patterns
do not belong here. If an entry is contradicted by later evidence, update or
remove it.

## Testing

### Use `PYTHONPATH=src python3 -m mindful` for invocation
The system Python and `.venv` cannot do a clean `pip install -e .` because
Manjaro enforces PEP 668. Existing editable installs in `.venv` point to
stale worktrees and break tests when invoked via the `mindful` shim on PATH.
Every test that subprocesses the CLI must fall back to
`python -c "from mindful.cli import main; main()"` (which is what
`tests/smoke/test_smoke.py:_mindful_invocation()` does) and pytest itself
must be invoked with `PYTHONPATH=src`. Confirmed iter-1 (bootstrap), iter-2
(stats/history scenarios).

### `MINDFUL_FAST_TICK=1` collapses minute durations to seconds
Internal test contract: when the env var is set, `mindful start --duration N`
treats N as seconds rather than minutes. Lets `--duration 1` finish a smoke
test in ~1s instead of 60s. Documented in `.kitchenloop/unbeatable-tests.md`.
Established iter-1; reused iter-2.

### Tests must run against a temp `$HOME`
The CLI writes to `~/.mindful/{sessions.json,streak.json}`. Tests that don't
override `HOME` to a `tmp_path` will pollute the operator's real home dir
and produce nondeterministic results. Pattern in
`tests/smoke/test_smoke.py` and `tests/scenarios/test_*.py`. Confirmed
both iterations.

## Specification

### Spec is the contract; tests pin it; implementation can drift silently
`docs/spec.md` defines exit codes (0/1/2/3), output formats (e.g., stats
output with one-decimal `avg_minutes`, two-decimal `completion_rate_30d`
as a fraction), and read-only commands. Implementation may quietly drift
from the spec (iter-2 found BUG-3: argparse default exit 2 vs spec's exit 1
for user errors). Pattern: every iteration should pin at least one
previously-unpinned spec contract via an L4 scenario test. Iter-1 pinned
the L3 happy path; iter-2 pinned stats output format end-to-end and the
exit-code contract.

## Architecture

### `cmd_start` writes; `cmd_stats` and `cmd_history` are pure readers
The start/stats/history seam is wired such that `cmd_start` is the sole
writer of `sessions.json` and `streak.json`; the read commands never touch
them. Two iterations have composed across this seam without schema drift —
the readers parse cleanly what the writer produces. If a future change
introduces a second writer, this invariant should be re-verified.
