# Production Deployment Guide

**Last updated:** 2026-06-07
**Compatibility:** Windows 11, Python 3.10, Conda
**Architecture:** FastAPI backend + Starlette frontend proxy (two-server topology)

---

## Quick Start (5 minutes)

```bash
# 1. Create and activate Conda environment
conda env create -f environment.yml        # Creates "projet-is" (Python 3.10)
conda activate projet-is

# 2. Configure environment
cp .env.example .env
# Edit .env — at minimum set:
#   OPENAI_API_KEY=sk-...
#   TEXT_CONFIG_PASSPHRASE=<provided separately>

# 3. Verify
python -c "from argumentation_analysis.orchestration.registry_setup import setup_registry; setup_registry(); print('OK')"
pytest tests/unit/ -x -q --tb=line         # Should pass (skip marks for missing API keys)

# 4. Launch API
uvicorn api.main:app --reload --port 8000
# → http://127.0.0.1:8000/health
```

---

## Prerequisites

| Requirement | Version | Source | Notes |
|---|---|---|---|
| Python | 3.10 | Conda | Pinned — `environment.yml:8` |
| Java | 11+ (portable JDK 17 auto-downloaded) | Temurin | CI uses Java 11. `jvm_setup.py` auto-downloads JDK 17 to `portable_jdk/` |
| Conda | Latest | Miniconda | |
| OpenAI API key | — | platform.openai.com | Required for LLM features. Tests skip without it. |

---

## Environment Variables

### Required for real use

| Variable | Type | Default | Source |
|---|---|---|---|
| `OPENAI_API_KEY` | str | `sk-dummy-key-for-testing` | `settings.py:9-11` |
| `TEXT_CONFIG_PASSPHRASE` | str | None | `settings.py:129` — decrypts `extract_sources.json.gz.enc` |

### LLM configuration

| Variable | Type | Default | Source |
|---|---|---|---|
| `OPENAI_CHAT_MODEL_ID` | str | `gpt-5-mini` | `settings.py:12` |
| `OPENAI_BASE_URL` | str | None | `settings.py:13` |
| `GLOBAL_LLM_SERVICE` | str | `OpenAI` | `.env.example:6` |
| `OPENROUTER_API_KEY` | str | None | `.env.example:36` — alternative provider |
| `OPENROUTER_BASE_URL` | str | None | `.env.example:37` |
| `LLM_DETERMINISTIC_MODE` | bool | off | `.env.example:19` — sends temp/seed |
| `LLM_TEMPERATURE` | float | 0.0 | `.env.example:23` |
| `LLM_SEED` | int | 42 | `.env.example:26` |
| `LLM_FORCE_SAMPLING_PARAMS` | bool | off | `.env.example:30` — bypass model-aware logic |

### Solver selection (prefix `ARG_ANALYSIS_`)

| Variable | Values | Default | Source |
|---|---|---|---|
| `ARG_ANALYSIS_SOLVER` | `tweety`, `prover9`, `eprover` | `eprover` | `config.py:40` |
| `ARG_ANALYSIS_MODAL_SOLVER` | `tweety`, `spass` | `spass` | `config.py:47` |
| `ARG_ANALYSIS_PL_SOLVER` | `tweety`, `pysat` | `tweety` | `config.py:54` |
| `ARG_ANALYSIS_PYSAT_SOLVER` | str | `cadical195` | `config.py:60` |

### Application

| Variable | Type | Default | Source |
|---|---|---|---|
| `DEBUG` | bool | `False` | `settings.py:127` |
| `ENABLE_JVM` | bool | `True` | `settings.py:131` |
| `USE_MOCK_LLM` | bool | `False` | `settings.py:132` |
| `FASTAPI_HOST` | str | `127.0.0.1` | `interface_web/app.py:19` |
| `FASTAPI_PORT` | str | `8095` | `interface_web/app.py:20` |
| `PORT` | str | `5003` | `interface_web/app.py:21` — Starlette proxy |
| `FRONTEND_URL` | str | `http://127.0.0.1:3001` | `api/factory.py:41` — CORS |

### Self-hosted LLM (optional)

| Variable | Default | Source |
|---|---|---|
| `SELF_HOSTED_LLM_ENDPOINT` | None | `.env.example:64` |
| `SELF_HOSTED_LLM_API_KEY` | None | `.env.example:65` |
| `SELF_HOSTED_LLM_MODEL` | `qwen3.5-35b-a3b` | `.env.example:66` |

---

## Entry Points

### FastAPI backend (recommended)

```bash
# Production (no reload)
uvicorn api.main:app --host 0.0.0.0 --port 8095

# Development (hot reload)
uvicorn api.main:app --reload --port 8000
```

- Routers: `/api`, `/api/v1/framework`, `/api/v1/informal`, `/api/v1/agents`, `/api/v1/jtms`
- Health: `GET /health` → `{"status": "healthy", "details": {"jvm": "Running"}}`
- Status: `GET /api/status` → `operational` or `degraded`
- Version: `2.0.0`

### Starlette web UI (frontend proxy)

```bash
# Build React frontend first (one-time)
cd services/web_api/interface-web-argumentative
npm install && npm run build
cd ../../..

# Launch proxy
uvicorn interface_web.app:app --port 5003 --fastapi-port 8095
```

- Proxies `/api/*` → FastAPI backend
- Serves React SPA from `services/web_api/interface-web-argumentative/build/`
- **WebSocket**: NOT proxied — WS clients must connect directly to FastAPI (`ws://FASTAPI_HOST:FASTAPI_PORT/ws/*`)

### CLI pipeline

```bash
# Quick analysis
python -m argumentation_analysis.run_orchestration --text "Your text here" --mode pipeline

# Full spectacular workflow
python -m argumentation_analysis.run_orchestration --text "Your text here" --workflow spectacular

# Conversational mode
python -m argumentation_analysis.run_orchestration --interactive --mode conversational
```

---

## External Solvers

The pipeline can use external theorem provers. When absent, it falls back to the in-JVM Tweety reasoner with `degraded: True` (#985).

| Solver | Binary | Auto-installed? | Install |
|---|---|---|---|
| **EProver** (FOL) | `eprover` | No | [eprover.org](https://eprover.org) — add to PATH |
| **SPASS** (modal) | `SPASS` | No | [spass-prover.org](https://spass-prover.org) — add to PATH |
| **Clingo** (ASP) | `clingo` | Yes (v5.4.0) | Auto-downloaded to `ext_tools/clingo/` |
| **Prover9** (FOL) | `prover9.bat` | Bundled | `libs/prover9/bin/prover9.bat` |
| Native SAT | `*.dll`/`*.so` | Yes | Auto-downloaded to `libs/native/` |

Solvers are detected via `shutil.which()` at JVM bootstrap (`jvm_setup.py:661-767`) and per-invocation in the spectacular workflow (`invoke_callables.py`).

---

## Health Checks

| Route | Method | Description |
|---|---|---|
| `/health` | GET | JVM status + API operational |
| `/api/status` | GET | `operational` / `degraded` (analysis service check) |
| `/api/health` | GET | Extended status with service details |
| `/api/endpoints` | GET | Route introspection |
| `/` | GET | Welcome + JVM status |

---

## Known Pitfalls

### WinError 182 — DLL load order (#882)

On Windows, importing `jpype` before `torch` causes `OSError: [WinError 182]` from `fbgemm.dll`.

**Mitigation**: The codebase handles this automatically:
- `dll_guard.py` pre-loads torch/transformers before JPype
- `conftest.py` enforces import order in tests
- If still failing: reinstall PyTorch >= 2.4 or set `ENABLE_JVM=false`

### Two-server topology

Production runs two processes:
1. **FastAPI** on `:8095` — business logic, JVM, agents
2. **Starlette** on `:5003` — React frontend proxy

Starlette forwards `/api/*` to FastAPI but does **NOT relay WebSockets**. WS clients connect directly to FastAPI.

### JVM startup

JVM initialization takes 10-60s on first call. It runs in a `ThreadPoolExecutor` with 60s timeout (`jvm_setup.py:898-926`). The JVM cannot be restarted — once stopped, the process must be restarted.

- `-Djava.awt.headless=true` is deliberately **disabled** (crash cause on Windows)
- JVM heap: `-Xms256m -Xmx2048m` (configurable in `settings.py:90-91`)

### conda run from non-interactive shells

`conda activate` doesn't work in non-interactive contexts. Use:

```bash
conda run -n projet-is --no-capture-output <command>
```

---

## Testing

```bash
# All tests
conda run -n projet-is --no-capture-output pytest tests/ -v

# Unit only (fast)
pytest tests/unit/ -v

# Skip slow / API-dependent tests
pytest tests/ -m "not slow and not requires_api" -v

# Skip Java/JPype tests
pytest tests/ -m "not jpype" -v

# Linting
black --check --diff .
flake8 .
```

Tests auto-skip when API keys are unavailable (no false failures).

---

## Architecture Summary

```
┌──────────────────┐     /api/*      ┌──────────────────┐
│  Starlette :5003 │ ──────────────► │  FastAPI :8095    │
│  (React proxy)   │                 │  (agents, JVM)    │
│  interface_web/  │                 │  api/main.py      │
└──────────────────┘                 └────────┬─────────┘
                                              │
                                     ┌────────┴─────────┐
                                     │  UnifiedPipeline  │
                                     │  (22 workflows)   │
                                     │  80 capabilities  │
                                     └──────────────────┘
```

Three-tier agent hierarchy: Strategic (orchestrators) → Tactical (coordinators) → Operational (BaseAgent). All agents extend Semantic Kernel's `ChatCompletionAgent` and expose `@kernel_function` methods.

---

## File Reference

| Path | Purpose |
|---|---|
| `environment.yml` | Conda env spec (`projet-is`) |
| `.env.example` | Environment variable template |
| `argumentation_analysis/config/settings.py` | Main Pydantic settings |
| `argumentation_analysis/core/config.py` | Solver selection settings |
| `argumentation_analysis/core/jvm_setup.py` | JVM bootstrap + solver wiring |
| `api/main.py` | FastAPI application (v2.0.0) |
| `interface_web/app.py` | Starlette frontend proxy (v3.1.0) |
| `argumentation_analysis/run_orchestration.py` | CLI runner |
| `docs/architecture/` | Architecture documents |
| `docs/guides/` | User guides |

---

*Supersedes `GUIDE_DEPLOIEMENT_PRODUCTION.md` (June 2025, Sprint 3 Flask-based).*
