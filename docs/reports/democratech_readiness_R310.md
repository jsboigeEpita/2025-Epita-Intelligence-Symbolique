# Democratech Readiness — R310

**Date**: 2026-06-02
**Author**: Claude Code @ myia-po-2023
**Base**: `3b11ac17` (main, post-R310)
**Issue**: #78 (ROADMAP: Vers Democratech — Plan complet post-intégration)
**Nature**: Décision-support — **PAS d'implémentation, PAS de choix de direction imposé**

---

## 0. À l'attention de l'utilisateur

Ce document est un **menu de décision-support**. Il rafraîchit l'état-des-lieux du projet après la convergence des Epics A/B/C (juin 2026) et propose 5 macro-objectifs candidats avec effort/valeur/risque. **Le choix vous appartient.**

---

## 1. État-des-lieux actualisé (juin 2026)

### 1.1 Delta depuis le tableau #78 « post-Epic G » (mars 2026)

Chaque valeur a été **vérifiée contre le code actuel** (import + introspection runtime), pas recopiée de #78.

| Dimension | #78 (mars 2026) | **Actuel (juin 2026)** | Delta |
|-----------|:---:|:---:|:---:|
| Capabilities enregistrées | 35+ / « 46 » | **80** (53 components) | +74% |
| Pre-built workflows | 12 | **22** | +83% |
| Spectacular pipeline phases | 20 | **29** | +45% |
| Formal extended phases | 15 | 15 (stable) | = |
| API routers / routes | — | **9 routers / 49 routes** (46 HTTP + 3 WS) | nouveau |
| Tests | ~3160 | **~13k fonctions / 719 fichiers** | +312% |
| External solvers routés | 4 | 4 (EProver, Prover9, SPASS, Clingo) | = |
| Architecture docs | 5 | 5 (tous présents) | = |

### 1.2 P0 Gaps de #78 — TOUS RÉSOLUS

| Gap P0 | Statut | Preuve |
|--------|--------|--------|
| Narrative synthesis saute en mode pipeline | ✅ **RÉSOLU** | Phase réelle dans `full`/`spectacular`/`sherlock_modern`, invoke callable `_invoke_narrative_synthesis` exécute inconditionnellement |
| External solvers pas routés dans spectacular | ✅ **RÉSOLU** | `fol_solver` + `modal_solver` comme phases DAG (depends_on fol/modal), EProver/Prover9 avec fallback TweetyBridge |
| DAG-level parallelism pas exploité | ✅ **RÉSOLU** | `WorkflowExecutor` calcule les niveaux d'exécution et lance `asyncio.gather()` par niveau |

### 1.3 Épigramme de convergence (juin 2026)

| Épic | Scope | Statut |
|------|-------|--------|
| **A — Audits Intégration** | 17/17 tracks (17 projets étudiants audités) | ✅ CLOS |
| **B — Audits Tests** | 15/15 tracks (~10 060 tests analysés) | ✅ CLOS |
| **C — Audits Sujets** | 8/8 tracks (72 sujets proposés audités) | ✅ CLOS |
| **G — Liberation Lego** | 14/14 (SK wiring, formal chain, solvers) | ✅ CLOS |
| **Présentable #717** | Préparation soutenance | ✅ CLOS |
| **Convergence #695** | Pipeline validation | ✅ CLOS |

### 1.4 Fix-intents post-audit

16 fix-intents générés par les audits R288. **15/16 mergés et vérifiés** (PR #878, 51 tests). Le dernier (#835, A-10 phase optionnelle local_llm) est en CI (PR #879).

### 1.5 Architecture actée (A-14)

- **FastAPI** = surface API unique (`api/main.py`, 49 routes)
- **Starlette** = proxy frontend-only (httpx vers FastAPI)
- **JTMS** = import guard graceful (`_JTMS_AVAILABLE`, dégrade sans crash)
- **AI Shield** = auth opt-in (`X-Shield-Token`, ouvert en dev, verrouillable via `SHIELD_ENDPOINT_TOKEN`)
- **Topologie** = deux processus couplés (Starlette :5003 → FastAPI :8095)

---

## 2. Menu — Macro-objectifs candidats post-convergence

### Option M1 : Durcissement Soutenance (S)

**Scope** : Fiabiliser le système pour une démonstration live en conditions réelles (soutenance, demo prof, jury).

| Dimension | Valeur |
|-----------|--------|
| **Effort** | S (1-2 sessions) |
| **Valeur jury** | HAUTE — une demo qui crash = impact direct sur la note |
| **Valeur utilisateur** | HAUTE — confiance avant soutenance |
| **Risque** | FAIBLE |
| **Dépendances** | Aucune |

**Actions typiques** :
- Script demo reproductible (`demonstration_epita.py` hardening)
- Smoke test E2E sur les 3 workflows core (light/standard/full)
- Vérification que les 49 routes API répondent sans erreur 500
- Docker compose validation (deux processus couplés)
- Nettoyage résidus cosmétiques identifiés en R309 (model_id, ws_proxy non enregistré)

---

### Option M2 : Cleanup Orchestrateurs Dépréciés (S)

**Scope** : Exécuter les actions du rapport B-09 (#875, en attente de ratification) — archiver 3 orchestrateurs pré-Registry, supprimer le stub `LogiqueComplexeOrchestrator`.

| Dimension | Valeur |
|-----------|--------|
| **Effort** | S (1 session) |
| **Valeur jury** | FAIBLE — invisible pour le jury |
| **Valeur utilisateur** | MOYENNE — réduit la dette technique, clarifie l'architecture |
| **Risque** | FAIBLE (les orchestrateurs sont dormants/dépréciés) |
| **Dépendances** | Ratification #875 par l'utilisateur |

**Actions typiques** (détaillées dans `docs/reports/orchestrator_migration_decision_b09.md`) :
- Supprimer `LogiqueComplexeOrchestrator` (109 LOC stub, 2 tests mockés)
- Archiver base `CluedoOrchestrator` (2-agent, superseded par ExtendedOrchestrator 3-agent)
- Archiver `ConversationOrchestrator` (1045 LOC dormant, superseded par 8-agent SK system)
- Archiver `RealLLMOrchestrator` shim (125 LOC, UnifiedPipeline replacement)

---

### Option M3 : Activation Mode Hiérarchique (L)

**Scope** : Réactiver le mode hiérarchique dormant (Strategic → Tactical → Operational). Les 302 tests sont en skip (`pytestmark`), l'infrastructure existe mais n'est pas branchée.

| Dimension | Valeur |
|-----------|--------|
| **Effort** | L (3-5 sessions) — réactivation + wiring + debugging |
| **Valeur jury** | MOYENNE — montre un 3e mode d'orchestration au-delà de pipeline/conversational |
| **Valeur utilisateur** | HAUTE — débloque les workflows complexes multi-niveaux |
| **Risque** | HAUT — code dormant depuis des mois, dépendances potentiellement cassées |
| **Dépendances** | Aucune bloquante, mais le mode hiérarchique n'a jamais été testé en conditions réelles |

**Actions typiques** :
- Retirer les `pytestmark = pytest.mark.skip` sur 302 tests hiérarchiques
- Brancher les adaptateurs opérationnels sur les agents réels (pas les mocks)
- Tester le mode hiérarchique avec le workflow `hierarchical_fallacy`
- Déboguer les singletons/dépendances croisées (cause initiale du skip)

---

### Option M4 : Workflow Democratech Complet (M)

**Scope** : Réaliser la Phase 2 de #78 — workflow de délibération citoyenne multi-tour avec API propositions, vote, et dashboard temps réel. L'infrastructure de base existe (22 workflows, 49 routes API, 3 WebSocket channels).

| Dimension | Valeur |
|-----------|--------|
| **Effort** | M (2-3 sessions) — le scaffolding existe (workflow `democratech` 9 phases, proposal API 9 endpoints, React dashboard) |
| **Valeur jury** | HAUTE — le "flagship" du projet Democratech |
| **Valeur utilisateur** | HAUTE — cas d'usage central de la roadmap |
| **Risque** | MOYEN — les composants existent mais le workflow complet n'a jamais été testé E2E avec de vrais agents |
| **Dépendances** | M1 recommandé en préalable (fiabilisation avant demo) |

**Actions typiques** :
- Vérifier le workflow `democratech` (9 phases) en conditions réelles avec LLM
- Tester les 9 endpoints proposals + 3 channels WebSocket en intégration
- Valider le dashboard React gouvernance avec données réelles
- Scénario demo : simulation de délibération citoyenne avec 3-5 propositions

---

### Option M5 : Scalabilité & Batch Processing (M)

**Scope** : Optimiser pour le traitement de corpus complets (Phase 3 de #78). Objectif : corpus complet en <1h avec caching LLM.

| Dimension | Valeur |
|-----------|--------|
| **Effort** | M (2-3 sessions) |
| **Valeur jury** | MOYENNE — les performances impressionnent mais le jury valorise plus la fonctionnalité |
| **Valeur utilisateur** | HAUTE — débloque l'analyse à grande échelle |
| **Risque** | MOYEN — profiling + optimisation, pas de réécriture majeure |
| **Dépendances** | M1 recommandé (stable avant optimisation) |

**Actions typiques** :
- Profiling du chemin critique (déjà documenté dans `spectacular_profiling.md`)
- Caching LLM (`LLM_CACHE_MODE=replay`) pour reproductibilité
- Batch processing optimisé (traitement parallèle multi-sources)
- Monitoring basique (timing par phase, hit/miss cache)

---

## 3. Trade-offs — Recommandation neutre

**Effort minimal, impact maximal pour la soutenance** : M1 (durcissement) est un préalable naturel à M4 (Democratech demo) et M5 (scalabilité). M2 (cleanup) peut se faire en parallèle sans risque. M3 (hiérarchique) est le plus risqué et le moins urgent.

**Séquence possible** : M1 → M2 → M4 → M5, avec M3 en option "si le temps le permet".

**Séquence alternative** : Si l'objectif est le demo Democratech pour la soutenance, M1 + M4 suffisent. M2 et M5 sont des améliorations post-soutenance.

**Le choix reste ouvert.** Ce menu est conçu pour steerer la décision, pas pour l'imposer.
