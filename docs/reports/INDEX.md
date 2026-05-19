# Reports Index

## SCDA Spectacular Pipeline Reports (Epic #530)

The SCDA (Spectacular Conversational Discourse Analysis) reports document the development and validation of a multi-agent argumentation analysis pipeline across Sprints 3-8.

### Master Report

| Report | Description |
|--------|-------------|
| [EPIC_530_SCDA_SPECTACULAR_FINAL_REPORT.md](EPIC_530_SCDA_SPECTACULAR_FINAL_REPORT.md) | Capstone narrative: 4 spectacular properties demonstrated, sprint journey, consolidated metrics, patterns & lessons |

### Spectacular Demo Bundle

| Directory | Description |
|-----------|-------------|
| [spectacular/](spectacular/) | Full artefact bundle: state dumps (6 formats), balance reports, cross-reference graphs, re-prompt traces for corpora A/B/C |

### Sprint Audit Trail (chronological)

| Date | Report | Sprint | Focus |
|------|--------|--------|-------|
| 2026-05-15 | [SCDA_AUDIT_2026-05-15.md](SCDA_AUDIT_2026-05-15.md) | 2 | Initial audit, baseline metrics |
| 2026-05-15 | [SCDA_AUDIT_MAXTURNS_2026-05-15.md](SCDA_AUDIT_MAXTURNS_2026-05-15.md) | 2 | Max-turns convergence analysis |
| 2026-05-15 | [REPRODUCIBILITY_2026-05-15.md](REPRODUCIBILITY_2026-05-15.md) | 2 | Reproducibility validation framework |
| 2026-05-15 | [TEST_HEALTH_2026-05-15.md](TEST_HEALTH_2026-05-15.md) | 2 | Test suite health audit |
| 2026-05-16 | [SCDA_AUDIT_POST_SPRINT3_2026-05-16.md](SCDA_AUDIT_POST_SPRINT3_2026-05-16.md) | 3 | ParserException fixes (159→0), pipeline completion |
| 2026-05-16 | [BASELINE_0SHOT_2026-05-16.md](BASELINE_0SHOT_2026-05-16.md) | 3 | LLM 0-shot baseline comparison |
| 2026-05-16 | [AUDIT_ROGUE_CLEANUP_2026-05-16.md](AUDIT_ROGUE_CLEANUP_2026-05-16.md) | — | Rogue cleanup audit (14 HIGH priority docs) |
| 2026-05-16 | [SCDA_AUDIT_POST_SPRINT4_2026-05-16.md](SCDA_AUDIT_POST_SPRINT4_2026-05-16.md) | 4 | JTMS sync bridge, convergence gate |
| 2026-05-17 | [SCDA_CORPUS_A_PUSH_2026-05-17.md](SCDA_CORPUS_A_PUSH_2026-05-17.md) | 5 | Corpus A convergence fix, phase-aware gate |
| 2026-05-17 | [SCDA_DEEPSYNTH_BASELINE_2026-05-17.md](SCDA_DEEPSYNTH_BASELINE_2026-05-17.md) | 5 | DeepSynthesis agent baseline comparison |
| 2026-05-17 | [SCDA_INSTRUCTION_TUNING_2026-05-17.md](SCDA_INSTRUCTION_TUNING_2026-05-17.md) | 5 | Instruction tuning for agent prompts |
| 2026-05-18 | [SCDA_GROWTH_HOOK_2026-05-18.md](SCDA_GROWTH_HOOK_2026-05-18.md) | 6 | Growth validation hook (re-prompt on zero delta) |
| 2026-05-18 | [SCDA_MULTI_CORPUS_BASELINE_2026-05-18.md](SCDA_MULTI_CORPUS_BASELINE_2026-05-18.md) | 6 | gpt-5-mini upgrade, 3-corpus baseline |
| 2026-05-18 | [SCDA_CROSS_CORPUS_PARALLELS_2026-05.md](SCDA_CROSS_CORPUS_PARALLELS_2026-05.md) | 7 | Cross-corpus rhetorical parallels, 3-axis radar |
| 2026-05-18 | [SCDA_GROWTH_HOOK_MULTI_CORPUS_2026-05-18.md](SCDA_GROWTH_HOOK_MULTI_CORPUS_2026-05-18.md) | 6 | Growth hook validation across 3 corpora |
| 2026-05-18 | [SCDA_INFORMAL_AGENT_TUNING_2026-05-18.md](SCDA_INFORMAL_AGENT_TUNING_2026-05-18.md) | 6 | InformalAgent taxonomy tuning |
| 2026-05-18 | [SCDA_TOOL_GATING_2026-05.md](SCDA_TOOL_GATING_2026-05.md) | 7 | Phase-scoped tool gating (composition) |
| 2026-05 | [SCDA_MULTI_FORMAT_PIPELINE_2026-05.md](SCDA_MULTI_FORMAT_PIPELINE_2026-05.md) | 8 | Multi-format exporter + re-prompt trace extraction |

### Performance & Profiling

| Report | Description |
|--------|-------------|
| [spectacular_profiling.md](spectacular_profiling.md) | 17-phase workflow profile: 80s wall-clock, 66.8 MB peak |
| [spectacular_perf_bench.md](spectacular_perf_bench.md) | Standard vs spectacular comparison |
| [spectacular_vs_baseline.md](spectacular_vs_baseline.md) | Spectacular delta: +3 fields, +9.4% coverage |

## Pre-SCDA Reports (Legacy)

| Report | Description |
|--------|-------------|
| [benchmark_evaluation_report.md](benchmark_evaluation_report.md) | Early benchmark evaluation |
| [fallacy_benchmark_report.md](fallacy_benchmark_report.md) | Fallacy detection benchmarks |
| [benchmark_comparative_analysis.md](benchmark_comparative_analysis.md) | Comparative analysis across runs |
| [discourse_patterns.md](discourse_patterns.md) | Discourse pattern analysis |
| [EPIC_G_CLOSURE_REPORT.md](EPIC_G_CLOSURE_REPORT.md) | Epic G closure report |
| [coverage_audit.md](coverage_audit.md) / [coverage_audit_2026_03_07.md](coverage_audit_2026_03_07.md) | Test coverage audits |

## Infrastructure Reports

| Report | Description |
|--------|-------------|
| [D-CI-01 through D-CI-06](.) | CI pipeline setup and stabilization (6 reports) |
| [M-MCP-01_rapport_configuration_extension_mcps.md](M-MCP-01_rapport_configuration_extension_mcps.md) | MCP server configuration |
| [services_web_api_audit_317.md](services_web_api_audit_317.md) | Web API audit (Epic #317) |
| [soutenance_comparison.md](soutenance_comparison.md) | Soutenance comparison data |
