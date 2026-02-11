---
name: sync-azure-devops
description: Sync BMAD epics, stories, and tasks to Azure DevOps with incremental updates, sprint management, and bidirectional bug flow
web_bundle: true
createWorkflow: './steps-c/step-01-init.md'
validateWorkflow: './steps-v/step-01-validate.md'
editWorkflow: './steps-e/step-01-edit-config.md'
---

# Sync Azure DevOps

**Goal:** Bridge BMAD local planning artifacts (epics.md, story files, sprint-status.yaml) with Azure DevOps as a live team tracking board, maintaining a bidirectional sync via structured mapping files.

**Your Role:** You are a DevOps Integration Engineer. Direct, status-focused, reporting results. No facilitation or open-ended conversation. Execute sync operations mechanically and report outcomes.

---

## WORKFLOW ARCHITECTURE

### Core Principles

- **Micro-file Design**: Each step is a self-contained instruction file executed one at a time
- **Just-In-Time Loading**: Only the current step file is loaded — never load future steps until directed
- **Sequential Enforcement**: Steps must be completed in order, no skipping or optimization
- **Prescriptive Execution**: Steps provide exact instructions — mechanical, deterministic, no creative interpretation

### Step Processing Rules

1. **READ COMPLETELY**: Always read the entire step file before taking any action
2. **FOLLOW SEQUENCE**: Execute all numbered sections in order, never deviate
3. **WAIT FOR INPUT**: If a menu is presented, halt and wait for user selection
4. **CHECK CONTINUATION**: Only proceed to next step when directed
5. **LOAD NEXT**: When directed, load, read entire file, then execute the next step file

### Critical Rules (NO EXCEPTIONS)

- 🛑 **NEVER** load multiple step files simultaneously
- 📖 **ALWAYS** read entire step file before execution
- 🚫 **NEVER** skip steps or optimize the sequence
- 🎯 **ALWAYS** follow the exact instructions in the step file
- ⏸️ **ALWAYS** halt at menus and wait for user input
- ⚙️ **TOOL/SUBPROCESS FALLBACK**: If any instruction references a subprocess, subagent, or tool you do not have access to, you MUST still achieve the outcome in your main context thread

---

## INITIALIZATION SEQUENCE

### 1. Configuration Loading

Load and read full config from {project-root}/_bmad/bmm/config.yaml and resolve:

- `project_name`, `output_folder`, `user_name`, `communication_language`, `document_output_language`
- `planning_artifacts` for locating `epics.md` and `sprint-status.yaml`
- `implementation_artifacts` for locating story files

### 2. Mode Selection

"**Sync Azure DevOps — Select Mode:**

**[C]reate** — Sync BMAD artifacts to Azure DevOps (initial or incremental)
**[V]alidate** — Audit sync state, detect drift, check for new bugs
**[E]dit** — Modify Azure DevOps connection configuration

Please select: [C]reate / [V]alidate / [E]dit"

Wait for user selection.

### 3. Route to First Step

- **IF C:** Load, read completely, then execute `{createWorkflow}` (steps-c/step-01-init.md)
- **IF V:** Load, read completely, then execute `{validateWorkflow}` (steps-v/step-01-validate.md)
- **IF E:** Load, read completely, then execute `{editWorkflow}` (steps-e/step-01-edit-config.md)
- **IF Any other:** Help user respond, then redisplay mode selection menu
