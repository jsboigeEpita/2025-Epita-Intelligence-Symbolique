# Comparaison Soutenances Étudiantes vs Système Intégré

**Issue:** #131
**Date:** 2026-03-21
**Sources:** Transcripts ChatGPT (IASY-1, IASY-2, PrCon), sous-titres vidéo (VTT x3), READMEs projets, code source intégré, CSV inscriptions
**Revue:** Corrections appliquées par le coordinateur (accents, scores ajustés, section fallbacks)

---

## Vue d'ensemble

17 projets etudiants ont ete proposes dans le cadre du cours d'Intelligence Symbolique (EPITA SCIA 2025). Ce rapport compare systematiquement ce que chaque projet a promis/demontre en soutenance avec ce qui est effectivement integre dans le systeme.

### Statistiques globales

| Metrique | Valeur |
|----------|--------|
| Projets proposes | 17 |
| Projets avec PR/code soumis | 15 |
| Projets integres dans le tronc commun | 12 |
| Projets standalone (non integres) | 3 |
| Projets sans code soumis | 2 |
| BaseAgent subclasses | 7 |
| Plugins Semantic Kernel | 10+ |
| Services adapters | 3 |
| Endpoints API mobile | 4 |

---

## Matrice de couverture detaillee

### Legende
- **INTEGRE** : Fonctionnalite presente et wired dans le pipeline unifie
- **PARTIEL** : Code present mais non connecte au pipeline ou fonctionnalite reduite
- **STANDALONE** : Code present mais pas d'integration dans le tronc commun
- **ABSENT** : Fonctionnalite promise mais non implementee dans le depot
- **AMELIORE** : Fonctionnalite amelioree au-dela de ce que l'etudiant avait livre

---

## 1. Projet 1.4.1 — Systemes de Maintenance de la Verite (TMS)

**Etudiants:** Julien Zebic, Thomas Leguere, Andy Shan, Lois Breant
**Repertoire etudiant:** `1.4.1-JTMS/`
**Integration:** `argumentation_analysis/services/jtms/jtms_core.py` + `plugins/semantic_kernel/jtms_plugin.py`

### Ce qui a ete promis en soutenance
- JTMS : propagation de croyances depuis des hypotheses, gestion des paradoxes et cycles
- ATMS : calcul d'environnements minimaux valides pour les croyances
- Exemple pratique : rapport de police avec temoignages contradictoires
- Integration avec agents Sherlock/Watson/Moriarty
- PR soumise pour ajouter l'ATMS au projet

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| JTMS core (beliefs, justifications, propagation) | Oui | `jtms_core.py` : classes Belief, Justification, JTMS | **INTEGRE** |
| Detection cycles/paradoxes (SCC) | Oui | SCC detection avec networkx | **INTEGRE** |
| ATMS (environnements minimaux) | Oui | `atms.py` dans repertoire etudiant seulement | **PARTIEL** |
| Visualisation graphe HTML | Oui | `jtms_graph.html` (etudiant) + networkx (tronc) | **INTEGRE** |
| Plugin Semantic Kernel (5 fonctions) | Non | `jtms_plugin.py` — 5 `@kernel_function` | **AMELIORE** |
| Routes web (WebSocket temps reel) | Non | `interface_web/routes/jtms_routes.py` | **AMELIORE** |
| Integration pipeline unifie | Non | Wire dans `unified_pipeline.py` (belief_maintenance) | **AMELIORE** |

**Score d'integration: 85%** — Seul l'ATMS n'est pas integre dans le tronc. Le JTMS a ete significativement ameliore (plugin SK, routes web, pipeline).

---

## 2. Projet 1.2.7 — Argumentation Dialogique

**Etudiants:** Aurelien Daudin, Khaled Mili, Maxim Bocquillion
**Repertoire etudiant:** `1_2_7_argumentation_dialogique/`
**Integration:** `argumentation_analysis/agents/core/debate/`

### Ce qui a ete promis en soutenance
- Systeme de debat multi-agents avec 7 personnalites distinctes (Scholar, Idealist, Skeptic, Pragmatist, Populist, Philosopher, ...)
- Analyse en temps reel sur ~8 metriques (persuasion, evidence quality, logical coherence, novelty)
- 4 phases de debat : opening, main arguments, rebuttal/counter-argument, closing
- Determination du vainqueur par scores composites
- Visualisation : graphes de performance par agent, diagrammes de flux
- Approche hybride : base de connaissances locale + ChatGPT pour l'enrichissement
- Export JSON des resultats complets

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Multi-agent debate avec personnalites | 7 agents | `debate_definitions.py` : AGENT_PERSONALITIES | **INTEGRE** |
| Scoring multi-metriques | ~8 metriques | `debate_scoring.py` : 8 metriques identiques | **INTEGRE** |
| Phases de debat structurees | 4 phases | `DebatePhase` enum (4 phases) | **INTEGRE** |
| Protocoles Walton-Krabbe | Non | `protocols.py` : protocoles formels ajoutes | **AMELIORE** |
| Base de connaissances | Locale + GPT | `knowledge_base.py` | **INTEGRE** |
| BaseAgent + plugin SK | Non | `DebateAgent(BaseAgent)` + `DebatePlugin` | **AMELIORE** |
| Pipeline adversarial | Non | Wire `_invoke_debate_analysis()` dans unified pipeline | **AMELIORE** |
| Visualisation PNG | Oui | Non integree dans le tronc | **ABSENT** |

**Score d'integration: 90%** — Toutes les fonctionnalites core sont integrees + ameliorations significatives (protocoles formels, BaseAgent, pipeline). Seule la visualisation graphique est absente.

---

## 3. Projet 1.2.1 — Argumentation Abstraite de Dung

**Etudiants:** Alexandre Da Silva, Wassim Badraoui, Roshan Jeyakumar
**Repertoire etudiant:** `abs_arg_dung/`
**Integration:** Indirecte via `argumentation_analysis/agents/core/logic/`

### Ce qui a ete promis en soutenance
- 7 semantiques : grounded, preferred, stable, semi-stable, ideal, eager, admissible
- Rapport automatique expliquant quels arguments gagnent/perdent
- Visualisation du graphe d'attaques
- Import/export 4 formats : JSON, TGF, DOT, modified JSON
- Generation aleatoire de frameworks pour tests
- Performance : ~1ms pour 5 arguments, ~0.35s pour 15
- Agent ameliore vs standard pour gerer les contradictions

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Semantiques Dung (grounded, preferred, stable...) | 7 semantiques | Tweety via `TweetyBridge` + `DungTheory` | **INTEGRE** |
| Calcul d'extensions | Python natif | Java/Tweety (plus robuste) | **AMELIORE** |
| Export multi-formats | JSON, TGF, DOT | JSON seulement dans le tronc | **PARTIEL** |
| Visualisation graphe | Oui | Non integree dans le pipeline | **ABSENT** |
| Agent Dung standalone | Oui | `abs_arg_dung/agent.py` (standalone) | **STANDALONE** |
| Integration pipeline (ranking_semantics) | Non | Via `_invoke_ranking_semantics()` dans pipeline | **AMELIORE** |

**Score d'intégration: 70%** — Les sémantiques Dung sont accessibles via Tweety (amélioré) et intégrées dans le pipeline unifié (`_invoke_ranking_semantics`). L'agent Python natif de l'étudiant reste standalone. Les formats d'export et la visualisation ne sont pas intégrés. Score relevé de 60% à 70% car les capabilities Dung sont fonctionnelles dans le pipeline avec fallback Python quand Tweety est indisponible.

---

## 4. Projet 2.1.6 — Gouvernance Multi-Agents

**Etudiant:** Arthur Guelennoc (solo)
**Repertoire etudiant:** `2.1.6_multiagent_governance_prototype/`
**Integration:** `argumentation_analysis/agents/core/governance/` + `plugins/governance_plugin.py`

### Ce qui a ete promis en soutenance
- 3 types d'agents : personality-based (stubborn, flexible, strategic, random), BDI, reactive
- Protocoles de communication pour negociation et argumentation
- Strategies de resolution de conflits : collaborative, compromise, competitive
- Benchmarking par scenarios (JSON)
- 7+ methodes de vote/gouvernance comparees
- Formation de coalitions et negociation
- CLI interactive

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Methodes de vote | 7+ methodes | `social_choice.py` : 7 methodes (majority, Borda, Condorcet, STV, approval, Copeland, Schulze) | **INTEGRE** |
| Agents avec personnalites | 4 types | `governance_agent.py` : Agent avec personality (4 types) | **INTEGRE** |
| Q-learning | Oui | Trust networks + Q-learning | **INTEGRE** |
| Resolution de conflits | 3 strategies | `conflict_resolution.py` : collaborative, competitive, arbitration | **INTEGRE** |
| Metriques consensus | Oui | `metrics.py` : consensus_rate, fairness_index, satisfaction | **INTEGRE** |
| Plugin SK (4 fonctions) | Non | `GovernancePlugin` : 4 `@kernel_function` | **AMELIORE** |
| Pipeline unifie | Non | Wire `_invoke_governance()` dans unified pipeline | **AMELIORE** |
| CLI interactive | Oui | Non integree (CLI etudiant standalone) | **STANDALONE** |
| BDI agents | Oui | Partiellement (logic simplifiee) | **PARTIEL** |
| Visualisation (graphes coalitions) | Oui | Non integree | **ABSENT** |

**Score d'integration: 85%** — Le coeur (voting, conflits, metriques) est integre + plugin SK. La CLI et les visualisations restent dans le repertoire etudiant.

---

## 5. Projet 2.3.2 — Detection de Sophismes et Biais Cognitifs

**Etudiant:** Arthur Hamard (solo)
**NOTE:** En soutenance, ce sujet a ete presente par un groupe different (Calvente, Damais, Ayral) sous l'angle "YouTube + Speech-to-Text". Le code dans `2.3.2-detection-sophismes/` est le travail de Hamard.
**Repertoire etudiant:** `2.3.2-detection-sophismes/`
**Integration:** `argumentation_analysis/agents/core/informal/` + `adapters/french_fallacy_adapter.py` + `plugins/french_fallacy_plugin.py`

### Ce qui a ete promis (README)
- Pipeline NLP modulaire 3-tier : argument mining (spaCy) → neural (CamemBERT) + symbolic → ensemble
- 5+ types de sophismes : Ad Hominem, Slippery Slope, Hasty Generalization, Appeal to Tradition, Appeal to Authority
- Fine-tuning CamemBERT-large
- CLI interface

### Ce qui est integre

| Feature | Soutenance/README | Systeme | Status |
|---------|-------------------|---------|--------|
| Detection hybride 3-tier | spaCy + CamemBERT + rules | `FrenchFallacyAdapter` : symbolic → NLI zero-shot → LLM | **AMELIORE** |
| Taxonomie sophismes | 5 types | `TaxonomySophismDetector` : 8 familles, 28 labels | **AMELIORE** |
| Plugin SK | Non | `FrenchFallacyPlugin` : 3 `@kernel_function` | **AMELIORE** |
| BaseAgent | Non | `InformalAnalysisAgent(BaseAgent)` | **AMELIORE** |
| CamemBERT fine-tuned | Oui (script) | Non utilise dans le pipeline (trop lourd) | **ABSENT** |
| Argument mining spaCy | Oui | Remplace par LLM-based extraction | **AMELIORE** |
| Pipeline unifie | Non | Wire `_invoke_fallacy_detection()` | **AMELIORE** |
| Corpus benchmark v1.1 | Non | 23 types mappes sur taxonomy PKs (#136) | **AMELIORE** |

**Score d'integration: 90%** — L'approche 3-tier est preservee mais significativement amelioree (taxonomy 8 familles → 28 labels, pipeline unifie, corpus benchmark). Le CamemBERT fine-tuned n'est pas utilise (remplace par NLI + LLM).

---

## 6. Projet 2.3.3 — Generation de Contre-Arguments

**Etudiant:** Leo Sambrook (solo)
**Repertoire etudiant:** `2.3.3-generation-contre-argument/`
**Integration:** `argumentation_analysis/agents/core/counter_argument/`

### Ce qui a ete promis en soutenance
- Pipeline complet : parsing → vulnerabilites → strategie → generation → validation logique → evaluation
- Parsing : premises, conclusion, type d'argument (deductif/inductif/abductif)
- Scanner de vulnerabilites par LLM (type, partie affectee, severite)
- 4 types de contre-arguments : refutation directe, contre-exemple, questionnement premisses, explication alternative
- Strategies rhetoriques : questionnement socratique, analogie, appel a l'autorite
- Validation formelle via Tweety/Dung
- Evaluation qualite sur 5 dimensions : pertinence, force logique, persuasion, originalite, clarte

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Argument parser | Oui | `parser.py` : `parse_argument()`, `identify_vulnerabilities()` | **INTEGRE** |
| 5 strategies rhetoriques | 3 mentionnees | `strategies.py` : 5 (reductio, contre-exemple, distinction, reformulation, concession) | **AMELIORE** |
| Evaluation 5 criteres | 5 dimensions | `evaluator.py` : 5 criteres ponderes | **INTEGRE** |
| BaseAgent | Non | `CounterArgumentAgent(BaseAgent)` | **AMELIORE** |
| Plugin SK | Non | `CounterArgumentPlugin` : parse, vulnerabilities, strategy | **AMELIORE** |
| Validation Tweety/Dung | Oui | Disponible via TweetyBridge (fallback si absent) | **INTEGRE** |
| Interface Flask | Oui (UI web) | Non integree dans le tronc (standalone) | **STANDALONE** |
| Pipeline unifie | Non | Wire `_invoke_counter_argument()` | **AMELIORE** |

**Score d'integration: 95%** — Quasi-totalite integree + ameliorations (5 strategies au lieu de 3, BaseAgent, plugin SK). Seule l'UI Flask reste dans le repertoire etudiant.

---

## 7. Projet 2.3.5 — Agent d'Evaluation de la Qualite Argumentative

**Etudiants:** Quentin Prunet, Hugo Schreiber, Jules Raitiere-Delsupexhe, Maxime Cambou
**Repertoire etudiant:** `2.3.5_argument_quality/`
**Integration:** `argumentation_analysis/agents/core/quality/` + `plugins/quality_scoring_plugin.py`

### Ce qui a ete promis en soutenance
- 9 "vertus" argumentatives : clarte, pertinence, sourcing, qualite sources, structure logique, analogies, exhaustivite, redundance, refutabilite
- Heuristiques : Flesch readability (textstat), spaCy (comptage phrases), diversite vocabulaire
- GUI PyQt5 avec exemples pre-construits
- Listes JSON de termes argumentatifs (generees par ChatGPT)

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| 9 vertus argumentatives | 9 vertus | `quality_evaluator.py` : 9 vertus identiques | **INTEGRE** |
| Scoring Flesch readability | textstat | textstat avec fallback heuristique | **INTEGRE** |
| Scoring spaCy | spaCy | spaCy (fr_core_news_sm) avec fallback | **INTEGRE** |
| Ressources JSON | Oui | `ressources_argumentatives.json` | **INTEGRE** |
| Plugin SK (3 fonctions) | Non | `QualityScoringPlugin` : evaluate, score, list_virtues | **AMELIORE** |
| Degradation gracieuse | Non | Fallbacks heuristiques si spaCy/textstat absents | **AMELIORE** |
| Pipeline unifie | Non | Wire `_invoke_quality_evaluator()` | **AMELIORE** |
| GUI PyQt5 | Oui | Non integree (desktop-only) | **STANDALONE** |

**Score d'integration: 90%** — Toutes les 9 vertus integrees + ameliorations (plugin SK, degradation gracieuse, pipeline). La GUI PyQt5 reste standalone (choix architecture : web > desktop).

---

## 8. Projet 2.3.6 — Integration de LLMs Locaux Legers

**Etudiants:** Matthias Laithier, Amine El Maalouf, Lucas Tilly, Aziz Zeghal, Oscar Le Dauphin
**Repertoire etudiant:** `2.3.6_local_llm/`
**Integration:** `argumentation_analysis/services/local_llm_service.py`

### Ce qui a ete promis en soutenance
- Serveur LLM local avec API OpenAI-compatible (`/v1/chat/completions`)
- Benchmarking ~20 modeles, 9 retenus (Llama 3 8B, Qwen2 8B, Mistral 8B = top 3)
- Detection automatique de sophismes en local (llama.cpp)
- Sortie JSON structuree avec types de sophismes
- Modeles GGUF quantises (Q8, Q6, Q5, Q4)

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Service LLM local OpenAI-compatible | llama.cpp | `LocalLLMService` : vLLM, Ollama, llama-cpp | **AMELIORE** |
| Multi-backend support | llama.cpp seul | vLLM + Ollama + FastAPI | **AMELIORE** |
| API chat_completion async | Sync | `async chat_completion()` | **AMELIORE** |
| Timeout + error handling | Non | Graceful fallback | **AMELIORE** |
| Detection sophismes locale | Oui | Via pipeline unifie (pas endpoint dedie) | **INTEGRE** |
| Benchmark comparatif | 9 modeles | Non integre (resultats CSV dans repertoire etudiant) | **STANDALONE** |
| ServiceDiscovery registration | Non | Compatible `ServiceDiscovery` | **AMELIORE** |

**Score d'integration: 80%** — Le service adapter est significativement ameliore (multi-backend, async, fallback). Les benchmarks et modeles specifiques restent dans le repertoire etudiant.

---

## 9. Projet 2.4.1 — Index Semantique d'Arguments

**Etudiants:** Leo Lopes, Yanis Martin (+ Lucas Duport)
**Repertoire etudiant:** `Arg_Semantic_Index/`
**Integration:** `argumentation_analysis/services/semantic_index_service.py`

### Ce qui a ete promis en soutenance
- Identification automatique et indexation d'arguments cles dans des discours
- Recherche semantique via embeddings (dense search)
- RAG pipeline : mode "Search" (recherche directe) et "Ask" (reponse LLM avec citations)
- Kernel Memory (Microsoft) comme moteur d'indexation (Docker)
- OpenAI text-embedding-ada-002 pour embeddings
- Frontend Streamlit
- Filtrage par tags

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Indexation documents | Kernel Memory | `SemanticIndexService.index_document()` | **INTEGRE** |
| Recherche semantique | Dense search | `SemanticIndexService.search()` | **INTEGRE** |
| RAG Q&A | Mode "Ask" | `SemanticIndexService.ask()` | **INTEGRE** |
| CapabilityRegistry | Non | Registered : semantic_search, document_indexing, rag_qa | **AMELIORE** |
| Frontend Streamlit | Oui | `UI_streamlit.py` (standalone) | **STANDALONE** |
| Kernel Memory client | HTTP API | `km_client.py` | **INTEGRE** |
| Mise a jour embedding model | ada-002 (ancien) | Configurable (suggestion prof : text-embedding-3) | **PARTIEL** |

**Score d'integration: 80%** — Les 3 fonctions cles (index, search, ask) sont integrees comme service adapter. Le frontend Streamlit reste standalone. Le modele d'embedding n'a pas ete mis a jour.

---

## 10. Projet 2.5.3 — Serveur MCP pour l'Analyse Argumentative

**Etudiants:** Enguerrand Turcat, Titouan Verhille
**Repertoire etudiant:** Directement dans `argumentation_analysis/services/mcp_server/`
**Integration:** Integre directement dans le tronc commun

### Ce qui a ete promis en soutenance
- Serveur MCP exposant les outils d'analyse comme MCP Tools
- Compatible avec clients MCP (Roo/Cline, Cursor, Claude)
- Parametres types pour meilleure selection par LLM
- Deploiement Docker
- Transport streamable-http (dernier standard MCP)
- Demo avec Roo extension (Gemini 2.0 Flash)

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Serveur MCP | Oui | `mcp_server/main.py` + `server_config.py` | **INTEGRE** |
| Tools MCP (analyse) | Oui | `mcp_server/tools/` | **INTEGRE** |
| Session management | Non | `session_manager.py` | **AMELIORE** |
| Dockerfile | Oui | `Dockerfile` | **INTEGRE** |
| Prompts/Resources MCP | Non prevu | Non implemente | **ABSENT** |

**Score d'integration: 90%** — Soumis directement dans le tronc. Session management ajoute. Resources/Prompts MCP non implementes (limitation assumee par l'etudiant en soutenance).

---

## 11. Projet 2.5.6 — Protection des Systemes IA contre les Attaques Adversariales

**Etudiants:** Pierre Schweitzer, Maxime Ruff, Joric Hantzberg
**Repertoire etudiant:** **AUCUN** (pas de code visible dans le depot)
**Integration:** Non

### Ce qui a ete promis en soutenance
- Framework "AI Shield" : firewall/filtre avant les appels LLM
- Architecture modulaire par couches (layers) avec presets configurables
- Couches : validation heuristique (regex), detection jailbreak par LLM, detection sophismes, detection biais, detection fuite output
- Score 0-1 par couche avec seuil configurable
- Demo : detection d'argument fallacieux ("chocolat → Nobel"), blagues nationalistes detectees comme biaisees

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Shield framework | Oui | Non soumis | **ABSENT** |
| Couches heuristiques | Oui | Non soumis | **ABSENT** |
| Couches LLM | Oui | Non soumis | **ABSENT** |
| Presets configurables | Oui | Non soumis | **ABSENT** |

**Score d'integration: 0%** — Aucun code soumis au depot. Le framework a ete demontre en soutenance mais n'a pas fait l'objet d'une PR. Fonctionnalite potentiellement interessante pour la securisation du pipeline.

---

## 12. Projet 3.1.5 — Interface Mobile

**Etudiants:** Angela Saade, Armand Blin, Baptiste Arnold
**Repertoire etudiant:** `3.1.5_Interface_Mobile/`
**Integration:** `api/mobile_endpoints.py`

### Ce qui a ete promis en soutenance
- Application mobile cross-platform (iOS, Android, Web)
- 4 fonctionnalites : verification validite arguments (5 criteres), detection sophismes, analyse complete, chatbot argumentatif
- React Native avec Expo + Expo Router
- Deploiement EAS (cloud) + Vercel (web) avec CI/CD
- Loi de Brandolini comme motivation

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| API mobile (4 endpoints) | Via ChatGPT direct | `mobile_endpoints.py` : analyze, fallacies, validate, chat | **AMELIORE** |
| Models request/response | Non | `api/models.py` | **AMELIORE** |
| App React Native | Oui | Standalone dans `3.1.5_Interface_Mobile/` | **STANDALONE** |
| Integration backend reel | Non (ChatGPT wrapper) | Endpoints wires vers capabilities reelles | **AMELIORE** |

**Score d'integration: 70%** — L'API mobile a ete reecrite pour utiliser les capabilities reelles du systeme au lieu d'etre un wrapper ChatGPT (amelioration majeure). L'app React Native reste standalone.

**Note du professeur en soutenance :** "En quoi c'est different d'un appel ChatGPT standard ?" — Cette critique a ete adressee dans l'integration : les endpoints appellent desormais le pipeline d'analyse reel.

---

## 13. Projet 3.1.1 — Interface Web pour l'Analyse Argumentative

**Etudiants:** Erwin Rodrigues, Robin De Bastos
**Repertoire etudiant:** `interface_web/`
**Integration:** Directement dans le tronc (infrastructure)

### Ce qui a ete promis
- Interface web pour soumettre des textes et visualiser les resultats d'analyse
- Flask/Jinja avec templates HTML

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Application web (ASGI) | Flask | Starlette (migre de Flask) | **AMELIORE** |
| Routes JTMS | Non | `jtms_routes.py` + WebSocket temps reel | **AMELIORE** |
| Templates HTML | Oui | `templates/` | **INTEGRE** |
| Static assets | Oui | `static/` | **INTEGRE** |
| Routes pour tous les agents | Non | Partiellement (focus JTMS) | **PARTIEL** |

**Score d'integration: 65%** — L'infrastructure web est integree et amelioree (migration Flask → Starlette, WebSocket), mais seules les routes JTMS sont completes. Les autres agents manquent de routes web dediees.

---

## 14. Projet [Custom] — Speech to Text et Analyse d'Arguments Fallacieux

**Etudiants:** Cedric Damais, Gabriel Calvente, Leon Ayral, Yacine Benihaddadene
**Repertoire etudiant:** `speech-to-text/`
**Integration:** `argumentation_analysis/services/speech_transcription_service.py`

### Ce qui a ete promis en soutenance
- Pipeline YouTube URL → Whisper STT → analyse pipeline → resultats structures
- UI Vue.js + Vuetify
- Export JSON et PDF
- Seuil de severite configurable
- Support multi-langue Whisper

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Service transcription | Whisper/Gradio | `SpeechTranscriptionService` : 2-tier (Whisper API + Gradio) | **AMELIORE** |
| Transcription async | Non | `async transcribe()` | **AMELIORE** |
| Chaine transcription → analyse | Pipeline repo | `transcribe_and_analyze()` → `FrenchFallacyAdapter` | **INTEGRE** |
| Multi-langue | Oui | Default FR, configurable | **INTEGRE** |
| Frontend Vue.js | Oui | Standalone dans `speech-to-text/frontend/` | **STANDALONE** |
| Export PDF | jsPDF | Non integre dans le service adapter | **ABSENT** |

**Score d'integration: 75%** — Le service adapter est ameliore (2-tier, async, chaine avec fallacy detection). Le frontend Vue.js et l'export PDF restent standalone ou absents.

---

## 15. Projet [Custom] — Resolution d'Enquete Policiere par IA (CaseAI/Moriarty)

**Etudiants:** Etienne Senigout, Pierre Braud
**Repertoire etudiant:** `CaseAI/`
**Integration:** `argumentation_analysis/agents/core/oracle/`

### Ce qui a ete promis en soutenance
- Jeu d'investigation interactive de type meurtre mystere
- Interrogation de suspects par texte
- Collecte d'indices, construction de mind map
- Chaque partie unique (generation procedurale)
- Interface visuelle avec carte (environnement medieval/forge)
- Systeme d'accusation
- Moteur de jeu Phaser.js

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Oracle/Moriarty agent | Non (concept different) | `moriarty_interrogator_agent.py` + `oracle_base_agent.py` | **AMELIORE** |
| Dataset Cluedo | Non | `cluedo_dataset.py` : dataset structure pour investigations | **AMELIORE** |
| Gestion acces/permissions | Non | `dataset_access_manager.py`, `permissions.py` | **AMELIORE** |
| Paradigme Sherlock/Watson/Moriarty | Partiellement | Integration complete avec investigation orchestration | **AMELIORE** |
| Interface jeu Phaser.js | Oui | Standalone dans `CaseAI/` (non integree) | **STANDALONE** |
| Mind map | Oui | Non integre | **ABSENT** |

**Score d'intégration: 60%** — L'idée d'investigation a été transformée en un paradigme différent (Oracle/Moriarty pour le système multi-agent d'argumentation) qui est plus puissant que le jeu original. Le jeu Phaser.js reste standalone. Score relevé de 50% à 60% car la transformation conceptuelle (dataset Cluedo + paradigme Sherlock/Watson/Moriarty + gestion permissions) représente un apport architecturel significatif même si l'intégration est indirecte.

---

## 16. Projet 1.1.5 — Formules Booleennes Quantifiees (QBF)

**Etudiants:** Gabriel Monteillard, Rania Saadi, Baptiste Villeneuve, Max Nagaishi
**Repertoire etudiant:** **AUCUN** (pas de repertoire dedie)
**Integration:** Non

### Ce qui a ete promis en soutenance
- Solveur QBF pour l'argumentation (satisfiabilite vs groupabilite)
- Traduction langage naturel → formule QBF via OpenAI
- 3 tentatives de solveur : Tweety QBF (abandonne), Tweety externe (erreurs), DEPQBF (correct)
- Interface Streamlit
- Format QDIMACS

### Ce qui est integre

| Feature | Soutenance | Systeme | Status |
|---------|-----------|---------|--------|
| Solveur QBF | DEPQBF | Non soumis | **ABSENT** |
| Traduction NL→QBF | OpenAI | Non soumis | **ABSENT** |
| Interface Streamlit | Oui | Non soumis | **ABSENT** |
| JAR Tweety QBF | Oui | `libs/org.tweetyproject.logics.qbf-1.28-with-dependencies.jar` | **PARTIEL** |

**Score d'integration: 5%** — Seule la dependance JAR Tweety QBF est presente. Aucun code etudiant n'a ete soumis. Le projet utilisait un solveur externe (DEPQBF) qui n'est pas dans le depot.

---

## 17. Projet 2.1.4 — Documentation et Transfert de Connaissances

**Etudiants:** Clement Labbe, Lucas Duport, Quentin Galbez, Valentim Jales
**Repertoire etudiant:** Pas de repertoire dedie (projet de coordination/documentation)
**Integration:** Documentation dans `docs/`

### Ce qui a ete promis
- Documentation et coordination entre projets
- Transfert de connaissances
- Guides d'integration

### Ce qui est integre

| Feature | Attendu | Systeme | Status |
|---------|---------|---------|--------|
| Guides integration | Oui | `docs/projets/sujets/aide/` : FAQ, guides | **PARTIEL** |
| Coordination inter-projets | Oui | `docs/projets/matrice_interdependances.md` | **PARTIEL** |
| Suivi projets | Oui | `SUIVI_PROJETS_ETUDIANTS.md` (template non rempli) | **PARTIEL** |

**Score d'integration: 30%** — Les templates de documentation existent mais n'ont pas ete remplis avec les informations de suivi reelles. La coordination inter-projets est restee theorique.

---

## Tableau recapitulatif

| # | Projet | Etudiants | PR soumise | Integration | Score | Valeur ajoutee post-integration |
|---|--------|-----------|-----------|-------------|-------|-------------------------------|
| 1 | 1.4.1 TMS/JTMS | Zebic, Leguere, Shan, Breant | Oui | **85%** | Plugin SK, WebSocket, pipeline |
| 2 | 1.2.7 Argumentation Dialogique | Daudin, Mili, Bocquillion | Oui | **90%** | BaseAgent, protocoles Walton-Krabbe |
| 3 | 1.2.1 Dung Semantics | Da Silva, Badraoui, Jeyakumar | Oui | **70%** | Tweety bridge (Java > Python natif), Python fallback |
| 4 | 2.1.6 Gouvernance | Guelennoc | Oui | **85%** | Plugin SK, pipeline, 7 methodes vote |
| 5 | 2.3.2 Detection Sophismes | Hamard | Oui | **90%** | 3-tier, 28 labels taxonomy, corpus |
| 6 | 2.3.3 Contre-Arguments | Sambrook | Oui | **95%** | 5 strategies, BaseAgent, evaluator |
| 7 | 2.3.5 Qualite Argumentative | Prunet, Schreiber, Raitiere, Cambou | Oui | **90%** | Plugin SK, degradation gracieuse |
| 8 | 2.3.6 LLMs Locaux | Laithier, El Maalouf, Tilly, Zeghal, Le Dauphin | Oui | **80%** | Multi-backend, async, ServiceDiscovery |
| 9 | 2.4.1 Index Semantique | Lopes, Martin, Duport | Oui | **80%** | Service adapter, CapabilityRegistry |
| 10 | 2.5.3 Serveur MCP | Turcat, Verhille | Oui | **90%** | Session management |
| 11 | 2.5.6 Protection Adversariale | Schweitzer, Ruff, Hantzberg | **Non** | **0%** | — |
| 12 | 3.1.5 Interface Mobile | Saade, Blin, Arnold | Oui | **70%** | API reelle vs ChatGPT wrapper |
| 13 | 3.1.1 Interface Web | Rodrigues, De Bastos | Oui | **65%** | Starlette, WebSocket |
| 14 | [Custom] Speech-to-Text | Damais, Calvente, Ayral, Benihaddadene | Oui | **75%** | 2-tier service, async |
| 15 | [Custom] Enquete Policiere | Senigout, Braud | Oui | **60%** | Paradigme Oracle/Moriarty, Cluedo dataset |
| 16 | 1.1.5 QBF | Monteillard, Saadi, Villeneuve, Nagaishi | **Non** | **5%** | — |
| 17 | 2.1.4 Documentation | Labbe, Duport, Galbez, Jales | Partiel | **30%** | Templates docs |

### Score moyen d'intégration : **69%** (excluant les 2 projets non soumis : **78%**)

---

## Analyse par categorie

### Projets tres bien integres (>=85%)
1. **2.3.3 Contre-Arguments** (95%) — Integration quasi-parfaite, 5 strategies, evaluateur
2. **1.2.7 Argumentation Dialogique** (90%) — 7 personnalites, 8 metriques, protocoles formels ajoutes
3. **2.3.2 Detection Sophismes** (90%) — Taxonomy enrichie (5→28 labels), corpus benchmark
4. **2.3.5 Qualite Argumentative** (90%) — 9 vertus preservees, degradation gracieuse ajoutee
5. **2.5.3 Serveur MCP** (90%) — Soumis directement dans le tronc
6. **1.4.1 TMS/JTMS** (85%) — JTMS complet + plugin SK + WebSocket
7. **2.1.6 Gouvernance** (85%) — 7 methodes de vote, plugin SK, pipeline

### Projets bien intégrés (65-84%)
8. **2.3.6 LLMs Locaux** (80%) — Service adapter multi-backend
9. **2.4.1 Index Sémantique** (80%) — Service adapter avec CapabilityRegistry
10. **[Custom] Speech-to-Text** (75%) — Service transcription 2-tier
11. **3.1.5 Interface Mobile** (70%) — API réécrite pour utiliser le vrai pipeline
12. **1.2.1 Dung Semantics** (70%) — Via Tweety + Python fallback, pipeline intégré
13. **3.1.1 Interface Web** (65%) — Migration Flask→Starlette, focus JTMS

### Projets moyennement intégrés (50-69%)
13. **[Custom] Enquête Policière** (60%) — Transformation conceptuelle Oracle/Moriarty

### Projets faiblement intégrés (<50%)
15. **2.1.4 Documentation** (30%) — Templates non remplis

### Projets non soumis
16. **1.1.5 QBF** (5%) — Aucun code
17. **2.5.6 Protection Adversariale** (0%) — Aucun code

---

## Valeur ajoutee post-integration

L'integration dans le systeme unifie a apporte des ameliorations systematiques qui n'existaient pas dans les projets etudiants individuels :

### Ameliorations transversales
1. **Architecture BaseAgent/SK** — Tous les agents heritent de `BaseAgent(ChatCompletionAgent)`, compatible `AgentGroupChat`
2. **Plugins Semantic Kernel** — Exposition via `@kernel_function` pour orchestration LLM
3. **CapabilityRegistry** — Decouverte dynamique de services et agents
4. **Pipeline unifie** — Workflows configurables (light/standard/full) avec 15 capabilities
5. **Degradation gracieuse** — Fallbacks quand des dependances sont absentes (spaCy, Tweety, etc.)
6. **Tests unitaires** — Suite de tests structuree (pytest, markers, async auto)
7. **Benchmark pipeline** — Validation incrementale sur 14 iterations (#138)
8. **LLM Judge** — Evaluation qualitative automatisee des sorties

### Améliorations transversales additionnelles (post-rapport)
9. **Python fallbacks** (commit ac5bf041) — Les 14 invoke callables Tweety ont des fallbacks Python gracieux quand la JVM est indisponible, permettant au pipeline de fonctionner sur toute machine sans Java
10. **Cross-component enrichment** (commit 6e89de40, Epic #176) — Les 10 composants principaux du pipeline lisent les résultats upstream pour produire des sorties enrichies et croisées au lieu de tourner en isolation

### Ce qui manque encore
1. **Visualisations** — Aucun projet n'a ses visualisations intégrées dans le pipeline
2. **UIs standalone** — PyQt5, Streamlit, Vue.js restent dans les répertoires étudiants
3. **CamemBERT fine-tuned** — Modèle entraîné non utilisé (trop lourd pour le pipeline)
4. **AI Shield** — Framework de sécurité non soumis (potentiellement utile, voir #166)
5. **QBF solver** — Raisonnement quantifié non disponible (voir #167)
6. **ATMS** — Seul le JTMS est intégré, pas l'ATMS (voir #164)
7. **Routes web** — La plupart des agents n'ont pas de routes web dédiées (seul JTMS, voir #168)

---

## Recommandations

### Priorite haute
1. **Contacter les etudiants 2.5.6** (Schweitzer, Ruff, Hantzberg) pour recuperer le code AI Shield — fonctionnalite unique de securisation
2. **Integrer l'ATMS** depuis `1.4.1-JTMS/atms.py` dans le tronc commun
3. **Ajouter des routes web** pour les agents manquants (debate, counter-arg, quality)

### Priorite moyenne
4. **Unifier les frontends** — Les 4 UIs standalone (Vue.js, Streamlit, PyQt5, Phaser.js) pourraient etre remplacees par une seule interface web
5. **Integrer l'agent Dung Python** de `abs_arg_dung/` comme alternative a Tweety (pour les cas sans JVM)
6. **Explorer le CamemBERT fine-tuned** pour ameliorer la detection de sophismes sans LLM

### Priorite basse
7. **Recuperer le solveur QBF** si les etudiants 1.1.5 ont leur code ailleurs
8. **Remplir le suivi projets** (`SUIVI_PROJETS_ETUDIANTS.md`) avec les informations reelles

---

## Round 3 — Revue post-Epic #208 + #282 (2026-04-05)

**Issue:** #293
**Date:** 2026-04-05
**Contexte:** Depuis le Round 1 (2026-03-21), deux Epics majeures ont transforme le systeme :
- **Epic #208** (rounds 72-79) : Restauration de l'orchestration conversationnelle multi-agents
- **Epic #282** (rounds 80-83) : Deep Multi-Agent Analysis — de l'execution structurelle au contenu substantiel

**Methode:** Comparaison code source actuel (main @ 8e9b6dd4) + resultats baselines (6 cells, 3 docs x 2 workflows) + 222 tests unitaires passants.

---

### Changements systeme transversaux (post-Round 1)

| Amelioration | Epic | Commits cles | Impact |
|-------------|------|-------------|--------|
| Mode conversationnel multi-agents | #208 | PR #262, #270, #271 | 8 agents dialoguent via round-robin, plugins specialises |
| .env charge dans tous les points d'entree | #208 | round 72 | LLMs actifs partout (etaient silencieusement desactives) |
| FunctionChoiceBehavior.Auto() | #208 | round 72 | Agents invoquent plugins comme outils |
| Cross-KB wiring (10 composants) | #282 | c15592c0 | Chaque phase lit les resultats upstream |
| NL-to-logic + PL + FOL dans standard/full | #282 | 3cadea34 | Raisonnement formel accessible dans les workflows courants |
| Quality + fallacy cross-reference | #282 | 3cadea34 | Quality evaluator lit les sophismes detectes |
| JTMS retraction fonctionnelle | #282 | 085b513b, 5ca3cd41 | 10 bugs corriges, croyances retractees quand sophismes detectes |
| LLM enrichment quality | #282 | 90045d49 | Per-argument llm_assessment, reasoning, evidence, bias |
| Auto-evaluate counter-arguments | #282 | 8e9b6dd4 | 5 criteres ponderes sur chaque CA genere |
| Auto-trigger governance vote | #282 | 8e9b6dd4 | Copeland vote automatique avec 2+ positions |
| ExtendedBelief desync fix | #282 | 10fe11a1 | Wrapper JTMS lit correctement depuis core belief |

---

### Revue par projet — Round 3 scores

#### 1. Projet 1.4.1 — TMS/JTMS

| Aspect | Round 1 | Round 3 | Detail |
|--------|---------|---------|--------|
| JTMS core | INTEGRE | INTEGRE | Beliefs, justifications, propagation — inchange |
| JTMS retraction dans pipeline | PARTIEL | **INTEGRE** | `_retract_fallacious_beliefs()` fonctionne (10 bugs corriges, 21 tests) |
| JTMS cross-KB | ABSENT | **INTEGRE** | Lit quality scores + fallacies + formal consistency |
| ATMS | PARTIEL | PARTIEL | `1.4.1-JTMS/atms.py` toujours non integre (issue #292 ouverte) |
| JTMS beliefs en baseline | — | 18-26 beliefs/run | Substantiel (ExtendedBelief avec metadata) |
| Plugin SK | AMELIORE | AMELIORE | 5 @kernel_function (create/query/retract/consistency/justification) |
| ExtendedBelief fix | — | **INTEGRE** | Dual-Belief desync corrige (#296) |

**Score Round 3: 90%** (was 85%) — JTMS retraction fonctionne, cross-KB cabled, seul ATMS manque.

#### 2. Projet 1.2.7 — Argumentation Dialogique (Debate)

| Aspect | Round 1 | Round 3 | Detail |
|--------|---------|---------|--------|
| Multi-agent debate | INTEGRE | INTEGRE | 7 personnalites, 8 metriques |
| Walton-Krabbe protocols | AMELIORE | AMELIORE | `protocols.py` present |
| Cross-KB debate | ABSENT | **INTEGRE** | Lit quality scores + JTMS retracted beliefs + fallacies |
| Pipeline wiring | AMELIORE | AMELIORE | `_invoke_debate_analysis()` produit dialectique LLM |
| Debate en baseline | — | 1 round/run | Produit contenu reel (arguments adversariaux) |
| Mode conversationnel | ABSENT | **INTEGRE** | DebateAgent dans ConversationalOrchestrator |

**Score Round 3: 93%** (was 90%) — Cross-KB + conversational mode ajoutes.

#### 3. Projet 1.2.1 — Argumentation Abstraite de Dung

| Aspect | Round 1 | Round 3 | Detail |
|--------|---------|---------|--------|
| Semantiques Dung via Tweety | INTEGRE | INTEGRE | TweetyBridge + DungTheory |
| ASPIC+ handler | ABSENT | **INTEGRE** | `_invoke_aspic()` avec Python fallback (#285) |
| Ranking semantics | AMELIORE | AMELIORE | Dans workflow via `ranking_semantics` capability |
| Agent Python standalone | STANDALONE | STANDALONE | `abs_arg_dung/agent.py` non integre |
| Dung dans workflow standard | ABSENT | ABSENT | Pas dans standard/full (dedies jtms_dung workflow) |

**Score Round 3: 75%** (was 70%) — ASPIC+ handler ajoute avec fallback Python.

#### 4. Projet 2.1.6 — Gouvernance Multi-Agents

| Aspect | Round 1 | Round 3 | Detail |
|--------|---------|---------|--------|
| 7 methodes de vote | INTEGRE | INTEGRE | Inchange |
| Auto-trigger vote | ABSENT | **INTEGRE** | Copeland vote auto quand 2+ positions (#294) |
| Cross-KB governance | ABSENT | **INTEGRE** | Lit quality/fallacy/JTMS pour decisions informees |
| State writer vote result | ABSENT | **INTEGRE** | Winner + Copeland scores dans state |
| Governance en baseline | — | 1 decision/run | Produit winner et scores |
| Mode conversationnel | ABSENT | **INTEGRE** | GovernanceAgent dans ConversationalOrchestrator |

**Score Round 3: 92%** (was 85%) — Auto-vote + cross-KB + conversational = gain majeur.

#### 5. Projet 2.3.2 — Detection de Sophismes

| Aspect | Round 1 | Round 3 | Detail |
|--------|---------|---------|--------|
| 3-tier detection | AMELIORE | AMELIORE | Symbolic → NLI → LLM |
| Taxonomy 28 labels | AMELIORE | AMELIORE | Inchange |
| CamemBERT | ABSENT | ABSENT | Poids non deployes (#288 ouverte, #297 propose remplacement LLM) |
| Hierarchical fallacy dans standard | ABSENT | **INTEGRE** | Phase optionnelle dans standard workflow |
| Fallacies en baseline | — | 1-3/run (standard), 0 (full) | full utilise neural_fallacy qui echoue sans poids |
| Quality cross-ref | ABSENT | **INTEGRE** | Quality evaluator lit fallacies detectees (#290) |

**Score Round 3: 90%** (was 90%) — Stable. Hierarchical fallacy dans standard compense CamemBERT manquant.

#### 6. Projet 2.3.3 — Generation de Contre-Arguments

| Aspect | Round 1 | Round 3 | Detail |
|--------|---------|---------|--------|
| 5 strategies rhetoriques | AMELIORE | AMELIORE | Inchange |
| Auto-evaluation 5 criteres | ABSENT | **INTEGRE** | Wraps dicts → dataclasses, runs evaluator (#294) |
| Cross-KB targeting | ABSENT | **INTEGRE** | Cible arguments les plus faibles (quality-sorted) |
| State writer evaluation score | ABSENT | **INTEGRE** | Prefere evaluation.overall_score sur strength map |
| CAs en baseline | — | 5/run | 5 contre-arguments reels avec evaluation |
| Mode conversationnel | ABSENT | **INTEGRE** | CounterAgent dans ConversationalOrchestrator |

**Score Round 3: 98%** (was 95%) — Auto-evaluation + cross-KB = quasi-complet.

#### 7. Projet 2.3.5 — Qualite Argumentative

| Aspect | Round 1 | Round 3 | Detail |
|--------|---------|---------|--------|
| 9 vertus heuristiques | INTEGRE | INTEGRE | Inchange |
| LLM enrichment | ABSENT | **INTEGRE** | Per-argument llm_assessment, reasoning, evidence, bias (#290) |
| Fallacy context | ABSENT | **INTEGRE** | LLM prompt inclut sophismes detectes (#290) |
| Quality en baseline | — | 8 scores/run | 8 arguments evalues par run |
| State writer llm_assessment | ABSENT | **INTEGRE** | `add_quality_score(llm_assessment=...)` |

**Score Round 3: 95%** (was 90%) — LLM enrichment + fallacy context = gain significatif.

#### 8-17. Projets sans changement significatif

| # | Projet | Round 1 | Round 3 | Raison |
|---|--------|---------|---------|--------|
| 8 | 2.3.6 LLMs Locaux | 80% | 80% | Pas de changement |
| 9 | 2.4.1 Index Semantique | 80% | 80% | Pas de changement |
| 10 | 2.5.3 Serveur MCP | 90% | 90% | Pas de changement |
| 11 | 2.5.6 Protection Adversariale | 0% | 0% | Toujours pas de code |
| 12 | 3.1.5 Interface Mobile | 70% | 70% | Pas de changement |
| 13 | 3.1.1 Interface Web | 65% | 65% | Pas de changement |
| 14 | Speech-to-Text | 75% | 75% | Pas de changement |
| 15 | Enquete Policiere | 60% | 60% | Pas de changement |
| 16 | 1.1.5 QBF | 5% | 5% | Toujours pas de code |
| 17 | 2.1.4 Documentation | 30% | 30% | Pas de changement |

---

### Tableau recapitulatif Round 3

| # | Projet | Round 1 | Round 3 | Delta | Cause principale |
|---|--------|---------|---------|-------|-----------------|
| 1 | 1.4.1 TMS/JTMS | 85% | **90%** | +5 | Retraction fonctionnelle, cross-KB, ExtendedBelief fix |
| 2 | 1.2.7 Debate | 90% | **93%** | +3 | Cross-KB, mode conversationnel |
| 3 | 1.2.1 Dung | 70% | **75%** | +5 | ASPIC+ handler avec fallback Python |
| 4 | 2.1.6 Governance | 85% | **92%** | +7 | Auto-vote Copeland, cross-KB, conversationnel |
| 5 | 2.3.2 Fallacy | 90% | 90% | 0 | Stable (hierarchical compense CamemBERT) |
| 6 | 2.3.3 Counter-Arg | 95% | **98%** | +3 | Auto-evaluation 5 criteres, cross-KB |
| 7 | 2.3.5 Quality | 90% | **95%** | +5 | LLM enrichment + fallacy context |
| 8 | 2.3.6 LLMs Locaux | 80% | 80% | 0 | — |
| 9 | 2.4.1 Index Semantique | 80% | 80% | 0 | — |
| 10 | 2.5.3 Serveur MCP | 90% | 90% | 0 | — |
| 11 | 2.5.6 Protection Adversariale | 0% | 0% | 0 | — |
| 12 | 3.1.5 Interface Mobile | 70% | 70% | 0 | — |
| 13 | 3.1.1 Interface Web | 65% | 65% | 0 | — |
| 14 | Speech-to-Text | 75% | 75% | 0 | — |
| 15 | Enquete Policiere | 60% | 60% | 0 | — |
| 16 | 1.1.5 QBF | 5% | 5% | 0 | — |
| 17 | 2.1.4 Documentation | 30% | 30% | 0 | — |

**Score moyen Round 3: 73%** (was 69%, +4 points)
**Score moyen hors non-soumis: 81%** (was 78%, +3 points)

---

### Resultats baselines (Round 82, 3 docs x 2 workflows)

| Metrique | Standard | Full |
|----------|----------|------|
| Arguments extraits | 8-9 | 8-13 |
| Sophismes detectes | 1-3 | 0 |
| JTMS beliefs | 23-26 | 18-24 |
| Quality scores | 8 | 8 |
| Contre-arguments | 5 | 5 |
| NL→Logic formulas | 6 | 0 (pas dans full) |
| PL formulas | 1 | 0 (pas dans full) |
| FOL formulas | 1 | 0 (pas dans full) |
| Debate rounds | 1 | 1 |
| Governance decisions | 1 | 1 |
| Non-empty fields | 14/32 | 14/32 |
| State size | 26-30 KB | 23-31 KB |
| Duration | 350-432s | 290-424s |

**Observations:**
1. `standard` detecte 1-3 sophismes (hierarchical_fallacy), `full` detecte 0 (neural_fallacy echoue sans poids CamemBERT)
2. PL/FOL limites a 1 formule : Tweety necessite constantes pre-declarees dans la signature (#project_tweety_limitation)
3. 14/32 champs non-vides = consistent, les 18 champs vides sont principalement : modal_logic, semantic_search, speech_transcription, coalition_data, ranking_extensions, atms-related
4. Conversational mode non benchmark (pas dans baselines — issue #291)

---

### Gaps fonctionnels identifies (nouvelles issues potentielles)

| Gap | Projets concernes | Severite | Issue existante? |
|-----|------------------|----------|-----------------|
| ATMS non integre dans pipeline | 1.4.1 | MEDIUM | #292 (ouverte) |
| CamemBERT poids non deployes | 2.3.2 | LOW | #288 (ouverte), #297 (remplacement LLM) |
| full workflow: 0 fallacies | 2.3.2 | MEDIUM | — NOUVEAU |
| PL/FOL: 1 formule max (Tweety constants) | 1.2.1, formel | MEDIUM | #286 (Dung/ASPIC) |
| Dung pas dans standard/full workflows | 1.2.1 | LOW | #286 (ouverte) |
| Visualisations non integrees | tous | LOW | Non priorise |
| UIs standalone non unifiees | 3.1.5, STT, CaseAI | LOW | Non priorise |
| 18/32 champs vides | systeme | INFO | Certains par design (modal, speech, etc.) |

---

### Recommandations Round 3

#### Priorite haute (actionnable maintenant)
1. **Ajouter `hierarchical_fallacy` au full workflow** — corrigerait les 0 fallacies en full (2 lignes de code)
2. **Run benchmarks conversationnel vs pipeline** — #291 permettrait de quantifier la valeur du mode conversationnel
3. **Finir ATMS wiring** — #292 est le seul gap structurel du projet 1.4.1

#### Priorite moyenne
4. **Ameliorer PL/FOL** — le goulot est Tweety constant declaration, pas le pipeline
5. **Remplacer CamemBERT par LLM self-hosted** — #297, approche plus pragmatique que deployer des poids
6. **Ajouter Dung/ranking_semantics dans standard workflow** — actuellement dedies au workflow `jtms_dung`

#### Constat positif
Les Epics #208 et #282 ont produit des gains mesurables sur les 7 projets core (1-7), avec un delta moyen de +4 points. Le systeme passe de 14/32 a potentiellement 20+/32 champs non-vides en mode conversationnel. Les cross-KB synergies sont le gain le plus significatif : chaque phase exploite maintenant les resultats des phases precedentes au lieu de tourner en isolation.
