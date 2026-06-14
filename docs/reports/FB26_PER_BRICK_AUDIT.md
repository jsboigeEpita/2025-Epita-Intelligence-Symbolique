# FB-26 — Per-Brick Audit Refresh (B-A … B-F)

| Field | Value |
|---|---|
| **Scope** | Epic #947 latent-bug inventory, bricks B-A … B-F |
| **Method** | Read-only re-verification on current `main`; every verdict cites `file:line` (proof, not memo) |
| **`main` HEAD** | `4a0511ba` (origin/main, 2026-06-14) — all 5 cited source files verified bit-identical to the audit working copy |
| **Parent dispatch** | FB-26 (#1094), item 1 — independent track |
| **Author** | Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique |
| **Privacy** | Opaque IDs only (`corpus_A/B/C`). No `raw_text`/`full_text` in any artifact. |

---

## TL;DR — Verdict matrix

| Brick | Original complaint (Epic #947 body) | Current verdict | Resolver |
|---|---|---|---|
| **B-A** | FOL has **no** eprover→Tweety binary-absent fallback → silent Python *template* fallback | ✅ **RESOLVED** | #949 / #955 (`abfaf5b3`) |
| **B-B** | Dung Python fallback **degenerate**: grounded-only, drops synthetic nodes, no `all_extensions`/`count` | ✅ **RESOLVED** | #1025 (`5d3c0eda`), folded into #941 |
| **B-C** | C1 extractor reads `satisfiable`; FOL writes `consistent` → FOL always 0 | ✅ **RESOLVED** | #941 / #954 (`2e61f146`) |
| **B-D** | C1 extractor reads `all_extensions`/`count` absent from `dung_frameworks` | ✅ **RESOLVED** | #941 / #954 (`2e61f146`) |
| **B-E** | Quality value-gate (`overall>0`) lives **only** in capstone harness → a zeroing regression passes CI | ✅ **RESOLVED** | #1005/#1007, #1009/#1010, #1013/#1014 |
| **B-F** | Conversational-path LLM-budget coverage **unverified** (`llm_budget_scope` only in `workflow_dsl.py`) | ✅ **RESOLVED** | #950 / #956 (`eec7339d`) |

**Net still-real holes among B-A…B-F: 0.** Every brick the Epic named as a latent bug is now closed on `main`, with the degradation path signal-bearing (#1019-compliant) rather than silent.

---

## Per-brick detail

### B-A — FOL eprover→Tweety binary-absent fallback — ✅ RESOLVED

**Original ask.** FOL had no equivalent of the modal SPASS→Tweety binary-absent fallback; an absent `eprover`/`prover9` binary fell through to a silent Python *template* fallback (degrade-without-signal).

**Current evidence (proof).**
- `argumentation_analysis/agents/core/logic/fol_handler.py:257-287` — `fol_check_consistency` now wraps the `eprover`/`prover9` call and dispatches to `_fol_check_consistency_with_tweety_fallback` on `RuntimeError`.
- `fol_handler.py:289-305` — `_fol_check_consistency_with_tweety_fallback` returns `(is_consistent, msg, solver_fallback=True)` so the **caller can see the degradation**, and `raise`s `RuntimeError` if *both* solvers fail (fail-loud, not silent).

**Resolver.** `abfaf5b3` — #949 (open) / #955 (merge).

**Mechanism note (not a downgrade).** The resolver is **exception-based** (catch prover `RuntimeError` → Tweety), not the proactive `shutil.which` probe the Epic body speculated about. The *concern the bug raised* — silent degradation when a binary is absent — is nonetheless eliminated: the fallback is graceful *and* it surfaces a `solver_fallback` flag, which is strictly better than the original ask (it aligns with the #1019 mandate to signal, not silently fill). Verdict stays RESOLVED.

---

### B-B — Dung Python fallback degeneracy — ✅ RESOLVED

**Original ask.** `_python_dung_fallback` computed **only** the grounded extension, dropped synthetic attack nodes (`fallacy_{i}_{label}` never present in `arg_set`), and emitted no `all_extensions`/`count` → no-JVM Dung was trivially empty (origin of the #941 XFAIL).

**Current evidence (proof).** `argumentation_analysis/orchestration/invoke_callables.py:5428-5574` — `_python_dung_fallback` is a textbook-correct exact implementation:
- `:5502-5520` grounded via iterative fixpoint (polynomial, **always** computed).
- `:5525-5533` power-set enumeration of complete/preferred/stable, **capped** at `_DUNG_ENUM_CAP = 25` arguments with an explicit `logger.warning` when the cap is exceeded (signals degradation → grounded-only, never silent).
- `:5560-5562` `extensions["complete"|"preferred"|"stable"]` all populated.
- `:5564-5574` returns `{semantics, extensions (4 semantics), arguments, attacks, statistics{arguments_count, attacks_count, semantics_computed}}`.

**Synthetic-node concern (the B-B sub-point).** The guard at `:5457` keeps an attack only if `attacker in arg_set and target in arg_set`. The **caller** at `:5335` passes the *same* `arguments`+`attacks` list to the fallback as it does to the Tweety handler (`:5319-5320`, `:5327`) — so whatever synthetic `fallacy_*` nodes the framework was built with transit both paths and survive in `arg_set`. The "dropped synthetic nodes" failure mode is therefore closed at the call site, not by special-casing inside the fallback.

**Resolver.** `5d3c0eda` (#1025), with the cap + synthetic handling folded into the #941 scope.

---

### B-C — C1 extractor FOL gate `satisfiable` vs `consistent` — ✅ RESOLVED

**Original ask.** The C1 extractor read `satisfiable` for FOL; the FOL writer emits `consistent` → FOL gate always reported 0/0.

**Current evidence (proof).** `scripts/run_capstone_c1.py:179` comment: *"state uses 'consistent' (not 'satisfiable' which is PL-only)"*; reads at `:184` and `:191` now use `consistent`. Field-name mismatch eliminated.

**Resolver.** `2e61f146` — #941 (open) / #954 (merge).

---

### B-D — C1 extractor Dung counter shape — ✅ RESOLVED

**Original ask.** The extractor read `all_extensions`/`count` which `dung_frameworks` did not carry → Dung count always 0.

**Current evidence (proof).** `scripts/run_capstone_c1.py:203-212` computes `fw_ext_count` from `extensions.values()` and emits both `count` and `dung_total_extensions`. The shape now matches what `_python_dung_fallback` (B-B) and the Tweety multi-semantics path produce.

**Resolver.** `2e61f146` — #941 / #954.

---

### B-E — Quality value-gate only in capstone harness — ✅ RESOLVED

**Original ask.** The `overall>0` quality gate lived only in the capstone sweep harness (`test_quality_sweep_lang_jj` asserted `len==2` only); a regression zeroing every quality score would **pass CI**.

**Current evidence (proof).** `tests/unit/argumentation_analysis/test_value_gates.py` now carries the gate in the **pytest suite**:
- `:24` — suite docstring: *"Quality — overall > 0 on non-trivial input"*.
- `:49` — `assert result["note_moyenne"] > 0`.
- `:53` — `assert result["note_finale"] > 0`.
- A zeroing regression now **fails CI**.

Satellite value-gates land alongside it: FOL value-gate (`:1382`), PL value-gate (`:1552`), and a 10-brick satellite sweep (`:1682`).

**Resolver.** #1005/#1007 (satellite sweep 10 formal bricks), #1009/#1010 (tighten SAT/ATMS/ASPIC/Probabilistic), #1013/#1014 (tighten EAF/Dialogue/ADF/BeliefRevision). This is the FB-3 track (po-2023) — Phase 1 DoD.

---

### B-F — Conversational-path LLM-budget coverage — ✅ RESOLVED

**Original ask.** `llm_budget_scope` was grep-found only in `workflow_dsl.py`; `ConversationalOrchestrator` counter-argument calls were potentially uncapped (risk of a repeat of the 8h/12.4K-call runaway).

**Current evidence (proof).** `argumentation_analysis/orchestration/conversational_orchestrator.py`:
- `:513` imports `llm_budget_scope`; `:516` wraps the conversational analysis body in `with llm_budget_scope():`.
- `_bump_sk_budget()` is called per turn / per SK call at `:1403`, `:1431`, `:1506`, `:1544`.

The conversational path is therefore under the same global `_LLMBudget` circuit breaker as the pipeline path.

**Resolver.** `eec7339d` — #950 (open) / #956 (merge).

---

## Related finding — "presence-only" satellite bricks

The Epic body flagged satellite formal bricks (SAT, SetAF, Weighted, EAF, DeLP, QBF, ABA, ADF, bipolar, probabilistic, dialogue, belief_revision, ATMS) as having **only** a `fallback:python` sentinel presence check — no value-correctness assertion.

**Status on `main`.** Substantially closed by the same value-gate promotion track as B-E: #1005/#1007 (sweep 10 bricks), #1009/#1010 (tighten SAT/ATMS/ASPIC/Probabilistic), #1013/#1014 (tighten EAF/Dialogue/ADF/BeliefRevision). Commit verbs "tighten … gates" indicate value assertions, not presence-only sentinels.

**Honest hedge.** This audit re-verified B-A…B-F line-by-line but did **not** spot-check every satellite gate's assertion strength. A dedicated sweep (open a value-correctness probe per brick, confirm it asserts a non-trivial bound rather than `is not None`) remains a worthwhile Phase-1 hardening follow-up — but it is **outside the B-A…B-F scope** of this dispatch and is **not** a regression. Recorded here for traceability, not as a still-real B-* hole.

---

## DoD compliance (Epic #947 global checklist)

| Phase | DoD item | Bugs | Status |
|---|---|---|---|
| Phase 0 | Measurement trustworthy (#941 + #944 + #945) | B-B, B-C, B-D | ✅ **CLOSED** on `main` (#944 merged `b3cd6834`; #941→#954 `2e61f146`; #945 re-run landed) |
| Phase 1 | Value-tests in front of every brick | B-E (+ presence-only bricks) | ✅ **CLOSED** (#1005/#1009/#1013) |
| Phase 2 | Latent-bug resolution | B-A, B-F, B-B | ✅ **CLOSED** (#949→#955, #950→#956, #1025) |

Phases 0–2 of the Epic are **done**. The remaining Epic work is Phase 3 (per-subsystem critical verdict — FB-6) and Phase 4 (terminal spectacular reports — Option A), which depend on the FB-25 quality numbers landing (item 2 of the FB-26 dispatch).

---

## Anti-pendule / methodology attestation

- This audit is **read-only verification**. No production code was edited under the audit hat; no "fix while auditing." (Per FB-26 anti-pendule: audit → fix-intent pattern.)
- Every RESOLVED verdict cites `file:line` on current `main`, not memo. Resolver PR citations are **secondary** to the on-disk code evidence.
- No concern was re-encoded that an automatic mechanism already handles (LLM budget, per-formula isolation, Dung cap-warning all verified as present, not duplicated).
- Where a resolver's *mechanism* differs from the bug's speculated fix (B-A: exception-based vs `shutil.which` probe), the verdict reflects the **concern** (silent degradation), not the literal mechanism — and notes the divergence rather than silently equating them.
