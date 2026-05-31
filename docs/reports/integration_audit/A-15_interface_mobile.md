# Audit A-15: Interface Mobile

**Issue**: N/A | **SUIVI**: Score 70% | **Date audit**: 2026-05-31

## Status: 🟡 Partial

The mobile interface has a complete API layer and a React Native Expo frontend, but suffers from latent defects in endpoint implementations and test quality issues that mask real bugs.

## What was delivered (student source)

- `3.1.5_Interface_Mobile/` — React Native Expo mobile application
- API contract: `analyzeText`, `validateArgument`, `detectFallacies`, `chat`

## What exists in `argumentation_analysis/` / `api/`

| Layer | File | Detail |
|---|---|---|
| API endpoints | `api/mobile_endpoints.py` | 4 endpoints: `/analyze`, `/fallacies`, `/validate`, `/chat` |
| API registration | `api/main.py:7,52` | `mobile_router` imported and mounted at `/api` prefix |
| Mobile app | `3.1.5_Interface_Mobile/` | React Native Expo application (standalone frontend) |
| Tests | `tests/integration/api/test_openapi_contract.py` | References mobile endpoints (indirect) |

### Endpoint Details

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/mobile/analyze` | POST | Full argument analysis |
| `/api/mobile/fallacies` | POST | Fallacy detection |
| `/api/mobile/validate` | POST | Logical validation (Toulmin model) |
| `/api/mobile/chat` | POST | Chat with AI assistant |

## Preservation Assessment

- API contract: **PRESENT** — All 4 endpoints from the mobile spec are implemented
- Request/response models: **PRESENT** — Pydantic models for all endpoints
- Frontend: **PRESENT** — React Native Expo app in student directory
- Router registration: **PRESENT** — Mounted in FastAPI app at `/api` prefix

## Gap Analysis

### Latent Defects (verified in code)

1. **`/chat` — Wrong call signature**: `create_llm_service()` is called without the required `service_id` parameter. Will raise `TypeError` at runtime instead of returning a chat response.

2. **`/validate` — Toulmin field type mismatch**: The endpoint returns Toulmin model fields as objects (structured data) but the mobile frontend contract expects strings. Type coercion will fail or produce unexpected JSON shapes.

3. **Tests give false confidence**: Tests use broad `try/except` patterns that return HTTP 200 even when the underlying logic raises exceptions. A bug in any endpoint is masked by the test framework — the test passes but the feature is broken.

4. **No real pipeline test**: All tests use mocked services. No integration test exercises the full path from HTTP request through the actual pipeline to response. The latent defects above would be caught immediately by a real pipeline test.

### Integration Gaps

5. **Frontend disconnected from API evolution**: The React Native app in `3.1.5_Interface_Mobile/` has its own API client that may not match the current endpoint signatures (e.g., response field names, error formats).

6. **No WebSocket/SSE streaming**: The `/chat` endpoint is synchronous. A mobile chat experience typically expects streaming responses.

## Recommended Action

**Medium priority.** The 70% score is accurate — the scaffolding is complete but latent defects reduce real usability.

1. **Fix `/chat` call signature** — Add the required `service_id` parameter to `create_llm_service()`
2. **Fix `/validate` type mismatch** — Ensure Toulmin fields are serialized as the mobile contract expects
3. **Fix tests** — Replace broad `try/except` with specific exception assertions. Tests should FAIL when endpoints have bugs.
4. **Add 1 integration test** — Exercise at least `/analyze` and `/chat` with a real (or carefully faked) pipeline to catch signature/type errors.

## Source Files

- `api/mobile_endpoints.py`
- `api/main.py` (lines 7, 52)
- `3.1.5_Interface_Mobile/` (React Native Expo app)
- `tests/integration/api/test_openapi_contract.py`
