"""L4 scenario test — first-day user round-trip (T2 composition).

Pins the seam between three subcommands as a brand-new user would experience
them on day one:

  1. `mindful stats` on an empty $HOME — zeros, spec-pinned format, read-only
     (no ~/.mindful/ created).
  2. `mindful start --duration 1 --mode bell_only` (under MINDFUL_FAST_TICK=1).
  3. `mindful stats` again — current_streak=1, longest_streak=1,
     total_minutes=1, avg_minutes=1.0, completion_rate_30d=1.00 — verifying
     the start→stats seam (sessions.json + streak.json wired through).
  4. `mindful history` — the new completed session is listed.
  5. A second start the same day — current_streak STAYS at 1 (same-day
     sessions accumulate minutes, not streak days).

This is the first L4 scenario that asserts the stats output contract end-to-end
(docs/spec.md "Output format (pinned)"); existing scenario tests cover history
and start banner but never pin stats lines.
"""

from __future__ import annotations

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


# Spec-pinned stats lines. The spec allows alignment padding between the
# colon and the value, so we use `\s+`, not a literal-space match.
STATS_LINE = {
    "current_streak":      re.compile(r"^current_streak:\s+(\d+)\s*$"),
    "longest_streak":      re.compile(r"^longest_streak:\s+(\d+)\s*$"),
    "total_minutes":       re.compile(r"^total_minutes:\s+(\d+)\s*$"),
    "avg_minutes":         re.compile(r"^avg_minutes:\s+(\d+\.\d)\s*$"),  # 1 decimal
    "completion_rate_30d": re.compile(r"^completion_rate_30d:\s+(\d\.\d{2})\s*$"),  # 2 decimal
}
EXPECTED_ORDER = [
    "current_streak",
    "longest_streak",
    "total_minutes",
    "avg_minutes",
    "completion_rate_30d",
]
SESSION_ID_RE = re.compile(r"[0-9a-fA-F-]{8,}")


def _parse_stats(stdout: str) -> dict[str, str]:
    """Parse stats output, enforcing spec-pinned order + per-line format.

    Returns the captured value strings (so the caller can assert on exact
    formatting, e.g. '0.00' vs '0').
    """
    lines = [ln for ln in stdout.splitlines() if ln.strip()]
    assert len(lines) == len(EXPECTED_ORDER), (
        f"stats should print exactly {len(EXPECTED_ORDER)} lines, "
        f"got {len(lines)}: {stdout!r}"
    )
    captured: dict[str, str] = {}
    for metric_name, line in zip(EXPECTED_ORDER, lines):
        match = STATS_LINE[metric_name].match(line)
        assert match, (
            f"stats line {metric_name!r} failed format check: "
            f"line={line!r}, expected pattern={STATS_LINE[metric_name].pattern}"
        )
        captured[metric_name] = match.group(1)
    return captured


def test_first_day_round_trip(tmp_path: Path):
    """Brand-new user: stats → start → stats → history → start-again-same-day."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mindful_dir = fake_home / ".mindful"

    # --- Step 1: stats on empty $HOME --------------------------------------
    # Expect zeros in spec-pinned format AND read-only (no ~/.mindful/).
    r1 = _run(_mindful_invocation() + ["stats"], home=fake_home)
    assert r1.returncode == 0, (
        f"stats on empty home exited {r1.returncode}\n"
        f"stdout: {r1.stdout!r}\nstderr: {r1.stderr!r}"
    )
    assert not mindful_dir.exists(), (
        f"stats on empty home violated read-only contract: "
        f"{mindful_dir} was created"
    )
    zero_stats = _parse_stats(r1.stdout)
    assert zero_stats == {
        "current_streak": "0",
        "longest_streak": "0",
        "total_minutes": "0",
        "avg_minutes": "0.0",
        "completion_rate_30d": "0.00",
    }, f"unexpected zero-state stats: {zero_stats!r}"

    # --- Step 2: start (1 minute, bell_only, fast-tick) --------------------
    r2 = _run(
        _mindful_invocation()
        + ["start", "--duration", "1", "--mode", "bell_only"],
        home=fake_home,
        fast_tick=True,
    )
    assert r2.returncode == 0, (
        f"start exited {r2.returncode}\n"
        f"stdout: {r2.stdout!r}\nstderr: {r2.stderr!r}"
    )
    # Layer-3 sanity: stdout must contain a session id token somewhere.
    assert SESSION_ID_RE.search(r2.stdout), (
        f"expected a session id in start stdout, got: {r2.stdout!r}"
    )
    # Layer-4 sanity: persistence files now exist.
    sessions_file = mindful_dir / "sessions.json"
    streak_file = mindful_dir / "streak.json"
    assert sessions_file.exists() and streak_file.exists(), (
        f"start did not create persistence files: "
        f"sessions.json exists={sessions_file.exists()}, "
        f"streak.json exists={streak_file.exists()}"
    )

    # --- Step 3: stats reflects the completed session ----------------------
    r3 = _run(_mindful_invocation() + ["stats"], home=fake_home)
    assert r3.returncode == 0, (
        f"stats post-session exited {r3.returncode}\n"
        f"stderr: {r3.stderr!r}"
    )
    post_stats = _parse_stats(r3.stdout)
    assert post_stats == {
        "current_streak": "1",
        "longest_streak": "1",
        "total_minutes": "1",
        "avg_minutes": "1.0",
        "completion_rate_30d": "1.00",
    }, f"unexpected post-session stats: {post_stats!r}"

    # --- Step 4: history lists the session --------------------------------
    r4 = _run(_mindful_invocation() + ["history"], home=fake_home)
    assert r4.returncode == 0, (
        f"history exited {r4.returncode}\nstderr: {r4.stderr!r}"
    )
    history_lines = [ln for ln in r4.stdout.splitlines() if ln.strip()]
    assert len(history_lines) == 1, (
        f"history should print exactly 1 line after one session, "
        f"got: {r4.stdout!r}"
    )
    # Line shape: "<iso_timestamp>  <N>min  <mode>"
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T[\d:.+\-]+\s+1min\s+bell_only\s*$", history_lines[0]
    ), f"history line shape unexpected: {history_lines[0]!r}"

    # --- Step 5: second session same day → streak STAYS at 1 --------------
    # Spec contract: a streak counts *days*, not sessions. Two sessions on
    # the same calendar day must not bump current_streak past 1, but they
    # do accumulate total_minutes.
    r5 = _run(
        _mindful_invocation()
        + ["start", "--duration", "1", "--mode", "bell_only"],
        home=fake_home,
        fast_tick=True,
    )
    assert r5.returncode == 0, (
        f"second start exited {r5.returncode}\nstderr: {r5.stderr!r}"
    )

    r6 = _run(_mindful_invocation() + ["stats"], home=fake_home)
    assert r6.returncode == 0
    final_stats = _parse_stats(r6.stdout)
    assert final_stats == {
        "current_streak": "1",        # NOT 2 — same-day sessions don't double-bump
        "longest_streak": "1",
        "total_minutes": "2",         # 1 + 1
        "avg_minutes": "1.0",
        "completion_rate_30d": "1.00",
    }, f"unexpected stats after 2 same-day sessions: {final_stats!r}"


def test_stats_on_empty_home_is_read_only(tmp_path: Path):
    """Tighten the iter-1 read-only contract specifically for stats.

    The history read-only contract already pins this for `history`. This
    test pins the same contract for `stats`, closing the obvious
    "well, what about stats?" gap.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mindful_dir = fake_home / ".mindful"
    assert not mindful_dir.exists()

    # Run stats three times — each must leave $HOME pristine.
    for i in range(3):
        result = _run(_mindful_invocation() + ["stats"], home=fake_home)
        assert result.returncode == 0, (
            f"stats run #{i + 1} exited {result.returncode}\n"
            f"stderr: {result.stderr!r}"
        )
        assert not mindful_dir.exists(), (
            f"stats run #{i + 1} created {mindful_dir} "
            f"(violates read-only contract)"
        )
