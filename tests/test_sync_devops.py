"""Tests for sync-devops.py (unit tests for pure functions only — no az CLI calls)."""

import importlib

import pytest

sync_devops = importlib.import_module("sync-devops")


# --- get_story_type ---

class TestGetStoryType:
    def test_agile(self):
        assert sync_devops.get_story_type("Agile") == "User Story"

    def test_scrum(self):
        assert sync_devops.get_story_type("Scrum") == "Product Backlog Item"

    def test_cmmi(self):
        assert sync_devops.get_story_type("CMMI") == "Requirement"

    def test_basic(self):
        assert sync_devops.get_story_type("Basic") == "Issue"

    def test_unknown_defaults(self):
        assert sync_devops.get_story_type("CustomProcess") == "User Story"


# --- get_ac_field ---

class TestGetAcField:
    def test_agile(self):
        assert sync_devops.get_ac_field("Agile") == "Microsoft.VSTS.Common.AcceptanceCriteria"

    def test_basic_returns_none(self):
        assert sync_devops.get_ac_field("Basic") is None


# --- get_complete_state ---

class TestGetCompleteState:
    def test_agile(self):
        assert sync_devops.get_complete_state("Agile") == "Closed"

    def test_scrum(self):
        assert sync_devops.get_complete_state("Scrum") == "Done"

    def test_cmmi(self):
        assert sync_devops.get_complete_state("CMMI") == "Resolved"


# --- map_bmad_status_to_devops_state ---

class TestMapBmadStatus:
    def test_draft_agile(self):
        assert sync_devops.map_bmad_status_to_devops_state("draft", "Agile") == "New"

    def test_in_progress_scrum(self):
        assert sync_devops.map_bmad_status_to_devops_state("in-progress", "Scrum") == "Committed"

    def test_review_maps_like_in_progress(self):
        assert sync_devops.map_bmad_status_to_devops_state("review", "Agile") == "Active"
        assert sync_devops.map_bmad_status_to_devops_state("in-progress", "Agile") == "Active"

    def test_done_cmmi(self):
        assert sync_devops.map_bmad_status_to_devops_state("done", "CMMI") == "Resolved"

    def test_empty_status_returns_none(self):
        assert sync_devops.map_bmad_status_to_devops_state("", "Agile") is None

    def test_none_status_returns_none(self):
        assert sync_devops.map_bmad_status_to_devops_state(None, "Agile") is None

    def test_unknown_status_returns_none(self):
        assert sync_devops.map_bmad_status_to_devops_state("blocked", "Agile") is None

    def test_whitespace_and_case_insensitive(self):
        assert sync_devops.map_bmad_status_to_devops_state("  DONE  ", "Scrum") == "Done"


# --- wrap_html ---

class TestWrapHtml:
    def test_basic(self):
        assert sync_devops.wrap_html("Hello") == "<div>Hello</div>"

    def test_escapes_html(self):
        result = sync_devops.wrap_html("a < b & c > d")
        assert "&lt;" in result
        assert "&amp;" in result
        assert "&gt;" in result
        assert "<div>" in result

    def test_newlines_to_br(self):
        result = sync_devops.wrap_html("line 1\nline 2")
        assert "<br>" in result

    def test_empty(self):
        assert sync_devops.wrap_html("") == ""

    def test_none(self):
        assert sync_devops.wrap_html(None) == ""

    def test_max_len_no_truncation(self):
        result = sync_devops.wrap_html("short", max_len=100)
        assert result == "<div>short</div>"

    def test_max_len_truncates_long_text(self):
        text = "A" * 5000
        result = sync_devops.wrap_html(text, max_len=100)
        assert "truncated" in result
        # The raw text inside the div should be well under 5000 chars
        assert len(result) < 1000

    def test_max_len_zero_means_no_limit(self):
        text = "B" * 5000
        result = sync_devops.wrap_html(text, max_len=0)
        assert "truncated" not in result
        assert "B" * 100 in result


# --- truncate_title ---

class TestTruncateTitle:
    def test_short_title_unchanged(self):
        assert sync_devops.truncate_title("Hello World") == "Hello World"

    def test_exact_255_unchanged(self):
        title = "A" * 255
        assert sync_devops.truncate_title(title) == title

    def test_over_255_truncated(self):
        title = "A" * 300
        result = sync_devops.truncate_title(title)
        assert len(result) == 255
        assert result.endswith("...")

    def test_custom_max_len(self):
        title = "A" * 50
        result = sync_devops.truncate_title(title, max_len=20)
        assert len(result) == 20
        assert result.endswith("...")

    def test_empty_string(self):
        assert sync_devops.truncate_title("") == ""


# --- get_default_iteration ---

class TestGetDefaultIteration:
    def test_with_root_and_project(self):
        config = {"iterationRootPath": "Iterations", "projectName": "MyProject"}
        assert sync_devops.get_default_iteration(config) == "MyProject\\Iterations"

    def test_root_already_includes_project(self):
        config = {"iterationRootPath": "MyProject\\Iterations", "projectName": "MyProject"}
        assert sync_devops.get_default_iteration(config) == "MyProject\\Iterations"

    def test_no_root_returns_empty(self):
        config = {"projectName": "MyProject"}
        assert sync_devops.get_default_iteration(config) == ""

    def test_no_project(self):
        config = {"iterationRootPath": "Iterations"}
        assert sync_devops.get_default_iteration(config) == "Iterations"


# --- find_az_executable ---

class TestFindAzExecutable:
    def test_returns_string(self):
        result = sync_devops.find_az_executable()
        assert isinstance(result, str)
        assert len(result) > 0


# --- detect_template (from detect-template.py) ---

detect_template = importlib.import_module("detect-template")


class TestDetectTemplate:
    def test_agile(self):
        assert detect_template.detect_template(["Epic", "User Story", "Task", "Bug"]) == "Agile"

    def test_scrum(self):
        assert detect_template.detect_template(["Epic", "Product Backlog Item", "Task"]) == "Scrum"

    def test_cmmi(self):
        assert detect_template.detect_template(["Epic", "Requirement", "Task"]) == "CMMI"

    def test_basic(self):
        assert detect_template.detect_template(["Epic", "Issue", "Task"]) == "Basic"

    def test_unknown(self):
        assert detect_template.detect_template(["Custom Type"]) == "Unknown"

    def test_priority_agile_over_basic(self):
        # If both User Story and Issue exist, Agile wins
        assert detect_template.detect_template(["User Story", "Issue"]) == "Agile"
