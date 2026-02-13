"""Tests for write-sync-state.py."""

import importlib
import json

import pytest

write_sync_state = importlib.import_module("write-sync-state")


# --- build_iteration_map ---

class TestBuildIterationMap:
    def test_extracts_created_iterations(self):
        sync_results = {
            "iterations": {
                "created": [
                    {"slug": "epic-2-workspace", "epicId": "2", "devopsId": 430}
                ],
                "failed": [],
                "skipped": [],
                "movements": [],
            }
        }
        result = write_sync_state.build_iteration_map(sync_results)
        assert "epic-2-workspace" in result
        assert result["epic-2-workspace"]["devopsId"] == 430
        assert result["epic-2-workspace"]["epicId"] == "2"

    def test_extracts_skipped_iterations(self):
        sync_results = {
            "iterations": {
                "created": [],
                "failed": [],
                "skipped": [
                    {"slug": "epic-1-foundation", "epicId": "1", "classification": "EXISTS"}
                ],
                "movements": [],
            }
        }
        result = write_sync_state.build_iteration_map(sync_results)
        assert "epic-1-foundation" in result
        assert result["epic-1-foundation"]["epicId"] == "1"

    def test_created_takes_priority_over_skipped(self):
        sync_results = {
            "iterations": {
                "created": [
                    {"slug": "epic-1-test", "epicId": "1", "devopsId": 999}
                ],
                "failed": [],
                "skipped": [
                    {"slug": "epic-1-test", "epicId": "1"}
                ],
                "movements": [],
            }
        }
        result = write_sync_state.build_iteration_map(sync_results)
        assert result["epic-1-test"]["devopsId"] == 999

    def test_does_not_create_entries_from_dict_keys(self):
        """Regression: the old bug wrote 'created', 'failed', 'skipped', 'movements'
        as iteration IDs instead of extracting actual slugs."""
        sync_results = {
            "iterations": {
                "created": [
                    {"slug": "epic-1-real", "epicId": "1", "devopsId": 100}
                ],
                "failed": [],
                "skipped": [],
                "movements": [{"type": "epic", "id": "1", "status": "moved"}],
            }
        }
        result = write_sync_state.build_iteration_map(sync_results)
        assert "created" not in result
        assert "failed" not in result
        assert "skipped" not in result
        assert "movements" not in result
        assert "epic-1-real" in result

    def test_empty_iterations(self):
        sync_results = {"iterations": {"created": [], "failed": [], "skipped": [], "movements": []}}
        result = write_sync_state.build_iteration_map(sync_results)
        assert result == {}


# --- sort_key_numeric ---

class TestSortKeyNumeric:
    def test_simple_numeric(self):
        items = ["2", "10", "1", "3"]
        assert sorted(items, key=write_sync_state.sort_key_numeric) == ["1", "2", "3", "10"]

    def test_dotted_ids(self):
        items = ["1.2", "1.10", "1.1", "2.1"]
        assert sorted(items, key=write_sync_state.sort_key_numeric) == ["1.1", "1.2", "1.10", "2.1"]

    def test_task_ids(self):
        items = ["1.1-T2", "1.1-T1", "1.1-T10"]
        assert sorted(items, key=write_sync_state.sort_key_numeric) == ["1.1-T1", "1.1-T2", "1.1-T10"]


# --- write_sync_state ---

class TestWriteSyncState:
    def test_basic_write(self, tmp_path):
        diff_results = {
            "epics": [
                {"id": "1", "title": "Foundation", "contentHash": "aaa111", "classification": "UNCHANGED", "devopsId": 100}
            ],
            "stories": [
                {"id": "1.1", "epicId": "1", "title": "Setup", "contentHash": "bbb222", "classification": "UNCHANGED", "devopsId": 200}
            ],
            "tasks": [
                {"id": "1.1-T1", "storyId": "1.1", "description": "Do thing", "contentHash": "ccc333", "classification": "UNCHANGED", "devopsId": 300}
            ],
            "iterations": [
                {"slug": "epic-1-foundation", "epicId": "1", "classification": "EXISTS", "devopsId": 429}
            ],
        }
        sync_results = {
            "epicIdMap": {"1": 100},
            "storyIdMap": {"1.1": 200},
            "taskIdMap": {"1.1-T1": 300},
            "iterations": {"created": [], "failed": [], "skipped": [
                {"slug": "epic-1-foundation", "epicId": "1"}
            ], "movements": []},
        }
        config = {"projectName": "Projects", "iterationRootPath": "MyIter"}
        output = str(tmp_path / "sync.yaml")

        counts = write_sync_state.write_sync_state(diff_results, sync_results, config, "2026-01-01T00:00:00Z", output)

        assert counts["epics"] == 1
        assert counts["stories"] == 1
        assert counts["tasks"] == 1
        assert counts["iterations"] == 1

        content = open(output, encoding="utf-8").read()
        assert "epic-1-foundation" in content
        assert "devopsId: 429" in content
        assert 'status: "synced"' in content

    def test_pending_items(self, tmp_path):
        diff_results = {
            "epics": [],
            "stories": [
                {"id": "13.2", "epicId": "13", "title": "Broken", "contentHash": "xxx", "classification": "NEW", "devopsId": None}
            ],
            "tasks": [
                {"id": "1.1-R1.1", "storyId": "1.1", "description": "Review", "contentHash": "yyy", "classification": "UNCHANGED", "devopsId": "None"}
            ],
            "iterations": [],
        }
        sync_results = {
            "epicIdMap": {},
            "storyIdMap": {"13.2": "None"},
            "taskIdMap": {"1.1-R1.1": "None"},
            "iterations": {"created": [], "failed": [], "skipped": [], "movements": []},
        }
        config = {"projectName": "P", "iterationRootPath": ""}
        output = str(tmp_path / "sync.yaml")

        counts = write_sync_state.write_sync_state(diff_results, sync_results, config, "2026-01-01T00:00:00Z", output)

        assert counts["pending_stories"] == 1
        assert counts["pending_tasks"] == 1

        content = open(output, encoding="utf-8").read()
        assert 'status: "pending"' in content

    def test_iteration_from_newly_created(self, tmp_path):
        diff_results = {
            "epics": [
                {"id": "2", "title": "Workspace", "contentHash": "eee", "classification": "CHANGED", "devopsId": 200}
            ],
            "stories": [],
            "tasks": [],
            "iterations": [
                {"slug": "epic-2-workspace", "epicId": "2", "classification": "NEW", "devopsId": None}
            ],
        }
        sync_results = {
            "epicIdMap": {"2": 200},
            "storyIdMap": {},
            "taskIdMap": {},
            "iterations": {
                "created": [{"slug": "epic-2-workspace", "epicId": "2", "devopsId": 430}],
                "failed": [],
                "skipped": [],
                "movements": [],
            },
        }
        config = {"projectName": "Projects", "iterationRootPath": "Product-CaseFusion"}
        output = str(tmp_path / "sync.yaml")

        counts = write_sync_state.write_sync_state(diff_results, sync_results, config, "2026-01-01T00:00:00Z", output)

        assert counts["iterations"] == 1
        content = open(output, encoding="utf-8").read()
        assert "epic-2-workspace" in content
        assert "devopsId: 430" in content
        assert 'epicId: "2"' in content

    def test_orphaned_items_excluded(self, tmp_path):
        diff_results = {
            "epics": [
                {"id": "1", "title": "Keep", "contentHash": "aaa", "classification": "UNCHANGED", "devopsId": 100},
                {"id": "99", "classification": "ORPHANED", "devopsId": 999, "contentHash": "zzz"},
            ],
            "stories": [],
            "tasks": [],
            "iterations": [],
        }
        sync_results = {
            "epicIdMap": {"1": 100},
            "storyIdMap": {},
            "taskIdMap": {},
            "iterations": {"created": [], "failed": [], "skipped": [], "movements": []},
        }
        config = {"projectName": "P", "iterationRootPath": ""}
        output = str(tmp_path / "sync.yaml")

        counts = write_sync_state.write_sync_state(diff_results, sync_results, config, "2026-01-01T00:00:00Z", output)

        assert counts["epics"] == 1
        content = open(output, encoding="utf-8").read()
        assert '"99"' not in content
