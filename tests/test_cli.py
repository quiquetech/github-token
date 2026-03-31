"""Tests for CLI configuration resolution and output writing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from github_token.cli import Config, resolve_config, write_output

if TYPE_CHECKING:
    from pathlib import Path


class TestResolveConfig:
    def test_reads_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv(
            "GITHUB_APP_PRIVATE_KEY",
            "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
        )

        config = resolve_config()
        assert config.app_id == "111"
        assert config.installation_id == "222"
        assert "fake" in config.private_key

    def test_reads_key_from_file(self, monkeypatch: pytest.MonkeyPatch, key_file: Path) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY", raising=False)
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(key_file))

        config = resolve_config()
        assert "-----BEGIN" in config.private_key

    def test_literal_key_takes_precedence(
        self, monkeypatch: pytest.MonkeyPatch, key_file: Path
    ) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "literal-key")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(key_file))

        config = resolve_config()
        assert config.private_key == "literal-key"

    def test_missing_app_id_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_APP_ID", raising=False)
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "key")

        with pytest.raises(SystemExit):
            resolve_config()

    def test_missing_installation_id_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.delenv("GITHUB_APP_INSTALLATION_ID", raising=False)
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "key")

        with pytest.raises(SystemExit):
            resolve_config()

    def test_missing_key_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.delenv("GITHUB_APP_PRIVATE_KEY", raising=False)
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", "/nonexistent/path.pem")

        with pytest.raises(SystemExit):
            resolve_config()

    def test_parses_permissions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "key")
        monkeypatch.setenv("GITHUB_TOKEN_PERMISSIONS", '{"contents":"read","issues":"write"}')

        config = resolve_config()
        assert config.permissions == {"contents": "read", "issues": "write"}

    def test_invalid_permissions_json_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "key")
        monkeypatch.setenv("GITHUB_TOKEN_PERMISSIONS", "not-json")

        with pytest.raises(SystemExit):
            resolve_config()

    def test_parses_repositories(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "key")
        monkeypatch.setenv("GITHUB_TOKEN_REPOSITORIES", "repo-a, repo-b")

        config = resolve_config()
        assert config.repositories == ["repo-a", "repo-b"]

    def test_output_mode_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "key")
        monkeypatch.setenv("GITHUB_TOKEN_OUTPUT", "file:/tmp/token.txt")

        config = resolve_config()
        assert config.output_mode == "file"
        assert config.output_path == "/tmp/token.txt"

    def test_output_mode_github(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "key")
        monkeypatch.setenv("GITHUB_TOKEN_OUTPUT", "github-output")

        config = resolve_config()
        assert config.output_mode == "github-output"

    def test_invalid_output_mode_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GITHUB_APP_ID", "111")
        monkeypatch.setenv("GITHUB_APP_INSTALLATION_ID", "222")
        monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY", "key")
        monkeypatch.setenv("GITHUB_TOKEN_OUTPUT", "invalid")

        with pytest.raises(SystemExit):
            resolve_config()


class TestWriteOutput:
    def test_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        config = Config(
            app_id="1",
            installation_id="2",
            private_key="k",
            output_mode="stdout",
        )
        write_output("ghs_abc", config)
        assert capsys.readouterr().out.strip() == "ghs_abc"

    def test_file(self, tmp_path: Path) -> None:
        out = tmp_path / "token.txt"
        config = Config(
            app_id="1",
            installation_id="2",
            private_key="k",
            output_mode="file",
            output_path=str(out),
        )
        write_output("ghs_abc", config)
        assert out.read_text().strip() == "ghs_abc"

    def test_github_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        gh_out = tmp_path / "github_output"
        gh_out.write_text("")
        monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))

        config = Config(
            app_id="1",
            installation_id="2",
            private_key="k",
            output_mode="github-output",
        )
        write_output("ghs_abc", config)
        assert "token=ghs_abc" in gh_out.read_text()

    def test_github_output_fallback_to_stdout(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        config = Config(
            app_id="1",
            installation_id="2",
            private_key="k",
            output_mode="github-output",
        )
        write_output("ghs_abc", config)
        assert "ghs_abc" in capsys.readouterr().out
