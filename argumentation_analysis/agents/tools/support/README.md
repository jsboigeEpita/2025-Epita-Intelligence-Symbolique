# `agents/tools/support/` — utilitaires transverses des analyseurs de sophismes

## Rôle et frontière

Un module : `shared_services.py` (64 lignes), sans `__init__.py` (seul enfant de `tools/` dans ce cas — `tools/__init__.py` et `tools/analysis/__init__.py` existent). Trois utilitaires transverses pour l'arbre [`tools/analysis/`](../analysis/README.md) :

- `get_configured_logger(name)` :5 — rend le logger nommé ; il ne configure plus le logger racine (#2346) ;
- `ServiceRegistry` :15 — cache singleton par classe (dict de niveau classe :18, `reset()` :28) ;
- `ConfigManager` :33 — cache de configuration avec callback de chargement (:36, `reset()` :62). Un chargeur qui rend `None` n'est pas mis en cache : l'appel suivant réessaie (#2346).

## Composants publics

Les trois ci-dessus. Stdlib uniquement (logging, typing) — zéro dépendance.

## Points d'entrée valides

Atteint via les analyseurs qui le consomment : `tools/analysis/complex_fallacy_analyzer.py:23`, `tools/analysis/contextual_fallacy_analyzer.py:20` (re-import lazy :404), `tools/analysis/fallacy_severity_evaluator.py:19`. Ces analyseurs sont montés par `informal_fallacy_agent.py:15-17` et `plugins/analysis_tools/plugin.py:16-18` → chaînes web API / hiérarchique / pipeline (cf. [`../../concrete_agents/README.md`](../../concrete_agents/README.md)).

## Amont / aval

- Amont : stdlib.
- Aval : les 3 analyseurs de `tools/analysis/` → `InformalFallacyAgent`, `AgentFactory`, plugin SK `analysis_tools`.

## Statut d'intégration

**actif** — 3 importeurs production directs dans le sous-arbre tools (mesuré). Un 4e référencement est commenté (`agents/core/orchestration_service.py:55`).

## Artefacts et lecteurs

Aucun.

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/unit/argumentation_analysis/agents/tools/test_fallacy_analyzers.py tests/unit/argumentation_analysis/agents/tools/support/test_shared_services.py -v
```

84 `def test_` dans le fichier analyzeurs (section dédiée shared_services dès :776) + fichier dédié `test_shared_services.py`.

## Frères et parent

Parent : [`../README.md`](../README.md) (outils). Frère : [`../analysis/`](../analysis/README.md) (les consommateurs). Frère documenté : [`../encryption/`](../encryption/README.md).

## Limites connues

- état global mutable de niveau classe, pour tout le processus. Les tests ne le partagent plus : la fixture `reset_shared_services` de `tests/conftest.py` appelle les deux `reset()` après chaque test (#2346) ;
- sans `__init__.py` — namespace implicite, découvert par le packaging (mesuré sur un cas analogue : [`../../../integrations/README.md`](../../../integrations/README.md)).
