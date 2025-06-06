# Tests Unitaires pour les Outils d'Analyse (Analytics)

## Objectif

Ce répertoire contient les tests unitaires pour les modules d'analyse statistique et textuelle. L'objectif est de valider les fonctions qui agrègent des données, calculent des métriques et orchestrent des analyses de plus haut niveau sur des corpus de textes.

Ces tests garantissent que les résultats chiffrés sont corrects et que les pipelines d'analyse de texte sont robustes et gèrent correctement les dépendances et les erreurs.

## Fonctionnalités Testées

### `stats_calculator`

-   **Calcul de Scores Moyens (`calculate_average_scores`)** :
    -   **Cas Nominal** : Vérification du calcul correct des moyennes pour plusieurs métriques numériques (ex: `confidence_score`, `richness_score`) à travers différents corpus.
    -   **Gestion des Données Manquantes** : Test du comportement avec des corpus vides ou des résultats ne contenant aucune donnée numérique pertinente. Le résultat attendu est un dictionnaire vide pour ces corpus.
    -   **Robustesse** : Validation de la capacité de la fonction à ignorer les champs non numériques et les éléments invalides (non-dictionnaires) au sein d'une liste de résultats, sans lever d'erreur.
    -   **Cas Limites** : Test avec des corpus ne contenant qu'un seul résultat.

### `text_analyzer`

-   **Orchestration de l'Analyse (`perform_text_analysis`)** :
    -   **Flux Nominal** : Test du scénario où l'analyse de texte est lancée avec succès. La fonction principale `run_analysis_conversation` est mockée pour confirmer qu'elle est bien appelée avec les bons paramètres (texte à analyser, service LLM).
    -   **Gestion des Dépendances** :
        -   Vérification qu'une erreur critique est journalisée si le service LLM (`llm_service`) est manquant dans les services fournis.
        -   L'analyse ne doit pas être tentée si cette dépendance clé est absente.
    -   **Gestion des Erreurs** :
        -   Test de la propagation correcte des exceptions (`Exception`, `ImportError`) qui pourraient être levées par la fonction d'analyse sous-jacente (`run_analysis_conversation`).
        -   Vérification que les erreurs sont correctement journalisées avant d'être propagées.

## Dépendances Clés

-   **`pytest`** : Utilisé comme framework de test, notamment avec des fixtures (`@pytest.fixture`) pour fournir des données de test cohérentes (échantillons de résultats, services mockés).
-   **`unittest.mock`** : Utilisé pour mocker les dépendances externes.
    -   Dans `test_text_analyzer`, `run_analysis_conversation` est systématiquement mocké avec `AsyncMock` pour simuler une fonction asynchrone et isoler le testeur du pipeline d'analyse complet.
-   **`logging` (via `caplog`)** : La fixture `caplog` de `pytest` est utilisée pour capturer les sorties de logs et vérifier que les messages d'information, d'erreur et critiques sont correctement émis par `perform_text_analysis`.
