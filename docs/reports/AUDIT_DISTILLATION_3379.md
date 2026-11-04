# Audit de distillation — ce que chaque projet étudiant offre que le tronc ne porte pas au lecteur (#3379)

Le 03/11, deux capacités nommées par l'utilisateur manquent au tronc : les personas
historien/stratège, et un moteur de stratégie qui oriente l'analyse. La distillation avait été
annoncée finie (#35). « Intégré » voulait dire *enregistré et appelable* — jamais *sa
contribution singulière atteint le lecteur*. Cet audit mesure, projet par projet, la distance
entre les deux.

## Méthode — trois instruments, un par colonne

Chaque colonne de la table vient d'une mesure, pas d'une impression :

1. **Consumer de production** — census des `capability="…"` sous `argumentation_analysis/`
   (les règles de #1842/#1980 : `add_phase(capability=…)`, jamais un test seul) :
   ```bash
   grep -rn 'capability="' --include=*.py argumentation_analysis/ \
     | sed 's/.*capability="\([a-z_]*\)".*/\1/' | sort | uniq -c | sort -rn
   ```
2. **Atteint le rendu ?** — census des champs lus par la surface de restitution (les plugins
   d'actes + leurs extracteurs, `argumentation_analysis/reporting/restitution/`) :
   ```bash
   grep -ohE 'getattr\(state, "[a-z_]+"' argumentation_analysis/reporting/restitution/*.py \
     | sed 's/getattr(state, "//;s/"//' | sort | uniq -c | sort -rn
   ```
   Un champ écrit par une phase mais absent de cette liste n'atteint jamais les quatre actes
   (`act1_framing`, `act2_narrative`, `act3_conclusion`, `narrative_synthesis`).
3. **Où il vit** — lignes d'enregistrement dans `orchestration/registry_setup.py` et sites
   d'appel dans `orchestration/invoke_callables.py`.

## Table — un projet, une ligne

| projet | capacité offerte (README/code) | où elle vit dans le tronc | consumer de production | atteint le rendu ? | singulier vs zero-shot ? | verdict |
|---|---|---|---|---|---|---|
| **1.4.1-JTMS** | graphe de croyances à justifications, rétraction, chargement JSON (`README.md`) | `services/jtms/jtms_core.py` (JTMS), `services/jtms/atms_core.py` (ATMS) ; enregistrés `registry_setup.py:178-196` | `belief_maintenance` ×12 (`orchestration/workflows.py:261,351,541,680`…), `atms_reasoning` ×3 (`workflows.py:1044`, `workflows/formal_verification.py:167`) | **oui, comme signal dérivé** : `state.jtms_beliefs` lu par `compute_argument_convergence` (`plugins/narrative_synthesis_plugin.py:499`) → `global_projection.py:78` ; #3145 la classe DÉRIVÉE (l'écho JTMS d'un sophisme ne compte pas comme méthode indépendante, `narrative_synthesis_plugin.py:474-480`) ; ATMS : aucun lecteur | **oui** — la rétraction sous nouvelle information est instrumentale ; un zero-shot ne rejoue pas un JTMS | **kept and reaching the reader** (honnêtement : comme contenu cité, pas comme voix indépendante) |
| **1_2_7_argumentation_dialogique** | débat multi-agents, 6 personnalités argumentatives (`README.md`) | `agents/core/debate/debate_agent.py` (DebateAgent 8 personnalités) ; enregistré `registry_setup.py:134-139` ; le vocabulaire dialogique Walton-Krabbe vit dans `debate/protocols.py` (#2137, #1649) | `adversarial_debate` ×9, `dialogue_protocols` ×3 (`workflows.py:956,1289`, `workflows/formal_debate.py:67`) | **oui** : `state.debate_transcripts` lu par `act2_narrative_plugin.py:1344` et `act3_conclusion_plugin.py:2701` (échanges non vides seulement) | **partiellement** — les tours structurés + score + gagnant sont instrumentaux ; la prose d'un tour reste du modèle | **kept and reaching the reader** |
| **2.1.6_multiagent_governance_prototype** | benchmark de gouvernance multi-agents : négociation, **apprentissage (Q-learning)**, **formation de coalitions**, simulation réseau, **analyse de manipulabilité** (`README.md`) | votes/scrutins : `agents/core/governance/governance_methods.py` + `social_choice.py`, plugin `plugins/governance_plugin.py` ; personnalités/coalitions/Q-learning : `agents/core/governance/governance_agent.py:38,68,83` — enregistré `registry_setup.py:151-161` | `governance_simulation` ×11. **Mais** la phase de production (`_invoke_governance`, `invoke_callables.py:2892`) agrège des positions amont en un vote formel (`_aggregate_governance_votes`, ~`:3003-3013`) + délibération LLM — **sans instancier les agents** (coalitions/Q-learning jamais exécutés) | **oui** : `state.governance_decisions` lu 4× (`act2_narrative_plugin.py`, `act3_conclusion_plugin.py`, `cited_units.py`, `reading_record.py`) | votes : **oui** (le scrutin est instrumental) ; coalitions/Q-learning/manipulabilité : **oui, singulier** (nommé par l'utilisateur) — et non portés | **kept and reaching** (votes) **+ kept but inert** (coalitions, Q-learning, manipulabilité) → issue #3386 |
| **2.3.2-detection-sophismes** | pipeline NLP hybride, explicable, de détection de sophismes en français (`README.md`) | `agents/core/informal/` + `plugins/french_fallacy_plugin.py` (3 niveaux) + `plugins/fallacy_workflow_plugin.py` (descente hiérarchique, `registry_setup.py:250-255`) ; détecteur auto-hébergé `:234` | `hierarchical_fallacy_detection` ×9, `neural_fallacy_detection` ×6, `fallacy_winner_reading` ×3 | **oui** : `state.identified_fallacies` lu 8× (`act2`, `act3`, `cited_units.py`, `conclusion_salience.py`) | **oui** — la descente de taxonomie calibrée est l'instrument que le zero-shot n'atteint pas (« the Cap », #3374) | **kept and reaching the reader** |
| **2.3.3-generation-contre-argument** | analyser un argument, identifier ses vulnérabilités, générer des contre-arguments typés (`README.md`) | `agents/core/counter_argument/` (5 types + 5 stratégies, `definitions.py`) ; enregistré `registry_setup.py:98` | `counter_argument_generation` ×14 | **oui** : `state.counter_arguments` lu 4× (`act2`, `act3`, `cited_units.py`, `reading_record.py`) | **partiellement** — la sélection par cibles et la citation d'unités sont instrumentales | **kept and reaching the reader** |
| **2.3.5_argument_quality** | 9 vertus argumentatives détectées par heuristiques linguistiques, note par vertu (`README.md`) | `agents/core/quality/quality_evaluator.py` (9 vertus) + `agentic_virtue_detectors.py` (LLMCallable injectable) ; enregistré `registry_setup.py:114-119` | `argument_quality` ×22 (le plus demandé du tronc) | **oui** : `state.argument_quality_scores` lu 8× (`act2`, `act3`, `conclusion_salience.py`, `specialist_roles.py`) | **partiellement** — les heuristiques (connecteurs, Flesch, regex citations) sont instrumentales ; la note globale reste du modèle | **kept and reaching the reader** |
| **2.3.6_local_llm** | API de détection de sophismes sur LLM local (`README.md`) | `services/local_llm_service.py` (adapteur OpenAI-compatible) + `self_hosted_fallacy_detector` (`registry_setup.py:234`) | `local_llm` ×3 (`workflows.py:309,439`, `act3_conclusion_plugin.py:1485`) | **oui, comme statut** : `state.local_llm_results` lu par `act3_conclusion_plugin.py:1466` et `reading_record.py:274` (statuts depuis #3113) | **non** — infrastructure de routage, pas une capacité d'analyse | **kept and reaching the reader** (en tant que statut ; la capacité analytique est celle de 2.3.2) |
| **3.1.5_Interface_Mobile** | app mobile d'analyse d'arguments (`README.md`) | `api/routers/mobile_endpoints.py`, monté `api/main.py:14,103` | surface HTTP (`/api`), **pas de phase** | n/a — canal de distribution, pas un producteur d'analyse | **non** — un canal | **kept** (canal de livraison) |
| **abs_arg_dung** | agent d'argumentation abstraite de Dung sur Tweety (`README.md`) | `state.dung_frameworks` + `reporting/restitution/native_dung.py`, `dung_reader.py` | `dung_extensions` ×7, `ranking_semantics` ×5 | **oui, richement** : `dung_frameworks` lu 5× (`act2`, `act3`, `cited_units.py`, `native_dung.py`) + le lecteur dédié `dung_reader.py` ; les rejections Dung nourrissent la convergence (`global_projection.py`, `_native_dung_rejections`) | **oui** — les extensions de sémantiques sont l'instrument nommé par le Cap | **kept and reaching the reader** |
| **Arg_Semantic_Index** (sujet 2.4.1) | indexation sémantique et recherche sur discours historiques, Kernel Memory (`README.md`) | `services/semantic_index_service.py`, enregistré `registry_setup.py:306-311` | `semantic_indexing` ×3 (`invoke_callables.py:4799`) | **non** : la phase écrit `state.semantic_index_refs` (`shared_state.py:810,1630-1646`) — **aucun lecteur dans `reporting/restitution/`** (census nul) | **potentiellement** — l'ancrage KB orienterait l'analyse (cf. #2960) | **kept but inert** → issue #3387 |
| **speech-to-text** (sujet Custom) | transcrire l'audio puis analyser le texte (`README.md`) | `services/speech_transcription_service.py`, enregistré `registry_setup.py:326-331` | `speech_transcription` ×3 | n/a — canal d'**entrée**, la barre du rendu ne s'applique pas (le texte transcrit entre par le chemin normal) | **non** — un modality d'entrée | **kept** (canal d'entrée ; pas d'issue : pas de contribution analytique singulière) |
| **CaseAI** | front-end conversationnel (Slack) | **aucune référence dans le tronc** — `grep -rln "CaseAI\|caseai\|slack" argumentation_analysis/ api/ interface_web/` = 0 hit | aucun | n/a | **non** — un canal de livraison | **not ported** — raison consignée : canal de livraison sans contribution analytique ; pas d'issue ouverte pour cette raison |

Sujets de `docs/projets/sujets/` portés par le tronc sans dossier étudiant numéroté : **2.5.6**
(protection attaques adversariales → `ai_shield_service`, `registry_setup.py:701-706`),
**DEMOCRATECH** (`workflows/democratech.py` et le workflow `governance`), **2.5.3** (serveur
MCP → `services/mcp_server/tools/capability_tools.py`, `specialized_tools.py`), **3.1.1**
(interface web → `interface_web/`), **1.1.5** (formules booléennes → logique propositionnelle,
`fol_reasoning` ×6 / `propositional_logic` ×6). Aucun de ces cinq n'est « étudiant intégré » au
sens de #35 ; ils sont cités pour fermer l'énumération de l'issue.

## Ce que la table dit

- **Neuf lignes sur douze atteignent le lecteur** — mais deux d'entre elles de manière
  dégradée : le JTMS comme signal dérivé (jamais voix indépendante, #3145), le local LLM
  comme statut de phase.
- **Deux lignes inertes** avec une contribution singulière : les coalitions/Q-learning/
  manipulabilité de 2.1.6 (l'agent existe, la phase vote sans lui — exactement ce que
  l'utilisateur a nommé), et l'index sémantique (les refs s'écrivent, rien ne les lit).
- **Une ligne non portée** sans contribution analytique : CaseAI.
- Le moteur de stratégie réclamé par l'utilisateur n'est pas dans la table parce qu'il n'a
  jamais été livré par un projet : 2.1.6 offrait la matière (coalitions, manipulabilité),
  le tronc n'en porte que le vote. Les personas historien/stratège sont, eux, en cours de
  fusion (#3377, PR #3385).

## DoD

- [x] Table complète pour chaque projet, chaque cellule citant fichier:ligne ou la commande
      qui la reproduit (les deux commandes ci-dessus, exécutées le 04/11).
- [x] Une issue par ligne `kept but inert` / `not ported` à contribution singulière :
      #3386 (2.1.6 coalitions/Q-learning/manipulabilité), #3387 (index sémantique non lu).
- [x] Le libellé « integrated » de `CLAUDE.md` mis à jour vers ce que la table mesure.

Épic : #3374. Issue : #3379.
