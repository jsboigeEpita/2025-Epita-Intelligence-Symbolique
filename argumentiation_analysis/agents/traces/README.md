# Traces d'Exécution

Ce répertoire contient les traces d'exécution des agents du système d'analyse d'argumentation.

## Structure

- `informal/` - Traces de l'agent d'Analyse Informelle
- `orchestration/` - Traces de l'orchestration des agents

## Objectif

Les traces d'exécution sont séparées du code pour plusieurs raisons:

1. **Clarté** - Elles permettent de garder le code propre et lisible
2. **Analyse** - Elles facilitent l'analyse des performances et du comportement des agents
3. **Débogage** - Elles sont utiles pour identifier et résoudre les problèmes
4. **Amélioration** - Elles fournissent des données pour améliorer les agents

## Format

Les traces sont stockées dans un format structuré qui permet de suivre l'exécution des agents étape par étape. Elles incluent:

- Les entrées reçues par les agents
- Les décisions prises par les agents
- Les sorties produites par les agents
- Les erreurs ou exceptions rencontrées

## Utilisation

Les traces peuvent être analysées manuellement ou automatiquement pour:

- Comprendre le comportement des agents
- Identifier des points d'amélioration
- Déboguer des problèmes
- Évaluer les performances

## Organisation des traces

Chaque agent dispose de son propre sous-répertoire pour stocker ses traces. Les traces sont généralement organisées par date et par session d'exécution, ce qui permet de suivre l'évolution des performances au fil du temps.

## Analyse des traces

Des outils d'analyse sont disponibles dans le répertoire `tools/analysis/` pour faciliter l'exploitation des traces. Ces outils permettent de :

- Extraire des statistiques sur les performances
- Visualiser le comportement des agents
- Comparer différentes versions des agents
- Identifier des motifs récurrents

## Bonnes pratiques

- Nettoyez régulièrement les traces obsolètes
- Utilisez un système de nommage cohérent
- Incluez des métadonnées utiles (date, version, configuration)
- Structurez les traces de manière à faciliter leur analyse automatique
