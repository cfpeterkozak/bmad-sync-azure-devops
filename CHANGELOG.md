# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.4.1] - 2026-02-11

### Fixed
- Truncate work item titles to 255 chars (Azure DevOps `System.Title` limit) — fixes review follow-up task creation failures
- Truncate HTML description/acceptance-criteria fields to 3000 chars before CLI escaping — fixes Windows cmd.exe 8191-char command line limit for large story content

### Added
- `truncate_title()` helper with configurable max length and ellipsis
- `max_len` parameter on `wrap_html()` for CLI-safe field truncation
- Tests for `truncate_title()` and `wrap_html()` truncation behavior

## [0.4.0] - 2026-02-11

### Changed
- Replaced sprint-based iterations with epic-based iteration management
- `parse_sprint_yaml()` replaced by `parse_epic_statuses()` — parses `development_status:` block
- Epic content hash now includes epic status (triggers iteration creation on status change)
- `sync_iterations()` replaced by `sync_epic_iterations()` — creates sub-iterations per epic and moves epics, stories, and tasks into them
- Iteration slugs use kebab-case naming (e.g., `epic-1-foundation-infrastructure-platform-bootstrap`)
- `sync_tasks()` now returns an ID map for iteration movement

### Added
- `generate_iteration_slug()` helper for kebab-case iteration naming with 128-char truncation
- `taskIdMap` in sync output for task-to-DevOps-ID mapping
- Epic status slug reuse from sync state to prevent renames on title changes

## [0.3.0] - 2026-02-11

### Added
- `--iteration` flag on work item creation to place items in configured iteration root path
- `get_default_iteration()` helper to build iteration path from config
- `iterationRootPath` config support

## [0.2.0] - 2026-02-11

### Fixed
- Duplicate epic parsing when epics.md has both summary and detailed sections
- Windows `cmd.exe` shell escaping for HTML descriptions containing `<>` characters

### Added
- Epic deduplication by ID (keeps first occurrence)
- Per-argument double-quoting for Windows `cmd.exe` shell execution

## [0.1.0] - 2026-02-11

### Added
- Flat story file support (`{N-M-slug}.md` filename format)
- Review follow-up parsing from `### Review Follow-ups (AI)` sections
- Story status sync (`Status:` field maps to Azure DevOps work item state)
- Story status included in content hash for change detection
- 3-pass story file discovery (nested, flat, unknown directories)

## [0.0.1] - 2026-02-10

### Added
- Initial release
- Parse `epics.md` with auto-detected heading levels
- Parse story files for tasks and subtasks
- Content hash-based change detection (SHA-256, first 12 hex chars)
- Diff classification (NEW/CHANGED/UNCHANGED/ORPHANED)
- Batch sync to Azure DevOps via `az boards` CLI
- Cross-platform support (Windows `az.cmd` auto-detection)
- Process template auto-detection via REST API
- `devops-sync.yaml` mapping file for incremental sync
- Validate mode for drift auditing and bug discovery
- Sprint/iteration creation and story assignment

[Unreleased]: https://github.com/cfpeterkozak/bmad-sync-azure-devops/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/cfpeterkozak/bmad-sync-azure-devops/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/cfpeterkozak/bmad-sync-azure-devops/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/cfpeterkozak/bmad-sync-azure-devops/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/cfpeterkozak/bmad-sync-azure-devops/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/cfpeterkozak/bmad-sync-azure-devops/releases/tag/v0.0.1
