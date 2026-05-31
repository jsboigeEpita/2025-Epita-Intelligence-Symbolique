# Audit A-01: QBF (Quantified Boolean Formulas)

**Issue**: #167 (CLOSED) | **SUIVI**: Score 5% (non soumis) | **Date audit**: 2026-05-31
**Ré-audit R289**: DoD enrichi intent-fix (Epic A #742, Track A-01 #745)
**Author**: Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique

## Status: 🟢 Integrated — Pas de gap pipeline

The audit premise in `SUIVI_PROJETS_ETUDIANTS.md` is **partially incorrect**. Issue #167 is **CLOSED** and a complete QBF implementation exists — the "no Python code" claim is false.

## What exists in `argumentation_analysis/`

| Layer | File | Detail |
|---|---|---|
| JAR Tweety | `libs/org.tweetyproject.logics.qbf-1.28-with-dependencies.jar` | Tweety QBF module |
| JVM handler | `agents/core/logic/qbf_handler.py` | `QBFHandler` using Tweety `org.tweetyproject.logics.qbf` |
| JVM-free fallback | `agents/core/logic/qbf_native.py` | Pure-Python QBF AST + naive enumeration |
| TweetyBridge | `agents/core/logic/tweety_bridge.py:239` | `qbf_handler` lazy-loaded property |
| SK Plugin | `plugins/tweety_logic_plugin.py:596` | `@kernel_function check_qbf` |
| Capability Registry | `orchestration/registry_setup.py:759` | `qbf_handler` → capability `qbf_reasoning` |
| Invoke callable | `orchestration/invoke_callables.py:3454` | `_invoke_qbf` (JVM → native fallback → error) |
| State writer | `orchestration/state_writers.py:846` | `_write_qbf_to_state` |
| Workflow | `workflows/formal_verification.py:147-186` | `qbf_analysis` phase (capability `qbf_reasoning`) |
| NL guidance | `services/nl_to_logic.py:8` | LLM-only translation lesson |

**Tests**: `test_qbf_native.py`, `test_track_a_handlers.py`, `test_formal_verification.py`, plus integration tests (`test_qbf.py`).

## Preservation Assessment

- JAR present: ✅ `libs/org.tweetyproject.logics.qbf-1.28-with-dependencies.jar`
- QBF API: ✅ formula parsing, `check_validity`, `analyze_qbf`
- JVM-free path: ✅ pure-Python AST + enumeration
- Argumentation bridge: ✅ `credulous_acceptance_qbf`, `skeptical_acceptance_qbf`
- CapabilityRegistry: ✅ `qbf_handler` registered with `qbf_reasoning` capability
- Invoke callable: ✅ 3-level fallback (JVM → native Python → error)
- State writer: ✅ `_write_qbf_to_state` writes to `UnifiedAnalysisState`

## Gap Analysis

**No gap.** The previous audit noted "No capability registration in `core/capability_registry.py`" — this is superseded: the registration happens in `registry_setup.py` (line 759), which IS the canonical registration point for the CapabilityRegistry system.

The project **exceeds** the original student scope: ships both Tweety/JPype AND JVM-free paths, with 3-level fallback in the invoke callable.

## Fix-intents

**Aucun fix-intent ouvert.** L'intégration QBF est complète, wirée, testée, et dispose d'un fallback robuste.

## Recommended Action

**No work needed.** Issue #167 is correctly closed. Update `SUIVI_PROJETS_ETUDIANTS.md`:
- Score: 5% → 90% (in-house reimplementation)
- Integration: "JAR Tweety QBF + handler Python + native fallback"
- Issue: #167 → CLOSED

## Source Files

- `argumentation_analysis/agents/core/logic/qbf_handler.py`
- `argumentation_analysis/agents/core/logic/qbf_native.py`
- `argumentation_analysis/plugins/tweety_logic_plugin.py`
- `argumentation_analysis/workflows/formal_verification.py`

---

*Ré-audit R289 — Claude Code @ myia-po-2025:2025-Epita-Intelligence-Symbolique*
*Track A-01 #745 — Epic A #742*
