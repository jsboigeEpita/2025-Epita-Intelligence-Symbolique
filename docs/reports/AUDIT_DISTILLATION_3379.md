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
   **Limite de l'instrument** (review R1140) : ce census ne voit que la forme
   `getattr(state, "…")` **et ne couvre que `reporting/restitution/`** — une lecture
   `state.champ` directe, une lecture via un dict exporté, ou une lecture dans un
   producteur d'acte qui vit sous `plugins/` lui échappent toutes (mesuré : la cellule
   ATMS de la première version disait « aucun lecteur » à tort —
   `narrative_synthesis_plugin.py:143` lit `atms_contexts`). Pour chaque cellule
   « aucun lecteur » ci-dessous, l'instrument est donc le grep du **nom de champ sur
   tout l'arbre**, qui voit toutes les formes — ex. `git grep -n semantic_index_refs`
   ne rend que le producteur (`shared_state.py`), la plomberie d'export
   (`sanitize_state.py`, `conversational_benchmark.py`, `run_spectacular_comparison.py`)
   et des tests : aucun acte.
3. **Où il vit** — lignes d'enregistrement dans `orchestration/registry_setup.py` et sites
   d'appel dans `orchestration/invoke_callables.py`.

## Table — un projet, une ligne

| projet | capacité offerte (README/code) | où elle vit dans le tronc | consumer de production | atteint le rendu ? | singulier vs zero-shot ? | verdict |
|---|---|---|---|---|---|---|
| **1.4.1-JTMS** | graphe de croyances à justifications, rétraction, chargement JSON (`README.md`) | `services/jtms/jtms_core.py` (JTMS), `services/jtms/atms_core.py` (ATMS) ; enregistrés `registry_setup.py:178-196` | `belief_maintenance` ×12 (`orchestration/workflows.py:261,351,541,680`…), `atms_reasoning` ×3 (`workflows.py:1044`, `workflows/formal_verification.py:167`) | **oui, comme signal dérivé** : `state.jtms_beliefs` lu par `compute_argument_convergence` (`plugins/narrative_synthesis_plugin.py:499`) → `global_projection.py:78` ; #3145 la classe DÉRIVÉE (l'écho JTMS d'un sophisme ne compte pas comme méthode indépendante, `narrative_synthesis_plugin.py:474-480`) ; l'ATMS atteint lui aussi le rendu, même forme dérivée : `narrative_synthesis_plugin.py:143-167` lit `state.atms_contexts` dans la convergence (**correction R1140** : la première version de cette cellule disait « aucun lecteur » — le census `getattr` initial ne couvrait que `reporting/restitution/` et un producteur d'acte vit dans `plugins/` ; le grep large `git grep -n atms_contexts` voit la lecture) | **oui** — la rétraction sous nouvelle information est instrumentale ; un zero-shot ne rejoue pas un JTMS | **kept and reaching the reader** (honnêtement : comme contenu cité, pas comme voix indépendante) |
| **1_2_7_argumentation_dialogique** | débat multi-agents, 6 personnalités argumentatives (`README.md`) | `agents/core/debate/debate_agent.py` (DebateAgent 8 personnalités) ; enregistré `registry_setup.py:134-139` ; le vocabulaire dialogique Walton-Krabbe vit dans `debate/protocols.py` (#2137, #1649) | `adversarial_debate` ×9, `dialogue_protocols` ×3 (`workflows.py:956,1289`, `workflows/formal_debate.py:67`) | **oui** : `state.debate_transcripts` lu par `act2_narrative_plugin.py:1344` et `act3_conclusion_plugin.py:2701` (échanges non vides seulement) | **partiellement** — les tours structurés + score + gagnant sont instrumentaux ; la prose d'un tour reste du modèle | **kept and reaching the reader** |
| **2.1.6_multiagent_governance_prototype** | benchmark de gouvernance multi-agents : négociation, **apprentissage (Q-learning)**, **formation de coalitions**, simulation réseau, **analyse de manipulabilité** (`README.md`) | votes/scrutins : `agents/core/governance/governance_methods.py` + `social_choice.py`, plugin `plugins/governance_plugin.py` ; personnalités/coalitions/Q-learning : `agents/core/governance/governance_agent.py:38,68,83` — enregistré `registry_setup.py:151-161` | `governance_simulation` ×11. La phase de production (`_invoke_governance`, `invoke_callables.py:2942`) agrège des positions amont en un vote formel + délibération LLM. Les agents sont instanciés comme électeurs : un `Agent(elector_<vertu>, personality="stubborn", preferences=ordre)` par vertu (`_derive_governance_profile`, `:2683`, construction `:2747-2753`). **Re-lecture du 13/11** : la négociation tourne. `play_sensitivity` (`:3080`) rejoue le profil sous des postures de négociation (`coalition_play.py:89` appelle `negotiate`) et écrit `coalition` dans le verdict (`:3088`, #3418). La manipulabilité du profil déclaré est calculée par `compute_manipulability` (`:3097`, le moteur de #3385). Le Q-learning ne tourne pas : `git grep -n -e '\.update_q(' -e 'update_memory(' -- argumentation_analysis/ api/ scripts/` rend la définition `governance_agent.py:112` et l'appel interne `:133`, aucun appelant de `update_memory`. Le grep que cette cellule citait le 04/11 (« 0 hit » sous `orchestration/` et `plugins/`) rend 16 lignes le 13/11 | **votes : oui** : `state.governance_decisions` lu 4× (`act2_narrative_plugin.py`, `act3_conclusion_plugin.py`, `cited_units.py`, `reading_record.py`). **Coalitions et manipulabilité, cycle 6 du panel** (mesures 1 et 2 ci-dessous) : le jeu de coalitions tourne sur 9 documents sur 9. Il ne change le vainqueur sur aucun (`outcome_changed` 0 sur 9) et dépend de la posture sur 9 (`stance_dependent`), donc sa ligne (`coalition_note`, `coalition_play.py:269`) ne s'imprime sur aucun. La ligne de manipulabilité entre dans les prompts des actes II et III (`act2_narrative_plugin.py:2548`, `act3_conclusion_plugin.py:3796`) sur 5 documents ; aucun acte rendu ne contient « manipulab » (0 sur 10). Le cycle 6 précède #3524 ; #3530 rapporte qu'après #3524 la manipulabilité est vide dès qu'un vainqueur de Condorcet existe (rapporté, non re-vérifié) | votes : **oui** (le scrutin est instrumental) ; coalitions/Q-learning/manipulabilité : **oui, singulier** (nommé par l'utilisateur) — coalitions et manipulabilité calculées, pas rendues | **kept and reaching** (votes) **+ kept but inert au rendu** (coalitions jouées sans effet sur l'issue ; manipulabilité jusqu'au prompt, pas au rendu ; Q-learning sans appelant) → issues #3386, #3530 |
| **2.3.2-detection-sophismes** | pipeline NLP hybride, explicable, de détection de sophismes en français (`README.md`) | `agents/core/informal/` + `plugins/french_fallacy_plugin.py` (3 niveaux) + `plugins/fallacy_workflow_plugin.py` (descente hiérarchique, `registry_setup.py:250-255`) ; détecteur auto-hébergé `:234` | `hierarchical_fallacy_detection` ×9, `neural_fallacy_detection` ×6, `fallacy_winner_reading` ×3 | **oui** : `state.identified_fallacies` lu 8× (`act2`, `act3`, `cited_units.py`, `conclusion_salience.py`) | **oui** — la descente de taxonomie calibrée est l'instrument que le zero-shot n'atteint pas (« the Cap », #3374) | **kept and reaching the reader** |
| **2.3.3-generation-contre-argument** | analyser un argument, identifier ses vulnérabilités, générer des contre-arguments typés (`README.md`) | `agents/core/counter_argument/` (5 types + 5 stratégies, `definitions.py`) ; enregistré `registry_setup.py:98` | `counter_argument_generation` ×14 | **oui** : `state.counter_arguments` lu 4× (`act2`, `act3`, `cited_units.py`, `reading_record.py`) | **partiellement** — la sélection par cibles et la citation d'unités sont instrumentales | **kept and reaching the reader** |
| **2.3.5_argument_quality** | 9 vertus argumentatives détectées par heuristiques linguistiques, note par vertu (`README.md`) | `agents/core/quality/quality_evaluator.py` (9 vertus) + `agentic_virtue_detectors.py` (LLMCallable injectable) ; enregistré `registry_setup.py:114-119` | `argument_quality` ×22 (le plus demandé du tronc) | **oui** : `state.argument_quality_scores` lu 8× (`act2`, `act3`, `conclusion_salience.py`, `specialist_roles.py`) | **partiellement** — les heuristiques (connecteurs, Flesch, regex citations) sont instrumentales ; la note globale reste du modèle | **kept and reaching the reader** |
| **2.3.6_local_llm** | API de détection de sophismes sur LLM local (`README.md`) | `services/local_llm_service.py` (adapteur OpenAI-compatible) + `self_hosted_fallacy_detector` (`registry_setup.py:234`) | `local_llm` ×3 au census : deux phases, dans les workflows `standard` et `full` (`workflows.py:348`, `:507`), et le libellé d'absence `act3_conclusion_plugin.py:1608`. **Re-lecture du 13/11** : aucune phase `local_llm` dans `build_spectacular_workflow` (`workflows.py:818`), le workflow que le panel exécute (défaut de `scripts/dataset/run_corpus_batch.py:1100`, que `scripts/panel/run_cycle.py:237` lance sans `--workflow`) | **statut seulement, et pas sur le panel** : les lecteurs existent (`_collect_local_llm_dimension`, `act3_conclusion_plugin.py:1572` ; `_local_llm_reading_line`, `reading_record.py:469` ; statuts depuis #3113). Au cycle 6, la phase n'apparaît dans aucun `workflow_results` et `local_llm_results` est vide sur 10 documents sur 10 (mesure 3 ci-dessous). Une liste vide est un silence par conception (`act3_conclusion_plugin.py:1580-1582`) | **non** — infrastructure de routage, pas une capacité d'analyse | **kept, statut hors du workflow du panel** (atteint le lecteur comme statut dans `standard` et `full` seulement ; la capacité analytique est celle de 2.3.2) |
| **3.1.5_Interface_Mobile** | app mobile d'analyse d'arguments (`README.md`) | `api/routers/mobile_endpoints.py`, monté `api/main.py:14,103` | surface HTTP (`/api`), **pas de phase** | n/a — canal de distribution, pas un producteur d'analyse | **non** — un canal | **kept** (canal de livraison) |
| **abs_arg_dung** | agent d'argumentation abstraite de Dung sur Tweety (`README.md`) | `state.dung_frameworks` + `reporting/restitution/native_dung.py`, `dung_reader.py` | `dung_extensions` ×7, `ranking_semantics` ×5 | **oui, richement** : `dung_frameworks` lu 5× (`act2`, `act3`, `cited_units.py`, `native_dung.py`) + le lecteur dédié `dung_reader.py` ; les rejections Dung nourrissent la convergence (`global_projection.py`, `_native_dung_rejections`) | **oui** — les extensions de sémantiques sont l'instrument nommé par le Cap | **kept and reaching the reader** |
| **Arg_Semantic_Index** (sujet 2.4.1) | indexation sémantique et recherche sur discours historiques, Kernel Memory (`README.md`) | `services/semantic_index_service.py`, enregistré `registry_setup.py:315-324` avec `invoke=_invoke_semantic_index` | `semantic_indexing` ×3. **Re-lecture du 13/11** : depuis la v1 de #3387 (#3426), la phase (`_invoke_semantic_index`, `invoke_callables.py:4876`) classe les passages du document analysé contre la thèse de la première lecture et rend `priority_spans` (`:4952`) | **oriente la sélection ; effet sur le rendu non mesuré**. `semantic_priority_spans` est non vide sur 10 documents sur 10 au cycle 6 (mesure 3 ci-dessous), et le sélecteur de budget le lit (`_selection_priority_spans`, `invoke_callables.py:9608`, appel `:9717`). Aucun acte ne lit les passages eux-mêmes ; ce qu'ils changent au rendu demande une ablation (#3387). La branche `semantic_index_refs` n'a plus de producteur : `_write_semantic_index_to_state` (`state_writers.py:1314`) ne l'écrit qu'à partir d'une clé `results` que la phase ne rend pas, et le champ est vide sur 10 sur 10 (mesure 3). Ses seuls lecteurs comptent, exportent ou effacent (`shared_state.py:2803,2853`, `sanitize_state.py:258`, `conversational_benchmark.py:84`, `scripts/run_spectacular_comparison.py:103` ; `git grep -n semantic_index_refs -- ':!tests/' ':!docs/'`) | **potentiellement** — l'ancrage KB orienterait l'analyse (cf. #2960) | **kept, oriente la sélection** (v1) ; effet au rendu non mesuré ; lecture du corpus et sort de `semantic_index_refs` → #3387 |
| **speech-to-text** (sujet Custom) | transcrire l'audio puis analyser le texte (`README.md`) | `services/speech_transcription_service.py`, enregistré `registry_setup.py:326-331` | `speech_transcription` ×3 | n/a — canal d'**entrée**, la barre du rendu ne s'applique pas (le texte transcrit entre par le chemin normal) | **non** — un modality d'entrée | **kept** (canal d'entrée ; pas d'issue : pas de contribution analytique singulière) |
| **CaseAI** | front-end conversationnel (Slack) | **aucune référence dans le tronc** — `grep -rln "CaseAI\|caseai\|slack" argumentation_analysis/ api/ interface_web/` = 0 hit | aucun | n/a | **non** — un canal de livraison | **not ported** — raison consignée : canal de livraison sans contribution analytique ; pas d'issue ouverte pour cette raison |

Sujets de `docs/projets/sujets/` portés par le tronc sans dossier étudiant numéroté : **2.5.6**
(protection attaques adversariales → `ai_shield_service`, `registry_setup.py:701-706`),
**DEMOCRATECH** (`workflows/democratech.py` et le workflow `governance`), **2.5.3** (serveur
MCP → `services/mcp_server/tools/capability_tools.py`, `specialized_tools.py`), **3.1.1**
(interface web → `interface_web/`), **1.1.5** (formules booléennes → logique propositionnelle,
`fol_reasoning` ×6 / `propositional_logic` ×6). Aucun de ces cinq n'est « étudiant intégré » au
sens de #35 ; ils sont cités pour fermer l'énumération de l'issue.

## Re-lecture du 13/11 — les mesures citées par la table

Le 13/11, trois lignes ont été relues contre `main` (après #3531) et contre les états
enregistrés du cycle 6 du panel (10 documents). Ce cycle a tourné à la tête de `main`
après la fusion de #3521, donc avant #3524. Les états vivent sous
`argumentation_analysis/evaluation/results/panel_cycles/c6/states/` (gitignoré) : les
commandes ci-dessous tournent depuis la racine du dépôt, sur un siège qui les détient,
dans l'environnement conda du siège. Elles ne comptent que des champs ; aucune n'affiche
de texte ni d'identifiant de document.

Mesure 1 — gouvernance (sortie : `10 9 9 0 9`, soit états, documents avec une décision,
documents avec un jeu de coalitions, `outcome_changed`, `stance_dependent`) :

```bash
python -c "import glob,json;S=[json.load(open(f,encoding='utf-8')) for f in glob.glob('argumentation_analysis/evaluation/results/panel_cycles/c6/states/state_full_*.json')];D=[[d for d in s.get('governance_decisions') or [] if isinstance(d,dict)] for s in S];D=[x for x in D if x];C=[[d.get('coalition') or {} for d in x] for x in D];print(len(S),len(D),sum(any(c) for c in C),sum(any(e.get('outcome_changed') for e in c) for c in C),sum(any(e.get('stance_dependent') for e in c) for c in C))"
```

Mesure 2 — ce que `coalition_note` donne aux prompts des actes, et ce que les actes rendus
contiennent (sortie : `0 5 0`, soit documents avec la ligne « Jeu de coalitions »,
documents avec la ligne « Manipulabilité », documents dont les quatre actes contiennent
« manipulab ») :

```bash
python -c "import glob,json,re;from argumentation_analysis.agents.core.governance.coalition_play import coalition_note;S=[json.load(open(f,encoding='utf-8')) for f in glob.glob('argumentation_analysis/evaluation/results/panel_cycles/c6/states/state_full_*.json')];N=[' | '.join(coalition_note(d) for d in s.get('governance_decisions') or [] if isinstance(d,dict)) for s in S];A=[' '.join(str(s.get(k) or '') for k in ('act1_framing','act2_narrative','act3_conclusion','narrative_synthesis')) for s in S];print(sum('Jeu de coalitions' in n for n in N),sum('Manipulabilit' in n for n in N),sum(bool(re.search('manipulab',a,re.I)) for a in A))"
```

Mesure 3 — local LLM et index sémantique (sortie : `10 0 10 0 0 10`, soit états,
`local_llm_results` non vide, `semantic_priority_spans` non vide, `semantic_index_refs`
non vide, `workflow_results` nommant `local_llm`, `workflow_results` nommant
`semantic_index`) :

```bash
python -c "import glob,json;S=[json.load(open(f,encoding='utf-8')) for f in glob.glob('argumentation_analysis/evaluation/results/panel_cycles/c6/states/state_full_*.json')];W=[json.dumps(s.get('workflow_results') or {}) for s in S];print(len(S),*(sum(bool(s.get(k)) for s in S) for k in ('local_llm_results','semantic_priority_spans','semantic_index_refs')),sum('local_llm' in w for w in W),sum('semantic_index' in w for w in W))"
```

Les neuf autres lignes gardent leur verdict du 04/11 ; la re-lecture du 13/11 ne les a
pas re-mesurées.

## Ce que la table dit — la partition que la table porte (correction R1140, re-lecture du 13/11)

- **6 lignes sur 12 atteignent le lecteur**, dont une de manière dégradée : le JTMS
  comme signal dérivé (jamais voix indépendante, #3145 — l'ATMS aussi, même forme,
  cf. sa cellule). Ces six verdicts sont ceux du 04/11.
- **1 ligne n'atteint le lecteur que comme statut de phase, et pas sur le panel** : le
  local LLM. Sa phase n'est que dans les workflows `standard` et `full` ; le panel
  exécute `spectacular`, et `local_llm_results` y est vide sur 10 documents sur 10. Le
  04/11 la comptait parmi les lignes qui atteignent le lecteur.
- **1 ligne oriente la sélection sans effet mesuré au rendu** : l'index sémantique.
  Ses passages prioritaires sont non vides sur 10 documents sur 10 et le sélecteur de
  budget les lit ; ce qu'ils changent au rendu attend une ablation (#3387). Le 04/11 la
  comptait inerte.
- **2 lignes sont des canaux** (3.1.5 mobile, speech-to-text) : la barre du rendu ne
  s'y applique pas — un canal qui transporte du texte ne porte pas de contribution
  analytique au lecteur, et le décompter parmi ceux qui « atteignent le lecteur »
  surévalue le résultat (la première version écrivait « 9 sur 12 » pour cela).
- **1 ligne inerte au rendu** avec une contribution singulière : 2.1.6. Le vote atteint
  le lecteur. La négociation tourne depuis #3418, mais le jeu de coalitions ne change
  l'issue sur aucun des 9 documents ; la manipulabilité atteint le prompt sur 5
  documents et le rendu sur aucun ; le Q-learning n'a pas d'appelant.
- **1 ligne non portée** sans contribution analytique : CaseAI.
- Le moteur de stratégie réclamé par l'utilisateur n'est pas dans la table parce qu'il n'a
  jamais été livré par un projet : 2.1.6 offrait la matière (coalitions, manipulabilité).
  Le tronc porte le vote, joue la négociation et calcule la manipulabilité ; ni l'une ni
  l'autre n'atteint encore le rendu. Les personas historien/stratège sont dans le tronc
  depuis PR #3385 (`agents/core/context/`) ; #3377 suit leurs consommateurs.

## DoD

- [x] Table complète pour chaque projet, chaque cellule citant fichier:ligne ou la commande
      qui la reproduit (les deux commandes ci-dessus, exécutées le 04/11).
- [x] Une issue par ligne `kept but inert` / `not ported` à contribution singulière :
      #3386 (2.1.6 coalitions/Q-learning/manipulabilité), #3387 (index sémantique non lu).
- [x] Le libellé « integrated » de `CLAUDE.md` mis à jour vers ce que la table mesure.
- [x] Re-lecture du 13/11 : les lignes 2.1.6, 2.3.6 et Arg_Semantic_Index relues contre
      `main` et le cycle 6 du panel (mesures 1 à 3), suivies par #3386 et #3530 (2.1.6)
      et #3387 (index sémantique, dont la v1 oriente la sélection) ; `CLAUDE.md` reprend
      la nouvelle partition.

Épic : #3374. Issue : #3379.
