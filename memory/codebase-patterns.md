# Codebase Patterns — mindful

> Patterns CONFIRMED by ≥ 2 iterations of empirical evidence (or removed
> if contradicted). Speculative patterns do not belong here.
>
> First populated 2026-05-05 (iteration 1). Most entries are PROVISIONAL
> until iteration 2 either confirms or contradicts.

## Testing patterns

### L3 4-layer pattern is the contract for this project (PROVISIONAL — 1 iter)

Every L3 test must verify all four layers in order:

1. **Compile** — `import mindful; import mindful.cli` (catches syntax /
   missing dep).
2. **Execute** — invoke the installed `mindful` console script via
   `subprocess`, assert `returncode == 0`.
3. **Parse** — assert stdout contains the expected token (e.g. session id
   regex, all 5 metric names).
4. **State** — assert `~/.mindful/sessions.json` (or `streak.json`) on
   disk reflects the action; for read-only commands, assert these files
   are NOT created.

`tests/smoke/test_smoke.py` and `tests/integration/test_stats_zero_sessions.py`
both follow this pattern. Any future L3 test should too. Promote to
CONFIRMED if iteration 2 adds a third L3 test that follows the same shape
without revision.

### `MINDFUL_FAST_TICK=1` is the test-time-acceleration contract (PROVISIONAL)

Because real meditation sessions are minutes long, the L3 smoke test
needs the CLI to honor `MINDFUL_FAST_TICK=1` and treat `--duration N`
minutes as `N` seconds. Documented in `.kitchenloop/unbeatable-tests.md`.
Any new time-gated subcommand (e.g. `breath_pacing`) must respect the
same env-var contract or the smoke test cannot exercise it.

### Override `HOME` to a `tmp_path`, not the real filesystem (PROVISIONAL)

Both existing L3 tests follow `env={"HOME": str(tmp_path / "home"), ...}`
to isolate `~/.mindful/` per test. This avoids polluting the developer's
real home and lets tests assert on file presence/absence without
cleanup. Pattern shared verbatim between smoke and integration tests.

## Infrastructure patterns

### Worktrees share a single venv → editable install pins to one branch (DISCOVERED iter 1)

The repo uses a shared `.venv/` across all `.claude/worktrees/*` worktrees.
Whichever worktree most recently ran `pip install -e .` "wins": all other
worktrees `import mindful` from that worktree's `src/`, regardless of
which worktree pytest is invoked from.

**Symptom**: tests in worktree A pass GREEN even though A's `src/mindful/`
is a stub, because the venv resolves `mindful` to worktree B's
implementation.

**Mitigation** (until properly fixed):
- After switching worktrees, re-run `pip install -e .` from the
  current worktree before trusting any test result, OR
- Create a per-worktree venv.

This was the headline regress finding for iteration 1. Promote to
CONFIRMED if it bites a second iteration without being fixed.

## Architecture patterns

(none confirmed yet — too early)

## Error patterns

(none confirmed yet — too early)
