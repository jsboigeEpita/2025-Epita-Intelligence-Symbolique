# Student Project Integration Strategy

**Issue**: #35 — Prepare student project integration into tronc commun
**Status**: Phase 0 (Foundations) in progress
**Date**: 2026-02-26

---

## 1. Objective

Integrate 12 student projects into the core `argumentation_analysis/` framework using a **Lego-like composable architecture** where any combination of capabilities can form an agentic conversation.

## 2. Architecture: Lego Composability

### Core Infrastructure (new files)

| File | Role |
|------|------|
| `core/capability_registry.py` | Unified registry for agents, plugins, services by capability |
| `orchestration/workflow_dsl.py` | Declarative workflow builder — compose by capability, not by class |
| `agents/core/abc/plugin.py` | Extended `LegoPlugin` interface with `provides`/`requires`/`parameters` |
| `core/interfaces/analysis_service.py` | Abstract analysis service contract |

### Three Integration Patterns

| Pattern | When | How | Projects |
|---------|------|-----|----------|
| **A: Deep** | Python code → agent/plugin/service | Refactor into BaseAgent + register | JTMS, Dialogique, Governance, Counter-arg, Quality |
| **B: Adapter** | Heavy deps (Java, ML models) | Thin wrapper + graceful degradation | CamemBERT, LLM local, Dung, Semantic Index, Speech |
| **C: External** | Non-Python (TypeScript, HTML) | Consumes FastAPI, no Python imports | Mobile, CaseAI |

### Capability Registration

Every integrated component registers in the `CapabilityRegistry`:

```python
from argumentation_analysis.core.capability_registry import CapabilityRegistry, ComponentType

registry = CapabilityRegistry()
registry.register_agent(
    name="debate_agent",
    agent_class=DebateAgent,
    capabilities=["adversarial_debate", "argument_generation"],
    requires=["llm_service"],
)
```

### Workflow Composition

Workflows are defined declaratively by capability:

```python
from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

workflow = WorkflowBuilder("full_analysis") \
    .add_phase("transcribe", capability="speech_transcription", optional=True) \
    .add_phase("extract", capability="fact_extraction") \
    .add_phase("fallacy", capability="fallacy_detection") \
    .add_phase("quality", capability="argument_quality") \
    .add_phase("counter", capability="counter_argument", depends_on=["fallacy"]) \
    .add_phase("synthesis", capability="synthesis") \
    .build()
```

## 3. Project Inventory

| # | Project | Pattern | Target | Effort | Status |
|---|---------|---------|--------|--------|--------|
| 1 | 1.4.1-JTMS | A: Deep | `services/jtms/core.py` | 2h | Pending |
| 2 | 1.2.7 Dialogique | A: Deep | `agents/core/debate/` | 10h | Pending |
| 3 | 2.1.6 Governance | A: Deep | `agents/core/governance/` | 5h | Pending |
| 4 | 2.3.2 Sophismes | B: Adapter | `adapters/camembert_fallacy.py` | 5h | Pending |
| 5 | 2.3.3 Counter-arg | A: Deep | `agents/core/counter_argument/` | 14h | Pending |
| 6 | 2.3.5 Quality | A: Deep | `agents/core/quality/` | 3h | Pending |
| 7 | 2.3.6 LLM local | B: Adapter | `services/local_llm_service.py` | 2h | Pending |
| 8 | 3.1.5 Mobile | C: External | stays, consumes API | 5h | Pending |
| 9 | abs_arg_dung | B: Adapter | `adapters/dung_framework.py` | 3h | Pending |
| 10 | Arg_Semantic_Index | B: Adapter | `services/semantic_index.py` | 3h | Pending |
| 11 | CaseAI | C: External | stays, webhooks | 2h | Pending |
| 12 | speech-to-text | B: Adapter | `services/speech_transcription.py` | 5h | Pending |

**Total estimated effort**: ~59h

## 4. Model Modernization

Several student projects use outdated models:
- **CamemBERT** (2019) in 2.3.2 → keep fine-tune + add LLM zero-shot fallback
- **gpt-3.5-turbo** in 1.2.7 and 2.3.3 → abstract via ServiceDiscovery
- **text-embedding-ada-002** in Arg_Semantic_Index → use local embeddings.myia.io

The `ServiceDiscovery` class manages model providers as swappable services:
- Local Qwen 3.5 35B (OpenAI-compatible, free)
- OpenRouter (multi-model experimentation)
- OpenAI direct (when needed)

## 5. Emergent Capabilities

The full pipeline traverses all 12 components:

```
Audio → speech-to-text → CamemBERT + InformalFallacyAgent → quality scoring
      → counter-argument generation → JTMS belief maintenance → Dung semantics
      → governance simulation → adversarial debate → semantic indexing
      → LLM synthesis → Mobile / CaseAI display
```

Cross-orchestration loops:
1. **Debate-Governance**: vote → debate challenge → re-vote → converge
2. **JTMS-Dung**: belief retraction → Dung extension change → JTMS update
3. **Quality-gated Counter-Arg**: low quality → flag; high quality → generate counter-argument
4. **Neural-Symbolic Fallacy Fusion**: CamemBERT + rule-based → ensemble vote

## 6. Phasing

| Phase | Focus | Duration |
|-------|-------|----------|
| **0** | Lego foundations (registry, DSL, skills) | 3-4 days |
| **1** | Quick wins (JTMS, Dung, Quality, LLM local) | 2-3 days |
| **2** | Service adapters (CamemBERT, Index, CaseAI, Speech) | 3-4 days |
| **3** | Deep agents (Governance, Dialogique, Mobile) | 5-7 days |
| **4** | Unification (Counter-arg, pipeline, state) | 5-7 days |
| **5** | Documentation and polish | 2-3 days |

## 7. Verification

After each phase:
```bash
pytest tests/ --allow-dotenv --disable-jvm-session -q  # 0 regressions
black --check .                                         # Formatting
```

Gate criteria:
- Phase 0: CapabilityRegistry functional with 3+ agents, WorkflowBuilder produces valid workflows
- Phase 4: Full analysis workflow traverses all 12 capabilities
- Phase 5: CI green, all documentation produced

## 8. Related Documents

- [Plan file](../../.claude/plans/playful-painting-rossum.md) — detailed execution plan
- [INTEGRATION_PLANS/](INTEGRATION_PLANS/) — per-project integration plans (to be created)
- [TWEETY_CAPABILITY_MAP.md](TWEETY_CAPABILITY_MAP.md) — Tweety module mapping (to be created)
