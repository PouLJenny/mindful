# mindful — Product Specification

## What This Is

A command-line meditation companion. Single-user, local-only, no network.
Stores all data in `~/.mindful/` as JSON files.

## Core Entities

- **Session**: One sit. Has duration, mode, start_time, end_time, status, optional note.
- **Streak**: Consecutive days with at least one completed session.
- **Config**: User preferences (bell sound, default duration, voice gender).

## Commands

### `mindful start`

**User view**: `mindful start --duration 10 --mode breath_pacing` shows a
countdown, plays guidance, and on completion records the session.

**Preconditions**:
- `~/.mindful/` writable (auto-created on first run)
- duration is 1–120 minutes
- mode is one of: bell_only, voice_guide, breath_pacing

**Expected behavior**:
- Creates session record with status=in_progress
- Plays guidance per mode
- On completion, marks status=completed, updates streak
- Returns session_id (printed to stdout)

**Streak rule — same-day completions** (pinned):
A second completed session on the **same calendar date** does NOT increment
`current_streak`. The streak counts consecutive *days* with at least one
completed session, not the number of completed sessions. Sessions on
day N+1 increment the streak by 1 (regardless of how many sessions were
completed on day N); sessions on day N do not change the count once it
already reflects day N. Rationale: the streak is a habit signal —
practising twice in one day proves consistency on that day, not on a
second day.

**Failure modes the product claims to handle**:
- Ctrl+C mid-session → save with status=interrupted, do NOT count toward streak
- duration > 120 → exit code 1, clear error message
- ~/.mindful/ not writable → exit code 3, name the directory and OS error
- Concurrent start (another in_progress exists) → reject, suggest resume/abort

**Ground truth (for unbeatable test)**:
- `~/.mindful/sessions.json` has +1 entry
- New entry has status="completed" or "interrupted"
- If completed: `~/.mindful/streak.json` updated correctly

---

### `mindful note`

**User view**: `mindful note "felt calm"` attaches text to the most recent
**completed** session.

**Preconditions**:
- At least one completed session exists
- Note is 1–500 chars

**Failure modes**:
- No prior session → error "no session to annotate"
- Note > 500 chars → reject with current count
- Note already exists → ask to overwrite, or `--force` to override
- Empty note → reject

**Ground truth**:
- `sessions.json` last completed entry has `note` field set

---

### `mindful stats`

**User view**: Prints five metrics — current_streak, longest_streak,
total_minutes, avg_minutes, completion_rate_30d — one per line, in that
order.

**Preconditions**: None — works with zero sessions, returns zeros.

**Output format** (pinned):
- One metric per line, in the exact order above (top-to-bottom).
- Each line is `<metric_name>: <value>`. Metric names appear **verbatim**
  (snake_case, lowercase, no humanisation). Whitespace between the colon
  and the value may be padded for column alignment but is not part of the
  contract.
- Value formatting:
  - `current_streak`, `longest_streak`, `total_minutes` — integer (e.g. `0`, `42`).
  - `avg_minutes` — float with one decimal place (e.g. `0.0`, `12.5`).
  - `completion_rate_30d` — fraction in `[0.00, 1.00]` with two decimal
    places (e.g. `0.00`, `0.83`). It is **not** a percentage.
- Lines are written to stdout. Warnings (corrupt data, etc.) go to stderr.

**`completion_rate_30d` denominator** (pinned):
The denominator is `started_in_last_30d` — the count of sessions whose
`start_time` falls within the last 30 days, regardless of final
`status`. It is **not** a constant (e.g., not 30 "expected sessions per
month") and **not** restricted to completed-only sessions (which would
make the rate always 1.00 by construction). When `started_in_last_30d`
is 0, `completion_rate_30d` is reported as `0.00`. Rationale: the
metric measures follow-through — of the sessions the user actually
started in the window, what fraction did they complete?

**Failure modes**:
- `sessions.json` corrupt → recover what's parseable, warn to stderr
- Timezone change between sessions → use UTC internally

**Ground truth**:
- stdout contains all 5 numeric metrics, one per line, in the pinned
  order, with the pinned formatting above.
- For corrupt data: warning to stderr, partial stats to stdout, exit 0.

**Side effects**: None. `mindful stats` is **read-only** — see
"Read-only commands" under Cross-cutting Constraints.

---

### `mindful history` (abbreviated — same pattern)

### `mindful config` (abbreviated — same pattern)

## Non-Goals (explicit)

- No cloud sync, accounts, social features
- No reminders/notifications
- mode/duration N/A to note/stats/config/history (see spec.blocked)

## Cross-cutting Constraints

- All times stored as UTC ISO8601
- All file writes are atomic (temp file + rename)
- Exit codes: 0=success, 1=user error, 2=data error, 3=system error

### Read-only commands

The following commands MUST NOT mutate `~/.mindful/` or its contents.
They read whatever exists and treat absence as zero state. They MUST NOT
create the `~/.mindful/` directory, `sessions.json`, or `streak.json` as
a side effect.

- `mindful stats`
- `mindful history` (and any future read-only flags such as
  `--last N`, `--since DATE`)
- `mindful config --get …` (read paths only; mutating forms such as
  `--bell-sound X` are NOT read-only by definition and may write the
  config file)

This is a hard contract — Layer-4 state-delta tests pin it. Any future
command added under this list inherits the same no-side-effect rule.
