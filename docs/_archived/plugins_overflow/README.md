# Archived: Orphan SK Plugins

**Archived:** 2026-04-09 (Epic #317, PR #321)
**Original location:** `plugins/` (root level)

## Contents

- `GitAudit/CommitAnalyzer/skprompt.txt` — Semantic Kernel prompt for git commit analysis
- `StrategicNarrative/ChapterGenerator/skprompt.txt` — Semantic Kernel prompt for narrative chapter generation

## Reason for Archival

These SK prompt directories were residuals from an earlier migration. No code in the codebase imports or references them:
- No `import_plugin` calls for `GitAudit` or `StrategicNarrative`
- No Python imports from `plugins.GitAudit` or `plugins.StrategicNarrative`
- The `argumentation_analysis/plugins/` directory has the active plugins

## If Needed

If these prompts are needed again, they should be placed under `argumentation_analysis/plugins/` following the established plugin architecture.
