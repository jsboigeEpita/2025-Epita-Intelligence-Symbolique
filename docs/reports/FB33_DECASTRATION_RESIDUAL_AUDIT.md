# FB-33 — De-castration Residual Audit (close #1109 §4)

**Issue**: #1113 (Track FB-33). **Parent**: #1109 §4 (residual castration sites). **Dispatch**: R406 (ai-01 → po-2023, HIGH).
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique (conceptual audit lane).
**Base**: main `fd3831a8` (post FB-30 #1110 + FB-31 #1111 — both major de-castration sites landed).
**Date**: 2026-06-15.

> Privacy: opaque IDs only. This report references code paths, line numbers, and
> capability names — no `raw_text`, no source/speaker identifiers.

---

## 1. Mandate

The two **major** castration sites are de-castrated: the descent (FB-30 #1110,
removed the mechanical `_beam_descent` + depth cap) and the synthesis (FB-31
#1111, removed the count-template `_build_final_synthesis` fallback, Section 9
now LLM fail-loud). #1109 §4 lists **residual** items to verify so no mechanical
/template bypass silently re-bridles richness/variance. FB-33 closes the last 3:

1. **`_run_one_shot`** — true fail-loud last resort, or a default template?
2. **Mechanical-loop sweep** — any other Python loop/f-string replacing SK
   function-calling or emitting analysis without the LLM?
3. **Final-run config** — does the spectacular run force `LLM_DETERMINISTIC_MODE`?
   Does any golden test freeze **prose** (structure-only is OK)?

The first 4 §4 items (descent, wide-net pre-gating, Section 9 template,
`narrative_synthesis_plugin` label) were addressed by FB-30/FB-31; FB-33 audits
the last 3 + re-verifies the `narrative_synthesis` residual (see §5 — finding).

---

## 2. Method

All checks run against **current main `fd3831a8`** (post-de-castration), not a
stale tree. Tools: `git show origin/main:<path>`, `grep`, targeted `Read`. No
live LLM run (file-disjoint from FB-32 po-2025 runs lane; this is a conceptual
audit).

---

## 3. Item 1 — `_run_one_shot` audit ✅ PASS (no fix needed)

**Location**: `argumentation_analysis/plugins/fallacy_workflow_plugin.py:1415`
(`async def _run_one_shot`).

**Verdict**: `_run_one_shot` is a **genuine single-LLM-call last resort**, NOT a
template and NOT a default path.

- **Single LLM call** — it builds a prompt (argument + compact taxonomy ≤depth 6)
  and calls `self.llm_service.get_chat_message_content(...)` (line 1571 in the
  method). The fallacy content is produced by the LLM, not an f-string. It does
  NOT kill variance/richness.
- **Not a default path** — 3 call sites: (a) opt-in `use_one_shot=True`
  (`run_guided_analysis`), (b) fallback when wide-net produces no candidates,
  (c) Phase-4 fallback when iterative deepening finds nothing. The default path
  is the restored agentic `_explore_single_branch` (FB-30). One-shot is a safety
  net + opt-in, not the default.
- **No synthetic/template output on LLM failure**:
  - LLM transport failure → `{"error": str(e), "fallacies": []}` (error field
    present, no fabricated fallacy).
  - LLM responded but unparseable + no taxonomy-name match →
    `{"fallacies": [], "exploration_method": "one_shot_no_match"}` (measured
    empty, **flagged**).
  - Taxonomy name matched in raw LLM text → real extraction (confidence 0.35),
    not synthetic.
- **DoD fix condition NOT triggered** — the DoD says "fix fail-loud IF it emits
  synthetic/template output on LLM failure." It emits neither.

**Minor note (not a fix — anti-pendule)**: the transport-failure return uses
`{"error": ..., "fallacies": []}` rather than the #1019 `last_degraded=True` +
`last_error` convention. The `error` field IS surfaced (propagated by the
caller), so it is not *silent*; aligning the field name to the convention would
be cosmetic, not a real gap. Left as-is.

---

## 4. Item 2 — Mechanical-loop sweep ✅ (table below; one residual → fix-intent #1115)

Sweep of Python loops / f-string emitters that could replace SK function-calling
or emit analysis bypassing the LLM. **Reference SK function-calling path**:
`_explore_single_branch` (`fallacy_workflow_plugin.py`) — the restored agentic
core (FB-30) using `explore_branch` / `confirm_fallacy` / `conclude_no_fallacy`
kernel functions via `FunctionChoiceBehavior.Auto`.

| # | Artefact | Location | Verdict | Action |
|---|----------|----------|---------|--------|
| 1 | `_beam_descent` (mechanical per-level beam) | `fallacy_workflow_plugin.py` (was :442) | **DELETED (FB-30 #1110)** — method + Phase 3b call gone. Only 3 doc/comment refs remain (lines 72, 1268-1269 — historical, record WHY). | ✅ none — verified 0 live refs |
| 2 | `MAX_DEPTH_PER_BRANCH` cap | `fallacy_workflow_plugin.py:72` | **REMOVED (FB-30)** — comment-only ref remains. | ✅ none |
| 3 | `_build_final_synthesis` (count-template Section 9 fallback) | `deep_synthesis_agent.py` (was :278) | **DELETED (FB-31 #1111)** — 0 defs in `argumentation_analysis/`. Section 9 now `_llm_synthesis` fail-loud (`final_synthesis_status`). | ✅ none |
| 4 | `narrative_synthesis_plugin.build_narrative` (pure template prose) | `plugins/narrative_synthesis_plugin.py:46`; phase in `workflows.py:869` | **RESIDUAL — still wired into spectacular + surfaced** (see §5). FB-31 labeled the module; the phase is NOT skipped in spectacular. | ⚠️ **fix-intent #1115** (coordinated DAG test updates needed) |
| 5 | `build_convergent_synthesis` (convergence scores/verdicts) | `narrative_synthesis_plugin.py` (used by `deep_synthesis_agent:598`) | **Structural computation** (scores, methods, statements) — NOT template prose. Produces `ConvergentVerdict` records, fed to the LLM-grounded synthesis as structured input. | ✅ keep (structural input to LLM, not a prose bypass) |
| 6 | `IterativeDeepeningOrchestrator` (generalized beam pattern) | `orchestration/iterative_deepening.py:62` | **Orphaned/dormant** — 0 prod importers (test-only, `test_iterative_deepening.py`). Matches #1109 §2. | ✅ keep (dormant; not live-wired, no castration effect) |
| 7 | `_run_one_shot` (single LLM call) | `fallacy_workflow_plugin.py:1415` | **Genuine LLM call** (item 1). Not a template. | ✅ none |

**Sweep result**: of 7 candidate sites, 6 are clean (deleted/structural/dormant/LLM).
**One residual** (row 4, `narrative_synthesis` template prose on the spectacular
path) → fix-intent issue **#1115**.

---

## 5. The one residual — `narrative_synthesis` template on the spectacular path

`build_narrative()` weaves f-strings over state counts ("N arguments, M
fallacies…") → near-identical prose regardless of model → a determinization
residue (#1109) killing richness AND variance. FB-31 (#1108) labeled the
**module** with a strong warning and stated it is "always-skipped in
spectacular." **FB-33 verified that claim is inaccurate**:

1. `build_spectacular_workflow` (`orchestration/workflows.py:869-874`) declares
   `narrative_synthesis` as a phase (`optional=True` → runs by default; optional
   means non-fatal-on-failure, NOT skipped).
2. `deep_synthesis` (the LLM fail-loud spectacular deliverable) lists
   `narrative_synthesis` in `depends_on` (`workflows.py:924`).
3. The generic HTML report surfaces the template prose:
   `visualization/html_report.py:283` → `<div class="narrative">{{ narrative_synthesis }}</div>`.

**Severity — moderate, not critical**: the **canonical** spectacular deliverable
(the `deep_synthesis` 9-section markdown, Section 9 = LLM `_llm_synthesis`
fail-loud per FB-31) is already template-free. The residual is that the template
`narrative_synthesis` phase still runs and is surfaced **alongside** it (state
field + generic HTML `.narrative` div), i.e. "habillage template" that #1109 §5
wants gone.

**Why a fix-intent issue, not an in-audit fix**: removing the phase is the
correct anti-pendule action (delete the bypass so the LLM path is the only one),
and it is **safe** (`deep_synthesis` does not hard-consume the narrative output —
it recomputes convergence via `build_convergent_synthesis`; `narrative_synthesis`
is only an optional citable artifact field, `deep_synthesis_agent.py:163`). But
the removal breaks **7+ DAG assertions** across
`test_spectacular_workflow_dag.py:54` and `test_spectacular_regression_suite.py`
(lines 118/261/284/321/531/566/573 — a writer, capability assertions, and
`depends_on` assertions) — a coordinated pipeline change, beyond FB-33's
"minimal fix" scope (DoD explicitly allows fix-intent issues). → **#1115**.

---

## 6. Item 3 — Final-run config ✅ PASS (no fix needed)

### 6a. `LLM_DETERMINISTIC_MODE` — not forced
The spectacular run does NOT force determinism. The env var is **opt-in** and
only *read* by `_get_determinism_params` (`invoke_callables.py:208`), which (per
#1109 §3) suppresses temperature/seed for reasoning models like `gpt-5-mini`
anyway. **No non-test code SETS `LLM_DETERMINISTIC_MODE`**; no spectacular or
soutenance script (`scripts/`, `examples/`) sets it. The only `os.environ[…]=`
assignments are in **tests** (`test_track_xx_extraction_variance.py`,
`test_track_aa_model_aware_determinism.py`) which set it to test the determinism
logic, then `pop` it. ✅ The spectacular path embraces variance.

### 6b. Golden test — structure-only, does NOT freeze prose
`tests/golden/test_spectacular.py` is a **structural** regression test (DoD
#365): ≥28 populated state fields, ≥3 ATMS hypotheses, ≥5 FOL formulas, ≥1 JTMS
retraction cascade, etc. It runs against a **pre-recorded frozen fixture**
(`doc_a_golden.json`) — no live LLM, no prose string-comparison. It does NOT
assert any generated prose is byte-identical across runs. ✅ No prose-freezing
golden test (structure-only, exactly as #1109 §4 requires).

**Minor stale-DoD note**: the golden test's docstring lists "state.narrative_synthesis
present and cites ≥5 fields" as a DoD item. If #1115 removes `narrative_synthesis`
from spectacular, that DoD line goes stale (the frozen fixture still has it, so
the test keeps passing; only the docstring needs updating). Captured in #1115.

---

## 7. #1109 §4 checklist — final status

| §4 item | Owner | Status |
|---------|-------|--------|
| Descent `_beam_descent` | FB-30 #1110 | ✅ DONE (merged `d7126089`) |
| Wide-net pre-gating | FB-30 #1110 | ✅ DONE |
| Synthesis Section 9 count-template `_build_final_synthesis` | FB-31 #1111 | ✅ DONE (merged `fd3831a8`) |
| `narrative_synthesis_plugin` label | FB-31 #1111 | ⚠️ labeled, but phase still wired into spectacular → **#1115** (FB-33 follow-up) |
| **one-shot fallback `_run_one_shot`** | **FB-33** | ✅ **AUDITED — genuine LLM last resort, not a template** (§3) |
| **Sweep other mechanical loops** | **FB-33** | ✅ **DONE — 6/7 clean, 1 residual → #1115** (§4) |
| **Final-run config (no forced determinism, no prose-freeze)** | **FB-33** | ✅ **CONFIRMED** (§6) |

**All 7 §4 items addressed.** The descent + synthesis sites are de-castrated;
`_run_one_shot` + determinism + golden test are clean; the lone residual
(narrative template on spectacular) is captured as fix-intent **#1115**.

---

## 8. Actions delivered (this audit, file-disjoint)

- **This report** (`docs/reports/FB33_DECASTRATION_RESIDUAL_AUDIT.md`).
- **Fix-intent issue #1115** — remove template `narrative_synthesis` phase from
  spectacular (coordinated DAG test updates).
- **1-line docstring fix** — `_invoke_deep_synthesis`
  (`invoke_callables.py:6290`) said "runs the 9-section **template-driven**
  synthesis"; stale/misleading post-FB-31 (Section 9 is LLM fail-loud). Corrected
  to state sections 1-8 are grounded-over-state and Section 9 `final_synthesis`
  is LLM-conducted fail-loud. (Docstring only — no behavior/test change.)

**No production behavior change** in this audit PR (the narrative removal is
deferred to #1115; the docstring fix is comment-only). This keeps the audit PR
low-risk and file-disjoint from FB-32 (po-2025 runs/measurements).

### Incidental finding (pre-existing, out of FB-33 scope) — stale spectacular DAG test

While smoke-testing, `test_spectacular_workflow_dag.py::test_phase_count` and
`::test_all_expected_phases_present` **fail**. Verified **pre-existing on clean
`origin/main fd3831a8`** (stashed my edit → still fails → not FB-33-introduced).
Cause: the tests assert **exactly 17 phases** with a fixed name set, but
`build_spectacular_workflow` has grown to ~25+ phases over many PRs (#504
solvers, #506 KB/tweety, #507 belief_revision, #508 synthesis, #534
deep_synthesis, …). The expected-set/count was never updated. This is workflow
test-maintenance debt, **unrelated to de-castration** — left for a separate
cleanup (not FB-33). Noted here only so the PR's CI red on these 2 tests is
understood as pre-existing, not a regression.

---

## 9. Anti-pendule / privacy

- **Anti-pendule**: every fix here is subtraction or documentation. The one
  deletion due (narrative phase, #1115) removes a template bypass so the LLM
  path is the only one — no "smarter template" counterweight added. FB-18
  grounded synthesis + the restored agentic descent were NOT touched.
- **Privacy HARD**: opaque IDs only; no `raw_text`/`full_text`/source identifiers
  in any artifact.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
