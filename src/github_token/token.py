"""Exchange a GitHub App JWT for a short-lived installation access token."""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def get_installation_token(
    jwt: str,
    installation_id: str,
    permissions: dict[str, str] | None = None,
    repositories: list[str] | None = None,
) -> str:
    """Request an installation access token from the GitHub API.

    Args:
        jwt: A valid GitHub App JWT.
        installation_id: The target installation ID.
        permissions: Optional mapping of permission names to access levels.
        repositories: Optional list of repository names to scope the token to.

    Returns:
        The installation access token string.

    Raises:
        RuntimeError: If the API request fails or the response is unexpected.
    """
    url = f"api.github.com/app/installations/{installation_id}/access_tokens"

    body: dict[str, object] = {}
    if permissions:
        body["permissions"] = permissions
    if repositories:
        body["repositories"] = repositories

    data = json.dumps(body).encode() if body else b"{}"

    request = urllib.request.Request(
        f"https://{url}",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:  # noqa: S310
            result = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else "no response body"
        raise RuntimeError(f"GitHub API returned {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach GitHub API: {exc.reason}") from exc

    token: str | None = result.get("token")
    if not token:
        raise RuntimeError(f"Unexpected API response (no token field): {result}")
    return token
