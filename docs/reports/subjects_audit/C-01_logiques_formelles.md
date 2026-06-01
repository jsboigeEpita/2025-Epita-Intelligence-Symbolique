# Audit C-01: Section I-A "Logiques Formelles" (6 sujets)

**Issue**: #779 (C-01) | **Epic**: #744 | **Date audit**: 2026-05-31 | **Enriched**: 2026-06-01 (po-2023)

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
|------------|--------|-----------------------|
| 1.1.1 PL (propositionnelle) | 🟢 Code exists, no subject doc | — |
| 1.1.2 FOL (premier ordre) | 🟢 Code exists, no subject doc | — |
| 1.1.3 Modale | 🟢 Code exists, no subject doc | — |
| 1.1.4 DL (description / defeasible) | 🟢 Code exists, no subject doc | — |
| 1.1.5 QBF | 🟢 Treated (subject + code) | A-01 #745 🟢 INTÉGRÉ (fermée) |
| 1.1.6 CL (conditionnelle / circconscriptionnelle) | 🟢 Code exists, no subject doc | — |

## Résultats

### 1.1.1 PL (Logique Propositionnelle) — 🟢 TREATED (code)
- **Handler**: `argumentation_analysis/agents/core/logic/pl_handler.py` — `PLHandler` wrapping Tweety `SimplePlReasoner`
- **Agent**: `propositional_logic_agent.py` + `pl_formula_sanitizer.py`
- **Plugin**: `tweety_logic_plugin.py:115` `check_propositional_consistency` + `:443` `solve_sat`
- **JVM-free fallback**: `sat_handler.py` (PySAT, no JVM)
- **Config**: `PLSolverChoice` in `core/config.py` switches between Tweety and PySAT
- **Subject doc**: None in `docs/projets/sujets/`
- **Assessment**: Most mature logic handler (config switch, sanitizer, two backends). No angle mort.

### 1.1.2 FOL (Logique du Premier Ordre) — 🟢 TREATED (code)
- **Handler**: `fol_handler.py` — `FOLHandler` with two backends: Tweety and Prover9 (`prover9_runner.py`)
- **Agent**: `fol_logic_agent.py` + `first_order_logic_agent_adapter.py`
- **Plugin**: `tweety_logic_plugin.py:136` `check_fol_consistency`
- **Tests**: Signature pre-declaration, EProver/SPASS integration
- **Subject doc**: None
- **Assessment**: Strong test coverage, multi-backend. No angle mort.

### 1.1.3 Logique Modale — 🟢 TREATED (code)
- **Handler**: `modal_handler.py` — `ModalHandler` supporting `SimpleMlReasoner` (Tweety) and `SPASSMlReasoner` (external SPASS binary)
- **Agent**: `modal_logic_agent.py`
- **Plugin**: `tweety_logic_plugin.py:156` `check_modal_satisfiability` (S5/K/T)
- **Config**: `ModalSolverChoice`
- **Subject doc**: None
- **Assessment**: Multiple solver backends. No angle mort.

### 1.1.4 DL (Logique de Description) — 🟢 TREATED (code)
- **Handler**: `dl_handler.py` — `DLHandler` with ALC: atomic concepts/roles/individuals, complement/union/intersection, existential/universal restrictions, TBox+ABox
- **Plugin**: `tweety_logic_plugin.py:380` `check_dl_consistency`
- **Origin**: PR #81 (`feat(logic): add Description Logic and Conditional Logic handlers`)
- **Subject doc**: None
- **Minor caveat**: `is_consistent` returns `True` unconditionally on successful query — latent correctness bug worth tracking

### 1.1.5 QBF — 🟢 TREATED (subject + code) → Epic A #745 (A-01)
- **Subject doc**: `docs/projets/sujets/sujet_1.1.5_formules_booleennes_quantifiees.md`
- **SUIVI entry**: `SUIVI_PROJETS_ETUDIANTS.md:16-22` (stale — still claims "aucun code Python")
- **Handler**: `qbf_handler.py` + `qbf_native.py` (JVM-free fallback)
- **Plugin**: `tweety_logic_plugin.py:596` `check_qbf`
- **Issue**: #167 (should be closed or re-scoped — Python code now exists)
- **Cross-ref**: Confirmed → Epic A issue #745 (A-01)

### 1.1.6 CL (Logique Conditionnelle) — 🟢 TREATED (code)
- **Handler**: `cl_handler.py` — `CLHandler` with non-monotonic reasoning, conditionals `(B|A)`, `SimpleCReasoner` + optional `ZReasoner` (System Z)
- **Plugin**: `tweety_logic_plugin.py:410` `query_conditional_logic`
- **Origin**: PR #81 (same as DL)
- **Subject doc**: None
- **Assessment**: Functional, no gap.

## Wiring Matrix (enriched R291)

| Logique | Handler | Agent | Kernel Function | Workflow Pipeline | Registry | Wiring |
| --- | --- | --- | --- | --- | --- | --- |
| PL | `pl_handler.py` | `propositional_logic_agent.py` | ✅ `check_propositional_consistency` | ✅ pass1/pass2 | ✅ `tweety_logic_plugin` | ✅ Full |
| FOL | `fol_handler.py` | `fol_logic_agent.py` + adapter | ✅ `check_fol_consistency` | ✅ pass1/pass2 | ✅ `tweety_logic_plugin` | ✅ Full |
| Modal | `modal_handler.py` | `modal_logic_agent.py` | ✅ `check_modal_satisfiability` | ✅ pass1/pass2 | ✅ `tweety_logic_plugin` | ✅ Full |
| QBF | `qbf_handler.py` + `qbf_native.py` | — | ✅ `solve_qbf` | ✅ QBF pass | ✅ `qbf_reasoning` | ✅ Full (A-01 fermée) |
| DL | `dl_handler.py` | — | ✅ `check_dl_consistency` | ⚠️ Plugin-only | ✅ `tweety_logic_plugin` | ⚠️ Partial |
| CL | `cl_handler.py` | — | ✅ `query_conditional_logic` | ⚠️ Plugin-only | ✅ `tweety_logic_plugin` | ⚠️ Partial |

## Synthèse C-01

**6/6 sujets couverts par le code existant.** Aucun angle mort technique. Tous disposent d'un handler Tweety + plugin SK + JAR dans `libs/tweety/`.

**4/6 Fully Wired** (PL, FOL, Modal, QBF — intégrés au pipeline séquentiel et conversationnel). **2/6 Partially Wired** (DL, CL — kernel function exposée mais pas de workflow pipeline dédié).

**Gap documentation**: Seul 1.1.5 (QBF) a un fichier sujet dans `docs/projets/sujets/`. Les 5 autres logiques sont implémentées mais jamais documentées comme sujets pédagogiques. Ce n'est pas un angle mort technique mais un gap de documentation pédagogique.

**Gap état SUIVI**: L'entrée QBF (#167) est obsolète — le handler Python existe depuis PR #88.

## Enhancement proposals

| # | Issue | Priorité | Justification |
| --- | --- | --- | --- |
| E1 | `enhancement(c-01): add DL/CL workflow callables to unified_pipeline` | **LOW** | DL et CL ont des kernel functions mais pas de callable dans `invoke_callables.py` ni de state writer. Ils ne sont accessibles que via appel direct du plugin. |

## Fichiers sources
- `argumentation_analysis/agents/core/logic/` — tous les handlers (pl, fol, modal, dl, qbf, cl)
- `argumentation_analysis/plugins/tweety_logic_plugin.py` — exposition SK (614 LOC, 15+ kernel functions)
- `argumentation_analysis/orchestration/invoke_callables.py` — pipeline callables
- `argumentation_analysis/orchestration/registry_setup.py` — capability registration
- `libs/tweety/` — JARs Tweety `logics.{pl,fol,ml,dl,qbf,cl}-1.28`
