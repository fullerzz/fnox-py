from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from fnox_py.cli import main
from fnox_py.errors import FnoxNotFoundError
from tests.conftest import make_result


def test_which(monkeypatch_binary: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["fnox-py", "which"]),
        patch("fnox_py.cli.find_fnox_bin", return_value=str(monkeypatch_binary)),
    ):
        main()
    out = capsys.readouterr().out
    assert str(monkeypatch_binary) in out


def test_which_not_found(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["fnox-py", "which"]),
        patch("fnox_py.cli.find_fnox_bin", side_effect=FnoxNotFoundError("not found")),
        pytest.raises(SystemExit, match="1"),
    ):
        main()


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["fnox-py", "version"]),
        patch("fnox_py.cli.run", return_value=make_result(stdout="fnox 1.0.0\n")),
    ):
        main()
    out = capsys.readouterr().out
    assert "fnox-py" in out
    assert "fnox 1.0.0" in out


def test_doctor(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(sys, "argv", ["fnox-py", "doctor"]),
        patch("fnox_py.cli.find_fnox_bin", return_value="/usr/local/bin/fnox"),
        patch("fnox_py.cli.run", return_value=make_result(stdout="fnox 1.0.0\n")),
    ):
        main()
    out = capsys.readouterr().out
    assert "fnox-py" in out
    assert "Python" in out
    assert "/usr/local/bin/fnox" in out
