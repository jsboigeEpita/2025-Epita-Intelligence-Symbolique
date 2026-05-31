# Audit A-10: LLMs Locaux

**Issue**: #35 | **SUIVI**: Score 80% | **Date audit**: 2026-05-31

## Status: 🟡 Partial

## What was delivered (student source)

Student project `2.3.6_local_llm/` delivered a local LLM service adapter designed to work with OpenAI-compatible HTTP endpoints (vLLM, Ollama, etc.). The system provides a unified interface for chat completion requests against locally-hosted models, with the stated goal of enabling fallacy detection and argumentation analysis without depending on external API providers.

Key claims in the student deliverable:
- Multi-backend support (vLLM, Ollama, LM Studio, etc.)
- Local fallacy detection endpoint
- ServiceDiscovery-compatible registration
- Chat completion via OpenAI-compatible HTTP API

## What exists in argumentation_analysis/

### Service adapter

- **`services/local_llm_service.py`** — `LocalLLMService` class implementing an async HTTP adapter using `httpx` for OpenAI-compatible endpoints. Provides `chat_completion()` and related methods.

### Registration

- **`registry_setup.py:207-222`** — `local_llm_service` registered in `CapabilityRegistry` with capabilities `["local_llm", "chat_completion"]`.

### Tests

- **`test_local_llm_service.py`** — 11 tests covering connection, completion, error handling, and fallback behavior.

## Preservation Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| HTTP adapter | **Preserved** | OpenAI-compatible HTTP via httpx, async support added |
| Chat completion | **Preserved** | Core request/response flow intact |
| ServiceDiscovery | **Partially preserved** | Compatible, but auto-registration not wired by default |
| Multi-backend | **Emergent only** | All backends speak OpenAI HTTP — no backend-specific logic |
| Fallacy detection | **Not surfaced** | Student endpoint not exposed as registry capability |
| Capability names | **Mismatch** | Registry: "local_llm", tests: "local_llm_inference" |

## Gap Analysis

### Gap 1: Multi-backend claim is emergent, not implemented

The student project claimed support for vLLM, Ollama, LM Studio, etc. In practice, the adapter sends standard OpenAI HTTP requests. This works because all listed backends implement the OpenAI chat completion API — but there are no backend-specific connection tests, configuration profiles, or validated endpoints. The "multi-backend" property is emergent from the protocol, not from implemented code.

**Impact**: Low. In practice, any OpenAI-compatible endpoint works. But there are no integration tests validating vLLM or Ollama specifically.

### Gap 2: Fallacy detection endpoint not surfaced

The student project included a fallacy-detection-specific endpoint or prompt chain. This has not been surfaced as a registered capability in the `CapabilityRegistry`. Consumers cannot discover or invoke "local fallacy detection" as a distinct service.

**Impact**: Medium. The service is registered as generic `chat_completion` but its argumentation-specific value proposition is invisible to the Lego Architecture.

### Gap 3: ServiceDiscovery auto-registration not wired by default

The `LocalLLMService` is `ServiceDiscovery`-compatible in design but does not self-register into `ServiceDiscovery` during bootstrap. Users must manually wire the registration.

**Impact**: Low. Can be added in a follow-up PR if needed.

### Gap 4: Capability name mismatch

The registry registers capability `"local_llm"` but tests reference `"local_llm_inference"`. This is a naming inconsistency that could cause lookup failures if a consumer searches for one name but the other is registered.

**Impact**: Low. Both names should work, or one should be canonicalized.

## Recommended Action

1. **Canonicalize capability names** — Align registry and tests on a single name (prefer `"local_llm"` as it is shorter and already in the registry).
2. **Surface fallacy detection** — Add a `local_fallacy_detection` capability to the registry entry, or expose a dedicated `@kernel_function` in a plugin wrapping the local LLM with a fallacy-detection prompt.
3. **Wire ServiceDiscovery** — Add auto-registration in `registry_setup.py` or `bootstrap.py`.
4. **Add backend validation tests** — At minimum, document which backends have been tested and which are theoretical.

## Source Files

| File | Role |
|------|------|
| `argumentation_analysis/services/local_llm_service.py` | LocalLLMService adapter |
| `argumentation_analysis/core/capability_registry.py` | Registry (registration at lines 207-222) |
| `tests/.../test_local_llm_service.py` | 11 tests |
| `2.3.6_local_llm/` | Student project source (reference) |
