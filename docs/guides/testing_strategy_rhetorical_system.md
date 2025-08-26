# Stratégie de Test pour le Système d'Analyse Rhétorique

## 1. Introduction

Ce document décrit l'approche de test initiée pour le "Système d'Analyse Rhétorique Unifié", conformément à la méthodologie SDDD. L'objectif est de construire une base de tests robuste qui sécurise le développement actuel et les refactorisations futures, notamment la migration vers une architecture hiérarchique.

## 2. Approche de Test

La stratégie repose sur une pyramide de tests classique, en commençant par la base : les tests unitaires.

### 2.1. Tests Unitaires

Les tests unitaires sont la fondation de la qualité du code. Leur but est de valider chaque composant de manière isolée.

*   **Framework**: `pytest` est utilisé pour sa simplicité et sa puissance.
*   **Localisation**: Les tests unitaires sont placés dans `tests/unit/`.
*   **Conventions**:
    *   Utilisation de `fixtures` pour fournir des objets de test réutilisables (ex: `rhetorical_state`).
    *   Les tests qui ne nécessitent pas la JVM (la majorité des tests `core`) sont marqués avec `@pytest.mark.no_jvm_session` pour accélérer l'exécution et éviter les conflits.
    *   Les fonctions de test asynchrones sont marquées avec `@pytest.mark.asyncio`.

### 2.2. Composants Ciblés en Priorité

L'analyse architecturale a identifié le `core` du système comme étant la zone la plus critique et la moins testée. Les premiers tests ont donc ciblé :

1.  **`RhetoricalAnalysisState` (`core/shared_state.py`)**: Valide la création et la manipulation de l'état partagé.
2.  **`StateManagerPlugin` (`core/state_manager_plugin.py`)**: S'assure que l'interface entre les agents et l'état fonctionne comme prévu.
3.  **Stratégies (`core/strategies.py`)**: Valide la logique de contrôle de flux de la conversation (`SimpleTerminationStrategy`, `BalancedParticipationStrategy`).

## 3. Comment étendre la couverture de test

Pour améliorer la robustesse du système, les prochaines étapes devraient se concentrer sur :

1.  **Tests d'Intégration**: Créer des tests qui simulent des conversations entre deux ou trois agents (mocks ou réels) pour valider leur interaction via le `StateManagerPlugin`.
2.  **Tests des Agents**: Écrire des tests unitaires pour la logique interne de chaque agent, en moquant leurs dépendances externes (comme les appels LLM).
3.  **Couverture des `Utils`**: Ajouter des tests pour les fonctions utilitaires critiques.
4.  **Métriques de Couverture**: Mettre en place un outil (ex: `pytest-cov`) pour mesurer le pourcentage de code couvert par les tests et identifier les zones non testées.
