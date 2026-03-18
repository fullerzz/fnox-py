from __future__ import annotations

import sys

from .binary import find_fnox_bin
from .errors import FnoxNotFoundError
from .runner import run, run_passthrough


def main() -> None:
    if len(sys.argv) < 2:
        run_passthrough([])
        return

    subcmd = sys.argv[1]

    if subcmd == "which":
        _cmd_which()
    elif subcmd == "version":
        _cmd_version()
    elif subcmd == "doctor":
        _cmd_doctor()
    else:
        run_passthrough(sys.argv[1:])


def _cmd_which() -> None:
    try:
        path = find_fnox_bin()
    except FnoxNotFoundError as exc:
        print(str(exc), file=sys.stderr)  # noqa: T201
        sys.exit(1)
    print(path)  # noqa: T201


def _cmd_version() -> None:
    from importlib.metadata import version as pkg_version

    wrapper_version = pkg_version("fnox-py")
    print(f"fnox-py {wrapper_version}")  # noqa: T201
    try:
        result = run(["version"], check=False)
        print(result.stdout.strip())  # noqa: T201
    except FnoxNotFoundError:
        print("fnox binary not found", file=sys.stderr)  # noqa: T201


def _cmd_doctor() -> None:
    import shutil
    from importlib.metadata import version as pkg_version

    print(f"fnox-py {pkg_version('fnox-py')}")  # noqa: T201
    print(f"Python  {sys.version}")  # noqa: T201
    try:
        path = find_fnox_bin()
        print(f"Binary  {path}")  # noqa: T201
        is_bundled = shutil.which("fnox") != path
        print(f"Bundled {is_bundled}")  # noqa: T201
        result = run(["version"], check=False)
        print(f"fnox    {result.stdout.strip()}")  # noqa: T201
    except FnoxNotFoundError as exc:
        print(f"Binary  NOT FOUND: {exc}", file=sys.stderr)  # noqa: T201
