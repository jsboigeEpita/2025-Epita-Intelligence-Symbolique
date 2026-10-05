# `agents/core/debate/` — plugin de débat adversarial (agent multi-personnalités en compatibilité)

## Rôle et frontière

6 modules + `__init__` (1 588 lignes ; 7 modules / 1 809 l. avant les retraits #2137 : `knowledge_base.py`, les 3 classes de protocole, les champs `strengths`/`weaknesses`) — deux systèmes accolés lors de l'intégration du projet étudiant `1_2_7_argumentation_dialogique` : (1) un **débat adversarial à 8 personnalités** (génération d'arguments, scoring à 8 métriques, phases et modérateur), (2) un socle de **vocabulaire dialogique Walton-Krabbe** (6 types de dialogue, 9 actes de langage, 10 schémas d'argumentation). Frontière : le module produit une *évaluation adversariale* (scores, vainqueur, qualité honnête) et des *transcripts* ; il ne fait ni extraction, ni détection de sophismes, ni vote — il les consomme.

## Composants publics

- **Plugin — le seul chemin exercé en production** : `debate_agent.py`, `DebatePlugin`. Ses `def` décorés `@kernel_function` : `analyze_argument_quality`, `analyze_logical_structure`, `suggest_debate_strategy` — **3**. `grep -c '@kernel_function'` en rend **4** : la docstring de classe ouvre une ligne avec la chaîne (le piège d'over-count est réel ici) ;
- Scoring : `debate_scoring.py`, `ArgumentAnalyzer` (`analyze_argument`, 8 métriques pondérées → `_calculate_persuasiveness`) ;
- Structures : `debate_definitions.py` — `ArgumentType` (6 membres), `DebatePhase` (5), `ArgumentMetrics` (8 champs), `EnhancedArgument`, `DebateState`, `AGENT_PERSONALITIES` (**8** archétypes) ;
- Agent / modérateur : `debate_agent.py`, `DebateAgent(BaseAgent)`, alias `EnhancedArgumentationAgent`, `EnhancedDebateModerator` (utilitaire, pas un `BaseAgent`) ;
- Protocoles : `protocols.py` — `DialogueType` (**6**), `SpeechAct` (**9**), `Proposition`, `FormalArgument`, `DialogueMove`. Les classes `DialogueProtocol` / `InquiryProtocol` / `PersuasionProtocol` ont été **retirées (#2137)** — jumeaux morts du `dialogue_handler` JVM vivant ;
- Schémas : `argumentation_schemes.py` — `ArgumentationScheme`, `_load_argumentation_schemes` (**10** schémas, table verbatim du livrable étudiant), `classify_scheme` (matcher lexical déterministe, fail-loud), `schemes_as_prompt_context` ;
- Base de connaissances : `knowledge_base.py` **retiré (#2137)** — `KnowledgeBase` n'avait aucun importeur de production et n'était pas exporté.

`__init__.py` (66 l.) exporte **14** noms (`__all__`) — tous réels. **Non exportés** : `FormalArgument`, `DialogueMove`, `ArgumentationScheme`, `classify_scheme`.

## Points d'entrée valides

1. **Phases workflow** `capability="adversarial_debate"` : `orchestration/workflows.py` (`build_standard_workflow`), (`build_full_workflow`), (`build_iterative_analysis_workflow`), (`build_spectacular_workflow`), (`build_debate_governance_loop_workflow` — docstring « STUB ») ; `workflows/debate_tournament.py`, `workflows/democratech.py`, `workflows/comprehensive_analysis.py`, `workflows/belief_dynamics.py` ;
2. **Registre** : `orchestration/registry_setup.py` — `register_agent(name="debate_agent", agent_class=DebateAgent, capabilities=["adversarial_debate"], invoke=_invoke_debate_analysis)` ;
3. **Handler** : `await _invoke_debate_analysis(input_text: str, context: Dict[str, Any]) -> Dict[str, Any]` — `orchestration/invoke_callables.py` ; première instruction `plugin = DebatePlugin()`, puis `plugin.analyze_argument_quality(input_text)` ;
4. **Writer d'état** : `CAPABILITY_STATE_WRITERS["adversarial_debate"] = _write_debate_to_state` — `orchestration/state_writers.py`, définition ;
5. **API** : `api/proposal_endpoints.py` expose `debate_tournament` comme workflow sélectionnable (`api/proposal_models.py`) ;
6. **Appel direct du plugin** (hors DAG) : `scripts/capstone_brick_health.py` appelle `_invoke_debate_analysis(CORPUS_A, ctx)` ; `examples/03_integrations/demo_unified_capabilities.py`.

Signature réelle du plugin : `DebatePlugin().analyze_argument_quality(text: str) -> str` (`debate_agent.py`) — renvoie une **chaîne JSON à 8 clés plates** (`logical_coherence` … `readability_score`), **sans** enveloppe `metrics`.

## Amont / aval

- **Amont** (lu par `_invoke_debate_analysis`) : `phase_extract_output` (arguments), `phase_hierarchical_fallacy_output`, `phase_counter_output`, `phase_quality_output`, `phase_jtms_output`. Porte honnête : sans argument amont, branche dégradée explicite `debate_degraded=True` / `no_arguments_upstream` (« pas de verdict fabriqué ») ;
- **Aval** : `UnifiedAnalysisState.debate_transcripts` (`core/shared_state.py`, `add_debate_transcript`). Lecteurs : restitution `reporting/restitution/act2_narrative_plugin.py` (`_collect_debate`), CLI `cli/output_formatter.py` (`_render_debate`), synthèse profonde `agents/core/synthesis/deep_synthesis_agent.py` (champ citable), `core/state_manager_plugin.py`. `DebatePlugin` est aussi déclaré dans le registre de plugins de la factory (`agents/factory.py`).

## Statut d'intégration

**actif** (chemin plugin/scoring) · **compatibilité** (agent, modérateur, alias). Mesures :

- **capability** : 1 déclarée (`registry_setup.py`), **9** littéraux `add_phase(capability="adversarial_debate")` en production (comptage `grep -n` sur `argumentation_analysis/`, liste ci-dessus), plus le routeur (`orchestration/router.py`) et les harnais d'évaluation (`evaluation/run_iteration.py`, `evaluation/capability_eval.py`) ;
- **surface de capacité unique (#1842) : vérifiée** — `debate/__init__.py` est un **commentaire**, pas une fonction : `grep -n "register_with_capability_registry" argumentation_analysis/` ne trouve ici que ce commentaire (les seuls `def` restants sont `counter_argument/__init__.py`, câblé dans `registry_setup.py`, et un commentaire jumeau dans `governance/`, `quality/`, `synthesis/`). Garde `tests/unit/argumentation_analysis/orchestration/test_one_capability_surface_1842.py` → **8 passed** (mesuré) ; « câblé » y signifie : le module qui définit la fonction est celui que `registry_setup` importe, et la capability déclarée a un demandeur de production ;
- **`DebateAgent` (classe) n'est jamais instancié en production** — il n'occupe qu'un slot `agent_class=` (`registry_setup.py`) que le chemin d'invocation ne lit pas (`_invoke_debate_analysis` construit `DebatePlugin` directement). `grep -n "DebateAgent("` sur `argumentation_analysis/` → la seule occurrence est la définition `debate_agent.py` ; `AgentFactory.create_debate_agent` (`agents/factory.py`) n'a que des appelants de test. Donc `generate_argument`, `_adapt_strategy`, `_analyze_opponents`, `EnhancedDebateModerator.run_debate` sont **exercés par les tests seulement** : d'où **compatibilité** ;
- **`protocols.SpeechAct`** : plus **aucun importeur de production** — l'import vivant dans `dung_arbitration_stage.py` (`WALTON_KRABBE_ATTACKING_ACTS`) est parti avec le canal Walton-Krabbe (#1649 R1065) ; les importeurs restants sont les tests (`test_protocols.py`). Le vocabulaire (types/actes) reste commis pour la garde-bac à sable CoursIA. Les classes `DialogueProtocol`/`InquiryProtocol`/`PersuasionProtocol` n'avaient **aucun** appelant de production (le workflow `dialogue_protocols` passe par `agents/core/logic/dialogue_handler.py`, JVM/Tweety, pas par ce fichier) → **retirées (#2137)** ;
- **`argumentation_schemes.py`** : 2 points d'appel de production exécutés — `invoke_callables.py` (`schemes_as_prompt_context`, bloc de prompt) et `state_writers.py` (`classify_scheme`) — plus `neuro_symbolic_arbitrator.py` via le stage d'arbitrage → **actif** (voir toutefois la limite n°1 : l'effet du second est nul).

## Artefacts et lecteurs

Transcript `{"topic", "exchanges": [{"point", "rebuttal", "scheme"?, "scheme_key"?, "critical_question"?}], "winner"}` écrit dans `state.debate_transcripts` ; scores de phase `debate_quality` (entier 0-5 **ou `None`**) + `debate_quality_source` ∈ {`llm`, `heuristic`, `unscored`} — contrat honnête GE-5 #1467 (`invoke_callables.py` `_resolve_debate_quality`, commentaire) : `None` s'affiche « —/5 », jamais « 0/5 ». Lecteurs : restitution (Acte II), CLI, synthèse profonde, `api/agent_routes.py`.

## Tests représentatifs

```bash
conda run -n projet-is --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/debate/ -v
```

**149 `def test_`** sur 5 fichiers (209/6 avant les retraits #2137 ; comptage `grep -c 'def test_'` : test_debate.py 54, test_debate_scoring.py 35, test_debate_definitions.py 29, test_protocols.py 20, test_argumentation_schemes.py 11 — `test_knowledge_base.py` retiré). Tests croisés CoursIA : le roundtrip garde-bac à sable `tests/unit/coursia/dialogue_protocols/` ne couvre plus que la surface survivante (types/actes, jonction schémas, notebook avec sorties exécutées) ; celui de `knowledge_base` est retiré avec son sujet. Tests croisés hors répertoire : `agents/core/informal/test_dung_arbitration_stage.py`, `.../test_neuro_symbolic_arbitrator.py`, `orchestration/test_unified_pipeline.py` (mock du plugin), `test_value_gates.py`, `test_architecture_compliance.py`, `tests/agents/factories/test_agent_factory.py`, `tests/performance/test_integration_benchmarks.py`.

## Frères et parent

Parent : `agents/core/` ([`../README.md`](../README.md)). Frères : [`counter_argument/`](../counter_argument/README.md), [`governance/`](../governance/README.md), [`informal/`](../informal/README.md), [`quality/`](../quality/README.md), [`synthesis/`](../synthesis/README.md). Câblage : [`../../../orchestration/registry_setup.py`](../../../orchestration/registry_setup.py), [`../../../orchestration/invoke_callables.py`](../../../orchestration/invoke_callables.py). Origine : projet étudiant `1_2_7_argumentation_dialogique/` (racine du dépôt ; livrable source conservé en SANCTUAIRE read-only).

## Limites connues

- **Le grounding par schéma G8 (#1184) ne produit rien sur le chemin d'état — discordance de clés.** Le producteur (prompt LLM, `invoke_callables.py`) demande `agent_a_point` / `agent_b_rebuttal` ; le consommateur (`state_writers.py`) lit `point` / `rebuttal`. Conséquences mesurées : `entry["point"]`/`entry["rebuttal"]` sont **toujours vides** ; `classify_scheme(point or rebuttal)` reçoit `""` et renvoie `None` (`argumentation_schemes.py`) ; et `act2_narrative_plugin.py` (« fail-loud: skip empty exchanges ») écarte l'échange → **aucun échange de débat n'atteint l'Acte II**. `api/agent_routes.py` lit, lui, les bons noms : les deux chemins se contredisent. Le test doré (`tests/unit/argumentation_analysis/orchestration/test_regression_golden.py`) fabrique les clés du *writer* (`point`/`rebuttal`) et passe donc au-dessus de la brèche. Le scratch gitignoré `.cache/_g8_smoke.py` reproduit la même erreur — indice que le writer n'a jamais été confronté à la sortie réelle ;
- **`walton_krabbe_relations` — canal RETIRÉ (#1649 R1065)** : la décision #2137 de garder le lecteur est close — la mesure R1065 a établi que **le producteur n'a jamais existé** (`DebateAgent` émet des scores de qualité, pas des actes ; les classes porteuses d'actes étaient des jumeaux morts retirés par #2137 ; aucun writer de production de la clé). Le paramètre, sa policy, l'annotation et le read de contexte sont partis ensemble ; le stage arbitre sur la rivalité same-span seule. Le cas 5 restant de #1649 (l'`undercut` ASPIC comme candidat de prose) est hors de ce canal ;
- **`AGENT_PERSONALITIES.strengths` / `weaknesses` retirés (#2137)** : jamais lus — les seules lectures de `AGENT_PERSONALITIES` sont `get_agent_capabilities` (`debate_agent.py`, qui liste les noms) et les tests. La personnalité n'entre dans la génération que comme nom en texte libre (`_create_enhanced_prompt`). « 8 personality archetypes with adaptive strategies » sur-décrit : les archétypes sont des données, l'adaptativité est générique ;
- **`knowledge_base.py` retiré (#2137)** : `KnowledgeBase` n'avait **aucun** importeur de production et n'était **pas** exporté — seuls ses tests l'exerçaient. Les notebooks CoursIA `dialogue_protocols.ipynb` et `knowledge_base.ipynb` (docs/coursia_contrib/) restent commis avec leurs sorties exécutées comme artefacts d'enseignement, mais ne sont plus rejouables contre ce code ;
- **`build_debate_governance_loop_workflow` se déclare « STUB »** (`workflows.py`) tout en câblant une phase `adversarial_debate` réelle — `[inféré]` : la docstring et le code divergent sur l'état du workflow ;
- **Démo cassée côté consommateur** : `examples/03_integrations/demo_unified_capabilities.py` lit `quality["metrics"]` alors que le plugin renvoie un dict plat (`debate_agent.py`) ; le garde `if "metrics" in quality` est donc toujours faux et la démo n'affiche rien — le bug est dans le consommateur, pas dans le module.
