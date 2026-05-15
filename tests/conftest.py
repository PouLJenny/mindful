"""Shared pytest fixtures for the mindful test suite.

The `mindful_home` fixture centralizes the isolated-HOME setup that every L4
scenario otherwise re-implements: a temp `$HOME`, `MINDFUL_FAST_TICK=1`, and a
`PYTHONPATH` that points subprocess invocations at the in-repo `src/` layout.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest

_PROJECT_SRC = str(Path(__file__).resolve().parent.parent / "src")


@pytest.fixture
def mindful_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return an isolated `$HOME` configured for real-CLI subprocess tests.

    Side effects (scoped to the test):
      - `$HOME` is set to `<tmp_path>/home` (created).
      - `MINDFUL_FAST_TICK=1` so `start --duration N` sleeps N seconds.
      - `PYTHONPATH` is prefixed with `<repo>/src` so `python -m mindful` and
        `from mindful.cli import main` work without an installed console
        script.
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("MINDFUL_FAST_TICK", "1")

    existing = os.environ.get("PYTHONPATH", "")
    new_pythonpath = (
        f"{_PROJECT_SRC}{os.pathsep}{existing}" if existing else _PROJECT_SRC
    )
    monkeypatch.setenv("PYTHONPATH", new_pythonpath)
    return home


@pytest.fixture
def mindful_run(mindful_home: Path) -> Callable[..., subprocess.CompletedProcess]:
    """Return a callable that invokes `python -m mindful` against `mindful_home`.

    Usage:
        result = mindful_run(["start", "--duration", "1", "--mode", "bell_only"])
        assert result.returncode == 0
    """

    def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "mindful", *args],
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    return _run
