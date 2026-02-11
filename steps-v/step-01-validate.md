---
name: 'step-01-validate'
description: 'Audit sync state, detect drift between BMAD and DevOps, check for new bugs'

configFile: '{output_folder}/devops-sync-config.yaml'
syncFile: '{output_folder}/devops-sync.yaml'
bugsFile: '{output_folder}/devops-bugs.yaml'
parsingPatterns: '../data/parsing-patterns.md'
cliReference: '../data/azure-devops-cli.md'
---

# Validate: Audit Sync State

## STEP GOAL:

Load existing sync mappings, re-parse local BMAD files, query Azure DevOps via `az boards` CLI for current state, compare content hashes bidirectionally, check for new bugs, and produce a comprehensive drift report.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`
- ⚙️ TOOL/SUBPROCESS FALLBACK: If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread

### Role Reinforcement:

- ✅ You are a DevOps Integration Engineer — auditing and reporting
- ✅ Report findings clearly with actionable recommendations
- ✅ This is READ-ONLY — no modifications to BMAD files or DevOps items

### Step-Specific Rules:

- 🎯 Focus on comparison and reporting — zero modifications
- 🚫 FORBIDDEN to create, update, or delete any Azure DevOps work items
- 🚫 FORBIDDEN to modify any local BMAD files
- 💬 Report drift clearly so user can decide whether to re-sync

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly
- 💾 Write bug findings to {bugsFile}
- 📖 Present drift report at the end
- 🚫 Read-only operations only

## CONTEXT BOUNDARIES:

- Available: {configFile}, {syncFile}, BMAD source files, `az boards` CLI (read-only queries)
- Focus: Comparison, drift detection, bug discovery
- Limits: No write operations to DevOps
- Dependencies: Prior Create sync must have run (config and sync files must exist)

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Load Prerequisites

Load {configFile} — if missing: "Config not found. Run Create mode first to initialize." — HALT.

Load {syncFile} — if missing: "Sync state not found. Run Create mode first." — HALT.

Load {cliReference} for CLI command patterns.

Report: "Loaded config and sync state. {N} mapped items to validate."

### 2. Re-Parse Local BMAD Files

Using patterns from {parsingPatterns}, re-parse:
- `epics.md` for current epics and stories
- Story files for current task breakdowns (if they exist)

Compute fresh content hashes for all items (see {parsingPatterns} "Hash Computation Commands" for exact shell commands).

Report: "Re-parsed BMAD files. Computing hashes for comparison..."

### 3. Compare Local Hashes vs Stored Hashes

For each item in the sync file, compare stored hash against freshly computed hash:

| Stored Hash | Fresh Hash | Classification |
|-------------|-----------|----------------|
| Match | Match | **In sync** — local unchanged since last sync |
| Differ | — | **Local changed** — BMAD updated but not synced |
| — | Item not found locally | **Locally removed** — exists in DevOps but deleted from BMAD |
| Not in sync file | Fresh hash exists | **Never synced** — new item not yet pushed |

### 4. Query Azure DevOps State

For a sample of mapped items (up to 50, or all if fewer), query Azure DevOps to verify they still exist:

```bash
az boards query \
  --wiql "SELECT [System.Id], [System.Title], [System.State] FROM workitems WHERE [System.Id] IN ({comma-separated-ids})" \
  --output json
```

Check for:
- **Missing items:** Work item ID returned no result — may have been deleted from DevOps
- **State changes:** DevOps state different from expected (informational only)

Report: "Queried Azure DevOps for {N} items. {M} discrepancies found."

### 5. Query for New Bugs

Using the WIQL bug query from {cliReference}:

```bash
az boards query \
  --wiql "SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], [System.CreatedDate] FROM workitems WHERE [System.WorkItemType] = 'Bug' AND [System.AreaPath] UNDER '{areaPath}' AND [System.State] <> 'Closed' ORDER BY [System.CreatedDate] DESC" \
  --output json
```

For each bug ID not already in {bugsFile}, fetch details:

```bash
az boards work-item show --id {bugId} --output json
```

### 6. Write Bugs File

If new bugs found, write or update {bugsFile}:

```yaml
# Azure DevOps Bugs — Synced from Validate mode
lastChecked: "{current-ISO-timestamp}"
bugs:
  - devopsId: {id}
    title: "{title}"
    state: "{state}"
    assignedTo: "{name}"
    createdDate: "{date}"
    description: "{description}"
    bmadStatus: "new"  # new | triaged | fixed
```

Report: "{N} new bugs found and written to {bugsFile}."

If no new bugs: Report: "No new bugs found."

### 7. Present Drift Report

Display:

```
VALIDATION REPORT
=================
                In Sync    Local Changed    Never Synced    Locally Removed    DevOps Missing
Epics:          {n}        {n}              {n}             {n}                {n}
Stories:        {n}        {n}              {n}             {n}                {n}
Tasks:          {n}        {n}              {n}             {n}                {n}

Last full sync: {lastFullSync from sync file}

{If local changes detected:}
LOCAL CHANGES (not yet synced):
- Story 1.3: acceptance criteria updated
- Epic 5: description changed
→ Run Create mode to push these changes.

{If locally removed items:}
LOCALLY REMOVED (in DevOps but removed from BMAD):
- Story 2.1 (DevOps #12346): no longer in epics.md
→ Review and remove from DevOps manually if no longer needed.

{If DevOps items missing:}
DEVOPS ITEMS MISSING:
- Story 2.1 (DevOps #12346): not found in Azure DevOps — may have been deleted
→ Review and re-sync if needed.

BUGS:
- {N} new bugs found (written to {bugsFile})
- {M} previously known bugs

Recommendation: {recommendation based on findings}
```

### 8. Workflow Complete

Display: "**Validation complete.** Run [C]reate mode to push local changes, or review bugs in {bugsFile}."

No next step — workflow ends.

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All mapped items validated against local files and stored hashes
- Azure DevOps state spot-checked via `az boards query`
- New bugs discovered and written to {bugsFile}
- Orphaned/locally-removed items flagged with manual review guidance
- Comprehensive drift report displayed
- Zero modifications made to BMAD files or DevOps items

### ❌ SYSTEM FAILURE:

- Creating, updating, or deleting Azure DevOps work items
- Modifying any BMAD source files
- Not checking for new bugs
- Reporting inaccurate hash comparisons
- Not flagging locally-removed/orphaned items

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
