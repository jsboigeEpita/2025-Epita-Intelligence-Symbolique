#!/usr/bin/env python3
"""Helper script to write the C-08 audit report."""
import os

content = """# C-08: Audit Sujets — Sections III-B/C Applications + Lutte Désinformation + RÉCAP GLOBAL

**Track**: C-08 #786 (Epic C #744)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
**Scope**: 14 sujets (9 applications + 5 lutte désinformation dont 3 doublons explicites)

---

## Table préalable — Status des sujets

| Code | Sujet | Statut | Lien Epic A | Pipeline wiring |
|------|-------|--------|-------------|-----------------|
| 3.2.1 | Système de débat assisté par IA | À auditer | — | COMPLETE (DebateAgent + scoring + WebSocket) |
| 3.2.2 | Plateforme éducation argumentation | À auditer | — | PARTIAL (tutoriels, pas gamification) |
| 3.2.3 | Aide à la décision argumentative | À auditer | — | PARTIAL (gouvernance + vote, pas MCDM) |
| 3.2.4 | Plateforme collaborative analyse | À auditer | — | PARTIAL (WebSocket multi-agent, pas annotation UI) |
| 3.2.5 | Assistant écriture argumentative | À auditer | — | NONE |
| 3.2.6 | Analyse débats politiques | À auditer | — | PARTIAL (stakes + fact-check + fallacy) |
| 3.2.7 | Plateforme délibération citoyenne | À auditer | — | PARTIAL (Democratech + governance dashboard) |
| 3.2.8 | Plateforme éducative avancée | À auditer | — | NONE |
| 3.2.9 | Applications commerciales | À auditer | — | NONE |
| 3.3.1 | Fact-checking automatisé | 🔵 Doublon | — | = 2.4.4 (C-06) |
| 3.3.2 | Détection sophismes | 🔵 Doublon | — | = 2.3.2 (C-05, A-07) |
| 3.3.3 | Protection IA adversariale | 🔵 Doublon | — | = 2.5.6 (C-06, A-13) |
| 3.3.4 | ArgumentuMind (cognitif) | À auditer | — | NONE |
| 3.3.5 | ArgumentuShield (inoculation) | À auditer | — | NONE |

**Bilan** : 3 doublons explicites (🔵), 11 à auditer.

---

## Audit détaillé

### 3.2.1 Système de débat assisté par IA

**Sujet** : LLMs + Tweety, interface interactive de débat, scoring, formalisation.
**Pipeline** : **COMPLÈTEMENT COUVERT** :
- **DebateAgent** (`agents/core/debate/`) : débat multi-personnalité, 8 métriques de scoring, stratégies adaptatives, ASPIC+ formal reasoning
- **Protocols** : Walton-Krabbe (permissive, adversarial, exploration)
- **Workflows** : `formal_debate.py`, `debate_tournament.py`, `democratech.py`
- **Collaborative debate** : `orchestration/collaborative_debate.py` (4 roles)
- **WebSocket** : channels `/ws/debate/` + `/ws/deliberation/`
- **React UI** : `DebateArena.js`, `DebateTimeline.js`
- **Capability** : `adversarial_debate`, `argument_stress_test`, `debate_scoring`

**Classification** : 🔵 **Doublon cross-section** — le système de débat est l'une des couches les plus riches. Probable "traité implicite" (débat existait avant formalisation sujets).

---

### 3.2.2 Plateforme d'éducation à l'argumentation

**Sujet** : Gamification, agents pédagogiques, progressive learning.
**Pipeline** : **PARTIELLEMENT COUVERT** :
- Tutoriels : `docs/guides/tutorials/`, `examples/05_notebooks/logic_agents_tutorial.ipynb`
- Showcase : `project_core/rhetorical_analysis_from_scripts/educational_showcase_system.py`
- Templates JTMS : `interface_web/templates/jtms/tutorial.html`, `playground.html`
- **Gap** : pas de gamification engine, pas de progressive learning path, pas de graded exercises

**Valeur potentielle** : LOW — l'analyse argumentative est réutilisable en contexte éducatif, mais la gamification est un **overlay UI** spécifique à un cas d'usage pédagogique qui ne s'applique pas au pipeline de recherche.
**Classification** : ⚫ **Abandonné légitimement** — gamification hors scope pipeline.

---

### 3.2.3 Système d'aide à la décision argumentative

**Sujet** : Frameworks pondérés, MCDM (PROMETHEE, ELECTRE), scoring multi-critères, recommandation.
**Pipeline** : **PARTIELLEMENT COUVERT** :
- **Gouvernance** : agents BDI avec personnalités, Q-learning, Shapley values, coalitions
- **Vote** : 7 méthodes (Borda, Condorcet, Copeland, Schulze, approval...)
- **Argument strength** : `workflows/argument_strength.py`
- **Scoring** : 8 métriques de débat
- **Gap** : pas de MCDM formel (PROMETHEE/ELECTRE), pas de weighted AF, pas de decision-support UI

**Valeur potentielle** : LOW — la gouvernance (2.1.6, A-06) couvre 80% du besoin. Le gap MCDM est académique.
**Classification** : 🟡 **Partiellement couvert** — gouvernance+vote couvre l'essentiel, MCDM est un enhancement académique.

---

### 3.2.4 Plateforme collaborative d'analyse de textes

**Sujet** : Collaboration temps réel, annotation, canvas partagé, versioning d'annotations.
**Pipeline** : **PARTIELLEMENT COUVERT** :
- **Multi-agent collaborative** : `collaborative_debate.py` (4 roles), `group_chat.py`, `collaboration_channel.py`
- **WebSocket** : manager + routes + React hook
- **Gap** : pas d'annotation UI multi-utilisateurs, pas de shared canvas, pas de version-controlled annotation

**Valeur potentielle** : LOW — la collaboration multi-agent existe (agents collaborent sur l'analyse). La collaboration multi-utilisateurs humains (annotation partagée) est un cas d'usage déploiement, pas pipeline.
**Classification** : 🟡 **Partiellement couvert** — collaboration multi-agent complète, collaboration multi-humains hors scope.

---

### 3.2.5 Assistant d'écriture argumentative

**Sujet** : NLP, analyse rhétorique, génération contrôlée, coaching d'écriture.
**Pipeline** : **AUCUN WIRING** — le système analyse des arguments existants, il n'en **génère** pas (sauf contre-arguments via CounterArgumentAgent). Pas de writing assistant, pas de rhetorical structure coach, pas de controlled generation pour essay building.

**Valeur potentielle** : MEDIUM — un assistant d'écriture argumentative serait un **cas d'usage applicatif** naturel du pipeline (analyser un draft → suggérer améliorations structurelles → vérifier cohérence logique). Cependant, c'est un **nouveau produit** (application) pas un gap pipeline. Les capabilities existent (fallacy detection, quality evaluation, logic verification) mais ne sont pas orchestrées dans un workflow "writing improvement".

**Classification** : 🟠 **Angle mort utile** — potentiel applicatif réel (cas d'usage étudiant/professeur), les briques existent, seul le workflow d'orchestration "amélioration d'argumentaire" manque.

---

### 3.2.6 Système d'analyse de débats politiques

**Sujet** : Fact-checking, propagation de désinformation, analyse de discours politiques.
**Pipeline** : **PARTIELLEMENT COUVERT** — combine plusieurs capabilities existantes :
- **Stakes extraction** : `agents/core/political/stakes_extractor.py` (enjeux, acteurs, registre rhétorique, arène discursive)
- **Fact-checking** : `workflows/fact_check_pipeline.py` (6 phases, cf C-06 2.4.4)
- **Fallacy detection** : 3-tier hybrid + contextual analyzer
- **Argument ranking** : `plugins/ranking_plugin.py`
- **Gap** : pas de propagation analysis (modélisation diffusion réseaux sociaux), pas de media analysis dashboard

**Valeur potentielle** : LOW — les briques existent (stakes + fact-check + fallacy), l'assemblage "political debate analyzer" est un cas d'usage applicatif, pas un gap pipeline. La propagation analysis est un sujet de recherche distinct.
**Classification** : 🟡 **Partiellement couvert** — combine des capabilities existantes, manque la propagation modeling.

---

### 3.2.7 Plateforme de délibération citoyenne

**Sujet** : Modération IA, consensus, délibération démocratique.
**Pipeline** : **PARTIELLEMENT COUVERT** :
- **Democratech workflow** : `workflows/democratech.py` (9 phases de délibération démocratique)
- **Governance** : BDI agents, trust networks, coalitions, consensus tracking
- **Dashboard** : GovernanceDashboard.js, ConsensusGauge.js, DecisionTimeline.js
- **WebSocket** : `/ws/deliberation/`
- **Gap** : pas de citizen onboarding, pas de deliberation history persistence, pas de community proposal submission

**Valeur potentielle** : LOW — Democratech + gouvernance couvrent le cas d'usage principal. Les gaps sont des features UI (onboarding, persistence, submission) pour un déploiement citoyen.
**Classification** : 🟡 **Partiellement couvert** — Democratech workflow complet, gaps UI pour déploiement citoyen.

---

### 3.2.8 Plateforme éducative avancée

**Sujet** : Apprentissage adaptatif, learning paths personnalisés, learner modeling.
**Pipeline** : **AUCUN WIRING** — pas de adaptive learning, pas de learner model, pas de skill assessment engine, pas de personalized learning path. Les seules mentions d'"adaptive" sont dans le contexte orchestration (stratégies adaptatives pour workflows, pas pour apprenants).

**Valeur potentielle** : LOW — l'apprentissage adaptatif est un produit éducatif complet, pas un gap pipeline. Les briques existent (analyse argumentative) mais le learner modeling + adaptive engine serait un système entier à part.
**Classification** : ⚫ **Abandonné légitimement** — produit éducatif complet, hors scope pipeline.

---

### 3.2.9 Applications commerciales

**Sujet** : Réputation, surveillance de marque, market analysis, sentiment tracking.
**Pipeline** : **AUCUN WIRING** — pas de reputation monitoring, pas de brand surveillance, pas de sentiment tracking commercial. Seule référence : `docs/projets/modeles_affaires_ia.md` (document conceptuel, pas implémentation).

**Valeur potentielle** : NONE — les applications commerciales sont un cas d'usage **marché**, pas un gap pipeline. Le système d'analyse argumentative pourrait servir de backend, mais le frontend commercial (dashboard marque, alertes sentiment) est un produit distinct.
**Classification** : ⚫ **Abandonné légitimement** — cas d'usage commercial, hors scope pipeline recherche.

---

### 3.3.4 ArgumentuMind — Système cognitif de compréhension argumentative

**Sujet** : Modèles cognitifs computationnels, représentation des biais, compréhension argumentative.
**Pipeline** : **AUCUN WIRING** — pas de cognitive bias model, pas de mental model representation, pas de computational cognitive architecture.

**Valeur potentielle** : NONE — la modélisation cognitive computationnelle est un domaine de recherche fondamental (IA cognitif), pas un gap pipeline. Le système actuel analyse la structure argumentative, pas les processus cognitifs sous-jacents.
**Classification** : ⚫ **Abandonné légitimement** — recherche fondamentale, hors scope pipeline.

---

### 3.3.5 ArgumentuShield — Système de protection cognitive

**Sujet** : Inoculation cognitive (prebunking), protection contre la désinformation.
**Pipeline** : **AUCUN WIRING** — pas de mécanisme d'inoculation, pas de prebunking content generator, pas de cognitive shield. Le système détecte les sophismes mais ne "vaccine" pas les utilisateurs.

**Valeur potentielle** : NONE — l'inoculation cognitive est un concept de psychologie expérimentale (exposer les utilisateurs à des versions affaiblies d'arguments fallacieux pour les "vacciner"). C'est un cas d'usage applicatif avancé qui nécessiterait un frontend spécifique + user studies.
**Classification** : ⚫ **Abandonné légitimement** — psychologie expérimentale, hors scope pipeline.

---

## Récapitulatif

| Code | Sujet | Classification | Pipeline wiring | Valeur potentielle |
|------|-------|----------------|-----------------|-------------------|
| 3.2.1 | Débat assisté IA | 🔵 Doublon | COMPLETE (DebateAgent + scoring + WS) | NONE |
| 3.2.2 | Éducation argumentation | ⚫ Abandonné | PARTIAL (tutoriels) | LOW |
| 3.2.3 | Aide à la décision | 🟡 Partiel | PARTIAL (gouvernance + vote) | LOW |
| 3.2.4 | Collaborative analyse | 🟡 Partiel | PARTIAL (multi-agent collab) | LOW |
| 3.2.5 | Assistant écriture | 🟠 Angle mort | NONE | MEDIUM |
| 3.2.6 | Analyse débats politiques | 🟡 Partiel | PARTIAL (stakes+factcheck+fallacy) | LOW |
| 3.2.7 | Délibération citoyenne | 🟡 Partiel | PARTIAL (Democratech) | LOW |
| 3.2.8 | Éducative avancée | ⚫ Abandonné | NONE | LOW |
| 3.2.9 | Applications commerciales | ⚫ Abandonné | NONE | NONE |
| 3.3.4 | ArgumentuMind | ⚫ Abandonné | NONE | NONE |
| 3.3.5 | ArgumentuShield | ⚫ Abandonné | NONE | NONE |
| 3.3.1 | Fact-checking | 🔵 Doublon | = 2.4.4 | — |
| 3.3.2 | Sophismes | 🔵 Doublon | = 2.3.2 | — |
| 3.3.3 | IA adversariale | 🔵 Doublon | = 2.5.6 | — |

### Décompte

| Classification | Count | Sujets |
|----------------|-------|--------|
| 🔵 Doublon cross-section | 4 | 3.2.1, 3.3.1, 3.3.2, 3.3.3 |
| 🟡 Partiel | 4 | 3.2.3, 3.2.4, 3.2.6, 3.2.7 |
| 🟠 Angle mort utile | 1 | 3.2.5 (assistant écriture) |
| ⚫ Abandonné | 5 | 3.2.2, 3.2.8, 3.2.9, 3.3.4, 3.3.5 |

**Angle mort utile** : 3.2.5 (assistant d'écriture argumentative) — les briques existent (fallacy detection, quality evaluation, logic verification, counter-argument generation), seul le workflow d'orchestration "writing improvement" manque. Cas d'usage naturel pour étudiants/professeurs EPITA.

---

## Issues enhancement proposées

| # | Issue proposée | Priorité | Action |
|---|----------------|----------|--------|
| E1 | `enhancement(c-08): add argumentative writing improvement workflow` | **MEDIUM** | Nouveau workflow `writing_improvement` : analyse draft → identify weaknesses (fallacies, quality gaps, logic errors) → generate improvement suggestions → verify improved version. Combine capabilities existantes : fallacy_detection + quality_scoring + logic_verification + counter_argument_generation. |

### À valider par l'utilisateur

- RAS — audit read-only. E1 (writing improvement workflow) est un cas d'usage applicatif naturel mais pas pipeline-critical.

---

# RÉCAP GLOBAL — Cross-audit Epic C #744

## Vue d'ensemble des 8 rapports C-01 → C-08

### Périmètre total audité

| Rapport | Section | Sujets audités | Treated | Audités |
|---------|---------|---------------|---------|---------|
| C-01 | I-A Logiques formelles | 6 | 1 (A-01) | 5 |
| C-02 | I-B Frameworks argumentation | 9 | 2 (A-02, A-03) | 7 |
| C-03 | I-C/D/E Taxonomies+Croyances+Planif | 11 | 1 (A-04) | 10 |
| C-04 | II-A/B Architecture+Sources | 8 | 1 (A-06) | 7 |
| C-05 | II-C Moteur agentique | 7 | 5 (A-07→A-10, A-16) | 2 |
| C-06 | II-D/E Indexation+MCP | 10 | 3 (A-11→A-13) | 7 |
| C-07 | III-A Interfaces utilisateurs | 7 | 2 (A-14, A-15) | 5 |
| C-08 | III-B/C Applications+Désinformation | 14 | 0 (+ 4 doublons cross) | 14 |
| **TOTAL** | | **72** | **15** (Epic A) | **57** |

### Classification globale (57 sujets non-traités audités)

| Classification | Count | % | Description |
|----------------|-------|---|-------------|
| 🟠 Angle mort utile | 7 | 12% | Valeur pipeline réelle, mérite intégration |
| 🟡 Partiel | 15 | 26% | Modules existants mais dormants/incomplets |
| 🔵 Doublon cross-section | 11 | 19% | Déjà couvert par l'existant ou autre sujet |
| ⚫ Abandonné | 24 | 42% | Hors scope, valeur pipeline NONE/LOW |
| **TOTAL** | **57** | **100%** | |

### Les 7 angles morts utiles (priorité pipeline)

| # | Sujet | Section | Priorité | Cas d'usage pipeline |
|---|-------|---------|----------|---------------------|
| 1 | **2.2.2** Formats étendus (PDF/DOCX/HTML/OCR) | II-B | **HIGH** | Débloque analyse corpus réels non-texte |
| 2 | **2.4.4** Fact-checking automatisé (API externe) | II-D | **HIGH** | Débloque vérification réelle des claims |
| 3 | **1.3.1** Walton argument schemes | I-C | MEDIUM | Complémente fallacy detection par identification schemas |
| 4 | **1.4.5** Révision croyances multi-agents | I-D | MEDIUM | Complémente JTMS pour workflows collaboratifs |
| 5 | **3.2.5** Assistant écriture argumentative | III-B | MEDIUM | Cas d'usage applicatif naturel (étudiants EPITA) |
| 6 | **3.1.3** Éditeur visuel d'arguments | III-A | MEDIUM | Complémente DungGraph existant |
| 7 | **3.1.6** Accessibilité (ARIA) | III-A | MEDIUM | Dette technique UI, qualité pédagogique |

### Les 2 angles morts HIGH (action prioritaire)

**2.2.2 Formats étendus** : Le pipeline ne gère que du plain text. Un module `document_loader_service` (PyPDF2/pdfplumber pour PDF, python-docx pour DOCX, BeautifulSoup pour HTML, pytesseract pour OCR) débloquerait l'analyse de sources primaires non-texte. À câbler avant `_invoke_fact_extraction` dans le workflow full.

**2.4.4 Fact-checking API externe** : Le pipeline fact-checking existe (6 phases + orchestrateur + VerificationStatus enum), mais `verify_claim()` retourne systématiquement UNVERIFIABLE simulé. Brancher une API externe (Tavili/SearXNG/Wikipedia) débloquerait la vérification réelle.

### Vue d'ensemble : qu'est-ce qui couvre le pipeline ?

**Couverture forte (~80%)** : Logiques formelles (C-01), Frameworks argumentation (C-02), Architecture multi-agents (C-04), Moteur agentique (C-05), MCP/automatisation (C-06). Ces sections constituent le "noyau dur" du système — 4/6 sont des doublons cross-section (l'infrastructure existait avant la formalisation des sujets).

**Couverture partielle (~40%)** : Taxonomies/croyances (C-03), Indexation (C-06 partiel), Interfaces (C-07). Handlers et modules existent mais sont dormants ou incomplets.

**Couverture faible (~10%)** : Sources/Données (C-04 : formats étendus), Applications (C-08). Ces sections identifient les vrais gaps — le document loader et le fact-checking API sont les plus impactants.

### Qu'est-ce qui manque le plus ?

1. **Couche document** (2.2.2) : le pipeline est text-only → ne peut pas traiter les corpus réels
2. **Couche vérification** (2.4.4) : le fact-checking est simulé → ne peut pas vérifier les claims
3. **Couche éducative** (3.2.5) : cas d'usage applicatif naturel non adressé → valeur étudiante immédiate

### Ce qui est abandonné légitimement (42%)

Les 24 sujets ⚫ sont répartis en 3 catégories :
- **Recherche fondamentale** (ontologie OWL, modèles cognitifs, inoculation cognitive) → académiques
- **Overkill technique** (Airflow/Luigi, Neo4j, multi-framework agents) → overkill pour le scope
- **Cas d'usage marché** (applications commerciales, monitoring ops, gamification) → hors scope pipeline recherche
"""

path = os.path.join('docs', 'reports', 'subjects_audit', 'C-08_applications_desinformation.md')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Written {len(content)} chars to {path}')
