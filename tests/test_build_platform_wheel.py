from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "build_platform_wheel.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_platform_wheel", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return _load_module()


def test_normalize_fnox_version_strips_v_prefix(mod) -> None:
    assert mod._normalize_fnox_version("v1.2.3") == "1.2.3"
    assert mod._normalize_fnox_version("1.2.3") == "1.2.3"


def test_resolve_fnox_version_uses_requested_value(mod) -> None:
    assert mod._resolve_fnox_version("v1.2.3") == "1.2.3"


def test_resolve_fnox_version_reads_version_file(mod, monkeypatch, tmp_path) -> None:
    version_file = tmp_path / "FNOX_VERSION.txt"
    version_file.write_text("v1.18.0\n")
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)

    assert mod._resolve_fnox_version(None) == "1.18.0"


def test_resolve_fnox_version_raises_when_file_missing(mod, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "VERSION_FILE", tmp_path / "nonexistent.txt")

    with pytest.raises(FileNotFoundError, match=r"FNOX_VERSION\.txt not found"):
        mod._resolve_fnox_version(None)
