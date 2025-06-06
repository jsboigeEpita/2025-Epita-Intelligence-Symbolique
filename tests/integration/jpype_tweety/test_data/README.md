# Données de Test pour l'Intégration JPype/Tweety

## Objectif

Ce répertoire contient un ensemble de fichiers de données utilisés par les tests d'intégration situés dans le répertoire parent, `tests/integration/jpype_tweety`. Ces fichiers servent d'entrées pour valider le bon fonctionnement de l'intégration entre JPype et la bibliothèque Tweety, notamment pour les opérations de raisonnement logique.

## Contenu des Fichiers

Les fichiers présents dans ce répertoire représentent diverses formes de connaissances logiques :

*   **Fichiers `.lp` (Logic Program) :** Contiennent des théories et des requêtes en programmation logique avec ensembles réponses (ASP - Answer Set Programming). Ils sont utilisés pour tester les capacités de raisonnement non monotone.
    *   `sample_theory.lp` (situé dans le répertoire parent `jpype_tweety`)
    *   `sample_theory_advanced.lp`
    *   `asp_queries.lp`
    *   `simple_asp_consistent.lp`
*   **Fichiers `.pl` (Prolog) :** Contiennent des programmes en logique probabiliste (Problog).
    *   `simple_problog.pl`

## Prérequis et Dépendances

Ces fichiers ne sont pas exécutables directement. Ils sont chargés et utilisés par les scripts de test Python (`.py`) dans le répertoire `tests/integration/jpype_tweety`. Pour que les tests fonctionnent, ces fichiers de données doivent être présents et accessibles.