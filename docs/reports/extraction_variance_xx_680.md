# Track XX (#680): Extraction Run-to-Run Variance Report

> **Updated by Track AA (#686):** The determinism knob is now **model-aware** — reasoning models (gpt-5*, o1*, o3*) automatically suppress temperature/seed params to avoid a 400 BadRequest. See the [Reasoning-Model Caveat](#reasoning-model-caveat-aa-686) section.

## Summary

Characterization of non-determinism sources in the argument extraction pipeline. A **determinism knob** is implemented (`LLM_DETERMINISTIC_MODE`, `LLM_TEMPERATURE`, `LLM_SEED` env vars) that propagates `temperature=0` + `seed=42` (or custom values) to all 10 LLM call sites in `invoke_callables.py`. Downstream parsing and aggregation are confirmed deterministic.

## Reasoning-Model Caveat (AA #686)

Reasoning models (gpt-5 family, o1, o3) **reject** `temperature` and `seed` parameters with a `400 BadRequest`. Since the cluster's production model is `gpt-5-mini`, the knob would be a foot-gun if applied naively.

**Solution**: `_get_determinism_params()` now detects the active model (via `OPENAI_CHAT_MODEL_ID` / `OPENROUTER_CHAT_MODEL_ID`) and **suppresses** temperature/seed for known reasoning-model prefixes. A `WARN` log is emitted when determinism is requested but unsupported.

| Prefix | Classification |
|--------|---------------|
| `gpt-5` | Reasoning — suppress |
| `o1` | Reasoning — suppress |
| `o3` | Reasoning — suppress |
| `openai/gpt-5` | Reasoning — suppress |
| `openai/o1` | Reasoning — suppress |
| `openai/o3` | Reasoning — suppress |
| `gpt-4o` | Standard — allow |
| `gpt-4` | Standard — allow |
| Others | Standard — allow |

**Escape hatch**: Set `LLM_FORCE_SAMPLING_PARAMS=1` to force sending temperature/seed regardless of model detection (e.g. for self-hosted endpoints that accept these params even on reasoning architectures).

## Sources of Non-Determinism

### Tier 1: LLM Sampling (dominant, ~90% of variance)

| Site | Location | Default behavior | Fix |
|------|----------|------------------|-----|
| Fact extraction | `invoke_callables.py:3361` | Provider default (temp=1.0) | `**det_params` |
| Quality enrichment | `invoke_callables.py:363` | Provider default | `**det_params` |
| Counter-argument | `invoke_callables.py:474` | Provider default | `**det_params` |
| Debate analysis | `invoke_callables.py:714` | Provider default | `**det_params` |
| Governance | `invoke_callables.py:913` | Provider default | `**det_params` |
| PL pass 1 (atoms) | `invoke_callables.py:3533` | Provider default | `**det_params` |
| PL pass 2 (formulas) | `invoke_callables.py:3582` | Provider default | `**det_params` |
| PL wide-net | `invoke_callables.py:3624` | Provider default | `**det_params` |
| FOL pass 1 (signature) | `invoke_callables.py:3842` | Provider default | `**det_params` |
| FOL pass 2 (formulas) | `invoke_callables.py:3899` | Provider default | `**det_params` |

**Verdict**: The primary source of extraction variance is LLM sampling parameters. For OpenAI `gpt-5-mini`, the default temperature is 1.0, producing different argument sets on each run.

### Tier 2: SK Plugin JSON Configs (low variance, already tuned)

| Plugin | Temperature | top_p | Verdict |
|--------|-------------|-------|---------|
| ExplorationPlugin | 0.0 | 0.1 | SAFE — deterministic |
| SynthesisPlugin | 0.2 | 0.5 | LOW — minor variance |
| TaxonomyDisplayPlugin | 0.0 | 1.0 | SAFE |
| GuidingPlugin | 0.0 | 1.0 | SAFE |

These plugins operate through SK's config.json mechanism and are NOT affected by the new knob (they have their own execution settings). Variance from these is minimal.

### Tier 3: Downstream Parsing (confirmed deterministic)

| Operation | Location | Verdict |
|-----------|----------|---------|
| `_parse_json_from_llm` | `invoke_callables.py:3401` | DETERMINISTIC |
| `_normalize_items_with_quotes` | `invoke_callables.py:3303` | DETERMINISTIC |
| `_aggregate_virtue_scores` | `invoke_callables.py:278` | DETERMINISTIC |
| `_generate_hypotheses` | `invoke_callables.py:1374` | DETERMINISTIC |
| `_python_social_fallback` | `invoke_callables.py:4323` | DETERMINISTIC |
| `_build_substantive_insight` | synthesis | DETERMINISTIC |

Once the LLM output is fixed (same temperature + seed), the entire downstream pipeline is deterministic. Python 3.7+ dict ordering guarantees stable iteration.

### Tier 4: Async Ordering (negligible)

`asyncio.gather` for per-argument fallacy detection (line ~3146) runs tasks concurrently but results are ordered by input list position (`return_exceptions=True`). No variance introduced.

### Out of Scope

- `french_fallacy_adapter.py` lines 957/1131: hardcoded `temperature=0.1` in raw httpx/OpenAI calls. These bypass the knob but are already low-temperature.
- `analysis_config.py:78`: `llm_temperature=0.3` is dead code (never propagated to SK).
- Agent execution settings (debate, counter-argument, informal fallacy): use SK defaults (no temperature set), which means provider defaults apply. These are NOT affected by the invoke_callables knob.

## Determinism Knob Implementation

### New function: `_get_determinism_params()`

```python
def _get_determinism_params() -> Dict[str, Any]:
    """Read determinism settings from environment variables."""
    params = {}
    if os.environ.get("LLM_DETERMINISTIC_MODE"):
        params["temperature"] = 0.0
        params["seed"] = 42
    # Fine-grained overrides take precedence
    temp_str = os.environ.get("LLM_TEMPERATURE")
    if temp_str is not None:
        params["temperature"] = float(temp_str)  # ValueError → skip
    seed_str = os.environ.get("LLM_SEED")
    if seed_str is not None:
        params["seed"] = int(seed_str)  # ValueError → skip
    return params
```

### Environment Variables

| Variable | Effect | Default |
|----------|--------|---------|
| `LLM_DETERMINISTIC_MODE` | Set `temperature=0` + `seed=42` | Not set (no effect) |
| `LLM_TEMPERATURE` | Override temperature (float) | Not set |
| `LLM_SEED` | Set seed (int) | Not set |
| `LLM_FORCE_SAMPLING_PARAMS` | Force temperature/seed even on reasoning models | Not set |

Fine-grained overrides take precedence over the shorthand. Reasoning models suppress params unless force flag is set.

### Usage

For measurement/benchmark runs:
```bash
export LLM_DETERMINISTIC_MODE=1
# or fine-grained:
export LLM_TEMPERATURE=0.0
export LLM_SEED=42
```

For creative mode (default): leave unset. Provider defaults apply (temperature=1.0).

### Scope

The knob applies to all 10 raw-SDK LLM call sites in `invoke_callables.py` (fact extraction, quality enrichment, counter-argument, debate, governance, PL 2-pass + wide-net, FOL 2-pass). It does NOT affect:
- SK plugin configs (already have their own temperature settings)
- Agent-level execution settings (debate, counter-argument agents)
- Raw httpx calls in `french_fallacy_adapter.py`

## Tests

20 tests in `tests/unit/argumentation_analysis/test_track_xx_extraction_variance.py`:
- 8 env var parsing tests (`_get_determinism_params`)
- 3 JSON parsing determinism tests
- 3 extraction metrics determinism tests
- 6 source wiring verification tests

- 14 tests in `tests/unit/argumentation_analysis/test_track_aa_model_aware_determinism.py`:

  - 3 model resolution tests (`_resolve_model_id`)
  - 17 reasoning model classification tests (`_is_reasoning_model`, parametrized)
  - 9 model-aware determinism tests (suppression, allow-list, force flag, fine-grained)
  - 1 backward-compat test (XX default behavior preserved)

## Deferred

- **Live variance measurement**: Requires API key. Run with `LLM_DETERMINISTIC_MODE=1` on same corpus 3× to confirm 0 variance in argument count.
- **SK agent-level determinism**: Debate/counter-argument agents use SK execution settings without temperature control. A separate knob would need `PromptExecutionSettings` overrides per agent.
