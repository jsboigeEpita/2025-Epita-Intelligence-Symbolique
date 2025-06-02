# Tests d'Orchestration Tactique

Ce répertoire regroupe les tests unitaires et d'intégration pour les composants d'orchestration tactique, incluant les coordinateurs et les moniteurs tactiques. Ces tests visent à assurer la robustesse et la fiabilité de la logique de coordination des agents et de la surveillance de l'état du système à un niveau tactique.

## Objectifs des Tests :

*   Valider le comportement nominal des coordinateurs tactiques dans la gestion des plans et des tâches des agents.
*   Tester les fonctionnalités avancées des coordinateurs, telles que la résolution de conflits, la replanification et l'adaptation dynamique.
*   Assurer une couverture de code adéquate pour les modules des coordinateurs.
*   Vérifier le fonctionnement des moniteurs tactiques dans la détection d'événements pertinents et la mise à jour de l'état tactique.
*   Tester les capacités avancées des moniteurs, y compris l'agrégation d'informations et le déclenchement d'alertes ou d'actions.

## Fichiers Inclus :

*   [`test_tactical_coordinator_advanced.py`](test_tactical_coordinator_advanced.py:1): Tests pour les fonctionnalités avancées du coordinateur tactique.
*   [`test_tactical_coordinator_coverage.py`](test_tactical_coordinator_coverage.py:1): Tests visant à maximiser la couverture de code du coordinateur tactique.
*   [`test_tactical_coordinator.py`](test_tactical_coordinator.py:1): Tests de base pour le coordinateur tactique.
*   [`test_tactical_monitor_advanced.py`](test_tactical_monitor_advanced.py:1): Tests pour les fonctionnalités avancées du moniteur tactique.
*   [`test_tactical_monitor.py`](test_tactical_monitor.py:1): Tests de base pour le moniteur tactique.

Ces tests sont essentiels pour garantir que la couche d'orchestration tactique fonctionne comme prévu et peut gérer de manière fiable les interactions complexes entre les agents et l'environnement.