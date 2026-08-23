# run_e2e_tests.py Archive (#1783)

Archived: 2026-08-23 — superseded by nothing; its target was deleted.

## Why

`scripts/orchestration/run_e2e_tests.py` (created `e549ffd0`, 2025-09-25,
"feat: Ajout orchestration E2E asynchrone complète") launched an uvicorn
backend on `services.web_api_from_libs.app:app_asgi`. That module was
deleted on 2026-02-25 by `df031b34` ("refactor(consolidate): migrate
plugins/, archive legacy services/" — #34), which archived the whole
`web_api_from_libs` tree but did not follow this launcher.

For six months the script could only fail: uvicorn dies at import of a
module that no longer exists anywhere in the repo (it survives only in
docs). It was never executed by CI or the gate argv — invisible rot,
exactly the #1783 family.

## Qualification (measured, #1783 dispatch R853)

**Dead-by-design**: the target was deliberately removed (#34); keeping
the launcher cannot resurrect it. No fix exists short of rewriting it
against `api.main:app` — at which point it duplicates
`scripts/run_e2e_backend.py`, which already does exactly that (#1853).

## Related

- Issue #1783 (gate names a fifth of the test tree — invisible rot)
- PR #34 / commit `df031b34` (target deletion)
- PR #1855 (#1853 — live e2e backend launcher on `api.main:app`)
