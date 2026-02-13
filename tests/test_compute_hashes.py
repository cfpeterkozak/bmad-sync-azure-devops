"""Tests for compute-hashes.py."""

import importlib

import pytest

compute_hashes = importlib.import_module("compute-hashes")


# --- normalize ---

class TestNormalize:
    def test_basic(self):
        assert compute_hashes.normalize("  Hello  World  ") == "hello world"

    def test_collapse_whitespace(self):
        assert compute_hashes.normalize("a   b\n\nc") == "a b c"

    def test_empty(self):
        assert compute_hashes.normalize("") == ""

    def test_none(self):
        assert compute_hashes.normalize(None) == ""

    def test_tabs_and_newlines(self):
        assert compute_hashes.normalize("\t  foo\tbar\n  ") == "foo bar"


# --- normalize_list ---

class TestNormalizeList:
    def test_basic(self):
        assert compute_hashes.normalize_list(["B", "A", "C"]) == "a,b,c"

    def test_empty_list(self):
        assert compute_hashes.normalize_list([]) == ""

    def test_none(self):
        assert compute_hashes.normalize_list(None) == ""

    def test_with_whitespace(self):
        assert compute_hashes.normalize_list([" FR-1 ", "  ARCH-2  "]) == "arch-2,fr-1"

    def test_filters_empty_strings(self):
        assert compute_hashes.normalize_list(["A", "", "  ", "B"]) == "a,b"


# --- compute_hash ---

class TestComputeHash:
    def test_deterministic(self):
        h1 = compute_hashes.compute_hash("test")
        h2 = compute_hashes.compute_hash("test")
        assert h1 == h2

    def test_length(self):
        h = compute_hashes.compute_hash("anything")
        assert len(h) == 12

    def test_hex_chars(self):
        h = compute_hashes.compute_hash("test input")
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_inputs(self):
        h1 = compute_hashes.compute_hash("input A")
        h2 = compute_hashes.compute_hash("input B")
        assert h1 != h2


# --- hash_epic ---

class TestHashEpic:
    def test_basic(self):
        epic = {"id": "1", "title": "Foundation", "description": "Desc", "phase": "Alpha", "requirements": []}
        h = compute_hashes.hash_epic(epic)
        assert len(h) == 12

    def test_status_changes_hash(self):
        epic = {"id": "1", "title": "Test", "description": "", "phase": "", "requirements": []}
        h_no_status = compute_hashes.hash_epic(epic)
        h_with_status = compute_hashes.hash_epic(epic, {"1": "in-progress"})
        assert h_no_status != h_with_status

    def test_different_status_different_hash(self):
        epic = {"id": "1", "title": "Test", "description": "", "phase": "", "requirements": []}
        h1 = compute_hashes.hash_epic(epic, {"1": "in-progress"})
        h2 = compute_hashes.hash_epic(epic, {"1": "done"})
        assert h1 != h2

    def test_no_status_for_epic(self):
        epic = {"id": "1", "title": "Test", "description": "", "phase": "", "requirements": []}
        h1 = compute_hashes.hash_epic(epic, {"2": "in-progress"})  # different epic ID
        h2 = compute_hashes.hash_epic(epic)  # no statuses at all
        assert h1 == h2  # both have empty status for epic 1

    def test_whitespace_insensitive(self):
        e1 = {"id": "1", "title": "  Test  Epic  ", "description": "  desc  ", "phase": "", "requirements": []}
        e2 = {"id": "1", "title": "Test Epic", "description": "desc", "phase": "", "requirements": []}
        assert compute_hashes.hash_epic(e1) == compute_hashes.hash_epic(e2)

    def test_requirements_order_insensitive(self):
        e1 = {"id": "1", "title": "T", "description": "", "phase": "", "requirements": ["FR-2", "FR-1"]}
        e2 = {"id": "1", "title": "T", "description": "", "phase": "", "requirements": ["FR-1", "FR-2"]}
        assert compute_hashes.hash_epic(e1) == compute_hashes.hash_epic(e2)


# --- hash_story ---

class TestHashStory:
    def test_basic(self):
        story = {"id": "1.1", "title": "Setup", "userStoryText": "As a...", "acceptanceCriteria": ""}
        h = compute_hashes.hash_story(story)
        assert len(h) == 12

    def test_status_changes_hash(self):
        story = {"id": "1.1", "title": "Setup", "userStoryText": "", "acceptanceCriteria": ""}
        h1 = compute_hashes.hash_story(story)
        h2 = compute_hashes.hash_story(story, {"1.1": "done"})
        assert h1 != h2


# --- hash_task ---

class TestHashTask:
    def test_incomplete(self):
        task = {"description": "Do thing", "complete": False}
        h = compute_hashes.hash_task(task)
        assert len(h) == 12

    def test_complete_changes_hash(self):
        t1 = {"description": "Do thing", "complete": False}
        t2 = {"description": "Do thing", "complete": True}
        assert compute_hashes.hash_task(t1) != compute_hashes.hash_task(t2)

    def test_description_changes_hash(self):
        t1 = {"description": "Task A", "complete": False}
        t2 = {"description": "Task B", "complete": False}
        assert compute_hashes.hash_task(t1) != compute_hashes.hash_task(t2)

    def test_new_fields_do_not_affect_hash(self):
        """Enriched fields (priority, tags, subtaskHtml, acReferences, etc.) must not change hash."""
        base = {"description": "Do thing", "complete": False}
        enriched = {
            "description": "Do thing",
            "complete": False,
            "priority": 1,
            "tags": ["AI-Review"],
            "subtaskHtml": "<div><ul><li>sub</li></ul></div>",
            "acReferences": [1, 3],
            "cleanTitle": "Do thing",
            "filePath": "src/foo.py:42",
            "isReviewFollowup": True,
            "reviewRound": 1,
        }
        assert compute_hashes.hash_task(base) == compute_hashes.hash_task(enriched)


# --- generate_iteration_slug ---

class TestGenerateIterationSlug:
    def test_basic(self):
        slug = compute_hashes.generate_iteration_slug("1", "Foundation Infrastructure")
        assert slug == "epic-1-foundation-infrastructure"

    def test_special_chars_removed(self):
        slug = compute_hashes.generate_iteration_slug("2", "Security & Access Control!")
        assert slug == "epic-2-security-access-control"

    def test_long_title_truncated(self):
        long_title = "A" * 200
        slug = compute_hashes.generate_iteration_slug("1", long_title)
        assert len(slug) <= 128
        assert slug.startswith("epic-1-")
        assert not slug.endswith("-")

    def test_no_trailing_hyphens(self):
        slug = compute_hashes.generate_iteration_slug("1", "Test---")
        assert not slug.endswith("-")

    def test_numeric_title(self):
        slug = compute_hashes.generate_iteration_slug("3", "Phase 1 Setup")
        assert slug == "epic-3-phase-1-setup"

    def test_real_world_title(self):
        slug = compute_hashes.generate_iteration_slug("1", "Platform Operator Runtime Readiness")
        assert slug == "epic-1-platform-operator-runtime-readiness"


# --- load_sync_state ---

class TestLoadSyncState:
    def test_empty_path(self):
        result = compute_hashes.load_sync_state("")
        assert result == {"epics": {}, "stories": {}, "tasks": {}, "iterations": {}}

    def test_none_path(self):
        result = compute_hashes.load_sync_state(None)
        assert result == {"epics": {}, "stories": {}, "tasks": {}, "iterations": {}}

    def test_nonexistent_file(self):
        result = compute_hashes.load_sync_state("/nonexistent.yaml")
        assert result == {"epics": {}, "stories": {}, "tasks": {}, "iterations": {}}

    def test_basic_sync_state(self, tmp_file):
        content = (
            "epics:\n"
            '  "1":\n'
            "    devopsId: 12345\n"
            '    contentHash: "abc123def456"\n'
            '  "2":\n'
            "    devopsId: 12399\n"
            '    contentHash: "xyz"\n'
            "stories:\n"
            '  "1.1":\n'
            "    devopsId: 12346\n"
            "    epicDevopsId: 12345\n"
            '    contentHash: "def456ghi789"\n'
            '  "1.2":\n'
            "    devopsId: 12347\n"
            '    contentHash: "ghi"\n'
            "tasks:\n"
            "iterations:\n"
        )
        path = tmp_file(content, "sync.yaml")
        result = compute_hashes.load_sync_state(path)
        assert result["epics"]["1"]["devopsId"] == 12345
        assert result["epics"]["1"]["contentHash"] == "abc123def456"
        assert result["epics"]["2"]["devopsId"] == 12399
        assert result["stories"]["1.1"]["devopsId"] == 12346
        assert result["stories"]["1.1"]["epicDevopsId"] == 12345

    def test_last_item_per_section_saved(self, tmp_file):
        """Ensure the last item before a section transition is not lost."""
        content = (
            "epics:\n"
            '  "1":\n'
            "    devopsId: 100\n"
            '    contentHash: "aaa"\n'
            "stories:\n"
            '  "1.1":\n'
            "    devopsId: 200\n"
            '    contentHash: "bbb"\n'
            "tasks:\n"
            '  "1.1-T1":\n'
            "    devopsId: 300\n"
            '    contentHash: "ccc"\n'
            "iterations:\n"
            "  epic-1-test:\n"
            '    epicId: "1"\n'
        )
        path = tmp_file(content, "sync.yaml")
        result = compute_hashes.load_sync_state(path)
        # Each section has exactly 1 item — all must be preserved
        assert result["epics"]["1"]["devopsId"] == 100
        assert result["stories"]["1.1"]["devopsId"] == 200
        assert result["tasks"]["1.1-T1"]["devopsId"] == 300
        assert result["iterations"]["epic-1-test"]["epicId"] == "1"

    def test_iteration_with_epicId(self, tmp_file):
        content = (
            "iterations:\n"
            "  epic-1-foundation:\n"
            '    epicId: "1"\n'
            '    devopsId: "guid-here"\n'
        )
        path = tmp_file(content, "sync.yaml")
        result = compute_hashes.load_sync_state(path)
        assert result["iterations"]["epic-1-foundation"]["epicId"] == "1"

    def test_empty_value_property_not_treated_as_id(self, tmp_file):
        """Regression: 4-space-indented empty-value lines like 'epicDevopsId: '
        must NOT be misinterpreted as 2-space item ID lines."""
        content = (
            "stories:\n"
            '  "1.1":\n'
            "    devopsId: 13327\n"
            "    epicDevopsId: \n"
            '    contentHash: "abc123def456"\n'
            '  "1.2":\n'
            "    devopsId: 13328\n"
            "    epicDevopsId: \n"
            '    contentHash: "xyz789"\n'
            "tasks:\n"
            '  "1.1-T1":\n'
            "    devopsId: 13400\n"
            "    storyDevopsId: \n"
            '    contentHash: "task111"\n'
        )
        path = tmp_file(content, "sync.yaml")
        result = compute_hashes.load_sync_state(path)
        # Stories must retain their contentHash (not lost to phantom items)
        assert result["stories"]["1.1"]["devopsId"] == 13327
        assert result["stories"]["1.1"]["contentHash"] == "abc123def456"
        assert result["stories"]["1.2"]["devopsId"] == 13328
        assert result["stories"]["1.2"]["contentHash"] == "xyz789"
        # Tasks must retain their contentHash too
        assert result["tasks"]["1.1-T1"]["devopsId"] == 13400
        assert result["tasks"]["1.1-T1"]["contentHash"] == "task111"
        # No phantom items should exist
        assert "epicDevopsId" not in result["stories"]
        assert "storyDevopsId" not in result["tasks"]


# --- classify_items ---

class TestClassifyItems:
    def test_new_item(self):
        parsed = [{"id": "1", "title": "Test"}]
        stored = {}
        results = compute_hashes.classify_items(parsed, stored, lambda x: "hash123")
        assert len(results) == 1
        assert results[0]["classification"] == "NEW"
        assert results[0]["contentHash"] == "hash123"

    def test_unchanged_item(self):
        parsed = [{"id": "1", "title": "Test"}]
        stored = {"1": {"contentHash": "hash123", "devopsId": 100}}
        results = compute_hashes.classify_items(parsed, stored, lambda x: "hash123")
        assert results[0]["classification"] == "UNCHANGED"
        assert results[0]["devopsId"] == 100

    def test_changed_item(self):
        parsed = [{"id": "1", "title": "Updated"}]
        stored = {"1": {"contentHash": "oldhash", "devopsId": 100}}
        results = compute_hashes.classify_items(parsed, stored, lambda x: "newhash")
        assert results[0]["classification"] == "CHANGED"

    def test_orphaned_item(self):
        parsed = []
        stored = {"1": {"contentHash": "hash123", "devopsId": 100}}
        results = compute_hashes.classify_items(parsed, stored, lambda x: "hash123")
        assert len(results) == 1
        assert results[0]["classification"] == "ORPHANED"
        assert results[0]["id"] == "1"

    def test_mixed(self):
        parsed = [
            {"id": "1", "title": "Same"},
            {"id": "2", "title": "Changed"},
            {"id": "3", "title": "Brand New"},
        ]
        stored = {
            "1": {"contentHash": "aaa", "devopsId": 10},
            "2": {"contentHash": "bbb", "devopsId": 20},
            "4": {"contentHash": "ddd", "devopsId": 40},
        }

        def hash_fn(item):
            return {"1": "aaa", "2": "ccc", "3": "eee"}[item["id"]]

        results = compute_hashes.classify_items(parsed, stored, hash_fn)
        by_id = {r["id"]: r["classification"] for r in results}
        assert by_id["1"] == "UNCHANGED"
        assert by_id["2"] == "CHANGED"
        assert by_id["3"] == "NEW"
        assert by_id["4"] == "ORPHANED"


# --- EXISTS iteration filtering ---

class TestExistsIterationFiltering:
    """Verify that EXISTS iterations only include NEW items, not already-synced ones."""

    def _run_main_logic(self, parsed, sync_state):
        """Run the iteration derivation logic from compute-hashes main().

        Extracted here to test the filtering without invoking argparse.
        """
        epic_statuses = parsed.get("epicStatuses", {})
        stored_iterations = sync_state.get("iterations", {})

        story_ids_by_epic = {}
        for story in parsed.get("stories", []):
            eid = story.get("epicId", "")
            if eid:
                story_ids_by_epic.setdefault(eid, []).append(story["id"])

        task_ids_by_story = {}
        for task in parsed.get("tasks", []):
            sid = task.get("storyId", "")
            if sid:
                task_ids_by_story.setdefault(sid, []).append(task["id"])

        iteration_results = []
        for epic in parsed.get("epics", []):
            epic_id = epic.get("id", "")
            status = epic_statuses.get(epic_id, "")
            if status not in ("in-progress", "done"):
                continue

            existing_slug = None
            for slug, iter_data in stored_iterations.items():
                if iter_data.get("epicId") == epic_id:
                    existing_slug = slug
                    break

            slug = existing_slug or compute_hashes.generate_iteration_slug(epic_id, epic.get("title", ""))

            epic_story_ids = story_ids_by_epic.get(epic_id, [])
            epic_task_ids = []
            for sid in epic_story_ids:
                epic_task_ids.extend(task_ids_by_story.get(sid, []))

            stored = stored_iterations.get(slug, {})
            has_devops_id = stored.get("devopsId") not in (None, "", "None")
            if slug in stored_iterations and has_devops_id:
                new_story_ids = [sid for sid in epic_story_ids
                                 if sid not in sync_state.get("stories", {})]
                new_task_ids = [tid for tid in epic_task_ids
                                if tid not in sync_state.get("tasks", {})]
                iteration_results.append({
                    "slug": slug,
                    "epicId": epic_id,
                    "storyIds": new_story_ids,
                    "taskIds": new_task_ids,
                    "classification": "EXISTS",
                    "devopsId": stored.get("devopsId")
                })
            else:
                iteration_results.append({
                    "slug": slug,
                    "epicId": epic_id,
                    "storyIds": epic_story_ids,
                    "taskIds": epic_task_ids,
                    "classification": "NEW",
                    "devopsId": None
                })
        return iteration_results

    def test_exists_iteration_excludes_synced_items(self):
        """An EXISTS iteration should not include stories/tasks already in sync state."""
        parsed = {
            "epics": [{"id": "1", "title": "Foundation"}],
            "stories": [
                {"id": "1.1", "epicId": "1"},
                {"id": "1.2", "epicId": "1"},
            ],
            "tasks": [
                {"id": "1.1-T1", "storyId": "1.1"},
                {"id": "1.1-T2", "storyId": "1.1"},
            ],
            "epicStatuses": {"1": "done"},
        }
        sync_state = {
            "epics": {"1": {"devopsId": 100, "contentHash": "aaa"}},
            "stories": {
                "1.1": {"devopsId": 200, "contentHash": "bbb"},
                "1.2": {"devopsId": 201, "contentHash": "ccc"},
            },
            "tasks": {
                "1.1-T1": {"devopsId": 300, "contentHash": "ddd"},
                "1.1-T2": {"devopsId": 301, "contentHash": "eee"},
            },
            "iterations": {
                "epic-1-foundation": {"epicId": "1", "devopsId": 429}
            },
        }
        results = self._run_main_logic(parsed, sync_state)
        assert len(results) == 1
        it = results[0]
        assert it["classification"] == "EXISTS"
        assert it["storyIds"] == []
        assert it["taskIds"] == []

    def test_exists_iteration_includes_new_items_only(self):
        """An EXISTS iteration should include only NEW stories/tasks not yet in sync state."""
        parsed = {
            "epics": [{"id": "1", "title": "Foundation"}],
            "stories": [
                {"id": "1.1", "epicId": "1"},
                {"id": "1.2", "epicId": "1"},
                {"id": "1.3", "epicId": "1"},  # NEW - not in sync state
            ],
            "tasks": [
                {"id": "1.1-T1", "storyId": "1.1"},
                {"id": "1.3-T1", "storyId": "1.3"},  # NEW - not in sync state
            ],
            "epicStatuses": {"1": "in-progress"},
        }
        sync_state = {
            "epics": {"1": {"devopsId": 100, "contentHash": "aaa"}},
            "stories": {
                "1.1": {"devopsId": 200, "contentHash": "bbb"},
                "1.2": {"devopsId": 201, "contentHash": "ccc"},
            },
            "tasks": {
                "1.1-T1": {"devopsId": 300, "contentHash": "ddd"},
            },
            "iterations": {
                "epic-1-foundation": {"epicId": "1", "devopsId": 429}
            },
        }
        results = self._run_main_logic(parsed, sync_state)
        assert len(results) == 1
        it = results[0]
        assert it["classification"] == "EXISTS"
        assert it["storyIds"] == ["1.3"]
        assert it["taskIds"] == ["1.3-T1"]

    def test_new_iteration_includes_all_items(self):
        """A NEW iteration should include ALL stories and tasks."""
        parsed = {
            "epics": [{"id": "2", "title": "Workspace"}],
            "stories": [
                {"id": "2.1", "epicId": "2"},
                {"id": "2.2", "epicId": "2"},
            ],
            "tasks": [
                {"id": "2.1-T1", "storyId": "2.1"},
            ],
            "epicStatuses": {"2": "in-progress"},
        }
        sync_state = {
            "epics": {},
            "stories": {},
            "tasks": {},
            "iterations": {},
        }
        results = self._run_main_logic(parsed, sync_state)
        assert len(results) == 1
        it = results[0]
        assert it["classification"] == "NEW"
        assert it["storyIds"] == ["2.1", "2.2"]
        assert it["taskIds"] == ["2.1-T1"]

    def test_backlog_epic_skipped(self):
        """Epics with backlog status should not generate iterations."""
        parsed = {
            "epics": [{"id": "3", "title": "Future"}],
            "stories": [{"id": "3.1", "epicId": "3"}],
            "tasks": [],
            "epicStatuses": {"3": "backlog"},
        }
        sync_state = {"epics": {}, "stories": {}, "tasks": {}, "iterations": {}}
        results = self._run_main_logic(parsed, sync_state)
        assert len(results) == 0
