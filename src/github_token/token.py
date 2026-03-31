"""GitHub App API helpers: list installations and create access tokens."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


def _github_api_request(
    *,
    method: str,
    path: str,
    jwt: str,
    body: dict[str, object] | None = None,
) -> Any:
    """Send an authenticated request to the GitHub API and return parsed JSON.

    Raises:
        RuntimeError: On HTTP or network errors.
    """
    data: bytes | None = json.dumps(body).encode() if body is not None else None

    request = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            **({"Content-Type": "application/json"} if data else {}),
        },
    )

    try:
        with urllib.request.urlopen(request) as response:  # noqa: S310
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode() if exc.fp else "no response body"
        raise RuntimeError(f"GitHub API returned {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach GitHub API: {exc.reason}") from exc


def list_installations(jwt: str) -> list[dict[str, Any]]:
    """Fetch all installations for the authenticated GitHub App.

    Args:
        jwt: A valid GitHub App JWT.

    Returns:
        A list of installation objects as returned by the API.

    Raises:
        ValueError: If *jwt* is empty.
        RuntimeError: If the API request fails.
    """
    if not jwt or not jwt.strip():
        raise ValueError("jwt must be a non-empty string")

    result = _github_api_request(method="GET", path="/app/installations", jwt=jwt)
    if not isinstance(result, list):
        raise RuntimeError(f"Unexpected API response (expected a list): {result}")
    return result


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
        ValueError: If *jwt* or *installation_id* are empty.
        RuntimeError: If the API request fails or the response is unexpected.
    """
    if not jwt or not jwt.strip():
        raise ValueError("jwt must be a non-empty string")
    if not installation_id or not installation_id.strip():
        raise ValueError("installation_id must be a non-empty string")

    body: dict[str, object] = {}
    if permissions:
        body["permissions"] = permissions
    if repositories:
        body["repositories"] = repositories

    result = _github_api_request(
        method="POST",
        path=f"/app/installations/{installation_id}/access_tokens",
        jwt=jwt,
        body=body if body else {},
    )

    token: str | None = result.get("token")
    if not token:
        raise RuntimeError(f"Unexpected API response (no token field): {result}")
    return token
