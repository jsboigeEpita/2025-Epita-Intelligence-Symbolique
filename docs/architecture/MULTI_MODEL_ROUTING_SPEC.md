# Multi-Model Routing Design Specification

**Issue**: #988 — Roadmap #78 Phase 2, North-Star parametric integration
**Scope**: Design spec only. No code changes to `invoke_callables.py` (collision guard: po-2025 owns that file's logic).
**Purpose**: Define how per-phase model tier routing should work so that cheap mechanical phases (extraction, NL-to-logic) can use a cheaper model while reasoning-heavy phases (synthesis, governance, debate) use a strong model — reducing cost on repeated Phase 4 integral runs.

**Status**: Design spec — awaiting implementation in a future sprint by the owner of `invoke_callables.py`.

---

## 1. Current State

### 1.1 LLM Acquisition Path

All LLM calls in the spectacular pipeline funnel through two functions in `invoke_callables.py`:

| Function | Purpose | Location |
|----------|---------|----------|
| `_get_openai_client()` | Create `AsyncOpenAI` client + resolve model id | Line 175 |
| `_get_determinism_params()` | Resolve temperature/seed (model-aware) | Line 127 |
| `_resolve_model_id()` | Resolve active model id from env vars | Line 109 |
| `_guarded_chat_completion()` | Budget-guarded chat completion funnel | Line 312 |

**Current model resolution** (`_resolve_model_id()`):
```
If OPENROUTER_BASE_URL + OPENROUTER_API_KEY set:
    model = OPENROUTER_CHAT_MODEL_ID || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
Else:
    model = OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
```

**Key constraint**: `_resolve_model_id()` returns a **single** model id. Every phase in the pipeline uses this same model.

### 1.2 Budget Guard

`_guarded_chat_completion()` (line 312) funnels ALL LLM chat completions through a per-run budget. The circuit breaker is model-agnostic — it counts calls, not tokens or cost. Model-tier routing would allow the budget to become cost-aware (e.g., cheap calls count as 0.1, strong calls as 1.0).

### 1.3 Determinism Logic

`_get_determinism_params()` is already **model-aware**: it suppresses temperature/seed for reasoning models (gpt-5*, o1*, o3*) unless `LLM_FORCE_SAMPLING_PARAMS=1`. This logic MUST be preserved per resolved model (not just the global model).

---

## 2. Proposed Architecture

### 2.1 Tier System

Introduce a **tier** abstraction over model ids:

| Tier | Purpose | Default resolution | Example models |
|------|---------|-------------------|----------------|
| `cheap` | Mechanical phases (extraction, parsing, NL-to-logic) | Falls back to `OPENAI_CHAT_MODEL_ID` | `gpt-5-mini`, `gpt-4.1-mini` |
| `strong` | Reasoning-heavy phases (synthesis, debate, governance) | Falls back to `OPENAI_CHAT_MODEL_ID` | `gpt-5-mini`, `gpt-4.1`, `o3-mini` |

**Default behaviour**: Both tiers resolve to `OPENAI_CHAT_MODEL_ID`. This means **zero breaking change** — if the user doesn't configure tier overrides, every phase uses the same model as today.

### 2.2 Environment Variables

```bash
# Existing (unchanged):
OPENAI_CHAT_MODEL_ID=gpt-5-mini          # Default model for all tiers
OPENAI_API_KEY=<key>

# New (optional, both default to OPENAI_CHAT_MODEL_ID):
LLM_MODEL_CHEAP=gpt-5-mini               # Model for "cheap" tier phases
LLM_MODEL_STRONG=gpt-5-mini              # Model for "strong" tier phases
```

**Resolution priority**:
```
cheap model = LLM_MODEL_CHEAP || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
strong model = LLM_MODEL_STRONG || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
```

Same for OpenRouter path:
```
cheap model = OPENROUTER_MODEL_CHEAP || LLM_MODEL_CHEAP || OPENROUTER_CHAT_MODEL_ID || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
strong model = OPENROUTER_MODEL_STRONG || LLM_MODEL_STRONG || OPENROUTER_CHAT_MODEL_ID || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
```

### 2.3 Phase → Tier Mapping

Each invoke callable declares its tier. Conservative: only obviously-mechanical phases get `cheap`, everything else defaults to `strong`.

| Phase | Capability (snake_case) | Proposed Tier | Rationale |
|-------|------------------------|--------------|-----------|
| `extract` | `fact_extraction` | `cheap` | Heuristic extraction + optional LLM for claim classification |
| `nl_to_logic` | `nl_to_logic_translation` | `cheap` | NL→formula pattern matching |
| `text_to_kb` | `nl_extraction` | `cheap` | Structured KB extraction |
| `kb_to_tweety` | `kb_to_tweety` | `cheap` | Formula syntax translation |
| `quality` | `argument_quality` | `cheap` | Heuristic 9-virtue scoring (spacy/textstat + fallback) |
| `hierarchical_fallacy` | `hierarchical_fallacy_detection` | `strong` | Requires nuanced rhetorical analysis |
| `counter` | `counter_argument_generation` | `strong` | Generative counter-argument creation |
| `debate` | `adversarial_debate` | `strong` | Multi-turn adversarial reasoning |
| `governance` | `governance_simulation` | `strong` | Multi-method voting + conflict resolution |
| `jtms` | `belief_maintenance` | `cheap` | Truth maintenance (largely algorithmic) |
| `atms` | `atms_reasoning` | `cheap` | Multi-context reasoning (algorithmic) |
| `dung_extensions` | `dung_extensions` | `cheap` | Graph-based extension computation |
| `aspic_analysis` | `aspic_plus_reasoning` | `cheap` | Structured argumentation (algorithmic) |
| `narrative_synthesis` | `narrative_synthesis` | `strong` | Generative prose synthesis |
| `formal_synthesis` | `formal_synthesis` | `cheap` | Aggregation of formal results |
| `analysis_synthesis` | `analysis_synthesis` | `strong` | Terminal synthesis with interpretation |
| `deep_synthesis` | `deep_synthesis` | `strong` | 9-section grounded report generation |
| `stakes` | `stakes_extraction` | `strong` | Requires stakeholder analysis reasoning |
| `pl` | `propositional_logic` | `cheap` | Tweety SAT solving (algorithmic) |
| `fol` | `fol_reasoning` | `cheap` | Tweety FOL reasoning (algorithmic) |
| `modal` | `modal_logic` | `cheap` | Tweety modal reasoning (algorithmic) |
| `tweety_interpretation` | `formal_result_interpretation` | `cheap` | Formula→NL translation |
| `belief_revision` | `belief_revision` | `cheap` | Dalal/Levi distance (algorithmic) |
| `probabilistic` | `probabilistic_argumentation` | `cheap` | Probability computation |
| `ranking` | `ranking_semantics` | `cheap` | Ranking computation |
| `bipolar` | `bipolar_argumentation` | `cheap` | Support+attack framework |
| `neural_detect` | `neural_fallacy_detection` | `cheap` | NLP model inference (no reasoning) |

**Cost projection** (spectacular pipeline, 29 phases):
- All-strong (current): ~29 × strong-model cost
- Tiered: ~18 cheap + ~11 strong ≈ 18 × 0.1 + 11 × 1.0 = **12.8 cost-units** vs 29.0 (56% reduction)

### 2.4 Implementation Pattern

The following changes are scoped to `invoke_callables.py` (owned by po-2025):

#### A. New resolver function

```python
def _resolve_model_for_tier(tier: str = "strong") -> str:
    """Resolve model id for a given tier.

    Falls back to OPENAI_CHAT_MODEL_ID when no tier-specific override is set,
    preserving current single-model behaviour.
    """
    base_model = _resolve_model_id()  # existing function

    if tier == "cheap":
        tier_model = os.environ.get("LLM_MODEL_CHEAP")
        if os.environ.get("OPENROUTER_BASE_URL") and os.environ.get("OPENROUTER_API_KEY"):
            tier_model = tier_model or os.environ.get("OPENROUTER_MODEL_CHEAP")
    elif tier == "strong":
        tier_model = os.environ.get("LLM_MODEL_STRONG")
        if os.environ.get("OPENROUTER_BASE_URL") and os.environ.get("OPENROUTER_API_KEY"):
            tier_model = tier_model or os.environ.get("OPENROUTER_MODEL_STRONG")
    else:
        tier_model = None

    return tier_model or base_model
```

#### B. Extend `_get_openai_client()` to accept tier

```python
def _get_openai_client(tier: str = "strong") -> Tuple[Any, str]:
    # ... existing provider selection logic ...
    model_id = _resolve_model_for_tier(tier)
    # ... rest unchanged ...
```

#### C. Extend `_guarded_chat_completion()` to accept tier

```python
async def _guarded_chat_completion(
    messages: list,
    *,
    tier: str = "strong",
    phase_name: str = "",
    **kwargs,
) -> str:
    client, model_id = _get_openai_client(tier=tier)
    # determinism params use the resolved model_id (already model-aware)
    det = _get_determinism_params_for_model(model_id)
    # ... rest of existing guard logic ...
```

#### D. Each `_invoke_*` passes its tier

```python
async def _invoke_fact_extraction(text, context):
    # cheap tier — mechanical extraction
    result = await _guarded_chat_completion(messages, tier="cheap", phase_name="extract")
    ...

async def _invoke_deep_synthesis(text, context):
    # strong tier — generative synthesis
    result = await _guarded_chat_completion(messages, tier="strong", phase_name="deep_synthesis")
    ...
```

#### E. Per-model determinism

`_get_determinism_params()` currently reads `_resolve_model_id()`. With tiering, it must accept the **resolved** model id as a parameter:

```python
def _get_determinism_params(model_id: str = None) -> Dict[str, Any]:
    resolved = model_id or _resolve_model_id()
    # ... existing logic, but use `resolved` instead of _resolve_model_id() ...
```

---

## 3. Testing Strategy

### 3.1 Unit Tests

| Test | What it verifies |
|------|-----------------|
| `test_default_tier_unresolved` | Without `LLM_MODEL_CHEAP`/`LLM_MODEL_STRONG`, both tiers resolve to `OPENAI_CHAT_MODEL_ID` |
| `test_cheap_tier_env_override` | `LLM_MODEL_CHEAP=gpt-4.1-mini` resolves cheap tier correctly |
| `test_strong_tier_env_override` | `LLM_MODEL_STRONG=o3-mini` resolves strong tier correctly |
| `test_determinism_per_tier_model` | `_get_determinism_params(strong_model)` suppresses temp/seed for reasoning models, allows for non-reasoning |
| `test_tier_passed_to_guarded` | `_guarded_chat_completion(tier="cheap")` uses cheap model id in API call |

### 3.2 Integration Test

A fixture pipeline run with `LLM_MODEL_CHEAP=gpt-5-mini` and `LLM_MODEL_STRONG=gpt-5-mini` (both same, to avoid actual cost) that verifies:
- Each phase logs its resolved model id
- The log shows tier labels per phase
- Output is identical to current single-model run (behavioural parity)

---

## 4. Cost Model

### 4.1 Current (all-strong)

Assuming `gpt-5-mini` at ~$0.15/1M input tokens, ~$0.60/1M output tokens:
- Spectacular pipeline: ~20-29 LLM calls per run
- Estimated cost per run: ~$0.05-0.15

### 4.2 With Tiered Routing

Cheap tier could use `gpt-4.1-mini` at ~$0.10/1M input tokens:
- 18 cheap phases × lower cost + 11 strong phases × current cost
- Estimated savings: ~40-56% on LLM calls
- Meaningful at scale (100+ runs for benchmarking)

### 4.3 Break-Even

The tier system pays for itself when:
- Phase 4 requires >10 integral runs (corpus_A/B/C × variations)
- Or when daily development iteration needs cheap smoke-tests

---

## 5. Migration Path

### 5.1 Phase 1: Additive (zero breaking change)

1. Add `_resolve_model_for_tier()` and `LLM_MODEL_CHEAP`/`LLM_MODEL_STRONG` env vars
2. Extend `_get_openai_client(tier=)` and `_guarded_chat_completion(tier=)` with default `"strong"`
3. All existing callers continue to work without changes (default tier = strong = current model)

### 5.2 Phase 2: Opt-in tier labels

4. Add `tier="cheap"` parameter to mechanical phase callables (extract, nl_to_logic, quality, pl, fol, modal, dung, jtms, atms, aspic, etc.)
5. Verify via logging that tiers resolve correctly

### 5.3 Phase 3: Cost-aware budget

6. Extend `_guarded_chat_completion` to weight calls by tier (cheap = 0.1×, strong = 1.0×)
7. Add `--llm-budget` CLI parameter for explicit budget control

---

## 6. Constraints

| Constraint | Detail |
|-----------|--------|
| **No breaking change** | Default = both tiers resolve to `OPENAI_CHAT_MODEL_ID` |
| **Determinism preserved** | `_get_determinism_params()` must work per resolved model, not just global |
| **Budget guard compatible** | `_guarded_chat_completion` remains the single funnel |
| **OpenRouter compatible** | Tier resolution must work for both OpenAI and OpenRouter paths |
| **Collision guard** | Implementation in `invoke_callables.py` only by po-2025 |

---

## 7. Cross-References

- **LLM acquisition**: `argumentation_analysis/orchestration/invoke_callables.py` (`_get_openai_client`, `_resolve_model_id`, `_get_determinism_params`)
- **Budget guard**: `argumentation_analysis/orchestration/invoke_callables.py` (`_guarded_chat_completion`, `llm_budget_scope`)
- **Spectacular workflow**: `argumentation_analysis/orchestration/workflows.py` (`build_spectacular_workflow()` — 29 phases)
- **Registry**: `argumentation_analysis/orchestration/registry_setup.py` (capability → invoke mapping)
- **Roadmap #78**: GitHub issue #78 (Democratech Phase 2, North-Star parametric integration)
- **Issue #675**: Original OpenRouter toggle (established `create_llm_service` pattern)
