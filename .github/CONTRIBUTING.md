# Contributing

Thank you for your interest in contributing to github-token!

## Getting started

1. Fork and clone the repository
2. Create a virtual environment: `python3 -m venv .venv && source .venv/bin/activate`
3. Install dev dependencies: `uv sync --group dev`
4. Install pre-commit hooks: `pre-commit install`
5. Run the tests: `pytest`

## Development workflow

1. Create a feature branch from `main`
2. Make your changes
3. Ensure all checks pass: `uvx ruff check src/ tests/ && uvx ruff format --check src/ tests/ && uvx ty check src/ tests/ && uv run pytest`
4. Commit with a descriptive message
5. Open a pull request

## Code guidelines

- **Zero external dependencies** in `src/`. Only the Python standard library is allowed in production code. This is a hard requirement -- the Docker image must not run `pip install`.
- Test dependencies (`pytest`) are allowed in `tests/` only.
- All code must pass `ruff check`, `ruff format`, and `ty check`.
- New features should include tests with reasonable coverage.

## Python version lifecycle policy

This project builds images for **actively maintained CPython versions only** (see [Python release cycle](https://devguide.python.org/versions/)).

The supported versions are defined in [`python-versions.json`](../python-versions.json) at the repo root. This file is the **single source of truth** -- all CI workflows, the release pipeline, and the EOL checker read from it. To add or remove a Python version, edit only this file (and update `pyproject.toml` classifiers + `README.md` tag table).

- When a Python version reaches **end-of-life**, it is removed within one release cycle.
- When a **new stable Python version** is released (e.g., 3.14), it is added.
- A monthly automated workflow checks for EOL versions and opens an issue when action is needed.

## Reporting issues

- **Bugs**: Use the [bug report template](ISSUE_TEMPLATE/bug_report.md)
- **Features**: Use the [feature request template](ISSUE_TEMPLATE/feature_request.md)
- **Security**: See [SECURITY.md](SECURITY.md)
