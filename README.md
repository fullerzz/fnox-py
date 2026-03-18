# fnox-py

`fnox-py` is a thin Python wrapper around the [`fnox`](https://github.com/jdx/fnox) secrets management tool.

It does not reimplement `fnox` behavior in Python. Instead, it:

- locates a real `fnox` binary
- builds argv for common commands
- runs the binary
- returns parsed results or typed errors

Python requirement: `>=3.12`

> [!NOTE]
> Official fnox project links:
> - GitHub repo: [**jdx/fnox**](https://github.com/jdx/fnox)
> - Fnox docs: [https://fnox.jdx.dev](https://fnox.jdx.dev/)

## Installation

### uv

```bash
uv tool install fnox-py
```

### pip

```bash
pip install fnox-py
```

### Bundled binary vs source install

Platform wheels are intended to bundle the `fnox` binary.

If you install from source instead of a platform wheel, `fnox-py` requires a real `fnox` executable to be available via:

- `PATH`, or
- `FNOX_PY_BINARY=/absolute/path/to/fnox`

Examples:

```bash
pip install --no-binary fnox-py fnox-py
```

```bash
FNOX_PY_BINARY=/usr/local/bin/fnox python -c "import fnox_py; print(fnox_py.version())"
```

## Binary Resolution

At runtime, `fnox-py` resolves the `fnox` binary in this order:

1. `FNOX_PY_BINARY`
2. bundled/installed locations in the current environment
3. bundled/installed fallback locations associated with the base or target install
4. user scheme script location
5. `PATH`

If `FNOX_PY_BINARY` is set but points to a missing file, `fnox-py` raises `FnoxNotFoundError`.

## Python API

```python
from fnox_py import (
    config_files,
    export_json,
    get,
    lease_create,
    profiles,
    providers,
    schema,
    version,
)

value = get("MY_SECRET")
all_values = export_json()
schema_doc = schema()
profile_names = profiles()
provider_names = providers()
config_paths = config_files()
lease = lease_create("vault", duration="1h", label="local-dev")
fnox_version = version()
```

### Common examples

Get a single value:

```python
from fnox_py import get

token = get("API_TOKEN")
```

Get a value from a specific profile:

```python
from fnox_py import get

token = get("API_TOKEN", profile="prod")
```

Decode base64 output:

```python
from fnox_py import get

decoded = get("TLS_CERT", base64_decode=True)
```

Export all secrets as JSON:

```python
from fnox_py import export_json

data = export_json(profile="dev")
```

Inspect schema, profiles, providers, and config files:

```python
from fnox_py import config_files, profiles, providers, schema

print(schema())
print(profiles())
print(providers())
print(config_files())
```

Create a lease:

```python
from fnox_py import lease_create

lease = lease_create("vault", duration="30m", label="ci-job")
```

Get the underlying `fnox` version:

```python
from fnox_py import version

print(version())
```

## CLI

The package installs the `fnox-py` console script.

### Built-in subcommands

Locate the resolved binary:

```bash
fnox-py which
```

Show the wrapper version and attempt to print the underlying `fnox` version:

```bash
fnox-py version
```

Print basic environment diagnostics:

```bash
fnox-py doctor
```

### Passthrough behavior

Any arguments other than `which`, `version`, and `doctor` are passed directly through to `fnox`.

For example:

```bash
fnox-py get MY_SECRET
fnox-py profiles
fnox-py export --format json
```

With no arguments, `fnox-py` runs `fnox` with no extra argv.

## Public API

`fnox-py` currently exports:

- `config_files`
- `export_json`
- `get`
- `lease_create`
- `profiles`
- `providers`
- `schema`
- `version`
- `find_fnox_bin`
- `run`
- `FnoxResult`
- `FnoxCommandError`
- `FnoxError`
- `FnoxNotFoundError`
- `FnoxTimeoutError`

## Errors

Library calls raise typed exceptions:

- `FnoxNotFoundError` when the binary cannot be found
- `FnoxCommandError` when `fnox` exits non-zero
- `FnoxTimeoutError` on subprocess timeout
- `FnoxError` as the base exception type

## Development

This project uses `uv`, `pytest`, `ruff`, and `mypy`.

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run pytest -v
```

Run a single test:

```bash
uv run pytest tests/test_api.py::test_get -q
```

Lint:

```bash
uv run ruff check src tests scripts
```

Type-check:

```bash
uv run mypy src
```

Build distributions:

```bash
uv build
```

## Release / Platform Wheel Build

`scripts/build_platform_wheel.py` builds platform-specific wheels by:

1. building a pure Python wheel
2. downloading upstream `fnox` release binaries
3. injecting the binary into the wheel
4. rewriting wheel metadata
5. building an sdist

The upstream `fnox` version to bundle is read from `FNOX_VERSION.txt` at the repo root by default. To override it, pass `--fnox-version`:

```bash
uv run python scripts/build_platform_wheel.py --fnox-version 1.0.0 --output dist/
```

To bump the bundled version, update `FNOX_VERSION.txt` and commit the change.

## Notes

- `fnox-py` is intentionally small and wrapper-focused.
- For behavior, flags, and command semantics, prefer the upstream `fnox` documentation.
- If you need lower-level control, use `run()` directly and inspect `FnoxResult`.
