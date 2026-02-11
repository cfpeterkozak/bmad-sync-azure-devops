---
name: 'step-02-parse'
description: 'Extract structured data from epics.md, story files, and sprint-status.yaml'

nextStepFile: './step-03-diff.md'
configFile: '{output_folder}/devops-sync-config.yaml'
parsingPatterns: '../data/parsing-patterns.md'
---

# Step 2: Parse BMAD Artifacts

## STEP GOAL:

Extract structured data (epics, stories, tasks, iterations) from all BMAD source files into a compact in-memory representation for comparison and sync.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`
- ⚙️ TOOL/SUBPROCESS FALLBACK: If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread

### Role Reinforcement:

- ✅ You are a DevOps Integration Engineer — direct, status-focused, reporting results
- ✅ No facilitation or open-ended conversation — execute mechanically and report outcomes
- ✅ Tone: "Parsing epics.md... found 15 epics, 47 stories. Scanning story files... 3 task breakdowns found."

### Step-Specific Rules:

- 🎯 Focus ONLY on parsing — do not create or update anything in Azure DevOps
- 🚫 FORBIDDEN to modify any source files
- 🎯 Use subprocess Pattern 3 (Data Ops) for large epics.md to keep context clean
- 🎯 Use subprocess Pattern 4 (Parallel) for story file parsing when multiple story files exist
- 💬 Subprocesses return compact structured JSON — never full file contents
- ⚙️ If subprocesses unavailable, perform all parsing in main thread sequentially

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly
- 💾 Keep parsed data in memory for step-03 (do not write intermediate files)
- 📖 Report counts at each parsing stage
- 🚫 Do not halt on individual parse errors — log and continue

## CONTEXT BOUNDARIES:

- Available: BMM config (planning_artifacts, implementation_artifacts), {configFile} from step 01
- Focus: Data extraction only — no API calls, no diffing
- Limits: Do not compute hashes yet (that's step 03)
- Dependencies: Step 01 completed successfully (config file exists)

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Load Parsing Patterns

Load {parsingPatterns} for regex patterns and extraction rules.

### 2. Parse epics.md

Load {parsingPatterns} section "Source 1: epics.md" for heading patterns.

Locate `epics.md` at `{planning_artifacts}/epics.md`.

**Subprocess optimization (Pattern 3 — Data Operations):**

Launch a sub-agent that:
1. Loads the full `epics.md` file (potentially 6,000+ lines)
2. Extracts all epics using the `^## Epic (\d+):\s*(.+)$` pattern
3. For each epic: extracts title, description, phase, requirements references, dependencies
4. Extracts all stories using the `^### Story (\d+\.\d+):\s*(.+)$` pattern
5. For each story: extracts title, user story text, acceptance criteria block, epic parent ID
6. Returns compact JSON per the return format in {parsingPatterns}

**Fallback:** If sub-agent unavailable, parse epics.md directly in main thread section by section.

Report: "Parsed epics.md: {N} epics, {M} stories extracted."

### 3. Scan Story Files for Task Breakdowns

Check `{implementation_artifacts}/` for existing story directories containing `story.md` files.

**If story files exist:**

**Subprocess optimization (Pattern 4 — Parallel):**

For each story file found, launch a sub-process that:
1. Loads the story file
2. Finds the `## Tasks / Subtasks` section
3. Extracts tasks (checkboxes) and subtasks (indented checkboxes) with completion state
4. Assigns task IDs per the pattern: `{storyId}-T1`, `{storyId}-T2`, etc.
5. Returns compact JSON per the return format in {parsingPatterns}

All sub-processes run in parallel. Aggregate results when all complete.

**Fallback:** If sub-processes unavailable, parse story files sequentially in main thread.

**If no story files exist:** Report: "No story files found. Tasks will be created when stories are implemented."

Report: "Scanned story files: {N} stories with task breakdowns, {T} total tasks."

### 4. Load Sprint Data

Check if `sprint-status.yaml` exists at `{planning_artifacts}/sprint-status.yaml`.

**If exists:** Parse iteration names, dates, and story assignments.

Report: "Loaded sprint data: {N} iterations defined."

**If not exists:** Report: "No sprint-status.yaml found. Iterations will be skipped."

### 5. Present Parsing Summary

Display consolidated summary:

```
PARSING COMPLETE
================
Epics:       {N} extracted from epics.md
Stories:     {M} extracted from epics.md
Tasks:       {T} extracted from {S} story files (0 if no story files yet)
Iterations:  {I} from sprint-status.yaml (0 if not found)

Parse errors: {E} (details listed above if any)
```

### 6. Present MENU OPTIONS

Display: "**Parsed data summary above. Confirm and continue?** [C] Continue to diff"

#### Menu Handling Logic:

- IF C: Carry parsed data forward, then load, read entire file, then execute {nextStepFile}
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#6-present-menu-options)

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- ONLY proceed to next step when user selects 'C'

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- epics.md parsed with all epics and stories extracted
- Story files scanned for task breakdowns (if they exist)
- sprint-status.yaml loaded (if it exists)
- Parse errors logged but did not halt the process
- Compact structured data ready for step 03
- User confirmed parsing results

### ❌ SYSTEM FAILURE:

- Modifying any source files
- Making Azure DevOps API calls during parsing
- Computing content hashes (that's step 03)
- Halting on individual parse errors (should log and continue)
- Loading full file contents into sub-agent return (should be compact JSON only)

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
