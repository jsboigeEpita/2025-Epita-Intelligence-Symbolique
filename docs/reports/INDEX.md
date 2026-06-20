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
| [spectacular/](spectacular/) | Full artefact bundle: state dumps (5 formats), balance reports, cross-reference graphs, re-prompt traces for corpora A/B/C (42 files, ~454K) |

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

## Post-SCDA Culmination & Fidelity (Epics #947, #1045, #1134, #1165)

Reports produced after the SCDA/Epic #530 wave — the "Final Boss" hardening (#947),
the Agentic Redressement (#1045), the readable 3-act restitution (#1134), and the
culmination "every capability digested & integrated" relaunch (#1165). The `FB-*`
series is the de-castration / fidelity hardening inside #947.

### Final Boss / de-castration (#947, FB-18 → FB-39)

| Report | Description |
|--------|-------------|
| [FB20_PHASE4_TERMINAL_REPORT.md](FB20_PHASE4_TERMINAL_REPORT.md) | Phase-4 terminal synthesis (later reconciled by FB-26/FB-37) |
| [FB26_PER_BRICK_AUDIT.md](FB26_PER_BRICK_AUDIT.md) | Per-brick audit B-A..B-F of the de-castrated pipeline |
| [FB29_QUALITY_BLINDSPOT_REPORT.md](FB29_QUALITY_BLINDSPOT_REPORT.md) | Quality-axis "blind virtues" fix |
| [FB29_ADVERSARIAL_VERIFY.md](FB29_ADVERSARIAL_VERIFY.md) | Adversarial cross-verify of the FB-29 fix |
| [FB28_QUALITY_HEADTOHEAD_REPORT.md](FB28_QUALITY_HEADTOHEAD_REPORT.md) | Pipeline vs baseline quality head-to-head (EDGES verdict) |
| [FB32_DECAST_VARIANCE_REPORT.md](FB32_DECAST_VARIANCE_REPORT.md) | De-castration variance measure + wiring fix |
| [FB33_DECASTRATION_RESIDUAL_AUDIT.md](FB33_DECASTRATION_RESIDUAL_AUDIT.md) | Residual de-castration audit (#1109 §4) |
| [FB34_OPAQUENESS_HARDENING_REPORT.md](FB34_OPAQUENESS_HARDENING_REPORT.md) | Opaque-ID discipline in prompts (0-leak) |
| [FB37_CAPSTONE_SPECTACULAR_REPORT.md](FB37_CAPSTONE_SPECTACULAR_REPORT.md) | Capstone terminal deliverable — formal DECIDES, opaque 0-leak |
| [FB38_QUALITY_AGENTIC_REPORT.md](FB38_QUALITY_AGENTIC_REPORT.md) | 7/9 agentic virtues + EDGES re-measure |
| [FB38_ADVERSARIAL_CROSSVERIFY.md](FB38_ADVERSARIAL_CROSSVERIFY.md) | Adversarial cross-verify of FB-38 (no inflation, EDGES holds) |
| [FB39_PL_PARSING_REPORT.md](FB39_PL_PARSING_REPORT.md) | PL double-ampersand canonicalisation (21/81 → 81/81) |
| [FB39_ADVERSARIAL_CROSSVERIFY.md](FB39_ADVERSARIAL_CROSSVERIFY.md) | Real-Tweety cross-verify of FB-39 (root-cause confirmed) |
| [FB21_PL_VERIFICATION_ROOT_CAUSE.md](FB21_PL_VERIFICATION_ROOT_CAUSE.md) | PL coverage root cause (`PLHandler.check_consistency` missing) |

### Restitution — readable 3-act narrative (#1134 / #1165)

| Report | Description |
|--------|-------------|
| [R1_CULMINATING_REPORT.md](R1_CULMINATING_REPORT.md) | Culminating run + 23/23 substance checklist (the #1165 closer) |
| [R5_VIRTUOUS_SCAN_AGGREGATE.md](R5_VIRTUOUS_SCAN_AGGREGATE.md) | Virtuous-corpus lexical scan — 11 candidates identified |
| [R5_DERIVED_VIRTUOUS_REPORT.md](R5_DERIVED_VIRTUOUS_REPORT.md) | DERIVED virtuous confirmation — 0/4 (corpus-gap, not engine-gap) |

### Fidelity & reader↔writer contracts (#1166, #1151)

| Report | Description |
|--------|-------------|
| [FIDELITY_AUDIT_2026_06_18.md](FIDELITY_AUDIT_2026_06_18.md) | β audit: unified plugins vs student deliverables (71 integrated / 14 partial / 19 missing) |
| [AUDIT_1151_READER_WRITER_CONTRACTS.md](AUDIT_1151_READER_WRITER_CONTRACTS.md) | 3 reader↔writer schema mismatches proved (quality, PL, Dung-semantics) |
| [DIAG_1149_QUALITY_EMPTY_SPECTACULAR.md](DIAG_1149_QUALITY_EMPTY_SPECTACULAR.md) | Quality-empty spectacular diagnostic (schema bug proved) |

### Culmination foundations (D1/E1/W1/T1, Epic #1165)

| Report | Description |
|--------|-------------|
| [W1_REASONER_INVENTORY_REPORT.md](W1_REASONER_INVENTORY_REPORT.md) | Dormant-Tweety reasoner inventory (5 W1 reasoners wired) |
| [W1_REASONER_INVENTORY_REPORT_1178.md](W1_REASONER_INVENTORY_REPORT_1178.md) | 4 more reasoners (#1178: weighted/social/qbf/cl) wired into spectacular |

### Cross-cutting / reference

| Report | Description |
|--------|-------------|
| [CAPSTONE_INTEGRAL_VS_ZEROSHOT.md](CAPSTONE_INTEGRAL_VS_ZEROSHOT.md) | Pipeline vs zero-shot capstone comparison |
| [CAPSTONE_QUALITATIVE_RUBRIC.md](CAPSTONE_QUALITATIVE_RUBRIC.md) | Qualitative scoring rubric for the capstone |
| [PHASE4_VERDICT_RUBRIC.md](PHASE4_VERDICT_RUBRIC.md) | Verdict-band rubric (EXCEEDED/MATCH/PARTIAL/BELOW) |
| [FB18_DEEP_SYNTHESIS_SPEC.md](FB18_DEEP_SYNTHESIS_SPEC.md) | Deep-synthesis fail-loud spec (Section 9) |
| [DRIFT_REGISTER.md](DRIFT_REGISTER.md) | Memory/register of stale-vs-correct facts (FB-39 verify>memo) |
| [subsystem_verdict.md](subsystem_verdict.md) | Per-subsystem verdict map |

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
