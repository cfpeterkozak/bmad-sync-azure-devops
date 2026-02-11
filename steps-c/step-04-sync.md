---
name: 'step-04-sync'
description: 'Execute az boards CLI commands to create and update work items in dependency order'

nextStepFile: './step-05-complete.md'
configFile: '{output_folder}/devops-sync-config.yaml'
cliReference: '../data/azure-devops-cli.md'
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

### 1. Load Config and CLI Reference

Load {configFile} for connection settings and process template type.

Load {cliReference} for CLI command patterns, field mappings per process template, and error handling guidance.

Determine the correct `--type` value for stories based on process template:
- Agile: `"User Story"`
- Scrum: `"Product Backlog Item"`
- CMMI: `"Requirement"`
- Basic: `"Issue"`

Initialize results tracker: `{ created: [], updated: [], failed: [], skipped: [] }`

### 2. Sync Epics (Must Complete Before Stories)

For each Epic classified as **NEW**:

```bash
az boards work-item create \
  --type Epic \
  --title "{epicTitle}" \
  --description "{epicDescription wrapped in <div>}" \
  --area "{areaPath}" \
  --output json
```

Parse JSON response: extract `id` field. Record work item ID.

Report each: "Created Epic #{id}: {title}"

For each Epic classified as **CHANGED**:

```bash
az boards work-item update \
  --id {existingDevopsId} \
  --title "{updatedTitle}" \
  --description "{updatedDescription}" \
  --output json
```

Report each: "Updated Epic #{id}: {title}"

**On failure (non-zero exit):** Log error message, add to failed list, continue with next item.

Report summary: "Epics: {created} created, {updated} updated, {failed} failed."

### 3. Sync Stories (Must Complete Before Tasks)

For each Story classified as **NEW**:

**Create the work item:**
```bash
az boards work-item create \
  --type "{storyType per template}" \
  --title "{storyTitle}" \
  --description "{userStoryText wrapped in <div>}" \
  --area "{areaPath}" \
  --fields "{AcceptanceCriteriaField per template}={AC wrapped in <div>}" \
  --output json
```

Parse JSON response: extract `id`. Record work item ID.

**Add parent link to Epic:**
```bash
az boards work-item relation add \
  --id {newStoryId} \
  --relation-type parent \
  --target-id {epicDevopsId} \
  --output json
```

Report each: "Created Story #{id}: {title} (parent: Epic #{epicId})"

For each Story classified as **CHANGED**:

```bash
az boards work-item update \
  --id {existingDevopsId} \
  --fields "{AcceptanceCriteriaField}={updatedAC}" \
  --output json
```

Report each: "Updated Story #{id}: {title}"

**On failure:** Log, add to failed list, continue.

Report summary: "Stories: {created} created, {updated} updated, {failed} failed."

### 4. Sync Tasks (If Task Data Exists)

For each Task classified as **NEW**:

```bash
az boards work-item create \
  --type Task \
  --title "{taskDescription}" \
  --area "{areaPath}" \
  --output json
```

Parse response, extract `id`.

**Add parent link to Story:**
```bash
az boards work-item relation add \
  --id {newTaskId} \
  --relation-type parent \
  --target-id {storyDevopsId} \
  --output json
```

**If task is complete (checkbox checked), update state:**
```bash
az boards work-item update --id {newTaskId} --state "{completeState per template}" --output json
```

Report each: "Created Task #{id}: {description} (parent: Story #{storyId})"

For each Task classified as **CHANGED**:

```bash
az boards work-item update \
  --id {existingDevopsId} \
  --state "{state based on checkbox}" \
  --output json
```

**On failure:** Log, add to failed list, continue.

Report summary: "Tasks: {created} created, {updated} updated, {failed} failed."

### 5. Sync Iterations (If Sprint Data Exists)

For each Iteration classified as **NEW**:

```bash
az boards iteration project create \
  --name "{iterationName}" \
  --path "{iterationRootPath}" \
  --start-date "{startDate}" \
  --finish-date "{endDate}" \
  --output json
```

Report: "Created Iteration: {name}"

**Create empty iterations even if no stories are assigned yet** — the board structure should be ready.

For each Story assigned to this iteration:

```bash
az boards work-item update \
  --id {storyDevopsId} \
  --iteration "{iterationRootPath}\\{iterationName}" \
  --output json
```

Report: "Assigned Story #{id} to {iterationName}"

**On failure:** Log, continue.

Report summary: "Iterations: {created} created. {assigned} stories assigned."

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

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
