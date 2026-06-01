# C-03: Audit Sujets — Sections I-C/D/E Taxonomies + Croyances + Planification

**Track**: C-03 #781 (Epic C #744)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
**Scope**: 11 sujets (3 taxonomies + 5 croyances + 3 planification)

---

## Table prealable — Status des sujets

| Code | Sujet | Statut | Lien Epic A | Pipeline wiring |
|------|-------|--------|-------------|-----------------|
| 1.4.1 | Systemes de maintenance de la verite (TMS) | 🟢 Traite | A-04 #748 | `jtms_service`, `atms_service` registres |
| 1.3.1 | Taxonomie des schemas argumentatifs | À auditer | — | Aucun |
| 1.3.2 | Classification des sophismes | À auditer | — | Partiel (3-tier hybrid, 8 familles) |
| 1.3.3 | Ontologie de l'argumentation | À auditer | — | Aucun |
| 1.4.2 | Revision de croyances (AGM) | À auditer | — | `belief_revision` registre |
| 1.4.3 | Raisonnement non-monotone | À auditer | — | `conditional_logic` (System Z) + `defeasible_logic` (DeLP) registres |
| 1.4.4 | Mesures d'incoherence et resolution | À auditer | — | `sat_solving` (PySAT+Z3) registre |
| 1.4.5 | Revision de croyances multi-agents | À auditer | — | `belief_revision` existe, pas multi-agents |
| 1.5.1 | Integration d'un planificateur symbolique | À auditer | — | Aucun |
| 1.5.2 | Verification formelle d'arguments | À auditer | — | Aucun |
| 1.5.3 | Formalisation de contrats argumentatifs | À auditer | — | Aucun |

**Bilan** : 1 traité (🟢), 10 à auditer. L'effort se concentre sur les 10 sujets non traités.

---

## Audit detaille

### 🟢 1.4.1 Systemes de maintenance de la verite (TMS)

**Statut** : Integre (SUIVI 85%, dossier `1.4.1-JTMS/`)
**Epic A** : A-04 #748 — verdict 🟢 INTÉGRÉ
**Pipeline wiring** : `jtms_service` (capabilities: `belief_maintenance`, `truth_maintenance`, `jtms_reasoning`) + `atms_service` (capabilities: `atms_reasoning`, `environment_tracking`)
**Decision** : ✅ Déjà couvert — pas d'audit nécessaire.

---

### 1.3.1 Taxonomie des schemas argumentatifs

**Sujet** : Taxonomie de Walton des schemas argumentatifs (28 schemes), questions critiques, identification automatique.
**Pipeline** : Aucun wiring. Le système actuel utilise `FrenchFallacyPlugin` (8 familles / 28 labels) pour les **sophismes**, pas les **schemas argumentatifs** de Walton. Ce sont deux concepts différents : les sophismes sont des arguments fallacieux, les schemas de Walton sont des patterns d'arguments valides (ou fallacieux si les questions critiques echouent).
**Valeur potentielle** : MEDIUM — les schemas de Walton complementent la detection de sophismes. Un module "schema identifier" pourrait enrichir le pipeline en identifiant le type d'argument (causal, analogique, authority, etc.) en plus de détecter les fallacies.
**Classification** : 🟠 **Angle mort utile** — complement naturel du système de fallacy detection existant.

---

### 1.3.2 Classification des sophismes

**Sujet** : Taxonomies de sophismes, classification ML, detection automatisee.
**Pipeline** : **Partiellement couvert** — le système a déjà une taxonomie 8 familles / 28 labels avec 3-tier hybrid (regex + CamemBERT + LLM). Le projet étudiant 2.3.2 (A-07) a été intégré fidèlement avec cette taxonomie. Cependant, le sujet original demandait aussi du **ML de classification** (apprentissage supervisé) et une **taxonomie évolutive** que le système n'a pas (la taxonomie est statique dans le code).
**Valeur potentielle** : LOW — la classification des sophismes est déjà couverte par le 3-tier hybrid. Le gap est l'apprentissage supervisé et la taxonomie évolutive, qui sont des **enhancements** plutôt que des angles morts critiques.
**Classification** : 🔵 **Doublon partiel** — déjà couvert par A-07 (2.3.2-detection-sophismes). Le delta (ML supervisé, taxonomie évolutive) est un enhancement LOW.

---

### 1.3.3 Ontologie de l'argumentation

**Sujet** : Ontologie OWL de l'argumentation avec Protégé, vocabulaire formel pour décrire les arguments, attaques, soutiens, prémisses, conclusions.
**Pipeline** : Aucun wiring. Le système n'a pas d'ontologie formelle — les arguments sont représentés via `RhetoricalAnalysisState` (dictionnaire Python) et `SharedState` (dataclasses). Pas de OWL, pas de RDF, pas de SPARQL.
**Valeur potentielle** : LOW — une ontologie formelle serait utile pour l'interopérabilité et le raisonnement automatisé, mais le système actuel fonctionne bien avec des structures Python. L'ontologie est un cas d'usage **académique** (publication, comparaison avec d'autres systèmes) plutôt qu'un besoin pipeline.
**Classification** : ⚫ **Abandonné légitimement** — le système utilise des structures Python adaptées à son usage. L'ontologie OWL n'apporterait pas de valeur pipeline immédiate.

---

### 1.4.2 Revision de croyances (AGM)

**Sujet** : Opérateurs AGM (expansion, contraction, révision), postulats, Tweety `beliefdynamics`.
**Pipeline** : **Partiellement couvert** — `belief_revision` est une capability registree dans `registry_setup.py` avec invoke callable `_invoke_belief_revision` et state writer `_write_belief_revision_to_state`. Le handler utilise Tweety `beliefdynamics` pour les opérations AGM. Cependant, le wiring est un **handler passif** (invoqué uniquement si demandé explicitement) — pas de workflow phase automatique et pas de state dimension dédiée.
**Valeur potentielle** : MEDIUM — la révision de croyances AGM est un complément naturel du JTMS (1.4.1 déjà intégré). Un workflow "belief dynamics" pourrait chaîner JTMS → AGM pour gérer les mises à jour de croyances de manière formelle.
**Classification** : 🟡 **Partiellement couvert** — le handler existe mais est dormant (pas de workflow, pas de consumer). Améliorable en l'intégrant dans un workflow phase.

---

### 1.4.3 Raisonnement non-monotone

**Sujet** : Logique par défaut (Reiter), OCF (ordering of conditional), logique non-monotone (System Z, circumscription).
**Pipeline** : **Partiellement couvert** — deux capabilities registrees :
- `conditional_logic` (System Z) via `_invoke_cl` — raisonnement non-monotone avec conditionnels
- `defeasible_logic` (DeLP) via `_invoke_delp` — programmation logique défeasible

Comme pour 1.4.2, ce sont des **handlers passifs** sans workflow phase automatique.
**Valeur potentielle** : LOW — les handlers existent et sont fonctionnels. Le gap est l'intégration dans un workflow (scénario : argumentation non-monotone où les conclusions peuvent être rétractées).
**Classification** : 🟡 **Partiellement couvert** — handlers existants mais dormants. Le scénario d'utilisation dans un workflow reste à définir.

---

### 1.4.4 Mesures d'incoherence et resolution

**Sujet** : Mesures d'incohérence (Tweety `logics.pl.analysis`), MUS (Minimal Unsatisfiable Subsets), MaxSAT, résolution de conflits.
**Pipeline** : **Partiellement couvert** — `sat_solving` est une capability registree avec invoke callable `_invoke_sat` (PySAT + Z3). Le handler résout des problèmes SAT/MaxSAT et peut identifier des sous-ensembles insatisfaisables. Cependant, il n'y a pas de **mesure d'incohérence formelle** ni de **résolution de conflits** automatisée — le handler SAT est utilisé comme outil de vérification, pas comme module de résolution.
**Valeur potentielle** : MEDIUM — la mesure d'incohérence et la résolution de conflits seraient utiles pour le pipeline "full" (identifier les contradictions entre résultats d'analyse et proposer des résolutions). C'est un cas d'usage **avancé** qui pourrait améliorer la qualité du rapport final.
**Classification** : 🟡 **Partiellement couvert** — SAT/MaxSAT existe, mais pas de module de mesure d'incohérence ni de résolution de conflits.

---

### 1.4.5 Revision de croyances multi-agents

**Sujet** : Révision de croyances dans un contexte multi-agents (Tweety `beliefdynamics` multi-agent), opérateurs de fusion, consensus.
**Pipeline** : Le handler `belief_revision` (1.4.2) existe mais est **mono-agent**. Pas de wiring multi-agents pour la révision de croyances. Le système a un `JTMSCommunicationHub` pour la communication inter-agents (Sherlock↔Watson) mais pas de mécanisme de révision/consensus formel.
**Valeur potentielle** : MEDIUM — la révision multi-agents serait pertinente pour les workflows collaboratifs (débat, gouvernance). C'est un **enhancement** du pipeline conversationnel existant.
**Classification** : 🟠 **Angle mort utile** — complément naturel du pipeline collaboratif existant.

---

### 1.5.1 Integration d'un planificateur symbolique

**Sujet** : Planificateur symbolique (Tweety `action`, PDDL), génération de plans d'action argumentatifs, vérification de faisabilité.
**Pipeline** : Aucun wiring. Pas de planificateur, pas de PDDL, pas de module de planification d'actions.
**Valeur potentielle** : LOW — la planification symbolique est hors scope du pipeline d'analyse argumentative actuel. Le système analyse des arguments existants, il n'en **planifie** pas. Ce sujet serait pertinent pour un système de **génération d'arguments** (proactif), pas d'analyse (réactif).
**Classification** : ⚫ **Abandonné légitimement** — hors scope du pipeline actuel (analyse, pas planification).

---

### 1.5.2 Verification formelle d'arguments

**Sujet** : Model checking, prouveurs automatiques, vérification formelle de propriétés d'arguments (cohérence, complétude, validité).
**Pipeline** : Aucun wiring dédié. Le système utilise Tweety pour la **vérification syntaxique** (parsing de formules) et la **satisfiabilité** (SAT), mais pas de **model checking** formel ni de **preuve de propriétés**. Les prouveurs externes (`_invoke_external_fol_solver`, `_invoke_external_modal_solver`) peuvent vérifier des formules mais pas des propriétés argumentatives complexes.
**Valeur potentielle** : LOW — la vérification formelle d'arguments est un sujet académique avancé. Le pipeline actuel vérifie la **cohérence logique** via Tweety et SAT, ce qui couvre le cas d'usage principal. Le model checking serait un **plus académique** plutôt qu'un besoin pipeline.
**Classification** : ⚫ **Abandonné légitimement** — le pipeline couvre déjà la vérification de base via Tweety/SAT.

---

### 1.5.3 Formalisation de contrats argumentatifs

**Sujet** : Smart contracts pour l'argumentation, blockchain, enforcement de règles de débat.
**Pipeline** : Aucun wiring. Pas de blockchain, pas de smart contracts.
**Valeur potentielle** : NONE — ce sujet est totalement hors scope du pipeline d'analyse argumentative. C'est un cas d'usage de **gouvernance décentralisée** qui n'a pas de rapport avec l'analyse de texte argumentatif.
**Classification** : ⚫ **Abandonné légitimement** — hors scope.

---

## Recapitulatif

| Code | Sujet | Classification | Pipeline wiring | Valeur potentielle |
|------|-------|----------------|-----------------|-------------------|
| 1.4.1 | TMS (JTMS/ATMS) | 🟢 Traité (A-04) | Complet | — |
| 1.3.1 | Taxonomie schemas argumentatifs | 🟠 Angle mort utile | Aucun | MEDIUM |
| 1.3.2 | Classification sophismes | 🔵 Doublon partiel | 3-tier hybrid (A-07) | LOW |
| 1.3.3 | Ontologie argumentation | ⚫ Abandonné | Aucun | LOW |
| 1.4.2 | Revision croyances (AGM) | 🟡 Partiel | `belief_revision` registre | MEDIUM |
| 1.4.3 | Raisonnement non-monotone | 🟡 Partiel | `conditional_logic` + `defeasible_logic` | LOW |
| 1.4.4 | Mesures incoherence | 🟡 Partiel | `sat_solving` (PySAT+Z3) | MEDIUM |
| 1.4.5 | Revision croyances multi-agents | 🟠 Angle mort utile | Mono-agent seulement | MEDIUM |
| 1.5.1 | Planificateur symbolique | ⚫ Abandonné | Aucun | LOW |
| 1.5.2 | Verification formelle | ⚫ Abandonné | Tweety/SAT basique | LOW |
| 1.5.3 | Contrats argumentatifs | ⚫ Abandonné | Aucun | NONE |

### Decompte

| Classification | Count | Sujets |
|----------------|-------|--------|
| 🟢 Traité | 1 | 1.4.1 TMS |
| 🟠 Angle mort utile | 2 | 1.3.1, 1.4.5 |
| 🟡 Partiel | 3 | 1.4.2, 1.4.3, 1.4.4 |
| 🔵 Doublon partiel | 1 | 1.3.2 |
| ⚫ Abandonné | 4 | 1.3.3, 1.5.1, 1.5.2, 1.5.3 |

**Angles morts utiles** : 2 sujets (1.3.1 Walton argument schemes, 1.4.5 multi-agent belief revision)
**Partiellement couverts** : 3 sujets avec handlers existants mais dormants
**Abandonnés légitimement** : 4 sujets hors scope ou valeur LOW

---

## Issues enhancement proposees

| # | Issue proposee | Priorite | Action |
|---|----------------|----------|--------|
| E1 | `enhancement(c-03): add Walton argument scheme identifier capability` | **MEDIUM** | Nouveau module identifiant les schemas argumentatifs de Walton (causal, analogique, authority, etc.) complementaire au systeme de fallacy. Capability proposee : `argument_scheme_identification`. |
| E2 | `enhancement(c-03): extend belief revision for multi-agent scenarios` | **MEDIUM** | Etendre le handler `belief_revision` pour supporter la revision multi-agents (fusion de croyances, consensus). Utile pour les workflows collaboratifs (debat, gouvernance). |
| E3 | `enhancement(c-03): activate dormant belief/conditional/defeasible handlers in workflow` | **LOW** | Integrer les handlers existants (`belief_revision`, `conditional_logic`, `defeasible_logic`) dans des workflow phases optionnels du pipeline "full". |

### A valider par l'utilisateur

- RAS — audit read-only. Les 3 enhancement proposals sont des suggestions d'enrichissement du consolide.
