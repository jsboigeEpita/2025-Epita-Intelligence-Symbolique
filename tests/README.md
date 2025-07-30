# Stratégie de Test du Projet

Ce document décrit l'organisation et les conventions de la suite de tests automatisés pour ce projet.

## Objectif de la Structure de Test

La structure de test vise à fournir un filet de sécurité robuste pour garantir la qualité, la stabilité et la non-régression du code base. Elle est conçue pour être claire, maintenable et pour refléter l'architecture du code source (`src/`).

## Niveaux de Test

La suite est divisée en deux niveaux principaux de tests, chacun avec un objectif spécifique :

### `tests/unit`

*   **Objectif :** Tester des unités de code isolées (fonctions, classes, méthodes) de manière indépendante.
*   **Caractéristiques :**
    *   Rapides à exécuter.
    *   N'ont pas de dépendances externes (pas d'accès réseau, base de données, système de fichiers, etc.). Les dépendances sont remplacées par des "mocks" ou des "stubs".
    *   Permettent de valider la logique métier d'un composant spécifique.

### `tests/integration`

*   **Objectif :** Tester l'interaction entre plusieurs composants pour s'assurer qu'ils fonctionnent correctement ensemble.
*   **Caractéristiques :**
    *   Plus lents que les tests unitaires.
    *   Peuvent avoir des dépendances externes contrôlées (par exemple, une base de données de test en mémoire).
    *   Valident des flux de travail ou des "use cases" qui traversent plusieurs parties du système.

## Exécution des Tests

Pour exécuter la suite de tests complète, utilisez la commande suivante à la racine du projet :

```bash
pytest
```

## Conventions de Nommage

Pour que `pytest` découvre automatiquement les tests, les conventions suivantes doivent être respectées :

*   **Fichiers de test :** Doivent être nommés en suivant le pattern `test_*.py` (par exemple, `test_plugin_loader.py`).
*   **Fonctions de test :** Doivent être nommées en suivant le pattern `test_*` (par exemple, `test_plugin_loader_can_be_imported`).