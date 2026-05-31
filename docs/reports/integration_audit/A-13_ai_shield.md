# Audit A-13: AI Shield

**Issue**: #166 (CLOSED) | **SUIVI**: Score 0% (original not submitted) → recreated | **Date audit**: 2026-05-31

## Status: 🟡 Partial

The AI Shield was recreated from soutenance description after the original student project was not submitted (0%). Issue #166 is CLOSED. The service is complete and tested but operates as a standalone service — it is NOT wired into `UnifiedPipeline` as middleware.

## What was delivered (student source)

**Nothing.** The original student project was not submitted (0% score). The existing implementation was recreated from the soutenance description.

## What exists in `argumentation_analysis/`

| Layer | File | LOC | Detail |
|---|---|---|---|
| Core | `services/ai_shield/shield.py` | 192 | `Shield` orchestrator + `ShieldLayer` ABC + `LayerResult` dataclass |
| Heuristic layer | `services/ai_shield/layers/heuristic.py` | 146 | Regex/keyword validation for prompt injection, PII leaks |
| LLM validator | `services/ai_shield/layers/llm_validator.py` | 119 | LLM-based jailbreak/bias/toxicity detection |
| Output filter | `services/ai_shield/layers/output_filter.py` | 151 | Output leak prevention (secrets, internal state) |
| Presets | `services/ai_shield/presets.py` | 80 | Pre-configured shield profiles: `basic`, `advanced`, `output_only`, `strict` |
| Init | `services/ai_shield/__init__.py` | — | Package exports |
| Tests | `tests/unit/argumentation_analysis/test_ai_shield.py` | — | 33 tests, all passing |

**Total**: ~688 LOC across 5 source files.

## Preservation Assessment

- Layer architecture: **PRESENT** — ABC `ShieldLayer` with pluggable layers
- Heuristic validation: **PRESENT** — regex patterns for injection/PII detection
- LLM-based validation: **PRESENT** — jailbreak, bias, toxicity via LLM
- Output filtering: **PRESENT** — secret/redaction filtering
- Presets: **PRESENT** — 4 pre-configured security profiles
- Tests: **PRESENT** — 33 unit tests with full coverage

## Gap Analysis

1. **NOT wired into UnifiedPipeline** — The shield is a standalone service. There is no middleware hook in `UnifiedPipeline` or `invoke_callables.py` that routes input/output through the shield. It must be called manually.
2. **No registry entry** — The shield is NOT registered in `registry_setup.py`. No capability discovery path exists.
3. **No API endpoint** — No REST route exposes the shield. It can only be used programmatically.
4. **No orchestration integration** — The `router.py` does not include a `shield` or `security_check` capability in any workflow.

## Recommended Action

**Medium priority.** The shield is well-implemented and tested but needs a single integration point to become useful:

1. Add a `security_check` capability to `registry_setup.py` pointing to the shield
2. Add an optional `_invoke_ai_shield` callable in `invoke_callables.py`
3. Add a `shield_check` phase to the `full` workflow (or make it a pre/post middleware)
4. Expose a `/api/shield/validate` endpoint for direct API access

Alternatively, document that the shield is an opt-in service for deployments that need input/output security hardening.

## Source Files

- `argumentation_analysis/services/ai_shield/shield.py`
- `argumentation_analysis/services/ai_shield/layers/heuristic.py`
- `argumentation_analysis/services/ai_shield/layers/llm_validator.py`
- `argumentation_analysis/services/ai_shield/layers/output_filter.py`
- `argumentation_analysis/services/ai_shield/presets.py`
- `tests/unit/argumentation_analysis/test_ai_shield.py`
