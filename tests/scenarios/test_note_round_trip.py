"""L4 scenario test — `mindful note` round-trip via sessions.json.

Pins FEAT-3 (issue #14): `mindful note "<text>"` attaches text to the
most-recent completed session, persisted to ~/.mindful/sessions.json
under the `note` field.

The T2 (composition) scenario is `start` → `note` → assert state delta:
the note must round-trip through sessions.json.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


_PROJECT_SRC = str(Path(__file__).resolve().parents[2] / "src")


def _mindful_invocation() -> list[str]:
    try:
        import mindful  # noqa: F401
        return [sys.executable, "-m", "mindful"]
    except ImportError:
        binary = shutil.which("mindful")
        if binary:
            return [binary]
        return [sys.executable, "-c", "from mindful.cli import main; main()"]


def _run(cmd: list[str], home: Path, fast_tick: bool = False, timeout: int = 30):
    pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = (
        f"{_PROJECT_SRC}{os.pathsep}{pythonpath}" if pythonpath else _PROJECT_SRC
    )
    env = {**os.environ, "HOME": str(home), "PYTHONPATH": pythonpath}
    if fast_tick:
        env["MINDFUL_FAST_TICK"] = "1"
    return subprocess.run(
        cmd, env=env, capture_output=True, text=True, timeout=timeout
    )


def _load_entries(home: Path) -> list[dict]:
    payload = json.loads((home / ".mindful" / "sessions.json").read_text())
    return payload["sessions"] if isinstance(payload, dict) else payload


def test_note_round_trip_after_start(tmp_path: Path):
    """start → note "felt calm" → sessions.json last entry has note set."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    start = _run(
        _mindful_invocation() + ["start", "--duration", "1", "--mode", "bell_only"],
        home=fake_home,
        fast_tick=True,
    )
    assert start.returncode == 0, f"start failed: {start.stderr!r}"

    note = _run(_mindful_invocation() + ["note", "felt calm"], home=fake_home)
    assert note.returncode == 0, (
        f"note exited {note.returncode}\nstderr: {note.stderr!r}"
    )

    entries = _load_entries(fake_home)
    assert len(entries) == 1
    assert entries[0].get("status") == "completed"
    assert entries[0].get("note") == "felt calm", (
        f"note did not round-trip: entry={entries[0]!r}"
    )


def test_note_with_no_completed_session_errors(tmp_path: Path):
    """note on an empty $HOME prints an error and exits non-zero."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    result = _run(_mindful_invocation() + ["note", "anything"], home=fake_home)

    assert result.returncode != 0, (
        f"expected non-zero exit, got {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert "no session" in result.stderr.lower(), (
        f"expected 'no session' message on stderr, got: {result.stderr!r}"
    )


def test_note_missing_arg_errors(tmp_path: Path):
    """`mindful note` (no positional arg) prints usage error to stderr, exits non-zero."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    result = _run(_mindful_invocation() + ["note"], home=fake_home)

    assert result.returncode != 0, (
        f"expected non-zero exit for missing arg, got {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    # argparse writes usage to stderr; "usage" or the prog name should appear
    assert result.stderr.strip(), "expected something on stderr for missing arg"


def test_note_too_long_rejects_with_count(tmp_path: Path):
    """note > 500 chars rejects with a message that includes the char count."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _ = _run(
        _mindful_invocation() + ["start", "--duration", "1", "--mode", "bell_only"],
        home=fake_home,
        fast_tick=True,
    )

    long_text = "x" * 501
    result = _run(
        _mindful_invocation() + ["note", long_text], home=fake_home
    )

    assert result.returncode != 0
    assert "501" in result.stderr, (
        f"expected char count (501) in stderr, got: {result.stderr!r}"
    )

    # State unchanged: no `note` field on the entry.
    entries = _load_entries(fake_home)
    assert "note" not in entries[0], (
        f"rejected note must not be persisted: {entries[0]!r}"
    )


def test_note_overwrite_requires_force(tmp_path: Path):
    """Existing note + no --force → reject. With --force → overwrite."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    _ = _run(
        _mindful_invocation() + ["start", "--duration", "1", "--mode", "bell_only"],
        home=fake_home,
        fast_tick=True,
    )

    first = _run(
        _mindful_invocation() + ["note", "first"], home=fake_home
    )
    assert first.returncode == 0

    no_force = _run(
        _mindful_invocation() + ["note", "second"], home=fake_home
    )
    assert no_force.returncode != 0, "expected refusal without --force"
    entries = _load_entries(fake_home)
    assert entries[0]["note"] == "first", (
        f"refusal must not overwrite: entry={entries[0]!r}"
    )

    forced = _run(
        _mindful_invocation() + ["note", "second", "--force"], home=fake_home
    )
    assert forced.returncode == 0, (
        f"--force should succeed, got {forced.returncode}: {forced.stderr!r}"
    )
    entries = _load_entries(fake_home)
    assert entries[0]["note"] == "second", (
        f"--force did not overwrite: entry={entries[0]!r}"
    )
