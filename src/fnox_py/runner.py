from __future__ import annotations

import dataclasses
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from .binary import find_fnox_bin
from .errors import FnoxCommandError, FnoxNotFoundError, FnoxTimeoutError


@dataclasses.dataclass(frozen=True, slots=True)
class FnoxResult:
    returncode: int
    stdout: str
    stderr: str
    cmd: list[str]


def run(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
    check: bool = True,
    timeout: float | None = None,
    input: str | None = None,
) -> FnoxResult:
    """Run fnox with the given arguments and return the result."""
    fnox = find_fnox_bin()
    cmd = [fnox, *args]

    run_env: dict[str, str] | None = None
    if env is not None:
        run_env = {**os.environ, **env}

    try:
        proc = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            env=run_env,
            cwd=cwd,
            timeout=timeout,
            input=input,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FnoxTimeoutError(f"fnox timed out after {exc.timeout}s") from exc
    except FileNotFoundError as exc:
        raise FnoxNotFoundError(str(exc)) from exc

    result = FnoxResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        cmd=cmd,
    )

    if check and proc.returncode != 0:
        raise FnoxCommandError(proc.returncode, proc.stdout, proc.stderr, cmd)

    return result


def run_passthrough(
    args: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    cwd: str | Path | None = None,
) -> int:
    """Run fnox, forwarding stdio directly. On Unix, replaces the process."""
    fnox = find_fnox_bin()
    cmd = [fnox, *args]

    if sys.platform == "win32":
        try:
            proc = subprocess.run(cmd, env=env, cwd=cwd, check=False)  # noqa: S603
        except KeyboardInterrupt:
            sys.exit(2)
        sys.exit(proc.returncode)
    else:
        if env is not None:
            os.environ.update(env)
        if cwd is not None:
            os.chdir(cwd)
        os.execvp(fnox, cmd)  # noqa: S606
