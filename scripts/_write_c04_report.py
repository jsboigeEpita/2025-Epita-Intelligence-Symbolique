#!/usr/bin/env python3
"""Helper script to write the C-04 audit report."""
import os

content = """# C-04: Audit Sujets — Sections II-A/B Architecture + Sources/Données

**Track**: C-04 #782 (Epic C #744)
**Date**: 2026-06-01
**Author**: Claude Code @ myia-po-2023:2025-Epita-Intelligence-Symbolique
**Scope**: 8 sujets (4 architecture + 4 sources/données)

---

## Table préalable — Status des sujets

| Code | Sujet | Statut | Lien Epic A | Pipeline wiring |
|------|-------|--------|-------------|-----------------|
| 2.1.1 | Architecture multi-agents | À auditer | — | COMPLETE (GroupChat, Sherlock/Watson, JTMS hub) |
| 2.1.2 | Orchestration des agents | À auditer | — | COMPLETE (WorkflowDSL, UnifiedPipeline, 30+ invoke) |
| 2.1.3 | Monitoring et évaluation | À auditer | — | PARTIAL (10+ modules eval, pas de capability register) |
| 2.1.6 | Gouvernance multi-agents | 🟢 Traité | A-06 #751 | COMPLETE (governance_agent + 7 methods + plugin) |
| 2.2.1 | Amélioration moteur extraction | À auditer | — | COMPLETE (ExtractAgent + fact_extraction_service) |
| 2.2.2 | Support formats étendus | À auditer | — | NONE (plain text seulement) |
| 2.2.3 | Sécurisation des données | À auditer | — | PARTIAL (CryptoService existe, pas register) |
| 2.2.4 | Gestion de corpus | À auditer | — | PARTIAL (semantic_index_service register) |

**Bilan** : 1 traité (🟢), 7 à auditer.

---

## Audit détaillé

### 🟢 2.1.6 Gouvernance multi-agents

**Statut** : Intégré (SUIVI 85%, projet `2.1.6_multiagent_governance_prototype/`)
**Epic A** : A-06 #751 — verdict 🟢 INTÉGRÉ (CLOSED)
**Pipeline wiring** : `governance_agent` (capabilities: `governance_simulation`, `multi_method_voting`, `preference_aggregation`) + `_invoke_governance` + `GovernancePlugin` (4 fonctions SK) + 7 méthodes de vote (`social_choice.py`) + conflict resolution + consensus metrics + web dashboard (VotingPanel, ConsensusGauge, ProposalList)
**Décision** : ✅ Déjà couvert — pas d'audit nécessaire.

---

### 2.1.1 Architecture multi-agents

**Sujet** : Frameworks multi-agents, protocoles de communication, coordination (FIPA, ACL, AOP).
**Pipeline** : **Complètement couvert** — le système est un système multi-agents natif. Infrastructure :
- **Communication hub** : `jtms_communication_hub.py` (Sherlock↔Watson, Moriarty)
- **Group chat** : `group_chat.py` (`GroupChatOrchestration`), `cluedo_orchestrator.py`, `sherlock_modern_orchestrator.py`
- **Collaborative debate** : `collaborative_debate.py` (4 roles : critic, validator, devil's advocate, synthesizer)
- **Agent base** : `BaseAgent(ChatCompletionAgent, ABC)` — SK-native pour `AgentGroupChat`
- **Factory** : `AgentFactory` (agents/b_factory.py)
- **Strategies** : `SelectionStrategy`, `TerminationStrategy` (orchestration/base.py)
- **Turn protocol** : `turn_protocol.py`
- **Hierarchical** : `hierarchical/hierarchy_bridge.py` (strategic→tactical→operational)

Capabilities enregistrées : `collaborative_analysis`, `governance_simulation`, `adversarial_debate`, `belief_maintenance`, `atms_reasoning`, etc.
**Valeur potentielle** : NONE — l'architecture multi-agents est le cœur du système, ce sujet est un doublon total avec l'existant.
**Classification** : 🔵 **Doublon cross-section** — l'architecture MA est le pivot du système, pas un angle mort. Ce sujet est probablement un "traité implicite" jamais formalisé car l'infrastructure a précédé la formalisation des sujets étudiants.

---

### 2.1.2 Orchestration des agents

**Sujet** : Saga/Choreography patterns, workflows déclaratifs, orchestration robuste.
**Pipeline** : **Complètement couvert** — infrastructure d'orchestration massive :
- **WorkflowDSL déclaratif** : `orchestration/workflow_dsl.py` (`WorkflowBuilder`, `add_phase(capability=...)`, `depends_on()`)
- **UnifiedPipeline** : `orchestration/unified_pipeline.py` (`setup_registry()`, 3 workflows pré-construits : light/standard/full, `run_unified_analysis()`)
- **WorkflowExecutor** : phase-by-phase DAG execution
- **Hierarchical orchestration** : `hierarchical/` (strategic allocator + tactical monitor)
- **Checkpointing** : `checkpoint.py`
- **Itératif** : `iterative_deepening.py`
- **10+ workflows spécifiques** : `formal_verification`, `debate_tournament`, `democratech`, `fact_check_pipeline`, `comprehensive_analysis`, `formal_debate`, `argument_strength`, `belief_dynamics`
- **State writers** : 42 `_write_*_to_state` functions
- **Service manager** : `service_manager.py`

Capabilities : pas de capability "workflow" explicite (les workflows enchaînent des invoke callables).
**Valeur potentielle** : NONE — l'orchestration est complète, déclarative (WorkflowDSL), avec checkpoint, hierarchical, et 10+ workflows concrets. Saga/Choreography sont des patterns d'orchestration distribuée (microservices) qui ne s'appliquent pas à un pipeline monolithique Python.
**Classification** : 🔵 **Doublon cross-section** — orchestration entièrement couverte par l'existant.

---

### 2.1.3 Monitoring et évaluation

**Sujet** : Métriques, logging, visualisation, dashboards, observabilité.
**Pipeline** : **Partiellement couvert** :
- **Évaluation** : 10+ modules dans `argumentation_analysis/evaluation/` (benchmark_runner, multi_model_benchmark, fallacy_benchmark, conversational_benchmark, plugin_benchmark, capability_eval, synergy_analyzer, llm_judge, baseline_benchmark, pattern_mining, judge.py, result_collector)
- **Visualisation** : 5 modules dans `visualization/` (html_report, dung_viz, pipeline_viz, quality_viz)
- **Reporting** : 4 modules dans `reporting/` (cross_reference_graph, conversation_balance, multi_format_exporter, reprompt_trace)
- **Structured logging** : `orchestration/structured_logging.py`
- **Trace analyzer** : `orchestration/trace_analyzer.py`
- **Trace entries** : toutes les invoke callables écrivent `state.add_trace_entry()`

Cependant :
- **Aucune capability** "monitoring" / "benchmark" / "evaluation" enregistrée dans `registry_setup.py`
- **Aucun invoke callable** `_invoke_benchmark` ou `_invoke_monitoring`
- Le monitoring se fait via trace entries + scripts ad-hoc (pas intégré au pipeline runtime)

**Valeur potentielle** : LOW — les modules existent et sont fonctionnels (benchmarks, viz, reports). Le gap est l'absence de wiring pipeline runtime (une phase "monitoring" automatique dans le workflow full). C'est un **enhancement** intégrationnel plutôt qu'un angle mort fonctionnel.
**Classification** : 🟡 **Partiellement couvert** — modules complets mais dormant dans le pipeline runtime.

---

### 2.2.1 Amélioration du moteur d'extraction

**Sujet** : Robustesse d'extraction, validation, métadonnées, passages de contexte.
**Pipeline** : **Complètement couvert** :
- **ExtractAgent** : `agents/core/extract/extract_agent.py` (SK-based, LLM + native plugin hybrid)
- **ExtractAgentPlugin** : `agents/core/extract/extract_definitions.py` (`ExtractResult`, `ExtractDefinition`)
- **ExtractService** : `services/extract_service.py` (marker-based text extraction)
- **I/O Manager** : `core/io_manager.py` (`load_extract_definitions()` avec encrypted config loading)
- **Capability** : `fact_extraction_service` enregistrée avec `_invoke_fact_extraction` (LLM-based avec language-aware prompt + heuristic fallback)
- **Hierarchical adapter** : `operational/adapters/extract_agent_adapter.py`
- **Privacy HARD** : dataset chiffré + I/O manager in-memory (RL3 R288)

**Valeur potentielle** : NONE — moteur complet, register, invoke, fallback heuristique, multilingue.
**Classification** : 🔵 **Doublon cross-section** — extraction entièrement couverte.

---

### 2.2.2 Support de formats étendus

**Sujet** : PDF, DOCX, HTML, OCR, parsers multi-formats.
**Pipeline** : **AUCUN WIRING** :
- Aucun `document_loader` ou `format_parser` module
- Aucun capability enregistrée
- Aucun invoke callable
- Références minimales : `pypdf` dans 1 fichier de test, `pdfplumber` dans 1 composant UI (pas wiring pipeline)
- Tous les invoke callables prennent `input_text: str` (plain text uniquement)

**Valeur potentielle** : **HIGH** — c'est le plus grand angle mort du pipeline actuel. Le système ne peut analyser que du texte plain fourni directement. Pour traiter des corpus réels (articles, rapports PDF, transcriptions OCR), un module de parsing multi-format est critique. Cas d'usage concrets :
- Analyser un PDF de discours politique (source politique historique)
- Analyser un DOCX d'argumentaire académique
- Analyser une page HTML (article de presse en ligne)
- Analyser une image de texte (scan, photo de tract)

**Classification** : 🟠 **Angle mort utile — HIGH PRIORITY** — seul sujet du packet avec une valeur ajoutée pipeline immédiate. Un module `document_loader` capable de PDF/DOCX/HTML/OCR débloquerait l'analyse de sources primaires non-texte.

---

### 2.2.3 Sécurisation des données

**Sujet** : Chiffrement, contrôle d'accès, audit, gestion de clés.
**Pipeline** : **Partiellement couvert** — infrastructure crypto forte, mais wiring pipeline minimal :
- **CryptoService** : `services/crypto_service.py` (Fernet, PBKDF2, gzip, encrypt/decrypt/compress)
- **crypto_utils** : `core/utils/crypto_utils.py`
- **io_manager** : utilise `encrypt_data_with_fernet` pour config chiffrée + dataset chiffré (`extract_sources.json.gz.enc`)
- **Oracle permissions** : `agents/core/oracle/permissions.py` (système de permissions agents)
- **Opaque IDs** : `evaluation/opaque_id.py` (privacy-preserving IDs)
- **State sanitization** : `evaluation/sanitize_state.py`
- **Privacy discipline** : CLAUDE.md "Dataset Privacy Discipline" (RL3, R288,RL6)

Cependant :
- **CryptoService NON enregistré** dans `registry_setup.py` (utilisé en interne par io_manager, pas exposé comme capability)
- **Pas d'access control pipeline-level** (l'API ne restreint pas l'accès aux analyses)
- **Pas d'audit logging** (pas de trace qui a analysé quoi)
- **Pas de gestion de clés rotate** (clés statiques dans .env)

**Valeur potentielle** : LOW — la crypto fonctionne pour le dataset chiffré. Le gap est l'absence de contrôle d'accès API (authentification utilisateurs) et d'audit logging. Ces cas d'usage sont pour un déploiement multi-utilisateurs, pas pour un pipeline de recherche mono-utilisateur.
**Classification** : 🟡 **Partiellement couvert** — crypto forte mais non exposée comme capability. L'audit/access control est un cas d'usage déploiement, pas pipeline.

---

### 2.2.4 Gestion de corpus

**Sujet** : Indexation, versionnement, recherche, knowledge base.
**Pipeline** : **Partiellement couvert** :
- **SemanticIndexService** : `services/semantic_index_service.py` (Kernel Memory, RAG QA, semantic search)
- **Capability** : `semantic_index_service` enregistrée avec `_invoke_semantic_index`
- **Pattern mining** : `evaluation/pattern_mining.py`
- **Knowledge base** : `agents/core/debate/knowledge_base.py` (pour débat)
- **Cross-reference graph** : `reporting/cross_reference_graph.py`
- **Scripts corpus** : `scripts/dataset/` (add_extract, run_corpus_batch, clean_analysis_kb, build_pattern_report)
- **Corpus batch runner** : `scripts/dataset/run_corpus_batch.py`
- **Cross-corpus analysis** : `scripts/analysis/cross_corpus_parallels.py`

Cependant :
- **Pas de versionnement** de corpus (pas de git-like ou hash de contenu)
- **Pas de full-text search** (semantic index uniquement, pas d'inverted index BM25/TF-IDF)
- **Pas de capability** `corpus_management` ou `knowledge_base` (uniquement `semantic_index`)

**Valeur potentielle** : LOW — semantic index Kernel Memory couvre le use case principal (recherche sémantique + RAG). Le versionnement et le full-text search sont des **enhancements** non critiques.
**Classification** : 🟡 **Partiellement couvert** — semantic index complet, gaps sur versioning et full-text sont LOW.

---

## Récapitulatif

| Code | Sujet | Classification | Pipeline wiring | Valeur potentielle |
|------|-------|----------------|-----------------|-------------------|
| 2.1.6 | Gouvernance multi-agents | 🟢 Traité (A-06) | Complete | — |
| 2.1.1 | Architecture multi-agents | 🔵 Doublon | 25+ fichiers, 6 capabilities | NONE |
| 2.1.2 | Orchestration agents | 🔵 Doublon | WorkflowDSL + 10 workflows | NONE |
| 2.1.3 | Monitoring/évaluation | 🟡 Partiel | 10+ modules, pas register | LOW |
| 2.2.1 | Moteur extraction | 🔵 Doublon | ExtractAgent + capability | NONE |
| 2.2.2 | Formats étendus | 🟠 Angle mort HIGH | NONE | **HIGH** |
| 2.2.3 | Sécurisation données | 🟡 Partiel | CryptoService fort, pas register | LOW |
| 2.2.4 | Gestion corpus | 🟡 Partiel | semantic_index_service register | LOW |

### Décompte

| Classification | Count | Sujets |
|----------------|-------|--------|
| 🟢 Traité | 1 | 2.1.6 Gouvernance |
| 🟠 Angle mort utile | 1 | 2.2.2 Formats étendus (HIGH) |
| 🟡 Partiel | 3 | 2.1.3, 2.2.3, 2.2.4 |
| 🔵 Doublon | 3 | 2.1.1, 2.1.2, 2.2.1 |

**Angle mort critique** : 2.2.2 Support formats étendus (PDF/DOCX/HTML/OCR) — seul sujet du packet avec une valeur pipeline HIGH. Débloquerait l'analyse de corpus réels non-texte.

**Doublons** : 3 sujets (2.1.1 architecture MA, 2.1.2 orchestration, 2.2.1 extraction) sont entièrement couverts par l'existant — ce sont probablement des "traités implicites" jamais formalisés car l'infrastructure a précédé la formalisation des sujets étudiants.

---

## Issues enhancement proposées

| # | Issue proposée | Priorité | Action |
|---|----------------|----------|--------|
| E1 | `enhancement(c-04): add multi-format document loader capability (PDF/DOCX/HTML/OCR)` | **HIGH** | Nouveau module `document_loader_service` avec capability `document_parsing`. Wrappers : PyPDF2/pdfplumber (PDF), python-docx (DOCX), BeautifulSoup (HTML), pytesseract (OCR). À exposer avant `_invoke_fact_extraction` dans le workflow full. |
| E2 | `enhancement(c-04): register CryptoService as pipeline capability` | **LOW** | Enregistrer `CryptoService` dans `registry_setup.py` avec capability `data_encryption`. Permet l'utilisation comme phase optionnelle dans workflow full (chiffrement outputs). |
| E3 | `enhancement(c-04): add monitoring phase to full workflow` | **LOW** | Integrer un phase "monitoring" optional dans `WorkflowDSL` qui appelle les modules d'evaluation (benchmark_runner, pattern_mining) en post-analysis. |
| E4 | `enhancement(c-04): add corpus versioning and full-text search` | **LOW** | Étendre `semantic_index_service` avec : (a) hash SHA256 du contenu pour versioning, (b) inverted index BM25 pour full-text search. |

### À valider par l'utilisateur

- RAS — audit read-only. E1 (document loader HIGH) est la seule proposition à fort impact pipeline. E2-E4 sont des enhancements LOW.
"""

path = os.path.join('docs', 'reports', 'subjects_audit', 'C-04_architecture_sources.md')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f'Written {len(content)} chars to {path}')
