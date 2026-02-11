---
name: 'step-02-parse'
description: 'Extract structured data from epics.md, story files, and sprint-status.yaml'

nextStepFile: './step-03-diff.md'
configFile: '{output_folder}/devops-sync-config.yaml'
parsingPatterns: '../data/parsing-patterns.md'
parseScript: '../scripts/parse-artifacts.py'
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
- 🎯 Primary: Use {parseScript} for all parsing (cross-platform, handles heading level auto-detection)
- 🎯 Optional fallback: Use sub-agent approach if Python is unavailable
- ⚙️ If neither script nor subprocesses are available, perform all parsing in main thread sequentially

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

### 2. Parse All Artifacts

Locate source files:
- `epics.md` at `{planning_artifacts}/epics.md`
- Story files at `{implementation_artifacts}/`
- Sprint data at `{implementation_artifacts}/sprint-status.yaml`

**Primary method — cross-platform Python script:**

```bash
python {parseScript} --epics "{planning_artifacts}/epics.md" --stories-dir "{implementation_artifacts}" --sprint-yaml "{implementation_artifacts}/sprint-status.yaml" --output "{output_folder}/_parsed-artifacts.json"
```

The script:
1. Auto-detects heading levels (scans for `Epic N:` pattern at any `#` level)
2. Extracts all epics with title, description, phase, requirements, dependencies
3. Extracts all stories with title, user story text, acceptance criteria, epic parent
4. Scans story directories for task/subtask breakdowns with completion state
5. Parses sprint-status.yaml for epic development statuses (backlog, in-progress, done)
6. Writes structured JSON to the output path and prints it to stdout

Load the output JSON and report the counts from the `counts` field.

**Fallback (if Python unavailable) — sub-agent approach:**

Launch a sub-agent that:
1. Loads the full `epics.md` file
2. Extracts epics using `^#{2,4} Epic (\d+):\s*(.+)$` pattern (flexible heading level)
3. Extracts stories using `^#{2,5} Story (\d+\.\d+):\s*(.+)$` pattern (flexible heading level)
4. Returns compact JSON per the return format in {parsingPatterns}

If sub-agent also unavailable, parse in main thread sequentially using patterns from {parsingPatterns}.

Report: "Parsed epics.md: {N} epics, {M} stories extracted."

### 3. Verify Parse Results

Review the parsed JSON output:
- Check that epic and story counts look reasonable
- Check for any parse errors logged by the script

Report: "Scanned story files: {N} stories with task breakdowns, {T} total tasks."
Report: "Loaded sprint data: {I} iterations defined." (or "No sprint data found.")

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
- Manually writing a parser when the parse script is available

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
