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

**Empty / zero-denominator behavior**:
- When there are zero sessions in the last 30 days (so the denominator of
  `completion_rate_30d` would be zero), `completion_rate_30d` is `0.00`.
  It is **not** `NaN`, **not** `1.00`, and the command does **not** error.
  This applies equivalently when `sessions.json` is missing — absence is
  treated as the same zero state.
- `avg_minutes` follows the same convention: with zero completed sessions,
  it is `0.0` (not `NaN`).

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
