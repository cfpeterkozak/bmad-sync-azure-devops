#!/usr/bin/env python3
"""Batch Azure DevOps sync via az CLI with error resilience.

Cross-platform, stdlib-only. Auto-detects az executable path.
Creates/updates work items in dependency order (Epics -> Stories -> Tasks -> Iterations).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def find_az_executable() -> str:
    """Find the az CLI executable, handling Windows .cmd extension."""
    az = shutil.which("az")
    if az:
        return az
    # Windows: try az.cmd explicitly
    az_cmd = shutil.which("az.cmd")
    if az_cmd:
        return az_cmd
    # Last resort
    return "az"


def run_az(az_path: str, args: List[str], timeout: int = 120) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Run an az CLI command and return parsed JSON or error."""
    cmd = [az_path] + args + ["--output", "json"]

    try:
        if sys.platform == "win32":
            # On Windows, az.cmd requires shell execution. Python's list2cmdline
            # doesn't quote args that lack spaces, but HTML descriptions like
            # <div>text</div> contain <> which cmd.exe interprets as redirects.
            # Build a command string where every arg is individually double-quoted.
            quoted = []
            for a in cmd:
                # Escape any internal double-quotes for cmd.exe (use "")
                a_escaped = a.replace('"', '""')
                quoted.append(f'"{a_escaped}"')
            cmd_str = " ".join(quoted)
            result = subprocess.run(
                cmd_str,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True
            )
        else:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip() or f"Exit code {result.returncode}"
            return None, error_msg

        if result.stdout.strip():
            try:
                return json.loads(result.stdout), None
            except json.JSONDecodeError:
                return None, f"Invalid JSON response: {result.stdout[:200]}"
        return {}, None

    except subprocess.TimeoutExpired:
        return None, "Command timed out after 120s"
    except FileNotFoundError:
        return None, f"az CLI not found at: {az_path}"
    except Exception as e:
        return None, str(e)


def get_story_type(template: str) -> str:
    """Map process template to story work item type."""
    mapping = {
        "Agile": "User Story",
        "Scrum": "Product Backlog Item",
        "CMMI": "Requirement",
        "Basic": "Issue"
    }
    return mapping.get(template, "User Story")


def get_ac_field(template: str) -> Optional[str]:
    """Map process template to acceptance criteria field name."""
    if template == "Basic":
        return None  # Basic uses description
    return "Microsoft.VSTS.Common.AcceptanceCriteria"


def get_complete_state(template: str) -> str:
    """Map process template to complete state name."""
    mapping = {
        "Agile": "Closed",
        "Scrum": "Done",
        "CMMI": "Resolved",
        "Basic": "Done"
    }
    return mapping.get(template, "Done")


def map_bmad_status_to_devops_state(status: Optional[str], template: str) -> Optional[str]:
    """Map BMAD story status to Azure DevOps work item state.

    | BMAD Status  | Agile  | Scrum     | CMMI     | Basic |
    |--------------|--------|-----------|----------|-------|
    | draft        | New    | New       | Proposed | To Do |
    | in-progress  | Active | Committed | Active   | Doing |
    | review       | Active | Committed | Active   | Doing |
    | done         | Closed | Done      | Resolved | Done  |
    | (not set)    | None   | None      | None     | None  |
    """
    if not status:
        return None

    status = status.strip().lower()

    mapping = {
        "draft": {"Agile": "New", "Scrum": "New", "CMMI": "Proposed", "Basic": "To Do"},
        "in-progress": {"Agile": "Active", "Scrum": "Committed", "CMMI": "Active", "Basic": "Doing"},
        "review": {"Agile": "Active", "Scrum": "Committed", "CMMI": "Active", "Basic": "Doing"},
        "done": {"Agile": "Closed", "Scrum": "Done", "CMMI": "Resolved", "Basic": "Done"},
    }

    status_map = mapping.get(status)
    if not status_map:
        return None
    return status_map.get(template)


def truncate_title(text: str, max_len: int = 255) -> str:
    """Truncate a work item title to fit Azure DevOps 255-char limit."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3].rstrip() + "..."


def wrap_html(text: Optional[str], max_len: int = 0) -> str:
    """Wrap plain text in a div for Azure DevOps HTML fields.

    If max_len > 0, truncate the text before escaping to stay within CLI limits.
    On Windows cmd.exe has an 8191-char command line limit; large descriptions
    or acceptance criteria can exceed this.
    """
    if not text:
        return ""
    if max_len > 0 and len(text) > max_len:
        text = text[:max_len].rstrip() + "\n\n(truncated — full content in BMAD source files)"
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    escaped = escaped.replace("\n", "<br>")
    return f"<div>{escaped}</div>"


def progress(msg: str) -> None:
    """Print progress message to stderr so stdout stays clean for JSON."""
    print(msg, file=sys.stderr, flush=True)


def get_default_iteration(config: Dict[str, str]) -> str:
    """Build the default iteration path for new work items.

    Constructs '{projectName}\\{iterationRootPath}' from config values.
    Returns empty string if iterationRootPath is not set.
    """
    iteration_root = config.get("iterationRootPath", "")
    if not iteration_root:
        return ""
    project = config.get("projectName", "")
    # If iterationRootPath already starts with the project name, use as-is
    if project and iteration_root.startswith(project + "\\"):
        return iteration_root
    if project:
        return f"{project}\\{iteration_root}"
    return iteration_root


def sync_epics(az_path: str, config: Dict[str, str], epics: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Create/update epics. Returns dict mapping epic ID -> devops ID."""
    results = {"created": [], "updated": [], "failed": [], "skipped": []}
    id_map = {}

    area = config.get("areaPath", "")
    iteration = get_default_iteration(config)

    for epic in epics:
        cls = epic.get("classification", "")
        epic_id = epic.get("id", "")

        if cls == "UNCHANGED" or cls == "ORPHANED":
            if epic.get("devopsId"):
                id_map[epic_id] = epic["devopsId"]
            results["skipped"].append({"id": epic_id, "classification": cls})
            continue

        if cls == "NEW":
            args = [
                "boards", "work-item", "create",
                "--type", "Epic",
                "--title", truncate_title(epic.get("title", "")),
                "--description", wrap_html(epic.get("description", ""), max_len=3000),
            ]
            if area:
                args += ["--area", area]
            if iteration:
                args += ["--iteration", iteration]

            progress(f"Creating Epic {epic_id}: {epic.get('title', '')}")
            data, err = run_az(az_path, args)

            if err:
                progress(f"  FAILED: {err}")
                results["failed"].append({"id": epic_id, "error": err})
                continue

            devops_id = data.get("id")
            if devops_id:
                id_map[epic_id] = devops_id
                results["created"].append({
                    "id": epic_id, "devopsId": devops_id,
                    "contentHash": epic.get("contentHash", "")
                })
                progress(f"  Created Epic #{devops_id}")
            else:
                results["failed"].append({"id": epic_id, "error": "No ID in response"})

        elif cls == "CHANGED":
            devops_id = epic.get("devopsId")
            if not devops_id:
                results["failed"].append({"id": epic_id, "error": "No existing DevOps ID for update"})
                continue

            id_map[epic_id] = devops_id
            args = [
                "boards", "work-item", "update",
                "--id", str(devops_id),
                "--title", truncate_title(epic.get("title", "")),
                "--description", wrap_html(epic.get("description", ""), max_len=3000),
            ]

            progress(f"Updating Epic {epic_id} (#{devops_id}): {epic.get('title', '')}")
            data, err = run_az(az_path, args)

            if err:
                progress(f"  FAILED: {err}")
                results["failed"].append({"id": epic_id, "devopsId": devops_id, "error": err})
            else:
                results["updated"].append({
                    "id": epic_id, "devopsId": devops_id,
                    "contentHash": epic.get("contentHash", "")
                })
                progress(f"  Updated Epic #{devops_id}")

    return results, id_map


def sync_stories(az_path: str, config: Dict[str, str], stories: List[Dict[str, Any]], epic_id_map: Dict[str, int], story_statuses: Optional[Dict[str, str]] = None) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Create/update stories with parent links to epics and state sync."""
    results = {"created": [], "updated": [], "failed": [], "skipped": []}
    id_map = {}

    area = config.get("areaPath", "")
    iteration = get_default_iteration(config)
    template = config.get("processTemplate", "Agile")
    story_type = get_story_type(template)
    ac_field = get_ac_field(template)
    story_statuses = story_statuses or {}

    for story in stories:
        cls = story.get("classification", "")
        story_id = story.get("id", "")

        if cls == "UNCHANGED" or cls == "ORPHANED":
            if story.get("devopsId"):
                id_map[story_id] = story["devopsId"]
            results["skipped"].append({"id": story_id, "classification": cls})
            continue

        if cls == "NEW":
            args = [
                "boards", "work-item", "create",
                "--type", story_type,
                "--title", truncate_title(story.get("title", "")),
                "--description", wrap_html(story.get("userStoryText", ""), max_len=3000),
            ]
            if area:
                args += ["--area", area]
            if iteration:
                args += ["--iteration", iteration]

            # Add acceptance criteria
            ac_text = story.get("acceptanceCriteria", "")
            if ac_text and ac_field:
                args += ["--fields", f"{ac_field}={wrap_html(ac_text, max_len=3000)}"]

            progress(f"Creating Story {story_id}: {story.get('title', '')}")
            data, err = run_az(az_path, args)

            if err:
                progress(f"  FAILED: {err}")
                results["failed"].append({"id": story_id, "error": err})
                continue

            devops_id = data.get("id")
            if not devops_id:
                results["failed"].append({"id": story_id, "error": "No ID in response"})
                continue

            id_map[story_id] = devops_id
            progress(f"  Created Story #{devops_id}")

            # Add parent link to epic
            epic_id = story.get("epicId", "")
            epic_devops_id = epic_id_map.get(epic_id)
            if epic_devops_id:
                link_args = [
                    "boards", "work-item", "relation", "add",
                    "--id", str(devops_id),
                    "--relation-type", "parent",
                    "--target-id", str(epic_devops_id),
                ]
                _, link_err = run_az(az_path, link_args)
                if link_err:
                    progress(f"  WARNING: Parent link failed: {link_err}")

            # Update state if story has a non-default BMAD status
            devops_state = map_bmad_status_to_devops_state(
                story_statuses.get(story_id), template
            )
            if devops_state and devops_state != "New":
                state_args = [
                    "boards", "work-item", "update",
                    "--id", str(devops_id),
                    "--state", devops_state,
                ]
                _, state_err = run_az(az_path, state_args)
                if state_err:
                    progress(f"  WARNING: State update to '{devops_state}' failed: {state_err}")
                else:
                    progress(f"  Set state to '{devops_state}'")

            results["created"].append({
                "id": story_id, "devopsId": devops_id,
                "epicDevopsId": epic_devops_id,
                "contentHash": story.get("contentHash", "")
            })

        elif cls == "CHANGED":
            devops_id = story.get("devopsId")
            if not devops_id:
                results["failed"].append({"id": story_id, "error": "No existing DevOps ID for update"})
                continue

            id_map[story_id] = devops_id
            args = [
                "boards", "work-item", "update",
                "--id", str(devops_id),
                "--title", truncate_title(story.get("title", "")),
                "--description", wrap_html(story.get("userStoryText", ""), max_len=3000),
            ]

            ac_text = story.get("acceptanceCriteria", "")
            if ac_text and ac_field:
                args += ["--fields", f"{ac_field}={wrap_html(ac_text, max_len=3000)}"]

            # Include state in update if story has a BMAD status
            devops_state = map_bmad_status_to_devops_state(
                story_statuses.get(story_id), template
            )
            if devops_state:
                args += ["--state", devops_state]

            progress(f"Updating Story {story_id} (#{devops_id})")
            data, err = run_az(az_path, args)

            if err:
                progress(f"  FAILED: {err}")
                results["failed"].append({"id": story_id, "devopsId": devops_id, "error": err})
            else:
                results["updated"].append({
                    "id": story_id, "devopsId": devops_id,
                    "contentHash": story.get("contentHash", "")
                })
                progress(f"  Updated Story #{devops_id}")

    return results, id_map


def sync_tasks(az_path: str, config: Dict[str, str], tasks: List[Dict[str, Any]], story_id_map: Dict[str, int]) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Create/update tasks with parent links to stories. Returns (results, id_map)."""
    results = {"created": [], "updated": [], "failed": [], "skipped": []}
    id_map = {}

    area = config.get("areaPath", "")
    iteration = get_default_iteration(config)
    template = config.get("processTemplate", "Agile")
    complete_state = get_complete_state(template)

    for task in tasks:
        cls = task.get("classification", "")
        task_id = task.get("id", "")

        if cls == "UNCHANGED" or cls == "ORPHANED":
            if task.get("devopsId"):
                id_map[task_id] = task["devopsId"]
            results["skipped"].append({"id": task_id, "classification": cls})
            continue

        if cls == "NEW":
            args = [
                "boards", "work-item", "create",
                "--type", "Task",
                "--title", truncate_title(task.get("description", "")),
            ]
            if area:
                args += ["--area", area]
            if iteration:
                args += ["--iteration", iteration]

            progress(f"Creating Task {task_id}: {task.get('description', '')[:60]}")
            data, err = run_az(az_path, args)

            if err:
                progress(f"  FAILED: {err}")
                results["failed"].append({"id": task_id, "error": err})
                continue

            devops_id = data.get("id")
            if not devops_id:
                results["failed"].append({"id": task_id, "error": "No ID in response"})
                continue

            id_map[task_id] = devops_id
            progress(f"  Created Task #{devops_id}")

            # Add parent link to story
            story_id = task.get("storyId", "")
            story_devops_id = story_id_map.get(story_id)
            if story_devops_id:
                link_args = [
                    "boards", "work-item", "relation", "add",
                    "--id", str(devops_id),
                    "--relation-type", "parent",
                    "--target-id", str(story_devops_id),
                ]
                _, link_err = run_az(az_path, link_args)
                if link_err:
                    progress(f"  WARNING: Parent link failed: {link_err}")

            # If task is complete, update state
            if task.get("complete", False):
                state_args = [
                    "boards", "work-item", "update",
                    "--id", str(devops_id),
                    "--state", complete_state,
                ]
                _, state_err = run_az(az_path, state_args)
                if state_err:
                    progress(f"  WARNING: State update failed: {state_err}")

            results["created"].append({
                "id": task_id, "devopsId": devops_id,
                "storyDevopsId": story_devops_id,
                "contentHash": task.get("contentHash", "")
            })

        elif cls == "CHANGED":
            devops_id = task.get("devopsId")
            if not devops_id:
                results["failed"].append({"id": task_id, "error": "No existing DevOps ID for update"})
                continue

            id_map[task_id] = devops_id
            state = complete_state if task.get("complete", False) else "New"
            args = [
                "boards", "work-item", "update",
                "--id", str(devops_id),
                "--state", state,
            ]

            progress(f"Updating Task {task_id} (#{devops_id})")
            data, err = run_az(az_path, args)

            if err:
                progress(f"  FAILED: {err}")
                results["failed"].append({"id": task_id, "devopsId": devops_id, "error": err})
            else:
                results["updated"].append({
                    "id": task_id, "devopsId": devops_id,
                    "contentHash": task.get("contentHash", "")
                })
                progress(f"  Updated Task #{devops_id}")

    return results, id_map


def sync_epic_iterations(az_path: str, config: Dict[str, str], iterations: List[Dict[str, Any]], epic_id_map: Dict[str, int], story_id_map: Dict[str, int], task_id_map: Dict[str, int]) -> Dict[str, Any]:
    """Create epic-based iterations and move epics, stories, and tasks into them."""
    results = {"created": [], "failed": [], "skipped": [], "movements": []}

    # Build the full iteration root path (e.g., "ProjectName\Iterations\Root")
    # get_default_iteration prepends projectName if needed
    iteration_root = get_default_iteration(config)

    def move_item(item_type, item_id, devops_id, iter_path, slug):
        """Move a work item to an iteration path."""
        assign_args = [
            "boards", "work-item", "update",
            "--id", str(devops_id),
            "--iteration", iter_path,
        ]
        _, assign_err = run_az(az_path, assign_args)
        if assign_err:
            progress(f"  WARNING: {item_type} {item_id} move failed: {assign_err}")
            results["movements"].append({
                "type": item_type, "id": item_id, "iteration": slug,
                "status": "failed", "error": assign_err
            })
        else:
            results["movements"].append({
                "type": item_type, "id": item_id, "iteration": slug,
                "status": "moved"
            })
            progress(f"  Moved {item_type} #{devops_id} to {slug}")

    for it in iterations:
        cls = it.get("classification", "")
        slug = it.get("slug", "")
        epic_id = it.get("epicId", "")

        iter_path = f"{iteration_root}\\{slug}" if iteration_root else slug

        if cls == "NEW":
            args = [
                "boards", "iteration", "project", "create",
                "--name", slug,
            ]
            if iteration_root:
                # az boards iteration project create --path requires absolute
                # path with leading backslash, e.g. \ProjectName\Iterations
                abs_path = iteration_root if iteration_root.startswith("\\") else f"\\{iteration_root}"
                args += ["--path", abs_path]

            progress(f"Creating Iteration: {slug}")
            data, err = run_az(az_path, args)

            if err:
                progress(f"  FAILED: {err}")
                results["failed"].append({"slug": slug, "epicId": epic_id, "error": err})
                continue

            devops_id = data.get("id", data.get("identifier", ""))
            results["created"].append({"slug": slug, "epicId": epic_id, "devopsId": devops_id})
            progress(f"  Created Iteration: {slug}")

        elif cls == "EXISTS":
            results["skipped"].append({"slug": slug, "epicId": epic_id, "classification": cls})

        # Move epic into iteration
        epic_devops_id = epic_id_map.get(epic_id)
        if epic_devops_id:
            move_item("epic", epic_id, epic_devops_id, iter_path, slug)

        # Move stories into iteration
        for story_id in it.get("storyIds", []):
            story_devops_id = story_id_map.get(story_id)
            if story_devops_id:
                move_item("story", story_id, story_devops_id, iter_path, slug)
            else:
                progress(f"  WARNING: Story {story_id} not found in ID map, skipping")

        # Move tasks into iteration
        for task_id in it.get("taskIds", []):
            task_devops_id = task_id_map.get(task_id)
            if task_devops_id:
                move_item("task", task_id, task_devops_id, iter_path, slug)
            else:
                progress(f"  WARNING: Task {task_id} not found in ID map, skipping")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Batch sync work items to Azure DevOps via az CLI"
    )
    parser.add_argument("--diff", required=True, help="Path to diff results JSON (from compute-hashes.py)")
    parser.add_argument("--config", required=True, help="Path to devops-sync-config.yaml")
    parser.add_argument("--output", required=True, help="Path to write sync results JSON")
    args = parser.parse_args()

    # Find az CLI
    az_path = find_az_executable()
    progress(f"Using az CLI: {az_path}")

    # Load diff results
    with open(args.diff, "r", encoding="utf-8") as f:
        diff = json.load(f)

    # Load config (simple YAML parser)
    config = {}
    with open(args.config, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            m = __import__("re").match(r'^(\w+):\s*"?([^"]*)"?\s*$', line)
            if m:
                config[m.group(1)] = m.group(2).strip()

    progress(f"Config loaded: template={config.get('processTemplate', '?')}, project={config.get('projectName', '?')}")

    # Sync in dependency order
    progress("\n=== Syncing Epics ===")
    epic_results, epic_id_map = sync_epics(az_path, config, diff.get("epics", []))

    progress("\n=== Syncing Stories ===")
    story_statuses = diff.get("storyStatuses", {})
    story_results, story_id_map = sync_stories(
        az_path, config, diff.get("stories", []), epic_id_map,
        story_statuses=story_statuses
    )

    progress("\n=== Syncing Tasks ===")
    task_results, task_id_map = sync_tasks(az_path, config, diff.get("tasks", []), story_id_map)

    progress("\n=== Syncing Epic Iterations ===")
    iteration_results = sync_epic_iterations(
        az_path, config, diff.get("iterations", []),
        epic_id_map, story_id_map, task_id_map
    )

    # Build output
    result = {
        "epics": epic_results,
        "stories": story_results,
        "tasks": task_results,
        "iterations": iteration_results,
        "epicIdMap": {k: v for k, v in epic_id_map.items()},
        "storyIdMap": {k: v for k, v in story_id_map.items()},
        "taskIdMap": {k: v for k, v in task_id_map.items()},
        "summary": {
            "epicsCreated": len(epic_results["created"]),
            "epicsUpdated": len(epic_results["updated"]),
            "epicsFailed": len(epic_results["failed"]),
            "storiesCreated": len(story_results["created"]),
            "storiesUpdated": len(story_results["updated"]),
            "storiesFailed": len(story_results["failed"]),
            "tasksCreated": len(task_results["created"]),
            "tasksUpdated": len(task_results["updated"]),
            "tasksFailed": len(task_results["failed"]),
            "iterationsCreated": len(iteration_results["created"]),
            "iterationsFailed": len(iteration_results["failed"]),
            "iterationMovements": len([m for m in iteration_results["movements"] if m["status"] == "moved"])
        }
    }

    # Write output
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Print to stdout
    print(json.dumps(result, indent=2))

    # Print summary to stderr
    s = result["summary"]
    progress(f"\n=== SYNC COMPLETE ===")
    progress(f"Epics:      {s['epicsCreated']} created, {s['epicsUpdated']} updated, {s['epicsFailed']} failed")
    progress(f"Stories:    {s['storiesCreated']} created, {s['storiesUpdated']} updated, {s['storiesFailed']} failed")
    progress(f"Tasks:      {s['tasksCreated']} created, {s['tasksUpdated']} updated, {s['tasksFailed']} failed")
    progress(f"Iterations: {s['iterationsCreated']} created, {s['iterationsFailed']} failed, {s['iterationMovements']} items moved")


if __name__ == "__main__":
    main()
