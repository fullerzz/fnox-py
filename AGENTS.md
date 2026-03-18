# AGENTS.md

Guidance for coding agents working in `fnox-py`.

## Scope
- `fnox-py` is a thin Python wrapper around the `fnox` binary.
- Do not reimplement `fnox` behavior in Python; construct argv, invoke the binary, and translate results.
- Prefer small, typed, test-backed changes that preserve the current module boundaries.

## Repository Layout
- `src/fnox_py/`: library code.
- `tests/`: pytest suite.
- `scripts/build_platform_wheel.py`: release helper that builds a pure wheel, injects upstream binaries, and emits platform wheels plus an sdist.
- `pyproject.toml`: package metadata plus Ruff, mypy, and pyright configuration.
- `.pre-commit-config.yaml`: local hook definitions.
- `.github/workflows/ci.yml`: canonical CI commands.
- `.github/workflows/release.yml`: release pipeline and artifact publishing flow.

## Agent Rules Files
- No `.cursor/rules/` directory was found.
- No `.cursorrules` file was found.
- No `.github/copilot-instructions.md` file was found.
- Treat this file as the canonical repo guidance unless those rule files are added later.

## Baseline Facts
- Package manager and task runner: `uv`.
- Build backend: `uv_build`.
- Python requirement: `>=3.12`; local version pin in `.python-version`: `3.14`; Ruff target: `py313`.
- Source layout is `src/`; import the package as `fnox_py`; console entry point is `fnox-py`.
- Runtime behavior depends on finding a real `fnox` binary or the `FNOX_PY_BINARY` override.

## Setup Commands
Run from the repo root.

```bash
uv sync
uv sync --frozen
```

- Use `uv sync --frozen` for CI-parity installs from `uv.lock`.
- Use `uv sync` for normal local setup or dependency refreshes.

## Test Commands
Primary suite:

```bash
uv run pytest -v
```

Useful focused runs:

```bash
uv run pytest tests/test_api.py -v
uv run pytest tests/test_api.py::test_get -q
uv run pytest tests/test_runner.py -v
uv run pytest -k version -v
uv run pytest --maxfail=1 -x
```

- Prefer a single test or single file while iterating, then run the relevant broader suite.
- Tests are mostly isolated unit tests built with `pytest`, `monkeypatch`, `capsys`, and `unittest.mock.patch`.
- Reuse helpers from `tests/conftest.py` such as `write_fake_script()` and `make_result()`.

## Lint, Format, and Type Check

```bash
uv run ruff check src tests scripts
uv run ruff check --fix src tests scripts
uv run ruff format src tests scripts
uv run mypy src
uv run prek run --all-files
```

- CI runs `pytest`, `ruff check`, and `mypy`.
- CI lint paths are `src/ tests/ scripts/`; release linting only covers `src/ tests/`.
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

- `scripts/build_platform_wheel.py` reads `FNOX_VERSION.txt` and `FNOX_HASHES.json` when `--fnox-version` is omitted.
- The release workflow builds platform wheels, runs a wheel-content smoke check, then publishes to TestPyPI and PyPI.

## Architecture Expectations
- Keep the wrapper thin and focused on subprocess orchestration.
- Preserve the current split: `binary.py` for discovery, `runner.py` for subprocess execution, `api.py` for convenience wrappers, `errors.py` for typed exceptions, and `cli.py` for the CLI surface.
- Prefer small functions over new abstraction layers; update `src/fnox_py/__init__.py` deliberately if the public API changes.

## Code Style

### Formatting
- Follow Ruff formatting from `pyproject.toml`.
- Use 4-space indentation and double quotes.
- Keep lines readable; configured line length is `120` and `E501` is ignored, so use judgment instead of packing lines aggressively.
- Let Ruff manage import sorting and trailing commas; default to ASCII unless the file already needs Unicode.

### Imports
- Keep `from __future__ import annotations` first when used; most modules do this.
- Order imports as standard library, third-party, then first-party.
- Prefer `collections.abc` imports such as `Mapping` and `Sequence`; use relative imports inside `src/fnox_py/` and absolute imports from `fnox_py` in tests.
- Avoid unused imports; Ruff enforces this.

### Typing
- Add type hints to new functions, methods, fixtures, and module-level values.
- Prefer built-in generics like `list[str]` and `dict[str, Any]`; prefer `Path` or `str | Path` for filesystem parameters.
- Keep public return types explicit.
- Use `TypedDict` for structured dict-like data when appropriate; the wheel builder already follows this pattern.
- Mypy is strict: `disallow_untyped_defs`, `disallow_any_generics`, `warn_return_any`, and `no_implicit_reexport` are enabled.
- If you must ignore a type error, use a precise code; `ignore-without-code` is enabled.
- Pyright is configured for both `src/**` and `tests/**`, even though CI only runs mypy on `src/`.

### Naming
- Use `snake_case` for modules, functions, variables, and fixtures.
- Use `PascalCase` for exceptions and dataclasses like `FnoxCommandError` and `FnoxResult`; use `UPPER_SNAKE_CASE` for constants like `PLATFORM_MAP`, `VERSION_FILE`, and `HASHES_FILE`.
- Prefix private helpers with `_`.
- Name tests `test_*` and keep names behavior-oriented.

### Error Handling
- Raise repo-specific exceptions from `src/fnox_py/errors.py`.
- Preserve subprocess context; `FnoxCommandError` stores `returncode`, `stdout`, `stderr`, and `cmd`.
- Convert timeout and missing-binary failures into `FnoxTimeoutError` and `FnoxNotFoundError`.
- Do not swallow exceptions silently; avoid broad `except Exception` unless you immediately re-raise a more specific domain error.
- Use `check=False` only when callers intentionally need a non-zero result object.
- In CLI code, print user-facing failures to stderr and exit non-zero.

### Paths, Processes, and Output
- Prefer `pathlib.Path` over manual path-string manipulation.
- Match `runner.py`: use `subprocess.run(..., check=False)` and raise typed errors yourself.
- Keep platform-aware logic explicit and local rather than spreading conditionals across modules.
- Be careful with environment merging; `runner.run()` only merges onto `os.environ` when an override mapping is supplied.
- Avoid process-global state changes except at clear boundaries like `run_passthrough()`.
- Avoid `print()` in library code; `print()` is acceptable in CLI code and scripts when intentional, usually with targeted `# noqa: T201`.

### Security and Lint-Sensitive Patterns
- Ruff enables bugbear, bandit, pathlib, pytest-style, performance, simplify, and logging rules.
- Existing code uses targeted `# noqa` comments for justified subprocess and `print()` calls; keep suppressions narrow and documented by context.
- Avoid shelling out unless the wrapper or release script genuinely needs it.

### Comments and Docstrings
- Keep comments sparse and useful.
- Add docstrings for public functions and fixtures when they clarify behavior.
- Do not add narration comments for obvious code; add targeted comments only around tricky subprocess, packaging, or platform-specific logic.

## Testing Conventions
- Extend the existing pytest style instead of inventing a new harness.
- Prefer isolated unit tests with fake shell scripts and patched binary discovery over real external dependencies.
- Assert exact argv lists when testing command construction.
- When adding exceptions or result objects, test both behavior and stored attributes.
- For CLI behavior, assert stdout, stderr, and exit codes explicitly.

## Change Checklist
- Add or update focused tests.
- Run at least the most relevant single test or test file.
- Run `uv run ruff check src tests scripts` after code changes.
- Run `uv run mypy src` when source typing may be affected.
- Update `src/fnox_py/__init__.py` if you changed the public surface.
- If packaging changes, review `scripts/build_platform_wheel.py` together with `.github/workflows/release.yml`.
