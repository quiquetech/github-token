"""Tests for the __main__ entry point and auto-discovery logic."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from github_token.__main__ import _discover_installation_id
from github_token.cli import Config


def _make_config(installation_id: str | None = None) -> Config:
    return Config(
        app_id="123",
        installation_id=installation_id,
        private_key="key",
        permissions={"contents": "read"},
    )


class TestDiscoverInstallationId:
    @patch("github_token.__main__.get_installation_token")
    @patch("github_token.__main__.list_installations")
    def test_picks_first_successful(self, mock_list: MagicMock, mock_token: MagicMock) -> None:
        mock_list.return_value = [
            {"id": 100, "account": {"login": "org-a"}},
            {"id": 200, "account": {"login": "org-b"}},
        ]
        mock_token.side_effect = [
            RuntimeError("GitHub API returned 404: Not Found"),
            "ghs_token_ok",
        ]

        result = _discover_installation_id("jwt", _make_config())
        assert result == "200"
        assert mock_token.call_count == 2

    @patch("github_token.__main__.get_installation_token")
    @patch("github_token.__main__.list_installations")
    def test_picks_first_when_all_succeed(
        self, mock_list: MagicMock, mock_token: MagicMock
    ) -> None:
        mock_list.return_value = [
            {"id": 100, "account": {"login": "org-a"}},
            {"id": 200, "account": {"login": "org-b"}},
        ]
        mock_token.return_value = "ghs_token_ok"

        result = _discover_installation_id("jwt", _make_config())
        assert result == "100"
        assert mock_token.call_count == 1

    @patch("github_token.__main__.get_installation_token")
    @patch("github_token.__main__.list_installations")
    def test_raises_when_all_fail(self, mock_list: MagicMock, mock_token: MagicMock) -> None:
        mock_list.return_value = [
            {"id": 100, "account": {"login": "org-a"}},
            {"id": 200, "account": {"login": "org-b"}},
        ]
        mock_token.side_effect = RuntimeError("404")

        with pytest.raises(RuntimeError, match="Could not obtain a token from any installation"):
            _discover_installation_id("jwt", _make_config())

    @patch("github_token.__main__.list_installations")
    def test_raises_on_empty_installations(self, mock_list: MagicMock) -> None:
        mock_list.return_value = []

        with pytest.raises(RuntimeError, match="No installations found"):
            _discover_installation_id("jwt", _make_config())

    @patch("github_token.__main__.get_installation_token")
    @patch("github_token.__main__.list_installations")
    def test_prints_selected_to_stderr(
        self, mock_list: MagicMock, mock_token: MagicMock, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mock_list.return_value = [
            {"id": 42, "account": {"login": "my-org"}},
        ]
        mock_token.return_value = "ghs_ok"

        _discover_installation_id("jwt", _make_config())
        captured = capsys.readouterr()
        assert "Auto-selected installation 42" in captured.err
        assert "my-org" in captured.err
