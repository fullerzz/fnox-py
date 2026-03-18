from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

from fnox_py import api
from tests.conftest import make_result


def test_get(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="secret_value\n")
    result = api.get("MY_KEY")
    assert result == "secret_value"
    mock_run.assert_called_once_with(["get", "MY_KEY"], env=None, cwd=None, timeout=None)


def test_get_with_profile_and_base64(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="decoded\n")
    result = api.get("KEY", profile="prod", base64_decode=True)
    assert result == "decoded"
    args = mock_run.call_args[0][0]
    assert args == ["get", "--profile", "prod", "--base64-decode", "KEY"]


def test_export_json(mock_run: MagicMock) -> None:
    data = {"KEY1": "val1", "KEY2": "val2"}
    mock_run.return_value = make_result(stdout=json.dumps(data) + "\n")
    result = api.export_json()
    assert result == data
    mock_run.assert_called_once_with(["export", "--format", "json"], env=None, cwd=None, timeout=None)


def test_export_json_with_profile(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="{}\n")
    api.export_json(profile="staging")
    args = mock_run.call_args[0][0]
    assert args == ["export", "--profile", "staging", "--format", "json"]


def test_schema(mock_run: MagicMock) -> None:
    schema_data: dict[str, Any] = {"type": "object", "properties": {}}
    mock_run.return_value = make_result(stdout=json.dumps(schema_data))
    result = api.schema()
    assert result == schema_data


def test_profiles(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="default\nprod\nstaging\n")
    result = api.profiles()
    assert result == ["default", "prod", "staging"]


def test_profiles_empty(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="")
    result = api.profiles()
    assert result == []


def test_providers(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="aws\nvault\n")
    result = api.providers()
    assert result == ["aws", "vault"]


def test_config_files(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="/etc/fnox.toml\n~/.config/fnox.toml\n")
    result = api.config_files()
    assert result == ["/etc/fnox.toml", "~/.config/fnox.toml"]


def test_lease_create(mock_run: MagicMock) -> None:
    lease_data: dict[str, Any] = {"id": "abc123", "ttl": 3600}
    mock_run.return_value = make_result(stdout=json.dumps(lease_data))
    result = api.lease_create("vault")
    assert result == lease_data
    args = mock_run.call_args[0][0]
    assert args == ["lease", "create", "--format", "json", "vault"]


def test_lease_create_with_options(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="{}")
    api.lease_create("vault", duration="1h", label="test")
    args = mock_run.call_args[0][0]
    assert args == ["lease", "create", "--duration", "1h", "--label", "test", "--format", "json", "vault"]


def test_version(mock_run: MagicMock) -> None:
    mock_run.return_value = make_result(stdout="fnox 1.2.3\n")
    result = api.version()
    assert result == "fnox 1.2.3"
