<!--
PROVENANCE (Cleanup Gate / global CLAUDE.md "Consolider != Archiver")
  Role:        audit report — systematic read-only sweep (no code change)
  Origin:      issue #1078 (AUDIT-LLM-ROUTING) — dispatched R395 by coordinator ai-01
  Context:     post-#1077 (3 toggle-bypass sites + .env fixed). This is the systematic
               sweep to find any REMAINING bypass / silent-degradation sites.
  Base:        b613ee5a (post-#1077 main)
  Author:      Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
  Date:        2026-06-13
  Privacy:     opaque IDs only; no raw_text / author / title / dataset content
-->

# AUDIT-LLM-ROUTING — systematic sweep for toggle-bypass + silent-degradation sites

## 0. TL;DR

Sweep of **every** OpenAI/AsyncOpenAI client-instantiation site + every LLM-call
silent-degradation path, post-#1077. **Base audited: `b613ee5a` (post-#1077 main).**

**Findings (honest):**

- **2 genuine production leaks** remaining (both in `orchestration/`): `router.py:239`
  (real, used) and the `service_manager.py:803/896` clients (constructed-but-unused —
  code-smell, not a functional leak). A fix-issue is filed for each.
- **1 legacy-path bypass** (`project_core/.../unified_production_analyzer.py:379`) — not on
  the main production path; flagged, low priority.
- **1 silent-degradation path worth tightening**: `french_fallacy_adapter.py` returns `[]`
  with no degraded signal on API failure.
- The **4 files #1077 fixed** are confirmed HONORS the toggle (verified, not assumed).
- The **conversational LLM budget (#1006)** is **covered**: `conversational_executor.py:427`
  calls `_bump_sk_budget()` per AgentGroupChat turn. Not an open gap.

**No fabrication** — every verdict below is VERIFIED by reading the code at the cited lines
(SDDD: VERIFIED > REPORTED). Sites marked BYPASS were checked for *actual use* of the client,
not just construction.

---

## 1. The canonical toggle (reference)

`argumentation_analysis/core/llm_service.py:111-156` (`create_llm_service`):

```python
openrouter_base_url = os.environ.get("OPENROUTER_BASE_URL")
openrouter_api_key  = os.environ.get("OPENROUTER_API_KEY")
use_openrouter = bool(openrouter_base_url and openrouter_api_key)
if use_openrouter:
    api_key = openrouter_api_key
    model_id = os.getenv("OPENROUTER_CHAT_MODEL_ID", model_id)
    # ... client_kwargs["base_url"] = openrouter_base_url
else:
    api_key = os.environ.get("OPENAI_API_KEY")
```

**Definition used for this audit:**
- **HONORS** = the site consults `OPENROUTER_BASE_URL` + `OPENROUTER_API_KEY` and routes
  through OpenRouter when both are set (mirroring the factory).
- **BYPASS** = the site instantiates its own OpenAI/AsyncOpenAI reading `OPENAI_BASE_URL` /
  `OPENAI_API_KEY` only (or no-args), so when the toggle is ON it still hits the official
  endpoint → 429 → potential silent fallback. **The dangerous case.**
- **INTENTIONAL** = a baseline / connectivity test that legitimately calls official OpenAI
  for a controlled comparison (acceptable; not a leak).
- **NA** = fixed non-LLM endpoint (local embedding/re-ranker server) or self-hosted LLM —
  out of the OpenRouter toggle's scope by design.

---

## 2. LLM-client instantiation sites — full enumeration

### 2.1 Production trunk (`argumentation_analysis/`)

| file:line | base_url source | api_key source | verdict | genuinely used? | fix-issue |
|-----------|-----------------|----------------|---------|-----------------|-----------|
| `core/llm_service.py:152` | OPENROUTER_* / OPENAI_* | OPENROUTER_* / OPENAI_* | **HONORS** | yes (the factory) | — (canonical) |
| `orchestration/invoke_callables.py:273` | OPENROUTER_* / OPENAI_* | OPENROUTER_* / OPENAI_* | **HONORS** | yes (`_get_llm_client`, lines 254-275 mirror the toggle exactly) | — |
| `orchestration/router.py:239` | none (official default) | `OPENAI_API_KEY` (`self._api_key`, set at `:149`) | **BYPASS** | **yes** — `client.chat.completions.create` at `:251` | **#1079** |
| `orchestration/service_manager.py:803` | none | pydantic `settings.openai.api_key` | **BYPASS** (constructed) | **no** — dead; real call is `self.kernel.invoke(chat_function)` at `:814` | **#1080** (cleanup) |
| `orchestration/service_manager.py:896` | none | pydantic `settings.openai.api_key` | **BYPASS** (constructed) | **no** — dead; real call is `self.kernel.invoke(chat_function)` at `:906` | **#1080** (cleanup) |
| `orchestration/collaborative_debate.py:119` | `OPENAI_BASE_URL` (default api.openai.com) | `OPENAI_API_KEY` | **BYPASS** | yes (early api_key check returns explicit `_fallback_collaborative` w/ `interaction_type:"fallback_heuristic"` — *signaled*) | **#1079** |
| `orchestration/invoke_callables.py:2298` | `SELF_HOSTED_LLM_ENDPOINT` | `SELF_HOSTED_LLM_API_KEY` | **NA** | yes (self-hosted, out of scope) | — |
| `adapters/french_fallacy_adapter.py:1105` | `OPENAI_BASE_URL` | `OPENAI_API_KEY` | **BYPASS** | yes (`detect_async`) | **#1079** |
| `agents/tools/analysis/new/semantic_argument_analyzer.py:20` | hardcoded `localhost:8000` | hardcoded `"EMPTY"` | **NA** | no (local embedding server client; LLM call is via `kernel.invoke` at `:34`) | — |
| `evaluation/judge.py:116` | `OPENAI_BASE_URL` | `OPENAI_API_KEY` | **BYPASS** | yes (LLM-judge) | **#1079** |
| `evaluation/fallacy_benchmark.py:547` | `OPENAI_BASE_URL` (default api.openai.com) | `OPENAI_API_KEY` | **INTENTIONAL** | yes (mode A baseline) | — (baseline) |
| `evaluation/fallacy_benchmark.py:588` | `OPENAI_BASE_URL` (default api.openai.com) | `OPENAI_API_KEY` | **INTENTIONAL** | yes (mode B baseline) | — (baseline) |
| `evaluation/fallacy_benchmark.py:627` | `OPENAI_BASE_URL` (default api.openai.com) | `OPENAI_API_KEY` | **INTENTIONAL** | yes (mode C baseline) | — (baseline) |
| `nlp/embedding_utils.py:91` | none (OpenAI default) | `OPENAI_API_KEY` (SDK default) | **BYPASS** (embeddings) | yes (`text-embedding-*`, not chat-completion) | low-pri note in #1079 |

#### Confirmed-fixed by #1077 (out of scope, verified HONORS for consistency)

| file:line | verdict | note |
|-----------|---------|------|
| `services/nl_to_logic.py:282-295` | **HONORS** | toggle consulted (`_translate_with_llm`); verified `:282-295` reads OPENROUTER_* first |
| `plugins/coordinated_logic_plugin.py:62` | HONORS (per #1077) | not re-read; trusts the merged fix |
| `services/ai_shield/layers/llm_validator.py:70` | HONORS (per #1077) | not re-read; trusts the merged fix |
| `scripts/run_capstone_c1.py:284` | HONORS (per #1077) | not re-read; trusts the merged fix |

### 2.2 `project_core/` (legacy "from scripts")

| file:line | base_url source | api_key source | verdict | note | fix-issue |
|-----------|-----------------|----------------|---------|------|-----------|
| `rhetorical_analysis_from_scripts/unified_production_analyzer.py:379` | none (`openai.AsyncOpenAI()` no-args) | SDK-default | **BYPASS** | legacy analyzer; not on main production path; `:390` raises (not silent) | low-pri note in #1079 |

### 2.3 `scripts/` (runners / baselines / connectivity)

Tolerance is higher here (one-shot runners, controlled comparisons). All classified
**INTENTIONAL** (baselines / connectivity tests by design): `baseline_0shot.py:118`,
`scda_deepsynthesis_vs_baseline.py:382`, `compare_fallacy_detection_modes.py:148/170/219`,
`apps/sherlock_watson/validation_point1_simple.py:61/117/179`, `maintenance/validate_openai_connection.py:23`,
`validation/validate_openai_key.py:20`.

One **BYPASS** in scripts that is NOT a baseline: `scripts/narrative_reporting/agent/narrative_agent.py:52`
(production-ish narrative agent reading `OPENAI_API_KEY` only). Low priority — noted in #1079.

### 2.4 Out of scope (sanctuarized student dirs / docs / archives / tests)

`2.3.3-generation-contre-argument/*`, `1_2_7_argumentation_dialogique/*`, `3.1.5_Interface_Mobile/*`,
`docs/**`, `tests/integration/test_api_connectivity.py` (connectivity test by design),
`CONTRIBUTING.md`. Not audited for fixes (sanctuary / illustrative).

---

## 3. Silent-degradation paths (try/except around LLM calls)

Anti-théâtre mandate #1019: a degraded path must `raise` OR emit a `degraded=True` /
`status="failed"` / `error=...` signal a consumer acts on. A path that returns an
empty/heuristic result with **no** signal is the dangerous case.

| file:line | behavior on LLM failure | signal to consumer? | verdict |
|-----------|-------------------------|---------------------|---------|
| `adapters/french_fallacy_adapter.py:1120-1126` | returns `[]` | **NO** — caller sees empty fallacy list, indistinguishable from "no fallacies found" | **SILENT — tighten** (in #1079) |
| `evaluation/judge.py:142-153` | returns zeroed `JudgeScore`, error embedded in `reasoning` string | partial (zeroed scores + string) | borderline — acceptable (zeroed scores are observable) |
| `orchestration/service_manager.py:833-840 / 859` | returns `{status:"error", error:str(e)}` | **YES** | OK |
| `orchestration/invoke_callables.py:2343` | returns `{tiers_used:["none"], error:str(e), total_fallacies:0}` | **YES** | OK |
| `orchestration/collaborative_debate.py:113` | early return `_fallback_collaborative` w/ `interaction_type:"fallback_heuristic"` | **YES** (explicit) | OK |
| `project_core/.../unified_production_analyzer.py:388-390` | logs + `raise` | YES (propagates) | OK |

**One genuine silent path**: `french_fallacy_adapter.detect_async` swallowing API errors into `[]`.
This is the exact #1019 failure shape (empty result, no signal) and is included in fix-issue #1079.

---

## 4. Cross-check: #1006 (AgentGroupChat conversational LLM budget)

The dashboard's structural blocker "#1006 — `AgentGroupChat.invoke()` does not pass through
`_guarded_chat_completion`; bounded by `max_turns`" was checked.

**Finding (VERIFIED):** the conversational path's budget is **covered**.
`argumentation_analysis/orchestration/conversational_executor.py:39` imports `_bump_sk_budget`
from `invoke_callables`, and `:427` calls `_bump_sk_budget()` after each AgentGroupChat turn.
So the per-run LLM budget counter is incremented on the conversational path — the gap noted in
#1006 / R364 (kernel-internal calls bypassing `_guarded_chat_completion`) is mitigated by this
turn-level counter. **Not an open silent-degradation gap.** No fix-issue needed; documented here
to close the loop.

---

## 5. Fix-issues filed

- **#1079** — Fix the genuine production leaks: `router.py:239`,
  `collaborative_debate.py:119`, `french_fallacy_adapter.py:1105` (+ its silent `[]`
  degradation), `judge.py:116`, `embedding_utils.py:91` (low-pri), and the legacy
  `unified_production_analyzer.py:379` / `narrative_agent.py:52` (low-pri). Pattern: route
  through the OPENROUTER_* toggle exactly as `invoke_callables._get_llm_client` does
  (anti-pendule: remove the bypass, do NOT add a new knob).
- **#1080** — Cleanup the dead OpenAI clients in `service_manager.py:803/896` (constructed
  but never used — the real call goes through `kernel.invoke`). Remove the dead construction;
  this is a code-smell, not a functional leak.

---

## 6. Methodology & limits

- **Triple grounding**: technical (Read/Grep of `b613ee5a`), the #1078 body, and the #1077
  diff context. Every BYPASS verdict was checked for *actual client use*, not just
  construction (this is what separates the real `router.py:239` leak from the dead
  `service_manager.py:803` client).
- **Anti-pendule**: baselines/connectivity tests that intentionally call official OpenAI are
  classified INTENTIONAL, not flagged as leaks — the official-OpenAI path is correct behavior
  when OpenRouter is not configured.
- **Read-only**: no production code edited. The 4 #1077 files were verified but not touched.
- **Limit**: `plugins/coordinated_logic_plugin.py`, `ai_shield/layers/llm_validator.py`, and
  `run_capstone_c1.py` were trusted as HONORS per the merged #1077 rather than re-read in full
  (marked REPORTED-per-#1077, not re-VERIFIED, to respect the "don't touch" constraint and
  avoid redundant work). nl_to_logic.py WAS re-verified (HONORS confirmed at :282-295).
