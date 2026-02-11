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


def normalize(text):
    """Normalize text: trim, collapse whitespace, lowercase."""
    if not text:
        return ""
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    text = text.lower()
    return text


def normalize_list(items):
    """Sort list items and join with comma."""
    if not items:
        return ""
    return ",".join(sorted(str(i).strip().lower() for i in items if str(i).strip()))


def compute_hash(content_string):
    """SHA-256 hash, first 12 hex chars."""
    h = hashlib.sha256(content_string.encode("utf-8")).hexdigest()
    return h[:12]


def hash_epic(epic):
    """Compute content hash for an epic."""
    parts = [
        normalize(epic.get("title", "")),
        normalize(epic.get("description", "")),
        normalize(epic.get("phase", "")),
        normalize_list(epic.get("requirements", []))
    ]
    return compute_hash("|".join(parts))


def hash_story(story, story_statuses=None):
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


def hash_task(task):
    """Compute content hash for a task."""
    state = "complete" if task.get("complete", False) else "incomplete"
    parts = [
        normalize(task.get("description", "")),
        state
    ]
    return compute_hash("|".join(parts))


def load_sync_state(path):
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
        if re.match(r'^epics:\s*$', line):
            current_section = "epics"
            current_id = None
            continue
        if re.match(r'^stories:\s*$', line):
            current_section = "stories"
            current_id = None
            continue
        if re.match(r'^tasks:\s*$', line):
            current_section = "tasks"
            current_id = None
            continue
        if re.match(r'^iterations:\s*$', line):
            current_section = "iterations"
            current_id = None
            continue
        if re.match(r'^\w', line) and not line.startswith(" "):
            # Other top-level key (like lastFullSync)
            current_section = None
            current_id = None
            continue

        if not current_section:
            continue

        # Item ID line: "  "1":"  or  "  1.1-T1:"
        id_match = re.match(r'^  "?([^":]+)"?:\s*$', line)
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


def classify_items(parsed_items, stored_items, hash_fn, id_field="id"):
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

    # Extract story statuses from parsed data
    story_statuses = parsed.get("storyStatuses", {})

    # Classify each type
    epic_results = classify_items(
        parsed.get("epics", []),
        sync_state.get("epics", {}),
        hash_epic
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

    # Classify iterations
    iteration_results = []
    stored_iterations = sync_state.get("iterations", {})
    for it in parsed.get("iterations", []):
        name = it["name"]
        if name in stored_iterations:
            iteration_results.append({
                **it,
                "classification": "EXISTS",
                "devopsId": stored_iterations[name].get("devopsId")
            })
        else:
            iteration_results.append({
                **it,
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

    cli_calls = (
        epic_counts["NEW"] + epic_counts["CHANGED"]  # epic create/update
        + story_counts["NEW"] * 2  # story create + parent link
        + new_story_state_updates  # state update for NEW stories with non-default status
        + story_counts["CHANGED"]  # story update (includes state in same call)
        + task_counts["NEW"] * 2  # task create + parent link
        + task_counts["CHANGED"]  # task update
        + iter_counts["NEW"]  # iteration create
    )
    # Add iteration assignments for new iterations
    for it in iteration_results:
        if it["classification"] == "NEW":
            cli_calls += len(it.get("stories", []))

    result = {
        "epics": epic_results,
        "stories": story_results,
        "tasks": task_results,
        "iterations": iteration_results,
        "storyStatuses": story_statuses,
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
