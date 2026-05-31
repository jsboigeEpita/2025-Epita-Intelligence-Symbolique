# Audit A-14: Interface Web

**Issue**: #168 | **SUIVI**: Score 65% | **Date audit**: 2026-05-31

## Status: 🟡 Partial

## What was delivered (student source)

Student project delivered a web interface for the argumentation analysis platform. The deliverable includes:

- A server-side application serving both API endpoints and a React frontend
- Analysis capabilities exposed via HTTP routes
- Agent interaction routes (quality evaluation, counter-arguments, debate, governance)
- WebSocket support for streaming analysis results
- A React-based single-page application for user interaction

Issue #168 requested integration of agent routes into the web interface.

## What exists in argumentation_analysis/

### Two separate web applications

**Starlette app (port 5003):**
- **`interface_web/app.py`** — Starlette application with 6 routes
- Serves the React frontend (static files from `services/web_api/interface-web-argumentative/build/`)
- Provides `/api/*` routes for analysis

**FastAPI app (port 8000):**
- **`api/main.py`** — FastAPI application with 8 routers
- **`api/agent_routes.py`** — Agent routes added by PR #197 (quality, counter-arguments, debate, governance, full-analysis)
- **`api/websocket_routes.py`** — WebSocket streaming for real-time results
- Additional routers for proposals, mobile, and other features

### Frontend

- **React build** at `services/web_api/interface-web-argumentative/build/` — served by the Starlette app

### Legacy routes

- **`interface_web/routes/jtms_routes.py`** — JTMS-specific routes still using Flask imports (dead code under Starlette migration)

## Preservation Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| React frontend | **Preserved** | Build served by Starlette |
| Analysis API | **Preserved** | Both apps expose analysis endpoints |
| Agent routes (quality, debate, etc.) | **Preserved in FastAPI** | Added by PR #197 |
| WebSocket streaming | **Preserved in FastAPI** | `websocket_routes.py` |
| JTMS routes | **Broken** | Flask imports under Starlette |
| Route coherence | **Fragmented** | Two apps on different ports, overlapping concerns |

## Gap Analysis

### Gap 1: TWO separate apps that don't share routing

The system runs two independent web applications:

- **Starlette** on port 5003 — serves the React frontend and basic `/api/*` routes
- **FastAPI** on port 8000 — serves `/api/v1/*` routes with agent capabilities, WebSocket streaming

These apps do not share routing, middleware, or session state. A request to one cannot be forwarded to the other. This creates a fragmented architecture where functionality is split across two ports with no unified entry point.

**Impact**: High. Users and consumers must know which port serves which feature. The API surface is non-discoverable.

### Gap 2: Issue #168 routes in FastAPI, not Starlette

Issue #168 specifically requested agent routes in the web interface. PR #197 added them to the FastAPI app (`api/agent_routes.py`), but the Starlette app (`interface_web/app.py`) — which serves the actual user-facing frontend — did not receive these routes. The issue was closed, but the target application was not the one modified.

**Impact**: High. The frontend (served by Starlette on port 5003) has no access to agent routes. Users must interact with a separate port 8000 service that has no UI.

### Gap 3: JTMS routes still use Flask (dead under Starlette)

`interface_web/routes/jtms_routes.py` contains Flask-style route definitions (`@app.route`, `Flask()` imports). The parent app was migrated from Flask to Starlette, rendering these routes dead code. They will never be invoked.

**Impact**: Medium. JTMS functionality is unavailable via the web interface. The dead code also creates confusion for developers expecting Flask patterns.

### Gap 4: React frontend only calls Starlette `/api/*`, not FastAPI `/api/v1/agents/*`

The React frontend's API calls are hardcoded to the Starlette app's `/api/*` endpoints. The new agent routes on FastAPI's `/api/v1/agents/*` have no UI consumer. The frontend and the agent routes are on different ports with no cross-origin wiring documented.

**Impact**: High. New features (quality evaluation, debate, governance, counter-arguments) have backend routes but no user interface. They are effectively API-only features invisible to end users.

### Gap 5: New debate/quality/governance routes have NO UI consumer

The FastAPI agent routes added by PR #197 (debate, quality, governance, counter-arguments, full-analysis) are backend-only. No React components, pages, or API client code calls these endpoints.

**Impact**: Medium. The routes are functional via direct HTTP calls (curl, Postman, programmatic) but are not accessible through the web interface.

## Recommended Action

### Short-term (stabilize)

1. **Migrate JTMS routes from Flask to Starlette** — Rewrite `jtms_routes.py` using Starlette routing. This restores JTMS web access and removes dead Flask code.
2. **Document the two-app architecture** — Add a clear section to `docs/guides/` explaining which app serves which purpose, which port to use, and why two apps exist.

### Medium-term (unify)

3. **Merge into a single application** — Evaluate migrating all Starlette routes into the FastAPI app (FastAPI is a superset of Starlette). This would give a single entry point with both the frontend and all API routes. Alternatively, make Starlette a reverse proxy to FastAPI for API routes.
4. **Add React pages for agent features** — Create UI components for quality evaluation, debate, governance, and counter-argument features that call the FastAPI endpoints.
5. **Close the loop on Issue #168** — Verify that the agent routes are accessible from the same app that serves the frontend, fulfilling the original issue intent.

### Long-term (cleanup)

6. **Remove dead Flask code** — After JTMS routes are migrated, delete all Flask imports and patterns from the web interface codebase.

## Source Files

| File | Role |
|------|------|
| `interface_web/app.py` | Starlette app (port 5003, frontend + basic API) |
| `api/main.py` | FastAPI app (port 8000, agent routes + WebSocket) |
| `api/agent_routes.py` | Agent routes (quality, debate, governance, etc.) |
| `api/websocket_routes.py` | WebSocket streaming |
| `interface_web/routes/jtms_routes.py` | JTMS routes (dead Flask code) |
| `services/web_api/interface-web-argumentative/build/` | React frontend build |
| PR #197 | Added agent routes to FastAPI |
| Issue #168 | Original integration request (CLOSED) |
