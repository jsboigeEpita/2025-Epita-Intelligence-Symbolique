# `agents/core/counter_argument/` — chaîne contre-argumentative (parse → vulnérabilités → stratégie → évaluation)

## Rôle et frontière

6 fichiers, 1 737 lignes (`__init__` 61, `counter_agent` 397, `evaluator` 437, `parser` 444, `strategies` 297, `definitions` 101). C'est **un axe d'analyse**, pas une couche de restitution : il consomme du texte argumentatif français et rend un contre-argument structuré, pesé sur 5 critères. La chaîne est : parse (prémisses / conclusion / type / confiance) → analyse de vulnérabilités → sélection de stratégie rhétorique → génération (kernel SK avec repli gabarit) → évaluation. Ce module est la version unifiée (#35) du projet étudiant `2.3.3-generation-contre-argument` ; le dossier racine éponyme reste le livrable d'origine, hors périmètre de lecture production.

## Composants publics

- `counter_agent.py` — `CounterArgumentPlugin` :47 (3 `@kernel_function` : `parse_argument` :59, `identify_vulnerabilities` :71, `suggest_strategy` :83) et `CounterArgumentAgent(BaseAgent)` :96 ; pipeline `invoke_single` :175, `generate_counter_argument` :195, `generate_multiple` :253 ; repli LLM→gabarit `_generate_content` :299 ;
- `definitions.py` — **deux enums à ne pas confondre** : `CounterArgumentType` :15 (5 valeurs : `DIRECT_REFUTATION`, `COUNTER_EXAMPLE`, `ALTERNATIVE_EXPLANATION`, `PREMISE_CHALLENGE`, `REDUCTIO_AD_ABSURDUM`) et `RhetoricalStrategy` :34 (5 valeurs : `SOCRATIC_QUESTIONING`, `REDUCTIO_AD_ABSURDUM`, `ANALOGICAL_COUNTER`, `AUTHORITY_APPEAL`, `STATISTICAL_EVIDENCE`) — les deux partagent la valeur `reductio_ad_absurdum` mais ce sont deux axes distincts (type d'attaque ≠ procédé rhétorique). Plus `ArgumentStrength` :25 (4 valeurs) et 5 dataclasses (`Argument` :44, `Vulnerability` :55, `CounterArgument` :66, `EvaluationResult` :80, `ValidationResult` :93) ;
- `evaluator.py` — `CounterArgumentEvaluator` :26 ; les 5 critères pondérés sont lus en :30-36 (`relevance` 0.25, `logical_strength` 0.25, `persuasiveness` 0.20, `originality` 0.15, `clarity` 0.15) ; entrée `evaluate` :69 ;
- `parser.py` — `ArgumentParser` :20 (`parse_argument` :55, `identify_vulnerabilities` :72), `VulnerabilityAnalyzer` :277 (`analyze_vulnerabilities` :315) ;
- `strategies.py` — `RhetoricalStrategies` :24 (`apply_strategy` :75, `suggest_strategy` :87, `get_best_strategy` :103).

`__init__.py` : `__all__` :25-40 exporte **14 noms** — les 14 ont été retrouvés dans les modules ci-dessus, zéro fantôme. Le module expose **en plus** `register_with_capability_registry` :43, hors `__all__`.

## Points d'entrée valides

1. **Registre Lego** — `orchestration/registry_setup.py:99-103` importe `register_with_capability_registry` (`__init__.py:43`) et l'appelle ; l'enregistrement déclare `capabilities=["counter_argument_generation"]` (`__init__.py:54`) et `setup_registry` câble aussitôt `invoke=_invoke_counter_argument` (:106-108) ;
2. **Phases workflow** — **13** littéraux production `capability="counter_argument_generation"` (comptés par `grep -rn 'capability="counter_argument_generation"' argumentation_analysis/`) : `orchestration/workflows.py` :157 (light workflow, phase `counter` **non optionnelle**), :219, :294, :468, :557, :915 ; `workflows/argument_strength.py:75`, `comprehensive_analysis.py:89`, `debate_tournament.py:74`, `democratech.py:101`, `fact_check_pipeline.py:59` ; `orchestration/router.py:409` (phase construite dynamiquement quand la capability est sélectionnée, `router.py:36`) ; `orchestration/sherlock_modern_orchestrator.py:483` ;
3. **Invoke callable** — `orchestration/invoke_callables.py:1148` `_invoke_counter_argument(input_text, context)` : instancie le plugin (:1156), appelle `parse_argument` puis `suggest_strategy` (:1157-1158), surcharge la stratégie via le sélecteur paramétrique `--counter-strategy` (:1163-1178), enrichit via LLM ; l'évaluateur tourne dans `_evaluate_counter_arguments` (:1351) ;
4. **Écriture d'état** — `orchestration/state_writers.py:2287` mappe `counter_argument_generation` → `_write_counter_argument_to_state` (:499) ;
5. **MCP** — `services/mcp_server/tools/specialized_tools.py:61` (`generate_counter_argument`) → `_invoke_by_capability("counter_argument_generation", …)` (:70) → `provider.invoke` = le callable du point 3 ;
6. **Démo** — `examples/03_integrations/demo_unified_capabilities.py:89` (instancie `CounterArgumentPlugin` en direct).

## Amont / aval

- Amont : texte brut (aucun état préalable requis pour le plugin). L'enrichissement LLM lit `context["phase_extract_output"]` et `context["phase_hierarchical_fallacy_output"]` (`invoke_callables.py:1197-1201`) ;
- Aval : `UnifiedAnalysisState` via `add_counter_argument` (`state_writers.py:499`), plus le verdict `validation` de forme `ValidationResult` consommé par la restitution (G6 #1180 — `act2_narrative_plugin.py:185`, `act3_conclusion_plugin.py:313`).

## Statut d'intégration

**actif** — 6 familles de points d'entrée production mesurées (registre, phases workflow, invoke callable, writer d'état, outil MCP, démo), 13 phases production, et la phase `counter` est non optionnelle dans le workflow le plus léger (`workflows.py:157`). La fonction de registre module-level est **conservée** ici (contrairement à `debate`/`governance`/`quality` dont la seconde surface a été supprimée par #1842) : `registry_setup` l'importe et l'appelle réellement — c'est la surface que garde `test_one_capability_surface_1842.py:86`.

## Artefacts et lecteurs

Aucun artefact persisté par le module lui-même : il rend des dataclasses/dicts. Lecteurs : `UnifiedAnalysisState` (état partagé), la restitution (verdict `validation`), le notebook `docs/coursia_contrib/counter_argument_quality.ipynb` — qui importe `definitions` et `evaluator` (`:65`) et **sans aucun appel LLM** (`:14`) rejoue l'évaluateur 5 critères.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/counter_argument/ -v
```

**502 `def test_`** sur 9 fichiers — comptés par `grep -rE '^\s*def test_'` dans `tests/unit/argumentation_analysis/agents/core/counter_argument/` (scope : ce dossier uniquement). Répartition : `test_parser.py` 95, `test_counter_argument_parser.py` 72, `test_evaluator_extended.py` 63, `test_strategies_extended.py` 57, `test_strategies.py` 56, `test_counter_argument_evaluator.py` 55, `test_evaluator.py` 46, `test_counter_argument.py` 42, `test_counter_argument_definitions.py` 16.

Tests croisés hors dossier : `orchestration/test_counter_argument_caps_gg.py` (ciblage par sophisme **et** par argument, plancher K2), `test_architecture_compliance.py:58,77` (le `CounterArgumentAgent` instancié), `agents/factories/test_agent_factory.py:255` (via la factory).

## Frères et parent

Parent : [`../`](../README.md) (`agents/core/`). Amont : [`../../abc/`](../../abc/) (`BaseAgent`, non documenté à ce jour), [`../../../orchestration/`](../../../orchestration/README.md) (registre + `_invoke_counter_argument`), [`../../../core/`](../../../core/README.md) (état partagé). Frères du même lot : `debate`, `governance`, `quality`, `oracle`, `synthesis`, `political`.

## Limites connues

- `CounterArgumentAgent` (le `BaseAgent`) **n'est jamais instancié en production** : le registre le déclare comme `agent_class` puis remplace immédiatement son `invoke` par `_invoke_counter_argument` (`registry_setup.py:106-108`) ; `AgentFactory.create_counter_argument_agent` (`factory.py:412`) n'a **aucun appelant production** (seulement `tests/agents/factories/test_agent_factory.py:255,273` et `tests/unit/argumentation_analysis/test_architecture_compliance.py:301`). Statut de la classe : **compatibilité** — elle porte le contrat `BaseAgent`/`ChatCompletionAgent` et les points d'extension `invoke_single`/`generate_multiple` (`counter_agent.py:175,253`), mais le chemin production passe par le plugin. `[inféré]` aucune bascule n'est câblée.
- `ValidationResult` (`definitions.py:93`) est **résiduel** : déclaré et exporté (`__init__.py:18`), jamais instancié — aucun `ValidationResult(` dans le dépôt. La production fabrique un **dict de même forme** (`invoke_callables.py:1297` `_build_counter_argument_validation`), dont le commentaire :1303-1308 documente explicitement le gap (G6 #1180 : le pont formel Dung du livrable étudiant a été perdu à l'unification #35). La dataclass est donc un vestige déclaré-mais-non-rempli.
- `parse_llm_response` (`parser.py:406`) et `parse_structured_text` (:414) sont **résiduels** : zéro appelant dans tout le dépôt (les homonymes de `services/nl_to_logic.py` sont des méthodes privées distinctes). Reliquats du parsing de réponses LLM du projet étudiant, rendus inutiles par le passage au kernel SK.
- `CounterArgumentPlugin.identify_vulnerabilities` (`counter_agent.py:71`) n'est pas appelé par le chemin production : `_invoke_counter_argument` n'invoque que `parse_argument` et `suggest_strategy` (`invoke_callables.py:1157-1158`). La détection de vulnérabilités reste atteignable en interne (`counter_agent.py:216,260`) et depuis la démo/tests, pas depuis le pipeline.
- Les contre-arguments statistiques sont un **gabarit placeholdé** assumé (`strategies.py:255-267`) : le générateur refuse d'inventer des chiffres. `[inféré]` un consommateur lisant `counter_content` doit donc traiter ce préfixe `[template/placeholder]` comme un signal de non-substantiation, pas comme une donnée.
