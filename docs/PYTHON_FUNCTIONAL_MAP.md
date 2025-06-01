# Cartographie Fonctionnelle des Modules Python

Ce document fournit une vue d'ensemble des principaux modules et classes Python du projet, décrivant leur rôle et leur statut de stabilité.

## 1. Modules d'Analyse d'Argumentation (`argumentation_analysis/`)

Ce répertoire contient le cœur logique de l'analyse rhétorique et de la détection des sophismes.

*   **`argumentation_analysis/__init__.py`**
    *   **Rôle :** Initialisation du package, gestion des importations paresseuses pour optimiser le chargement des dépendances.
    *   **Statut :** Stable.
*   **`argumentation_analysis/main_orchestrator.py`**
    *   **Rôle :** Orchestre l'exécution complète de l'analyse rhétorique, intégrant divers agents et services. Gère la configuration du logging et le flux principal.
    *   **Statut :** Stable (testé avec mocks pour les services externes).
*   **`argumentation_analysis/paths.py`**
    *   **Rôle :** Gère les chemins de fichiers et de répertoires utilisés par l'application, assurant la création des structures de dossiers nécessaires.
    *   **Statut :** Stable.
*   **`argumentation_analysis/run_analysis.py`**
    *   **Rôle :** Point d'entrée pour l'exécution d'une analyse argumentative sur un contenu textuel donné. Inclut la configuration du logging et l'appel aux services d'analyse.
    *   **Statut :** Stable (testé avec mocks).
*   **`argumentation_analysis/run_extract_editor.py`**
    *   **Rôle :** Script pour lancer l'éditeur de marqueurs d'extraits.
    *   **Statut :** Stable.
*   **`argumentation_analysis/run_extract_repair.py`**
    *   **Rôle :** Script pour lancer la réparation des bornes défectueuses dans les extraits.
    *   **Statut :** Stable.
*   **`argumentation_analysis/run_orchestration.py`**
    *   **Rôle :** Gère l'orchestration des agents pour l'analyse de texte, y compris la configuration de l'environnement et l'exécution des agents.
    *   **Statut :** Stable (testé avec mocks).

## 2. Scripts Utilitaires (`scripts/`)

Ce répertoire contient divers scripts pour des tâches spécifiques, la maintenance, la génération de rapports et les tests.

*   **`scripts/advanced_rhetorical_analysis.py`**
    *   **Rôle :** Effectue une analyse rhétorique avancée, incluant le chargement des extraits, la comparaison avec des analyses de base et la génération de mocks pour les outils d'analyse.
    *   **Statut :** Stable (principalement testé avec mocks).
*   **`scripts/analyze_directory_usage.py`**
    *   **Rôle :** Analyse l'utilisation des répertoires et les références de fichiers.
    *   **Statut :** Stable.
*   **`scripts/check_encoding.py`**
    *   **Rôle :** Vérifie l'encodage des fichiers.
    *   **Statut :** Stable.
*   **`scripts/check_imports.py`**
    *   **Rôle :** Vérifie la validité des importations Python.
    *   **Statut :** Stable.
*   **`scripts/check_jpype_import.py`**
    *   **Rôle :** Script simple pour tester l'importation de JPype.
    *   **Statut :** Stable.
*   **`scripts/compare_rhetorical_agents_simple.py`**
    *   **Rôle :** Compare les performances de différents agents rhétoriques de manière simplifiée, génère des visualisations et des rapports.
    *   **Statut :** Stable.
*   **`scripts/compare_rhetorical_agents.py`**
    *   **Rôle :** Version plus complète de la comparaison des agents rhétoriques, incluant des métriques détaillées et des visualisations.
    *   **Statut :** Stable.
*   **`scripts/decrypt_extracts.py`**
    *   **Rôle :** Déchiffre et charge les définitions d'extraits, gère les clés de chiffrement.
    *   **Statut :** Stable.
*   **`scripts/demonstration_epita.py`**
    *   **Rôle :** Script de démonstration pour l'EPITA, incluant des tests unitaires, l'analyse de texte clair et chiffré, et la génération de rapports. Utilise des mocks pour les services non stables.
    *   **Statut :** Stable (pour la démonstration avec mocks).
*   **`scripts/download_test_jars.py`**
    *   **Rôle :** Télécharge les fichiers JAR nécessaires pour les tests.
    *   **Statut :** Stable.
*   **`scripts/embed_all_sources.py`**
    *   **Rôle :** Intègre toutes les sources dans le projet.
    *   **Statut :** Stable.
*   **`scripts/fix_project_structure.py`**
    *   **Rôle :** Corrige les problèmes de structure du projet.
    *   **Statut :** Stable.
*   **`scripts/generate_comprehensive_report.py`**
    *   **Rôle :** Génère un rapport complet à partir des résultats d'analyse, incluant des visualisations et des recommandations.
    *   **Statut :** Stable.
*   **`scripts/generate_coverage_report.py`**
    *   **Rôle :** Génère un rapport de couverture de code.
    *   **Statut :** Stable.
*   **`scripts/generate_rhetorical_analysis_summaries.py`**
    *   **Rôle :** Génère des résumés d'analyse rhétorique.
    *   **Statut :** Stable.
*   **`scripts/initialize_coverage_history.py`**
    *   **Rôle :** Initialise l'historique de couverture de code.
    *   **Statut :** Stable.
*   **`scripts/regenerate_encrypted_definitions.py`**
    *   **Rôle :** Régénère les définitions chiffrées.
    *   **Statut :** Stable.
*   **`scripts/run_full_python_analysis_workflow.py`**
    *   **Rôle :** Exécute un workflow d'analyse Python complet, incluant le chargement de corpus chiffré, l'analyse rhétorique avec des composants Python (potentiellement mockés comme `MockFallacyDetector`), et la génération de rapports JSON et Markdown. Conçu pour valider la chaîne d'outils Python de bout en bout.
    *   **Statut :** Stable (testé fonctionnellement avec `MockFallacyDetector`).
*   **`scripts/rhetorical_analysis_standalone.py`**
    *   **Rôle :** Version autonome de l'analyse rhétorique, utilisant des mocks pour les dépendances externes.
    *   **Statut :** Stable.
*   **`scripts/rhetorical_analysis.py`**
    *   **Rôle :** Script principal pour l'analyse rhétorique.
    *   **Statut :** Stable (avec gestion des mocks).
*   **`scripts/test_imports_after_reorg.py`**
    *   **Rôle :** Teste les importations après une réorganisation.
    *   **Statut :** Stable.
*   **`scripts/test_imports.py`**
    *   **Rôle :** Teste les importations.
    *   **Statut :** Stable.
*   **`scripts/test_rhetorical_analysis.py`**
    *   **Rôle :** Teste l'analyse rhétorique.
    *   **Statut :** Stable.
*   **`scripts/update_imports.py`**
    *   **Rôle :** Met à jour les importations dans les fichiers.
    *   **Statut :** Stable.
*   **`scripts/update_paths.py`**
    *   **Rôle :** Met à jour les chemins dans les fichiers.
    *   **Statut :** Stable.
*   **`scripts/verify_content_integrity.py`**
    *   **Rôle :** Vérifie l'intégrité du contenu des fichiers.
    *   **Statut :** Stable.
*   **`scripts/verify_files.py`**
    *   **Rôle :** Vérifie l'existence et la lisibilité des fichiers.
    *   **Statut :** Stable.
*   **`scripts/visualize_test_coverage.py`**
    *   **Rôle :** Visualise la couverture des tests.
    *   **Statut :** Stable.

## 3. Modules de Tests (`tests/`)

Ce répertoire contient les tests unitaires et d'intégration du projet.

*   **`tests/mocks/`**
    *   **Rôle :** Contient les implémentations des mocks pour les dépendances externes (JPype, bibliothèques scientifiques, etc.), permettant des tests isolés des composants Python.
    *   **Statut :** Stable et essentiel pour le développement.
*   **`tests/integration/`**
    *   **Rôle :** Contient les tests d'intégration. Notez que `tests/integration/jpype_tweety/` contient les tests qui nécessitent une JVM réelle et sont en cours de stabilisation.
    *   **Statut :** En développement (partiellement stable avec mocks, en cours de stabilisation pour l'intégration réelle).
*   **`tests/functional/test_python_analysis_workflow_components.py`**
    *   **Rôle :** Contient les tests fonctionnels pour les composants clés du workflow d'analyse Python, tels que la dérivation de clé, le chargement de corpus, et l'exécution de bout en bout du script `scripts/run_full_python_analysis_workflow.py`.
    *   **Statut :** Stable (couvre les aspects Python purs du workflow).

## 4. Autres Modules et Répertoires Clés

*   **`portable_jdk/`**
    *   **Rôle :** Contient la version portable du JDK 17 utilisée par le projet.
    *   **Statut :** Stable.
*   **`libs/`**
    *   **Rôle :** Contient les bibliothèques externes, notamment les JARs de Tweety (`libs/tweety_jars/`) nécessaires pour l'intégration Java.
    *   **Statut :** Stable (les JARs sont présents, l'intégration est en cours).
*   **`config/`**
    *   **Rôle :** Contient les fichiers de configuration du projet.
    *   **Statut :** Stable.
*   **`services/`**
    *   **Rôle :** Contient les définitions des services (LLM, Crypto, etc.).
    *   **Statut :** Stable (les interfaces sont définies, les implémentations peuvent varier).