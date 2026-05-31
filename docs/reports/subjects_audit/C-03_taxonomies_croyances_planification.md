# Audit C-03: Section I-C/D/E Taxonomies + Croyances + Planification (11 sujets)

**Issue**: #781 (C-03) | **Epic**: #744 | **Date audit**: 2026-05-31

## Préambule — Table de correspondance

| Code sujet | Statut | Lien Epic A si traité |
|------------|--------|-----------------------|
| 1.3.1 Schémas argumentatifs | 🟡 Partial (dialogue typology only) | — |
| 1.3.2 Classification sophismes | 🟢 Treated (via student 2.3.2) | #753 (A-07) |
| 1.3.3 Ontologie argumentation | 🔴 Angle mort | — |
| 1.4.1 TMS | 🟢 Treated | #748 (A-04) |
| 1.4.2 Révision croyances | 🟢 Treated (trunk) | — |
| 1.4.3 Raisonnement non-monotone | 🟢 Treated (trunk) | — |
| 1.4.4 Mesures d'incohérence | 🔴 **Angle mort prioritaire** | — |
| 1.4.5 Révision multi-agents | 🟡 Partial (docstring overpromises) | — |
| 1.5.1 Planificateur symbolique | 🔴 Angle mort (low priority) | — |
| 1.5.2 Vérification formelle | 🟢 Treated (trunk, 15 phases) | — |
| 1.5.3 Contrats argumentatifs | 🔴 Angle mort (lowest priority) | — |

## Résultats détaillés

### 🟢 TREATED (4)

**1.3.2 Classification des sophismes** — Taxonomy underpinning student project 2.3.2. Code: `TaxonomySophismDetector` (400+ sophismes), `fallacy_family_definitions.py` (8 families/28 labels), `fallacy_taxonomy_service.py`. Cross-ref → Epic A #753 (A-07).

**1.4.1 TMS** — Student project (score 85%). Code: `services/jtms/jtms_core.py`, `atms_core.py`, `agents/jtms_agent_base.py`, `plugins/atms_plugin.py`. Cross-ref → Epic A #748 (A-04).

**1.4.2 Révision de croyances (AGM)** — Trunk implementation: `belief_revision_handler.py` with Dalal/Levi/Kernel operators, `belief_revision_plugin.py`, `tweety_logic_plugin.py:302 revise_beliefs`. Wired into `formal_verification.py` phase 14. Exceeds spec scope.

**1.4.3 Raisonnement non-monotone** — Trunk: `cl_handler.py` (OCF/System Z), `delp_handler.py` (DeLP), `aspic_handler.py` (defeasible rules). Plugin: `query_conditional_logic`. Minor caveat: default logic and circumscription not covered (OCF/System Z satisfies "au moins une approche").

**1.5.2 Vérification formelle** — Trunk: `workflows/formal_verification.py` — 15-phase pipeline integrating PL/FOL/Modal consistency, Dung/ASPIC+/ADF/bipolar, DL/CL, JTMS/ATMS, AGM revision. Best-covered untracked subject. Caveat: no external theorem-prover (Lean/E/SPASS).

### 🟡 PARTIAL (2)

**1.3.1 Taxonomie des schémas argumentatifs** — `debate/protocols.py` has Walton-Krabbe dialogue protocols with `scheme: Optional[str]` field, but this is dialogue typology, NOT a structured Walton scheme taxonomy (~60 schemes with critical questions). `scheme` is a free string placeholder. **Value: MEDIUM** — would complement fallacy taxonomy (1.3.2).

**1.4.5 Révision multi-agents (CrMas)** — `belief_revision_handler.py:7` docstring claims "CrMas" but only loads `{"dalal", "levi"}` single-agent operators. No Java class binding for `CrMasRevision`. Governance voting (2.1.6) handles consensus via voting, not belief revision. **Value: MEDIUM** — docstring overpromises (correctness liability).

### 🔴 ANGLE MORTS (4)

**1.4.4 Mesures d'incohérence** — ⭐ TOP PICK. `pl_handler.py` does binary consistency checks only. No `logics.pl.analysis` measure classes, no MUS enumeration, no MaxSAT. **HIGH value + LOW effort**: Tweety `logics.pl.analysis` already on classpath; new handler plugs into `formal_verification._has_inconsistency`. Best ROI of untreated subjects.

**1.3.3 Ontologie argumentation** — DL handler provides reasoning substrate but no OWL ontology artifact, no `owlready2`/Protégé integration. **Value: MEDIUM-LOW** (research-grade, standalone).

**1.5.1 Planificateur symbolique** — `StrategicPlanner` is LLM-driven task decomposer, NOT symbolic planner. No PDDL/Tweety `action` binding. **Value: LOW-MEDIUM** (niche).

**1.5.3 Contrats argumentatifs** — No code at all. No blockchain, no Solidity, no contract DSL. **Value: LOW** (tangential to argumentation core).

## Synthèse C-03

- **4/11 🟢 Treated** (1 student + 3 trunk)
- **2/11 🟡 Partial** (1.3.1 Walton schemes, 1.4.5 CrMas)
- **5/11 🔴 Angle morts** — priorité: 1.4.4 (HIGH) > 1.3.1/1.4.5 (MEDIUM) > 1.3.3/1.5.1 (LOW-MEDIUM) > 1.5.3 (LOW)

## Fichiers sources
- `argumentation_analysis/workflows/formal_verification.py`
- `argumentation_analysis/agents/core/logic/{belief_revision_handler,cl_handler,dl_handler,pl_handler,qbf_handler}.py`
- `argumentation_analysis/plugins/tweety_logic_plugin.py`
- `argumentation_analysis/agents/core/informal/taxonomy_sophism_detector.py`
- `argumentation_analysis/agents/core/debate/protocols.py`
- `argumentation_analysis/orchestration/hierarchical/strategic/planner.py`
- `docs/projets/fondements_theoriques.md` (specs 1.3/1.4/1.5)
