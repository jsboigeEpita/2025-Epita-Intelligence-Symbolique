# Design Spec — Track 3: AI Shield Preset Selector (`--shield-preset`)

**Date**: 2026-06-02
**Author**: Claude Code @ myia-po-2023
**Base**: `841ed091` (main, post-hierarchical reactivation)
**Effort**: S (1 session)
**Parent**: `docs/architecture/parametric_integration_map.md` (PR #885)

---

## Verdict

**GO — trivial** — The 4 presets already exist in `services/ai_shield/presets.py`, the registry entry exists, the invoke callable exists, the REST endpoint exists. The only gap is a **CLI argument** and a **workflow phase** to integrate shield as a named pipeline step. This is almost pure wiring.

---

## 1. Current State

### 1.1 Four Presets Already Defined

File: `argumentation_analysis/services/ai_shield/presets.py` (lines 21-81)

| Preset | Layers | Heuristic Threshold | LLM Threshold | Output Threshold | `fail_open` |
|--------|--------|:-------------------:|:-------------:|:----------------:|:-----------:|
| **basic** | Heuristic only | 0.5 | N/A | N/A | configurable |
| **advanced** | Heuristic + LLM + Output | 0.5 | 0.6 | 0.4 | configurable |
| **output_only** | Output only | N/A | N/A | 0.4 | configurable |
| **strict** | All 3, lowest thresholds | 0.3 | 0.4 | 0.3 | always False |

```python
def load_preset(preset_name: str = "basic", api_key=None, fail_open: bool = False) -> Shield:
```

### 1.2 Existing Wiring

| Component | Status | Location |
|-----------|--------|----------|
| Registry entry | ✅ | `registry_setup.py:660` — `ai_shield_service` with capabilities |
| Invoke callable | ✅ | `invoke_callables.py:6118` — `_invoke_ai_shield()` |
| Shared state | ✅ | `shared_state.py:452` — `state.ai_shield_results` |
| REST endpoint | ✅ | `api/shield_endpoints.py` — `POST /api/shield/validate` |
| Auth guard | ✅ | `X-Shield-Token` / `SHIELD_ENDPOINT_TOKEN`, relu **par requête** (rotation à chaud). Sans token la route **refuse de servir** (`503`) sauf opt-in dev explicite `SHIELD_ALLOW_ANONYMOUS=1` — plus de pass-through implicite (#2144) |

### 1.3 Gaps

1. **No CLI argument** — `run_orchestration.py` has no `--shield-preset` flag
2. **No dedicated workflow phase** — Shield is not a named phase in any workflow definition (light/standard/full)
3. **Not in default workflows** — Even `full` workflow doesn't include a shield phase
4. **Invoke callable reads from context only** — `context.get("shield_config", {})` with no CLI propagation

---

## 2. Proposed Design

### 2.1 CLI Integration

```python
# In run_orchestration.py argparse
parser.add_argument(
    "--shield-preset",
    type=str,
    choices=["off", "basic", "advanced", "output_only", "strict"],
    default="off",
    help="AI Shield preset: off (default, no shield), "
         "basic (heuristic only, no LLM cost), "
         "advanced (heuristic+LLM+output filter), "
         "output_only (post-LLM filtering only), "
         "strict (all layers, lowest thresholds, fail-closed)",
)
```

**Usage examples:**
```bash
# No shield (default, unchanged behavior)
python run_orchestration.py --file text.txt

# Basic shield — heuristic only, zero LLM cost
python run_orchestration.py --file text.txt --shield-preset basic

# Full protection
python run_orchestration.py --text "..." --shield-preset advanced

# Post-LLM output filtering only
python run_orchestration.py --file text.txt --shield-preset output_only

# Maximum security (fail-closed)
python run_orchestration.py --file text.txt --shield-preset strict
```

### 2.2 Pipeline Integration

**Option A — Named workflow phase (recommended)**:

Add a `"shield"` phase to workflow definitions, placed as the **first** phase (before extraction):

```python
# workflow_dsl.py or unified_pipeline.py
WorkflowBuilder("standard_with_shield")
    .add_phase(name="shield", capability="input_validation", optional=True)
    .add_phase(name="extract", capability="argument_extraction", depends_on=["shield"])
    .add_phase(name="quality", capability="quality_evaluation", depends_on=["extract"])
    ...
```

**Option B — Context-driven invocation (simpler, recommended for v1)**:

Pass preset through context dict; the existing `_invoke_ai_shield()` callable already reads it:

```python
# run_orchestration.py
if args.shield_preset != "off":
    context["shield_config"] = {
        "preset": args.shield_preset,
        "fail_open": args.shield_preset != "strict",  # strict = fail-closed
    }
```

Then add a `shield` phase to the workflow builder when context contains shield_config.

**Chosen approach**: Option B for v1 (minimal LOC, no workflow restructuring). Option A is a follow-up.

### 2.3 Default Behavior (No Breaking Change)

- `--shield-preset off` (default) → no shield phase runs, identical to current behavior
- Only when user explicitly sets `--shield-preset basic|advanced|...` does the shield invoke
- `fail_open=True` by default → if shield fails to load (missing deps, no API key), pipeline continues

### 2.4 API Integration

Add `shield_preset` parameter to existing analysis endpoint:

```python
@router.post("/api/v1/agents/full-analysis")
async def full_analysis(
    text: str,
    workflow: str = "standard",
    fallacy_tier: str = "llm",
    shield_preset: str = Query("off", regex="^(off|basic|advanced|output_only|strict)$"),
):
    context = {
        "fallacy_tier": fallacy_tier,
        "shield_config": {"preset": shield_preset} if shield_preset != "off" else {},
    }
```

### 2.5 Security Considerations

- **`basic` preset**: Zero LLM cost. Heuristic-only. Safe for CI.
- **`advanced`/`strict`**: Call LLM for validation → API cost. `strict` has `fail_open=False` → blocks on error.
- **`SHIELD_ENDPOINT_TOKEN`**: Existing auth guard on REST endpoint, read **per request** (hot rotation). CLI bypasses this (local execution).
- **`SHIELD_ALLOW_ANONYMOUS`**: Explicit dev opt-in. Without it, an unset `SHIELD_ENDPOINT_TOKEN` makes the route **refuse to serve** (`503`) instead of passing through — a deployment that forgets the token is closed, not open (#2144).
- **Privacy**: Shield's `OutputFilterLayer` checks for credential/PII leaks in LLM responses — complementary to existing `_scrub_state_for_export`.

---

## 3. Implementation Plan

| Step | File | Change | LOC |
|------|------|--------|-----|
| 1 | `run_orchestration.py` | Add `--shield-preset` argument + context propagation | ~8 |
| 2 | `unified_pipeline.py` | Add conditional shield phase to workflow builders | ~15 |
| 3 | `api/` | Add `shield_preset` to analysis endpoint | ~5 |
| 4 | Tests | Unit tests for preset propagation + shield-off default | ~40 |
| **Total** | | | **~68 LOC** |

---

## 4. Testing Plan

| Test | What | API Key? |
|------|------|----------|
| `test_shield_preset_off` | Default = no shield phase in context | No |
| `test_shield_preset_basic` | `--shield-preset basic` → context has preset, no LLM needed | No |
| `test_shield_preset_strict` | `--shield-preset strict` → fail_open=False in context | No |
| `test_shield_preset_cli_parse` | argparse accepts all 5 values | No |
| `test_shield_preset_invalid` | Invalid preset → argparse error | No |
| `test_shield_invoke_with_preset` | `_invoke_ai_shield()` reads preset from context | Yes (optional) |

---

## 5. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Shield LLM layer adds cost | Expected | Default is `off`; `basic` is zero-cost |
| `strict` blocks legitimate input | Possible | Default `fail_open=True` for all except `strict`; user explicitly chooses |
| Shield depends on `ai_shield` package | Low | `try/except ImportError` already in invoke callable; `fail_open=True` default |
| Privacy scrub overlap | None | Shield checks LLM output; `_scrub_state_for_export` checks exported state — complementary |

---

## 6. DoD

- [ ] `--shield-preset` CLI argument with 5 choices (off/basic/advanced/output_only/strict)
- [ ] Default = `off` (no change to current behavior)
- [ ] Context propagation to pipeline invoke callable
- [ ] Shield phase conditionally added to workflow when preset ≠ off
- [ ] API endpoint accepts `shield_preset` parameter
- [ ] 5+ tests passing
- [ ] `## À valider par l'utilisateur`: Default choice (off vs basic)

---

## À valider par l'utilisateur

1. **Default**: `off` (no shield, zero overhead) or `basic` (heuristic guard always on, zero LLM cost)?
2. **Shield in `full` workflow**: Should the `full` workflow always include shield (as `basic`), or keep it opt-in?
