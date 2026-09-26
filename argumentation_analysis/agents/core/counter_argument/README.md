# `agents/core/counter_argument/` — chaîne contre-argumentative (parse → vulnérabilités → stratégie → évaluation)

## Rôle et frontière

6 fichiers, 1 698 lignes (`__init__` 59, `counter_agent` 397, `evaluator` 437, `parser` 407, `strategies` 297, `definitions` 95 ; avant #2137 : 1 737 — retraits `ValidationResult` + 2 fonctions parser). C'est **un axe d'analyse**, pas une couche de restitution : il consomme du texte argumentatif français et rend un contre-argument structuré, pesé sur 5 critères. La chaîne est : parse (prémisses / conclusion / type / confiance) → analyse de vulnérabilités → sélection de stratégie rhétorique → génération (kernel SK avec repli gabarit) → évaluation. Ce module est la version unifiée (#35) du projet étudiant `2.3.3-generation-contre-argument` ; le dossier racine éponyme reste le livrable d'origine, hors périmètre de lecture production.

## Composants publics

- `counter_agent.py` — `CounterArgumentPlugin` (3 `@kernel_function` : `parse_argument`, `identify_vulnerabilities`, `suggest_strategy`) et `CounterArgumentAgent(BaseAgent)` ; pipeline `invoke_single`, `generate_counter_argument`, `generate_multiple` ; repli LLM→gabarit `_generate_content` ;
- `definitions.py` — **deux enums à ne pas confondre** : `CounterArgumentType` (5 valeurs : `DIRECT_REFUTATION`, `COUNTER_EXAMPLE`, `ALTERNATIVE_EXPLANATION`, `PREMISE_CHALLENGE`, `REDUCTIO_AD_ABSURDUM`) et `RhetoricalStrategy` (5 valeurs : `SOCRATIC_QUESTIONING`, `REDUCTIO_AD_ABSURDUM`, `ANALOGICAL_COUNTER`, `AUTHORITY_APPEAL`, `STATISTICAL_EVIDENCE`) — les deux partagent la valeur `reductio_ad_absurdum` mais ce sont deux axes distincts (type d'attaque ≠ procédé rhétorique). Plus `ArgumentStrength` (4 valeurs) et 4 dataclasses (`Argument`, `Vulnerability`, `CounterArgument`, `EvaluationResult`) ; `ValidationResult` a été retiré (#2137) — jamais instancié, le verdict production est le dict de même forme (`_build_counter_argument_validation`) ;
- `evaluator.py` — `CounterArgumentEvaluator` ; les 5 critères pondérés sont lus en (`relevance` 0.25, `logical_strength` 0.25, `persuasiveness` 0.20, `originality` 0.15, `clarity` 0.15) ; entrée `evaluate` ;
- `parser.py` — `ArgumentParser` (`parse_argument`, `identify_vulnerabilities`), `VulnerabilityAnalyzer` (`analyze_vulnerabilities`) ;
- `strategies.py` — `RhetoricalStrategies` (`apply_strategy`, `suggest_strategy`, `get_best_strategy`).

`__init__.py` : `__all__` exporte **13 noms** (14 avant le retrait de `ValidationResult`, #2137) — tous retrouvés dans les modules ci-dessus, zéro fantôme. Le module expose **en plus** `register_with_capability_registry`, hors `__all__`.

## Points d'entrée valides

1. **Registre Lego** — `orchestration/registry_setup.py` importe `register_with_capability_registry` (`__init__.py`) et l'appelle ; l'enregistrement déclare `capabilities=["counter_argument_generation"]` (`__init__.py`) et `setup_registry` câble aussitôt `invoke=_invoke_counter_argument` ;
2. **Phases workflow** — **13** littéraux production `capability="counter_argument_generation"` (comptés par `grep -rn 'capability="counter_argument_generation"' argumentation_analysis/`) : `orchestration/workflows.py` (light workflow, phase `counter` **non optionnelle**) ; `workflows/argument_strength.py`, `comprehensive_analysis.py`, `debate_tournament.py`, `democratech.py`, `fact_check_pipeline.py` ; `orchestration/router.py` (phase construite dynamiquement quand la capability est sélectionnée, `router.py`) ; `orchestration/sherlock_modern_orchestrator.py` ;
3. **Invoke callable** — `orchestration/invoke_callables.py` `_invoke_counter_argument(input_text, context)` : instancie le plugin, appelle `parse_argument` puis `suggest_strategy`, surcharge la stratégie via le sélecteur paramétrique `--counter-strategy`, enrichit via LLM ; l'évaluateur tourne dans `_evaluate_counter_arguments` ;
4. **Écriture d'état** — `orchestration/state_writers.py` mappe `counter_argument_generation` → `_write_counter_argument_to_state` ;
5. **MCP** — `services/mcp_server/tools/specialized_tools.py` (`generate_counter_argument`) → `_invoke_by_capability("counter_argument_generation", …)` → `provider.invoke` = le callable du point 3 ;
6. **Démo** — `examples/03_integrations/demo_unified_capabilities.py` (instancie `CounterArgumentPlugin` en direct).

## Amont / aval

- Amont : texte brut (aucun état préalable requis pour le plugin). L'enrichissement LLM lit `context["phase_extract_output"]` et `context["phase_hierarchical_fallacy_output"]` (`invoke_callables.py`) ;
- Aval : `UnifiedAnalysisState` via `add_counter_argument` (`state_writers.py`), plus le verdict `validation` — un **dict** de la forme de l'ex-dataclass `ValidationResult` (retirée #2137) — consommé par la restitution (G6 #1180 — `act2_narrative_plugin.py`, `act3_conclusion_plugin.py`).

## Statut d'intégration

**actif** — 6 familles de points d'entrée production mesurées (registre, phases workflow, invoke callable, writer d'état, outil MCP, démo), 13 phases production, et la phase `counter` est non optionnelle dans le workflow le plus léger (`workflows.py`). La fonction de registre module-level est **conservée** ici (contrairement à `debate`/`governance`/`quality` dont la seconde surface a été supprimée par #1842) : `registry_setup` l'importe et l'appelle réellement — c'est la surface que garde `test_one_capability_surface_1842.py`.

## Artefacts et lecteurs

Aucun artefact persisté par le module lui-même : il rend des dataclasses/dicts. Lecteurs : `UnifiedAnalysisState` (état partagé), la restitution (verdict `validation`), le notebook `docs/coursia_contrib/counter_argument_quality.ipynb` — qui importe `definitions` et `evaluator` et **sans aucun appel LLM** rejoue l'évaluateur 5 critères.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/core/counter_argument/ -v
```

**474 `def test_`** sur 9 fichiers — comptés par `grep -rE '^\s*def test_'` dans `tests/unit/argumentation_analysis/agents/core/counter_argument/` (scope : ce dossier uniquement ; 502 avant les retraits #2137). Répartition : `test_parser.py` 84, `test_counter_argument_parser.py` 61, `test_evaluator_extended.py` 63, `test_strategies_extended.py` 57, `test_strategies.py` 56, `test_counter_argument_evaluator.py` 55, `test_evaluator.py` 46, `test_counter_argument.py` 39, `test_counter_argument_definitions.py` 13.

Tests croisés hors dossier : `orchestration/test_counter_argument_caps_gg.py` (ciblage par sophisme **et** par argument, plancher K2), `test_architecture_compliance.py` (le `CounterArgumentAgent` instancié), `agents/factories/test_agent_factory.py` (via la factory).

## Frères et parent

Parent : [`../`](../README.md) (`agents/core/`). Amont : [`../abc/`](../abc/README.md) (`BaseAgent`), [`../../../orchestration/`](../../../orchestration/README.md) (registre + `_invoke_counter_argument`), [`../../../core/`](../../../core/README.md) (état partagé). Frères du même lot : `debate`, `governance`, `quality`, `oracle`, `synthesis`, `political`.

## Limites connues

- `CounterArgumentAgent` (le `BaseAgent`) **n'est jamais instancié en production** : le registre le déclare comme `agent_class` puis remplace immédiatement son `invoke` par `_invoke_counter_argument` (`registry_setup.py`) ; `AgentFactory.create_counter_argument_agent` (`factory.py`) n'a **aucun appelant production** (seulement `tests/agents/factories/test_agent_factory.py` et `tests/unit/argumentation_analysis/test_architecture_compliance.py`). Statut de la classe : **compatibilité** — elle porte le contrat `BaseAgent`/`ChatCompletionAgent` et les points d'extension `invoke_single`/`generate_multiple` (`counter_agent.py`), mais le chemin production passe par le plugin. `[inféré]` aucune bascule n'est câblée.
- `ValidationResult` (`definitions.py`) **retiré (#2137)** : déclaré et exporté mais jamais instancié — aucun `ValidationResult(` dans le dépôt. La production fabrique un **dict de même forme** (`invoke_callables.py` `_build_counter_argument_validation`), dont le commentaire documente explicitement le gap (G6 #1180 : le pont formel Dung du livrable étudiant a été perdu à l'unification #35). #1180 étant clos sur le dict comme contrat livré, la dataclass vestige est partie avec ses tests.
- `parse_llm_response` et `parse_structured_text` (`parser.py`) **retirés (#2137)** : zéro appelant dans tout le dépôt (les homonymes de `services/nl_to_logic.py` sont des méthodes privées distinctes). Reliquats du parsing de réponses LLM du projet étudiant, rendus inutiles par le passage au kernel SK.
- `CounterArgumentPlugin.identify_vulnerabilities` (`counter_agent.py`) n'est pas appelé par le chemin production : `_invoke_counter_argument` n'invoque que `parse_argument` et `suggest_strategy` (`invoke_callables.py`). La détection de vulnérabilités reste atteignable en interne (`counter_agent.py`) et depuis la démo/tests, pas depuis le pipeline.
- Les contre-arguments statistiques sont un **gabarit placeholdé** assumé (`strategies.py`) : le générateur refuse d'inventer des chiffres. `[inféré]` un consommateur lisant `counter_content` doit donc traiter ce préfixe `[template/placeholder]` comme un signal de non-substantiation, pas comme une donnée.
