from __future__ import annotations

import hashlib
import importlib.util
import json
import tarfile
import zipfile
from io import BytesIO
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sync_upstream.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sync_upstream", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod() -> ModuleType:
    return _load_module()


# --- Version helpers ---


def test_normalize_version_strips_v_prefix(mod: ModuleType) -> None:
    assert mod._normalize_version("v1.19.0") == "1.19.0"
    assert mod._normalize_version("1.19.0") == "1.19.0"


def test_read_current_version_returns_content(mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    version_file = tmp_path / "FNOX_VERSION.txt"
    version_file.write_text("1.18.0\n")
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)

    assert mod._read_current_version() == "1.18.0"


def test_read_current_version_returns_none_when_missing(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(mod, "VERSION_FILE", tmp_path / "nonexistent.txt")

    assert mod._read_current_version() is None


def test_read_current_version_returns_none_when_empty(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    version_file = tmp_path / "FNOX_VERSION.txt"
    version_file.write_text("  \n")
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)

    assert mod._read_current_version() is None


# --- URL construction ---


def test_archive_url_tar_gz_for_linux(mod: ModuleType) -> None:
    url = mod._archive_url("1.19.0", "fnox-x86_64-unknown-linux-gnu")
    assert url == "https://github.com/jdx/fnox/releases/download/v1.19.0/fnox-x86_64-unknown-linux-gnu.tar.gz"


def test_archive_url_zip_for_windows(mod: ModuleType) -> None:
    url = mod._archive_url("1.19.0", "fnox-x86_64-pc-windows-msvc")
    assert url == "https://github.com/jdx/fnox/releases/download/v1.19.0/fnox-x86_64-pc-windows-msvc.zip"


# --- SHA256 ---


def test_sha256_digest_matches_known_bytes(mod: ModuleType, tmp_path: Path) -> None:
    data = b"hello world"
    path = tmp_path / "test.bin"
    path.write_bytes(data)

    expected = hashlib.sha256(data).hexdigest()
    assert mod._sha256_digest(path) == expected


# --- Binary extraction ---


def test_extract_binary_from_tar_gz(mod: ModuleType, tmp_path: Path) -> None:
    binary_bytes = b"fake fnox binary"
    archive_path = tmp_path / "fnox-x86_64-unknown-linux-gnu.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tf:
        info = tarfile.TarInfo("fnox-x86_64-unknown-linux-gnu/fnox")
        info.size = len(binary_bytes)
        tf.addfile(info, BytesIO(binary_bytes))

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    result = mod._extract_binary_and_hash(archive_path, "fnox-x86_64-unknown-linux-gnu", work_dir)
    assert result == hashlib.sha256(binary_bytes).hexdigest()
    assert (work_dir / "fnox").read_bytes() == binary_bytes


def test_extract_binary_from_zip(mod: ModuleType, tmp_path: Path) -> None:
    binary_bytes = b"fake fnox.exe binary"
    archive_path = tmp_path / "fnox-x86_64-pc-windows-msvc.zip"

    with zipfile.ZipFile(archive_path, "w") as zf:
        zf.writestr("fnox-x86_64-pc-windows-msvc/fnox.exe", binary_bytes)

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    result = mod._extract_binary_and_hash(archive_path, "fnox-x86_64-pc-windows-msvc", work_dir)
    assert result == hashlib.sha256(binary_bytes).hexdigest()
    assert (work_dir / "fnox.exe").read_bytes() == binary_bytes


def test_extract_binary_raises_when_not_found(mod: ModuleType, tmp_path: Path) -> None:
    archive_path = tmp_path / "empty.tar.gz"

    with tarfile.open(archive_path, "w:gz"):
        pass

    work_dir = tmp_path / "work"
    work_dir.mkdir()

    with pytest.raises(FileNotFoundError, match=r"Could not find fnox"):
        mod._extract_binary_and_hash(archive_path, "fnox-x86_64-unknown-linux-gnu", work_dir)


# --- API response parsing ---


def _make_mock_response(data: dict[str, Any]) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_fetch_latest_release_parses_response(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_resp = _make_mock_response(
        {
            "tag_name": "v1.19.0",
            "html_url": "https://github.com/jdx/fnox/releases/tag/v1.19.0",
            "body": "Release notes here",
        }
    )
    monkeypatch.setattr(mod, "urlopen", lambda _req: mock_resp)

    result = mod._fetch_latest_release()
    assert result["tag_name"] == "v1.19.0"
    assert result["html_url"] == "https://github.com/jdx/fnox/releases/tag/v1.19.0"
    assert result["body"] == "Release notes here"


def test_fetch_latest_release_sends_auth_header(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_resp = _make_mock_response(
        {
            "tag_name": "v1.19.0",
            "html_url": "https://github.com/jdx/fnox/releases/tag/v1.19.0",
            "body": "",
        }
    )

    captured_req: list[Any] = []

    def fake_urlopen(req: object) -> MagicMock:
        captured_req.append(req)
        return mock_resp

    monkeypatch.setattr(mod, "urlopen", fake_urlopen)

    test_token = "ghp_test123"  # noqa: S105
    mod._fetch_latest_release(token=test_token)
    assert len(captured_req) == 1
    assert captured_req[0].get_header("Authorization") == f"Bearer {test_token}"


def test_fetch_latest_release_no_auth_without_token(mod: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    mock_resp = _make_mock_response(
        {
            "tag_name": "v1.19.0",
            "html_url": "https://github.com/jdx/fnox/releases/tag/v1.19.0",
            "body": "",
        }
    )

    captured_req: list[Any] = []

    def fake_urlopen(req: object) -> MagicMock:
        captured_req.append(req)
        return mock_resp

    monkeypatch.setattr(mod, "urlopen", fake_urlopen)

    mod._fetch_latest_release(token=None)
    assert len(captured_req) == 1
    assert not captured_req[0].has_header("Authorization")


# --- File writing ---


def test_write_version_file(mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    version_file = tmp_path / "FNOX_VERSION.txt"
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)

    mod._write_version_file("1.19.0")
    assert version_file.read_text() == "1.19.0\n"


def test_write_hashes_file(mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hashes_file = tmp_path / "FNOX_HASHES.json"
    monkeypatch.setattr(mod, "HASHES_FILE", hashes_file)

    hashes = {
        "fnox-x86_64-unknown-linux-gnu": {
            "archive_sha256": "aaa",
            "binary_sha256": "bbb",
        }
    }
    mod._write_hashes_file("1.19.0", hashes)

    written = json.loads(hashes_file.read_text())
    assert "1.19.0" in written
    assert written["1.19.0"]["fnox-x86_64-unknown-linux-gnu"]["archive_sha256"] == "aaa"
    assert hashes_file.read_text().endswith("\n")


# --- main() orchestration ---


def _make_fake_hashes(mod: ModuleType) -> dict[str, dict[str, str]]:
    return {name: {"archive_sha256": f"archive-{name}", "binary_sha256": f"binary-{name}"} for name in mod.ASSET_NAMES}


def test_main_noop_when_version_matches(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    version_file = tmp_path / "FNOX_VERSION.txt"
    version_file.write_text("1.19.0\n")
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)

    mock_resp = _make_mock_response(
        {
            "tag_name": "v1.19.0",
            "html_url": "https://github.com/jdx/fnox/releases/tag/v1.19.0",
            "body": "notes",
        }
    )
    monkeypatch.setattr(mod, "urlopen", lambda _req: mock_resp)
    monkeypatch.setattr("sys.argv", ["sync_upstream.py"])

    mod.main()

    captured = capsys.readouterr()
    assert "UPDATED=false" in captured.out
    assert "VERSION=1.19.0" in captured.out


def test_main_updates_when_new_version(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    version_file = tmp_path / "FNOX_VERSION.txt"
    version_file.write_text("1.18.0\n")
    hashes_file = tmp_path / "FNOX_HASHES.json"
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)
    monkeypatch.setattr(mod, "HASHES_FILE", hashes_file)

    mock_resp = _make_mock_response(
        {
            "tag_name": "v1.19.0",
            "html_url": "https://github.com/jdx/fnox/releases/tag/v1.19.0",
            "body": "New stuff",
        }
    )
    monkeypatch.setattr(mod, "urlopen", lambda _req: mock_resp)

    fake_hashes = _make_fake_hashes(mod)
    monkeypatch.setattr(mod, "_compute_platform_hashes", lambda _v, _w: fake_hashes)
    monkeypatch.setattr("sys.argv", ["sync_upstream.py"])

    mod.main()

    captured = capsys.readouterr()
    assert "UPDATED=true" in captured.out
    assert "VERSION=1.19.0" in captured.out
    assert version_file.read_text() == "1.19.0\n"
    assert json.loads(hashes_file.read_text())["1.19.0"] == fake_hashes


def test_main_force_updates_even_when_version_matches(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    version_file = tmp_path / "FNOX_VERSION.txt"
    version_file.write_text("1.19.0\n")
    hashes_file = tmp_path / "FNOX_HASHES.json"
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)
    monkeypatch.setattr(mod, "HASHES_FILE", hashes_file)

    mock_resp = _make_mock_response(
        {
            "tag_name": "v1.19.0",
            "html_url": "https://github.com/jdx/fnox/releases/tag/v1.19.0",
            "body": "notes",
        }
    )
    monkeypatch.setattr(mod, "urlopen", lambda _req: mock_resp)

    fake_hashes = _make_fake_hashes(mod)
    monkeypatch.setattr(mod, "_compute_platform_hashes", lambda _v, _w: fake_hashes)
    monkeypatch.setattr("sys.argv", ["sync_upstream.py", "--force"])

    mod.main()

    captured = capsys.readouterr()
    assert "UPDATED=true" in captured.out
    assert version_file.read_text() == "1.19.0\n"


def test_main_dry_run_does_not_write(
    mod: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    version_file = tmp_path / "FNOX_VERSION.txt"
    version_file.write_text("1.18.0\n")
    hashes_file = tmp_path / "FNOX_HASHES.json"
    monkeypatch.setattr(mod, "VERSION_FILE", version_file)
    monkeypatch.setattr(mod, "HASHES_FILE", hashes_file)

    mock_resp = _make_mock_response(
        {
            "tag_name": "v1.19.0",
            "html_url": "https://github.com/jdx/fnox/releases/tag/v1.19.0",
            "body": "notes",
        }
    )
    monkeypatch.setattr(mod, "urlopen", lambda _req: mock_resp)

    fake_hashes = _make_fake_hashes(mod)
    monkeypatch.setattr(mod, "_compute_platform_hashes", lambda _v, _w: fake_hashes)
    monkeypatch.setattr("sys.argv", ["sync_upstream.py", "--dry-run"])

    mod.main()

    captured = capsys.readouterr()
    assert "UPDATED=true" in captured.out
    assert "Dry run" in captured.out
    assert version_file.read_text() == "1.18.0\n"
    assert not hashes_file.exists()
