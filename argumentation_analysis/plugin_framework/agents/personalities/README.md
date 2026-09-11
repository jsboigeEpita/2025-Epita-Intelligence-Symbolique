# `plugin_framework/agents/personalities/` — coquille vide

## Rôle et frontière

Emplacement **réservé mais jamais rempli** pour les personnalités d'agents du framework de plugins. Le contenu intégral du répertoire est un `__init__.py` de 0 octet (aucun module n'a jamais existé : `__pycache__/` ne contient que le bytecode de `__init__`).

Ce répertoire n'est **pas** le lieu des personnalités de débat du système :

- les 8 personnalités (`AGENT_PERSONALITIES`) vivent dans `argumentation_analysis/agents/core/debate/debate_agent.py:296` ;
- le prototype étudiant a les siennes dans `2.1.6_multiagent_governance_prototype/cli.py:91`.

Aucun match grep « personalities » du dépôt ne désigne ce package.

## Composants publics

Aucun. Le `__init__.py` est vide (0 octet, lecture vérifiée).

## Points d'entrée valides

Aucun. Grep `plugin_framework.agents.personalities` sur tout le dépôt (production et tests) : **0 importeur**.

## Amont / aval

Vide des deux côtés : rien n'importe ce package, il n'importe rien.

## Statut d'intégration

**résiduel** — créé vide dans l'arborescence d'origine `src/` (commit `13787c3e0`, « feat: regularize and integrate benchmarking framework »), migré tel quel dans `argumentation_analysis/` par le nettoyage du trop-plein racine #34 (commit `738bf4f2f`), jamais rempli depuis, jamais importé.

## Artefacts et lecteurs

Aucun artefact, aucun lecteur.

## Tests représentatifs

Aucun test ne couvre ce répertoire. Le plus proche est `tests/unit/argumentation_analysis/test_plugin_framework.py::TestAgentLoader` (:1005), qui teste `agents/agent_loader.py` — un autre mécanisme que cette coquille.

## Frères et parent

- Parent : [`agents/README.md`](../README.md) — documente le mécanisme AgentLoader/manifest ; ne mentionne pas `personalities/`.
- Frère : `agents/simple_analyst/` — un manifeste seul (`agent_manifest.json`), sans README.

## Limites connues

Répertoire vide maintenu en vie sans consommateur ni plan documenté. Anomalie connexe du frère : `agents/simple_analyst/agent_manifest.json` déclare `"entry_point": "agent.py"` alors qu'aucun `agent.py` n'existe dans le répertoire (seul le manifeste y vit) — signalée en issue séparée.
