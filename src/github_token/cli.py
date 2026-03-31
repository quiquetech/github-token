"""CLI configuration resolution from environment variables and arguments."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_KEY_PATH = "/etc/github/GITHUB_APP_PRIVATE_KEY"


def _mask_value(value: str, visible: int = 4) -> str:
    """Return a masked version showing only the first *visible* characters."""
    if len(value) <= visible:
        return "***"
    return value[:visible] + "***"


def _mask_token_in_ci(token: str) -> None:
    """Emit a GitHub Actions masking command so the token is redacted from logs."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        print(f"::add-mask::{token}", file=sys.stderr)


@dataclass(frozen=True)
class Config:
    """Resolved runtime configuration."""

    app_id: str
    installation_id: str | None
    private_key: str
    permissions: dict[str, str] = field(default_factory=dict)
    repositories: list[str] = field(default_factory=list)
    output_mode: str = "stdout"
    output_path: str | None = None


def resolve_config() -> Config:
    """Build a ``Config`` from environment variables.

    Raises:
        SystemExit: If required variables are missing or the key cannot be read.
    """
    app_id = os.environ.get("GITHUB_APP_ID", "")
    installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID", "")

    errors: list[str] = []
    if not app_id:
        errors.append("GITHUB_APP_ID is required")
    elif not app_id.isdigit():
        errors.append(
            f"GITHUB_APP_ID must be a numeric App ID (e.g. '123456'), "
            f"got '{_mask_value(app_id)}'. "
            f"This looks like a Client ID -- find the numeric App ID at "
            f"https://github.com/settings/apps/<your-app>/edit"
        )
    if installation_id and not installation_id.isdigit():
        errors.append(
            f"GITHUB_APP_INSTALLATION_ID must be numeric (e.g. '12345678'), "
            f"got '{_mask_value(installation_id)}'"
        )

    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY", "")
    key_path = os.environ.get("GITHUB_APP_PRIVATE_KEY_PATH", _DEFAULT_KEY_PATH)

    if private_key:
        pass
    elif Path(key_path).is_file():
        private_key = Path(key_path).read_text().strip()
    else:
        errors.append(
            f"No private key: set GITHUB_APP_PRIVATE_KEY or mount a file at "
            f"GITHUB_APP_PRIVATE_KEY_PATH (tried {key_path})"
        )

    if errors:
        for msg in errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        raise SystemExit(1)

    permissions = _parse_permissions(os.environ.get("GITHUB_TOKEN_PERMISSIONS", ""))
    repositories = _parse_repositories(os.environ.get("GITHUB_TOKEN_REPOSITORIES", ""))
    output_mode, output_path = _parse_output(os.environ.get("GITHUB_TOKEN_OUTPUT", "stdout"))

    return Config(
        app_id=app_id,
        installation_id=installation_id or None,
        private_key=private_key,
        permissions=permissions,
        repositories=repositories,
        output_mode=output_mode,
        output_path=output_path,
    )


def _parse_permissions(raw: str) -> dict[str, str]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        print("ERROR: GITHUB_TOKEN_PERMISSIONS is not valid JSON", file=sys.stderr)
        raise SystemExit(1) from None
    if not isinstance(parsed, dict):
        print("ERROR: GITHUB_TOKEN_PERMISSIONS must be a JSON object", file=sys.stderr)
        raise SystemExit(1)
    return {str(k): str(v) for k, v in parsed.items()}


def _parse_repositories(raw: str) -> list[str]:
    if not raw.strip():
        return []
    return [r.strip() for r in raw.split(",") if r.strip()]


def _parse_output(raw: str) -> tuple[str, str | None]:
    value = raw.strip()
    if value == "" or value == "stdout":
        return "stdout", None
    if value == "github-output":
        return "github-output", None
    if value.startswith("file:"):
        return "file", value[5:]
    print(
        f"ERROR: GITHUB_TOKEN_OUTPUT must be 'stdout', 'github-output', "
        f"or 'file:<path>', got: {value!r}",
        file=sys.stderr,
    )
    raise SystemExit(1)


def write_output(token: str, config: Config) -> None:
    """Write the token according to the configured output mode."""
    _mask_token_in_ci(token)
    if config.output_mode == "stdout":
        print(token)
    elif config.output_mode == "file":
        assert config.output_path is not None
        Path(config.output_path).write_text(token + "\n")
    elif config.output_mode == "github-output":
        gh_output = os.environ.get("GITHUB_OUTPUT", "")
        if not gh_output:
            print("WARNING: GITHUB_OUTPUT not set, falling back to stdout", file=sys.stderr)
            print(token)
            return
        with open(gh_output, "a") as f:
            f.write(f"token={token}\n")
