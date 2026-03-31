"""Entry point: ``python -m github_token``."""

from __future__ import annotations

import sys

from github_token.cli import Config, resolve_config, write_output
from github_token.jwt import create_jwt
from github_token.token import get_installation_token, list_installations


def _discover_installation_id(jwt: str, config: Config) -> str:
    """Try each installation until a token can be created, return the working ID."""
    installations = list_installations(jwt)
    if not installations:
        raise RuntimeError(
            "No installations found for this GitHub App. "
            "Install the app on an organization or user account first."
        )

    errors: list[str] = []
    for inst in installations:
        inst_id = str(inst.get("id", ""))
        account = inst.get("account", {}).get("login", "unknown")
        if not inst_id:
            continue
        try:
            get_installation_token(
                jwt,
                inst_id,
                permissions=config.permissions or None,
                repositories=config.repositories or None,
            )
        except RuntimeError as exc:
            errors.append(f"  installation {inst_id} ({account}): {exc}")
            continue
        print(
            f"Auto-selected installation {inst_id} (account: {account})",
            file=sys.stderr,
        )
        return inst_id

    raise RuntimeError("Could not obtain a token from any installation:\n" + "\n".join(errors))


def main() -> None:
    try:
        config = resolve_config()

        jwt = create_jwt(config.app_id, config.private_key)

        if config.installation_id is not None:
            installation_id = config.installation_id
        else:
            installation_id = _discover_installation_id(jwt, config)

        token = get_installation_token(
            jwt,
            installation_id,
            permissions=config.permissions or None,
            repositories=config.repositories or None,
        )

        write_output(token, config)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
