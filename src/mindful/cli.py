"""mindful CLI entry point.

Subcommands implemented:
  - start: run a session, persist it to ~/.mindful/sessions.json
  - stats: print 5 metrics; read-only (does not mutate ~/.mindful/)

The MINDFUL_FAST_TICK=1 env var makes `start --duration N` sleep N seconds
instead of N minutes — used by the L3 smoke test so it runs in seconds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

VALID_MODES = ("bell_only", "voice_guide", "breath_pacing")
HOME_SUBDIR = ".mindful"
SESSIONS_FILE = "sessions.json"
STREAK_FILE = "streak.json"
CONFIG_FILE = "config.json"

CONFIG_DEFAULTS: dict[str, str] = {
    "bell_sound": "default",
    "duration_default": "10",
    "voice_gender": "neutral",
}


class _UserErrorArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that exits with status 1 (user error) on parse failure.

    The stock argparse uses status 2, but the spec reserves 2 for **data
    error**; argument validation failures are user errors → 1.
    """

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def _mindful_dir() -> Path:
    return Path.home() / HOME_SUBDIR


def _atomic_write(path: Path, data: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data)
    os.replace(tmp, path)


def _load_sessions(path: Path) -> tuple[list[dict], bool]:
    """Return (entries, was_corrupt)."""
    if not path.exists():
        return [], False
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return [], True
    if isinstance(raw, dict) and isinstance(raw.get("sessions"), list):
        return raw["sessions"], False
    if isinstance(raw, list):
        return raw, False
    return [], True


def _save_sessions(path: Path, sessions: list[dict]) -> None:
    _atomic_write(path, json.dumps({"sessions": sessions}, indent=2))


def _load_streak(path: Path) -> dict:
    if not path.exists():
        return {"current": 0, "longest": 0, "last_date": None}
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"current": 0, "longest": 0, "last_date": None}
    if not isinstance(raw, dict):
        return {"current": 0, "longest": 0, "last_date": None}
    raw.setdefault("current", 0)
    raw.setdefault("longest", 0)
    raw.setdefault("last_date", None)
    return raw


def _save_streak(path: Path, streak: dict) -> None:
    _atomic_write(path, json.dumps(streak, indent=2))


def _bump_streak(streak: dict, today: date) -> dict:
    last = streak.get("last_date")
    today_iso = today.isoformat()
    if last == today_iso:
        pass
    elif last is None:
        streak["current"] = 1
    else:
        try:
            delta = (today - date.fromisoformat(last)).days
        except (ValueError, TypeError):
            delta = None
        if delta == 1:
            streak["current"] = int(streak.get("current", 0)) + 1
        else:
            streak["current"] = 1
    streak["last_date"] = today_iso
    streak["longest"] = max(int(streak.get("longest", 0)), int(streak["current"]))
    return streak


def cmd_start(args: argparse.Namespace) -> int:
    if args.duration < 1 or args.duration > 120:
        print(
            f"error: --duration must be between 1 and 120 minutes (got {args.duration})",
            file=sys.stderr,
        )
        return 1
    if args.mode not in VALID_MODES:
        print(
            f"error: --mode must be one of {', '.join(VALID_MODES)} (got {args.mode!r})",
            file=sys.stderr,
        )
        return 1

    home = _mindful_dir()
    try:
        home.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create {home}: {exc}", file=sys.stderr)
        return 3

    sessions_file = home / SESSIONS_FILE
    streak_file = home / STREAK_FILE

    sessions, was_corrupt = _load_sessions(sessions_file)
    if was_corrupt:
        backup = sessions_file.with_suffix(f".corrupt-{int(time.time())}")
        sessions_file.replace(backup)
        print(f"warning: corrupt sessions.json backed up to {backup.name}", file=sys.stderr)
        sessions = []
    for entry in sessions:
        if entry.get("status") == "in_progress":
            print(
                "error: another session is already in progress; "
                "resume or abort it before starting a new one",
                file=sys.stderr,
            )
            return 1

    session_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc).isoformat()
    new_entry = {
        "id": session_id,
        "duration": args.duration,
        "mode": args.mode,
        "status": "in_progress",
        "start_time": start_time,
    }
    sessions.append(new_entry)
    try:
        _save_sessions(sessions_file, sessions)
    except OSError as exc:
        print(f"error: cannot write {sessions_file}: {exc}", file=sys.stderr)
        return 3

    fast_tick = os.environ.get("MINDFUL_FAST_TICK") == "1"
    seconds = args.duration if fast_tick else args.duration * 60

    print(
        f"starting {args.duration}min {args.mode} session "
        f"— Ctrl+C to interrupt",
        flush=True,
    )

    interrupted = False
    try:
        time.sleep(seconds)
    except KeyboardInterrupt:
        interrupted = True

    end_time = datetime.now(timezone.utc).isoformat()
    sessions, _ = _load_sessions(sessions_file)
    for entry in sessions:
        if entry.get("id") == session_id:
            entry["status"] = "interrupted" if interrupted else "completed"
            entry["end_time"] = end_time
            break
    _save_sessions(sessions_file, sessions)

    if not interrupted:
        streak = _load_streak(streak_file)
        streak = _bump_streak(streak, date.today())
        _save_streak(streak_file, streak)
        print("DING — session complete", flush=True)
    else:
        print("session interrupted", flush=True)

    print(session_id)
    return 0


def _within_30d(iso: str | None, now: datetime) -> bool:
    if not iso:
        return False
    try:
        dt = datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (now - dt).days <= 30


def cmd_stats(args: argparse.Namespace) -> int:
    home = _mindful_dir()
    sessions_file = home / SESSIONS_FILE
    streak_file = home / STREAK_FILE

    sessions: list[dict] = []
    corrupt = False
    if sessions_file.exists():
        sessions, corrupt = _load_sessions(sessions_file)
        if corrupt:
            print(
                f"warning: {sessions_file} is unreadable; reporting partial stats",
                file=sys.stderr,
            )

    streak = {"current": 0, "longest": 0, "last_date": None}
    if streak_file.exists():
        streak = _load_streak(streak_file)

    completed = [s for s in sessions if s.get("status") == "completed"]
    total_minutes = sum(int(s.get("duration", 0) or 0) for s in completed)
    avg_minutes = (total_minutes / len(completed)) if completed else 0.0

    now = datetime.now(timezone.utc)
    last_30 = [s for s in sessions if _within_30d(s.get("start_time"), now)]
    if last_30:
        completion_rate_30d = sum(
            1 for s in last_30 if s.get("status") == "completed"
        ) / len(last_30)
    else:
        completion_rate_30d = 0.0

    current = int(streak.get("current", 0) or 0)
    longest = int(streak.get("longest", 0) or 0)

    print(f"current_streak:      {current}")
    print(f"longest_streak:      {longest}")
    print(f"total_minutes:       {total_minutes}")
    print(f"avg_minutes:         {avg_minutes:.1f}")
    print(f"completion_rate_30d: {completion_rate_30d:.2f}")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """Print completed sessions in chronological order. Read-only.

    Per the read-only contract (spec.md "Read-only commands"), this MUST
    NOT create ~/.mindful/, sessions.json, or any sibling on disk.
    """
    home = _mindful_dir()
    sessions_file = home / SESSIONS_FILE

    sessions: list[dict] = []
    corrupt = False
    if sessions_file.exists():
        sessions, corrupt = _load_sessions(sessions_file)
        if corrupt:
            print(
                f"warning: {sessions_file} is unreadable; "
                f"showing partial history",
                file=sys.stderr,
            )

    completed = [s for s in sessions if s.get("status") == "completed"]
    completed.sort(key=lambda s: s.get("start_time") or "")

    for entry in completed:
        start = entry.get("start_time") or "?"
        duration = entry.get("duration", "?")
        mode = entry.get("mode") or "?"
        print(f"{start}  {duration}min  {mode}")
    return 0


def _load_config(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def cmd_config(args: argparse.Namespace) -> int:
    """`mindful config --get <key>` (read-only) | `--set <key> <value>` (write)."""
    home = _mindful_dir()
    config_file = home / CONFIG_FILE

    if args.get is not None:
        key = args.get[0]
        if key not in CONFIG_DEFAULTS:
            print(
                f"error: unknown config key {key!r}; "
                f"valid keys: {', '.join(sorted(CONFIG_DEFAULTS))}",
                file=sys.stderr,
            )
            return 1
        # Read-only path: NO mkdir, NO file creation.
        config = _load_config(config_file)
        print(config.get(key, CONFIG_DEFAULTS[key]))
        return 0

    if args.set is not None:
        key, value = args.set
        if key not in CONFIG_DEFAULTS:
            print(
                f"error: unknown config key {key!r}; "
                f"valid keys: {', '.join(sorted(CONFIG_DEFAULTS))}",
                file=sys.stderr,
            )
            return 1
        try:
            home.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            print(f"error: cannot create {home}: {exc}", file=sys.stderr)
            return 3
        config = _load_config(config_file)
        config[key] = value
        try:
            _atomic_write(config_file, json.dumps(config, indent=2, sort_keys=True))
        except OSError as exc:
            print(f"error: cannot write {config_file}: {exc}", file=sys.stderr)
            return 3
        return 0

    # argparse's mutually_exclusive_group(required=True) prevents this in
    # practice, but keep the branch defensive.
    print("error: config requires --get <key> or --set <key> <value>", file=sys.stderr)
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = _UserErrorArgumentParser(
        prog="mindful",
        description="A command-line meditation companion.",
    )
    sub = parser.add_subparsers(
        dest="cmd",
        metavar="COMMAND",
        parser_class=_UserErrorArgumentParser,
    )

    p_start = sub.add_parser("start", help="Start a meditation session")
    p_start.add_argument(
        "--duration",
        type=int,
        required=True,
        help="Session length in minutes (1-120)",
    )
    p_start.add_argument(
        "--mode",
        required=True,
        help=f"One of: {', '.join(VALID_MODES)}",
    )

    sub.add_parser("stats", help="Show meditation stats (read-only)")
    sub.add_parser("history", help="List completed sessions (read-only)")

    p_config = sub.add_parser("config", help="Get / set user preferences")
    cfg_group = p_config.add_mutually_exclusive_group(required=True)
    cfg_group.add_argument(
        "--get",
        metavar="KEY",
        nargs=1,
        help="Print the value for KEY (read-only)",
    )
    cfg_group.add_argument(
        "--set",
        metavar=("KEY", "VALUE"),
        nargs=2,
        help="Set KEY to VALUE (writes ~/.mindful/config.json atomically)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "start":
        rc = cmd_start(args)
    elif args.cmd == "stats":
        rc = cmd_stats(args)
    elif args.cmd == "history":
        rc = cmd_history(args)
    elif args.cmd == "config":
        rc = cmd_config(args)
    else:
        parser.print_help()
        rc = 0
    sys.exit(rc)


if __name__ == "__main__":
    main()
