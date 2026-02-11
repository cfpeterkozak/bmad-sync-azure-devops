---
name: 'step-01-init'
description: 'Check prerequisites (az CLI, PAT), load or create config, validate connection'

nextStepFile: './step-02-parse.md'
configFile: '{output_folder}/devops-sync-config.yaml'
cliReference: '../data/azure-devops-cli.md'
---

# Step 1: Initialize Azure DevOps Connection

## STEP GOAL:

Verify prerequisites (Azure CLI + devops extension + PAT), load or create the connection configuration, configure CLI defaults, detect the process template, and validate the connection.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`

### Role Reinforcement:

- ✅ You are a DevOps Integration Engineer — direct, status-focused, reporting results
- ✅ No facilitation or open-ended conversation — execute mechanically and report outcomes
- ✅ Tone example: "Checking az CLI... found v2.67. Checking devops extension... found. Validating connection..."

### Step-Specific Rules:

- 🎯 Focus ONLY on connection setup — do not parse epics or sync anything yet
- 🚫 FORBIDDEN to store the PAT value in any file — it must come from environment variable only
- 🚫 FORBIDDEN to proceed if any prerequisite check fails
- ⚙️ TOOL/SUBPROCESS FALLBACK: If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly
- 💾 Write config to {configFile} if created or updated
- 📖 Report status at each checkpoint
- 🚫 Fail fast on missing prerequisites or failed connection

## CONTEXT BOUNDARIES:

- Available: BMM config (project_name, output_folder), environment variables, {cliReference}
- Focus: Connection setup only
- Limits: Do not parse any BMAD artifacts yet
- Dependencies: None — this is the first step

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Check Azure CLI Prerequisites

Run prerequisite checks in order. HALT on first failure.

**Check Azure CLI:**
```bash
az --version
```
- **If found:** Report: "Azure CLI detected."
- **If not found:** HALT. "Azure CLI not installed. Install from: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli"

**Check devops extension:**
```bash
az extension show --name azure-devops
```
- **If found:** Report: "azure-devops extension detected."
- **If not found:** Ask user: "azure-devops extension not found. Install now? [Y/N]"
  - If Y: Run `az extension add --name azure-devops`
  - If N: HALT.

**Check AZURE_DEVOPS_EXT_PAT:**

Read the `AZURE_DEVOPS_EXT_PAT` environment variable.
- **If set:** Report: "AZURE_DEVOPS_EXT_PAT detected."
- **If not set:** HALT. Report: "AZURE_DEVOPS_EXT_PAT not set. Export it and retry:"
  - Linux/Mac: `export AZURE_DEVOPS_EXT_PAT=your-token`
  - PowerShell: `$env:AZURE_DEVOPS_EXT_PAT = "your-token"`

### 2. Load or Create Connection Config

Check if {configFile} exists.

**If exists:** Load and display current settings:

```
Organization URL:    [value]
Project Name:        [value]
Area Path:           [value]
Iteration Root Path: [value]
Process Template:    [value]
```

Ask user: "Config loaded. Continue with these settings? [Y]es / [E]dit"
- If E: Proceed to interactive prompts below
- If Y: Skip to section 3

**If not exists:** Report: "No config found. Starting first-run setup."

Prompt interactively for each field (one at a time, with examples):

1. **Organization URL** — e.g., `https://dev.azure.com/myorg`
2. **Project Name** — e.g., `CaseFusion` (must be an existing Azure DevOps project)
3. **Area Path** — e.g., `CaseFusion\Analyze` (backslash-separated, or blank for project root)
4. **Iteration Root Path** — e.g., `CaseFusion\Sprints` (parent path for auto-created iterations)

### 3. Configure CLI Defaults and Validate Connection

Set Azure CLI defaults so all subsequent commands inherit org and project:

```bash
az devops configure --defaults organization={organizationUrl} project={projectName}
```

Validate connection by retrieving project info:

```bash
az devops project show --project {projectName} --output json
```

- **If success (exit code 0):** Report: "Connection validated. Project '{projectName}' accessible."
- **If failure:** Report error message from CLI. HALT.

### 4. Detect Process Template

Query available work item types:

```bash
az boards work-item type list --output json
```

Detect process template from the response (see {cliReference} for detection logic):
- Contains `"User Story"` → **Agile**
- Contains `"Product Backlog Item"` → **Scrum**
- Contains `"Requirement"` → **CMMI**
- Contains `"Issue"` (no User Story/PBI/Requirement) → **Basic**

Report: "Process template detected: {template}"

### 5. Save Config

Write {configFile}:

```yaml
# Azure DevOps Sync Configuration
# Generated: {date}
organizationUrl: "{value}"
projectName: "{value}"
areaPath: "{value}"
iterationRootPath: "{value}"
processTemplate: "{detected-value}"
```

Report: "Config saved to {configFile}"

### 6. Present MENU OPTIONS

Display: "**Initialization complete. Proceeding to artifact parsing...**"

#### Menu Handling Logic:

- After config is saved and connection validated, immediately load, read entire file, then execute {nextStepFile}

#### EXECUTION RULES:

- This is an auto-proceed init step with no user choices at this point
- Proceed directly to next step after successful initialization

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Azure CLI and devops extension verified as installed
- AZURE_DEVOPS_EXT_PAT verified as set
- CLI defaults configured for org and project
- Connection validated via `az devops project show`
- Process template detected from work item types
- Config file saved
- Auto-proceeded to step 02

### ❌ SYSTEM FAILURE:

- Proceeding without Azure CLI installed
- Storing PAT value in config file
- Proceeding after connection failure
- Skipping process template detection
- Not setting CLI defaults with `az devops configure`

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
