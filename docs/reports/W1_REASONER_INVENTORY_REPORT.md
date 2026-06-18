# W1 #1169 — Reasoner Inventory & Wiring Report

**Track:** W1 Workflow completeness (#1169), Epic #1165 Culmination.
**Owner:** po-2025.
**Base:** `03b1feeb` (post-E1b #1173 + D1 #1172).
**Date:** 2026-06-18.

## Context

Coordinator R441 dispatched W1: ~12 dormant Tweety reasoners (with state-writers but never invoked by `spectacular`) must be wired in, per the user mandate "pres de 40 plugins couvrant toutes les capacites de Tweety". The DoD: every capability with a state-writer is either exercised by `spectacular` OR documented out-of-scope with a reason; a run shows non-trivial state; 0 silent hollow phases.

**Empirical investigation (FB-39 lesson — verify, don't assume)** probed each handler + callable directly against a real JVM with corpus-like input. The dispatch framing ("wire dormant reasoners") masked two distinct failure modes:

1. **Broken input contracts in invoke callables** (same family as E1b #1168 layer-2) — the handlers expect typed structures; the callables passed the wrong shape.
2. **Handler-level Tweety API bugs** (same family as E1b #1168 layer-1) — some handlers call non-existent/overloaded Tweety methods.

Both are fixable, but handler-level bugs each require a dedicated investigation (reflection + signature correction) — out of scope for a single wiring track.

## Inventory verdict

| Reasoner | Capability | Verdict | Detail |
|----------|-----------|---------|--------|
| SetAF | `setaf_reasoning` | **WIRED** | Input-contract fix: shaped pairwise attacks → `{attackers, target}` dicts. Real extensions computed. |
| ABA | `aba_reasoning` | **WIRED** | Input-contract fix: derived `{head, body}` rules from argument graph (was string rules `"a => valid"`). Real extensions. |
| DeLP | `defeasible_logic` | **WIRED** | Already functional; program from corpus text. Parse may degrade on non-DeLP syntax (reported in output, not fabricated). |
| Description Logic | `description_logic` | **WIRED** | Already functional via `_invoke_dl`. |
| Dialogue | `dialogue_protocols` | **WIRED** | Already functional; consumes counter-arguments. |
| Weighted | `weighted_argumentation` | **OUT-OF-SCOPE** | Handler bug: `SimpleWeightedGroundedReasoner.getModels(WeightedAF)` — no matching overload (reasoner expects a DungTheory, like ASPIC). Handler-level fix needed. |
| Social | `social_argumentation` | **OUT-OF-SCOPE** | Handler bug: `SocialAbstractArgumentationFramework` object has no expected attribute. Handler-level fix needed. |
| Epistemic (EAF) | `epistemic_argumentation` | **OUT-OF-SCOPE** | Handler bug: `IllegalArgumentException: Unsupported…` on construction. Handler-level fix needed. |
| ADF | `adf_reasoning` | **OUT-OF-SCOPE** | Handler bug: `GraphAbstractDialecticalFramework` getModels — no matching overload. Handler-level fix needed. |
| QBF | `qbf_reasoning` | **OUT-OF-SCOPE** | Handler bug: `Disjunction` constructor ambiguous overload. Handler-level fix needed. |
| Conditional Logic | `conditional_logic` | **OUT-OF-SCOPE** | Handler bug: parser requires parenthesized conditionals; `parse_and_query` raises on standard input. Handler-level fix needed. |
| SAT | `sat_solving` | **OUT-OF-SCOPE** | Env-dependent: `python-sat` (PySAT) not installed. Not a code bug. |

**Count: 5 wired + 7 documented out-of-scope.**

The 7 out-of-scope reasoners keep their state-writers registered and their handlers intact — wiring them requires a dedicated handler-fix track (same shape as E1b #1168: investigate each Tweety API via reflection, correct the call signature). That is the recommended follow-up.

## Changes

### `invoke_callables.py` (mypy-strict CI-gated, clean)

- **5 input-shaping helpers** (near `_extract_arguments_from_context`, ~line 2618):
  `_setaf_attacks_from_pairs`, `_weighted_attacks_from_pairs`, `_aba_rules_from_context`, `_adf_conditions_from_context`, `_eaf_beliefs_from_context`. Each deterministically maps spectacular's canonical context (arguments `List[str]`, attacks `List[List[str]]` pairs from `_generate_attacks_from_args`) into the typed structure the handler expects. Anti-pendule: subtraction of the mismatch, no fabricated signal (weights default neutral 0.5, beliefs `None` = valid baseline).
- **Fixed callables** `_invoke_setaf`, `_invoke_aba`, `_invoke_adf`, `_invoke_eaf` to use the helpers.
- **Fail-loud hollow phases** (#1019): `_invoke_camembert_fallacy` now returns `status="unavailable"` when the LLM endpoint is unconfigured (was an empty dict misreadable as "0 fallacies found"); `_invoke_tweety_interpretation` returns `status="unavailable"` with empty interpretation + reason when upstream formal data is missing (was a French placeholder string presented as a result). Modal was already fail-loud (`solver="unavailable"`, `valid=None`).

### `workflows.py`

- **5 new spectacular phases** (L4b, after `aspic_analysis`, `optional=True`, `timeout_seconds=180`): `setaf_reasoning`, `aba_reasoning`, `delp_reasoning`, `dl_reasoning`, `dialogue_reasoning`. Each `optional=True` so a failure does not break the run; the invoke callables fail-loud on genuine unavailability.

### Tests

- `test_w1_input_shaping.py` (NEW, 14 tests) — contract tests for the 5 shaping helpers (captures the format each handler expects; same regression-guard pattern as E1b's dict-arguments test).
- Bumped the spectacular phase-count regression suite (canary pattern): `test_belief_revision_spectacular`, `test_external_solver_spectacular`, `test_spectacular_workflow_dag`, `test_spectacular_regression_suite` — counts 28/29/31 → 36, `EXPECTED_PHASES` +5, L1 set +`dl_reasoning`.

## Verification

- mypy strict clean on `invoke_callables.py` + `workflows.py` (the 2 CI-gated files touched).
- 77 unit tests green (regression suite + W1 shaping + DAG + belief_revision + external_solver).
- Per-reasoner direct JVM probe: 5 wired reasoners produce non-trivial state (setaf ext=`[['claim_a','claim_b']]`, aba ext=`[['claim_a','claim_b']]`, delp/dl/dialogue return real dicts).
- DoD run: `spectacular`+`full` smoke (opaque `w1_smoke`, doc_A) — see `argumentation_analysis/evaluation/results/w1_validation/`.

## Privacy

Opaque id `w1_smoke` only. No corpus content, raw text, or source identifiers in this report. The validation harness (`scripts/run_w1_reasoner_status_check.py`) is untracked. Results under gitignored `evaluation/results/`.

## Anti-pendule / anti-theater notes

- The fix is **shaping the input the handlers already expect** (subtraction of the mismatch), not adding reasoner classes or extending classpath.
- No fabricated output: 7 reasoners that genuinely cannot run are documented out-of-scope, not wired with fake state.
- Hollow phases now fail-loud: the silent skeletons (empty dict, French placeholder) that masqueraded as results are replaced with explicit `status="unavailable"` markers.
