# Audit: services/web_api/ Root Directory — Epic #317 PR 5

**Date:** 2026-04-09
**Issue:** #322
**Author:** Claude Code (myia-po-2025)

## Executive Summary

Root `services/web_api/` and `argumentation_analysis/services/web_api/` are **NOT duplicates**. They serve fundamentally different purposes:

| Location | Purpose | Technology |
|----------|---------|------------|
| `services/web_api/` | Frontend + management infrastructure | React build, Flask legacy, management scripts |
| `argumentation_analysis/services/web_api/` | Backend API service | Flask + Pydantic models, routes, business logic |

## Critical Finding: STATIC_FILES_DIR is Load-Bearing

`interface_web/app.py:92-94` mounts React static files:

```python
STATIC_FILES_DIR = PROJECT_ROOT / "services" / "web_api" / "interface-web-argumentative" / "build"
# ...
app.mount("/", StaticFiles(directory=str(STATIC_FILES_DIR), html=True), name="static_assets")
```

- The `build/` directory **exists on disk** but is **NOT tracked in git** (0 files in `git ls-files`)
- `node_modules/` is gitignored
- Build script: `react-scripts build` (standard Create React App)
- **Implication**: Fresh clone will NOT have the React build → web app broken until `npm run build` is executed

## File Inventory

### Root `services/` — 6 subdirectories (78 tracked files)

| Subdirectory | Files | Tracked | Status |
|---|---|---|---|
| `web_api/interface-web-argumentative/` | ~38K (incl node_modules + build) | 63 (source only) | **LOAD-BEARING** — React frontend |
| `web_api/interface-simple/` | 8 | 8 | Legacy Flask app |
| `web_api/` (scripts + tests + PNGs) | 15 | 7 | Management infrastructure |
| `web_api_from_libs/` | 11 | 0 | Unknown origin |
| `data/` | 0 | 0 | Empty |
| `informal_analysis_service/` | 2 | 0 | Stale __pycache__ |
| `mcp_server/` | 2 | 0 | Stale __pycache__ |
| `results/` | 0 | 0 | Empty |

### Key Files in `services/web_api/`

#### Management Scripts (5 files)
| Script | Status | Dependencies |
|--------|--------|---|
| `start_full_system.py` | Functional | `scripts.apps.webapp.UnifiedWebOrchestrator` |
| `start_simple_only.py` | Functional | Flask, `interface-simple/` |
| `stop_all_services.py` | Functional | psutil |
| `health_check.py` | Functional | aiohttp, psutil |
| `trace_analyzer.py` | In tests/ dir | Playwright traces |

#### Tests (3 files)
| Test | Location | Status |
|------|----------|--------|
| `test_management_scripts.py` | `services/web_api/` | Functional, uses PROJECT_ROOT |
| `test_interface_simple_playwright.py` | `services/web_api/` | Playwright e2e |
| `test_interfaces_integration.py` | `services/web_api/` | Integration test |

#### PNGs (7 files, ~2.1 MB)
`test_analysis_results.png`, `test_before_analysis.png`, `test_error_handling.png`, `test_examples.png`, + 3 more

#### `interface-simple/` (Flask legacy)
- `app.py` — Standalone Flask app with Bootstrap UI
- `templates/index.html` — HTML template
- 4 test files (`test_api_validation.py`, `test_fallacy_detection.py`, `test_integration.py`, `test_webapp.py`)
- Uses its own analysis service, independent of ServiceManager

### `argumentation_analysis/services/web_api/` (backend API)
- `app.py` (1.5KB) — Flask app factory
- `asgi.py` — ASGI wrapper
- `flask_routes.py` — Flask route definitions
- `routes/` — API endpoint handlers
- `services/` — Business logic
- `models/` — Pydantic models
- `tests/` — Full test suite (4 test files)
- `start_api.py` — API launcher
- Referenced by 23 files across the codebase

## Dependency Analysis

### Who imports from root `services/`?
- `interface_web/app.py` — `ServiceManager` from `argumentation_analysis.orchestration.service_manager` (NOT from root services/)
- Root `services/__init__.py` — makes it a Python package but nothing imports from it directly
- `speech-to-text/` — imports from its own local `services/` (not root)

### Who uses `STATIC_FILES_DIR`?
- Only `interface_web/app.py:92-94` and `:380-381`
- No other references in the codebase

### Are management scripts referenced externally?
- `start_full_system.py` uses `UnifiedWebOrchestrator` (exists at `scripts/apps/webapp/`)
- Scripts are standalone entry points, not imported by other code

## Verdict Per File Category

| Category | Verdict | Action |
|----------|---------|--------|
| `interface-web-argumentative/build/` | **KEEP IN PLACE** | Document in CLAUDE.md. Add build instructions. |
| `interface-web-argumentative/src/` | **KEEP** | React source code |
| `interface-simple/` | **ARCHIVE** | Legacy Flask, superseded by Starlette interface_web |
| Management scripts (5) | **EVALUATE** | `start_full_system.py` is useful; others may be stale |
| Test files (3) | **MOVE** | To `tests/e2e/web_api/` |
| PNGs (7) | **DELETE** | Test artifacts, regenerable |
| `web_api_from_libs/` | **ARCHIVE** | Unknown origin, appears stale |
| `data/`, `informal_analysis_service/`, `mcp_server/`, `results/` | **DELETE** | Empty dirs or stale __pycache__ |

## Risk Assessment

| Action | Risk | Mitigation |
|--------|------|------------|
| Keep `build/` path | Low — it works today | Document the dependency clearly |
| Archive `interface-simple/` | Low — no external references | Keep in `docs/archives/` |
| Move tests | Low — update imports | Verify tests still pass |
| Delete PNGs | None — regenerable | Already git-tracked if needed |
| Delete empty dirs | None | `git rm` |

## Recommended Phase 2 Actions

1. **Document `STATIC_FILES_DIR` dependency** in CLAUDE.md (already noted in Known Overflow table)
2. **Archive `interface-simple/`** → `docs/archives/web_api_legacy_317/interface-simple/` + README
3. **Move test files** → `tests/e2e/web_api/` (update imports)
4. **Delete PNGs** (7 test screenshots, 2.1MB)
5. **Delete empty/stale dirs**: `services/data/`, `services/informal_analysis_service/`, `services/mcp_server/`, `services/results/`
6. **Archive `web_api_from_libs/`** → investigate origin first
7. **Keep management scripts** in place (they're entry points)
8. **Keep `interface-web-argumentative/`** in place entirely

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Root `services/` tracked files | 78 | ~68 (remove PNGs + stale dirs) |
| Untracked clutter (node_modules, build) | ~38K files | Same (gitignored) |
| Empty directories | 4 | 0 |
