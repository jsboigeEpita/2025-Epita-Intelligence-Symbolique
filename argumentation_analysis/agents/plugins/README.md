# `agents/plugins/` — deux plugins SK : affichage taxonomie et gestion projet

## Rôle et frontière

`__init__.py` vide (0 octet — marqueur de package seul). Deux plugins, deux destins :

- `taxonomy_display_plugin.py` (11 lignes) — `TaxonomyDisplayPlugin` (:4), corps `pass` :11. Classe-marqueur : la fonctionnalité vit dans les prompts SK auto-chargés (`agents/prompts/TaxonomyDisplayPlugin/DisplayBranch/{config.json,skprompt.txt}` — répertoire vérifié existant).
- `project_management_plugin.py` (50 lignes) — `AnalysisReport(BaseModel)` :7, `ProjectPlan(BaseModel)` :14, `ProjectManagementPlugin` :22 avec 2 `@kernel_function` : `create_project_plan` :25-29, `generate_analysis_report` :38-42.

## Composants publics

Les trois classes ci-dessus. Aucun export `__init__` (vide).

## Points d'entrée valides

- `TaxonomyDisplayPlugin` : instancié dans `informal_fallacy_agent.py:68-70` — **uniquement** pour `config_name ∈ {explore_only, workflow_only, full}` (le chemin web API passe une config qui ne matche aucune porte, cf. [`../concrete_agents/README.md`](../concrete_agents/README.md)) ;
- `ProjectManagementPlugin` : instancié uniquement dans `agents/factory.py:368` (`create_project_manager_agent` :365), dont les appelants production sont **zéro** (grep plein dépôt : seuls les tests `tests/agents/factories/test_agent_factory.py:325,341`).

## Amont / aval

- Amont : `pydantic.BaseModel`, `@kernel_function` (SK), `BaseAgent` pour le consommateur.
- Aval : `InformalFallacyAgent` (taxonomie) ; personne pour PM (hors tests).

## Statut d'intégration

**mixte** — `TaxonomyDisplayPlugin` **actif-cheminé** (via l'agent informel, configs exploration/workflow/full ; testé `tests/integration/triage/test_fallacy_agent_workflow.py:208` paramétré ×4 :192-207) ; `ProjectManagementPlugin` **résiduel** (fabrique test-only, zéro appelant production). Sort à trancher par le coordinateur.

## Artefacts et lecteurs

Prompts SK : `agents/prompts/TaxonomyDisplayPlugin/` (consommés par le mécanisme prompt-dir de SK — câblage non vérifié ici), `agents/prompts/ProjectManagerAgent/skprompt.txt` (lu par `factory.py:370-373`).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/integration/triage/test_fallacy_agent_workflow.py tests/agents/factories/test_agent_factory.py -v
```

(1 test ×4 configs + 23 tests factory.)

## Frères et parent

Parent : [`../README.md`](../README.md). Consommateur : [`../concrete_agents/`](../concrete_agents/README.md). Ne pas confondre avec `argumentation_analysis/plugins/` (plugins du tronc commun — fallacy, quality, governance — décrits dans le [`README racine`](../../README.md), sans README propre).

## Limites connues

- import mort : `agents/factory.py:18` importe `TaxonomyDisplayPlugin` sans jamais l'utiliser dans ce fichier (seule ligne du grep) ;
- `TaxonomyDisplayPlugin` est un `pass` nu — tout repose sur le chargement de prompts SK, aucun garde ne vérifie que le répertoire de prompts est enregistré ;
- en-tête fossile du test workflow : `test_fallacy_agent_workflow.py:1` annonce `tests/integration/...` alors que le chemin réel est `tests/integration/triage/`.
