# Kitchen Loop Review — Iterations 0 → 2

**Date**: 2026-05-15
**Reviewer**: loop-review (autonomous)
**Scope**: iter-0 (pre-loop skeleton, `7a032c3`) through iter-2 (current `kitchen/iter-2` branch)
**Inputs read**: `docs/internal/reports/iteration-1-report.md`, `docs/internal/reports/iteration-2-report.md`,
`docs/internal/loop-state.md`, `.kitchenloop/coverage-matrix.yaml`, `.kitchenloop/metrics.json`,
`.kitchenloop/unbeatable-tests.md`, `kitchenloop.yaml`, `scripts/kitchenloop/kitchenloop.sh`,
`scripts/kitchenloop/prompts/{ideate,regress}.md`, GitHub issues #1–#28, `git log`.

This review evaluates the **Kitchen Loop process itself** — not the `mindful` product. Findings are
categorised as **Blocker** (loop is silently losing work or producing wrong steering inputs),
**Important** (loop is functioning but accumulating measurable tax), or **Observation** (worth
noting, no action required). Per the run brief, Blocker and Important findings are auto-filed
as GitHub issues; Observations are recorded here only.

---

## Summary

| Iter | Date       | Tier | Tests at end | New bugs | Loop deliverable committed? |
|------|------------|------|--------------|----------|-----------------------------|
| 0    | 2026-05-05 | n/a  | 0            | n/a      | n/a — pre-loop skeleton     |
| 1    | 2026-05-05 | T1   | 3 (L3 smoke) | BUG-1, BUG-2 | **No, backfilled manually** (`55fa9b9`) |
| 2    | 2026-05-15 | T2   | 14           | BUG-3 (fixed) | **No, still uncommitted** at review time |

The loop is delivering real value — coverage growing, genuine bugs found and fixed, spec drift
being pinned — but its **auto-commit step is structurally broken**: the test files that are the
iteration's primary output are not being persisted. iter-1 papered over this with a manual
backfill commit; iter-2 has the same problem and there is currently no equivalent backfill.
This is the most important finding in the review.

---

## Findings

### LR-B1 — Auto-commit allowlist excludes the primary iteration deliverable  [**BLOCKER**]

**Evidence.**

- `scripts/kitchenloop/kitchenloop.sh:1214–1238` stages only four config-driven paths:
  `path_reports` (`docs/internal/reports/`), `path_scenarios` (`scenarios/incubating/`),
  `path_loop_state` (`docs/internal/loop-state.md`), `path_patterns` (`memory/codebase-patterns.md`).
- At the moment of this review, `git status` on `kitchen/iter-2` shows:
  ```
  modified:   .kitchenloop/coverage-matrix.yaml
  Untracked:  tests/scenarios/test_first_day_round_trip.py
  ```
  Both the ideate auto-commit (`db8ab73`) and the regress auto-commit (`515f718`) already ran
  for iter-2. `515f718 --stat` shows only `docs/internal/loop-state.md` and
  `memory/codebase-patterns.md` were captured. The iteration's L4 scenario test — the most
  visible deliverable described in `iteration-2-report.md` — is not in the branch.
- iter-1 had the identical problem. The operator manually committed the missing artifacts in
  `55fa9b9` (titled literally *"kitchenloop iter-1 missing artifacts: tests scaffold + state files"*,
  394 insertions across `tests/`, `kitchenloop.yaml`, `.kitchenloop/`). The auto-commit code was
  not updated after that manual fix, so the same omission recurred in iter-2.

**Impact.** If iter-3 branches fresh from `main` (the standard worktree pattern), all of
iter-2's test additions, the coverage-matrix update, and any state-file changes disappear.
Coverage growth and L4 regression value silently leak out between iterations.

**Recommendation.** Add `tests/` to the auto-commit allowlist, plus an explicit entry for
`.kitchenloop/coverage-matrix.yaml` (and any other ideate-mutable state under `.kitchenloop/`
that should persist). Alternatively, switch the allowlist semantics from "stage these paths"
to "stage everything except `.kitchenloop/state/*.counter` and other runtime-only files."

**Filed as GitHub issue** (loop-improvement, label `kitchenloop:meta`).

---

### LR-I1 — PEP 668 / editable-install friction is now permanent  [**IMPORTANT**]

**Evidence.**

- iter-1 friction point: "`pip install -e .` blocked by Manjaro PEP 668" → workaround
  `PYTHONPATH=src python3 -m mindful` for every test.
- iter-2 carry-over: "`mindful` is not on PATH … No action this iteration."
- `memory/codebase-patterns.md` now codifies the workaround as a *pattern* ("confirmed by 2+
  iterations"), which silently promotes a transient operational issue to project-architectural truth.
- Every L3/L4 test file re-implements `_mindful_invocation()` with a three-tier fallback
  (`-m mindful` → `shutil.which("mindful")` → `python -c "from mindful.cli import main; main()"`)
  to paper over the same root cause.

**Impact.** Each new test pays the boilerplate cost. The "pattern" hides the underlying fix
(use a project-local venv, pipx, `uv`, or document the workaround as the supported invocation).
A new contributor reading `codebase-patterns.md` will treat the workaround as canonical rather
than as debt.

**Recommendation.** Either (a) commit a one-time fix — a `scripts/dev-setup.sh` that creates
a clean local venv with `pip install -e .` inside it, plus a `Makefile` target — or (b) update
`docs/spec.md` and `README.md` to make `python -m mindful` the documented invocation, then
simplify `_mindful_invocation()` to a single line. Pick one and stop carrying the friction.

**Filed as GitHub issue** (loop-improvement).

---

### LR-I2 — Coverage matrix denominator counts non-existent dimensions  [**IMPORTANT**]

**Evidence.** `kitchenloop.yaml`'s `spec.blocked` list omits combinations that `docs/spec.md`
already makes impossible:

| Subcommand | What `spec.md` actually says            | Coverage matrix dimensions counted | Phantom combos |
|------------|-----------------------------------------|------------------------------------|----------------|
| `note`     | takes `<text>`, no duration             | 4 dur × 5 state = 20               | 15             |
| `history`  | takes `--last N --since DATE`, no duration | 4 dur × 5 state = 20            | 15             |
| `config`   | takes `--get/--set/--bell-sound`, no mode | 3 mode × 5 state = 15            | 10             |

True spec-surface denominator is approximately **80**, not 120. Current `coverage_pct = 5/120 =
4.17 %`; corrected it is `5/80 = 6.25 %`.

**Impact.** ideate's "biggest gap" tie-breaker selects scenarios partly by coverage gap. A
40-combo phantom denominator biases the prompt toward chasing combos that literally cannot
exist (e.g., `note × duration × state_condition`). That is wasted ideation budget at best,
and at worst will be filed as ideate-rejected combos that pollute the backlog.

**Recommendation.** Extend `kitchenloop.yaml: spec.blocked` to include:
```yaml
- subcommands: note
  duration: "*"
- subcommands: history
  duration: "*"
- subcommands: config
  mode: "*"
```
and regenerate `coverage-matrix.yaml` totals.

**Filed as GitHub issue** (loop-improvement).

---

### LR-I3 — Test boilerplate duplicated five times despite IMP-5 / #17  [**IMPORTANT**]

**Evidence.** `_mindful_invocation()` + `_run()` helpers are copy-pasted across:
1. `tests/smoke/test_smoke.py`
2. `tests/scenarios/test_history_readonly_contract.py`
3. `tests/scenarios/test_start_emits_progress_signals.py`
4. `tests/scenarios/test_first_day_round_trip.py` (iter-2)
5. `tests/scenarios/test_exit_code_contract.py` (iter-2 spin-off PR #28)

IMP-5 (issue #17, "Add `tests/conftest.py` with `mindful_run` fixture") was filed in iter-1 and is
still `kitchenloop:todo` after two iterations. Each ideate cycle adds another copy.

**Impact.** Cumulative duplication tax (~50 lines × 5 files). Worse, a non-trivial change to
the invocation contract (e.g., adding a new env var, or switching to `pipx`-style install per LR-I1)
now requires editing five locations in lockstep — exactly the brittleness pattern the kitchen loop
is supposed to detect.

**Recommendation.** Elevate #17's priority and have execute phase land it before iter-3's
ideate begins. Alternatively, codify in the ideate prompt: "if test boilerplate is being copied
for the 3rd+ time, the first deliverable of this iteration is the dedup, not the new scenario."

**Filed as GitHub issue** (loop-improvement).

---

### LR-I4 — `.kitchenloop/metrics.json` stops at iter-1  [**IMPORTANT**]

**Evidence.** `metrics.json` contains only one entry (iter-1, 3 tests, T1).
`docs/internal/loop-state.md` records iter-2 with 14 tests, T2, BUG-3 — but `metrics.json` was
never updated. `regress.md` (the phase responsible) does not mention `metrics.json` at all;
its Step 4 only updates `docs/internal/loop-state.md`.

**Impact.** `metrics.json` is the only machine-readable history file. Trend analysis (test count
trajectory, tier balance enforcement, pass-rate floor evaluation in
`scripts/kitchenloop/kitchenloop.sh` line ~130) reads JSON, not prose. After five iterations
this file will still claim only iter-1 ever ran.

**Recommendation.** Add a Step 4.5 to `regress.md`: append a new entry to `metrics.json` with
`num`, `ts`, `test_total`, `test_passed`, `test_failed`, `test_skipped`, `pass_rate`, `tier`.
The schema is already established by the iter-1 entry.

**Filed as GitHub issue** (loop-improvement).

---

### LR-O1 — iter-0 is a pre-loop bootstrap, not a loop iteration  [observation]

iter-0 (commit `7a032c3`, May 5 12:24) predates the kitchenloop tooling itself (`89a9250`,
May 5 22:16). It correctly serves as the baseline that iter-1 inherits.

Strengths the loop inherits from iter-0:
- `docs/spec.md` is unusually well-shaped for a freshly-bootstrapped repo: ground truth defined
  per command, exit codes pinned, non-goals explicit. iter-1's report flags this as a notable
  enabler.
- `pyproject.toml [project.scripts] mindful = "mindful.cli:main"` is wired before any tests
  exist, so the L3 smoke test could be written against a known entry point.

Weakness the loop inherits from iter-0:
- No `tests/` directory. iter-1 had to bootstrap it. Not a loop bug — but worth recording
  that "spec quality + missing tests" is the failure mode the kitchen loop is *most* effective
  against (one iteration to bootstrap, then linear coverage growth).

No action.

---

### LR-O2 — iter-2 found a real bug outside its declared scenario  [observation]

iter-2's scoped scenario was T2 round-trip (`stats → start → stats → history`). BUG-3 (argparse
exit-code violation) came from a side-quest: the model manually probed typo/invalid-int inputs,
explicitly encouraged by `ideate.md` Step 4.4 ("Try edge cases a real user might hit"). The
finding led to a clean PR (#28) and a new regression test (`test_exit_code_contract.py`).

This is a strength. Keep the prompt instruction. Consider promoting "probe at least 2 invalid
inputs as a user would" from an aside to an explicit sub-step, so it isn't accidentally dropped
when the report skeleton is filled in.

No action.

---

### LR-O3 — Spec-vs-implementation drift was caught by iter-2; needs IMP-7 to land  [observation]

iter-2 wrote tests that pin two undocumented implementation choices:
- same-day sessions don't double-bump the streak;
- `completion_rate_30d = completed / started_in_last_30d` (not `/ expected`).

`docs/spec.md` is silent on both. IMP-7 (#25) was filed to update the spec, currently
`kitchenloop:in-review`. Until it lands, a future "spec-faithful" refactor could legitimately
break a pinned test.

The pattern itself (iteration-N's tests find an implementation behavior the spec didn't mandate,
so iteration-N files a spec-update ticket) is a healthy loop behavior. The fix is procedural,
not structural; no separate loop-process issue.

No action.

---

### LR-O4 — Stop-condition thresholds are still in "early loop" mode  [observation]

`kitchenloop.yaml` keeps `pass_rate_floor: 0.80` (with a comment `跑稳后改 0.95`, "tighten to
0.95 once stable"). After two iterations at 100 %, this floor is loose enough that a 20 %
regression would not trip the gate. Consider tightening once iter-3 lands.

No action this review — this is a tuning decision the operator should make, not a process bug.

---

### LR-O5 — TIER tag is the only structured signal emitted by ideate reports  [observation]

Both reports end with `TIER: T1` / `TIER: T2`. The orchestrator parses this. Consider adding
parallel machine-readable lines: `BUGS_FOUND: N`, `TESTS_ADDED: N`, `COMBOS_ADDED: N`. This
would let the regress phase (or a future review phase) populate `metrics.json` mechanically
rather than re-reading prose.

No action this review — adjacent to LR-I4's fix and could be addressed together.

---

## Filed loop-improvement tickets (this review)

| Finding | Severity  | GitHub issue |
|---------|-----------|--------------|
| LR-B1   | Blocker   | [#29](https://github.com/PouLJenny/mindful/issues/29) |
| LR-I1   | Important | [#30](https://github.com/PouLJenny/mindful/issues/30) |
| LR-I2   | Important | [#31](https://github.com/PouLJenny/mindful/issues/31) |
| LR-I3   | Important | [#32](https://github.com/PouLJenny/mindful/issues/32) |
| LR-I4   | Important | [#33](https://github.com/PouLJenny/mindful/issues/33) |

Observations LR-O1 – LR-O5 are intentionally NOT filed as tickets per the run brief.

---

## What the loop is doing well

Worth recording these so they don't get optimised away when the items above are fixed:

- **Priority-Zero L3 bootstrap** worked exactly as designed. iter-1 saw an empty
  `smoke_command` and correctly devoted the whole iteration to bootstrapping the test, instead
  of chasing a scenario into a regression-gateless void.
- **Probing-as-a-user** discovered BUG-3 (real CLI contract violation) outside the chosen
  scenario. The prompt's "try edge cases" sub-step is paying off.
- **Spec-drift pinning** is becoming a per-iteration habit. iter-2 pinned the stats output
  format (an existing spec contract that had never been tested end-to-end) AND surfaced two
  undocumented behaviors for spec follow-up.
- **`codebase-patterns.md` ≥2-iter rule** is being honored — the file is short and contains
  only patterns confirmed by both iterations. LR-I1 above is a critique of one *content*
  choice, not of the process.

The loop is producing genuine engineering value. The action items in this review are about
making sure that value is actually captured in git history and reflected in the steering
metrics — not about changing the loop's core behavior.
