"""L3 integration smoke test for mindful.

Follows the 4-layer pattern:
  1. Compile  — package imports
  2. Execute  — `mindful start ...` runs end-to-end via subprocess
  3. Parse    — stdout produces a session_id token
  4. State    — ~/.mindful/sessions.json gains a completed entry

Contract with the implementation:
  MINDFUL_FAST_TICK=1  — when set, the CLI treats `--duration N` minutes as
  N seconds so the smoke test completes in seconds rather than minutes.
  This is an internal test contract; documented in
  .kitchenloop/unbeatable-tests.md.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SESSION_ID_RE = re.compile(r"[0-9a-fA-F-]{8,}")


def _mindful_invocation() -> list[str]:
    """Resolve how to invoke the mindful CLI in this environment."""
    binary = shutil.which("mindful")
    if binary:
        return [binary]
    return [sys.executable, "-c", "from mindful.cli import main; main()"]


# ---------- Layer 1: Compile ----------

def test_layer1_compile_package_imports():
    """Package imports cleanly — no syntax errors, no missing deps."""
    import importlib

    mindful = importlib.import_module("mindful")
    assert mindful is not None
    cli = importlib.import_module("mindful.cli")
    assert hasattr(cli, "main"), "mindful.cli must expose main()"


# ---------- Layer 2 + 3 + 4: Execute, Parse, State Deltas ----------

def test_layer234_start_session_end_to_end(tmp_path: Path):
    """`mindful start --duration 1 --mode bell_only` records a completed session."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    env = {
        **os.environ,
        "HOME": str(fake_home),
        "MINDFUL_FAST_TICK": "1",  # treat minutes as seconds for tests
    }

    cmd = _mindful_invocation() + [
        "start",
        "--duration", "1",
        "--mode", "bell_only",
    ]

    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # --- Layer 2: Execute -------------------------------------------------
    assert result.returncode == 0, (
        f"mindful start exited {result.returncode}\n"
        f"stdout: {result.stdout!r}\n"
        f"stderr: {result.stderr!r}"
    )

    # --- Layer 3: Parse ---------------------------------------------------
    assert SESSION_ID_RE.search(result.stdout), (
        f"expected a session id in stdout, got: {result.stdout!r}"
    )

    # --- Layer 4: State Deltas -------------------------------------------
    sessions_file = fake_home / ".mindful" / "sessions.json"
    assert sessions_file.exists(), (
        f"expected {sessions_file} to be created"
    )

    sessions = json.loads(sessions_file.read_text())
    # Accept either a list or a {"sessions": [...]} envelope; we want exactly
    # one new entry from this run.
    if isinstance(sessions, dict) and "sessions" in sessions:
        entries = sessions["sessions"]
    else:
        entries = sessions

    assert isinstance(entries, list), f"sessions.json must contain a list, got {type(entries)}"
    assert len(entries) == 1, f"expected exactly 1 session entry, got {len(entries)}"

    entry = entries[0]
    assert entry.get("status") == "completed", (
        f"expected status=completed, got entry={entry!r}"
    )
    assert entry.get("duration") in (1, "1"), (
        f"expected duration=1, got entry={entry!r}"
    )
    assert entry.get("mode") == "bell_only", (
        f"expected mode=bell_only, got entry={entry!r}"
    )


# ---------- Sanity: --help works ----------

def test_cli_help_does_not_crash():
    """`mindful --help` returns 0 and mentions 'start' subcommand."""
    cmd = _mindful_invocation() + ["--help"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, (
        f"mindful --help exited {result.returncode}: {result.stderr!r}"
    )
    assert "start" in result.stdout.lower(), (
        f"--help should mention 'start', got: {result.stdout!r}"
    )
