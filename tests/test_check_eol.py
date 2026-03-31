"""Tests for the Python EOL check action script."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "actions"
    / "python-eol-check"
    / "check_eol.py"
)

spec = importlib.util.spec_from_file_location("check_eol", _SCRIPT_PATH)
assert spec and spec.loader
check_eol = importlib.util.module_from_spec(spec)
sys.modules["check_eol"] = check_eol
spec.loader.exec_module(check_eol)


def _days_from_now(days: int) -> str:
    return (datetime.now(tz=UTC).date() + timedelta(days=days)).isoformat()


# ---- load_versions ----


class TestLoadVersions:
    def test_loads_valid_file(self, tmp_path: Path) -> None:
        f = tmp_path / "versions.json"
        f.write_text('["3.12", "3.13"]')
        assert check_eol.load_versions(str(f)) == ["3.12", "3.13"]

    def test_rejects_non_array(self, tmp_path: Path) -> None:
        f = tmp_path / "versions.json"
        f.write_text('{"3.12": true}')
        with pytest.raises(SystemExit):
            check_eol.load_versions(str(f))

    def test_rejects_non_string_items(self, tmp_path: Path) -> None:
        f = tmp_path / "versions.json"
        f.write_text("[3.12, 3.13]")
        with pytest.raises(SystemExit):
            check_eol.load_versions(str(f))

    def test_empty_array(self, tmp_path: Path) -> None:
        f = tmp_path / "versions.json"
        f.write_text("[]")
        assert check_eol.load_versions(str(f)) == []


# ---- build_issue ----


class TestBuildIssue:
    def test_contains_version_in_title(self) -> None:
        result = check_eol.build_issue("3.11", "2027-10-31", "eol", "python-versions.json")
        assert "3.11" in result["title"]
        assert "end-of-life" in result["title"]

    def test_body_references_eol_date(self) -> None:
        result = check_eol.build_issue("3.11", "2027-10-31", "approaching", "versions.json")
        assert "**2027-10-31**" in result["body"]

    def test_body_references_versions_file(self) -> None:
        result = check_eol.build_issue("3.11", "2027-10-31", "eol", "my-versions.json")
        assert "`my-versions.json`" in result["body"]

    def test_body_lists_action_items(self) -> None:
        result = check_eol.build_issue("3.10", "2026-10-04", "eol", "python-versions.json")
        assert "pyproject.toml" in result["body"]
        assert "README.md" in result["body"]
        assert "3.10-slim" in result["body"]
        assert "3.10-alpine" in result["body"]

    def test_labels_field(self) -> None:
        result = check_eol.build_issue("3.11", "2027-10-31", "eol", "python-versions.json")
        assert result["labels"] == "maintenance"

    def test_all_fields_present(self) -> None:
        result = check_eol.build_issue("3.11", "2027-10-31", "eol", "python-versions.json")
        assert set(result.keys()) == {"version", "eol_date", "status", "title", "body", "labels"}


# ---- check ----


class TestCheck:
    def test_version_not_in_eol_map(self) -> None:
        result = check_eol.check(["3.99"], {}, warn_days=30)
        assert result == []

    def test_version_eol_is_false(self) -> None:
        result = check_eol.check(["3.13"], {"3.13": False}, warn_days=30)
        assert result == []

    def test_version_well_within_support(self) -> None:
        far_future = _days_from_now(365)
        result = check_eol.check(["3.13"], {"3.13": far_future}, warn_days=30)
        assert result == []

    def test_version_already_eol(self) -> None:
        past = _days_from_now(-10)
        result = check_eol.check(["3.8"], {"3.8": past}, warn_days=30)
        assert len(result) == 1
        assert result[0]["version"] == "3.8"
        assert result[0]["status"] == "eol"
        assert result[0]["eol_date"] == past

    def test_version_approaching_eol(self) -> None:
        soon = _days_from_now(15)
        result = check_eol.check(["3.10"], {"3.10": soon}, warn_days=30)
        assert len(result) == 1
        assert result[0]["version"] == "3.10"
        assert result[0]["status"] == "approaching"

    def test_version_exactly_at_threshold(self) -> None:
        boundary = _days_from_now(30)
        result = check_eol.check(["3.11"], {"3.11": boundary}, warn_days=30)
        assert len(result) == 1
        assert result[0]["status"] == "approaching"

    def test_version_one_day_past_threshold(self) -> None:
        just_outside = _days_from_now(31)
        result = check_eol.check(["3.11"], {"3.11": just_outside}, warn_days=30)
        assert result == []

    def test_mixed_versions(self) -> None:
        eol_map: dict[str, Any] = {
            "3.8": _days_from_now(-100),
            "3.12": False,
            "3.13": _days_from_now(500),
            "3.10": _days_from_now(10),
        }
        result = check_eol.check(["3.8", "3.10", "3.12", "3.13"], eol_map, warn_days=30)
        versions = {r["version"] for r in result}
        assert versions == {"3.8", "3.10"}

    def test_custom_warn_days(self) -> None:
        date = _days_from_now(50)
        assert check_eol.check(["3.11"], {"3.11": date}, warn_days=30) == []
        result = check_eol.check(["3.11"], {"3.11": date}, warn_days=60)
        assert len(result) == 1
        assert result[0]["status"] == "approaching"

    def test_flagged_entries_have_issue_fields(self) -> None:
        past = _days_from_now(-5)
        result = check_eol.check(["3.8"], {"3.8": past}, warn_days=30)
        entry = result[0]
        assert "title" in entry
        assert "body" in entry
        assert "labels" in entry
        assert "3.8" in entry["title"]

    def test_custom_versions_file_appears_in_body(self) -> None:
        past = _days_from_now(-5)
        result = check_eol.check(["3.8"], {"3.8": past}, warn_days=30, versions_file="custom.json")
        assert "`custom.json`" in result[0]["body"]


# ---- set_output ----


class TestSetOutput:
    def test_writes_to_github_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        gh_out = tmp_path / "output"
        gh_out.write_text("")
        monkeypatch.setenv("GITHUB_OUTPUT", str(gh_out))

        check_eol.set_output("foo", "bar")
        assert "foo=bar\n" in gh_out.read_text()

    def test_falls_back_to_stdout(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        check_eol.set_output("key", "val")
        assert "key=val" in capsys.readouterr().out
