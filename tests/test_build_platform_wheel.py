from __future__ import annotations

import importlib.util
import json
import shutil
import stat
import tarfile
import zipfile
from io import BytesIO
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


def test_resolve_expected_hashes_reads_hash_manifest(mod, monkeypatch, tmp_path) -> None:
    hashes_file = tmp_path / "FNOX_HASHES.json"
    hashes_file.write_text(
        json.dumps(
            {
                "1.18.0": {
                    "fnox-x86_64-unknown-linux-gnu": {
                        "archive_sha256": "archive-hash",
                        "binary_sha256": "binary-hash",
                    }
                }
            }
        )
    )
    monkeypatch.setattr(mod, "HASHES_FILE", hashes_file)

    assert mod._resolve_expected_hashes("1.18.0", ["fnox-x86_64-unknown-linux-gnu"]) == {
        "fnox-x86_64-unknown-linux-gnu": {
            "archive_sha256": "archive-hash",
            "binary_sha256": "binary-hash",
        }
    }


def test_resolve_expected_hashes_raises_when_file_missing(mod, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mod, "HASHES_FILE", tmp_path / "nonexistent.json")

    with pytest.raises(FileNotFoundError, match=r"FNOX_HASHES\.json not found"):
        mod._resolve_expected_hashes("1.18.0", ["fnox-x86_64-unknown-linux-gnu"])


def test_resolve_expected_hashes_requires_manifest_entry(mod, monkeypatch, tmp_path) -> None:
    hashes_file = tmp_path / "FNOX_HASHES.json"
    hashes_file.write_text("{}")
    monkeypatch.setattr(mod, "HASHES_FILE", hashes_file)

    with pytest.raises(KeyError, match=r"No expected hashes configured"):
        mod._resolve_expected_hashes("1.18.0", ["fnox-x86_64-unknown-linux-gnu"])


def test_verify_sha256_raises_on_mismatch(mod, tmp_path) -> None:
    sample = tmp_path / "sample.txt"
    sample.write_text("hello")

    with pytest.raises(ValueError, match=r"SHA256 mismatch"):
        mod._verify_sha256(sample, "deadbeef", "sample")


def test_download_binary_verifies_archive_and_binary_hashes(mod, monkeypatch, tmp_path) -> None:
    archive_path = tmp_path / "fnox-x86_64-unknown-linux-gnu.tar.gz"
    binary_bytes = b"fake fnox binary"
    dest_dir = tmp_path / "dest"

    with tarfile.open(archive_path, "w:gz") as tf:
        info = tarfile.TarInfo("fnox-x86_64-unknown-linux-gnu/fnox")
        info.size = len(binary_bytes)
        info.mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
        tf.addfile(info, BytesIO(binary_bytes))

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        shutil.copy2(archive_path, Path(cmd[3]))

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    extracted = mod._download_binary(
        "1.18.0",
        "fnox-x86_64-unknown-linux-gnu",
        dest_dir,
        {
            "archive_sha256": mod._sha256_digest(archive_path),
            "binary_sha256": mod.hashlib.sha256(binary_bytes).hexdigest(),
        },
    )

    assert extracted.name == "fnox"
    assert extracted.read_bytes() == binary_bytes


def test_download_binary_rejects_unexpected_binary_hash(mod, monkeypatch, tmp_path) -> None:
    archive_path = tmp_path / "fnox-x86_64-pc-windows-msvc.zip"
    binary_bytes = b"fake fnox.exe"
    dest_dir = tmp_path / "dest"

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("fnox-x86_64-pc-windows-msvc/fnox.exe", binary_bytes)

    def fake_run(cmd: list[str], check: bool) -> None:
        assert check is True
        shutil.copy2(archive_path, Path(cmd[3]))

    monkeypatch.setattr(mod.subprocess, "run", fake_run)

    with pytest.raises(ValueError, match=r"SHA256 mismatch"):
        mod._download_binary(
            "1.18.0",
            "fnox-x86_64-pc-windows-msvc",
            dest_dir,
            {
                "archive_sha256": mod._sha256_digest(archive_path),
                "binary_sha256": "deadbeef",
            },
        )
