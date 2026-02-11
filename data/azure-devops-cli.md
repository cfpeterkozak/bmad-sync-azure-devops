# Azure DevOps CLI Reference

**Purpose:** `az devops` CLI commands, argument patterns, and field mappings for the sync-azure-devops workflow. Replaces raw REST API calls with stable CLI commands.

---

## Prerequisites

### Installation Check

```bash
az --version          # Azure CLI must be installed
az extension show --name azure-devops   # devops extension must be present
```

**If missing:**
```bash
# Install Azure CLI: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli
az extension add --name azure-devops
```

### Authentication

The CLI reads PAT from the `AZURE_DEVOPS_EXT_PAT` environment variable automatically — no manual base64 encoding needed.

```bash
# Set PAT (do NOT store in files)
# Linux/Mac:
export AZURE_DEVOPS_EXT_PAT=your-token

# PowerShell:
$env:AZURE_DEVOPS_EXT_PAT = "your-token"
```

### Configure Defaults

After first-run config, set CLI defaults so every command inherits org and project:

```bash
az devops configure --defaults organization={organizationUrl} project={projectName}
```

---

## Commands

### 1. Validate Connection

```bash
az devops project show --project {projectName} --organization {organizationUrl} --output json
```

Returns project details if accessible. Non-zero exit code on auth or not-found errors.

### 2. Detect Process Template (Work Item Types)

```bash
az boards work-item type list --project {projectName} --organization {organizationUrl} --output json
```

**Template Detection Logic:**
- Response contains `"name": "User Story"` → **Agile**
- Response contains `"name": "Product Backlog Item"` → **Scrum**
- Response contains `"name": "Requirement"` → **CMMI**
- Response contains `"name": "Issue"` but no User Story/PBI/Requirement → **Basic**

### 3. Create Work Item

```bash
az boards work-item create \
  --type "{workItemType}" \
  --title "{title}" \
  --description "{htmlDescription}" \
  --area "{areaPath}" \
  --iteration "{iterationPath}" \
  --fields "{AcceptanceCriteriaField}={htmlAC}" \
  --output json
```

**Returns:** JSON with `id` field containing the new work item ID.

### 4. Update Work Item

```bash
az boards work-item update \
  --id {workItemId} \
  --title "{newTitle}" \
  --description "{newHtmlDescription}" \
  --fields "{fieldPath}={value}" \
  --output json
```

Only include fields that changed.

### 5. Add Parent-Child Link

```bash
az boards work-item relation add \
  --id {childId} \
  --relation-type parent \
  --target-id {parentId} \
  --output json
```

### 6. Create Iteration

```bash
az boards iteration project create \
  --name "{iterationName}" \
  --path "{iterationRootPath}" \
  --start-date "{yyyy-MM-dd}" \
  --finish-date "{yyyy-MM-dd}" \
  --output json
```

### 7. Assign Story to Iteration

```bash
az boards work-item update \
  --id {storyId} \
  --iteration "{iterationRootPath}\\{iterationName}" \
  --output json
```

### 8. Query Bugs (WIQL)

```bash
az boards query \
  --wiql "SELECT [System.Id], [System.Title], [System.State], [System.AssignedTo], [System.CreatedDate] FROM workitems WHERE [System.WorkItemType] = 'Bug' AND [System.AreaPath] UNDER '{areaPath}' AND [System.State] <> 'Closed' ORDER BY [System.CreatedDate] DESC" \
  --output json
```

Returns list of matching work item IDs. Fetch details with:

```bash
az boards work-item show --id {workItemId} --output json
```

### 9. Get Work Item (for Validation)

```bash
az boards work-item show --id {workItemId} --fields "System.Title,System.State" --output json
```

### 10. Batch Get Work Items

```bash
# Query multiple IDs (loop or use WIQL with IN clause)
az boards query \
  --wiql "SELECT [System.Id], [System.Title], [System.State] FROM workitems WHERE [System.Id] IN ({id1},{id2},{id3})" \
  --output json
```

---

## Field Mappings by Process Template

### Story Work Item Type

| Template | `--type` Value |
|----------|---------------|
| **Agile** | `"User Story"` |
| **Scrum** | `"Product Backlog Item"` |
| **CMMI** | `"Requirement"` |
| **Basic** | `"Issue"` |

### Acceptance Criteria Field

| Template | `--fields` Key |
|----------|---------------|
| **Agile** | `Microsoft.VSTS.Common.AcceptanceCriteria` |
| **Scrum** | `Microsoft.VSTS.Common.AcceptanceCriteria` |
| **CMMI** | `Microsoft.VSTS.Common.AcceptanceCriteria` |
| **Basic** | Use `--description` (no dedicated AC field) |

### State Mapping

| BMAD Status | Agile | Scrum | CMMI | Basic |
|-------------|-------|-------|------|-------|
| Not Started | New | New | Proposed | To Do |
| In Progress | Active | Committed | Active | Doing |
| Complete | Closed | Done | Resolved | Done |

---

## Error Handling

The `az` CLI returns non-zero exit codes on failure with error messages to stderr.

| Scenario | CLI Behavior | Workflow Action |
|----------|-------------|-----------------|
| Auth failure | Exit code 1, "unauthorized" | HALT all operations |
| Project not found | Exit code 1, "not found" | HALT with guidance |
| Work item not found | Exit code 1, "does not exist" | Log, skip, continue |
| Invalid field | Exit code 1, field error message | Log, skip, continue |
| Rate limited | Exit code 1, "too many requests" | Wait 60s, retry once |
| Network error | Exit code 1, connection error | Retry once, then skip |

**Pattern for error handling in steps:**
```bash
result=$(az boards work-item create --type Epic --title "..." --output json 2>&1)
if [ $? -ne 0 ]; then
  echo "FAILED: $result"
  # Log and continue
else
  id=$(echo "$result" | jq -r '.id')
  echo "Created: #$id"
fi
```

---

## Output Parsing

All commands use `--output json`. Extract fields with `jq`:

```bash
# Get work item ID from create/update response
echo "$result" | jq -r '.id'

# Get state
echo "$result" | jq -r '.fields["System.State"]'

# Get title
echo "$result" | jq -r '.fields["System.Title"]'
```

**PowerShell alternative:**
```powershell
$result = az boards work-item create --type Epic --title "..." --output json | ConvertFrom-Json
$result.id
```
