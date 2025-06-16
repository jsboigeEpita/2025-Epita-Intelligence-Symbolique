# Tests des Agents

Ce répertoire contient tous les tests relatifs aux agents du système d'analyse d'argumentation. Les agents sont les acteurs principaux du système, responsables de l'exécution de tâches spécifiques de raisonnement et d'analyse.

## Objectif

L'objectif global de ces tests est de s'assurer que chaque agent, qu'il soit fondamental ou spécialisé, fonctionne comme prévu. Cela inclut la validation de leur logique interne, de leurs interactions avec les outils et services, et de leur robustesse.

## Sous-répertoires

- **[`core/`](core/README.md)**: Contient les tests pour les agents fondamentaux, qui sont les briques de base du système. Cela inclut les agents pour l'analyse informelle, la logique formelle et la gestion de projet.

- **[`tools/`](tools/README.md)**: Contient les tests pour les outils que les agents peuvent utiliser. Ces tests valident les composants d'analyse qui peuvent être invoqués par les agents.

## Approche de Test

L'approche de test pour les agents est principalement unitaire et axée sur l'isolation. Chaque agent est testé indépendamment de ses dépendances réelles en utilisant des mocks, ce qui permet de vérifier sa logique interne de manière ciblée.