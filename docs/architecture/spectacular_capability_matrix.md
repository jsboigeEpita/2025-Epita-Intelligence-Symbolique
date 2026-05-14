# Spectacular Capability Matrix

> Audit of all accumulated components (2026), their wiring status, and gaps vs spectacular target.
> Generated post-Epic G (commit `68aa1e29`, 2026-05-14). Closes #345.

## Legend

- **Wired**: How the component is activated (workflow name, orchestrator, or UI endpoint)
- **Gap**: Missing functionality vs the spectacular analysis target
- **Priority**: P0 = blocking for spectacular pipeline, P1 = important enhancement, P2 = nice-to-have

## Agents (15)

| # | Component | Purpose | Wired in | Gap | Priority |
|---|-----------|---------|----------|-----|----------|
| 1 | FactExtractionAgent | Extract verifiable claims from text | spectacular (extract), formal_extended (extract), light/standard/full/iterative | None | P0 |
| 2 | InformalFallacyAgent | Hybrid fallacy detection (8 families, symbolic+NLI+LLM) | spectacular (hierarchical_fallacy, neural_detect) | None | P0 |
| 3 | CounterArgumentAgent | Generate counter-arguments via 5 rhetorical strategies | spectacular (counter), standard/full/iterative/quality_gated | None | P0 |
| 4 | DebateAgent | Multi-personality adversarial debate (Walton-Krabbe protocols) | spectacular (debate), debate_governance | None | P1 |
| 5 | SynthesisAgent | Aggregate analysis results into coherent output | standard/full | Not in spectacular (no synthesis phase) | P2 |
| 6 | PropositionalLogicAgent | PL reasoning via Tweety | spectacular (pl), formal_extended (pl), nl_to_logic | None | P0 |
| 7 | FOLLogicAgent | First-order logic reasoning with N-to-1 sanitization | spectacular (fol), formal_extended (fol) | None | P0 |
| 8 | ModalLogicAgent | Modal logic (necessity/possibility) reasoning | spectacular (modal), formal_extended (modal) | None | P0 |
| 9 | GovernanceAgent | 7 voting methods, conflict resolution, consensus metrics | spectacular (governance), debate_governance | None | P1 |
| 10 | SherlockEnqueteAgent | Investigation orchestration (Sherlock paradigm) | sherlock_modern, cluedo | Not in spectacular | P2 |
| 11 | WatsonLogicAssistant | Logic analyst providing formal validation | cluedo, sherlock_modern | Not in spectacular | P2 |
| 12 | MoriartyInterrogatorAgent | Oracle interrogation (Cluedo game) | cluedo, cluedo_extended | Specialized — not for pipeline | P2 |
| 13 | SherlockJTMSAgent | Sherlock enriched with JTMS hypothesis tracking | cluedo | Not in spectacular | P2 |
| 14 | IterativeDeepeningOrchestrator | Reusable pattern for iterative refinement | Used by hierarchical_fallacy internally | None | P1 |
| 15 | BaseAgent (abstract) | Foundation for all agents (SK ChatCompletionAgent compat) | All agents inherit | None | P0 |

## Semantic Kernel Plugins (20)

| # | Component | Purpose | Wired in | Gap | Priority |
|---|-----------|---------|----------|-----|----------|
| 16 | StateManagerPlugin | 29 `@kernel_function` methods writing to shared state | All agents via kernel.add_plugin() | None — expanded in G.2 | P0 |
| 17 | FrenchFallacyPlugin | 3-tier hybrid French fallacy detection | spectacular (hierarchical_fallacy) via InformalFallacyAgent | None | P0 |
| 18 | TweetyLogicPlugin | 22 `@kernel_function` methods wrapping Tweety | spectacular (pl/fol/modal), formal_extended | None | P0 |
| 19 | NLToLogicPlugin | Natural language → formal logic translation | spectacular (nl_to_logic), formal_extended (nl_to_logic) | None | P0 |
| 20 | LogicAgentPlugin | PL/FOL/Modal validation with real check_consistency | formal_logic agents via kernel.add_plugin() | None — fixed in G.10 | P0 |
| 21 | ASPICPlugin | ASPIC+ structured argumentation | spectacular (aspic_analysis), formal_extended (aspic) | None | P0 |
| 22 | ATMSPlugin | Assumption-based truth maintenance | spectacular (atms) | None | P1 |
| 23 | RankingPlugin | Argument ranking/credibility evaluation | spectacular (ranking), formal_extended (ranking) | None | P0 |
| 24 | BeliefRevisionPlugin | Belief revision operations | formal_extended (belief_revision) | Not in spectacular | P1 |
| 25 | GovernancePlugin | 4 `@kernel_function` for voting, conflict, consensus | spectacular (governance) via GovernanceAgent | None | P1 |
| 26 | QualityScoringPlugin | 3 `@kernel_function` wrapping ArgumentQualityEvaluator | spectacular (quality) | None | P0 |
| 27 | TextToKBPlugin | NL → KB extraction (structured knowledge base) | formal_extended (extract→KB path) | Not standalone in spectacular | P1 |
| 28 | KBToTweetyPlugin | KB → Tweety formula translation | formal_extended (KB→formula path) | Not standalone in spectacular | P1 |
| 29 | TweetyResultInterpretationPlugin | Formal results → natural language synthesis | formal_extended (tweety_interpretation) | Not in spectacular | P1 |
| 30 | NarrativeSynthesisPlugin | Narrative synthesis for PM agents | spectacular (narrative_synthesis) | **Skips in pipeline mode** — works in conversational only | P0 |
| 31 | ToulminPlugin | Toulmin model argumentation structure | AGENT_SPECIALITY_MAP (informal_fallacy, extract) | Not a dedicated workflow phase | P2 |
| 32 | FallacyWorkflowPlugin | Complex fallacy detection workflow | InformalFallacyAgent internal | None | P1 |
| 33 | ComplexFallacyAnalyzer | Enhanced fallacy analysis tools | Part of analysis pipeline | None | P2 |
| 34 | RhetoricalResultAnalyzer | Rhetorical result analysis | Analysis pipeline | None | P2 |
| 35 | RhetoricalResultVisualizer | Visualization tools for analysis results | Analysis pipeline | None | P2 |

## Tweety Extensions & Semantics (11)

| # | Component | Purpose | Wired in | Gap | Priority |
|---|-----------|---------|----------|-----|----------|
| 36 | Dung Grounded | Grounded extension semantics | spectacular (dung_extensions) | None | P0 |
| 37 | Dung Preferred | Preferred extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P0 |
| 38 | Dung Stable | Stable extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P0 |
| 39 | Dung Complete | Complete extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P0 |
| 40 | Dung Semi-Stable | Semi-stable extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P1 |
| 41 | Dung Ideal | Ideal extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P1 |
| 42 | Dung Stage | Stage extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P2 |
| 43 | Dung CF2 | CF2 extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P2 |
| 44 | Dung Prudent | Prudent extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P2 |
| 45 | Dung Stage2 | Stage2 extension semantics | spectacular (dung_extensions) via analyze_multi_semantics | None | P2 |
| 46 | Dung Resolution-Based | Resolution-based grounded | spectacular (dung_extensions) via analyze_multi_semantics | None | P2 |

## External Solvers (4)

| # | Component | Purpose | Wired in | Gap | Priority |
|---|-----------|---------|----------|-----|----------|
| 47 | ASP/Clingo | Answer-set programming solver (3-tier fallback) | formal_extended, external_solvers module | None | P0 |
| 48 | EProver | FOL automated theorem prover | external_solvers module (FOL routing) | Not in spectacular workflow | P1 |
| 49 | Prover9 | FOL theorem prover (auxiliary) | external_solvers module (FOL fallback) | Not in spectacular workflow | P1 |
| 50 | SPASS | Modal logic theorem prover | external_solvers module (Modal routing) | Not in spectacular workflow | P1 |

## Workflows (12)

| # | Component | Phases | Purpose | Gap | Priority |
|---|-----------|-------:|---------|-----|----------|
| 51 | spectacular_analysis | 20 | Full pipeline: extract→fallacy→logic→Dung→ASPIC→counter→JTMS→governance | narrative_synthesis skips in pipeline | P0 |
| 52 | formal_extended | 15 | Chained Tweety extensions: extract→PL→FOL→Modal→Dung→ASPIC→ABA→ADF→bipolar→ranking→probabilistic→dialogue→belief_revision→interpretation | None | P0 |
| 53 | light_workflow | 3 | extract→quality→counter | None | P2 |
| 54 | standard_workflow | 5 | extract→neural_detect→quality→counter→jtms | None | P2 |
| 55 | full_workflow | 10 | Full analysis with neural+logic+debate | None | P1 |
| 56 | iterative_analysis | 8 | JTMS-driven iterative refinement | None | P1 |
| 57 | nl_to_logic_analysis | 4 | NL→formal logic pipeline | None | P1 |
| 58 | quality_gated_counter | 4+ | Quality-gated counter with loop | None | P1 |
| 59 | debate_governance_loop | 5 | Debate with governance controls | None | P2 |
| 60 | jtms_dung_loop | 5 | JTMS with Dung semantics loop | None | P2 |
| 61 | neural_symbolic_fallacy | 4 | Hybrid neural-symbolic fallacy detection | None | P2 |
| 62 | hierarchical_fallacy | 3 | Hierarchical fallacy detection only | None | P2 |

## Services & Infrastructure (10)

| # | Component | Purpose | Wired in | Gap | Priority |
|---|-----------|---------|----------|-----|----------|
| 63 | CapabilityRegistry | Central registry for agents/plugins/services | All workflows via WorkflowExecutor | None | P0 |
| 64 | AgentFactory | Creates agents with kernel wiring + plugin loading | All agent creation paths | None | P0 |
| 65 | WorkflowExecutor | Executes WorkflowDefinition with DAG-level parallelism | All workflows | asyncio.gather within levels not yet implemented | P1 |
| 66 | PhaseLogger | Structured logging with correlation_id + phase_name | WorkflowExecutor, all phases | None | P0 |
| 67 | Checkpoint/Resume | Per-document checkpoint for long batch runs | WorkflowExecutor (checkpoint_callback) | None | P0 |
| 68 | OpenAPI Contract | Snapshot-based CI protection (41 paths, 78 schemas) | CI pipeline (6 contract tests) | None | P1 |
| 69 | Multi-Model Benchmark | Spectacular workflow comparison across LLM models | scripts/benchmark/ | None | P1 |
| 70 | UnifiedAnalysisState | 34-field shared state (RhetoricalAnalysisState + 10 dimensions) | All workflows via state_writers | narrative_synthesis field not populated in pipeline mode | P0 |
| 71 | TweetyBridge | Python-Tweety (JPype) integration layer | All Tweety-dependent plugins | DLL load order sensitivity on Windows | P1 |
| 72 | LLM Cache Layer | Deterministic replay for tests (record/replay modes) | Test suite (LLM_CACHE_MODE) | Not used in production | P2 |

## Summary Statistics

| Category | Count | P0 | P1 | P2 |
|----------|------:|---:|---:|---:|
| Agents | 15 | 5 | 2 | 8 |
| SK Plugins | 20 | 7 | 5 | 8 |
| Tweety Extensions | 11 | 4 | 2 | 5 |
| External Solvers | 4 | 1 | 3 | 0 |
| Workflows | 12 | 2 | 4 | 6 |
| Services & Infra | 10 | 4 | 3 | 3 |
| **Total** | **72** | **23** | **19** | **30** |

## Key Gaps (P0)

1. **Narrative synthesis skips in pipeline mode** (#30) — The `narrative_synthesis` capability has a registered provider but the phase is skipped during pipeline execution. Works in conversational mode. Root cause: likely a missing state_writer or condition evaluation issue.

2. **External solvers not routed into spectacular** (#48-50) — EProver/Prover9/SPASS are wired in the external_solvers module but not invoked as phases in the spectacular workflow. Only the formal_extended workflow uses them indirectly.

3. **DAG-level parallelism not exploited** (#65) — `WorkflowExecutor` computes parallel execution groups but iterates sequentially within each level. Implementing `asyncio.gather()` within levels would reduce spectacular wall-clock by ~37% (80s→50s).

## Post-Epic G Metrics

| Metric | Pre-Epic G | Post-Epic G | Source |
|--------|-----------:|------------:|--------|
| Total components inventoried | ~35 | **72** | This matrix |
| SK plugins wired in factory | 8 | 13 | AGENT_SPECIALITY_MAP |
| StateManagerPlugin `@kernel_function` | 18 | 29 | G.2 (#469) |
| Dung semantics available | 2 | 11 | G.11 (#478) |
| External solvers routed | 0 | 4 | G.12 (#479) |
| Spectacular phases | 11 | 20 | spectacular workflow |
| Formal_extended phases | 0 | 15 | G.13 (#480) |
| Field coverage (post-baseline) | 44% | 94% | po-2023 post-baseline report |
