# AGENTS.md

Guidance for coding agents working in `fnox-py`.

## Scope
- `fnox-py` is a thin Python wrapper around the `fnox` binary.
- Do not reimplement `fnox` behavior in Python; build argv, invoke the binary, and translate results.
- Prefer small, typed, test-backed changes that preserve the current structure.

## Repository Layout
- `src/fnox_py/`: library code.
- `tests/`: pytest suite.
- `scripts/build_platform_wheel.py`: release helper for bundled platform wheels.
- `pyproject.toml`: packaging, Ruff, mypy, and pyright config.
- `.pre-commit-config.yaml`: hook definitions.
- `.github/workflows/ci.yml`: canonical CI commands.
- `.github/workflows/release.yml`: release and artifact build flow.

## Baseline Facts
- Package manager and task runner: `uv`.
- Build backend: `uv_build`.
- Python requirement: `>=3.12`.
- Local pin in `.python-version`: `3.14`.
- Ruff target version: `py313`.
- Source layout is `src/`; import the package as `fnox_py`.

## Agent Rules Files
- No `.cursor/rules/` directory was found.
- No `.cursorrules` file was found.
- No `.github/copilot-instructions.md` file was found.
- Treat this file as the canonical repo guidance unless new agent-rule files are added.

## Setup Commands
Run from the repo root.

```bash
uv sync
uv sync --frozen
```

- Use `uv sync --frozen` for CI-parity with `uv.lock`.
- Use `uv sync` for normal local setup or dependency refreshes.

## Test Commands
Primary command:

```bash
uv run pytest -v
```

Common focused runs:

```bash
uv run pytest tests/test_api.py -v
uv run pytest tests/test_api.py::test_get -q
uv run pytest -k version -v
uv run pytest --maxfail=1 -x
```

- `uv run pytest tests/test_api.py::test_get -q` is confirmed to work here.
- Prefer a single test or single file while iterating, then run the relevant broader suite.
- Tests rely heavily on `pytest`, `monkeypatch`, `capsys`, and `unittest.mock.patch`.

## Lint, Format, and Type Check

```bash
uv run ruff check src tests scripts
uv run ruff check --fix src tests scripts
uv run ruff format src tests scripts
uv run mypy src
uv run prek run --all-files
```

- `uv run ruff check src tests scripts` is confirmed to pass.
- `uv run mypy src` is confirmed to pass.
- CI runs `pytest`, `ruff check`, and `mypy`; it does not run `ruff format` automatically.
- Pre-commit hooks cover YAML validation, EOF/trailing-whitespace fixes, `uv-lock`, Ruff, and gitleaks.

## Build and Smoke Commands

```bash
uv build
uv build --wheel --out-dir dist
uv build --sdist --out-dir dist
uv run python scripts/build_platform_wheel.py --fnox-version 1.0.0 --output dist/
uv run fnox-py which
uv run fnox-py version
uv run fnox-py doctor
```

- The release script builds a pure wheel, injects upstream `fnox` binaries, rewrites wheel metadata, and then builds an sdist.
- The console entry point is `fnox-py`.
- Runtime behavior depends on discovering a real `fnox` binary or the `FNOX_PY_BINARY` override.

## Code Style

### Formatting
- Follow Ruff formatting from `pyproject.toml`.
- Use 4-space indentation and double quotes.
- Keep lines readable; configured line length is `120`.
- Allow trailing commas where Ruff would add them.
- Default to ASCII unless the file already needs Unicode.

### Imports
- Keep `from __future__ import annotations` first when used; the codebase does this almost everywhere.
- Order imports as standard library, third-party, then first-party.
- Prefer `collections.abc` imports such as `Mapping` and `Sequence`.
- Use relative imports inside `src/fnox_py/`.
- Use absolute imports from `fnox_py` inside tests.
- Avoid unused imports; Ruff enforces this.

### Typing
- Add type hints to new functions, methods, fixtures, and module-level values.
- Prefer built-in generics like `list[str]` and `dict[str, Any]`.
- Prefer `Path` or `str | Path` for filesystem parameters.
- Keep public return types explicit.
- Mypy is strict: `disallow_untyped_defs`, `disallow_any_generics`, `warn_return_any`, and `no_implicit_reexport` are enabled.
- If you must ignore a type error, use a precise code; `ignore-without-code` is enabled.
- Pyright is configured for `src/**` and `tests/**`, even though CI only runs mypy on `src/`.

### Naming
- Use `snake_case` for modules, functions, variables, and fixtures.
- Use `PascalCase` for exceptions and dataclasses like `FnoxCommandError` and `FnoxResult`.
- Use `UPPER_SNAKE_CASE` for constants like `PLATFORM_MAP`.
- Prefix private helpers with `_`.
- Name tests `test_*` and keep names behavior-oriented.

### Design Conventions
- Keep the wrapper thin and focused.
- Preserve the existing split: `binary.py` for discovery, `runner.py` for subprocess execution, `api.py` for convenience wrappers, `errors.py` for typed exceptions, and `cli.py` for the small CLI.
- Prefer small functions over new abstractions.
- Update `src/fnox_py/__init__.py` and `__all__` deliberately when the public API changes.

### Error Handling
- Raise repo-specific exceptions from `src/fnox_py/errors.py`.
- Preserve useful subprocess context; `FnoxCommandError` stores `returncode`, `stdout`, `stderr`, and `cmd`.
- Convert timeout and missing-binary failures into `FnoxTimeoutError` and `FnoxNotFoundError`.
- Do not swallow exceptions silently.
- Avoid broad `except Exception` unless you immediately re-raise a more specific domain error.
- Use `check=False` only when callers intentionally need a non-zero result object.
- In CLI code, print user-facing failures to stderr and exit non-zero.

### Paths, Processes, and Output
- Prefer `pathlib.Path` over manual path-string manipulation.
- Match `runner.py`: use `subprocess.run(..., check=False)` and raise typed errors yourself.
- Keep platform-aware logic explicit and local.
- Be careful with env merging; current code only merges onto `os.environ` when an override is supplied.
- Avoid process-global state changes except at clear boundaries like `run_passthrough()`.
- Avoid `print()` in library code.
- `print()` is acceptable in CLI code and scripts with targeted `# noqa: T201` when intentional.

### Comments and Docstrings
- Keep comments sparse and useful.
- Add docstrings for public functions and fixtures when they clarify behavior.
- Do not add narration comments for obvious code.
- Targeted explanatory comments are fine around tricky or ported logic.

## Testing Conventions
- Extend the existing pytest style instead of inventing a new harness.
- Reuse helpers in `tests/conftest.py`, especially `write_fake_script()` and `make_result()`.
- Prefer isolated unit tests with fake shell scripts and patched binary discovery over real external dependencies.
- Assert on exact argv lists when testing command construction.
- When adding exceptions or result objects, test both behavior and stored attributes.

## Change Checklist
- Add or update focused tests.
- Run at least the most relevant single test or test file.
- Run `uv run ruff check src tests scripts` after code changes.
- Run `uv run mypy src` when source typing may be affected.
- Update `src/fnox_py/__init__.py` if you changed the public surface.
- If packaging changes, review `scripts/build_platform_wheel.py` together with `.github/workflows/release.yml`.
