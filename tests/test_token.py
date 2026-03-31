"""Tests for the GitHub API token exchange."""

from __future__ import annotations

import json
import urllib.error
from http.client import HTTPResponse
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from github_token.token import get_installation_token


def _make_response(body: dict[str, Any], status: int = 200) -> MagicMock:
    """Create a mock HTTPResponse-like context manager."""
    data = json.dumps(body).encode()
    mock = MagicMock()
    mock.read.return_value = data
    mock.status = status
    mock.__enter__ = lambda self: self
    mock.__exit__ = MagicMock(return_value=False)
    return mock


class TestGetInstallationToken:
    @patch("github_token.token.urllib.request.urlopen")
    def test_returns_token(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _make_response({"token": "ghs_abc123"})

        result = get_installation_token("jwt-value", "12345")
        assert result == "ghs_abc123"

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "installations/12345/access_tokens" in request.full_url
        assert request.get_header("Authorization") == "Bearer jwt-value"
        assert request.get_header("Accept") == "application/vnd.github+json"

    @patch("github_token.token.urllib.request.urlopen")
    def test_sends_permissions(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _make_response({"token": "ghs_xyz"})

        get_installation_token(
            "jwt",
            "99",
            permissions={"contents": "read"},
        )

        request = mock_urlopen.call_args[0][0]
        body = json.loads(request.data)
        assert body["permissions"] == {"contents": "read"}

    @patch("github_token.token.urllib.request.urlopen")
    def test_sends_repositories(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _make_response({"token": "ghs_xyz"})

        get_installation_token(
            "jwt",
            "99",
            repositories=["repo-a", "repo-b"],
        )

        request = mock_urlopen.call_args[0][0]
        body = json.loads(request.data)
        assert body["repositories"] == ["repo-a", "repo-b"]

    @patch("github_token.token.urllib.request.urlopen")
    def test_sends_empty_body_when_no_options(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _make_response({"token": "ghs_tok"})

        get_installation_token("jwt", "1")

        request = mock_urlopen.call_args[0][0]
        body = json.loads(request.data)
        assert body == {}

    @patch("github_token.token.urllib.request.urlopen")
    def test_raises_on_http_error(self, mock_urlopen: MagicMock) -> None:
        error_body = BytesIO(b'{"message":"Bad credentials"}')
        mock_response = MagicMock(spec=HTTPResponse)
        mock_response.read.return_value = error_body.read()
        exc = urllib.error.HTTPError(
            url="https://api.github.com/...",
            code=401,
            msg="Unauthorized",
            hdrs=MagicMock(),  # type: ignore[arg-type]
            fp=mock_response,  # type: ignore[arg-type]
        )
        mock_urlopen.side_effect = exc

        with pytest.raises(RuntimeError, match="GitHub API returned 401"):
            get_installation_token("bad-jwt", "1")

    @patch("github_token.token.urllib.request.urlopen")
    def test_raises_on_missing_token_field(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = _make_response({"error": "something"})

        with pytest.raises(RuntimeError, match="no token field"):
            get_installation_token("jwt", "1")

    @patch("github_token.token.urllib.request.urlopen")
    def test_raises_on_url_error(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")

        with pytest.raises(RuntimeError, match="Failed to reach GitHub API"):
            get_installation_token("jwt", "1")
