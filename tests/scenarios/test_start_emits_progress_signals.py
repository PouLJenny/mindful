"""L4 scenario test — `mindful start` emits visible progress to stdout.

Pins BUG-2 (issue #13): a `start` session must emit a banner before the
sleep and a completion signal after, so the user can tell the process is
alive and when it finishes. Without this, a 30-minute session looks
indistinguishable from a hung process until the very end.

Acceptance criteria from #13:
  - banner like `starting <duration>min <mode> session — Ctrl+C to interrupt`
  - completion line like `DING ...` (mode=bell_only) before the session UUID
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

SESSION_ID_RE = re.compile(r"[0-9a-fA-F-]{8,}")


def test_start_emits_banner_and_completion_line(mindful_run):
    """`mindful start` prints a banner up front and a completion signal at end."""
    result = mindful_run(["start", "--duration", "1", "--mode", "bell_only"])

    assert result.returncode == 0, (
        f"start exited {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )

    stdout = result.stdout
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    assert len(lines) >= 3, (
        f"expected at least 3 lines (banner + DING + uuid), got: {stdout!r}"
    )

    # Banner — must be the first non-empty line, must mention duration + mode.
    banner = lines[0]
    assert "starting" in banner.lower(), f"banner missing 'starting': {banner!r}"
    assert "1min" in banner.replace(" ", ""), (
        f"banner should reference '1min' duration: {banner!r}"
    )
    assert "bell_only" in banner, (
        f"banner should reference 'bell_only' mode: {banner!r}"
    )

    # Completion signal — must appear before the session UUID line.
    uuid_idx = None
    for i, ln in enumerate(lines):
        if SESSION_ID_RE.fullmatch(ln.strip()):
            uuid_idx = i
            break
    assert uuid_idx is not None, (
        f"expected a session UUID line in stdout, got: {stdout!r}"
    )
    assert uuid_idx >= 2, (
        f"expected banner + completion line BEFORE the UUID, got lines: {lines!r}"
    )

    # The line just before the UUID is the completion signal — it must mention
    # DING for bell_only mode (acceptance criterion).
    completion = lines[uuid_idx - 1]
    assert "DING" in completion, (
        f"bell_only completion line should contain 'DING', got: {completion!r}"
    )


def test_start_help_does_not_crash(mindful_home: Path):
    """Sanity check: --help still works after the banner refactor."""
    result = subprocess.run(
        [sys.executable, "-m", "mindful", "start", "--help"],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"start --help exited {result.returncode}: {result.stderr!r}"
    )
