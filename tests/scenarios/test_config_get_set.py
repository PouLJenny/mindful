"""L4 scenario test — `mindful config --get / --set` round-trip.

Pins FEAT-5 (issue #16):

  - `--get <key>` prints the configured value (or default if unset),
    and MUST NOT create ~/.mindful/.
  - `--set <key> <value>` writes ~/.mindful/config.json atomically.
  - Invalid <key> exits non-zero with a clear stderr message.
"""

from __future__ import annotations

import hashlib
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


def _run(cmd: list[str], home: Path, timeout: int = 30):
    pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath = (
        f"{_PROJECT_SRC}{os.pathsep}{pythonpath}" if pythonpath else _PROJECT_SRC
    )
    env = {**os.environ, "HOME": str(home), "PYTHONPATH": pythonpath}
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
        out[str(p.relative_to(d))] = (
            st.st_size,
            st.st_mtime_ns,
            hashlib.sha256(p.read_bytes()).hexdigest(),
        )
    return out


def test_config_get_default_on_empty_home(tmp_path: Path):
    """--get a known key on empty $HOME prints the default, no .mindful/ created."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mindful_dir = fake_home / ".mindful"

    result = _run(
        _mindful_invocation() + ["config", "--get", "bell_sound"], home=fake_home
    )

    assert result.returncode == 0, (
        f"config --get exited {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert result.stdout.strip() == "default", (
        f"expected default 'default', got: {result.stdout!r}"
    )
    # Read-only contract: directory MUST NOT exist.
    assert not mindful_dir.exists(), (
        f"config --get violated read-only contract: {mindful_dir} was created"
    )


def test_config_get_unknown_key_errors(tmp_path: Path):
    """--get with an unknown key exits non-zero with a clear stderr message."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    result = _run(
        _mindful_invocation() + ["config", "--get", "no_such_key"], home=fake_home
    )

    assert result.returncode != 0, (
        f"expected non-zero for unknown key, got {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
    assert "unknown" in result.stderr.lower() or "valid" in result.stderr.lower(), (
        f"expected error message naming the issue, got: {result.stderr!r}"
    )


def test_config_set_then_get_round_trip(tmp_path: Path):
    """--set foo X → --get foo prints X; config.json on disk reflects it."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    set_result = _run(
        _mindful_invocation() + ["config", "--set", "bell_sound", "tibetan_bowl"],
        home=fake_home,
    )
    assert set_result.returncode == 0, (
        f"--set exited {set_result.returncode}: {set_result.stderr!r}"
    )

    config_file = fake_home / ".mindful" / "config.json"
    assert config_file.exists(), "--set MUST create ~/.mindful/config.json"
    payload = json.loads(config_file.read_text())
    assert payload.get("bell_sound") == "tibetan_bowl", (
        f"config file content unexpected: {payload!r}"
    )

    get_result = _run(
        _mindful_invocation() + ["config", "--get", "bell_sound"], home=fake_home
    )
    assert get_result.returncode == 0
    assert get_result.stdout.strip() == "tibetan_bowl", (
        f"--get did not see --set value: {get_result.stdout!r}"
    )


def test_config_set_unknown_key_errors_and_does_not_write(tmp_path: Path):
    """--set with an unknown key exits non-zero and writes no config file."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    result = _run(
        _mindful_invocation() + ["config", "--set", "weird_key", "x"],
        home=fake_home,
    )
    assert result.returncode != 0, (
        f"expected non-zero for unknown --set key, got {result.returncode}\n"
        f"stderr: {result.stderr!r}"
    )
    config_file = fake_home / ".mindful" / "config.json"
    assert not config_file.exists(), (
        "rejected --set must not create config.json"
    )


def test_config_get_does_not_mutate_existing_config(tmp_path: Path):
    """After a --set, repeated --get calls leave config.json byte-identical."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    mindful_dir = fake_home / ".mindful"

    _ = _run(
        _mindful_invocation() + ["config", "--set", "duration_default", "20"],
        home=fake_home,
    )
    before = _snapshot_dir(mindful_dir)
    assert "config.json" in before

    for _ in range(3):
        r = _run(
            _mindful_invocation() + ["config", "--get", "duration_default"],
            home=fake_home,
        )
        assert r.returncode == 0
        assert r.stdout.strip() == "20"

    after = _snapshot_dir(mindful_dir)
    assert before == after, (
        f"config --get mutated state:\n  before: {before}\n  after:  {after}"
    )


def test_config_requires_get_or_set(tmp_path: Path):
    """`mindful config` without --get/--set is an argparse error."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()

    result = _run(_mindful_invocation() + ["config"], home=fake_home)
    assert result.returncode != 0, (
        f"expected error without --get/--set, got {result.returncode}\n"
        f"stdout: {result.stdout!r}\nstderr: {result.stderr!r}"
    )
