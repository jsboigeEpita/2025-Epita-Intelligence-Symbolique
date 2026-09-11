# `agents/concrete_agents/` — agent sophismes informels assemblé par plugins

## Rôle et frontière

Un seul module : `informal_fallacy_agent.py` (143 lignes) — `InformalFallacyAgent(BaseAgent)` (:23), assemble des plugins SK selon une config (`simple`, `explore_only`, `workflow_only`, `full` — portes :63, :67, :71). Sans `__init__.py`. Ce n'est **pas** l'analyseur informel du tronc commun : celui-ci vit dans [`agents/core/informal/`](../core/README.md) (`InformalAnalysisPlugin`, 8 familles) ; ce module est l'agent conversationnel factorisé pour l'usine.

## Composants publics

- `InformalFallacyAgent` (:23) — méthodes `__init__` :29, `_add_plugins_from_config` :51, `get_agent_capabilities` :90, `get_response` :99, `analyze_text` :102, `invoke_single` :113.

## Points d'entrée valides

1. **Web API** : `api/dependencies.py:217` → `services/web_api/services/analysis_service.py:205-207` — `create_agent(AgentType.INFORMAL_FALLACY, config_name="default_with_plugins")`.
2. **Hiérarchique** : `orchestration/hierarchical/operational/agent_registry.py:68` → `informal_agent_adapter.py:76-78` → `factory.create_informal_fallacy_agent` (`agents/factory.py:324-345`).
3. Démos : `examples/02_core_system_demos/.../demo_analyse_argumentation.py:61`, `examples/03_demos_overflow/validation/validation_complete_epita.py:351`.

## Amont / aval

- Amont : `BaseAgent` ([`core/abc/agent_bases.py`](../core/README.md), :11), `TaxonomyDisplayPlugin` ([`../plugins/`](../plugins/README.md) :12), `ComplexFallacyAnalyzer` :15-17, `INFORMAL_AGENT_INSTRUCTIONS` (:18-20), `plugins/fallacy_workflow_plugin` via importlib (:73-74).
- Aval : `AgentFactory` → web API, mode hiérarchique, démos.

## Statut d'intégration

**actif** — deux chaînes production mesurées (web API `analysis_service.py:205-207` ; hiérarchique `informal_agent_adapter.py:77`), instantié dans `agents/factory.py:328` via `create_agent` (:344-345, `AgentType.INFORMAL_FALLACY`).

## Artefacts et lecteurs

Aucun artefact produit. `TracedAgent` ([`../utils/`](../utils/README.md)) peut l'envelopper quand `trace_log_path` est fourni (`factory.py:327,336`).

## Tests représentatifs

```bash
conda run -n projet-is-roo-new --no-capture-output pytest tests/agents/factories/test_agent_factory.py -v
```

23 `def test_` dans le fichier factory (informal :108-151 ×4). ⚠ `tests/agents/concrete_agents/` contient 2 tests **placeholder `pass`** (`test_informal_fallacy_agent.py:19-21` « sera ajouté dans WO-06 », `test_project_manager_agent.py:7-9` — agent absent du répertoire) : la couverture réelle vit côté factory.

## Frères et parent

Parent : [`../README.md`](../README.md). Frère fonctionnel : [`../core/`](../core/README.md) (analyse informelle du tronc commun).

## Limites connues

- **config morte sur le chemin web API** : `analysis_service.py:206` passe `config_name="default_with_plugins"` qui ne matche **aucune** porte (:63/:67/:71 — valeurs valides : `simple`, `explore_only`, `workflow_only`, `full`) → l'agent servi par l'API n'a **aucun plugin** malgré le nom, et le log suivant dit « configured successfully » (anomalie signalée en issue séparée) ;
- `get_agent_capabilities` :93 annonce `FallacyIdPlugin` alors que le nom enregistré est `FallacyIdentificationPlugin` (:65) ;
- import dynamique silencieux :85-88 (log + continue) pour le plugin workflow.
