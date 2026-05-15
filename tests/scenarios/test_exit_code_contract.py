"""L3 regression test — argparse parse failures exit 1, not 2.

Pins BUG-3 (#24): spec reserves exit code 2 for **data error**.
User-side argument validation failures (unknown subcommand, invalid int,
missing required arg) must exit 1 (user error), not argparse's default 2.

The implementation overrides the parser's error() handler to call
self.exit(1, ...) instead of self.exit(2, ...) and applies the same
parser class to subparsers so every parse path honors the rule.
"""

from __future__ import annotations

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


def _run(argv: list[str], home: Path, timeout: int = 10):
    pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = (
        f"{_PROJECT_SRC}{os.pathsep}{pythonpath}" if pythonpath else _PROJECT_SRC
    )
    env = {**os.environ, "HOME": str(home), "PYTHONPATH": pythonpath}
    return subprocess.run(
        _mindful_invocation() + argv,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def test_unknown_subcommand_exits_user_error(tmp_path: Path):
    """`mindful stat` (typo) is a user error → exit 1, not 2."""
    result = _run(["stat"], tmp_path)
    assert result.returncode == 1, (
        f"expected exit=1 for unknown subcommand, got {result.returncode}\n"
        f"stderr: {result.stderr!r}"
    )
    assert "invalid choice" in result.stderr.lower()


def test_invalid_int_for_duration_exits_user_error(tmp_path: Path):
    """`mindful start --duration abc` → exit 1 (argparse type=int rejects)."""
    result = _run(["start", "--duration", "abc", "--mode", "bell_only"], tmp_path)
    assert result.returncode == 1, (
        f"expected exit=1 for non-int --duration, got {result.returncode}\n"
        f"stderr: {result.stderr!r}"
    )
    assert "invalid int value" in result.stderr.lower()


def test_missing_required_args_exits_user_error(tmp_path: Path):
    """`mindful start` with no flags → exit 1 (required args missing)."""
    result = _run(["start"], tmp_path)
    assert result.returncode == 1, (
        f"expected exit=1 for missing required args, got {result.returncode}\n"
        f"stderr: {result.stderr!r}"
    )
    assert "required" in result.stderr.lower()


def test_help_still_exits_zero(tmp_path: Path):
    """`mindful --help` is not an error — must still exit 0."""
    result = _run(["--help"], tmp_path)
    assert result.returncode == 0, (
        f"expected exit=0 for --help, got {result.returncode}\n"
        f"stderr: {result.stderr!r}"
    )
