# Capability Duality

## Principle

Each capability in the system can be provided by two paths:

1. **Pipeline path** (`_invoke_*` callable) — Used by `WorkflowExecutor` during DAG-based pipeline execution. Each callable receives `(input_text, context)` and returns a result dict.

2. **SK plugin path** (`@kernel_function`) — Used by conversational agents via Semantic Kernel's function-calling mechanism. The LLM discovers and invokes these methods autonomously.

When both paths exist for the same capability, this is called a **duality**. Dualities are acceptable when both paths converge on the same backend implementation and share state through `UnifiedAnalysisState`.

## Invariant

> **Every capability duality must be documented in `ACCEPTED_DUALITIES`** in `tests/integration/test_capability_duality_invariant.py`.

The CI enforces this invariant. Undocumented dualities cause test failures.

## Accepted Dualities

| Capability | Plugin | Invoke Callable | Convergence Point |
|---|---|---|---|
| `argument_quality` | `QualityScoringPlugin` | `_invoke_quality_evaluator` | `ArgumentQualityEvaluator` |
| `counter_argument_generation` | `CounterArgumentAgent` @kf | `_invoke_counter_argument` | Same agent |
| `adversarial_debate` | `DebateAgent` @kf | `_invoke_debate_analysis` | Same agent |
| `governance_simulation` | `GovernancePlugin` | `_invoke_governance` | `GovernanceAgent` |
| `belief_maintenance` | `JTMSPlugin` | `_invoke_jtms` | `JTMS` core |
| `atms_reasoning` | `ATMSPlugin` | `_invoke_atms` | `ATMS` core |
| `aspic_plus_reasoning` | `ASPICPlugin` | `_invoke_aspic` | ASPIC handler |
| `ranking_semantics` | `RankingPlugin` | `_invoke_ranking` | Ranking handler |
| `dung_extensions` | `TweetyLogicPlugin` | `_invoke_dung_extensions` | Dung handler |
| `propositional_logic` | `TweetyLogicPlugin` + `LogiqueComplexePlugin` | `_invoke_propositional_logic` | Tweety PL |
| `fol_reasoning` | `TweetyLogicPlugin` | `_invoke_fol_reasoning` | Tweety FOL |
| `modal_logic` | `TweetyLogicPlugin` | `_invoke_modal_logic` | Tweety Modal |
| `fact_extraction` | — | `_invoke_fact_extraction` | Heuristic extractor |
| `nl_to_logic_translation` | `NLToLogicPlugin` | `_invoke_nl_to_logic` | NLToLogicTranslator |
| `belief_revision` | `BeliefRevisionPlugin` | `_invoke_belief_revision` | Tweety revision |
| `neural_fallacy_detection` | `FrenchFallacyPlugin` | `_invoke_camembert_fallacy` | Detection backend |
| `formal_synthesis` | `NarrativeSynthesisPlugin` | `_invoke_formal_synthesis` | Aggregation logic |
| `narrative_synthesis` | `NarrativeSynthesisPlugin` | `_invoke_narrative_synthesis` | Synthesis logic |

## Architecture Decision

The duality exists because the system operates in two modes:

- **Pipeline mode**: `WorkflowExecutor` orchestrates phases via `_invoke_*` callables with DAG parallelism
- **Conversational mode**: SK `AgentGroupChat` lets agents discover and call `@kernel_function` methods

Both modes must produce equivalent results for the same input. The state writers (`CAPABILITY_STATE_WRITERS`) normalize the output into `UnifiedAnalysisState` regardless of which path was taken.

## Adding a New Duality

1. Implement the capability in both paths (invoke callable + plugin method)
2. Ensure both use the same underlying implementation
3. Add an entry to `ACCEPTED_DUALITIES` in the invariant test
4. Add a row to the table above
5. Ensure the state writer handles the output of both paths identically
