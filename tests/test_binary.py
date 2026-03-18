from __future__ import annotations

import stat
import sysconfig
from pathlib import Path

import pytest

from fnox_py.binary import find_fnox_bin
from fnox_py.errors import FnoxNotFoundError


def test_env_var_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "fnox"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("FNOX_PY_BINARY", str(fake))
    assert find_fnox_bin() == str(fake)


def test_env_var_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FNOX_PY_BINARY", str(tmp_path / "nope"))
    with pytest.raises(FnoxNotFoundError, match="FNOX_PY_BINARY"):
        find_fnox_bin()


def test_sysconfig_discovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FNOX_PY_BINARY", raising=False)
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    exe = sysconfig.get_config_var("EXE") or ""
    fake = scripts_dir / f"fnox{exe}"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr("sysconfig.get_path", lambda _name, **_kw: str(scripts_dir) if _name == "scripts" else None)
    assert find_fnox_bin() == str(fake)


def test_path_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FNOX_PY_BINARY", raising=False)
    scripts_dir = tmp_path / "bin"
    scripts_dir.mkdir()
    exe = sysconfig.get_config_var("EXE") or ""
    fake = scripts_dir / f"fnox{exe}"
    fake.write_text("#!/bin/sh\n")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    # Make sysconfig paths return nothing useful
    monkeypatch.setattr("sysconfig.get_path", lambda _name, **_kw: None)
    monkeypatch.setattr("fnox_py.binary._module_path", lambda: None)
    monkeypatch.setattr("shutil.which", lambda _name: str(fake) if _name == "fnox" else None)
    assert find_fnox_bin() == str(fake)


def test_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FNOX_PY_BINARY", raising=False)
    monkeypatch.setattr("sysconfig.get_path", lambda _name, **_kw: None)
    monkeypatch.setattr("fnox_py.binary._module_path", lambda: None)
    monkeypatch.setattr("shutil.which", lambda _name: None)
    with pytest.raises(FnoxNotFoundError):
        find_fnox_bin()
