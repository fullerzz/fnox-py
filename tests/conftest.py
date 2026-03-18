from __future__ import annotations

import stat
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from fnox_py.runner import FnoxResult


def write_fake_script(path: Path, body: str = 'echo "$@"') -> Path:
    """Write a shell script and make it executable."""
    path.write_text(f"#!/bin/sh\n{body}\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return path


@pytest.fixture
def fake_fnox(tmp_path: Path) -> Path:
    """Create a fake fnox shell script that echoes its args."""
    return write_fake_script(tmp_path / "fnox")


@pytest.fixture
def monkeypatch_binary(fake_fnox: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Patch find_fnox_bin to return the fake binary."""
    monkeypatch.setattr("fnox_py.runner.find_fnox_bin", lambda: str(fake_fnox))
    return fake_fnox


def make_result(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
    cmd: list[str] | None = None,
) -> FnoxResult:
    return FnoxResult(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        cmd=cmd or ["fnox"],
    )


@pytest.fixture
def mock_run() -> Any:
    """Patch runner.run and yield the mock."""
    with patch("fnox_py.api.runner.run") as m:
        yield m
