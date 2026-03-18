from __future__ import annotations

import importlib.util
import json
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


def test_fetch_latest_release_tag_uses_urllib3(mod, monkeypatch) -> None:
    class FakeResponse:
        status = 200
        data = json.dumps({"tag_name": "v1.18.0"}).encode()

    class FakePoolManager:
        def request(self, method: str, url: str, *, headers: dict[str, str]) -> FakeResponse:
            assert method == "GET"
            assert url == mod.GITHUB_LATEST_RELEASE_API_URL
            assert headers == {
                "Accept": "application/vnd.github+json",
                "User-Agent": "fnox-py-release-helper",
            }
            return FakeResponse()

        def clear(self) -> None:
            pass

    monkeypatch.setattr(mod.urllib3, "PoolManager", FakePoolManager)

    assert mod._fetch_latest_release_tag() == "v1.18.0"


def test_fetch_latest_release_tag_raises_for_http_error(mod, monkeypatch) -> None:
    class FakePoolManager:
        def request(self, method: str, url: str, *, headers: dict[str, str]) -> object:
            raise mod.urllib3.exceptions.HTTPError("boom")

        def clear(self) -> None:
            pass

    monkeypatch.setattr(mod.urllib3, "PoolManager", FakePoolManager)

    with pytest.raises(RuntimeError, match="Failed to fetch latest fnox release metadata: boom"):
        mod._fetch_latest_release_tag()


def test_resolve_fnox_version_uses_requested_value(mod) -> None:
    assert mod._resolve_fnox_version("v1.2.3") == "1.2.3"


def test_resolve_fnox_version_fetches_latest_when_missing(mod, monkeypatch) -> None:
    monkeypatch.setattr(mod, "_fetch_latest_release_tag", lambda: "v1.18.0")

    assert mod._resolve_fnox_version(None) == "1.18.0"
