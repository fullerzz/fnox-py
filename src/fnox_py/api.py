from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import runner


def get(
    key: str,
    *,
    profile: str | None = None,
    base64_decode: bool = False,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> str:
    """Get a single secret value by key."""
    args: list[str] = ["get"]
    if profile is not None:
        args.extend(["--profile", profile])
    if base64_decode:
        args.append("--base64-decode")
    args.append(key)
    result = runner.run(args, env=env, cwd=cwd, timeout=timeout)
    return result.stdout.rstrip("\n")


def export_json(
    *,
    profile: str | None = None,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> dict[str, str]:
    """Export all secrets as a JSON dictionary."""
    args: list[str] = ["export"]
    if profile is not None:
        args.extend(["--profile", profile])
    args.extend(["--format", "json"])
    result = runner.run(args, env=env, cwd=cwd, timeout=timeout)
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def schema(
    *,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Return the fnox JSON schema."""
    result = runner.run(["schema"], timeout=timeout)
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def profiles(
    *,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> list[str]:
    """List available profiles."""
    result = runner.run(["profiles"], env=env, cwd=cwd, timeout=timeout)
    return result.stdout.strip().splitlines()


def providers(
    *,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> list[str]:
    """List available providers."""
    result = runner.run(["providers"], env=env, cwd=cwd, timeout=timeout)
    return result.stdout.strip().splitlines()


def config_files(
    *,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> list[str]:
    """List config file paths."""
    result = runner.run(["config-files"], env=env, cwd=cwd, timeout=timeout)
    return result.stdout.strip().splitlines()


def lease_create(
    backend: str,
    *,
    duration: str | None = None,
    label: str | None = None,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Create a lease and return its metadata."""
    args: list[str] = ["lease", "create"]
    if duration is not None:
        args.extend(["--duration", duration])
    if label is not None:
        args.extend(["--label", label])
    args.extend(["--format", "json", backend])
    result = runner.run(args, env=env, cwd=cwd, timeout=timeout)
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def version(
    *,
    timeout: float | None = None,
) -> str:
    """Return the fnox version string."""
    result = runner.run(["version"], timeout=timeout)
    return result.stdout.strip()
