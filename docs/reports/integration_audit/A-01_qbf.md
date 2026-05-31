# Audit A-01: QBF (Quantified Boolean Formulas)

**Issue**: #167 (CLOSED) | **SUIVI**: Score 5% (non soumis) | **Date audit**: 2026-05-31

## Status: 🟢 Integrated

The audit premise in `SUIVI_PROJETS_ETUDIANTS.md` is **partially incorrect**. Issue #167 is **CLOSED** and a complete QBF implementation exists — the "no Python code" claim is false.

## What exists in `argumentation_analysis/`

| Layer | File | Detail |
|---|---|---|
| JVM handler | `agents/core/logic/qbf_handler.py` | `QBFHandler` using Tweety `org.tweetyproject.logics.qbf` |
| JVM-free fallback | `agents/core/logic/qbf_native.py` | Pure-Python QBF AST + naive enumeration |
| TweetyBridge | `agents/core/logic/tweety_bridge.py:239` | `qbf_handler` lazy-loaded property |
| SK Plugin | `plugins/tweety_logic_plugin.py:596` | `@kernel_function check_qbf` |
| Workflow | `workflows/formal_verification.py:147-186` | `qbf_analysis` phase (capability `qbf_reasoning`) |
| NL guidance | `services/nl_to_logic.py:8` | LLM-only translation lesson |

**Tests**: `test_qbf_native.py`, `test_track_a_handlers.py`, `test_formal_verification.py`, plus integration tests.

## Preservation Assessment

- JAR present: ✅ `libs/tweety/org.tweetyproject.logics.qbf-1.28-with-dependencies.jar`
- QBF API: ✅ formula parsing, `check_validity`, `analyze_qbf`
- JVM-free path: ✅ pure-Python AST + enumeration
- Argumentation bridge: ✅ `credulous_acceptance_qbf`, `skeptical_acceptance_qbf`

## Gap Analysis

- **No capability registration in `core/capability_registry.py`** — registration happens at workflow level (`formal_verification.py`), not in the registry class
- The project **exceeds** the original student scope: ships both Tweety/JPype AND JVM-free paths

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
