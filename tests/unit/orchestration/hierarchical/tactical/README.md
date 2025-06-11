# Tests Unitaires : Orchestration Tactique

## Objectif du Répertoire

Ce répertoire contient les tests unitaires pour le **niveau tactique** de l'architecture d'orchestration hiérarchique. Le rôle de ce niveau est de décomposer les objectifs stratégiques en tâches concrètes, de surveiller leur exécution et, surtout, de **détecter et résoudre les conflits** qui émergent des analyses produites par les agents opérationnels.

Les tests se concentrent sur deux composants principaux :
1.  `TacticalState` : La machine à états qui maintient une vue complète de la situation tactique.
2.  `ConflictResolver` : Le moteur logique qui identifie et tente de résoudre les incohérences entre les différents résultats d'analyse.

## Fonctionnalités Testées

### Gestion de l'État (`TacticalState`)

*   **Suivi Complet** : Vérification de la capacité de l'état à suivre les objectifs, les tâches (avec leurs statuts : en attente, en cours, terminées), les dépendances, les assignations d'agents, et les résultats intermédiaires.
*   **Gestion des Conflits** : Validation de l'enregistrement et de la mise à jour des conflits identifiés.
*   **Métrique et Journalisation** : Test du calcul des métriques de performance (ex: taux de complétion des tâches) et de la journalisation des actions tactiques.
*   **Persistance** : Capacité de l'état à être sérialisé en JSON et rechargé, assurant la sauvegarde et la restauration de la situation tactique.

### Résolution de Conflits (`ConflictResolver`)

*   **Détection de Conflits** :
    *   **Contradiction** : Identification d'analyses qui s'opposent directement (ex: un argument jugé valide et invalide par deux agents différents).
    *   **Chevauchement (Overlap)** : Détection d'arguments ou d'analyses qui traitent du même sujet, pouvant être redondants.
    *   **Incohérence et Ambiguïté** : Reconnaissance d'autres formes de conflits moins directs.
*   **Stratégies de Résolution Automatique** :
    *   **Basée sur la Confiance** : Choisir l'analyse ayant le score de confiance le plus élevé.
    *   **Fusion (Merge)** : Combiner des arguments qui se chevauchent en une seule entité plus complète.
    *   **Récence (Recency)** : Privilégier le résultat le plus récent en cas d'incohérence.
*   **Escalade** : Test du mécanisme qui identifie les conflits non résolus par les stratégies automatiques et les prépare à être remontés au niveau stratégique pour une décision finale.

## Dépendances Clés

*   **unittest.mock** : Essentiel pour simuler le `TacticalState` et tester le `ConflictResolver` de manière isolée.
*   Les composants `TacticalState` et `ConflictResolver` sont conçus pour fonctionner ensemble et sont donc testés en interaction (avec l'un des deux étant souvent un mock).

## Liste des Fichiers de Test

*   [`test_tactical_state.py`](test_tactical_state.py:1) : Valide l'ensemble des opérations de la machine à états tactique.
*   [`test_tactical_resolver.py`](test_tactical_resolver.py:1) : Teste les scénarios de base de détection et de résolution de conflits.
*   [`test_tactical_resolver_advanced.py`](test_tactical_resolver_advanced.py:1) : Couvre des scénarios plus complexes, notamment le mécanisme d'escalade des conflits non résolus.
