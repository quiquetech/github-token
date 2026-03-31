"""Entry point: ``python -m github_token``."""

from __future__ import annotations

import sys

from github_token.cli import resolve_config, write_output
from github_token.jwt import create_jwt
from github_token.token import get_installation_token


def main() -> None:
    config = resolve_config()

    jwt = create_jwt(config.app_id, config.private_key)

    token = get_installation_token(
        jwt,
        config.installation_id,
        permissions=config.permissions or None,
        repositories=config.repositories or None,
    )

    write_output(token, config)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
