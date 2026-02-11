---
name: 'step-03-diff'
description: 'Compare content hashes against stored state and present dry-run summary'

nextStepFile: './step-04-sync.md'
syncFile: '{output_folder}/devops-sync.yaml'
parsingPatterns: '../data/parsing-patterns.md'
---

# Step 3: Diff and Dry-Run Summary

## STEP GOAL:

Compare parsed data against the stored sync state (if exists), classify every item as new/changed/unchanged, and present a dry-run summary for user confirmation before any API calls.

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
- ✅ Present the dry-run clearly so the user can make an informed decision
- ✅ This is the CRITICAL CHECKPOINT — nothing happens in Azure DevOps without user approval here

### Step-Specific Rules:

- 🎯 Focus ONLY on diffing and reporting — zero API calls
- 🚫 FORBIDDEN to create or update any Azure DevOps work items
- 🚫 FORBIDDEN to proceed without explicit user confirmation
- 💬 Present dry-run with enough detail for informed decision

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly
- 💾 Keep diff results in memory for step 04
- 📖 Report classification for every item
- 🚫 This is a gate — user MUST confirm before sync proceeds

## CONTEXT BOUNDARIES:

- Available: Parsed data from step 02, {syncFile} (if exists from prior runs)
- Focus: Hash computation, comparison, classification, dry-run report
- Limits: No Azure DevOps interaction
- Dependencies: Step 02 completed with parsed data

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Load Existing Sync State

Check if {syncFile} exists.

**If exists:** Load the mapping file. Extract stored content hashes, DevOps work item IDs, and sync status for all epics, stories, tasks, and iterations.

Report: "Existing sync state loaded: {N} epics, {M} stories, {T} tasks, {I} iterations mapped."

**If not exists:** Report: "No prior sync state. This is a first-run — all items will be new."

### 2. Compute Content Hashes

Load hash scope definitions from {parsingPatterns} section "Content Hash Scope".

For each parsed item, compute a normalized content hash:

**Epics:** `normalize(title) + normalize(description) + normalize(phase) + sort(requirements).join(",")` then SHA-256 (first 12 hex chars)

**Stories:** `normalize(title) + normalize(userStoryText) + normalize(acceptanceCriteriaBlock)` then SHA-256 (first 12 hex chars)

**Tasks:** `normalize(taskDescription) + checkboxState` then SHA-256 (first 12 hex chars)

**Normalization:** Trim, collapse whitespace, lowercase, sort lists, join with `|` separator.

**Hash computation:** Use shell commands from {parsingPatterns} section "Hash Computation Commands" — the LLM cannot compute SHA-256 natively.

### 3. Classify Each Item

Compare computed hashes against stored hashes:

| Condition | Classification |
|-----------|---------------|
| Item not in sync file | **NEW** — will be created |
| Item in sync file, hash matches | **UNCHANGED** — will be skipped |
| Item in sync file, hash differs | **CHANGED** — will be updated |
| Item in sync file, not in parsed data | **ORPHANED** — in DevOps but removed from BMAD (warn only) |

### 4. Classify Iterations

For each iteration from sprint-status.yaml:

| Condition | Classification |
|-----------|---------------|
| Iteration not in sync file | **NEW** — will be created |
| Iteration in sync file | **EXISTS** — will be skipped |

### 5. Present Dry-Run Summary

Display:

```
DRY-RUN SUMMARY
================
                Create    Update    Unchanged    Orphaned
Epics:          {n}       {n}       {n}          {n}
Stories:        {n}       {n}       {n}          {n}
Tasks:          {n}       {n}       {n}          {n}
Iterations:     {n}       -         {n}          -

Total CLI calls estimated: {total}
  (Epics: create+update, Stories: create+link+update, Tasks: create+link+update, Iterations: create+assign)
```

**CLI call estimation:** Count 1 call per create, 1 per update, 1 per parent link (new stories and tasks), 1 per iteration assignment. Example: 15 new epics + 47 new stories (create+link each) + 10 new iterations + 47 iteration assignments = 15+94+10+47 = 166 calls.

**If orphaned items exist:** Display warning:
```
WARNING: {N} orphaned items found in DevOps but no longer in BMAD:
- [list items with DevOps IDs]
These will NOT be deleted. Review manually if needed.
```

**If nothing to do:** Display: "All items are up to date. Nothing to sync." — Do NOT proceed to step 04.

### 6. Present MENU OPTIONS

Display: "**Review the dry-run above. Proceed with sync?** [C] Confirm and sync [X] Cancel"

#### Menu Handling Logic:

- IF C: Carry diff results forward, then load, read entire file, then execute {nextStepFile}
- IF X: Report "Sync cancelled. No changes made." — END workflow
- IF Any other comments or queries: help user respond then [Redisplay Menu Options](#6-present-menu-options)

#### EXECUTION RULES:

- ALWAYS halt and wait for user input after presenting menu
- ONLY proceed to sync when user selects 'C'
- This is the critical gate — user approval required

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Content hashes computed for all parsed items using normalized input
- Every item classified as new/changed/unchanged/orphaned
- Dry-run summary displayed with accurate counts
- User explicitly confirmed before proceeding
- Orphaned items warned but not deleted

### ❌ SYSTEM FAILURE:

- Making any Azure DevOps API calls
- Proceeding to sync without user confirmation
- Using raw (non-normalized) content for hashing
- Deleting orphaned items from Azure DevOps
- Skipping the dry-run summary

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
