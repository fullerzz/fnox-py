alias fmt := format

_default:
    @just --list

# Run pytest test suite
test:
    uv run pytest tests

# Run ruff linter
lint:
    uv run ruff check --fix .

# Run mypy and ty type checkers
typecheck:
    uv run mypy .
    uv run ty .

# Run the ruff formatter
format:
    uv run ruff format .

# Run python script with uv that updates version in pyproject.toml to match FNOX_VERSION.txt
_update-pyproject:
    #!/usr/bin/env -S uv run --script
    from pathlib import Path
    import re

    version = Path("FNOX_VERSION.txt").read_text().strip()
    pyproject = Path("pyproject.toml")
    updated, count = re.subn(r"(?m)^version = \".*\"$", f"version = \"{version}\"", pyproject.read_text(), count=1)
    assert count == 1, "project version not found"
    if count != 1:
        raise ValueError("project version not found")
    pyproject.write_text(updated)

# Sync pyproject version with the bundled fnox version and refresh uv.lock
sync-version: _update-pyproject
    uv sync
