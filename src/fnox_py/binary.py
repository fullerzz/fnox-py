# Binary discovery for fnox.
#
# Resolution order mirrors prek (MIT, Astral Software Inc.) with an
# additional env-var override and PATH fallback.

from __future__ import annotations

import os
import shutil
import sys
import sysconfig
from fnmatch import fnmatch
from pathlib import Path

from .errors import FnoxNotFoundError

_MODULE_DIR = str(Path(__file__).parent)


def find_fnox_bin() -> str:
    """Return the path to the fnox binary."""

    # 1. Env-var override (hard error if set but missing)
    env_path = os.environ.get("FNOX_PY_BINARY")
    if env_path is not None:
        if Path(env_path).is_file():
            return env_path
        raise FnoxNotFoundError(f"FNOX_PY_BINARY is set to {env_path!r} but the file does not exist")

    fnox_exe = "fnox" + sysconfig.get_config_var("EXE")

    targets: list[str | None] = [
        # 2. Current venv scripts
        sysconfig.get_path("scripts"),
        # 3. Base prefix scripts
        sysconfig.get_path("scripts", vars={"base": sys.base_prefix}),
        # 4. Parent-of-package-root (platform-aware)
        (
            _join(_matching_parents(_MODULE_DIR, "Lib/site-packages/fnox_py"), "Scripts")
            if sys.platform == "win32"
            else _join(_matching_parents(_MODULE_DIR, "lib/python*/site-packages/fnox_py"), "bin")
        ),
        # 5. Adjacent-to-package-root (--target installs)
        _join(_matching_parents(_MODULE_DIR, "fnox_py"), "bin"),
        # 6. User scheme scripts
        sysconfig.get_path("scripts", scheme=sysconfig.get_preferred_scheme("user")),
    ]

    seen: list[str] = []
    for target in targets:
        if not target:
            continue
        if target in seen:
            continue
        seen.append(target)
        candidate = Path(target) / fnox_exe
        if candidate.is_file():
            return str(candidate)

    # 7. PATH fallback (for sdist installs without bundled binary)
    which = shutil.which("fnox")
    if which is not None:
        return which

    locations = "\n".join(f" - {target}" for target in seen)
    raise FnoxNotFoundError(
        f"Could not find the fnox binary in any of the following locations:\n{locations}\n"
        "Install fnox or set the FNOX_PY_BINARY environment variable."
    )


# ---------------------------------------------------------------------------
# Helpers (ported from prek, MIT license, Astral Software Inc.)
# ---------------------------------------------------------------------------


def _matching_parents(path: str, match: str) -> str | None:
    parts = Path(path).parts
    match_parts = match.split("/")
    if len(parts) < len(match_parts):
        return None

    if not all(
        fnmatch(part, match_part) for part, match_part in zip(reversed(parts), reversed(match_parts), strict=False)
    ):
        return None

    return str(Path(*parts[: -len(match_parts)]))


def _join(path: str | None, *parts: str) -> str | None:
    if not path:
        return None
    return str(Path(path).joinpath(*parts))
