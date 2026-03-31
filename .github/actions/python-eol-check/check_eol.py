# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
# ]
# ///
"""Check supported Python versions against endoflife.date and output EOL status.

Pure logic only -- no side effects (no issue creation, no PR, no comments).
Outputs structured JSON for downstream workflow steps to act on.
Each flagged entry includes ready-to-use title, body, and labels so the
calling workflow can pass them straight to an issue/PR creation action.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

EOL_API = "https://endoflife.date/api/python.json"


def load_versions(path: str) -> list[str]:
    data = json.loads(Path(path).read_text())
    if not isinstance(data, list) or not all(isinstance(v, str) for v in data):
        print(f"::error::{path} must be a JSON array of strings", file=sys.stderr)
        raise SystemExit(1)
    return data


def fetch_eol_dates() -> dict[str, str | bool]:
    """Return {cycle: eol_date_string | False} for all Python cycles."""
    resp = httpx.get(EOL_API, timeout=30)
    resp.raise_for_status()
    return {entry["cycle"]: entry.get("eol", False) for entry in resp.json()}


def build_issue(version: str, eol_date: str, status: str, versions_file: str) -> dict[str, str]:
    """Build a complete issue record ready for an issue-creation action."""
    title = f"Python {version} has reached (or is approaching) end-of-life"
    body = (
        f"## Python {version} EOL Notice\n"
        f"\n"
        f"According to [endoflife.date](https://endoflife.date/python), "
        f"Python {version} reaches end-of-life on **{eol_date}**.\n"
        f"\n"
        f"### Action required\n"
        f"\n"
        f"1. Remove `{version}` from `{versions_file}`\n"
        f"2. Update `pyproject.toml` classifiers and `requires-python`\n"
        f"3. Update `README.md` image tag table\n"
        f"4. Tag a new release to stop publishing "
        f"`{version}-slim` and `{version}-alpine` images\n"
        f"\n"
        f"_This issue was created automatically by the Python EOL Check workflow._\n"
    )
    return {
        "version": version,
        "eol_date": eol_date,
        "status": status,
        "title": title,
        "body": body,
        "labels": "maintenance",
    }


def check(
    versions: list[str],
    eol_map: dict[str, str | bool],
    warn_days: int,
    versions_file: str = "python-versions.json",
) -> list[dict[str, str]]:
    """Return a list of fully-formed issue records for EOL or approaching-EOL versions."""
    today = datetime.now(tz=UTC).date()
    threshold = today + timedelta(days=warn_days)
    flagged: list[dict[str, str]] = []

    for version in versions:
        eol_raw = eol_map.get(version)

        if eol_raw is False or eol_raw is None:
            print(f"::notice::Python {version}: still supported (eol={eol_raw})")
            continue

        eol_date = datetime.strptime(str(eol_raw), "%Y-%m-%d").replace(tzinfo=UTC).date()

        if eol_date <= today:
            status = "eol"
        elif eol_date <= threshold:
            status = "approaching"
        else:
            print(f"::notice::Python {version}: supported until {eol_date}")
            continue

        print(f"::warning::Python {version}: {status} (eol={eol_raw})")
        flagged.append(build_issue(version, str(eol_raw), status, versions_file))

    return flagged


def set_output(name: str, value: str) -> None:
    gh_output = os.environ.get("GITHUB_OUTPUT")
    if gh_output:
        with open(gh_output, "a") as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"  {name}={value}")


def main() -> None:
    versions_file = os.environ.get("INPUT_VERSIONS_FILE", "python-versions.json")
    warn_days = int(os.environ.get("INPUT_WARN_DAYS_BEFORE", "30"))

    versions = load_versions(versions_file)
    eol_map = fetch_eol_dates()
    flagged = check(versions, eol_map, warn_days, versions_file)

    set_output("flagged", json.dumps(flagged))
    set_output("has-eol", json.dumps(len(flagged) > 0))


if __name__ == "__main__":
    main()
