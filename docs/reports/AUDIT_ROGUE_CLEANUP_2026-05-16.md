# Rogue Cleanup Audit -- 2026-05-16

**Scope**: 2025-06-01 to 2026-05-16
**Author**: Claude Code (automated audit)
**Issue**: #581 Phase 1
**Rule violated**: Consolider != Archiver (CLAUDE.md, global instructions)

---

## Executive Summary

| Metric | Count |
|--------|-------|
| Cleanup commits investigated | 27 |
| Total files deleted (not moved) | ~420 |
| Total LoC deleted | ~557,000+ |
| **HIGH priority files** | **14** |
| **MEDIUM priority files** | **22** |
| LOW (justified deletion) | ~384 |

### Must-Recover HIGH Items

1. argumentation_analysis/docs/DESIGN_INFERENCE_REPAIR.md (140 LoC) -- FOL type-inference repair design, still relevant to Tweety constant pre-declaration issue
2. argumentation_analysis/docs/architecture_fallacy_workflows.md (118 LoC) -- Fallacy workflow plugin architecture with mermaid diagrams
3. docs/maintenance/DESIGN_PARALLEL_WORKFLOW.md (209 LoC) -- Parallel exploration workflow design, foundational architecture doc
4. docs/refactoring/informal_fallacy_system/04_operational_plan.md (1323 LoC) -- Complete operational plan for fallacy system consolidation
5. docs/refactoring/informal_fallacy_system/03_informal_fallacy_consolidation_plan.md (1158 LoC) -- Consolidation plan with architecture diagrams
6. docs/refactoring/06_final_architecture_plan.md (307 LoC) -- Final architecture plan for 3-layer refactoring
7. docs/refactoring/07_implementation_roadmap.md (731 LoC) -- Implementation roadmap for script migration
8. docs/refactoring/04_scripts_maintenance_consolidation_plan.md (761 LoC) -- Scripts consolidation plan
9. docs/refactoring/02_system_legacy_and_evolution_analysis.md (519 LoC) -- Legacy system analysis
10. docs/refactoring/01_informal_fallacy_system_analysis.md (216 LoC) -- Fallacy system analysis
11. docs/maintenance/METHODOLOGIE_SDDD_PHASE_D1.md (475 LoC) -- SDDD methodology documentation
12. docs/maintenance/LLM_SERVICE_API_COMPATIBILITY_FIX.md (86 LoC) -- SK API compatibility reference
13. docs/maintenance/PLAN_DETAILLE_PHASE2_AUTHENTIC_LLM.md (256 LoC) -- LLM validation phase plan
14. docs/reports/VALIDATION_REPORT_PARALLEL_WORKFLOW.md (89 LoC) -- Validation of parallel workflow feature

---

## Detailed Findings Per Cleanup Wave

### Wave 1: 48f514c5 / PR #447 -- chore(cleanup): remove dead directories (2026-05-05)

**Deletions**: 34 files, 6339 LoC
**PR**: #442 / #447
**Rationale claimed**: 8 unused subdirectories, zero external imports

| File | LoC | Class | Excerpt / Rationale |
|------|-----|-------|---------------------|
| docs/DESIGN_INFERENCE_REPAIR.md | 140 | **HIGH** | FOL type-inference repair design with sort-hierarchy algorithm. Tweety constant pre-declaration (#304) is the descendant; this doc contains the original algorithm. |
| docs/architecture_fallacy_workflows.md | 118 | **HIGH** | FallacyWorkflowPlugin + FallacyIdentificationPlugin split architecture with mermaid diagrams. No equivalent exists elsewhere. |
| examples/orchestration/run_orchestration_pipeline_demo.py | 604 | MEDIUM | Comprehensive orchestration demo with all modes. Only demo of full pipeline. |
| examples/orchestration/run_hierarchical_orchestration.py | 579 | MEDIUM | Hierarchical orchestration demo. Documents 3-tier architecture usage. |
| examples/orchestration/hierarchical_architecture_example.py | 287 | MEDIUM | Example of hierarchical tactical/operational architecture. |
| examples/rhetorical_tools/rhetorical_analysis_example.py | 340 | MEDIUM | Rhetorical analysis usage example. |
| notebooks/main_orchestrator.ipynb | 481 | MEDIUM | Interactive Jupyter notebook for orchestration. Unique educational resource. |
| tests/test_jtms_complete.py | 629 | MEDIUM | Complete JTMS test suite (services, sessions, plugin SK, API REST). |
| demos/jtms/run_demo.py | 701 | MEDIUM | JTMS demo with SK integration. |
| examples/archived/communication_examples/exemple_extension_systeme.py | 572 | LOW | Communication extension example (archived). |
| examples/agent_integration/simple_agent_example.py | 40 | LOW | Trivial agent example. |
| 23 other files (READMEs, __init__.py, small examples) | -- | LOW | Boilerplate or trivially reproducible. |

### Wave 2: a62ef234 -- chore(#130): TIER 2 continued (2026-03-20)

**Deletions**: 60 files, 7230 LoC
**Rationale claimed**: historical plans, reports, roadmaps from 2025, all work completed

| File | LoC | Class | Excerpt / Rationale |
|------|-----|-------|---------------------|
| maintenance/DESIGN_PARALLEL_WORKFLOW.md | 209 | **HIGH** | Foundational parallel workflow design with mermaid architecture diagrams. No other doc covers this. |
| maintenance/METHODOLOGIE_SDDD_PHASE_D1.md | 475 | **HIGH** | SDDD methodology codification. Pattern still in active use per CLAUDE.md. |
| maintenance/PLAN_DETAILLE_PHASE2_AUTHENTIC_LLM.md | 256 | **HIGH** | LLM mock elimination plan. Still relevant -- mock elimination is ongoing. |
| maintenance/LLM_SERVICE_API_COMPATIBILITY_FIX.md | 86 | **HIGH** | SK API compatibility fix. Documents the SK 0.9.x to 1.x migration pattern. |
| maintenance/refactoring_plan.md | 224 | MEDIUM | Refactoring plan for fallacy tools with architecture diagrams. |
| maintenance/PLAN_MISE_A_JOUR_TESTS_FONCTIONNELS.md | 510 | MEDIUM | Playwright functional test plan for web app. Web app still in use. |
| maintenance/PLAN.md | 69 | MEDIUM | General maintenance plan. |
| maintenance/PROJECT_STRUCTURE_POST_CLEANUP.md | 295 | MEDIUM | Post-cleanup project structure reference. |
| maintenance/rapport_mission_ADR_sophismes.md | 94 | MEDIUM | ADR for fallacy detection architecture decisions. |
| maintenance/mcp_chronology.md | 81 | MEDIUM | MCP server chronology -- historical reference. |
| 50 other files (one-shot validation reports, test results) | -- | LOW | Session-specific verification reports, superseded. |

### Wave 3: 8a10a9c1 -- chore(#130): TIER 0+1 cleanup (2026-03-20)

**Deletions**: 161 files, 535,874 LoC
**Rationale claimed**: 160 dead files, ~536K lines removed. All content verified as dead/obsolete.

| File | LoC | Class | Excerpt / Rationale |
|------|-----|-------|---------------------|
| docs/DOC_CONCEPTION_SHERLOCK_WATSON.md | 12 | LOW | Already marked Document Obsolete with redirect. Justified deletion. |
| docs/archives/obsolete_2025/AGENT_FAMILY_DESIGN.md | 60 | **HIGH** | Design of 3 agent archetypes (Methodical Auditor, Parallel Explorer, Research Assistant). Although archetypes were removed (#216), the design rationale and strategy analysis is unique. |
| docs/archives/obsolete_2025/ANALYSE_MIGRATION_DUPLICATES.md | 278 | MEDIUM | Migration duplicates analysis with methodology. |
| docs/archives/obsolete_2025/CORRECTIFS_SEMANTIC_KERNEL_AGENTS_RAPPORT.md | 131 | MEDIUM | SK agents compatibility fix report. Reference for SK version issues. |
| docs/archives/obsolete_2025/FINALISATION_CONSOLIDATION_20250610.md | 105 | MEDIUM | Final consolidation session report. |
| 155 other files (.temp/, commit_analysis raw dumps, migration output, plugin overflow) | -- | LOW | Large raw dumps (268K LoC commit analysis), truly obsolete code, migration scripts. |

### Wave 4: c7ba0e3a -- chore(#130): TIER 2 -- consolidate docs/ (2026-03-20)

**Deletions**: 55 files, 10,220 LoC
**Rationale claimed**: student projects integrated, refactoring complete

| File | LoC | Class | Excerpt / Rationale |
|------|-----|-------|---------------------|
| refactoring/informal_fallacy_system/04_operational_plan.md | 1323 | **HIGH** | Complete operational plan for fallacy system consolidation with phased approach. No equivalent exists. |
| refactoring/informal_fallacy_system/03_informal_fallacy_consolidation_plan.md | 1158 | **HIGH** | Vision and principles for unified fallacy system with architecture diagrams. |
| refactoring/informal_fallacy_system/01_informal_fallacy_system_analysis.md | 216 | **HIGH** | System analysis of existing fallacy detection components. |
| refactoring/informal_fallacy_system/02_system_legacy_and_evolution_analysis.md | 519 | **HIGH** | Legacy system evolution analysis -- historical reference for architecture decisions. |
| refactoring/06_final_architecture_plan.md | 307 | **HIGH** | 3-layer architecture plan (argumentation_analysis / project_core / scripts). |
| refactoring/07_implementation_roadmap.md | 731 | **HIGH** | Implementation roadmap with iterative approach principles. |
| refactoring/04_scripts_maintenance_consolidation_plan.md | 761 | **HIGH** | Scripts consolidation plan with batch analysis methodology. |
| integration/plans/plan_1.4.1_jtms.md | 96 | MEDIUM | JTMS student integration analysis. Pedagogical reference. |
| integration/plans/plan_2.3.2_sophismes_camembert.md | 200 | MEDIUM | Sophism detection student integration analysis. |
| integration/plans/plan_2.3.3_contre_argument.md | 228 | MEDIUM | Counter-argument agent student integration analysis. |
| 8 other integration plans | 100-276 | MEDIUM | Student project integration analyses -- pedagogical value. |
| 10 refactoring reports (informal_fallacy_system/reports/) | 41-118 | MEDIUM | Session reports documenting decisions and incidents. |
| NAVIGATION.md, STRUCTURE.md, index.md | 843 | LOW | Replaced by docs/README.md. Justified. |

### Wave 5: d8338bc6 / PR #338 -- archive 86 pre-Nov-2025 reports (2026-05-01)

**Deletions**: 15 files deleted from docs/reports/, 86 files moved to archives
**Rationale claimed**: reduce clutter

| File | LoC | Class | Excerpt / Rationale |
|------|-----|-------|---------------------|
| reports/VALIDATION_REPORT_PARALLEL_WORKFLOW.md | 89 | **HIGH** | Validation report for parallel workflow feature. Corroborates DESIGN_PARALLEL_WORKFLOW.md. |
| reports/mission_report_20250727_final_grounding.md | 77 | MEDIUM | Grounding mission report with git workflow documentation. |
| reports/mission_report_ep2_web_applications.md | 123 | MEDIUM | Web applications mission report. |
| reports/mission_report_service_bus.md | 65 | MEDIUM | Service bus mission report. |
| reports/plugin_loader_mission_report.md | 48 | MEDIUM | Plugin loader mission report. |
| 10 other reports moved to archive (not deleted) | -- | LOW | Archived, recoverable from docs/archives/reports_pre_2025_11/. |

### Wave 6: e016e59b / PR #449 -- archive stale documentation (2026-05-05)

**Deletions**: 202 files moved to docs/_archived/ (not deleted from git)
**Rationale claimed**: stale since June/August 2025

| File | LoC | Class | Excerpt / Rationale |
|------|-----|-------|---------------------|
| sherlock_watson/guide_unifie_sherlock_watson.md | ~500 | MEDIUM | Comprehensive Sherlock/Watson guide. Moved to _archived, not deleted. |
| sherlock_watson/ARCHITECTURE_MULTI_AGENTS_TECHNIQUE.md | -- | MEDIUM | Multi-agent architecture doc. |
| investigations/DESIGN_DOC.md | ~200 | MEDIUM | FOL agent robust design from 18 code snapshots analysis. |
| investigations/investigation_report_sophism_systems.md | -- | MEDIUM | Cartography of fallacy detection systems. |
| All other files | -- | LOW | Archived (recoverable), not truly deleted. |

**Note**: This wave is a *move* to _archived/, not a deletion. Content is recoverable from git history. Classification reflects whether content should be in active docs/.

### Wave 7: 066de435 / PR #33 -- reorganize docs/ (2026-02-24)

**Deletions**: 587 LoC (stale comments), docs reorganization (53 to 17 dirs)
**Rationale claimed**: Major repository cleanup

| Change | Class | Note |
|--------|-------|------|
| Removed Authentic gpt-5-mini imports comments from 79 test files | LOW | Stale comments, justified. |
| Removed docs/diagrams/README.md (99 LoC) | LOW | Directory listing, no design content. |
| Removed docs/mcp_servers/README.md (122 LoC) | MEDIUM | MCP server documentation. |
| Removed docs/outils/README.md (139 LoC) | MEDIUM | Tools overview. |
| Moved, not deleted: ~200 files reorganized within docs/ | LOW | Reorganization, not deletion. |

### Wave 8: Other cleanup commits (justified)

These commits followed proper consolidation protocol (archive with header, move not delete, or genuinely dead):

| Commit | Description | Verdict |
|--------|-------------|---------|
| c11ffe1c / PR #34 | Archive core/ to docs/archives/core_overflow/ | PROPER |
| df031b34 / PR #34 | Migrate plugins/, archive legacy services/ | PROPER |
| 738bf4f2 / PR #34 | Migrate mcp_server/ and src/ | PROPER |
| b3808633 / PR #321 | Finalize src/ and plugins/ migration | PROPER |
| 4a09a948 / PR #323 | Archive reports/validation, relocate data | PROPER |
| 2f481355 / PR #322 | Consolidate services/web_api/ | PROPER |
| 2000b17e / PR #318-320 | Cleanup clutter, fix None bug, remove orphan scripts | PROPER |
| 9a1ab738 / PR #215 | Archive orchestrator.py + workflow.py with shims | PROPER |
| 64e2884e / PR #208-R | Archive Flask web_api, rename unified_pipeline | PROPER |
| e735c43f / PR #215 | Archive RealLLMOrchestrator with deprecation shim | PROPER |
| 3fdfe226 / PR #216 | Archive legacy project_manager_agent.py | PROPER |
| 8b02b38a / PR #213 | Consolidate duplicate factories and base_agent | PROPER |
| 33923dd6 / PR #216 | Remove 3 broken agent archetypes | PROPER |
| e2de7d21 / PR #157 | Delete dead scripts importing deleted plugins | PROPER |
| c2e724b1 | Archive old capability_evaluator.py | PROPER |
| 43d6f0d7 / PR #448 | Archive legacy test directories | PROPER |
| b08fa776 / PR #339 | Consolidate 9 README files | PROPER |
| ba43888f / PR #335 | Dedupe scripts/maintenance | PROPER |
| 975f1145 / PR #337 | Remove test scaffolding from production | PROPER |
| 1d2af658 / PR #330 | Remove plaintext dataset content | PROPER |
| 1c433791 / PR #446 | Remove tracked temp artifacts | PROPER |
| 76c5a2f1 / PR #264 | Remove dead logic_graph e2e tests | PROPER |
| cf5db68c / PR #340 | Remove 3 misplaced roo-extensions scripts | PROPER |

---

## Recommended Recovery List (HIGH Only)

| # | File | LoC | Recover from | New Path | Rationale |
|---|------|-----|-------------|----------|-----------|
| 1 | DESIGN_INFERENCE_REPAIR.md | 140 | 48f514c5^ | docs/architecture/DESIGN_INFERENCE_REPAIR.md | FOL type-inference algorithm, relevant to Tweety pre-declaration |
| 2 | architecture_fallacy_workflows.md | 118 | 48f514c5^ | docs/architecture/architecture_fallacy_workflows.md | Plugin split architecture, no equivalent exists |
| 3 | DESIGN_PARALLEL_WORKFLOW.md | 209 | a62ef234^ | docs/architecture/DESIGN_PARALLEL_WORKFLOW.md | Foundational parallel workflow design |
| 4 | 04_operational_plan.md | 1323 | c7ba0e3a^ | docs/architecture/fallacy_operational_plan.md | Complete fallacy system consolidation plan |
| 5 | 03_informal_fallacy_consolidation_plan.md | 1158 | c7ba0e3a^ | docs/architecture/fallacy_consolidation_plan.md | Vision + architecture for unified system |
| 6 | 01_informal_fallacy_system_analysis.md | 216 | c7ba0e3a^ | docs/architecture/fallacy_system_analysis.md | Component analysis of existing fallacy detection |
| 7 | 02_system_legacy_and_evolution_analysis.md | 519 | c7ba0e3a^ | docs/architecture/fallacy_legacy_evolution.md | Legacy evolution history |
| 8 | 06_final_architecture_plan.md | 307 | c7ba0e3a^ | docs/architecture/final_refactoring_plan.md | 3-layer architecture plan |
| 9 | 07_implementation_roadmap.md | 731 | c7ba0e3a^ | docs/architecture/implementation_roadmap.md | Migration methodology |
| 10 | 04_scripts_maintenance_consolidation_plan.md | 761 | c7ba0e3a^ | docs/architecture/scripts_consolidation_plan.md | Scripts consolidation methodology |
| 11 | METHODOLOGIE_SDDD_PHASE_D1.md | 475 | a62ef234^ | docs/architecture/METHODOLOGIE_SDDD.md | SDDD methodology documentation |
| 12 | LLM_SERVICE_API_COMPATIBILITY_FIX.md | 86 | a62ef234^ | docs/architecture/SK_API_COMPATIBILITY.md | SK version migration reference |
| 13 | PLAN_DETAILLE_PHASE2_AUTHENTIC_LLM.md | 256 | a62ef234^ | docs/architecture/AUTHENTIC_LLM_PLAN.md | LLM mock elimination strategy |
| 14 | VALIDATION_REPORT_PARALLEL_WORKFLOW.md | 89 | d8338bc6^ | docs/architecture/PARALLEL_WORKFLOW_VALIDATION.md | Test evidence for parallel workflow |

**Recovery command pattern**:

    git show <sha>^:<path> > <new_path>

---

## Cross-References

| Reference | Context |
|-----------|---------|
| PR #34 (c11ffe1c, df031b34, 738bf4f2) | Initial consolidation, properly archived |
| PR #33 (066de435) | docs/ reorganization, mostly moves |
| Issue #130 (8a10a9c1, c7ba0e3a, a62ef234) | 3-tier cleanup campaign -- TIER 0/1/2 |
| PR #154 | core/ deletion -- properly archived |
| PR #157 (e2de7d21) | Dead script cleanup |
| PR #213 (8b02b38a) | Duplicate factory consolidation |
| PR #215 (9a1ab738, e735c43f) | Orchestration archival with shims |
| PR #216 (33923dd6, 3fdfe226) | Broken archetype removal |
| PR #321, #322, #323 (Epic #317) | Root overflow consolidation -- properly moved |
| PR #330 (1d2af658) | Security: plaintext dataset removal |
| PR #338 (d8338bc6) | Archive 86 reports -- mixed move+delete |
| PR #442/#447 (48f514c5) | Remove dead directories -- **worst offender** |
| PR #444/#449 (e016e59b) | Archive stale docs -- moved to _archived/ |
| Session 101 | Post-mortem establishing Consolider != Archiver rule |
| CLAUDE.md (global) | Contains the violated consolidation rule |

---

## Session 101 Reference

No commit was found referencing Session 101 directly in the commit log. The Consolider != Archiver rule was codified in the global CLAUDE.md (user-level) after Session 101, where 8+ scripts lost, pipeline broken was identified. This audit confirms the pattern has recurred despite the rule.

---

## Methodology

1. **Git log scan**: all commits with cleanup/consolidation/TIER/dead/obsolete/archive/Phase keywords since 2025-06-01
2. **Diff-filter scan**: all file deletions via diff-filter=D
3. **Content peek**: first ~30 lines of each deleted file via git show sha^:path
4. **Classification**: HIGH = design/architecture/pattern/decision record; MEDIUM = technical report with data; LOW = session artifact, truly obsolete
5. **Scope limitation**: Did not investigate commits touching only .pyc, .log, __pycache__, binary files, or files under 10 LoC

---

## Limitations

1. **Branch coverage**: Only investigated commits reachable from main and active branches. Stale feature branches may contain additional deletions.
2. **MEDIUM depth**: MEDIUM-classified files were not fully audited for current relevance -- only first 30 lines examined. Some may warrant promotion to HIGH.
3. **Move vs delete**: Several commits (e016e59b, 43d6f0d7, 4a09a948) moved files to _archived/ or docs/archives/ rather than deleting. These are recoverable but the moves effectively remove them from active documentation.
4. **commit_analysis/ raw dumps**: The 268K-line targeted_analysis_raw.md and 20 analysis lot files (~190K LoC) were not individually reviewed -- classified as LOW bulk data.
5. **Author attribution**: All cleanup commits are authored by jsboigeEpita with Co-Authored-By: Claude -- indicates AI-assisted cleanup that may have lacked human verification of content value.
