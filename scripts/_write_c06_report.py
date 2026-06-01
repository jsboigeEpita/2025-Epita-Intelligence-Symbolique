#!/usr/bin/env python3
"""Helper script to write the C-06 audit report."""
import os

content = """# C-06: Audit Sujets — Sections II-D/E Indexation + Automatisation MCP

**Track**: C-06 #784 (Epic C #744)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
**Scope**: 10 sujets (4 indexation + 6 automatisation MCP)

---

## Table préalable — Status des sujets

| Code | Sujet | Statut | Lien Epic A | Pipeline wiring |
|------|-------|--------|-------------|-----------------|
| 2.4.1 | Index sémantique arguments | 🟢 Traité | A-11 #768 | COMPLETE (Kernel Memory + chunking argument-niveau) |
| 2.4.2 | Vecteurs de types d'arguments | À auditer | — | NONE (pas d'embeddings spécialisés) |
| 2.4.3 | Base de connaissances argumentatives | À auditer | — | NONE (pas de graph DB) |
| 2.4.4 | Fact-checking automatisé | À auditer | — | PARTIAL (pipeline complet, vérification simulée) |
| 2.5.1 | Automatisation de l'analyse | À auditer | — | PARTIAL (batch, pas Papermill) |
| 2.5.2 | Pipeline de traitement | À auditer | — | PARTIAL (cache/metrics, pas Airflow) |
| 2.5.3 | Serveur MCP analyse argumentative | 🟢 Traité | A-12 #773 | COMPLETE (23 tools, FastMCP, 4 categories) |
| 2.5.4 | Outils et ressources MCP | À auditer | — | COMPLETE (doublon avec 2.5.3) |
| 2.5.5 | Serveur MCP Tweety | À auditer | — | COMPLETE (doublon avec 2.5.3, JPype/TweetyBridge) |
| 2.5.6 | Protection IA attaques adversariales | 🟢 Traité | A-13 #774 | PARTIAL (recréé non câblé, 2 fix-intents) |

**Bilan** : 3 traités (🟢), 7 à auditer.

---

## Audit détaillé

### 🟢 2.4.1 Index sémantique d'arguments

**Statut** : Intégré fidèlement et enrichi (SUIVI, `2.4.1_Index_Semantique_Arguments/`)
**Epic A** : A-11 #768 — 🟢 INTÉGRÉ fidèlement (PR #836, 0 fix-intent)
**Pipeline wiring** : `SemanticIndexService` (Kernel Memory), capability `semantic_indexing` + `argument_search`, **enrichissement majeur** : chunking argument-niveau (258 LOC, #174 fermée), chaque argument indexé avec `quality_score`, `fallacy_type`, `quality_level`.

---

### 🟢 2.5.3 Développement d'un serveur MCP pour l'analyse argumentative

**Statut** : Intégré fidèlement et enrichi (SUIVI, soumission directe tronc commun)
**Epic A** : A-12 #773 — 🟢 INTÉGRÉ fidèlement (PR #837, 0 fix-intent)
**Pipeline wiring** : `MCPService` (FastMCP port 8000), V1 (10 outils) préservés + V2 (13 outils) ajoutés. 4 catégories : workflow, conversation, capability, specialized. Session manager TTL (30min, max 100 sessions). 40+ invoke callables câblés.

---

### 🟢 2.5.6 Protection des systèmes d'IA contre les attaques adversariales

**Statut** : Recréé fonctionnellement NON câblé (SUIVI 0%, reconstitué depuis #166)
**Epic A** : A-13 #774 — 🟡 recréé non câblé (PR #838)
**Pipeline wiring** : ~717 LOC (Shield orchestrator + 3 layers + 4 presets + 33 tests), mais **ZÉRO wiring pipeline**. 2 fix-intents (#841 wiring, #842 endpoint).

---

### 2.4.2 Vecteurs de types d'arguments

**Sujet** : Embeddings spécialisés par type d'argument (ex: embedding distinct pour arguments causaux vs analogiques vs d'autorité), clustering d'arguments par similarité sémantique.
**Pipeline** : **AUCUN WIRING** :
- `semantic_index_service.py` fait du document-level indexing via Kernel Memory HTTP
- `index_arguments()` indexe chaque argument comme vecteur uniforme avec metadata tags (quality_score, fallacy_type, quality_level, has_fallacy)
- **Pas d'embeddings spécialisés** par type d'argument
- **Pas de clustering** d'arguments

Les arguments sont stockés comme "blobs de texte uniformes" avec métadonnées attachées.

**Valeur potentielle** : LOW — le clustering d'arguments par similarité serait utile pour l'analyse de corpus (identifier les arguments récurrents across sources). Cependant :
- Kernel Memory fait déjà du semantic search standard qui couvre 80% du use case
- La spécialisation par type nécessiterait un modèle d'embeddings fine-tuné (lourd)
- Le metadata filtering existant (`fallacy_type`, `quality_level`) offre déjà une forme de regroupement

**Classification** : ⚫ **Abandonné légitimement** — la valeur ajoutée (clustering fin) ne justifie pas la complexité (embeddings spécialisés fine-tunés). Le metadata filtering standard suffit pour le use case pipeline.

---

### 2.4.3 Base de connaissances argumentatives

**Sujet** : BDD graphes (Neo4j), KMS, requêtes complexes (SPARQL, Cypher), ontologie argumentative persistante.
**Pipeline** : **AUCUN WIRING** :
- 0 hit pour Neo4j, SPARQL, RDF, triple store
- Les belief sets sont stockés en mémoire (`LogicService.belief_sets: Dict[str, Dict]`)
- Aucune persistence structurée des arguments/attaques/soutiens
- `knowledge_mapper.py` (scripts/documentation_system/) est un mappeur de docs, pas un graph DB

**Valeur potentielle** : LOW — une BDD graphes permettrait des requêtes structurelles complexes (ex: "trouve tous les arguments qui attaquent X indirectement via 3 sauts"). Cependant :
- Le use case pipeline (analyse one-shot d'un texte) ne nécessite pas de persistence inter-sessions
- Les frameworks d'argumentation (Dung, ABA, etc.) sont instanciés in-memory via Tweety
- Ajouter Neo4j = dépendance lourde + coût ops

**Classification** : ⚫ **Abandonné légitimement** — le use case pipeline ne justifie pas la BDD graphes. La formalisation OWL (cf C-03 1.3.3) et la BDD graphes (2.4.3) sont toutes deux hors scope pour les mêmes raisons.

---

### 2.4.4 Fact-checking automatisé et détection de désinformation

**Sujet** : Claim extraction, information retrieval, fake news detection, vérification externe (API fact-checkers).
**Pipeline** : **PARTIELLEMENT COUVERT** :
- **Pipeline complet** : `workflows/fact_check_pipeline.py` (6 phases : transcription → quality_assessment → fallacy_screen → belief_tracking JTMS → counter_check → indexing)
- **Orchestrateur** : `orchestration/fact_checking_orchestrator.py` (`FactCheckingOrchestrator`, `FactClaimExtractor`, `ExternalVerificationPlugin`, `FallacyFamilyAnalyzer`, `quick_fact_check()`, `batch_analyze()` avec asyncio.Semaphore(3))
- **Service de vérification** : `services/fact_verification_service.py` (`VerificationStatus` enum : VERIFIED_TRUE/FALSE/PARTIALLY_TRUE/DISPUTED/UNVERIFIABLE, `SourceReliability` avec 22 domain mappings)
- **Gap critique** : `verify_claim()` retourne toujours `UNVERIFIABLE` avec confidence 0.3 — **mode simulé**, aucune API externe (Tavily/SearXNG/Google Search) configurée

**Valeur potentielle** : **HIGH** — c'est le plus grand angle mort fonctionnel du packet. Le pipeline existe mais la **vérification externe** (call API à un fact-checker ou search engine) est absente. Cas d'usage :
- Vérifier un claim factuel contre Wikipedia/Google
- Détecter désinformation via cross-référencement de sources
- Quantifier la fiabilité (SourceReliability existe mais inutilisée)

**Classification** : 🟠 **Angle mort utile — HIGH PRIORITY** — pipeline prêt, seul le branchement API externe manque. Un `ExternalVerificationPlugin` fonctionnel (via Tavily API ou SearXNG MCP) débloquerait le fact-checking réel.

---

### 2.5.1 Automatisation de l'analyse

**Sujet** : Papermill, batch, parallélisation, orchestration notebooks, scheduled analysis.
**Pipeline** : **PARTIELLEMENT COUVERT** :
- **Batch runner** : `orchestration/pipeline_utils.py` (`run_batch_analysis()` avec asyncio.Semaphore concurrency, TTL cache 3600s LFU eviction 1000 entries, `PipelineMetrics` structured)
- **MCP automation** : `services/mcp_server/main.py` expose `run_workflow` MCP tool
- **Workflow catalog** : 8 workflows pré-construits (light/standard/full/quality_gated/debate_governance/jtms_dung/neural_symbolic/fact_check)
- **Gap** : pas de Papermill, pas de Jupyter notebook automation, pas de scheduler cron built-in

**Valeur potentielle** : LOW — `run_batch_analysis()` couvre le use case principal (analyser N textes en parallèle avec cache). Papermill/cron sont des **enhancements** ops (orchestration de notebooks Jupyter) qui ne s'appliquent pas au pipeline Python production.

**Classification** : 🟡 **Partiellement couvert** — batch runner complet, Papermill/notebook automation hors scope (cas d'usage académique, pas pipeline).

---

### 2.5.2 Pipeline de traitement

**Sujet** : Airflow/Luigi/Prefect/Dagster, ETL, reprise sur erreur, orchestration robuste enterprise-grade.
**Pipeline** : **PARTIELLEMENT COUVERT** :
- **Cache TTL+LFU** : `pipeline_utils.py` (3600s, 1000 entries)
- **Circuit breaker LLM** : `LLMBudgetExceeded` (500 calls/run max), per-call timeout (`LLM_CALL_TIMEOUT_S=300s`)
- **Retry logic** : retry sur thin-draw (GG-bis #709)
- **WorkflowDSL déclaratif** : phase dependencies, conditions, loops
- **State persistence** : `checkpoint.py` (pipeline checkpointing)
- **Gap** : pas d'Airflow/Luigi/Prefect/Dagster (frameworks ETL enterprise)

**Valeur potentielle** : NONE — les frameworks ETL enterprise sont **hors scope** pour un pipeline de recherche Python. Le système a sa propre orchestration (WorkflowDSL + UnifiedPipeline + checkpointing) qui couvre le use case. Airflow/Luigi seraient pour un déploiement multi-pipelines en production avec data lineage.

**Classification** : ⚫ **Abandonné légitimement** — overkill pour le scope. L'orchestration native Python (WorkflowDSL + pipeline_utils) couvre 100% du use case.

---

### 2.5.4 Outils et ressources MCP pour l'argumentation

**Sujet** : Outils et ressources MCP (JSON Schema), boîte à outils réutilisable.
**Pipeline** : **COMPLÈTEMENT COUVERT** — c'est la définition même du serveur MCP livré par A-12 (2.5.3) :
- 23 outils MCP (10 V1 + 13 V2) exposés via FastMCP
- 4 catégories : workflow (3 tools), conversation (3 tools), capability (3 tools), specialized (4 tools: evaluate_quality, generate_counter_argument, run_debate_analysis, run_governance_analysis)
- Session manager TTL (30min, 100 sessions max)
- `MCPServerConfig` dataclass (service_name, host, port, transport, session_ttl, max_sessions)

**Valeur potentielle** : NONE — sujet entièrement couvert par A-12 (2.5.3). La distinction entre "serveur MCP" (2.5.3) et "outils/ressources MCP" (2.5.4) est artificielle — c'est le même livrable.
**Classification** : 🔵 **Doublon cross-section** — 2.5.4 = 2.5.3 traité par A-12.

---

### 2.5.5 Serveur MCP pour les frameworks d'argumentation Tweety

**Sujet** : MCP + Tweety `arg.*` + JPype, exposition des solvers (Dung, ASPIC, ABA, ADF, etc.) via MCP.
**Pipeline** : **COMPLÈTEMENT COUVERT** :
- **TweetyBridge singleton** : `agents/core/logic/tweety_bridge.py` (JPype JVM management, lazy-loaded handlers : PropositionalLogicHandler, FirstOrderLogicHandler, ModalHandler, ArgumentationFrameworkHandler, RankingHandler, BipolarHandler, ABAHandler, ADFHandler, ASPICHandler, BeliefRevisionHandler, ProbabilisticHandler, DialogueHandler, QBFHandler)
- **MCP exposure** : `build_framework` MCP tool → `FrameworkService.build_framework()` → `tweety_bridge.af_handler.analyze_dung_framework()`
- **Capabilities** : tous les frameworks d'argumentation sont câblés via TweetyBridge handlers (Dung grounded/complete/preferred/stable/semi-stable, ASPIC, ABA, ADF, ranking, bipolar, EAF, SETAF, social, weighted, probabilistic, dialogue, DL, CL, SAT, Delp, QBF, belief revision, modal, propositional, FOL)
- **Invoke callables** : `_invoke_kb_to_tweety`, `_invoke_tweety_interpretation`, plus tous les `_invoke_*` handlers spécifiques

**Valeur potentielle** : NONE — sujet entièrement couvert par l'existant. La distinction entre "serveur MCP analyse argumentative" (2.5.3) et "serveur MCP Tweety" (2.5.5) est également artificielle — le serveur MCP unifié (A-12) expose déjà tous les solvers Tweety via FrameworkService.
**Classification** : 🔵 **Doublon cross-section** — 2.5.5 = 2.5.3 traité par A-12. La séparation 2.5.3/2.5.4/2.5.5 reflète 3 facettes du même serveur MCP unifié.

---

## Récapitulatif

| Code | Sujet | Classification | Pipeline wiring | Valeur potentielle |
|------|-------|----------------|-----------------|-------------------|
| 2.4.1 | Index sémantique | 🟢 Traité (A-11) | COMPLETE | — |
| 2.5.3 | Serveur MCP | 🟢 Traité (A-12) | COMPLETE (23 tools) | — |
| 2.5.6 | AI Shield | 🟢 Traité (A-13, partiel) | PARTIAL (non câblé) | — |
| 2.4.2 | Vecteurs types arguments | ⚫ Abandonné | NONE | LOW |
| 2.4.3 | Base connaissances (graph DB) | ⚫ Abandonné | NONE | LOW |
| 2.4.4 | Fact-checking automatisé | 🟠 Angle mort HIGH | PARTIAL (simulé) | **HIGH** |
| 2.5.1 | Automatisation analyse | 🟡 Partiel | Batch + cache, pas Papermill | LOW |
| 2.5.2 | Pipeline traitement | ⚫ Abandonné | WorkflowDSL + circuit breaker | NONE |
| 2.5.4 | Outils MCP | 🔵 Doublon | = 2.5.3 (A-12) | NONE |
| 2.5.5 | Serveur MCP Tweety | 🔵 Doublon | = 2.5.3 (A-12) | NONE |

### Décompte

| Classification | Count | Sujets |
|----------------|-------|--------|
| 🟢 Traité | 3 | 2.4.1, 2.5.3, 2.5.6 |
| 🟠 Angle mort utile | 1 | 2.4.4 Fact-checking (HIGH) |
| 🟡 Partiel | 1 | 2.5.1 Automatisation |
| 🔵 Doublon cross-section | 2 | 2.5.4, 2.5.5 (= 2.5.3) |
| ⚫ Abandonné | 3 | 2.4.2, 2.4.3, 2.5.2 |

**Angle mort critique** : 2.4.4 Fact-checking — pipeline complet en place, seul le branchement API externe manque (Tavily/SearXNG/Google). Débloquerait la vérification réelle des claims.

**Doublons MCP** : 2.5.3, 2.5.4, 2.5.5 sont 3 facettes du même serveur MCP unifié livré par A-12. La séparation thématique côté sujet ne correspond pas à une séparation implémentation.

---

## Issues enhancement proposées

| # | Issue proposée | Priorité | Action |
|---|----------------|----------|--------|
| E1 | `enhancement(c-06): wire external fact-checking API (Tavily/SearXNG)` | **HIGH** | Implémenter un `ExternalVerificationPlugin` fonctionnel dans `fact_verification_service.py`. Options : (a) Tavily API (spécialisé fact-checking, paid), (b) SearXNG MCP local (gratuit,instance self-hosted), (c) Wikipedia API + LLM cross-check. Brancher sur `verify_claim()` qui retourne actuellement UNVERIFIABLE simulé. |
| E2 | `enhancement(c-06): expose SourceReliability via fact-check pipeline` | LOW | Le service a déjà `SourceReliability` enum avec 22 domain mappings mais inutilisé. L'exposer dans le workflow fact-check permettrait de scorer les sources des claims vérifiés. |

### À valider par l'utilisateur

- **2.4.4 Fact-checking — HIGH priorité** : le pipeline est prêt, seul le branchement API externe manque. Valider le choix d'API (Tavily paid vs SearXNG self-hosted vs Wikipedia+LLM) mérite arbitrage utilisateur.
- **Doublons MCP (2.5.3/2.5.4/2.5.5)** : confirmation que la séparation thématique côté sujets est artificielle — implémentation = serveur MCP unifié (A-12).
"""

path = os.path.join('docs', 'reports', 'subjects_audit', 'C-06_indexation_automatisation.md')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Written {len(content)} chars to {path}')
