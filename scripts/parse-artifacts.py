#!/usr/bin/env python3
"""Parse BMAD artifacts (epics.md, story files, sprint YAML) into structured JSON.

Cross-platform, stdlib-only. Auto-detects heading levels.
"""

import argparse
import json
import os
import re
import sys


def detect_heading_levels(content):
    """Scan for 'Epic N:' pattern at any heading level and derive story level."""
    for line in content.splitlines():
        m = re.match(r'^(#{1,6})\s+Epic\s+\d+:', line)
        if m:
            epic_level = len(m.group(1))
            return epic_level, epic_level + 1
    # Defaults: ## Epic, ### Story
    return 2, 3


def parse_epics_file(path):
    """Parse epics.md, auto-detecting heading levels."""
    if not os.path.isfile(path):
        print(json.dumps({"error": f"File not found: {path}"}), file=sys.stderr)
        return [], []

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    epic_level, story_level = detect_heading_levels(content)

    epic_prefix = "#" * epic_level
    story_prefix = "#" * story_level

    epic_pattern = re.compile(
        rf'^{re.escape(epic_prefix)}\s+Epic\s+(\d+):\s*(.+)$', re.MULTILINE
    )
    story_pattern = re.compile(
        rf'^{re.escape(story_prefix)}\s+Story\s+(\d+\.\d+):\s*(.+)$', re.MULTILINE
    )

    # Also match any heading at epic level or above as section boundary
    any_heading_at_epic = re.compile(
        rf'^#{{{1},{epic_level}}}\s+', re.MULTILINE
    )

    lines = content.splitlines()
    epics = []
    stories = []

    # Find all epic and story positions
    epic_positions = []
    story_positions = []

    for i, line in enumerate(lines):
        em = re.match(rf'^{re.escape(epic_prefix)}\s+Epic\s+(\d+):\s*(.+)$', line)
        if em:
            epic_positions.append((i, em.group(1), em.group(2)))
        sm = re.match(rf'^{re.escape(story_prefix)}\s+Story\s+(\d+\.\d+):\s*(.+)$', line)
        if sm:
            story_positions.append((i, sm.group(1), sm.group(2)))

    # Parse epics with their content
    for idx, (line_num, epic_id, epic_title) in enumerate(epic_positions):
        # Content runs until next epic heading or end of file
        if idx + 1 < len(epic_positions):
            end_line = epic_positions[idx + 1][0]
        else:
            end_line = len(lines)

        content_lines = lines[line_num + 1:end_line]
        description_parts = []
        phase = ""
        requirements = []
        dependencies = []

        for cl in content_lines:
            # Skip story headings and deeper - they belong to stories
            if re.match(rf'^#{{{story_level},}}\s+', cl):
                break

            # Extract phase
            pm = re.match(r'^\*\*(?:Target\s+)?Phase:\*\*\s*(.+)', cl, re.IGNORECASE)
            if pm:
                phase = pm.group(1).strip()
                continue

            # Extract dependencies
            dm = re.match(r'^\*\*Depend(?:s on|encies):\*\*\s*(.+)', cl, re.IGNORECASE)
            if dm:
                deps_text = dm.group(1).strip()
                dependencies = [d.strip() for d in re.split(r'[,;]', deps_text) if d.strip()]
                continue

            # Extract requirement references
            refs = re.findall(r'(?:FR|NFR|ARCH)-[\w.]+', cl)
            if refs:
                requirements.extend(refs)

            # Description lines (non-empty, non-metadata)
            stripped = cl.strip()
            if stripped and not stripped.startswith("**") and not re.match(rf'^#{{{1},}}\s+', cl):
                description_parts.append(stripped)

        # Deduplicate requirements
        requirements = sorted(set(requirements))

        epics.append({
            "id": epic_id,
            "title": epic_title.strip(),
            "description": "\n".join(description_parts).strip(),
            "phase": phase,
            "requirements": requirements,
            "dependencies": dependencies
        })

    # Parse stories with their content
    for idx, (line_num, story_id, story_title) in enumerate(story_positions):
        # Determine parent epic
        epic_id = story_id.split(".")[0]

        # Content runs until next story heading or next epic heading or end
        end_line = len(lines)
        for next_pos in story_positions[idx + 1:]:
            end_line = next_pos[0]
            break
        # Also check next epic
        for ep_pos in epic_positions:
            if ep_pos[0] > line_num and ep_pos[0] < end_line:
                end_line = ep_pos[0]
                break

        content_lines = lines[line_num + 1:end_line]

        user_story_text = ""
        acceptance_criteria = ""
        requirements = []
        in_ac = False
        ac_lines = []
        desc_lines = []

        for cl in content_lines:
            # Check for AC header
            if re.match(r'^\*\*Acceptance Criteria:\*\*|^#{1,6}\s+Acceptance Criteria', cl):
                in_ac = True
                continue

            # Check for end of AC block (new bold section or higher heading)
            if in_ac:
                if re.match(r'^#{1,6}\s+', cl) and not re.match(r'^#{1,6}\s+Acceptance Criteria', cl):
                    in_ac = False
                elif re.match(r'^\*\*[^*]+:\*\*', cl) and not re.match(r'^\*\*Acceptance Criteria:\*\*', cl):
                    in_ac = False
                else:
                    ac_lines.append(cl)
                    continue

            # Extract requirement references
            refs = re.findall(r'(?:FR|NFR|ARCH)-[\w.]+', cl)
            if refs:
                requirements.extend(refs)

            # Description lines
            stripped = cl.strip()
            if stripped and not re.match(r'^#{1,6}\s+', cl):
                desc_lines.append(stripped)

        # First paragraph is typically the user story text
        user_story_text = "\n".join(desc_lines).strip()
        acceptance_criteria = "\n".join(ac_lines).strip()
        requirements = sorted(set(requirements))

        stories.append({
            "id": story_id,
            "epicId": epic_id,
            "title": story_title.strip(),
            "userStoryText": user_story_text,
            "acceptanceCriteria": acceptance_criteria,
            "requirements": requirements
        })

    return epics, stories


def parse_story_file(story_id, story_path):
    """Parse a single story file for task/subtask breakdowns, status, and review follow-ups.

    Returns (tasks, status, review_tasks) where:
    - tasks: list of task dicts with subtasks
    - status: string or None (e.g., 'done', 'in-progress', 'review', 'draft')
    - review_tasks: list of review follow-up task dicts
    """
    tasks = []
    status = None
    review_tasks = []

    if not os.path.isfile(story_path):
        return tasks, status, review_tasks

    with open(story_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.splitlines()

    # --- Extract Status field ---
    for line in lines:
        sm = re.match(r'^\*?\*?Status:\*?\*?\s*(.+)$', line, re.IGNORECASE)
        if sm:
            status = sm.group(1).strip().lower()
            break

    # --- Extract Tasks ---
    in_tasks = False
    task_num = 0
    current_task_num = 0

    for line in lines:
        # Detect Tasks section header
        if re.match(r'^##\s+Tasks\s*/?\s*Subtasks', line, re.IGNORECASE):
            in_tasks = True
            continue

        # End of tasks section on next heading (## or deeper)
        if in_tasks and re.match(r'^#{2,}\s+', line) and not re.match(r'^#{2,}\s+Tasks', line, re.IGNORECASE):
            break

        if not in_tasks:
            continue

        # Top-level task: "- [ ] description" or "- [x] description"
        tm = re.match(r'^- \[([ xX])\]\s*(.+)$', line)
        if tm:
            task_num += 1
            current_task_num = task_num
            tasks.append({
                "id": f"{story_id}-T{task_num}",
                "description": tm.group(2).strip(),
                "complete": tm.group(1).lower() == "x",
                "subtasks": []
            })
            continue

        # Subtask: indented "- [ ] description"
        sm = re.match(r'^\s{2,}- \[([ xX])\]\s*(.+)$', line)
        if sm and tasks:
            subtask_num = len(tasks[-1]["subtasks"]) + 1
            tasks[-1]["subtasks"].append({
                "id": f"{story_id}-T{current_task_num}.{subtask_num}",
                "description": sm.group(2).strip(),
                "complete": sm.group(1).lower() == "x"
            })

    # --- Extract Review Follow-ups ---
    review_header_re = re.compile(
        r'^###\s+Review Follow-ups(?:\s+Round\s+(\d+))?\s*\(AI\)\s*$', re.IGNORECASE
    )
    current_round = 0
    in_review = False
    item_num = 0

    for line in lines:
        hm = review_header_re.match(line)
        if hm:
            current_round = int(hm.group(1)) if hm.group(1) else 1
            in_review = True
            item_num = 0
            continue

        # End of review section on next heading at ## or ### level (that isn't another review header)
        if in_review and re.match(r'^##\s+', line) and not review_header_re.match(line):
            in_review = False
            continue

        if not in_review:
            continue

        # Review item: "- [ ] description" or "- [x] description"
        rm = re.match(r'^- \[([ xX])\]\s*(.+)$', line)
        if rm:
            item_num += 1
            review_tasks.append({
                "id": f"{story_id}-R{current_round}.{item_num}",
                "description": rm.group(2).strip(),
                "complete": rm.group(1).lower() == "x",
                "isReviewFollowup": True,
                "reviewRound": current_round,
                "subtasks": []
            })

    return tasks, status, review_tasks


def story_id_from_filename(filename):
    """Extract story ID from flat kebab-case filename.

    Example: '1-1-initialize-solution-scaffold.md' -> '1.1'
    """
    m = re.match(r'^(\d+)-(\d+)-', filename)
    return f"{m.group(1)}.{m.group(2)}" if m else None


def scan_story_files(stories_dir, story_ids):
    """Scan story directories and flat files for task breakdowns, statuses, and review follow-ups.

    3-pass scan returning (all_tasks, story_statuses, review_followups_by_story):
    1. Known story IDs in nested {N.M}/story.md format (backward compat)
    2. Flat {N-M-slug}.md files — skip IDs already found in pass 1
    3. Unknown nested directories matching ^\\d+\\.\\d+$
    """
    all_tasks = {}
    story_statuses = {}
    review_followups_by_story = {}

    if not stories_dir or not os.path.isdir(stories_dir):
        return all_tasks, story_statuses, review_followups_by_story

    found_ids = set()

    # Pass 1: Known story IDs in nested {N.M}/story.md format
    for story_id in story_ids:
        story_path = os.path.join(stories_dir, story_id, "story.md")
        if os.path.isfile(story_path):
            tasks, status, review_tasks = parse_story_file(story_id, story_path)
            if tasks:
                all_tasks[story_id] = tasks
            if status:
                story_statuses[story_id] = status
            if review_tasks:
                review_followups_by_story[story_id] = review_tasks
            found_ids.add(story_id)

    # Pass 2: Flat {N-M-slug}.md files — skip IDs already found
    try:
        for entry in os.listdir(stories_dir):
            if not entry.endswith(".md"):
                continue
            sid = story_id_from_filename(entry)
            if not sid or sid in found_ids:
                continue
            story_path = os.path.join(stories_dir, entry)
            if os.path.isfile(story_path):
                tasks, status, review_tasks = parse_story_file(sid, story_path)
                if tasks:
                    all_tasks[sid] = tasks
                if status:
                    story_statuses[sid] = status
                if review_tasks:
                    review_followups_by_story[sid] = review_tasks
                found_ids.add(sid)
    except OSError:
        pass

    # Pass 3: Unknown nested directories matching ^\d+\.\d+$
    try:
        for entry in os.listdir(stories_dir):
            entry_path = os.path.join(stories_dir, entry)
            if os.path.isdir(entry_path) and re.match(r'^\d+\.\d+$', entry) and entry not in found_ids:
                story_path = os.path.join(entry_path, "story.md")
                if os.path.isfile(story_path):
                    tasks, status, review_tasks = parse_story_file(entry, story_path)
                    if tasks:
                        all_tasks[entry] = tasks
                    if status:
                        story_statuses[entry] = status
                    if review_tasks:
                        review_followups_by_story[entry] = review_tasks
                    found_ids.add(entry)
    except OSError:
        pass

    return all_tasks, story_statuses, review_followups_by_story


def parse_sprint_yaml(path):
    """Parse sprint-status.yaml without PyYAML (simple key-value parser)."""
    iterations = []

    if not path or not os.path.isfile(path):
        return iterations

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple YAML parser for the expected sprint-status structure
    lines = content.splitlines()
    current_sprint = None
    current_data = {}

    for line in lines:
        # Sprint name: "Sprint 1":  or  Sprint 1:
        sm = re.match(r'^\s+"([^"]+)":\s*$|^\s+(\S[^:]*):\s*$', line)
        if sm:
            name = sm.group(1) or sm.group(2)
            # Check if this looks like a sprint name vs a property
            if name and name not in ("sprints", "startDate", "endDate", "stories"):
                if current_sprint and current_data:
                    iterations.append({
                        "name": current_sprint,
                        **current_data
                    })
                current_sprint = name
                current_data = {"startDate": "", "endDate": "", "stories": []}
            continue

        # Properties under a sprint
        if current_sprint:
            # startDate / endDate
            dm = re.match(r'^\s+startDate:\s*"?([^"]*)"?\s*$', line)
            if dm:
                current_data["startDate"] = dm.group(1).strip()
                continue
            dm = re.match(r'^\s+endDate:\s*"?([^"]*)"?\s*$', line)
            if dm:
                current_data["endDate"] = dm.group(1).strip()
                continue

            # Stories list: stories: ["1.1", "1.2"]
            slm = re.match(r'^\s+stories:\s*\[([^\]]*)\]', line)
            if slm:
                raw = slm.group(1)
                current_data["stories"] = [
                    s.strip().strip('"').strip("'")
                    for s in raw.split(",")
                    if s.strip()
                ]
                continue

            # Stories as YAML list items: - "1.1"
            sim = re.match(r'^\s+-\s*"?([^"]*)"?\s*$', line)
            if sim:
                val = sim.group(1).strip()
                if val:
                    current_data["stories"].append(val)

    # Don't forget the last sprint
    if current_sprint and current_data:
        iterations.append({
            "name": current_sprint,
            **current_data
        })

    return iterations


def main():
    parser = argparse.ArgumentParser(
        description="Parse BMAD artifacts (epics, stories, tasks, sprints) into structured JSON"
    )
    parser.add_argument("--epics", required=True, help="Path to epics.md")
    parser.add_argument("--stories-dir", default="", help="Path to implementation artifacts directory")
    parser.add_argument("--sprint-yaml", default="", help="Path to sprint-status.yaml")
    parser.add_argument("--output", required=True, help="Path to write output JSON")
    args = parser.parse_args()

    # Parse epics.md
    epics, stories = parse_epics_file(args.epics)

    # Scan story files for tasks, statuses, and review follow-ups
    story_ids = [s["id"] for s in stories]
    tasks_by_story, story_statuses, review_followups_by_story = scan_story_files(args.stories_dir, story_ids)

    # Flatten tasks
    all_tasks = []
    for story_id, task_list in sorted(tasks_by_story.items()):
        for task in task_list:
            all_tasks.append({**task, "storyId": story_id})

    # Flatten review follow-up tasks and merge into all_tasks
    all_review_tasks = []
    for story_id, review_list in sorted(review_followups_by_story.items()):
        for task in review_list:
            all_review_tasks.append({**task, "storyId": story_id})
    all_tasks.extend(all_review_tasks)

    # Parse sprint data
    iterations = parse_sprint_yaml(args.sprint_yaml)

    result = {
        "epics": epics,
        "stories": stories,
        "tasks": all_tasks,
        "iterations": iterations,
        "storyStatuses": story_statuses,
        "counts": {
            "epics": len(epics),
            "stories": len(stories),
            "tasks": len(all_tasks),
            "storyFilesWithTasks": len(tasks_by_story),
            "iterations": len(iterations),
            "reviewFollowupTasks": len(all_review_tasks),
            "storyFilesWithReviewFollowups": len(review_followups_by_story)
        }
    }

    # Write output
    output_path = args.output
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # Also print to stdout for visibility
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
