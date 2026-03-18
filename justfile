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
