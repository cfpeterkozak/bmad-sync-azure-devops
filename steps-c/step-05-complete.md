---
name: 'step-05-complete'
description: 'Write devops-sync.yaml with all mappings and present final sync report'

syncFile: '{output_folder}/devops-sync.yaml'
syncResults: '{output_folder}/_sync-results.json'
diffResults: '{output_folder}/_diff-results.json'
configFile: '{output_folder}/devops-sync-config.yaml'
writeStateScript: '../scripts/write-sync-state.py'
---

# Step 5: Write Results and Final Report

## STEP GOAL:

Persist all sync results to the mapping file and present a comprehensive final report showing what was created, updated, and any errors encountered.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`
- ⚙️ TOOL/SUBPROCESS FALLBACK: If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread

### Role Reinforcement:

- ✅ You are a DevOps Integration Engineer — final reporting
- ✅ Present results clearly and completely
- ✅ This is the final step — no next step to load

### Step-Specific Rules:

- 🎯 Focus on writing the sync file and presenting the report
- 🚫 FORBIDDEN to make any more Azure DevOps API calls
- 💬 Include all work item IDs and hashes in the sync file

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly
- 💾 Write {syncFile} with complete mapping data
- 📖 Present final summary report
- 🚫 This is the final step — workflow ends here

## CONTEXT BOUNDARIES:

- Available: All sync results from step 04, computed hashes from step 03
- Focus: Persistence and reporting
- Limits: No more API calls
- Dependencies: Step 04 completed

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Write Sync State File

**Primary method — cross-platform Python script:**

```bash
python {writeStateScript} --diff "{diffResults}" --sync-results "{syncResults}" --config "{configFile}" --output "{syncFile}"
```

The script:
1. Loads diff results (all items with contentHash and classification) and sync results (ID maps and iteration outcomes)
2. Merges data: uses devopsId from sync results ID maps, contentHash from diff results
3. Correctly extracts iteration slugs from the sync results `created[]`/`skipped[]` arrays (NOT the top-level dict keys)
4. Marks failed items (devopsId = "None") as `status: "pending"` for retry
5. Preserves unchanged items from diff results
6. Writes deterministic YAML with proper formatting

Report the counts from the script output.

**Fallback (if Python unavailable):**

Compile all results manually following this schema:

```yaml
lastFullSync: "{current-ISO-timestamp}"
epics:
  "{epicId}":
    devopsId: {work-item-id}
    contentHash: "{computed-hash}"
    lastSynced: "{current-ISO-timestamp}"
    status: "synced"
stories:
  "{storyId}":
    devopsId: {work-item-id}
    epicDevopsId: {parent-epic-devops-id}
    contentHash: "{computed-hash}"
    lastSynced: "{current-ISO-timestamp}"
    status: "synced"
tasks:
  "{taskId}":
    devopsId: {work-item-id}
    storyDevopsId: {parent-story-devops-id}
    contentHash: "{computed-hash}"
    lastSynced: "{current-ISO-timestamp}"
    status: "synced"
iterations:
  "{iterationSlug}":
    epicId: "{epicId}"
    devopsId: {iteration-id}
    devopsPath: "\\{project}\\Iteration\\{iterationRootPath}\\{slug}"
    lastSynced: "{current-ISO-timestamp}"
```

**CRITICAL:** For iterations, extract actual slugs from sync results `created[]` and `skipped[]` arrays. Do NOT use the top-level dict keys (`created`, `failed`, `skipped`, `movements`) as iteration IDs.

**For items that failed:** Set `status: "pending"` (no devopsId) so next sync retries them.

Report: "Sync state written to {syncFile}"

### 3. Present Final Report

Display:

```
SYNC COMPLETE
=============
              Created    Updated    Unchanged    Failed
Epics:        {n}        {n}        {n}          {n}
Stories:      {n}        {n}        {n}          {n}
Tasks:        {n}        {n}        {n}          {n}
Iterations:   {n}        -          {n}          {n}

Total API calls: {total}
Sync file: {syncFile}

{If failures exist:}
FAILED ITEMS:
- Epic {id}: {error message}
- Story {id}: {error message}
These items are marked 'pending' and will be retried on next sync.

{If orphaned items from step 03:}
ORPHANED ITEMS (in DevOps but not in BMAD):
- {type} {id} (DevOps #{devopsId})
Review and remove manually if no longer needed.
```

### 4. Workflow Complete

Display: "**Sync workflow complete.** Run again with [C]reate mode for incremental updates, or [V]alidate mode to check for drift."

No next step — workflow ends.

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- {syncFile} written with all work item IDs, hashes, and timestamps
- Failed items marked as "pending" for retry
- Unchanged items preserved from prior sync
- Comprehensive final report displayed
- Workflow ended cleanly

### ❌ SYSTEM FAILURE:

- Making additional API calls
- Losing work item IDs (not writing them to sync file)
- Overwriting unchanged entries with empty data
- Not marking failed items for retry
- Attempting to load a next step (this is the final step)

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
