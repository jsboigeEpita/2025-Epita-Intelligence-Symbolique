# Agents Principaux
Parent : [`agents/README.md`](../README.md).

Ce répertoire contient les implémentations des agents principaux du système d'analyse d'argumentation.

## Structure

- `pm/` - Agent Project Manager, responsable de la coordination globale
- `informal/` - Agent d'Analyse Informelle, spécialisé dans l'analyse des arguments informels
- `pl/` - Agent de Logique Propositionnelle, spécialisé dans l'analyse formelle
- `extract/` - Agent d'Extraction, responsable de l'extraction des arguments depuis les textes

## Utilisation

Chaque agent est implémenté comme un module Python indépendant avec ses propres définitions et prompts.
Consultez les README.md spécifiques dans chaque sous-répertoire pour plus de détails sur l'utilisation de chaque agent.

## Organisation Standard

Chaque sous-répertoire d'agent suit une structure standard :

- `__init__.py` - Fichier d'initialisation du module
- `*_definitions.py` - Définitions des structures de données et fonctions de configuration
- `prompts.py` - Prompts utilisés pour les interactions avec les modèles de langage
- `*_agent.py` - Implémentation principale de l'agent
- `README.md` - Documentation spécifique à l'agent

## Intégration

Les agents de ce répertoire sont conçus pour fonctionner ensemble dans le cadre du système d'analyse d'argumentation.
Ils peuvent être utilisés individuellement pour des tâches spécifiques ou orchestrés ensemble pour une analyse complète.

## Enfants documentés

- [`abc/`](./abc/README.md)
- [`counter_argument/`](./counter_argument/README.md)
- [`debate/`](./debate/README.md)
- [`extract/`](./extract/README.md)
- [`governance/`](./governance/README.md)
- [`informal/`](./informal/README.md)
- [`logic/`](./logic/README.md)
- [`oracle/`](./oracle/README.md)
- [`pl/`](./pl/README.md)
- [`pm/`](./pm/README.md)
- [`political/`](./political/README.md)
- [`quality/`](./quality/README.md)
- [`synthesis/`](./synthesis/README.md)
