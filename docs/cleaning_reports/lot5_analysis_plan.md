# Lot 5 - Plan d'Analyse et de Nettoyage des Tests

Date: 2025-06-02

## Objectif

Ce document détaille le plan d'analyse et les actions prévues pour le Lot 5 du projet de nettoyage et de valorisation de la base de tests. Ce lot se concentre sur les tests restants des outils d'analyse des agents et commence l'exploration des tests fonctionnels et d'orchestration.

## Fichiers de Test à Traiter

1.  `tests/agents/tools/test_rhetorical_tools_integration.py`
2.  `tests/agents/tools/test_rhetorical_tools_performance.py`
3.  `tests/agents/tools/test_semantic_argument_analyzer.py`
4.  `tests/agents/tools/test_semantic_fallacy_detector.py`
5.  `tests/agents/tools/test_sentence_encoder.py`
6.  `tests/functional/test_agent_collaboration_workflow.py`
7.  `tests/functional/test_fallacy_detection_workflow.py`
8.  `tests/functional/test_python_analysis_workflow_components.py`
9.  `tests/functional/test_rhetorical_analysis_workflow.py`
10. `tests/orchestration/hierarchical/operational/adapters/test_extract_agent_adapter.py`

## Méthodologie Générale (pour chaque fichier applicable)

1.  **Activation de l'Environnement et Synchronisation :** Utilisation du script `activate_project_env.ps1` pour toutes les opérations Git et Python, sur la branche `main` et synchronisée.
2.  **Analyse et Actions :**
    *   **a. Organisation des Tests :** Vérification de l'emplacement, du nom, et de la cohérence. Renommage/déplacement si pertinent.
    *   **b. Documentation du Répertoire de Test :** Création/mise à jour du `README.md` parent.
    *   **c. Extraction de Composants Réutilisables :** Identification et proposition d'extraction de fixtures/helpers.
    *   **d. Documentation des Composants Source :** Documentation des nouveaux composants extraits.
    *   **e. Enrichissement de la Documentation Croisée :** Identification de liens vers la documentation projet.
3.  **Commits et Push :** Commits atomiques et push réguliers via le script wrapper.

## Plan Détaillé par Fichier (Initial)

*   **`tests/agents/tools/test_rhetorical_tools_integration.py`**:
    *   Vérifier l'existence (potentiellement sous `tests/integration/`).
    *   Analyser le contenu pour les points 2.a à 2.e.
*   **`tests/agents/tools/test_rhetorical_tools_performance.py`**:
    *   Vérifier l'existence. Si absent, le noter.
    *   Sinon, analyser pour les points 2.a à 2.e.
*   **`tests/agents/tools/test_semantic_argument_analyzer.py`**:
    *   Vérifier l'existence. Si absent, le noter.
    *   Sinon, analyser pour les points 2.a à 2.e.
*   **`tests/agents/tools/test_semantic_fallacy_detector.py`**:
    *   Vérifier l'existence et la pertinence. Si absent ou non pertinent, le noter.
    *   Sinon, analyser pour les points 2.a à 2.e.
*   **`tests/agents/tools/test_sentence_encoder.py`**:
    *   Vérifier l'existence et la pertinence. Si absent ou non pertinent, le noter.
    *   Sinon, analyser pour les points 2.a à 2.e.
*   **`tests/functional/test_agent_collaboration_workflow.py`**:
    *   Analyser le contenu pour les points 2.a à 2.e. Créer `tests/functional/README.md` si besoin.
*   **`tests/functional/test_fallacy_detection_workflow.py`**:
    *   Analyser le contenu pour les points 2.a à 2.e. Mettre à jour `tests/functional/README.md`.
*   **`tests/functional/test_python_analysis_workflow_components.py`**:
    *   Analyser le contenu pour les points 2.a à 2.e. Mettre à jour `tests/functional/README.md`.
*   **`tests/functional/test_rhetorical_analysis_workflow.py`**:
    *   Analyser le contenu pour les points 2.a à 2.e. Mettre à jour `tests/functional/README.md`.
*   **`tests/orchestration/hierarchical/operational/adapters/test_extract_agent_adapter.py`**:
    *   Analyser le contenu pour les points 2.a à 2.e. Créer `tests/orchestration/hierarchical/operational/adapters/README.md` si besoin.

Ce plan sera ajusté au fur et à mesure de la découverte et de l'analyse des fichiers.