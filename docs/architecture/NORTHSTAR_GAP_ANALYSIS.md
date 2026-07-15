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

## 6. Dung Provider (#908 — ✅ CLOSED via multi-backend comparison, I5 #1430)

| Aspect | Detail |
|--------|--------|
| **Original gap** | `_invoke_dung_extensions` hardcoded AFHandler — no backend selection |
| **Resolution** | Multi-backend **comparison** (not selection): `dung_mode=compare` routes to `_compare_dung_backends` (`invoke_callables.py:6847`), running Tweety + student (`abs_arg_dung`) and surfacing per-semantics agreement/disagreement verbatim (never reconciled). Livré #1432/#1434/#1436. |
| **Note** | The pivot from "select one provider" → "compare all providers" supersedes the original `--dung-provider` selector framing. Disagreement between backends is a **result**, not masked (#1019). |

---

## 7. NORTH-STAR Consolidation — ✅ MECHANISMS COMPLETE, selectable (R606)

> Updated 2026-07-11 (po-2025, base `994baf93`). All NORTH-STAR mechanisms are
> now **complete and pipeline-selectable**. The **only** remaining open gap is
> the real-corpus run (ATT-3), gated on user go — honestly left OPEN.

### 7a. Text→structured translators — 5/5 ✅ CLOSED

| Formalism | Capability | Handler | Status |
|-----------|-----------|---------|--------|
| Bipolar AF | `bipolar_argumentation` | `_invoke_bipolar` (`invoke_callables.py:3064`) | ✅ #1422 |
| ABA | `aba_reasoning` | `_invoke_aba` (`invoke_callables.py:3111`) | ✅ #1422 |
| ASPIC+ | `aspic_plus_reasoning` | `_invoke_aspic` (`invoke_callables.py:3217`) | ✅ #1427 |
| SetAF | `setaf_reasoning` | `_invoke_setaf` (`invoke_callables.py:3620`) | ✅ #1428 |
| Weighted AF | `weighted_argumentation` | `_invoke_weighted` (`invoke_callables.py:3670`) | ✅ #1431 |

> **Honest nuance (#1442, verified firsthand 2026-07-12)**: 5/5 translators are
> coded AND genuine-extraction-capable. Probe scratchpad confirms SetAF extracts
> collective attacks (4-attacker joint attack on a corpus_A excerpt) and weighted
> derives varied weights from text (0.95 vs 0.2). The ATT-3 run nonetheless
> surfaced `degraded=true` for SetAF+weighted on its 3 political corpora while
> bipolar/ABA/ASPIC+ passed `evaluated` — this is **honest LLM-non-determinism
> on the specific run's inventory, not a translator defect** (a re-run can flip
> it). The `degraded` flag is the correct anti-théâtre signal when the LLM
> extraction returns empty; it is never masked into a synthetic `evaluated`.

> **GE-1 honest-degraded diagnosis (#1450, verified firsthand 2026-07-14)**: the
> ATT-3-degraded finding for SetAF+weighted is now **mechanically explained** on
> the 3 real corpora (the `#1442` nuance called it "LLM non-determinism"; this
> pass discriminates its source).

**Genuine-extraction matrix (corpus_A/B/C, `structured_arg_status` firsthand)**:

| Translator | corpus_A | corpus_B | corpus_C |
|------------|----------|----------|----------|
| SetAF      | degraded-honnête | degraded-honnête | degraded-honnête |
| Weighted   | degraded-honnête | **genuine evaluated** | degraded-honnête |

**Causal diagnosis** (multi-sample, single event loop, ≥2 runs per case — anti [[reference_llm_run_nondeterminism]]):

1. **corpus_A — auto-promotional speech.** All 10 arguments are parallel
   self-praise (« grandeur », « redressement », « faute admin »); no mutual
   attacks. Raw LLM (`_llm_extract_relations`) returns `{"attacks": []}`
   honestly: the translator sees no structure to extract. **Genuine-absence,
   not translator defect.**
2. **corpus_B — manifesto with oppositions.** Weighted extracts genuine
   dyadic attacks on the baseline run. SetAF returns `[]` on the same window
   on 2/3 re-probes and singleton-only sets on the 1/3 successful run — the
   few hits are singletons (= dyadic, already captured by weighted), never a
   true joint (`attacker-set-size > 1`). Stochasticity is LLM-native on hard
   text, not a window-size artefact.
3. **corpus_C — placeholder synthetic.** Neither formalism finds extractable
   structure; the handler falls back to auto-shaped synthetic flagged
   `degraded=true`. Documented in `state_writers._record_structured_arg_status`.

**Window-size hypothesis REFUTED** (`structured_arg_translator.py:184` sends
`input_text[:3000]`). Window-isolation probe N=3 per window:

| window | SetAF success on corpus_B |
|--------|---------------------------|
| `[:3000]` (production) | 0/3 |
| `[:30000]`             | 1/3 |
| `[:60000]` (full)      | 0/3 |

Widening the window does **not** improve extraction → the [:3000] cap is not
the bottleneck. The stochasticity is genuine LLM variance on hard text, not
a leakable artifact of the prompt construction.

**Positive control (decisive)**: synthetic corpus with a known 3→1 joint
attack (3 independent considerations jointly defeat a proposal) → SetAF
**reliably extracts `attacker-set-size=[3]` (2/2 samples)**. This proves the
prompt and translator are **genuine-capable**; the degraded status on the
real corpora is a property of the **material** (absence of collective-attack
structure in A and C; only dyadic structure in B), not a property of the
code.

**Conclusion**: SetAF+weighted are honest translators — coded correctly,
genuinely reachable when the source text carries the structure, and
correctly marked `degraded` (anti-théâtre #1019) when it does not. No code
fix is warranted. Forcing a populated SetAF on corpus_A auto-promotion or
on corpus_C would be **théâtre** — fabricating joint attacks the text does
not carry.

### 7b. Multi-backend comparison axes — 3/3 ✅ CLOSED

| Axis | Comparator | Backends | Status |
|------|-----------|----------|--------|
| FOL | `compare_fol_backends` (`fol_handler.py:963`) | EProver/Prover9/Mace4 | ✅ (pre-existing) |
| Dung | `_compare_dung_backends` (`invoke_callables.py:6847`) | Tweety/student | ✅ #1432-#1436 |
| Sophism | `compare_sophism_backends` (`neuro_symbolic_arbitrator.py:526`) | neural/neuro-symbolic | ✅ #1433/#1435 |

### 7c. Unified harness + pipeline-selectable capability — ✅ CLOSED

- `compare_all_axes` (`invoke_callables.py:7186`) — router + uniform aggregator over the 3 axes, zero re-implementation. ✅ #1438
- `_invoke_multi_axis_compare` (`invoke_callables.py:7333`) → capability `multi_axis_compare`, registered `multi_axis_compare_service` (`registry_setup.py:470`). Selectable, NOT forced into presets; default honest-absent. ✅ #1439

### 7d. ⏳ STILL OPEN — real-corpus multi-axis run (ATT-3)

The terminal data-feeding run over the real (encrypted) corpus is **not done**.
Gated on user decision; execution ai-01-local (nominative artefacts,
non-delegable). **Honestly left OPEN** — not coché.

> All pointers above verified via `git grep` (verify-before-assert, mandate R563).
> No invented capabilities; only merged code is cited as ✅.

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
| Dung provider | ❌ (superseded) | ❌ (superseded) | ✅ CLOSED §6 — multi-backend **comparison** via `dung_mode=compare` (`invoke_callables.py:6478`), not single-provider selection |
