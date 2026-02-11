# Parsing Patterns

**Purpose:** Regex patterns and heading structures for extracting epics, stories, and tasks from BMAD artifacts. Also defines content hash scope per item type.

---

## Source 1: epics.md

### Epic Headers

**Pattern:** Heading with "Epic N:" prefix (flexible heading level — auto-detected by parse script)

```regex
^#{2,4} Epic (\d+):\s*(.+)$
```

- Capture group 1: Epic ID (e.g., `1`, `2`, `15`)
- Capture group 2: Epic title
- Heading levels vary between projects (`##`, `###`, or `####`). The `scripts/parse-artifacts.py` script auto-detects the level by scanning for the first `Epic N:` heading.

**Content under each epic until next epic heading or same-level heading:**
- Description paragraphs
- Phase assignment (look for `**Phase:**` or `**Target Phase:**`)
- Requirements references (look for `FR-`, `NFR-`, `ARCH-` patterns)
- Dependencies (look for `**Dependencies:**` or `**Depends on:**`)

### Story Headers

**Pattern:** Heading with "Story N.M:" prefix (one level below epics — auto-detected)

```regex
^#{2,5} Story (\d+\.\d+):\s*(.+)$
```

- Capture group 1: Story ID (e.g., `1.1`, `3.5`)
- Capture group 2: Story title
- Story headings are always one level deeper than epic headings. The `scripts/parse-artifacts.py` script auto-detects both levels.

**Content under each story until next story heading, epic heading, or same-level heading:**
- User story text (first paragraph, often "As a... I want... So that...")
- Acceptance criteria block (see below)
- FR/NFR/ARCH references inline

### Acceptance Criteria Block

**Start pattern:** Line matching `**Acceptance Criteria:**` or `#### Acceptance Criteria`

```regex
^\*\*Acceptance Criteria:\*\*|^#### Acceptance Criteria
```

**AC items:** Lines starting with `- [ ]` or `- [x]` or `- ` after the AC header

```regex
^- \[[ x]\]\s*(.+)$|^- (.+)$
```

**End:** Next `###` heading, `**` bold line starting a new section, or blank line followed by non-AC content

---

## Source 2: Story Files (Individual)

### File Location

Story files are discovered in two formats (flat files take priority when both exist for the same ID):

**Format 1 — Flat kebab-case files (preferred):**
```
{implementation_artifacts}/{N-M-slug}.md
```
Example: `_bmad-output/implementation-artifacts/1-1-initialize-solution-scaffold-with-net-aspire.md`

Story ID extraction pattern:
```regex
^(\d+)-(\d+)-
```
Result: `{group1}.{group2}` → e.g., `1.1`

**Format 2 — Nested directories (backward compat):**
```
{implementation_artifacts}/{story-id}/story.md
```
Example: `_bmad-output/implementation-artifacts/1.1/story.md`

**Discovery priority:** The 3-pass scan in `parse-artifacts.py` ensures each story ID is only parsed once:
1. Known story IDs from `epics.md` in nested `{N.M}/story.md` format
2. Flat `{N-M-slug}.md` files — skips IDs already found in pass 1
3. Unknown nested directories matching `^\d+\.\d+$` — skips IDs found in passes 1-2

### Task/Subtask Extraction

**Section marker:** `## Tasks / Subtasks` or `## Tasks/Subtasks`

```regex
^## Tasks\s*/?\s*Subtasks
```

**Task items:** Checkboxes under the Tasks section

```regex
^- \[([ x])\]\s*(.+)$
```

- Capture group 1: Checkbox state (space = uncomplete, x = complete)
- Capture group 2: Task description

**Subtask items:** Indented checkboxes (2+ spaces or tab before dash)

```regex
^\s{2,}- \[([ x])\]\s*(.+)$
```

**Task ID generation:** Sequential within story: `{storyId}-T1`, `{storyId}-T2`, etc.

**Subtask ID:** `{storyId}-T{N}.{M}` (subtask M under task N)

### Status Field

**Pattern:** Matches both `Status: done` and `**Status:** done` (case-insensitive)

```regex
^\*?\*?Status:\*?\*?\s*(.+)$
```

**Valid values:** `draft`, `in-progress`, `review`, `done`

- Extracted from the first matching line in the story file
- Value is normalized to lowercase
- Maps to Azure DevOps work item state (see `azure-devops-cli.md` State Mapping)
- Included in story content hash — status changes trigger CHANGED classification

### Review Follow-ups

Review follow-up sections contain AI code review items that sync as Task work items in Azure DevOps.

**Section header pattern:**

```regex
^###\s+Review Follow-ups(?:\s+Round\s+(\d+))?\s*\(AI\)\s*$
```

Matches headers like:
- `### Review Follow-ups (AI)` — defaults to Round 1
- `### Review Follow-ups Round 2 (AI)`
- `### Review Follow-ups Round 3 (AI)`

**Item pattern:** Same checkbox format as tasks:

```regex
^- \[([ xX])\]\s*(.+)$
```

**Review follow-up ID generation:** `{storyId}-R{round}.{itemNum}`

Examples: `1.1-R1.1`, `1.1-R1.2`, `1.1-R2.1`, `1.1-R2.3`

**Metadata fields:** Each review follow-up task includes:
- `isReviewFollowup: true`
- `reviewRound: N` (integer)

Review follow-up tasks are merged into the main `tasks` array and use the same `description + checkboxState` hash as regular tasks.

---

## Source 3: sprint-status.yaml (Epic Statuses)

### Structure

```yaml
development_status:
  epic-1: in-progress
  epic-2: backlog
  epic-3: done
```

**Extract:** Epic ID → development status. Used to derive epic-based iterations — when an epic reaches `in-progress` or `done`, a sub-iteration is auto-created and the epic + its stories + their tasks are moved into it.

### Parsing

The `development_status:` block is parsed line-by-line. Each `epic-N: status` entry maps epic ID to status string (e.g., `{"1": "in-progress", "2": "backlog"}`). Parsing stops at the next non-indented line.

```regex
^\s+epic-(\d+):\s*(\S+)\s*$
```

- Capture group 1: Epic ID (e.g., `1`, `2`)
- Capture group 2: Status (e.g., `in-progress`, `backlog`, `done`)

---

## Content Hash Scope

Content hashes use normalized input (strip excess whitespace, trim, lowercase, sort lists) then SHA-256.

### Epic Hash Inputs

```
normalize(title) + normalize(description) + normalize(phase) + sort(requirements[]).join(",") + normalize(epicStatus)
```

**Note:** The epic status from `sprint-status.yaml` (e.g., `in-progress`, `done`) is included so that status changes trigger CHANGED classification and iteration creation.

### Story Hash Inputs

```
normalize(title) + normalize(userStoryText) + normalize(acceptanceCriteriaBlock) + normalize(status)
```

**Note:** The entire AC block is hashed as-is (after normalization), not individual AC items. The status field (e.g., `done`, `in-progress`) is included so that status changes trigger CHANGED classification and state sync.

### Task Hash Inputs

```
normalize(taskDescription) + checkboxState
```

Where `checkboxState` = `"complete"` or `"incomplete"`

### Normalization Rules

1. Trim leading/trailing whitespace
2. Collapse multiple spaces/newlines to single space
3. Convert to lowercase
4. For lists: sort alphabetically, then join with ","
5. Concatenate all fields with `|` separator
6. SHA-256 the result, output as hex string (first 12 chars for readability)

### Hash Computation

**Primary method — cross-platform Python script:**

```bash
python scripts/compute-hashes.py --parsed "{output_folder}/_parsed-artifacts.json" --sync-state "{syncFile}" --output "{output_folder}/_diff-results.json"
```

The script handles all normalization, SHA-256 computation, and diff classification internally using Python's `hashlib`. No shell commands needed — fully cross-platform.

**Manual fallback (if Python not available):**

The LLM cannot compute SHA-256 natively. Use these shell commands via the Bash tool:

**Linux/Mac:**
```bash
echo -n "normalized|content|string" | sha256sum | cut -c1-12
```

**PowerShell:**
```powershell
$bytes = [Text.Encoding]::UTF8.GetBytes("normalized|content|string")
$hash = [BitConverter]::ToString(([Security.Cryptography.SHA256]::Create()).ComputeHash($bytes)).Replace("-","").Substring(0,12).ToLower()
$hash
```

**Important:** The input string must be fully normalized (steps 1-5 above) BEFORE hashing. Build the normalized string in the LLM context, then pass it to the shell command for hashing.

---

## Extraction Return Format

### Sub-agent Return (epics.md parsing)

```json
{
  "epics": [
    {
      "id": "1",
      "title": "Infrastructure & Foundation",
      "description": "...",
      "phase": "Alpha",
      "requirements": ["FR-1.1", "FR-1.2", "ARCH-1"],
      "dependencies": []
    }
  ],
  "stories": [
    {
      "id": "1.1",
      "epicId": "1",
      "title": "Initialize Solution Scaffold with .NET Aspire",
      "userStoryText": "As a developer...",
      "acceptanceCriteria": "- [ ] AC1\n- [ ] AC2\n...",
      "requirements": ["FR-1.1"]
    }
  ]
}
```

### Sub-process Return (story file parsing)

```json
{
  "storyId": "1.1",
  "tasks": [
    {
      "id": "1.1-T1",
      "description": "Set up solution structure",
      "complete": false,
      "subtasks": [
        { "id": "1.1-T1.1", "description": "Create .sln file", "complete": false }
      ]
    }
  ]
}
```
