# Suivi des Projets Etudiants - Intelligence Symbolique 2025

Ce document centralise l'etat d'integration des 17 projets etudiants.
Derniere mise a jour : 2026-03-22. Voir aussi : `docs/reports/soutenance_comparison.md`.

## Synthese

| Projets proposes | PR soumises | Integres dans le tronc | Score moyen |
|-----------------|-------------|----------------------|-------------|
| 17 | 15 | 12 | 76% |

---

## Fondements Theoriques

### 1.1.5 Formules Booleennes Quantifiees (QBF)
*   **Etudiants :** baptiste.villeneuve, gabriel.monteillard, max.nagaishi, rania.saadi
*   **Sujet :** [`sujets/sujet_1.1.5_formules_booleennes_quantifiees.md`](sujets/sujet_1.1.5_formules_booleennes_quantifiees.md)
*   **Repertoire :** Aucun (code non soumis)
*   **Etat :** Non soumis | Score : 5%
*   **Integration :** JAR Tweety QBF present dans `libs/`, aucun code Python
*   **Issue ouverte :** #167

---

### 1.2.1 Argumentation Abstraite de Dung
*   **Etudiants :** alexandre.da-silva, roshan.jeyakumar, wassim.badraoui
*   **Sujet :** (pas de fichier sujet dedie)
*   **Repertoire :** `abs_arg_dung/`
*   **Etat :** Integre partiellement | Score : 60%
*   **Integration :** Semantiques Dung via Tweety (`TweetyBridge`), agent Python standalone. Moteur natif Python cree (`dung_native.py`, #165).
*   **Issue ouverte :** #165

---

### 1.2.7 Argumentation Dialogique
*   **Etudiants :** aurelien.daudin, khaled.mili, maxim.bocquillion
*   **Sujet :** [`sujets/1.2.7_Argumentation_Dialogique.md`](sujets/1.2.7_Argumentation_Dialogique.md)
*   **Repertoire :** `1_2_7_argumentation_dialogique/`
*   **Etat :** Integre | Score : 90%
*   **Integration :** `DebateAgent(BaseAgent)` avec 7 personnalites, 8 metriques, protocoles Walton-Krabbe. Plugin SK.

---

### 1.4.1 Systemes de Maintenance de la Verite (TMS)
*   **Etudiants :** julien.zebic, thomas.leguere, andy.shan, lois.breant
*   **Sujet :** [`sujets/1.4.1_Systemes_Maintenance_Verite_TMS.md`](sujets/1.4.1_Systemes_Maintenance_Verite_TMS.md)
*   **Repertoire :** `1.4.1-JTMS/`
*   **Etat :** Integre | Score : 85%
*   **Integration :** JTMS dans `services/jtms/jtms_core.py`, ATMS dans `services/jtms/atms_core.py` (#164). Plugin SK (5 fonctions). Routes web + WebSocket.

---

## Developpement Multi-Agents

### 2.1.4 Documentation et Transfert de Connaissances
*   **Etudiants :** clement.labbe, lucas.duport, quentin.galbez, valentim.jales
*   **Sujet :** [`sujets/sujet_2.1.4_documentation_coordination.md`](sujets/sujet_2.1.4_documentation_coordination.md)
*   **Repertoire :** Pas de repertoire dedie (projet de coordination)
*   **Etat :** Partiellement integre | Score : 30%
*   **Integration :** Templates dans `docs/projets/sujets/aide/`, matrice interdependances. Templates non remplis.

---

### 2.1.6 Gouvernance Multi-Agents
*   **Etudiant :** arthur.guelennoc (solo)
*   **Sujet :** [`sujets/2.1.6_Gouvernance_Multi_Agents.md`](sujets/2.1.6_Gouvernance_Multi_Agents.md)
*   **Repertoire :** `2.1.6_multiagent_governance_prototype/`
*   **Etat :** Integre | Score : 85%
*   **Integration :** 7 methodes de vote dans `social_choice.py`, agents avec personnalites, resolution de conflits. `GovernancePlugin` (4 fonctions SK).

---

### 2.3.2 Agent de Detection de Sophismes et Biais Cognitifs
*   **Etudiant :** arthur.hamard (solo)
*   **Sujet :** [`sujets/2.3.2_Agent_Detection_Sophismes_Biais_Cognitifs.md`](sujets/2.3.2_Agent_Detection_Sophismes_Biais_Cognitifs.md)
*   **Repertoire :** `2.3.2-detection-sophismes/`
*   **Etat :** Integre | Score : 90%
*   **Integration :** `InformalAnalysisAgent(BaseAgent)`, `FrenchFallacyAdapter` (3-tier), `TaxonomySophismDetector` (8 familles, 28 labels). Corpus benchmark avec taxonomy PKs.
*   **Issue ouverte :** #169 (CamemBERT fine-tuned)

---

### 2.3.3 Agent de Generation de Contre-Arguments
*   **Etudiant :** leo.sambrook (solo)
*   **Sujet :** [`sujets/2.3.3_Agent_Generation_Contre_Arguments.md`](sujets/2.3.3_Agent_Generation_Contre_Arguments.md)
*   **Repertoire :** `2.3.3-generation-contre-argument/`
*   **Etat :** Integre | Score : 95%
*   **Integration :** `CounterArgumentAgent(BaseAgent)`, 5 strategies rhetoriques, evaluateur 5 criteres, validation Tweety. Plugin SK.

---

### 2.3.5 Agent d'Evaluation de la Qualite Argumentative
*   **Etudiants :** quentin.prunet, hugo.schreiber, jules.raitiere-delsupexhe, maxime.cambou
*   **Sujet :** [`sujets/sujet_2.3.5_agent_evaluation_qualite.md`](sujets/sujet_2.3.5_agent_evaluation_qualite.md)
*   **Repertoire :** `2.3.5_argument_quality/`
*   **Etat :** Integre | Score : 90%
*   **Integration :** 9 vertus argumentatives, `QualityScoringPlugin` (3 fonctions SK), degradation gracieuse si spaCy/textstat absents.

---

### 2.3.6 Integration de LLMs Locaux Legers
*   **Etudiants :** amine.el-maalouf, aziz.zeghal, lucas.tilly, matthias.laithier, oscar.le-dauphin
*   **Sujet :** [`sujets/2.3.6_Integration_LLMs_locaux_legers.md`](sujets/2.3.6_Integration_LLMs_locaux_legers.md)
*   **Repertoire :** `2.3.6_local_llm/`
*   **Etat :** Integre | Score : 80%
*   **Integration :** `LocalLLMService` (multi-backend : vLLM, Ollama, llama-cpp), async, `ServiceDiscovery` compatible.

---

## Indexation et Analyse

### 2.4.1 Index Semantique d'Arguments
*   **Etudiants :** leo.lopes, yanis.martin (+ lucas.duport)
*   **Sujet :** [`sujets/2.4.1_Index_Semantique_Arguments.md`](sujets/2.4.1_Index_Semantique_Arguments.md)
*   **Repertoire :** `Arg_Semantic_Index/`
*   **Etat :** Integre | Score : 80%
*   **Integration :** `SemanticIndexService` (index, search, ask), `CapabilityRegistry`. Frontend Streamlit standalone.
*   **Issue ouverte :** #174 (argument-level chunking)

---

### 2.5.3 Developpement d'un Serveur MCP pour l'Analyse Argumentative
*   **Etudiants :** enguerrand.turcat, titouan.verhille
*   **Sujet :** [`sujets/2.5.3_Developpement_Serveur_MCP_Analyse_Argumentative.md`](sujets/2.5.3_Developpement_Serveur_MCP_Analyse_Argumentative.md)
*   **Repertoire :** `argumentation_analysis/services/mcp_server/` (directement dans le tronc)
*   **Etat :** Integre | Score : 90%
*   **Integration :** Serveur MCP avec tools, session manager, Dockerfile. Transport streamable-http.

---

### 2.5.6 Protection des Systemes d'IA contre les Attaques Adversariales
*   **Etudiants :** pierre.schweitzer, maxime.ruff, joric.hantzberg
*   **Sujet :** [`sujets/2.5.6_Protection_Systemes_IA_Attaques_Adversariales.md`](sujets/2.5.6_Protection_Systemes_IA_Attaques_Adversariales.md)
*   **Repertoire :** Aucun (code non soumis)
*   **Etat :** Non soumis | Score : 0%
*   **Integration :** Framework "AI Shield" presente en soutenance mais jamais soumis.
*   **Issue ouverte :** #166 (recreation depuis description soutenance)

---

## Interfaces et Applications

### 3.1.1 Interface Web pour l'Analyse Argumentative
*   **Etudiants :** erwin.rodrigues, robin.de-bastos
*   **Sujet :** [`sujets/3.1.1_Interface_Web_Analyse_Argumentative.md`](sujets/3.1.1_Interface_Web_Analyse_Argumentative.md)
*   **Repertoire :** `interface_web/`
*   **Etat :** Partiellement integre | Score : 65%
*   **Integration :** Starlette ASGI (migre de Flask), routes JTMS + WebSocket. Autres agents manquent de routes web.
*   **Issue ouverte :** #168 (routes web pour tous les agents)

---

### 3.1.5 Interface Mobile
*   **Etudiants :** angela.saade, armand.blin, baptiste.arnold
*   **Sujet :** (pas de fichier sujet dedie)
*   **Repertoire :** `3.1.5_Interface_Mobile/`
*   **Etat :** Integre | Score : 70%
*   **Integration :** 4 endpoints API mobile dans `api/mobile_endpoints.py` (analyze, fallacies, validate, chat). App React Native standalone.

---

## Projets Custom

### [Custom] Speech to Text et Analyse d'Arguments Fallacieux
*   **Etudiants :** cedric.damais, gabriel.calvente, leon.ayral, yacine.benihaddadene
*   **Sujet :** [`sujets/Custom_Speech_to_Text_Analyse_Arguments_Fallacieux.md`](sujets/Custom_Speech_to_Text_Analyse_Arguments_Fallacieux.md)
*   **Repertoire :** `speech-to-text/`
*   **Etat :** Integre | Score : 75%
*   **Integration :** `SpeechTranscriptionService` (2-tier : Whisper API + Gradio), async, chaine transcription-analyse.

---

### [Custom] Resolution d'Enquete Policiere par IA (CaseAI/Moriarty)
*   **Etudiants :** etienne.senigout, pierre.braud
*   **Sujet :** (pas de fichier sujet dedie)
*   **Repertoire :** `CaseAI/`
*   **Etat :** Partiellement integre | Score : 50%
*   **Integration :** Transformation en paradigme Oracle/Moriarty dans `agents/core/oracle/`. Jeu Phaser.js standalone.

---

## Interdependances

| Projet source | Utilise par | Dependance |
|--------------|------------|------------|
| 2.3.2 Detection sophismes | Pipeline unifie, 2.4.1 Index | Detection de fallacies |
| 2.3.6 LLMs locaux | Tous les agents | Backend LLM alternatif |
| 1.4.1 JTMS/ATMS | Pipeline unifie | Maintenance de croyances |
| 2.1.6 Gouvernance | Pipeline unifie | Decisions collectives |
| 2.3.5 Qualite | Pipeline unifie, ranking | Scoring arguments |
| 2.3.3 Contre-arguments | Pipeline unifie, debate | Strategies rhetoriques |
| 1.2.7 Dialogue | Pipeline unifie | Analyse adversariale |
| 2.4.1 Index semantique | Pipeline unifie | Recherche arguments |
| [Custom] Speech-to-text | Pipeline complet | Transcription audio |
