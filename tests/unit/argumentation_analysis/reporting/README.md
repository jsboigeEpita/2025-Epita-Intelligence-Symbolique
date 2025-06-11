# Tests Unitaires pour la Génération de Rapports

## Objectif

Ce répertoire contient les tests unitaires pour les modules responsables de la génération de synthèses et de rapports d'analyse. L'objectif est de valider le pipeline qui agrège les résultats de multiples analyses rhétoriques simulées et produit des documents de synthèse cohérents.

## Fonctionnalités Testées

### `summary_generator`

-   **Orchestration de la Génération de Rapports (`run_summary_generation_pipeline`)** :
    -   **Itération Combinatoire** : Valide que le pipeline itère correctement sur toutes les combinaisons possibles de sources de données, d'extraits, et d'agents d'analyse rhétorique pour générer une analyse pour chaque cas.
    -   **Séquencement des Appels** : Vérifie que pour chaque combinaison, les fonctions de génération sont appelées dans le bon ordre :
        1.  `generate_rhetorical_analysis_for_extract` (pour produire les données d'analyse brutes).
        2.  `generate_markdown_summary_for_analysis` (pour créer un rapport individuel en Markdown).
    -   **Agrégation et Rapport Global** : S'assure que tous les résultats d'analyse individuels sont collectés et passés à `generate_global_summary_report` pour créer une synthèse globale.
    -   **Sauvegarde des Résultats** : Valide que la collection complète des données d'analyse brutes est sauvegardée dans un unique fichier JSON.
    -   **Gestion des Cas Vides** : Teste le comportement du pipeline lorsque les listes d'entrée (sources, agents) sont vides, en s'assurant qu'il s'exécute sans erreur et produit des résultats vides.

## Dépendances Clés

-   **`pytest`** : Utilisé comme framework de test, avec des fixtures pour fournir des données d'entrée complexes (listes de sources, d'agents, etc.).
-   **`unittest.mock`** : Essentiel pour ces tests d'orchestration. Toutes les fonctions de génération de contenu (`generate_rhetorical_analysis_for_extract`, `generate_markdown_summary_for_analysis`, `generate_global_summary_report`) sont mockées pour isoler la logique du pipeline de la logique de génération de rapports elle-même.
-   Les interactions avec le système de fichiers (`open`, `json.dump`) sont également mockées pour tester la sauvegarde des résultats sans écrire de fichiers réels.
