# Audit A-03: Argumentation Dialogique

**Issue**: N/A | **SUIVI**: Score 90% | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

## What was delivered (student source)

Student project `1_2_7_argumentation_dialogique` delivered a Walton-Krabbe dialogue protocol implementation with structured argumentation, personality-driven debate agents, multi-metric scoring, and formal speech acts. Adapted from `local_db_arg/src/`.

## What exists in `argumentation_analysis/`

| File | Description |
|------|-------------|
| `agents/core/debate/debate_agent.py` | `DebateAgent(BaseAgent)` + `DebatePlugin` with 3 `@kernel_function` methods |
| `agents/core/debate/debate_definitions.py` | 8 personality archetypes (`AGENT_PERSONALITIES`), `ArgumentMetrics` (8 fields), `EnhancedArgument`, `DebateState`, `ArgumentType`, `DebatePhase` |
| `agents/core/debate/debate_scoring.py` | `ArgumentAnalyzer` with 8-metric evaluation (logical coherence, evidence quality, relevance, emotional appeal, readability, fact-check, novelty, persuasiveness) |
| `agents/core/debate/protocols.py` | `DialogueType` (6 types), `SpeechAct` (9 types), `InquiryProtocol`, `PersuasionProtocol` with formal transition rules |
| `orchestration/registry_setup.py` | :135 `debate_agent` registered with capabilities |

## Preservation Assessment

- **8 personality archetypes** fully preserved -- Scholar, Pragmatist, Devil's Advocate, Idealist, Skeptic, Populist, Economist, Philosopher. SUIVI documented 7; actual code has 8 (over-delivers).
- **8 evaluation metrics** fully preserved in `ArgumentMetrics` dataclass, each with 0.0-1.0 scoring.
- **Walton-Krabbe taxonomy** preserved: 6 `DialogueType` enum values + 9 `SpeechAct` enum values.
- **2 of 6 dialogue types have dedicated protocol classes** (`InquiryProtocol`, `PersuasionProtocol`) with formal state machines, transition rules, and termination conditions. The remaining 4 (information_seeking, negotiation, deliberation, eristic) exist as enum values only.
- **DebateAgent** correctly inherits from `BaseAgent(ChatCompletionAgent)` for `AgentGroupChat` compatibility.
- Plugin exposes 3 `@kernel_function` methods for Semantic Kernel orchestration.

## Gap Analysis

1. **4 of 6 dialogue types are enum-only** (information_seeking, negotiation, deliberation, eristic) without dedicated protocol classes. This matches the student source -- the original only implemented Inquiry and Persuasion fully.
2. **No dedicated tests for protocol state machines** -- InquiryProtocol and PersuasionProtocol transition logic is not explicitly covered by unit tests.

## Recommended Action

The integration is high-fidelity. The enum-only dialogue types match the student source scope. If full protocol coverage is desired for negotiation or deliberation, it would be an enhancement rather than a preservation gap.

## Source Files

- `argumentation_analysis/agents/core/debate/debate_agent.py`
- `argumentation_analysis/agents/core/debate/debate_definitions.py`
- `argumentation_analysis/agents/core/debate/debate_scoring.py`
- `argumentation_analysis/agents/core/debate/protocols.py`
- `argumentation_analysis/orchestration/registry_setup.py`
