# Tests Unitaires pour les Pipelines d'Analyse

## Objectif

Ce répertoire contient les tests unitaires pour les pipelines de haut niveau qui orchestrent des séquences complètes d'analyse, de la prise en charge d'un texte brut à la génération de résultats structurés.

L'objectif est de valider la robustesse et la fiabilité de ces flux d'orchestration, en s'assurant que chaque étape (initialisation des services, analyse, agrégation, sauvegarde) est appelée correctement et que les erreurs sont gérées de manière appropriée.

## Fonctionnalités Testées

### `analysis_pipeline`

-   **Orchestration du Flux Principal (`run_text_analysis_pipeline`)** :
    -   **Séquencement** : Valide que le pipeline initialise d'abord les services nécessaires (`initialize_analysis_services`) avant de lancer l'analyse principale (`perform_text_analysis`).
    -   **Gestion des Échecs** :
        -   Teste le cas où l'initialisation des services échoue, ce qui doit empêcher le démarrage de l'analyse.
        -   Teste le cas où l'analyse elle-même échoue.
    -   **Gestion des Entrées** : S'assure que le pipeline gère correctement les entrées de texte vides, en s'arrêtant prématurément.
    -   **Retour des Résultats** : Vérifie que le pipeline retourne directement les résultats produits par l'étape d'analyse.

### `advanced_rhetoric`

-   **Orchestration de l'Analyse Avancée (`run_advanced_rhetoric_pipeline`)** :
    -   **Itération sur les Données** : Valide la capacité du pipeline à itérer sur une collection de définitions d'extraits et à lancer une analyse avancée pour chacun.
    -   **Intégration des Données** : Teste la prise en compte optionnelle de résultats d'analyse de base pour enrichir l'analyse avancée.
    -   **Agrégation et Sauvegarde** : Vérifie que les résultats de toutes les analyses individuelles sont collectés et sauvegardés dans un unique fichier JSON.
    -   **Gestion des Erreurs** : S'assure que l'échec de l'analyse d'un seul extrait n'arrête pas tout le pipeline, mais est enregistré comme une erreur pour cet extrait spécifique. Teste également la gestion des erreurs lors de la sauvegarde finale.

### `embedding_pipeline` et `reporting_pipeline`

-   Les fichiers de test pour ces pipelines (`test_embedding_pipeline.py`, `test_reporting_pipeline.py`) sont actuellement **commentés**. Ils contiennent des fixtures pour mocker les dépendances, mais les tests eux-mêmes sont désactivés. Cela suggère que ces pipelines ont subi une refonte et que les tests correspondants n'ont pas encore été mis à jour.

## Dépendances Clés

-   **`pytest`** : Utilisé comme framework de test, notamment avec `pytest-asyncio` pour les pipelines asynchrones.
-   **`unittest.mock`** : Essentiel pour ces tests d'orchestration. Les fonctions et pipelines de plus bas niveau (`initialize_analysis_services`, `perform_text_analysis`, `analyze_extract_advanced`, etc.) sont systématiquement mockés pour isoler la logique de l'orchestrateur testé.
-   Les interactions avec le système de fichiers (`open`, `json.dump`) et les bibliothèques externes (`tqdm`) sont également mockées pour permettre des tests rapides et déterministes.
