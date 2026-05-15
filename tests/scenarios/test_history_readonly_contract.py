"""L4 scenario test — `mindful history` honors the read-only contract.

Pins FEAT-4 (issue #15): `mindful history` lists completed sessions and
MUST NOT mutate ~/.mindful/. It mirrors the three boundary cases the
existing stats read-only contract test pins:

  1. empty $HOME — no .mindful/ created
  2. post-start state — three runs leave files byte-identical
  3. corrupt sessions.json — warn to stderr, no backup, file untouched

This test deliberately duplicates the structure of the stats contract
(see tests/scenarios/test_stats_readonly_contract.py if it lands first
or in a parallel PR). The duplication is the seam IMP-6 (#18) collapses
into a parametrize.
"""

from __future__ import annotations

import hashlib
import os
import re
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


def _snapshot_dir(d: Path) -> dict[str, tuple[int, float, str]]:
    out: dict[str, tuple[int, float, str]] = {}
    if not d.exists():
        return out
    for p in sorted(d.rglob("*")):
        if not p.is_file():
            continue
        st = p.stat()
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        out[str(p.relative_to(d))] = (st.st_size, st.st_mtime_ns, digest)
    return out


# Each completed-history line shape: "<iso_timestamp>  <N>min  <mode>"
HISTORY_LINE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T[\d:.+\-]+\s+\d+min\s+\w+\s*$"
)


def test_history_on_empty_home_does_not_create_mindful_dir(tmp_path: Path):
    """Empty $HOME → empty stdout, exit 0, NO ~/.mindful/ created."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mindful_dir = fake_home / ".mindful"
    assert not mindful_dir.exists()

    result = _run(_mindful_invocation() + ["history"], home=fake_home)

    assert result.returncode == 0, (
        f"history on empty home exited {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    # Empty history → no output lines (only blank/whitespace allowed).
    assert result.stdout.strip() == "", (
        f"history on empty home should print nothing, got: {result.stdout!r}"
    )
    # Read-only contract: directory MUST NOT exist.
    assert not mindful_dir.exists(), (
        f"history violated read-only contract: {mindful_dir} was created"
    )


def test_history_after_start_does_not_mutate_state(tmp_path: Path):
    """history × 3 after start → all bytes byte-identical, no mtime drift."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mindful_dir = fake_home / ".mindful"

    start_result = _run(
        _mindful_invocation() + ["start", "--duration", "1", "--mode", "bell_only"],
        home=fake_home,
        fast_tick=True,
    )
    assert start_result.returncode == 0, (
        f"setup failed — start exited {start_result.returncode}\n"
        f"stderr: {start_result.stderr!r}"
    )
    assert mindful_dir.exists()

    before = _snapshot_dir(mindful_dir)
    assert "sessions.json" in before
    assert "streak.json" in before

    for i in range(3):
        result = _run(_mindful_invocation() + ["history"], home=fake_home)
        assert result.returncode == 0, (
            f"history run #{i + 1} exited {result.returncode}\n"
            f"stderr: {result.stderr!r}"
        )
        # Should print exactly one history line for the one completed session.
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        assert len(lines) == 1, (
            f"history run #{i + 1} expected 1 line, got: {result.stdout!r}"
        )
        assert HISTORY_LINE.match(lines[0]), (
            f"history line shape unexpected: {lines[0]!r}"
        )
        assert "1min" in lines[0]
        assert "bell_only" in lines[0]

    after = _snapshot_dir(mindful_dir)
    assert before.keys() == after.keys(), (
        f"file set changed: before={sorted(before)}, after={sorted(after)}"
    )
    for name in before:
        assert before[name] == after[name], (
            f"history mutated {name}: before={before[name]}, after={after[name]}"
        )


def test_history_on_corrupt_sessions_does_not_mutate_or_backup(tmp_path: Path):
    """Corrupt sessions.json → warn to stderr, exit 0, file byte-identical."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mindful_dir = fake_home / ".mindful"
    mindful_dir.mkdir()
    sessions_file = mindful_dir / "sessions.json"
    sessions_file.write_text("not valid json {{{")

    before = _snapshot_dir(mindful_dir)
    assert list(before) == ["sessions.json"]

    result = _run(_mindful_invocation() + ["history"], home=fake_home)

    assert result.returncode == 0, (
        f"history on corrupt data should exit 0, got {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert "warning" in result.stderr.lower() or "unreadable" in result.stderr.lower(), (
        f"expected a warning on stderr, got: {result.stderr!r}"
    )

    after = _snapshot_dir(mindful_dir)
    assert list(after) == ["sessions.json"], (
        f"history added sibling files (likely a backup): {sorted(after)}"
    )
    assert before["sessions.json"] == after["sessions.json"], (
        f"history mutated corrupt sessions.json:\n"
        f"  before: {before['sessions.json']}\n"
        f"  after:  {after['sessions.json']}"
    )
