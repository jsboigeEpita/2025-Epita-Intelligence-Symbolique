# North-Star Gap Analysis — Components Not Yet Selectable/Comparable

> Created: 2026-06-03 · Track 13 #922 · READ-ONLY scoping (no application code modified)
> Instance n°1 status: 8 CLI selectors + 4/4 API parity axes merged (R327)

## Methodology

For each candidate, we ground the **consumer** (file:line + context key) to ensure
any future selector is non-inerte from design (contrat anti-inerte R321b applied at
scoping stage). "N/A" means the consumer exists in pipeline mode but is genuinely
unreachable in the target context — documented honestly, not papered over.

---

## 1. Solver Selectors (LOW effort, HIGH value)

These have **wiring already in place** — `context.get()` reads exist in
`invoke_callables.py` — but no CLI flag or API field writes the key.

### 1a. Modal Solver (`tweety` vs `spass`)

| Aspect | Detail |
|--------|--------|
| **Consumer** | `invoke_callables.py:5374` — `modal_solver = context.get("modal_solver", "tweety")` |
| **Config enum** | `config.py:13` — `ModalSolverChoice(TWEETY, SPASS)` |
| **Secondary consumer** | `modal_handler.py:52` — `if settings.modal_solver == ModalSolverChoice.SPASS` |
| **CLI** | ❌ No `--modal-solver` flag in `run_orchestration.py` |
| **API** | ❌ No `modal_solver` field in `CustomWorkflowRequest` |
| **Effort** | LOW — add CLI flag (parallel to `--fol-solver`) + API Literal field |
| **Risque-inerte** | NONE — consumer reads exact key, just needs CLI/API surface |
| **Valeur produit** | HIGH — enables benchmarking Tweety vs SPASS on modal logic tasks |

### 1b. PL Solver (`tweety` vs `pysat`)

| Aspect | Detail |
|--------|--------|
| **Consumer** | `invoke_callables.py:~3200` — `_invoke_sat` reads `context.get("solver", "cadical195")` |
| **Config enum** | `config.py:20` — `PLSolverChoice(TWEETY, PYSAT)` |
| **CLI** | ❌ No `--pl-solver` flag |
| **API** | ❌ No `pl_solver` field |
| **Effort** | LOW |
| **Valeur produit** | MEDIUM — niche, but parity with FOL solver |

### 1c. SAT Solver Variant (`cadical195`/`glucose42`/etc.)

| Aspect | Detail |
|--------|--------|
| **Consumer** | `invoke_callables.py:3192` — `_invoke_sat` reads `context.get("solver", "cadical195")` |
| **Config** | `config.py:59` — `pysat_solver: str = "cadical195"` with 6 options |
| **CLI** | ❌ No `--sat-solver` flag |
| **API** | ❌ No selector |
| **Effort** | LOW |
| **Valeur produit** | MEDIUM — solver comparison for SAT-based analysis |

### 1d. ASP/Clingo Solver

| Aspect | Detail |
|--------|--------|
| **Consumer** | `invoke_callables.py:3591` — `_invoke_asp_reasoning` (JVM + Python clingo) |
| **Registry** | `registry_setup.py:786` — capability `asp_reasoning` |
| **CLI** | ❌ No `--asp-solver` flag |
| **API** | ❌ No selector |
| **Effort** | LOW |
| **Valeur produit** | LOW — ASP is niche, but completeness |

---

## 2. Workflow Catalog Parity (LOW effort, MEDIUM value)

The `WorkflowBuilder` catalog has **25+ workflows** (`workflows.py:1052-1141`), but
the API `CustomWorkflowRequest.workflow` field documents only `light/standard/full/auto`.
The field is `str` (not `Literal`), so any catalog name IS accepted at runtime — the gap
is discoverability and documentation.

**Not listed in API `/capabilities` endpoint:**

| Workflow | CLI `--workflow` | API | Consumer (builds in) | Value |
|----------|-----------------|-----|----------------------|-------|
| `spectacular` | ✅ | ✅ (undocumented) | `workflows.py:728` 20-phase full chain | HIGH — benchmark max config |
| `formal_extended` | ✅ | ✅ (undocumented) | `workflows.py:~950` 15-phase formal chain | HIGH — formal logic focus |
| `iterative` | ✅ | ✅ (undocumented) | `workflows.py:~800` multi-pass refinement | MEDIUM |
| `quality_gated` | ✅ | ✅ (undocumented) | `workflows.py:~830` quality threshold gate | MEDIUM |
| `debate_governance` | ✅ | ✅ (undocumented) | `workflows.py:~860` debate + vote combo | MEDIUM |
| `jtms_dung` | ✅ | ✅ (undocumented) | `workflows.py:~880` JTMS + Dung chain | LOW |
| `democratech` | ✅ | ✅ | `workflows.py:~900` deliberation workflow | HIGH |
| `debate_tournament` | ✅ | ✅ | `workflows.py:~920` tournament bracket | MEDIUM |
| `fact_check` | ✅ | ✅ | `workflows.py:~940` fact verification | MEDIUM |
| `neural_symbolic` | ✅ | ✅ (undocumented) | `workflows.py:~960` neural+symbolic | LOW |
| `formal_debate` | ✅ | ✅ (undocumented) | `workflows.py:~980` formal argumentation | LOW |
| `belief_dynamics` | ✅ | ✅ (undocumented) | `workflows.py:~1000` belief revision | LOW |
| `argument_strength` | ✅ | ✅ (undocumented) | `workflows.py:~1020` strength scoring | LOW |
| `formal_verification` | ✅ | ✅ (undocumented) | `workflows.py:~1040` verification chain | LOW |
| `comprehensive` | ✅ | ✅ (undocumented) | `workflows.py:~1060` everything enabled | MEDIUM |
| `hierarchical_fallacy` | ✅ | ✅ (undocumented) | `workflows.py:~1080` per-arg fallacy | LOW |
| `nl_to_logic` | ✅ | ✅ (undocumented) | `workflows.py:~1100` NL→formal | LOW |

**Effort:** LOW — update `/capabilities` endpoint listing + API docs. No code change needed.

---

## 3. Agent-Set Selector (MEDIUM effort, MEDIUM value)

| Aspect | Detail |
|--------|--------|
| **Consumer** | `workflow_dsl.py:572` — `provider = providers[0]` (always picks first) |
| **Registry** | `capability_registry.py:293` — `find_for_capability()` returns list, no selection |
| **Phase model** | `workflow_dsl.py:58` — `WorkflowPhase` has no `provider_selector` field |
| **Conversational** | Hardcoded `AGENT_SPECIALITY_MAP` — agents fixed per speciality |
| **Effort** | MEDIUM — requires `provider_selector` on `WorkflowPhase` + resolution logic |
| **Valeur produit** | MEDIUM — enables A/B comparison of different agents for same capability |
| **Risque-inerte** | MEDIUM — resolution must be wired at execution time, not just registration |

---

## 4. Conversational Mode Selector Gaps (grounded)

PR #921 forwarded `selector_context` to `_run_parent_harness_fallback()`, which only
invokes fallacy detection functions. The consumers for other selectors live in pipeline-
only phases.

| Selector | Pipeline Consumer | Conversational Consumer | Verdict |
|----------|-------------------|------------------------|---------|
| `fallacy_tier` | `invoke_callables.py:3732` | ✅ Same consumer via harness | Active |
| `shield_preset` | `invoke_callables.py:6393` `_invoke_ai_shield()` | ❌ ai_shield never invoked | **N/A** — shield is pipeline-phase |
| `vote_method` | `invoke_callables.py:1394` `_invoke_governance()` | ❌ governance via LLM tool-call | **N/A** — GovernanceAgent uses tool JSON args |
| `consensus_threshold` | `invoke_callables.py:1545` `_invoke_governance()` | ❌ same as vote_method | **N/A** — same reason |

**Root cause:** `_run_parent_harness_fallback` only calls `_invoke_hierarchical_fallacy` and
`_invoke_hierarchical_fallacy_per_argument`. These functions only read `fallacy_tier`.
The governance/shield consumers are in separate pipeline phases never reached from
conversational mode.

**Recommendation:** Document as N/A definitively. The conversational orchestrator's
GovernanceAgent selects method dynamically via LLM function calling (tool JSON args),
not via context key — a fundamentally different pattern that doesn't benefit from
a static selector.

---

## 5. Configuration Selectors (MEDIUM effort, MEDIUM value)

| Parameter | Consumer | CLI | API | Effort |
|-----------|----------|-----|-----|--------|
| Phase timeout | `workflow_dsl.py:66` per-phase timeout_seconds | ❌ | ❌ | MEDIUM |
| Loop max iterations | `workflow_dsl.py:53` loop_config | ❌ | ❌ | LOW |
| Parallelism limit | `workflow_dsl.py:458` asyncio.gather | ❌ | ❌ | MEDIUM |
| LLM budget ceiling | `invoke_callables.py:334` llm_budget_scope() | ❌ | ❌ | LOW |
| Checkpoint resume | `unified_pipeline.py:64` resume_from | ❌ | ❌ | LOW |
| Narrative synthesis mode | `invoke_callables.py` `_invoke_narrative_synthesis` | ❌ | ❌ | LOW |

---

## 6. Dung Provider (#908 — in progress, po-2025)

| Aspect | Detail |
|--------|--------|
| **Consumer** | `invoke_callables.py:5441` — `_invoke_dung_extensions` hardcodes AFHandler |
| **Provider** | `dung_student_provider.py:217` — `invoke_dung_student()` adapter ready |
| **CLI** | ❌ No `--dung-provider` flag |
| **API** | ❌ Deferred in `proposal_models.py:78` |
| **Effort** | LOW (consumer wiring) — premise corrected R327 |
| **Status** | Track 10, dispatched to po-2025 |

---

## Priority Recommendations (Top-3)

| Rank | Track | Value | Effort | Why |
|------|-------|-------|--------|-----|
| **1** | Solver selectors (modal, PL, SAT, ASP) | HIGH | LOW | Wiring exists, just surface flags. Enables benchmarking different formal reasoning backends. |
| **2** | Workflow catalog API parity | MEDIUM | LOW | `/capabilities` already lists some; fill the 14 gaps for discoverability. |
| **3** | Agent-set selector | MEDIUM | MEDIUM | Enables A/B agent comparison. Requires architectural change to `WorkflowPhase`. |

**Deprioritized:** Phase timeout, parallelism limit, checkpoint resume — nice-to-have but
no user demand yet. Narrative synthesis mode is already accessible via workflow selection
(`spectacular`, `full`).

---

## Appendix: Already-Exposed Selectors (baseline for completeness)

| Selector | CLI Flag | API Field | Consumer |
|----------|----------|-----------|----------|
| Orchestration mode | `--mode` | `orchestration_mode` | `proposal_endpoints.py:229` dispatch |
| Fallacy tier | `--fallacy-tier` | `fallacy_tier` | `invoke_callables.py:3732` |
| Shield preset | `--shield-preset` | `shield_preset` | `invoke_callables.py:6393` |
| Vote method | `--vote-method` | `vote_method` | `invoke_callables.py:1394` |
| Consensus threshold | `--consensus-threshold` | `consensus_threshold` | `invoke_callables.py:1545` |
| FOL solver | `--fol-solver` | ❌ | `invoke_callables.py:6023` |
| Counter strategy | `--counter-strategy` | ❌ | `invoke_callables.py` `_invoke_counter_argument` |
| Formal extension | `--formal-extension` | ❌ | `workflows.py` `filter_formal_extensions()` |
| Dung provider | ❌ (pending #908) | ❌ (deferred) | `invoke_callables.py:5441` |
