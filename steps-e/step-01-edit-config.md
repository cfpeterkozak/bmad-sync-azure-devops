---
name: 'step-01-edit-config'
description: 'Load, display, modify, and validate Azure DevOps connection configuration'

configFile: '{output_folder}/devops-sync-config.yaml'
detectTemplateScript: '../scripts/detect-template.py'
---

# Edit: Modify Connection Configuration

## STEP GOAL:

Load the existing Azure DevOps connection configuration, display current settings, allow the user to modify fields, validate the updated connection via `az devops` CLI, and save.

## MANDATORY EXECUTION RULES (READ FIRST):

### Universal Rules:

- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 📋 YOU ARE A FACILITATOR, not a content generator
- ✅ YOU MUST ALWAYS SPEAK OUTPUT In your Agent communication style with the config `{communication_language}`
- ⚙️ TOOL/SUBPROCESS FALLBACK: If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread

### Role Reinforcement:

- ✅ You are a DevOps Integration Engineer — configuration management
- ✅ Guide through field changes efficiently
- ✅ Always validate before saving

### Step-Specific Rules:

- 🎯 Focus on config editing only — no sync operations
- 🚫 FORBIDDEN to store PAT in the config file
- 🚫 FORBIDDEN to modify devops-sync.yaml or any BMAD files
- 💬 Validate connection after any URL or project changes

## EXECUTION PROTOCOLS:

- 🎯 Follow the MANDATORY SEQUENCE exactly
- 💾 Save updated config to {configFile}
- 📖 Re-validate connection if org URL or project changed
- 🚫 Config editing only — no sync or parse operations

## CONTEXT BOUNDARIES:

- Available: {configFile} (must exist)
- Focus: Config modification and validation
- Limits: Config changes only
- Dependencies: Prior Create mode must have run (config file must exist)

## MANDATORY SEQUENCE

**CRITICAL:** Follow this sequence exactly. Do not skip, reorder, or improvise unless user explicitly requests a change.

### 1. Load Existing Config

Load {configFile} — if missing: "Config not found. Run Create mode first to initialize." — HALT.

### 2. Display Current Settings

```
CURRENT CONFIGURATION
=====================
[1] Organization URL:    {organizationUrl}
[2] Project Name:        {projectName}
[3] Area Path:           {areaPath}
[4] Iteration Root Path: {iterationRootPath}
[5] Process Template:    {processTemplate} (auto-detected)
```

### 3. Prompt for Changes

Display: "Enter the number(s) of fields to change (comma-separated), or 'done' to save unchanged."

For each selected field:
- Display current value
- Prompt for new value
- If field 1 (Organization URL) or field 2 (Project Name) changed: flag for re-validation

**Field 5 (Process Template):** Cannot be edited directly — it is auto-detected. If org URL or project changes, it will be re-detected.

### 4. Re-Validate Connection (If Needed)

If Organization URL or Project Name changed:

Check `AZURE_DEVOPS_EXT_PAT` environment variable — if missing, HALT with message.

Update CLI defaults and validate:

```bash
az devops configure --defaults organization={newOrgUrl} project={newProject}
az devops project show --project {newProject} --output json
```

- **If success:** Report: "Connection validated."

Re-detect process template:

**Primary method — cross-platform Python script:**
```bash
python {detectTemplateScript} --org {newOrgUrl} --project {newProject}
```

**Manual REST API fallback (if Python not available):**
```bash
curl -s -u ":{AZURE_DEVOPS_EXT_PAT}" "{newOrgUrl}/{newProject}/_apis/wit/workitemtypes?api-version=7.0"
```

Update process template from response. Report: "Process template: {template}"

- **If failure:** Report error. Ask: "Keep previous values? [Y]es / [R]etry with different values"
  - If Y: Revert URL/project changes
  - If R: Return to field prompts

### 5. Save Updated Config

Write updated settings to {configFile}.

Report: "Config updated and saved to {configFile}"

Display current settings one more time for confirmation.

### 6. Workflow Complete

Display: "**Configuration updated.** Run [C]reate mode to sync with new settings, or [V]alidate to check current state."

No next step — workflow ends.

## 🚨 SYSTEM SUCCESS/FAILURE METRICS

### ✅ SUCCESS:

- Existing config loaded and displayed
- User-selected fields updated
- Connection re-validated via `az devops project show` if URL or project changed
- Process template re-detected if needed
- Updated config saved to {configFile}

### ❌ SYSTEM FAILURE:

- Storing PAT value in config file
- Modifying devops-sync.yaml or BMAD files
- Saving config without re-validating changed connection settings
- Allowing direct edit of auto-detected process template field

**Master Rule:** Skipping steps, optimizing sequences, or not following exact instructions is FORBIDDEN and constitutes SYSTEM FAILURE.
