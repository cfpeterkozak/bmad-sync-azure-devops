---
name: 'step-04-sync'
description: 'Execute az boards CLI commands to create and update work items in dependency order'

nextStepFile: './step-05-complete.md'
configFile: '{output_folder}/devops-sync-config.yaml'
cliReference: '../data/azure-devops-cli.md'
syncScript: '../scripts/sync-devops.py'
---

# Step 4: Sync to Azure DevOps

## STEP GOAL:

Execute `az boards` CLI commands to create and update Epics, Stories, Tasks, and Iterations in the correct dependency order, with error resilience and result tracking.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`
- ⚙️ TOOL/SUBPROCESS FALLBACK: If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread

### Role Reinforcement:

- ✅ You are a DevOps Integration Engineer — executing CLI commands mechanically
- ✅ Report each operation outcome: created/updated/failed
- ✅ Continue on individual failures — do not halt the entire sync

### Step-Specific Rules:

- 🎯 Execute ONLY items classified as NEW or CHANGED in step 03
- 🚫 FORBIDDEN to skip parent creation before children (Epics before Stories, Stories before Tasks)
- 💬 Log every CLI command result for the final report
- ⚙️ Use process template from {configFile} to select correct work item type and field names per {cliReference}

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly — dependency order is critical
- 💾 Track all created/updated work item IDs for devops-sync.yaml
- 📖 Parse JSON output from every `az boards` command
- 🚫 Individual failures logged, not fatal

## CONTEXT BOUNDARIES:

- Available: Diff results from step 03, {configFile}, {cliReference}
- Focus: CLI execution only
- Limits: Only process NEW and CHANGED items
- Dependencies: Step 03 completed with user confirmation

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Load Config and Execute Sync Script

**Primary method — cross-platform Python script:**

```bash
python {syncScript} --diff "{output_folder}/_diff-results.json" --config "{configFile}" --output "{output_folder}/_sync-results.json"
```

The script:
1. Auto-detects `az` executable path (`shutil.which` — handles `az.cmd` on Windows)
2. Loads diff results and config (process template, area path, iteration root)
3. Syncs in correct dependency order: **Epics → Stories → Tasks → Iterations**
4. For each NEW item: creates via `az boards work-item create`, extracts ID from JSON response
5. For each NEW story/task: adds parent link via `az boards work-item relation add`
6. For each CHANGED item: updates via `az boards work-item update`
7. For NEW iterations: creates via `az boards iteration project create`, then assigns stories
8. Individual failures are logged and the sync continues (error resilience)
9. Writes complete results JSON with all work item IDs, hashes, and error details
10. Prints progress to stderr as it executes each operation

Monitor the script's stderr output for real-time progress updates. When complete, load `{output_folder}/_sync-results.json` for the results.

Report the summary from the script output:
- "Epics: {created} created, {updated} updated, {failed} failed."
- "Stories: {created} created, {updated} updated, {failed} failed."
- "Tasks: {created} created, {updated} updated, {failed} failed."
- "Iterations: {created} created, {assigned} stories assigned."

**Fallback (if Python unavailable) — manual CLI execution:**

Load {configFile} for connection settings and process template type. Load {cliReference} for CLI command patterns and field mappings. Execute `az boards` commands individually in dependency order per {cliReference}. The dependency order is critical:

1. **Epics first** — create/update all epics, record DevOps IDs
2. **Stories second** — create with parent link to epic, update changed stories
3. **Tasks third** — create with parent link to story, update task state
4. **Iterations last** — create iterations, assign stories

See {cliReference} for exact command syntax, field mappings per process template, and error handling patterns.

### 6. Present MENU OPTIONS

Display: "**Sync execution complete. Proceeding to write results...**"

#### Menu Handling Logic:

- After sync execution completes, immediately load, read entire file, then execute {nextStepFile}

#### EXECUTION RULES:

- This is an auto-proceed step — sync results are carried to step 05
- Proceed directly to next step after all operations complete

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- All NEW and CHANGED items processed in correct dependency order
- Parent-child links established via `az boards work-item relation add`
- Work item IDs captured from JSON output for every created item
- Individual failures logged without halting sync
- Correct work item type and field names used per process template
- Empty iterations created even without story assignments

### ❌ SYSTEM FAILURE:

- Creating Stories before their parent Epics
- Creating Tasks before their parent Stories
- Halting entire sync on individual item failure
- Using wrong work item type for process template
- Processing UNCHANGED items
- Skipping iteration creation when no stories assigned
- Writing a new batch script from scratch when {syncScript} is available

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
