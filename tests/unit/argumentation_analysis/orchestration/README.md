# Tests Unitaires pour l'Orchestration de l'Analyse

## Objectif

Ce répertoire contient les tests unitaires pour les modules chargés d'orchestrer des séquences d'analyse complexes. Ces orchestrateurs agissent comme des chefs d'orchestre, appelant différents outils d'analyse spécialisés dans un ordre logique pour produire un résultat agrégé et cohérent.

L'objectif est de valider la robustesse de ce flux d'orchestration, en s'assurant que les données circulent correctement entre les différents outils et que les erreurs sont gérées de manière appropriée sans interrompre l'ensemble du processus.

## Fonctionnalités Testées

### `advanced_analyzer`

-   **Orchestration du Flux d'Analyse (`analyze_extract_advanced`)** :
    -   **Séquencement des Appels** : Vérification que les différents outils d'analyse (sophismes complexes, analyse contextuelle, évaluation de la sévérité, résultats rhétoriques) sont appelés dans le bon ordre.
    -   **Agrégation des Résultats** : S'assure que les résultats de chaque outil sont correctement collectés et structurés dans un dictionnaire final.
    -   **Gestion des Données d'Entrée** :
        -   Teste le comportement lorsque des données optionnelles, comme un résultat d'analyse de base, sont fournies ou non.
        -   Valide la capacité à gérer des extraits de texte manquants en générant un texte d'exemple.
        -   Vérifie que le texte entier est utilisé si la segmentation en arguments échoue.
    -   **Gestion des Erreurs** : Teste la robustesse de l'orchestrateur lorsqu'un des outils d'analyse lève une exception. Le pipeline doit capturer l'erreur, l'enregistrer dans les résultats et continuer son exécution avec les autres outils.
    -   **Gestion des Outils Manquants** : Valide le comportement lorsque le dictionnaire d'outils fournis est vide ou incomplet.

## Dépendances Clés

-   **`pytest`** : Utilisé comme framework de test, avec des fixtures pour fournir des données de test standardisées (définitions d'extraits, résultats d'analyse de base).
-   **`unittest.mock`** : Essentiel pour ces tests, car tous les outils d'analyse sous-jacents sont des mocks.
    -   Une fixture `mock_tools` fournit un dictionnaire complet d'outils d'analyse simulés (`MockEnhancedComplexFallacyAnalyzer`, `MockEnhancedContextualFallacyAnalyzer`, etc.). Cela permet de tester l'orchestrateur de manière complètement isolée de la logique interne de chaque outil.
