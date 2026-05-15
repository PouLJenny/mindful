# Codebase Patterns — mindful

Patterns confirmed across **2+ Kitchen Loop iterations**. Iteration 1 is the
first observation pass; nothing is promoted to a pattern yet. Future iterations
will populate this file once a behavior re-appears.

## Candidate observations from Iteration 1 (NOT yet patterns)

These were observed once. They become patterns only if iter-2+ confirms them.

- **Read-only commands honor the contract via `path.exists()` guards.** `mindful stats`
  and `mindful history` both check the home dir before any read; they never
  unconditionally `mkdir` or `touch`. — observed in `src/mindful/cli.py`.
- **`MINDFUL_FAST_TICK=1` is the test-shortcut convention.** Lets a 1-minute
  session run in ~1 second under pytest. Used by both smoke and scenario tests.
- **`_atomic_write` (in `cli.py`) is the disk-write primitive.** Writes to a
  `.tmp` sibling then renames; survives `Ctrl+C` mid-write.
- **L4 scenario tests invoke the CLI as a subprocess with isolated `HOME`.**
  Every test under `tests/scenarios/` re-implements the `tmp_path / "home"` +
  `monkeypatch.setenv("HOME", ...)` boilerplate (filed as IMP-2).

## Confirmed patterns

_(none yet — requires 2nd iteration to confirm)_
