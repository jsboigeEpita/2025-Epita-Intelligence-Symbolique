# Archived: Orphan SK Plugins

**Archived:** 2026-04-09 (Epic #317, PR #321) — root-level `plugins/`;
2026-09-14 (#2145) — `argumentation_analysis/plugins/` SK prompt directories.

## Contents

- `GitAudit/CommitAnalyzer/skprompt.txt` — Semantic Kernel prompt for git commit analysis
- `StrategicNarrative/ChapterGenerator/skprompt.txt` — Semantic Kernel prompt for narrative chapter generation
- `ExplorationPlugin/Explore/` (config.json + skprompt.txt) — fallacy detection focused on one taxonomy category (2026-09-14, #2145)
- `GuidingPlugin/GuidingPlugin/` (config.json + skprompt.txt) — identifies the most relevant fallacy categories in a text (2026-09-14, #2145)
- `SynthesisPlugin/Synthesize/` (config.json + skprompt.txt) — merges parallel exploration findings into one summary (2026-09-14, #2145)

## Reason for Archival

These SK prompt directories were residuals from an earlier migration. No code in the codebase imports or references them:
- No `import_plugin` calls for `GitAudit` or `StrategicNarrative`
- No Python imports from `plugins.GitAudit` or `plugins.StrategicNarrative`
- The `argumentation_analysis/plugins/` directory has the active plugins

The three directories archived by #2145 are the Guide-Explore-Synthesize prompts of the
parallel fallacy workflow plan (`docs/architecture/DESIGN_PARALLEL_WORKFLOW.md`). Measured
before the move: no `.py` loads them (no Semantic Kernel directory-loading API targets
them), their only occurrences were documentary, and their names collided with live classes
(`exploration_plugin.py`'s `ExplorationPlugin`, `narrative_synthesis_plugin.py`'s
`NarrativeSynthesisPlugin`). Origin: `5f0422b81` (feat — the parallel workflow plan),
last touched by `5839c96df` (chore — prompt hardening). The workflow it planned was
never wired in code; the live taxonomy-guided parallel fallacy analysis is
`argumentation_analysis/plugins/fallacy_workflow_plugin.py` (asyncio.gather branch
exploration), which never reads these prompt directories.

## If Needed

If these prompts are needed again, they should be placed under `argumentation_analysis/plugins/` following the established plugin architecture.
