# Parsing Patterns

**Purpose:** Regex patterns and heading structures for extracting epics, stories, and tasks from BMAD artifacts. Also defines content hash scope per item type.

---

## Source 1: epics.md

### Epic Headers

**Pattern:** Level 2 heading with "Epic N:" prefix

```regex
^## Epic (\d+):\s*(.+)$
```

- Capture group 1: Epic ID (e.g., `1`, `2`, `15`)
- Capture group 2: Epic title

**Content under each epic until next `## Epic` or `## ` heading:**
- Description paragraphs
- Phase assignment (look for `**Phase:**` or `**Target Phase:**`)
- Requirements references (look for `FR-`, `NFR-`, `ARCH-` patterns)
- Dependencies (look for `**Dependencies:**` or `**Depends on:**`)

### Story Headers

**Pattern:** Level 3 heading with "Story N.M:" prefix

```regex
^### Story (\d+\.\d+):\s*(.+)$
```

- Capture group 1: Story ID (e.g., `1.1`, `3.5`)
- Capture group 2: Story title

**Content under each story until next `### Story` or `### ` or `## ` heading:**
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

Story files are created by the Create Story workflow at:
```
{implementation_artifacts}/{story-id}/story.md
```

Example: `_bmad-output/implementation-artifacts/1.1/story.md`

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

---

## Source 3: sprint-status.yaml

### Structure

```yaml
sprints:
  "Sprint 1":
    startDate: "2026-03-01"
    endDate: "2026-03-14"
    stories: ["1.1", "1.2", "1.3"]
  "Sprint 2":
    startDate: "2026-03-15"
    endDate: "2026-03-28"
    stories: ["2.1", "2.2"]
```

**Extract:** Sprint name, dates, and story assignments for Azure DevOps Iteration creation.

---

## Content Hash Scope

Content hashes use normalized input (strip excess whitespace, trim, lowercase, sort lists) then SHA-256.

### Epic Hash Inputs

```
normalize(title) + normalize(description) + normalize(phase) + sort(requirements[]).join(",")
```

### Story Hash Inputs

```
normalize(title) + normalize(userStoryText) + normalize(acceptanceCriteriaBlock)
```

**Note:** The entire AC block is hashed as-is (after normalization), not individual AC items.

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

### Hash Computation Commands

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
