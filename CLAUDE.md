# CLAUDE.md

Project context for AI coding agents working on this repository.

## Project Overview

This is a BMAD Method workflow that syncs markdown planning artifacts to Azure DevOps work items. It consists of 4 Python scripts (stdlib-only, no external dependencies) and step-based workflow markdown files.

## Architecture

```
epics.md + story files + sprint-status.yaml
    → parse-artifacts.py (parse to JSON)
    → compute-hashes.py (SHA-256 diff classification)
    → sync-devops.py (batch az CLI execution)
    → devops-sync.yaml (state mapping file)
```

Scripts are designed to be run in sequence. Each reads the output of the previous step.

## Key Constraints

- **stdlib-only**: All Python scripts use only the standard library. Do not add `pip` dependencies.
- **Cross-platform**: Must work on Windows (cmd.exe, az.cmd), macOS, and Linux. Test shell escaping on Windows.
- **Python 3.6+**: Minimum version. Use f-strings but avoid walrus operator (3.8+) or match statements (3.10+).
- **No interactive commands**: Scripts are invoked by AI agents. Never use interactive prompts or `input()`.

## Code Style

- PEP 8 with 4-space indentation
- Type hints on function signatures
- Docstrings on all public functions
- Module-level docstring describing purpose and design constraints
- Regex patterns documented in `data/parsing-patterns.md`

## Testing

```bash
pytest tests/ -v
```

Tests cover pure functions only (parsing, hashing, normalization, slug generation). No Azure DevOps connection needed. Tests use `tmp_path` fixtures for file I/O.

## Important Files

| File | Purpose |
|------|---------|
| `scripts/parse-artifacts.py` | Parse epics.md, story files, epic statuses |
| `scripts/compute-hashes.py` | Content hashing, diff classification, iteration derivation |
| `scripts/sync-devops.py` | Batch Azure DevOps sync via az CLI |
| `scripts/write-sync-state.py` | Deterministic YAML state file writer (merges diff + sync results) |
| `scripts/detect-template.py` | Process template detection via REST API |
| `data/parsing-patterns.md` | Regex patterns and hash scope documentation |
| `workflow.md` | Entry point for AI agents running the workflow |

## Common Pitfalls

- **Windows shell escaping**: HTML descriptions contain `<>` which cmd.exe interprets as redirects. The `run_az()` function handles this by double-quoting every argument.
- **Heading level detection**: `epics.md` uses `##`, `###`, or `####` for epics depending on the project. The parser auto-detects.
- **Sync state YAML parser**: Hand-rolled (no PyYAML dependency). Expects exactly 2-space indent for IDs, 4-space for properties.
- **Epic iteration slugs**: Once created, slugs are reused from sync state to prevent renames if the epic title changes.
