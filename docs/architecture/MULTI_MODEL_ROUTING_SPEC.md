# Multi-Model Routing Design Specification

**Issue**: #988 — Roadmap #78 Phase 2, North-Star parametric integration
**Scope**: Design spec only. No code changes to `invoke_callables.py` (collision guard: po-2025 owns that file's logic).
**Purpose**: Define how per-phase model tier routing should work so that cheap mechanical phases (extraction, NL-to-logic) can use a cheaper model while reasoning-heavy phases (synthesis, governance, debate) use a strong model — reducing cost on repeated Phase 4 integral runs.

**Status**: Design spec (v2 — reviewer concerns reconciled) — awaiting implementation in a future sprint by the owner of `invoke_callables.py`.

---

## 0. Reviewer Concerns Reconciliation (R367)

Seven concerns were raised during review of v1. Each is addressed below with a cross-reference to the spec section where the fix is applied.

| # | Concern | Resolution | Spec section |
|---|---------|-----------|--------------|
| 1 | Phase count 29 vs 26 — 3 phases unclassified | Added `fol_solver`, `modal_solver`, `synthesis` to §2.3 table. All 29 phases now classified. | §2.3 |
| 2 | Cost projection weight 0.1 inflates savings ×10 | Replaced with realistic token-ratio estimate based on actual model pricing. Savings now estimated at 33% (not 56%). Labelled "estimation conceptuelle" explicitly. | §2.3, §4.2 |
| 3 | OpenRouter priority chain asymmetric with existing pattern | Aligned to mirror existing `_resolve_model_id()` precedence: `OPENROUTER_*` vars take priority over `LLM_MODEL_*` when on OpenRouter. See §2.2 revised chains. | §2.2 |
| 4 | `stakes_extraction` classified `strong` but is extraction | Reclassified to `cheap` (structured extraction, not generative reasoning). | §2.3 |
| 5 | Invalid tier string → silent `None` fallback | Added explicit `ValueError` with log warning for unknown tier values. | §2.4.A |
| 6 | OpenRouter test path gap | Added `test_openrouter_tier_priority` to §3.1 test table. | §3.1 |
| 7 | Phase 3 cost-aware budget underspecified | Added §5.3 detail: separate counters, threshold interaction, weight formula. | §5.3 |

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

**Resolution priority** (OpenAI path):
```
cheap model  = LLM_MODEL_CHEAP  || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
strong model = LLM_MODEL_STRONG || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
```

**Resolution priority** (OpenRouter path — mirrors existing `_resolve_model_id()` precedence):
```
cheap model  = OPENROUTER_MODEL_CHEAP  || OPENROUTER_CHAT_MODEL_ID || LLM_MODEL_CHEAP  || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
strong model = OPENROUTER_MODEL_STRONG || OPENROUTER_CHAT_MODEL_ID || LLM_MODEL_STRONG || OPENAI_CHAT_MODEL_ID || "gpt-5-mini"
```

> **Design rationale (Concern 3)**: The OpenRouter chain preserves the existing invariant that `OPENROUTER_CHAT_MODEL_ID` takes priority over `OPENAI_CHAT_MODEL_ID` when on the OpenRouter provider. The new `OPENROUTER_MODEL_CHEAP`/`OPENROUTER_MODEL_STRONG` vars sit above `OPENROUTER_CHAT_MODEL_ID` (per-provider overrides), while `LLM_MODEL_CHEAP`/`LLM_MODEL_STRONG` sit below (provider-agnostic fallbacks). This avoids the v1 asymmetry where `LLM_MODEL_CHEAP` would have silently overridden a user's `OPENROUTER_CHAT_MODEL_ID`.

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
| `synthesis` | `analysis_synthesis` | `strong` | Terminal synthesis with interpretation |
| `deep_synthesis` | `deep_synthesis` | `strong` | 9-section grounded report generation |
| `stakes` | `stakes_extraction` | `cheap` | Structured extraction (stakeholder identification, not generative reasoning) |
| `pl` | `propositional_logic` | `cheap` | Tweety SAT solving (algorithmic) |
| `fol` | `fol_reasoning` | `cheap` | Tweety FOL reasoning (algorithmic) |
| `fol_solver` | `external_fol_solving` | `cheap` | External prover invocation (EProver/Prover9 wrapper) |
| `modal` | `modal_logic` | `cheap` | Tweety modal reasoning (algorithmic) |
| `modal_solver` | `external_modal_solving` | `cheap` | External modal solver invocation (SPASS wrapper) |
| `tweety_interpretation` | `formal_result_interpretation` | `cheap` | Formula→NL translation |
| `belief_revision` | `belief_revision` | `cheap` | Dalal/Levi distance (algorithmic) |
| `probabilistic` | `probabilistic_argumentation` | `cheap` | Probability computation |
| `ranking` | `ranking_semantics` | `cheap` | Ranking computation |
| `bipolar` | `bipolar_argumentation` | `cheap` | Support+attack framework |
| `neural_detect` | `neural_fallacy_detection` | `cheap` | NLP model inference (no reasoning) |

**Tier summary**: 19 `cheap` + 10 `strong` = **29 phases** (matches `build_spectacular_workflow()` output exactly).

> **Change log (Concern 1)**: Added `fol_solver`, `modal_solver`, `synthesis` — the 3 phases present in `build_spectacular_workflow()` but missing from v1 table.
>
> **Change log (Concern 4)**: `stakes_extraction` reclassified from `strong` to `cheap`. Rationale: the phase performs structured extraction of stakeholder positions from argument text, not generative reasoning. The "stakes" label suggests reasoning, but the implementation is extraction.

### 2.4 Implementation Pattern

The following changes are scoped to `invoke_callables.py` (owned by po-2025):

#### A. New resolver function

```python
_VALID_TIERS = {"cheap", "strong"}

def _resolve_model_for_tier(tier: str = "strong") -> str:
    """Resolve model id for a given tier.

    Falls back to OPENAI_CHAT_MODEL_ID when no tier-specific override is set,
    preserving current single-model behaviour.
    """
    base_model = _resolve_model_id()  # existing function

    if tier not in _VALID_TIERS:
        logger.warning(
            "Unknown tier %r; expected one of %s. Falling back to base model %s.",
            tier, _VALID_TIERS, base_model,
        )
        return base_model

    tier_model = None
    if tier == "cheap":
        tier_model = os.environ.get("LLM_MODEL_CHEAP")
        if os.environ.get("OPENROUTER_BASE_URL") and os.environ.get("OPENROUTER_API_KEY"):
            tier_model = tier_model or os.environ.get("OPENROUTER_MODEL_CHEAP")
    elif tier == "strong":
        tier_model = os.environ.get("LLM_MODEL_STRONG")
        if os.environ.get("OPENROUTER_BASE_URL") and os.environ.get("OPENROUTER_API_KEY"):
            tier_model = tier_model or os.environ.get("OPENROUTER_MODEL_STRONG")

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
| `test_openrouter_tier_priority` | When `OPENROUTER_BASE_URL` + `OPENROUTER_API_KEY` set: `OPENROUTER_MODEL_CHEAP` takes priority over `OPENROUTER_CHAT_MODEL_ID`, which takes priority over `LLM_MODEL_CHEAP` |
| `test_invalid_tier_logs_warning` | `_resolve_model_for_tier("unknown")` logs warning and falls back to base model |

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

### 4.2 With Tiered Routing (estimation conceptuelle)

> **Note (Concern 2)**: The following savings estimate uses real token-pricing ratios rather than an arbitrary 0.1 weight. It is still an estimation conceptuelle — actual savings depend on prompt/output token distribution per phase, which varies by source text.

Cheap tier could use `gpt-4.1-mini` at ~$0.10/1M input tokens (~33% cheaper than `gpt-5-mini`):
- 19 cheap phases × ~0.67× cost + 10 strong phases × 1.0× cost
- Estimated effective cost: (19 × 0.67 + 10 × 1.0) / 29 ≈ **0.77× current** (~23% reduction)
- With more aggressively cheaper models (e.g. `gpt-4.1-mini` at half the token cost of `gpt-5-mini`): ~33% reduction
- Meaningful at scale (100+ runs for benchmarking, Phase 4 corpus_A/B/C × variations)

> The v1 projection of "56% reduction" used a conceptual weight of 0.1 for cheap phases, which implied a 10× cost difference between tiers. Actual tier differences for OpenAI models are typically 1.5-3×, not 10×. The revised estimate of 23-33% is more realistic.

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

6. Extend `_guarded_chat_completion` to weight calls by tier
7. Add `--llm-budget` CLI parameter for explicit budget control

**Cost-aware budget interaction (Concern 7 detail)**:

The current budget guard (`_guarded_chat_completion`, line 312) uses a simple call-count circuit breaker: each call increments a counter, and if it exceeds `LLM_BUDGET_MAX_CALLS` (default 100), further calls are rejected. It does not distinguish between expensive and cheap calls.

With tiering, the budget should become cost-weighted:

```python
TIER_WEIGHTS = {"cheap": 0.67, "strong": 1.0}

async def _guarded_chat_completion(messages, *, tier="strong", ...):
    weight = TIER_WEIGHTS.get(tier, 1.0)
    budget_state["cost_units"] += weight
    if budget_state["cost_units"] > budget_state["max_cost_units"]:
        raise BudgetExhausted(...)
    # ... rest of existing logic ...
```

**Interaction with existing call-count breaker**:
- The existing `LLM_BUDGET_MAX_CALLS` hard limit (count-based) is **preserved** as a safety cap — no amount of cheap calls should exceed it.
- The new `LLM_BUDGET_MAX_COST_UNITS` (default = `LLM_BUDGET_MAX_CALLS`, preserving parity) is the cost-weighted limit.
- Both limits are checked: `if call_count > MAX_CALLS or cost_units > MAX_COST_UNITS`.
- A cheap call counts as `1` call (for the hard cap) and `0.67` cost-units (for the budget).
- This ensures the budget is never exceeded even if all calls are strong, while still rewarding cheap calls with proportional savings.

**Configuration**:
```bash
LLM_BUDGET_MAX_CALLS=100       # Hard cap (existing, unchanged)
LLM_BUDGET_MAX_COST_UNITS=100  # Cost-weighted cap (new, defaults to MAX_CALLS for parity)
LLM_BUDGET_TIER_WEIGHT_CHEAP=0.67  # Weight for cheap tier (new)
```

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
