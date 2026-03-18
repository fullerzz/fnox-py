from __future__ import annotations

from pathlib import Path

import pytest

from fnox_py.errors import FnoxCommandError, FnoxTimeoutError
from fnox_py.runner import FnoxResult, run


def test_successful_run(monkeypatch_binary: Path) -> None:
    result = run(["version"])
    assert isinstance(result, FnoxResult)
    assert result.returncode == 0


def test_check_true_raises(monkeypatch_binary: Path, tmp_path: Path) -> None:
    # Create a script that exits 1
    script = monkeypatch_binary
    script.write_text("#!/bin/sh\nexit 1\n")
    with pytest.raises(FnoxCommandError) as exc_info:
        run(["bad"])
    assert exc_info.value.returncode == 1


def test_check_false_no_raise(monkeypatch_binary: Path) -> None:
    script = monkeypatch_binary
    script.write_text("#!/bin/sh\nexit 1\n")
    result = run(["bad"], check=False)
    assert result.returncode == 1


def test_env_merging(monkeypatch_binary: Path) -> None:
    script = monkeypatch_binary
    script.write_text('#!/bin/sh\necho "$MY_TEST_VAR"\n')
    result = run([], env={"MY_TEST_VAR": "hello"})
    assert result.stdout.strip() == "hello"


def test_cwd(monkeypatch_binary: Path, tmp_path: Path) -> None:
    script = monkeypatch_binary
    script.write_text("#!/bin/sh\npwd\n")
    subdir = tmp_path / "sub"
    subdir.mkdir()
    result = run([], cwd=subdir)
    assert result.stdout.strip() == str(subdir)


def test_timeout(monkeypatch_binary: Path) -> None:
    script = monkeypatch_binary
    script.write_text("#!/bin/sh\nsleep 10\n")
    with pytest.raises(FnoxTimeoutError):
        run([], timeout=0.1)


def test_input(monkeypatch_binary: Path) -> None:
    script = monkeypatch_binary
    script.write_text("#!/bin/sh\ncat\n")
    result = run([], input="hello world")
    assert result.stdout.strip() == "hello world"
