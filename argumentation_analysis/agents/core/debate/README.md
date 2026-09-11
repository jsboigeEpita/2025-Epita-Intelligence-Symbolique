# `agents/core/debate/` — plugin de débat adversarial (agent multi-personnalités en compatibilité)

## Rôle et frontière

7 modules + `__init__` (1 809 lignes) — deux systèmes accolés lors de l'intégration du projet étudiant `1_2_7_argumentation_dialogique` : (1) un **débat adversarial à 8 personnalités** (génération d'arguments, scoring à 8 métriques, phases et modérateur), (2) un socle de **protocoles dialogiques Walton-Krabbe** (6 types de dialogue, 9 actes de langage, 10 schémas d'argumentation, base de connaissances). Frontière : le module produit une *évaluation adversariale* (scores, vainqueur, qualité honnête) et des *transcripts* ; il ne fait ni extraction, ni détection de sophismes, ni vote — il les consomme.

## Composants publics

- **Plugin — le seul chemin exercé en production** : `debate_agent.py`, `DebatePlugin` :93. Ses `def` décorés `@kernel_function` : `analyze_argument_quality` :107, `analyze_logical_structure` :138, `suggest_debate_strategy` :174 — **3**. `grep -c '@kernel_function'` en rend **4** : la docstring de classe :97 ouvre une ligne avec la chaîne (le piège d'over-count est réel ici) ;
- Scoring : `debate_scoring.py`, `ArgumentAnalyzer` :16 (`analyze_argument` :74, 8 métriques pondérées → `_calculate_persuasiveness` :207) ;
- Structures : `debate_definitions.py` — `ArgumentType` :14 (6 membres), `DebatePhase` :25 (5), `ArgumentMetrics` :35 (8 champs), `EnhancedArgument` :49, `DebateState` :71, `AGENT_PERSONALITIES` :90 (**8** archétypes) ;
- Agent / modérateur : `debate_agent.py`, `DebateAgent(BaseAgent)` :193, alias `EnhancedArgumentationAgent` :588, `EnhancedDebateModerator` :591 (utilitaire, pas un `BaseAgent`) ;
- Protocoles : `protocols.py` — `DialogueType` :18 (**6**), `SpeechAct` :29 (**9**), `Proposition` :43, `FormalArgument` :64, `DialogueMove` :87, `DialogueProtocol` :106, `InquiryProtocol` :135, `PersuasionProtocol` :197 ;
- Schémas : `argumentation_schemes.py` — `ArgumentationScheme` :34, `_load_argumentation_schemes` :52 (**10** schémas, table verbatim du livrable étudiant), `classify_scheme` :264 (matcher lexical déterministe, fail-loud), `schemes_as_prompt_context` :311 ;
- Base de connaissances : `knowledge_base.py`, `KnowledgeBase` :15.

`__init__.py` (69 l.) exporte **17** noms (`__all__` :41-59) — tous réels (imports :23-40). **Non exportés** : `KnowledgeBase`, `FormalArgument`, `DialogueMove`, `ArgumentationScheme`, `classify_scheme`.

## Points d'entrée valides

1. **Phases workflow** `capability="adversarial_debate"` : `orchestration/workflows.py:236` (`build_standard_workflow`), :311 (`build_full_workflow`), :496 (`build_iterative_analysis_workflow`), :936 (`build_spectacular_workflow`), :588 (`build_debate_governance_loop_workflow` — docstring « STUB ») ; `workflows/debate_tournament.py:80`, `workflows/democratech.py:107`, `workflows/comprehensive_analysis.py:95`, `workflows/belief_dynamics.py:56` ;
2. **Registre** : `orchestration/registry_setup.py:139-147` — `register_agent(name="debate_agent", agent_class=DebateAgent, capabilities=["adversarial_debate"], invoke=_invoke_debate_analysis)` ;
3. **Handler** : `await _invoke_debate_analysis(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]` — `orchestration/invoke_callables.py:1480` ; première instruction `plugin = DebatePlugin()` :1486, puis `plugin.analyze_argument_quality(input_text)` :1487 ;
4. **Writer d'état** : `CAPABILITY_STATE_WRITERS["adversarial_debate"] = _write_debate_to_state` — `orchestration/state_writers.py:2290`, définition :644 ;
5. **API** : `api/proposal_endpoints.py:180` expose `debate_tournament` comme workflow sélectionnable (`api/proposal_models.py:46`) ;
6. **Appel direct du plugin** (hors DAG) : `scripts/capstone_brick_health.py:274` appelle `_invoke_debate_analysis(CORPUS_A, ctx)` ; `examples/03_integrations/demo_unified_capabilities.py:154`.

Signature réelle du plugin : `DebatePlugin().analyze_argument_quality(text: str) -> str` (`debate_agent.py:107`) — renvoie une **chaîne JSON à 8 clés plates** (`logical_coherence` … `readability_score`, :118-129), **sans** enveloppe `metrics`.

## Amont / aval

- **Amont** (lu par `_invoke_debate_analysis`) : `phase_extract_output` (arguments), `phase_hierarchical_fallacy_output` :1522, `phase_counter_output` :1527, `phase_quality_output` :1531, `phase_jtms_output` :1537. Porte honnête : sans argument amont, branche dégradée explicite `debate_degraded=True` / `no_arguments_upstream` :1490-1512 (« pas de verdict fabriqué ») ;
- **Aval** : `UnifiedAnalysisState.debate_transcripts` (`core/shared_state.py:1000`, `add_debate_transcript`). Lecteurs : restitution `reporting/restitution/act2_narrative_plugin.py:727` (`_collect_debate`), CLI `cli/output_formatter.py:243` (`_render_debate`), synthèse profonde `agents/core/synthesis/deep_synthesis_agent.py:185` (champ citable), `core/state_manager_plugin.py:799`. `DebatePlugin` est aussi déclaré dans le registre de plugins de la factory (`agents/factory.py:94-97`).

## Statut d'intégration

**actif** (chemin plugin/scoring) · **compatibilité** (agent, modérateur, alias) · **résiduel** (`knowledge_base.py`, protocoles de dialogue instanciables). Mesures :

- **capability** : 1 déclarée (`registry_setup.py:144`), **9** littéraux `add_phase(capability="adversarial_debate")` en production (comptage `grep -n` sur `argumentation_analysis/`, liste ci-dessus), plus le routeur (`orchestration/router.py:365-366`, :422) et les harnais d'évaluation (`evaluation/run_iteration.py`, `evaluation/capability_eval.py:80`) ;
- **surface de capacité unique (#1842) : vérifiée** — `debate/__init__.py:65-69` est un **commentaire**, pas une fonction : `grep -n "register_with_capability_registry" argumentation_analysis/` ne trouve ici que ce commentaire (les seuls `def` restants sont `counter_argument/__init__.py:43`, câblé en `registry_setup.py:100`, et un commentaire jumeau dans `governance/`, `quality/`, `synthesis/`). Garde `tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py` → **8 passed** (mesuré) ; « câblé » y signifie : le module qui définit la fonction est celui que `registry_setup` importe, et la capability déclarée a un demandeur de production ;
- **`DebateAgent` (classe) n'est jamais instancié en production** — il n'occupe qu'un slot `agent_class=` (`registry_setup.py:141`) que le chemin d'invocation ne lit pas (`_invoke_debate_analysis` construit `DebatePlugin` directement). `grep -n "DebateAgent("` sur `argumentation_analysis/` → la seule occurrence est la définition `debate_agent.py:193` ; `AgentFactory.create_debate_agent` (`agents/factory.py:428`) n'a que des appelants de test. Donc `generate_argument`, `_adapt_strategy`, `_analyze_opponents`, `EnhancedDebateModerator.run_debate` sont **exercés par les tests seulement** : d'où **compatibilité** ;
- **`protocols.SpeechAct`** : importé en production par `agents/core/informal/dung_arbitration_stage.py:31` (:45-46 `WALTON_KRABBE_ATTACKING_ACTS`), atteint par `_invoke_dung_arbitration` (`invoke_callables.py:8786`) → statut **spécialisé**. Les classes `DialogueProtocol`/`InquiryProtocol`/`PersuasionProtocol` n'ont **aucun** appelant de production (le workflow `dialogue_protocols` passe par `agents/core/logic/dialogue_handler.py`, JVM/Tweety, pas par ce fichier) → **résiduel** ;
- **`argumentation_schemes.py`** : 2 points d'appel de production exécutés — `invoke_callables.py:1634` (`schemes_as_prompt_context`, bloc de prompt) et `state_writers.py:662` (`classify_scheme`) — plus `neuro_symbolic_arbitrator.py:52` via le stage d'arbitrage → **actif** (voir toutefois la limite n°1 : l'effet du second est nul).

## Artefacts et lecteurs

Transcript `{"topic", "exchanges": [{"point", "rebuttal", "scheme"?, "scheme_key"?, "critical_question"?}], "winner"}` écrit dans `state.debate_transcripts` ; scores de phase `debate_quality` (entier 0-5 **ou `None`**) + `debate_quality_source` ∈ {`llm`, `heuristic`, `unscored`} — contrat honnête GE-5 #1467 (`invoke_callables.py:1446` `_resolve_debate_quality`, commentaire :1696-1706) : `None` s'affiche « —/5 », jamais « 0/5 ». Lecteurs : restitution (Acte II), CLI, synthèse profonde, `api/agent_routes.py:272-285`.

## Tests représentatifs

```bash
conda run -n projet-is --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/debate/ -v
```

**209 `def test_`** sur 6 fichiers (comptage `grep -c 'def test_'` : test_debate.py 69, test_protocols.py 41, test_debate_scoring.py 35, test_debate_definitions.py 33, test_knowledge_base.py 20, test_argumentation_schemes.py 11) → **209 passed en 6,01 s** (mesuré, `-o addopts=`). Tests croisés hors répertoire : `agents/core/informal/test_dung_arbitration_stage.py`, `.../test_neuro_symbolic_arbitrator.py`, `orchestration/test_unified_pipeline.py` (mock du plugin), `test_value_gates.py`, `test_architecture_compliance.py`, `tests/agents/factories/test_agent_factory.py`, `tests/performance/test_integration_benchmarks.py`.

## Frères et parent

Parent : `agents/core/` ([`../README.md`](../README.md)). Frères : [`counter_argument/`](../counter_argument/README.md), [`governance/`](../governance/README.md), [`informal/`](../informal/README.md), [`quality/`](../quality/README.md), [`synthesis/`](../synthesis/README.md). Câblage : [`../../../orchestration/registry_setup.py`](../../../orchestration/registry_setup.py), [`../../../orchestration/invoke_callables.py`](../../../orchestration/invoke_callables.py). Origine : projet étudiant `1_2_7_argumentation_dialogique/` (racine du dépôt ; livrable source conservé en SANCTUAIRE read-only).

## Limites connues

- **Le grounding par schéma G8 (#1184) ne produit rien sur le chemin d'état — discordance de clés.** Le producteur (prompt LLM, `invoke_callables.py:1670`) demande `agent_a_point` / `agent_b_rebuttal` ; le consommateur (`state_writers.py:669-670`) lit `point` / `rebuttal`. Conséquences mesurées : `entry["point"]`/`entry["rebuttal"]` sont **toujours vides** ; `classify_scheme(point or rebuttal)` (:673) reçoit `""` et renvoie `None` (`argumentation_schemes.py:277-278`) ; et `act2_narrative_plugin.py:753` (« fail-loud: skip empty exchanges ») écarte l'échange → **aucun échange de débat n'atteint l'Acte II**. `api/agent_routes.py:276-277` lit, lui, les bons noms : les deux chemins se contredisent. Le test doré (`tests/unit/argumentation_analysis/orchestration/test_regression_golden.py:202`) fabrique les clés du *writer* (`point`/`rebuttal`) et passe donc au-dessus de la brèche. Le scratch gitignoré `.cache/_g8_smoke.py:20` reproduit la même erreur — indice que le writer n'a jamais été confronté à la sortie réelle ;
- **`walton_krabbe_relations` n'a aucun producteur** : `dung_arbitration_stage.py:123` l'accepte, `invoke_callables.py:8809` passe `context.get("walton_krabbe_relations")`, mais rien en production ne pose cette clé (seul `tests/.../test_dung_arbitration_wiring.py:45`). La docstring (`dung_arbitration_stage.py:144-145`) diffère le producteur à « PR2/PR3 » — **le module `debate` n'émet aucun `SpeechAct`** : l'import de production est un vocabulaire sans émetteur ;
- **`AGENT_PERSONALITIES.strengths` / `weaknesses` ne sont jamais lus** : `debate_definitions.py:90-131` porte 8 archétypes avec forces/faiblesses, mais les seules lectures sont `get_agent_capabilities` (`debate_agent.py:296`, qui liste les clés) et les tests. La personnalité n'entre dans la génération que comme nom en texte libre (`_create_enhanced_prompt` :510). « 8 personality archetypes with adaptive strategies » sur-décrit : les archétypes sont des données, l'adaptativité est générique ;
- **`knowledge_base.py` est résiduel** : `KnowledgeBase` (:15) n'a **aucun** importeur de production et n'est **pas** exporté — seuls `tests/.../debate/test_knowledge_base.py` et `test_debate.py:695` l'exercent ;
- **`build_debate_governance_loop_workflow` se déclare « STUB »** (`workflows.py:589`) tout en câblant une phase `adversarial_debate` réelle (:588) — `[inféré]` : la docstring et le code divergent sur l'état du workflow ;
- **Démo cassée côté consommateur** : `examples/03_integrations/demo_unified_capabilities.py:165` lit `quality["metrics"]` alors que le plugin renvoie un dict plat (`debate_agent.py:118-129`) ; le garde `if "metrics" in quality` (:164) est donc toujours faux et la démo n'affiche rien — le bug est dans le consommateur, pas dans le module.
