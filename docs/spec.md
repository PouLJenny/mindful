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

**User view**: Prints current_streak, longest_streak, total_minutes,
avg_minutes, completion_rate_30d as a table.

**Preconditions**: None — works with zero sessions, returns zeros.

**Failure modes**:
- `sessions.json` corrupt → recover what's parseable, warn to stderr
- Timezone change between sessions → use UTC internally

**Ground truth**:
- stdout contains all 5 numeric metrics
- For corrupt data: warning to stderr, partial stats to stdout, exit 0

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
