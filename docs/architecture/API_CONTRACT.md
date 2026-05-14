# API Contract Testing

## Overview

The OpenAPI contract test (`tests/integration/api/test_openapi_contract.py`) protects against breaking API changes by comparing the live OpenAPI spec against a committed snapshot.

## Snapshot File

`api/openapi.snapshot.json` — committed, deterministic OpenAPI spec generated from the FastAPI app with sorted paths and schemas.

## How It Works

1. Test boots the FastAPI app via `TestClient` (JPype mocked, no JVM needed)
2. Fetches `/openapi.json` from the live app
3. Diffs against `api/openapi.snapshot.json`
4. **Fails on**: removed paths, removed HTTP methods, removed/changed required parameters, removed required request body fields
5. **Allows**: new endpoints, new methods, new optional params, new schemas

## When to Regenerate

Run the regeneration script when you **intentionally** change the API:

```bash
python scripts/api/regenerate_openapi_snapshot.py
git add api/openapi.snapshot.json
```

Typical triggers:
- Added a new endpoint
- Removed a deprecated endpoint
- Changed parameter names/types
- Added/removed request body fields

## CI Integration

The contract test runs in CI as part of `pytest tests/integration/api/`. If it fails, either:
1. The change was unintentional — fix the code
2. The change was intentional — regenerate the snapshot and commit it

## Architecture

```
api/openapi.snapshot.json          ← committed baseline
scripts/api/regenerate_openapi_snapshot.py  ← regeneration tool
tests/integration/api/test_openapi_contract.py  ← 6 contract tests
```
