#!/usr/bin/env python3
"""Write devops-sync.yaml by merging diff results and sync results.

Cross-platform, stdlib-only. Deterministically produces the sync state file
from the JSON outputs of compute-hashes.py and sync-devops.py.

Design constraints:
- No PyYAML dependency — writes YAML manually with simple formatting
- Preserves unchanged items from diff results (they already have devopsId/contentHash)
- Updates changed/new items with data from sync results
- Correctly extracts iteration slugs from sync results structure
- Marks failed items as 'pending' for retry on next sync
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def progress(msg: str) -> None:
    """Print progress to stderr."""
    print(msg, file=sys.stderr)


def yaml_val(val: Any) -> str:
    """Format a value for YAML output."""
    if val is None:
        return '""'
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    return f'"{val}"'


def sort_key_numeric(item_id: str) -> tuple:
    """Sort key that handles N.M, N.M-TN, N.M-RN.M patterns numerically."""
    # Split into tokens of text and numbers: "1.1-T10" -> ["1", ".", "1", "-", "T", "10"]
    tokens = re.findall(r'\d+|[^\d]+', item_id)
    result = []
    for t in tokens:
        if t.isdigit():
            result.append((0, int(t)))
        else:
            result.append((1, ord(t[0]) if t else 0))
    return tuple(result)


def build_epic_id_map(sync_results: Dict) -> Dict[str, int]:
    """Build epic ID -> devops ID map from sync results."""
    result = {}
    for eid, did in sync_results.get("epicIdMap", {}).items():
        if did not in (None, "None", ""):
            try:
                result[eid] = int(did)
            except (ValueError, TypeError):
                pass
    return result


def build_story_id_map(sync_results: Dict) -> Dict[str, int]:
    """Build story ID -> devops ID map from sync results."""
    result = {}
    for sid, did in sync_results.get("storyIdMap", {}).items():
        if did not in (None, "None", ""):
            try:
                result[sid] = int(did)
            except (ValueError, TypeError):
                pass
    return result


def build_task_id_map(sync_results: Dict) -> Dict[str, int]:
    """Build task ID -> devops ID map from sync results."""
    result = {}
    for tid, did in sync_results.get("taskIdMap", {}).items():
        if did not in (None, "None", ""):
            try:
                result[tid] = int(did)
            except (ValueError, TypeError):
                pass
    return result


def build_iteration_map(sync_results: Dict) -> Dict[str, Dict]:
    """Extract iteration slug -> {epicId, devopsId} from sync results.

    The sync results iterations structure is:
    {"created": [...], "failed": [...], "skipped": [...], "movements": [...]}

    created[] entries have: slug, epicId, devopsId
    skipped[] entries have: slug, epicId, classification
    """
    result = {}
    iters = sync_results.get("iterations", {})

    for entry in iters.get("created", []):
        slug = entry.get("slug", "")
        if slug:
            result[slug] = {
                "epicId": entry.get("epicId", ""),
                "devopsId": entry.get("devopsId"),
            }

    for entry in iters.get("skipped", []):
        slug = entry.get("slug", "")
        if slug and slug not in result:
            result[slug] = {
                "epicId": entry.get("epicId", ""),
                "devopsId": entry.get("devopsId"),
            }

    return result


def write_sync_state(
    diff_results: Dict,
    sync_results: Dict,
    config: Dict,
    timestamp: str,
    output_path: str,
) -> Dict[str, int]:
    """Write the devops-sync.yaml file. Returns counts dict."""
    epic_id_map = build_epic_id_map(sync_results)
    story_id_map = build_story_id_map(sync_results)
    task_id_map = build_task_id_map(sync_results)
    iteration_map = build_iteration_map(sync_results)

    iter_root = config.get("iterationRootPath", "")
    project = config.get("projectName", "")

    counts = {"epics": 0, "stories": 0, "tasks": 0, "iterations": 0,
              "pending_stories": 0, "pending_tasks": 0}
    lines = []
    lines.append(f"# Azure DevOps Sync State")
    lines.append(f"# Last full sync: {timestamp}")
    lines.append(f'lastFullSync: "{timestamp}"')
    lines.append("")

    # --- Epics ---
    lines.append("epics:")
    epics = sorted(diff_results.get("epics", []),
                   key=lambda e: sort_key_numeric(e.get("id", "")))
    for epic in epics:
        eid = epic.get("id", "")
        if epic.get("classification") == "ORPHANED":
            continue
        devops_id = epic_id_map.get(eid, epic.get("devopsId"))
        if devops_id in (None, "None", ""):
            continue
        try:
            devops_id = int(devops_id)
        except (ValueError, TypeError):
            continue
        lines.append(f'  "{eid}":')
        lines.append(f"    devopsId: {devops_id}")
        lines.append(f'    contentHash: "{epic.get("contentHash", "")}"')
        lines.append(f'    lastSynced: "{timestamp}"')
        lines.append(f'    status: "synced"')
        counts["epics"] += 1

    lines.append("")

    # --- Stories ---
    lines.append("stories:")
    stories = sorted(diff_results.get("stories", []),
                     key=lambda s: sort_key_numeric(s.get("id", "")))
    for story in stories:
        sid = story.get("id", "")
        if story.get("classification") == "ORPHANED":
            continue
        devops_id = story_id_map.get(sid, story.get("devopsId"))
        epic_id = story.get("epicId", "")
        epic_devops_id = epic_id_map.get(epic_id, "")

        is_pending = devops_id in (None, "None", "")
        lines.append(f'  "{sid}":')
        if is_pending:
            lines.append(f'    contentHash: "{story.get("contentHash", "")}"')
            lines.append(f'    lastSynced: "{timestamp}"')
            lines.append(f'    status: "pending"')
            counts["pending_stories"] += 1
        else:
            try:
                devops_id = int(devops_id)
            except (ValueError, TypeError):
                pass
            lines.append(f"    devopsId: {devops_id}")
            if epic_devops_id:
                lines.append(f"    epicDevopsId: {epic_devops_id}")
            lines.append(f'    contentHash: "{story.get("contentHash", "")}"')
            lines.append(f'    lastSynced: "{timestamp}"')
            lines.append(f'    status: "synced"')
        counts["stories"] += 1

    lines.append("")

    # --- Tasks ---
    lines.append("tasks:")
    tasks = sorted(diff_results.get("tasks", []),
                   key=lambda t: sort_key_numeric(t.get("id", "")))
    for task in tasks:
        tid = task.get("id", "")
        if task.get("classification") == "ORPHANED":
            continue
        devops_id = task_id_map.get(tid, task.get("devopsId"))
        story_id = task.get("storyId", "")
        story_devops_id = story_id_map.get(story_id, "")

        is_pending = devops_id in (None, "None", "")
        lines.append(f'  "{tid}":')
        if is_pending:
            lines.append(f'    contentHash: "{task.get("contentHash", "")}"')
            lines.append(f'    lastSynced: "{timestamp}"')
            lines.append(f'    status: "pending"')
            counts["pending_tasks"] += 1
        else:
            try:
                devops_id = int(devops_id)
            except (ValueError, TypeError):
                pass
            lines.append(f"    devopsId: {devops_id}")
            if story_devops_id:
                lines.append(f"    storyDevopsId: {story_devops_id}")
            lines.append(f'    contentHash: "{task.get("contentHash", "")}"')
            lines.append(f'    lastSynced: "{timestamp}"')
            lines.append(f'    status: "synced"')
        counts["tasks"] += 1

    lines.append("")

    # --- Iterations ---
    lines.append("iterations:")

    # Merge: iterations from diff results (have slug/epicId/devopsId)
    # plus any from sync results that were newly created
    seen_slugs = set()
    diff_iterations = diff_results.get("iterations", [])

    for it in diff_iterations:
        slug = it.get("slug", "")
        epic_id = it.get("epicId", "")
        if not slug:
            continue
        seen_slugs.add(slug)

        # Get devopsId: prefer sync results (newly created), fall back to diff results
        devops_id = None
        if slug in iteration_map and iteration_map[slug].get("devopsId"):
            devops_id = iteration_map[slug]["devopsId"]
        elif it.get("devopsId") not in (None, "None", ""):
            devops_id = it["devopsId"]

        if devops_id is None:
            continue

        devops_path = f"\\{project}\\Iteration\\{iter_root}\\{slug}" if iter_root else f"\\{project}\\Iteration\\{slug}"

        lines.append(f'  "{slug}":')
        lines.append(f'    epicId: "{epic_id}"')
        lines.append(f"    devopsId: {devops_id}")
        lines.append(f'    devopsPath: "{devops_path}"')
        lines.append(f'    lastSynced: "{timestamp}"')
        counts["iterations"] += 1

    # Add any iterations from sync results not already in diff results
    for slug, data in iteration_map.items():
        if slug not in seen_slugs and data.get("devopsId"):
            epic_id = data.get("epicId", "")
            devops_id = data["devopsId"]
            devops_path = f"\\{project}\\Iteration\\{iter_root}\\{slug}" if iter_root else f"\\{project}\\Iteration\\{slug}"

            lines.append(f'  "{slug}":')
            lines.append(f'    epicId: "{epic_id}"')
            lines.append(f"    devopsId: {devops_id}")
            lines.append(f'    devopsPath: "{devops_path}"')
            lines.append(f'    lastSynced: "{timestamp}"')
            counts["iterations"] += 1

    lines.append("")

    # Write file
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))

    return counts


def load_config(path: str) -> Dict:
    """Load devops-sync-config.yaml with simple parser."""
    config = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r'^(\w+):\s*"?([^"]*)"?\s*$', line)
            if m:
                config[m.group(1)] = m.group(2).strip()
    return config


def main():
    parser = argparse.ArgumentParser(
        description="Write devops-sync.yaml from diff results and sync results"
    )
    parser.add_argument("--diff", required=True, help="Path to diff results JSON (from compute-hashes.py)")
    parser.add_argument("--sync-results", required=True, help="Path to sync results JSON (from sync-devops.py)")
    parser.add_argument("--config", required=True, help="Path to devops-sync-config.yaml")
    parser.add_argument("--output", required=True, help="Path to write devops-sync.yaml")
    args = parser.parse_args()

    with open(args.diff, "r", encoding="utf-8") as f:
        diff_results = json.load(f)
    with open(args.sync_results, "r", encoding="utf-8") as f:
        sync_results = json.load(f)
    config = load_config(args.config)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    counts = write_sync_state(diff_results, sync_results, config, timestamp, args.output)

    progress(f"Sync state written to {args.output}")
    progress(f"  Epics: {counts['epics']}, Stories: {counts['stories']} ({counts['pending_stories']} pending)")
    progress(f"  Tasks: {counts['tasks']} ({counts['pending_tasks']} pending), Iterations: {counts['iterations']}")

    # Print counts as JSON to stdout
    print(json.dumps(counts))


if __name__ == "__main__":
    main()
