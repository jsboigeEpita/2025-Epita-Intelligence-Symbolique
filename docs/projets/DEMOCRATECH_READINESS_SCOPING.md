# Democratech Readiness Scoping — From Codebase to Deliberative Democracy

> Created: 2026-06-03 · Track 13 #922 · READ-ONLY scoping (no application code modified)
> Cross-reference: Issue #78 (Roadmap Democratech), NORTHSTAR_GAP_ANALYSIS.md

## Context

Issue #78 defines a 3-phase Democratech roadmap (Stabilisation → Démocratie délibérative →
Scalabilité). This document decomposes what "Democratech readiness" concretely requires
from this codebase, crossing the #78 requirements with the actual state as of main
`125923c5` (post R327).

---

## State Assessment

### Already EXISTS (no work needed)

| Component | Evidence | Tests |
|-----------|----------|-------|
| **Citizen Proposals API** (CRUD + voting) | `api/proposal_endpoints.py` 12 endpoints | `test_proposal_api.py` 324 LOC |
| **Deliberation lifecycle** (start/status/async) | `POST /api/deliberate` + `GET /deliberate/{id}/status` | Background task + state machine |
| **Democratech workflow** (9 phases) | `workflows/democratech.py` 9-phase pipeline via WorkflowBuilder | `test_democratech.py` |
| **Governance voting** (12 methods) | `governance_methods.py` (7 agent-based) + `social_choice.py` (5 formal) | 5 test files |
| **Governance SK plugin** | `governance_plugin.py` — 6 `@kernel_function` methods | Tested |
| **Consensus metrics** | `governance/metrics.py` — consensus_rate, fairness_index, satisfaction | Tested |
| **Conflict resolution** | `governance/conflict_resolution.py` — detect + resolve | Tested |
| **LLM response caching** | `services/llm_cache.py` — 3 modes (record/replay/off), diskcache backend | `test_llm_cache.py` |
| **External solvers in spectacular** | `fol_solver` + `modal_solver` phases, EProver/Prover9/SPASS with fallback | 9 tests |
| **Parametric selectors** (CLI+API) | 8 CLI flags + 4 API axes (tier/shield/vote+consensus/orchestration_mode) | 33 tests |

### PARTIAL (exists but incomplete)

| Component | What Exists | What's Missing |
|-----------|-------------|----------------|
| **React governance dashboard** | 9-tab SPA with `GovernanceDashboard` component | Dedicated proposal/voting/consensus visualization; deliberation timeline; real-time updates |
| **Multi-model routing** | OpenAI/Azure/OpenRouter/Mock providers in `llm_service.py` | Runtime model selection per-phase or per-workflow (no model selector param) |
| **Batch processing** | `comprehensive_workflow_processor.py` + async `BackgroundTasks` | Batch API endpoint, job queue, batch deliberation endpoint |
| **Production deployment** | `Dockerfile` + `docker-compose.yml` (3 services) | Health probes in compose, env documentation, production WSGI config, CI/CD pipeline |

### MISSING (not started)

| Component | Notes |
|-----------|-------|
| WebSocket streaming for deliberation | Placeholder documented non-goal (#858) |
| Prometheus metrics + Grafana dashboards | No observability stack |
| Mobile-optimized API endpoints | API exists but not optimized for mobile |
| Auth beyond opt-in shield token | No user authentication layer |

---

## Actionable Tracks (3+ tracks with scope + DoD)

### Track D1: Governance Dashboard UI (MEDIUM)

**Scope:** `services/web_api/interface-web-argumentative/src/components/governance/`

**What:** Build a dedicated Democratech governance dashboard component that:
1. Lists proposals with status badges (pending → analyzing → debating → voting → decided)
2. Shows voting results per proposal with vote distribution chart
3. Displays deliberation progress (queued → running → completed)
4. Shows consensus metrics (consensus_rate, fairness_index)

**Perimeter:**
- `src/components/governance/DemocratechDashboard.js` — New component
- `src/components/governance/ProposalList.js` — List with filters
- `src/components/governance/VotingPanel.js` — Cast vote UI
- `src/components/governance/DeliberationTracker.js` — Progress timeline
- `src/App.js` — Add Democratech tab

**DoD:**
- [ ] React component renders proposal list from `GET /api/proposals`
- [ ] Can submit vote via `POST /api/proposals/{id}/vote`
- [ ] Shows deliberation status via `GET /api/deliberate/{id}/status`
- [ ] Displays vote distribution and consensus metrics
- [ ] `npm run build` succeeds, served by Starlette proxy

**Dependencies:** None — backend API fully exists.

---

### Track D2: Multi-Model Routing (LOW-MEDIUM)

**Scope:** `argumentation_analysis/core/llm_service.py`, `api/proposal_models.py`, `api/proposal_endpoints.py`

**What:** Add a `model_routing` selector that allows per-workflow model selection:
- `single` (default) — one model for all phases
- `tiered` — cheap model for extraction, strong for reasoning
- `custom` — user-specified model IDs per phase category

**Consumer (grounded):**
- `llm_service.py:138` — `create_llm_service()` already accepts `model_id` parameter
- `invoke_callables.py:334` — `llm_budget_scope()` manages LLM call lifecycle

**Perimeter:**
- `api/proposal_models.py` — Add `model_routing: Literal["single", "tiered", "custom"]` field
- `api/proposal_endpoints.py` — Pass model_routing to context
- `run_orchestration.py` — Add `--model-routing` CLI flag (po-2025 lane)
- `llm_service.py` — Implement `TieredLLMService` wrapper that routes based on phase category

**DoD:**
- [ ] `model_routing` field in `CustomWorkflowRequest` with backward-compatible default
- [ ] Tiered routing uses different model IDs for extraction vs reasoning phases
- [ ] Test verifies model selection per phase category
- [ ] Backward-compatible (default = current behavior)

**Dependencies:** None.

---

### Track D3: Batch Deliberation API (MEDIUM)

**Scope:** `api/proposal_endpoints.py`, `api/proposal_service.py`

**What:** Add batch endpoints for submitting and tracking multiple deliberations:
- `POST /api/batch/deliberate` — Accept array of proposal IDs, return batch ID
- `GET /api/batch/{batch_id}/status` — Aggregate status of all deliberations in batch
- Rate limiting and concurrency control (semaphore)

**Consumer (grounded):**
- `proposal_service.py:136` — `run_deliberation_workflow()` already runs async
- `api/main.py:87` — Router registration point

**Perimeter:**
- `api/proposal_models.py` — `BatchDeliberationRequest`, `BatchDeliberationStatusResponse`
- `api/proposal_endpoints.py` — 2 new endpoints
- `api/proposal_service.py` — `BatchStore`, concurrent execution with semaphore

**DoD:**
- [ ] `POST /api/batch/deliberate` accepts `{"proposal_ids": [...], "workflow": "democratech"}`
- [ ] Returns batch ID with per-proposal tracking
- [ ] `GET /api/batch/{batch_id}/status` aggregates individual statuses
- [ ] Concurrency limited to configurable max (default: 3 concurrent)
- [ ] Test coverage for batch lifecycle

**Dependencies:** None.

---

### Track D4: Production Hardening (MEDIUM)

**Scope:** `docker-compose.yml`, `Dockerfile`, `api/main.py`

**What:**
1. Add health probes to docker-compose services
2. Add production env documentation (`.env.example` update)
3. Add Uvicorn production config (workers, timeout, access-log)
4. Add Prometheus metrics endpoint at `/metrics`

**Perimeter:**
- `docker-compose.yml` — healthcheck sections, resource limits
- `api/main.py` — Prometheus middleware, `/metrics` endpoint
- `.env.example` — Document all env vars with descriptions
- `docs/guides/DEPLOYMENT.md` — New deployment guide

**DoD:**
- [ ] `docker-compose up` starts API with health probe passing
- [ ] `/metrics` endpoint exposes request count, latency, LLM call count
- [ ] `.env.example` documents all env vars
- [ ] Deployment guide covers Docker + env vars + health checks

**Dependencies:** None.

---

## Phase Mapping (#78 → Tracks)

| #78 Phase | #78 Item | Status | Track |
|-----------|----------|--------|-------|
| **Phase 1** | Fix narrative_synthesis in pipeline | ✅ Already fixed (spectacular/full include it) | — |
| **Phase 1** | DAG-level asyncio.gather | ✅ Already implemented (`workflow_dsl.py:458`) | — |
| **Phase 1** | Route external solvers into spectacular | ✅ Already done (fol_solver + modal_solver phases) | — |
| **Phase 1** | Production deployment guide | ❌ | **D4** |
| **Phase 2** | Democratech workflow | ✅ Already exists | — |
| **Phase 2** | API proposals citoyennes | ✅ Already exists (12 endpoints) | — |
| **Phase 2** | Dashboard gouvernance React | ⚠️ Partial (9-tab SPA, no Democratech dashboard) | **D1** |
| **Phase 2** | Multi-model routing | ⚠️ Partial (providers exist, no per-phase routing) | **D2** |
| **Phase 3** | Batch processing optimisé | ⚠️ Partial (no batch API, no job queue) | **D3** |
| **Phase 3** | Caching LLM | ✅ Already exists (3-mode diskcache) | — |
| **Phase 3** | Mobile app integration | ❌ | Post-D1 (needs stable API first) |
| **Phase 3** | Monitoring & observabilité | ❌ | **D4** (Prometheus) |

---

## Recommendation

**Phase 1 is substantially complete** — 3/4 items already exist in the codebase. The
remaining item (production deployment guide) is covered by Track D4.

**Phase 2 is 50% complete** — backend fully exists, frontend and model routing are the gaps.
Priority: **D1 (dashboard)** → **D2 (model routing)**.

**Phase 3 starts with D3 (batch) and D4 (hardening)**. Mobile and advanced observability
are post-D1.

**Critical insight:** The codebase already has all the Democratech backend infrastructure.
The gap is not architectural — it's integration surface (dashboard UI, batch API, production
config). This is a thin layer over working components.
