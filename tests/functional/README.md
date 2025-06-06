# Tests Fonctionnels

## Objectif

Ce répertoire contient les tests fonctionnels du projet. Contrairement aux tests unitaires qui valident des composants isolés, les tests fonctionnels ont pour but de vérifier des **workflows complets** et des **scénarios d'utilisation de haut niveau**.

Ils simulent des interactions entre plusieurs composants du système pour s'assurer que les fonctionnalités clés opèrent comme attendu de bout en bout. Ces tests utilisent fréquemment des **mocks** pour simuler les dépendances externes (comme les appels à des LLM) afin de garantir des résultats déterministes et de se concentrer sur la logique du workflow.

## Workflows Utilisateur Testés

Les principaux workflows couverts par ces tests sont :

1.  **Workflow de Collaboration Hiérarchique (`test_agent_collaboration_workflow.py`)**
    *   **Description :** Simule une analyse argumentative complète orchestrée par une hiérarchie d'agents (Stratégique, Tactique, Opérationnel).
    *   **Scénario :**
        1.  Définition d'un objectif stratégique (ex: analyser un texte).
        2.  Décomposition de l'objectif en tâches tactiques.
        3.  Assignation et exécution des tâches par des agents opérationnels (mockés).
        4.  Suivi de la progression et génération de rapports.
    *   **Prérequis :** Aucun. L'environnement est entièrement simulé.

2.  **Workflow de Détection de Sophismes (`test_fallacy_detection_workflow.py`)**
    *   **Description :** Valide le pipeline d'identification et d'évaluation des sophismes dans un texte.
    *   **Scénario :**
        1.  Analyse contextuelle d'un texte pour une première détection.
        2.  Analyse complexe pour identifier des structures de sophismes combinées.
        3.  Évaluation de la gravité de chaque sophisme détecté.
    *   **Prérequis :** Aucun. Les analyseurs sont testés de manière séquentielle avec des données en mémoire.

3.  **Workflow d'Analyse via Script Python (`test_python_analysis_workflow_components.py`)**
    *   **Description :** Teste les composants d'un script (`run_full_python_analysis_workflow.py`) qui orchestre le déchiffrement d'un corpus, son analyse par un agent, et la génération de rapports.
    *   **Scénario :**
        1.  Vérification des fonctions de déchiffrement de données.
        2.  Test de l'exécution du script complet en tant que processus externe.
        3.  Validation des rapports (JSON, Markdown) générés par le script.
    *   **Prérequis :**
        *   Le fichier de corpus chiffré `tests/extract_sources_with_full_text.enc` doit être présent.
        *   Les dépendances de cryptographie doivent être installées.

4.  **Workflow d'Analyse Rhétorique (`test_rhetorical_analysis_workflow.py`)**
    *   **Description :** Simule le processus complet d'analyse rhétorique sur un ou plusieurs documents, orchestré par `RhetoricalAnalysisRunner`.
    *   **Scénario :**
        1.  Extraction du contenu d'un fichier source.
        2.  Analyse du texte par un agent (mocké) pour identifier des sophismes.
        3.  Génération d'un rapport d'analyse au format JSON.
    *   **Prérequis :** Les fichiers d'exemples (ex: `examples/exemple_sophisme.txt`) doivent être présents.

5.  **Démonstration d'Enquête Cluedo (`test_cluedo_demo.py`)**
    *   **Description :** Teste un dialogue entre deux agents (Sherlock et Watson) dans le cadre d'une enquête de Cluedo.
    *   **Scénario :** Simule une conversation où les agents échangent des hypothèses pour résoudre un mystère.
    *   **Note :** Ce test est actuellement **désactivé** (`@pytest.mark.skip`) en raison de problèmes techniques non résolus.
    *   **Prérequis :** Aucun. Les appels LLM sont mockés.

## Prérequis de Lancement

En général, les tests de ce répertoire sont conçus pour être autonomes. Les prérequis principaux sont :

*   **Installation des dépendances :** Assurez-vous que toutes les dépendances listées dans `requirements.txt` sont installées.
*   **Présence des fichiers de test :** Certains tests dépendent de fichiers de données ou d'exemples spécifiques (voir la description de chaque workflow).
*   **Exécution via Pytest :** Les tests sont conçus pour être lancés avec `pytest` depuis la racine du projet.