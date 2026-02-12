#!/usr/bin/env python3
"""Batch SHA-256 hashing and diff classification for BMAD sync.

Cross-platform, stdlib-only. Computes content hashes using hashlib,
compares against stored sync state, classifies items as NEW/CHANGED/UNCHANGED/ORPHANED.
"""

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any, Callable, Dict, List, Optional


def normalize(text: Optional[str]) -> str:
    """Normalize text: trim, collapse whitespace, lowercase."""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    text = text.lower()
    return text


def normalize_list(items: Optional[List]) -> str:
    """Sort list items and join with comma."""
    if not items:
        return ""
    return ",".join(sorted(str(i).strip().lower() for i in items if str(i).strip()))


def compute_hash(content_string: str) -> str:
    """SHA-256 hash, first 12 hex chars."""
    h = hashlib.sha256(content_string.encode("utf-8")).hexdigest()
    return h[:12]


def hash_epic(epic: Dict[str, Any], epic_statuses: Optional[Dict[str, str]] = None) -> str:
    """Compute content hash for an epic.

    Includes normalized epic status in hash so status changes trigger CHANGED classification.
    """
    status = ""
    if epic_statuses:
        status = epic_statuses.get(epic.get("id", ""), "")
    parts = [
        normalize(epic.get("title", "")),
        normalize(epic.get("description", "")),
        normalize(epic.get("phase", "")),
        normalize_list(epic.get("requirements", [])),
        normalize(status)
    ]
    return compute_hash("|".join(parts))


def hash_story(story: Dict[str, Any], story_statuses: Optional[Dict[str, str]] = None) -> str:
    """Compute content hash for a story.

    Includes normalized status in hash so status changes trigger CHANGED classification.
    """
    status = ""
    if story_statuses:
        status = story_statuses.get(story.get("id", ""), "")
    parts = [
        normalize(story.get("title", "")),
        normalize(story.get("userStoryText", "")),
        normalize(story.get("acceptanceCriteria", "")),
        normalize(status)
    ]
    return compute_hash("|".join(parts))


def hash_task(task: Dict[str, Any]) -> str:
    """Compute content hash for a task."""
    state = "complete" if task.get("complete", False) else "incomplete"
    parts = [
        normalize(task.get("description", "")),
        state
    ]
    return compute_hash("|".join(parts))


def generate_iteration_slug(epic_id: str, title: str) -> str:
    """Generate a kebab-case iteration slug from epic ID and title."""
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    full = f"epic-{epic_id}-{slug}"
    return full[:128].rstrip('-') if len(full) > 128 else full


def load_sync_state(path: Optional[str]) -> Dict[str, Dict]:
    """Load existing sync YAML state. Returns dict with epics/stories/tasks/iterations."""
    empty = {"epics": {}, "stories": {}, "tasks": {}, "iterations": {}}

    if not path or not os.path.isfile(path):
        return empty

    # Simple YAML parser for the sync state file
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    result = {"epics": {}, "stories": {}, "tasks": {}, "iterations": {}}
    current_section = None
    current_id = None
    current_item = {}

    for line in content.splitlines():
        # Top-level sections
        section_match = re.match(r'^(epics|stories|tasks|iterations):\s*$', line)
        if section_match:
            # Save pending item before switching sections
            if current_section and current_id and current_item:
                result[current_section][current_id] = current_item
            current_section = section_match.group(1)
            current_id = None
            current_item = {}
            continue
        if re.match(r'^\w', line) and not line.startswith(" "):
            # Other top-level key (like lastFullSync) — save pending item
            if current_section and current_id and current_item:
                result[current_section][current_id] = current_item
            current_section = None
            current_id = None
            current_item = {}
            continue

        if not current_section:
            continue

        # Item ID line: "  "1":"  or  "  1.1-T1:" (exactly 2-space indent, not 4+)
        id_match = re.match(r'^  (?! )"?([^":]+)"?:\s*$', line)
        if id_match:
            # Save previous item
            if current_id and current_item:
                result[current_section][current_id] = current_item
            current_id = id_match.group(1).strip()
            current_item = {}
            continue

        # Properties: "    key: value"
        if current_id:
            prop_match = re.match(r'^    (\w+):\s*"?([^"]*)"?\s*$', line)
            if prop_match:
                key = prop_match.group(1)
                val = prop_match.group(2).strip()
                # Try to parse as int for devopsId
                if key in ("devopsId", "epicDevopsId", "storyDevopsId"):
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                current_item[key] = val

    # Save last item
    if current_section and current_id and current_item:
        result[current_section][current_id] = current_item

    return result


def classify_items(parsed_items: List[Dict], stored_items: Dict, hash_fn: Callable, id_field: str = "id") -> List[Dict]:
    """Classify items as NEW/CHANGED/UNCHANGED/ORPHANED."""
    results = []

    parsed_ids = set()
    for item in parsed_items:
        item_id = item[id_field]
        parsed_ids.add(item_id)
        new_hash = hash_fn(item)

        stored = stored_items.get(item_id, {})
        old_hash = stored.get("contentHash", "")
        devops_id = stored.get("devopsId", None)

        if not old_hash:
            classification = "NEW"
        elif old_hash == new_hash:
            classification = "UNCHANGED"
        else:
            classification = "CHANGED"

        results.append({
            **item,
            "contentHash": new_hash,
            "classification": classification,
            "devopsId": devops_id
        })

    # Find orphaned items (in stored but not in parsed)
    for item_id, stored in stored_items.items():
        if item_id not in parsed_ids:
            results.append({
                "id": item_id,
                "classification": "ORPHANED",
                "devopsId": stored.get("devopsId"),
                "contentHash": stored.get("contentHash", "")
            })

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Compute content hashes and classify items for sync diff"
    )
    parser.add_argument("--parsed", required=True, help="Path to parsed artifacts JSON (from parse-artifacts.py)")
    parser.add_argument("--sync-state", default="", help="Path to existing devops-sync.yaml")
    parser.add_argument("--output", required=True, help="Path to write diff results JSON")
    args = parser.parse_args()

    # Load parsed data
    with open(args.parsed, "r", encoding="utf-8") as f:
        parsed = json.load(f)

    # Load existing sync state
    sync_state = load_sync_state(args.sync_state)

    # Extract statuses from parsed data
    story_statuses = parsed.get("storyStatuses", {})
    epic_statuses = parsed.get("epicStatuses", {})

    # Classify each type
    epic_results = classify_items(
        parsed.get("epics", []),
        sync_state.get("epics", {}),
        lambda e: hash_epic(e, epic_statuses)
    )

    story_results = classify_items(
        parsed.get("stories", []),
        sync_state.get("stories", {}),
        lambda s: hash_story(s, story_statuses)
    )

    task_results = classify_items(
        parsed.get("tasks", []),
        sync_state.get("tasks", {}),
        hash_task
    )

    # Derive epic-based iterations for epics with status in-progress or done
    iteration_results = []
    stored_iterations = sync_state.get("iterations", {})

    # Build lookup: story epicId -> list of story IDs
    story_ids_by_epic = {}
    for story in parsed.get("stories", []):
        eid = story.get("epicId", "")
        if eid:
            story_ids_by_epic.setdefault(eid, []).append(story["id"])

    # Build lookup: task storyId -> list of task IDs
    task_ids_by_story = {}
    for task in parsed.get("tasks", []):
        sid = task.get("storyId", "")
        if sid:
            task_ids_by_story.setdefault(sid, []).append(task["id"])

    for epic in parsed.get("epics", []):
        epic_id = epic.get("id", "")
        status = epic_statuses.get(epic_id, "")
        if status not in ("in-progress", "done"):
            continue

        # Check if sync state already has an iteration for this epic (by epicId field)
        existing_slug = None
        for slug, iter_data in stored_iterations.items():
            if iter_data.get("epicId") == epic_id:
                existing_slug = slug
                break

        slug = existing_slug or generate_iteration_slug(epic_id, epic.get("title", ""))

        # Collect story and task IDs belonging to this epic
        epic_story_ids = story_ids_by_epic.get(epic_id, [])
        epic_task_ids = []
        for sid in epic_story_ids:
            epic_task_ids.extend(task_ids_by_story.get(sid, []))

        stored = stored_iterations.get(slug, {})
        has_devops_id = stored.get("devopsId") not in (None, "", "None")
        if slug in stored_iterations and has_devops_id:
            iteration_results.append({
                "slug": slug,
                "epicId": epic_id,
                "storyIds": epic_story_ids,
                "taskIds": epic_task_ids,
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

    # Compute summary counts
    def count_by_class(items):
        counts = {"NEW": 0, "CHANGED": 0, "UNCHANGED": 0, "ORPHANED": 0, "EXISTS": 0}
        for item in items:
            cls = item["classification"]
            counts[cls] = counts.get(cls, 0) + 1
        return counts

    epic_counts = count_by_class(epic_results)
    story_counts = count_by_class(story_results)
    task_counts = count_by_class(task_results)
    iter_counts = count_by_class(iteration_results)

    # Estimate CLI calls
    # Count NEW stories that have a non-default status needing a state update
    new_story_state_updates = 0
    for s in story_results:
        if s["classification"] == "NEW" and story_statuses.get(s.get("id", "")):
            status = story_statuses[s["id"]]
            if status not in ("draft", ""):
                new_story_state_updates += 1

    # Count story attachment calls (upload + relation add = 2 per story with file)
    story_file_paths = parsed.get("storyFilePaths", {})
    attachment_calls = 0
    for s in story_results:
        if s["classification"] in ("NEW", "CHANGED") and story_file_paths.get(s.get("id", "")):
            attachment_calls += 2  # REST upload + az relation add

    cli_calls = (
        epic_counts["NEW"] + epic_counts["CHANGED"]  # epic create/update
        + story_counts["NEW"] * 2  # story create + parent link
        + new_story_state_updates  # state update for NEW stories with non-default status
        + story_counts["CHANGED"]  # story update (includes state in same call)
        + task_counts["NEW"] * 2  # task create + parent link
        + task_counts["CHANGED"]  # task update
        + attachment_calls  # story file attachments (REST + CLI)
    )
    # Add iteration calls: creation + item movement (epic + stories + tasks)
    for it in iteration_results:
        if it["classification"] == "NEW":
            cli_calls += 1  # iteration create
            cli_calls += 1  # move epic
            cli_calls += len(it.get("storyIds", []))  # move stories
            cli_calls += len(it.get("taskIds", []))  # move tasks
        elif it["classification"] == "EXISTS":
            # Still move items (handles items added since last sync)
            cli_calls += 1  # move epic
            cli_calls += len(it.get("storyIds", []))  # move stories
            cli_calls += len(it.get("taskIds", []))  # move tasks

    result = {
        "epics": epic_results,
        "stories": story_results,
        "tasks": task_results,
        "iterations": iteration_results,
        "epicStatuses": epic_statuses,
        "storyStatuses": story_statuses,
        "storyFilePaths": story_file_paths,
        "summary": {
            "epics": epic_counts,
            "stories": story_counts,
            "tasks": task_counts,
            "iterations": iter_counts,
            "estimatedCliCalls": cli_calls
        }
    }

    # Write output
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
