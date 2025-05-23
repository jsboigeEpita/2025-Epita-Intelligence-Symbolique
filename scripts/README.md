# Scripts Utilitaires du Projet

Ce répertoire contient divers scripts Python et PowerShell pour faciliter le développement, la maintenance, l'exécution et la validation du projet d'analyse argumentative.

## Organisation des Scripts

Les scripts sont organisés en sous-dossiers thématiques :

-   **[`cleanup/`](./cleanup/README.md)** : Scripts pour nettoyer le projet, supprimer les fichiers obsolètes et gérer la configuration du dépôt.
-   **[`execution/`](./execution/README.md)** : Scripts principaux pour exécuter des fonctionnalités clés du système, comme la réparation ou la vérification des extraits.
-   **[`reports/`](./reports/README.md)** : Scripts liés à la génération ou à la mise à jour de rapports (par exemple, rapports de couverture).
-   **[`setup/`](./setup/README.md)** : Scripts pour configurer l'environnement de développement, gérer les dépendances (notamment JPype et les outils de compilation).
-   **[`testing/`](./testing/README.md)** : Scripts spécifiques pour des scénarios de test ou des simulations.
-   **[`utils/`](./utils/README.md)** : Petits scripts utilitaires pour des tâches de maintenance ponctuelles sur les fichiers du code source (encodage, indentation, syntaxe).
-   **[`validation/`](./validation/README.md)** : Scripts pour valider la structure du projet, les fichiers Markdown, ou d'autres aspects de la qualité.

## Scripts Principaux à la Racine de `scripts/`

En plus des sous-dossiers, quelques scripts importants résident directement à la racine de `scripts/` :

-   **`analyze_directory_usage.py`**: Analyse l'utilisation de certains répertoires dans le code.
-   **`check_encoding.py`**: Vérifie l'encodage des fichiers.
-   **`check_imports.py`**: S'assure que toutes les importations Python fonctionnent correctement.
-   **`compare_rhetorical_agents.py` / `compare_rhetorical_agents_simple.py`**: Scripts pour comparer les performances ou les résultats de différents agents rhétoriques.
-   **`decrypt_extracts.py`**: Utilitaire pour déchiffrer les extraits (à utiliser avec précaution).
-   **`download_test_jars.py`**: Télécharge les JARs minimaux nécessaires pour les tests.
-   **`fix_project_structure.py`**: Ancien script principal de restructuration (peut contenir des logiques utiles mais à utiliser avec prudence sur la structure actuelle).
-   **`generate_comprehensive_report.py`**: Génère un rapport d'analyse complet.
-   **`generate_coverage_report.py`**: Génère un rapport de couverture de tests.
-   **`generate_rhetorical_analysis_summaries.py`**: Crée des résumés à partir des analyses rhétoriques.
-   **`initialize_coverage_history.py`**: Initialise l'historique pour le suivi de la couverture des tests.
-   **`rhetorical_analysis.py` / `rhetorical_analysis_standalone.py`**: Scripts pour lancer des analyses rhétoriques.
-   **`script_commits.ps1`**: Script PowerShell pour aider à la gestion des commits.
-   **`test_imports.py` / `test_imports_after_reorg.py`**: Scripts pour tester les importations Python.
-   **`test_rhetorical_analysis.py`**: Script pour tester les fonctionnalités d'analyse rhétorique.
-   **`update_imports.py` / `update_paths.py`**: Anciens scripts de restructuration pour mettre à jour les importations et les chemins (à utiliser avec prudence).
-   **`verify_content_integrity.py` / `verify_files.py`**: Scripts pour vérifier l'intégrité des fichiers ou du contenu.
-   **`visualize_test_coverage.py`**: Génère des visualisations pour la couverture des tests.

## Utilisation

Pour chaque sous-dossier et pour de nombreux scripts individuels, un `README.md` spécifique détaille leur fonction et leur mode d'emploi.
De manière générale, les scripts Python s'exécutent avec `python scripts/chemin/vers/script.py [options]` et les scripts PowerShell avec `.\scripts\chemin\vers\script.ps1 [options]`.

Il est recommandé de se référer au README spécifique du script ou du sous-dossier avant toute utilisation.