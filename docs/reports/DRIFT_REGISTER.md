# DRIFT_REGISTER — Module-by-Module Drift Archaeology (Epic #1045)

**Track**: RA-5 #1050 (Epic #1045 Agentic Redressement)
**Author**: po-2023 worker
**Date**: 2026-06-11
**Method**: Compare current main (`218d8dfa`) vs peak-capability historical state per module. Four loss patterns: (1) degraded prompts, (2) deleted tests, (3) severed wiring, (4) dormant features.

---

## Batch A (done by coordinator R377)

| Module | Findings | Register Entry |
|--------|----------|----------------|
| `agents/core/informal` | 4 findings (degraded prompt, deleted 721 lines tests, archived depth 4-5 cases, deleted DESIGN_PARALLEL_WORKFLOW.md) | See Epic #1045 body |

---

## Batch B (this sweep)

### Module: `agents/core/oracle` (Cluedo + Moriarty)

| # | Finding | Pattern | SHA Lost | Restore? |
|---|---------|---------|----------|----------|
| O-1 | Deleted integration tests: 10 files → 1 consolidated (`ba3d3d95` "consolidate oracle tests"). Lost: real LLM integration with UnifiedConfig, permission rules, cache behavior, Moriarty standalone tests. | 2 | `ba3d3d95` | **Won't restore** — integration tests requiring live LLM (gpt-4o-mini), codebase moved away from this pattern |
| O-2 | `HypothesisTracker` (ATMS-based) in `hypothesis_tracker.py`: exported from `__init__.py`, never instantiated. Redundant with JTMS HypothesisTracker in `sherlock_jtms_agent.py` which IS active. | 4 | Present since initial | **Won't restore** — redundant |
| O-3 | `PhaseDExtensions` mixin: 5 methods (dramatic timing, false lead, narrative twist, conversational polish, ideal trace metrics) adding indirection to CluedoOracleState which already has inline Phase D methods. | 4 | Present since initial | **Won't restore** — inline works, mixin is unnecessary |
| O-4 | `MoriartyTools.simulate_other_player_response()`: kernel function never called. Only `validate_suggestion_cluedo()` and 3 reveal methods are active. | 4 | Present since initial | **Won't restore** — never wired into any pipeline |
| O-5 | No prompt degradation — BASE_ORACLE_SYSTEM_PROMPT and MORIARTY_SPECIALIZED_INSTRUCTIONS intact (only Black formatting changes). | N/A | — | N/A |

**Net**: Oracle is clean — no prompt degradation, no severed wiring. Losses are dormant code and integration tests that are no longer the testing pattern.

---

### Module: `agents/core/debate` (DebateAgent, Walton-Krabbe)

| # | Finding | Pattern | SHA Lost | Restore? |
|---|---------|---------|----------|----------|
| D-1 | **System prompt truncated**: original `_create_enhanced_prompt()` injected OPPONENT ANALYSIS JSON (avg_persuasiveness, dominant_style, weakness per opponent). Current prompt (L217-221) is 138 chars generic. Strategy descriptions abbreviated. | 1 | `c5f15ac1` (student→SK consolidation) | **Consider restoring** — opponent analysis JSON was the key differentiator for adaptive debate. The data structure exists but is never injected into the prompt. |
| D-2 | `EnhancedDebateModerator.run_debate()`: complete phase-based debate flow (opening→main→rebuttals→closing, audience simulation, winner determination). Never called. `_invoke_debate_analysis` only uses `DebatePlugin.analyze_argument_quality()` for single-argument scoring. | 3 | `c5f15ac1` | **Won't restore** — standalone demo pattern, not pipeline-integrated |
| D-3 | Walton-Krabbe protocol classes (`DialogueProtocol`, `InquiryProtocol`, `PersuasionProtocol`, `DialogueMove`, `FormalArgument`, `KnowledgeBase`): well-designed formal dialogue specifications, never instantiated. | 3 | Present since initial | **Consider restoring** if formal dialogue protocols become a goal |
| D-4 | `_conclude_debate()` lost multi-criteria winner: original had 4 categories (overall, audience_favorite, most_logical, best evidence) + narrative summary. Current only sets single winner. | 1 | `c5f15ac1` | **Consider restoring** — multi-criteria adds analytical depth |
| D-5 | No deleted test files. | N/A | — | N/A |

**Net**: Debate has the **most significant prompt degradation** in Batch B — the opponent analysis injection loss (D-1) directly reduces debate quality. Highest-impact restoration candidate.

---

### Module: `agents/core/counter_argument` (5 strategies, 5-criteria evaluator)

| # | Finding | Pattern | SHA Lost | Restore? |
|---|---------|---------|----------|----------|
| CA-1 | No deleted test files found. | N/A | — | N/A |
| CA-2 | No dedicated prompt file (skprompt.txt) — prompt is inline in agent code. No degradation detected vs git history. | N/A | — | N/A |
| CA-3 | `CounterArgumentAgent` and its plugin are wired: `AgentFactory.create_counter_argument_agent()`, `_invoke_counter_argument` in `invoke_callables.py`. Active path verified. | N/A | — | N/A |
| CA-4 | 5 strategies (reductio ad absurdum, counter-example, distinction, reformulation, concession) and 5-criteria evaluator all present and tested. | N/A | — | N/A |

**Net**: Counter-argument is **clean** — no drift detected.

---

### Module: `agents/core/governance` (7 voting methods)

| # | Finding | Pattern | SHA Lost | Restore? |
|---|---------|---------|----------|----------|
| G-1 | No deleted test files found. | N/A | — | N/A |
| G-2 | `GovernancePlugin` is wired: registered in `AgentFactory` (`factory.py:91`), invoked via `_invoke_governance` in `invoke_callables.py:1402`. Active path verified. | N/A | — | N/A |
| G-3 | 7 voting methods (majority, Borda, Condorcet, approval, etc.) present and functional. Fabricated probabilities fixed in prior PR. | N/A | — | N/A |

**Net**: Governance is **clean** — no drift detected.

---

### Module: `agents/core/quality` (9 virtues, QualityScoringPlugin)

| # | Finding | Pattern | SHA Lost | Restore? |
|---|---------|---------|----------|----------|
| Q-1 | No deleted test files found. | N/A | — | N/A |
| Q-2 | `QualityScoringPlugin` wired: registered in `AgentFactory` (`factory.py:87`), also in `SherlockModernOrchestrator` and `plugin_benchmark.py`. Active path verified. | N/A | — | N/A |
| Q-3 | 9 virtue detectors (clarity, coherence, relevance, etc.) present and deterministic. Value-gate tests pass (TRUSTWORTHY in subsystem verdict). | N/A | — | N/A |

**Net**: Quality is **clean** — no drift detected.

---

### Module: `orchestration/` (hierarchical, conversational, pipeline)

| # | Finding | Pattern | SHA Lost | Restore? |
|---|---------|---------|----------|----------|
| ORC-1 | **Strategic objectives hardcoded**: `StrategicManager._define_initial_objectives()` (manager.py L223-247) defines 4 fixed objectives. Never LLM-generated. `StrategicState.global_objectives` field exists but is populated deterministically. StrategicState is completely separate from `UnifiedAnalysisState` — operational agents never see strategic objectives. | 4 | `de7c9334` (#35 — UnifiedPipeline became main path, shared state evolved as results receptacle only) | **Restore** — feeds RA-4 (#1049, wake strategic NL journaling). The bridge between strategic and operational state was severed. |
| ORC-2 | `HierarchicalOrchestrator` (R311, `841ed091`) short-circuits the 3-tier chain into deterministic `WorkflowDefinition`s via `objectives_to_workflow()`. The hierarchical delegation (strategic→tactical→operational) was the original design but is bypassed. | 3 | `841ed091` | **Restore** — the 3-tier delegation is the architectural foundation for PM-agentique (FB-18 Mode B). Not a loss, but a deactivation. |
| ORC-3 | Deleted orchestrators: `real_llm_orchestrator.py` and `logique_complexe_orchestrator.py` removed by `c95c41c3` (#887 — "remove 2 empty orchestrators"). These were stubs/shims, not real losses. | 2 | `c95c41c3` | **Won't restore** — were empty stubs |
| ORC-4 | Deleted `analysis_runner.py` and `enhanced_pm_analysis_runner.py` by `d2fef7b4`. These were early pipeline runners superseded by `UnifiedPipeline`. | 2 | `d2fef7b4` | **Won't restore** — superseded by UnifiedPipeline |
| ORC-5 | `ConversationalOrchestrator` PM re-prompting and growth validation: ACTIVE. Not degraded. The harness fallbacks (Dung, ASPIC, modal, CA, PL/FOL, quality) are present. | N/A | — | N/A |
| ORC-6 | `WorkflowDSL` + `CapabilityRegistry`: ACTIVE. `find_*_for_capability()` dynamic resolution works. | N/A | — | N/A |

**Net**: Orchestration has **one significant finding** (ORC-1: strategic objectives hardcoded, bridge to operational state severed) and one deactivation (ORC-2: hierarchical short-circuit). Both feed RA-4 (#1049).

---

### Module: `core/communication` (multi-channel messaging)

| # | Finding | Pattern | SHA Lost | Restore? |
|---|---------|---------|----------|----------|
| CM-1 | **Deleted `test_middleware.py`** (474 lines → 0 in main, 314 reduced in tests/unit). Lost: MockChannel, routing assertions (COMMAND/INFORMATION/REQUEST→COLLABORATION), statistics test, async request test. | 2 | `b350e539` | **Restore (partial)** — the reduced version lacks routing assertions and async tests |
| CM-2 | `ChannelType.NEGOTIATION`, `FEEDBACK`, `SYSTEM`: declared in routing table but no channel implementations exist. `determine_channel()` routes to them but `get_channel()` returns None. | 3 | Present since initial | **Won't restore** — forward-declared, never implemented |
| CM-3 | `CommandMessage`, `InformationMessage`, `RequestMessage`, `EventMessage`: defined, tested, never used in production. All production code uses `Message()` directly. | 4 | Present since initial | **Won't restore** — convenience wrappers never adopted |
| CM-4 | `InformationMessage` uses `DATA_DIR` (Path object) as dict key instead of string `"data"`. Latent portability bug (dormant, never called). | 4 | Present since initial | **Won't restore as-is** — fix if re-activated |
| CM-5 | `MessageMiddleware.get_adapter()` (monkey-patched in `middleware_patch.py`): zero callers. All production code instantiates adapters directly. | 3 | `dc32640a` | **Won't restore** — unnecessary indirection |
| CM-6 | `RequestResponseProtocol.send_request_async_callback()`: zero callers. Superseded by Future-based `send_request_async()`. | 3 | Present since initial | **Won't restore** — superseded |
| CM-7 | `HierarchicalChannel.clear_queue()`: zero production callers (tested only). | 4 | Present since initial | **Won't restore** — not needed in current flow |

**Net**: Communication core architecture is intact. Only significant loss is CM-1 (test coverage). The channel types and message subclasses are dormant design, not lost functionality.

---

## Aggregate Summary

| Module | Clean | Findings | Restore-worthy |
|--------|-------|----------|----------------|
| Oracle | ✅ Mostly | 4 (all dormant/deleted tests) | None |
| **Debate** | ⚠️ Degraded | 4 (2 prompt, 2 wiring) | **D-1 opponent analysis JSON** (HIGH), D-4 multi-criteria winner |
| Counter-argument | ✅ Clean | 0 | None |
| Governance | ✅ Clean | 0 | None |
| Quality | ✅ Clean | 0 | None |
| **Orchestration** | ⚠️ Dormant | 6 (2 significant) | **ORC-1 strategic objectives** (feeds RA-4), ORC-2 hierarchical delegation |
| Communication | ✅ Mostly | 7 (1 test loss, 6 dormant) | CM-1 test coverage (MEDIUM) |

### High-Impact Restoration Candidates (feed new RA-* sub-issues)

1. **D-1**: Debate opponent analysis JSON injection → sub-issue for debate prompt restoration
2. **ORC-1**: Strategic NL objectives → feeds existing RA-4 #1049
3. **CM-1**: Communication middleware test coverage → sub-issue for test restoration
4. **D-4**: Multi-criteria debate winner → sub-issue for debate quality improvement

### Modules With Zero Drift

Counter-argument, governance, and quality show **zero drift** — they are well-maintained, properly wired, and have no deleted tests or degraded prompts.

---

## Privacy Compliance

- Opaque IDs only
- No source names, authors, URLs, dates
- No `raw_text`, `full_text`, `full_text_segment`
- grep-clean (verified before commit)
