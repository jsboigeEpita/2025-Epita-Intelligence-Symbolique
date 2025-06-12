# Analyse d'Argumentation

Ce répertoire contient le cœur du projet d'analyse d'argumentation. Il inclut les modèles, les pipelines de traitement, les agents et les orchestrateurs nécessaires pour analyser et évaluer des structures argumentatives.

## Organisation des répertoires

La structure de ce répertoire est la suivante :

-   **agents/** : Contient les agents intelligents qui exécutent des tâches spécifiques.
-   **analytics/** : Outils et scripts pour l'analyse des résultats.
-   **api/** : Points d'entrée de l'API pour l'intégration avec d'autres services.
-   **config/** : Fichiers de configuration pour les différents composants.
-   **core/** : Composants de base du système.
-   **data/** : Données utilisées pour l'entraînement, les tests et l'analyse.
-   **demos/** : Scripts de démonstration.
-   **docs/** : Documentation du projet.
-   **examples/** : Exemples d'utilisation des outils et des pipelines.
-   **execution\_traces/** : Traces d'exécution pour le débogage et l'analyse.
-   **integrations/** : Intégrations avec des services externes.
-   **mocks/** : Mocks pour les tests.
-   **models/** : Modèles d'apprentissage automatique pré-entraînés.
-   **nlp/** : Outils et bibliothèques pour le traitement du langage naturel.
-   **notebooks/** : Notebooks Jupyter pour l'expérimentation et l'analyse.
-   **orchestration/** : Orchéstrateurs qui coordonnent les différents composants.
-   **pipelines/** : Pipelines de traitement des données et d'analyse.
-   **plugins/** : Plugins pour étendre les fonctionnalités.
-   **reporting/** : Scripts pour générer des rapports.
-   **results/** : Résultats des analyses.
-   **scripts/** : Scripts utilitaires pour le projet.
-   **service\_setup/** : Scripts pour la configuration des services.
-   **services/** : Services externes utilisés par le projet.
-   **temp\_downloads/** : Téléchargements temporaires.
-   **tests/** : Tests unitaires et d'intégration.
-   **text\_cache/** : Cache pour les textes traités.
-   **ui/** : Interface utilisateur pour interagir avec le système.
-   **utils/** : Fonctions et classes utilitaires.

## Points d'Entrée Principaux

-   **`main_orchestrator.py`** : Le point d'entrée principal pour lancer l'orchestration complète de l'analyse d'argumentation. Il coordonne les pipelines, les agents et les modèles pour exécuter une analyse de bout en bout.
-   **`run_analysis.py`** : Lance une analyse spécifique en utilisant un pipeline ou un modèle particulier. Utile pour des exécutions ciblées.
-   **`run_orchestration.py`** : Exécute un scénario d'orchestration prédéfini. Permet de tester ou de lancer des workflows d'analyse complexes.