# `orchestration/operational/` — exécuteur séquentiel « Pipeline 1 » (orphelin)

## Rôle et frontière

Un seul composant actif : `DirectOperationalExecutor` (`direct_executor.py:20`) — exécuteur séquentiel surnommé « Pipeline 1 » (docstring :22). Son constructeur (:26-41) monte 4 agents sur un kernel Semantic Kernel (`ExtractAgent`, `InformalAnalysisAgent`, `PropositionalLogicAgent`, `SynthesisAgent`). La méthode publique `execute_operational_pipeline` (:47-83) enchaîne extraction → analyse informelle → analyse logique (avec bifurcation `chat_history` → `invoke_single`, :167-179) → synthèse (`unify_results`, :217-221).

N'est **pas** la couche opérationnelle du mode hierarchical — celle-ci est [`orchestration/hierarchical/operational/`](../hierarchical/operational/README.md) (documentée : manager, adapters, agent_registry, state). Grep `DirectOperationalExecutor` : zéro hit dans `hierarchical/`. La seule source qui les associe est `docs/architecture/architecture_map.md:40`, avec l'adverbe « probablement » — le couplage n'existe pas en code.

## Composants publics

- `DirectOperationalExecutor` (:20) — voir Rôle ;
- `execute_operational_pipeline` (:47) — la méthode d'entrée, **jamais appelée** (1 seul hit grep sur tout le dépôt suivi = sa définition).

## Points d'entrée valides

**Aucun.** Référents dans l'arbre git suivi : sa définition, son test in-source, deux documents (`architecture_map.md:40`, inventaire #2088). Pas dans `orchestration/registry_setup.py` (grep 0 hit), ni instancié par `hierarchy_bridge`/`workflow_dsl`. Les seules autres mentions textuelles vivent dans un résidu de worktree non suivi (`.claude/worktrees/…`) et le `__pycache__` de l'arbre mort #2055 `orchestration/engine/` — hors arbre suivi.

## Amont / aval

- Amont : les 4 agents (`agents/core/extract`, `informal`, `pl`, `synthesis`), Semantic Kernel.
- Aval : aucun.

## Statut d'intégration

**résiduel** — orphelin de production : aucune route, aucun workflow, aucune phase Lego ne l'appelle. Sa méthode publique n'a aucun appelant.

## Artefacts et lecteurs

Aucune écriture disque. Effet de bord d'import : `logging.basicConfig(level=logging.INFO)` au niveau module (`direct_executor.py:16`) reconfigure le root logger de tout process qui importe le module.

## Tests représentatifs

`test_conversation_history.py` — 1 test (`test_execute_logic_agent_with_chat_history` :11), **non collecté** par la suite standard (`pytest.ini:2` `testpaths = tests`) : il mocke le constructeur (:29-32) et vérifie que `chat_history` route vers `invoke_single` et non `text_to_belief_set` (:49-52). C'est l'artefact du fix `8f576b476` (2025-06-24, « bug chat_history ignoré »), jamais rapatrié dans `tests/`.

```bash
conda run -n projet-is-roo-new --no-capture-output pytest argumentation_analysis/orchestration/operational/test_conversation_history.py -v
```

## Frères et parent

Parent : [`../README.md`](../README.md) — couvre les approches engine + hierarchical ; ne mentionne ni `operational/`, ni `plugins/`, ni le mode Cluedo. Frère documenté : l'arbre [`hierarchical/`](../hierarchical/README.md).

## Limites connues

- `logging.basicConfig` module-level (:16) — effet de bord global d'import ;
- test de régression du fix chat_history hors de la suite collectée — invisible en CI ;
- `architecture_map.md:40` présente l'exécuteur comme intégré au « Niveau Opérationnel » — infirmé par grep.
