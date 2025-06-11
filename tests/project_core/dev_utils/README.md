# Tests des Utilitaires de Développement

## Objectif

Ce répertoire contient les tests pour les outils et utilitaires utilisés durant le cycle de développement. L'objectif principal est de garantir la fiabilité et la robustesse des scripts qui ne font pas partie du cœur de l'application, mais qui sont essentiels pour la préparation des données, la validation de la configuration et la maintenance du projet.

Ces tests s'assurent que les utilitaires de vérification fonctionnent comme attendu, notamment pour la validation des extraits de données qui sont une composante fondamentale pour l'entraînement et l'évaluation des modèles.

## Composants Testés

Les tests dans ce module se concentrent sur la validation des fonctions suivantes :

-   **`verify_extract`**: Valide un extrait de données individuel en vérifiant la présence de marqueurs de début et de fin, la longueur du texte extrait, et sa conformité avec un template prédéfini.
-   **`verify_all_extracts`**: Orchestre la vérification d'un ensemble complet de définitions d'extraits pour garantir l'intégrité d'une collection de données.
-   **`generate_verification_report`**: Génère un rapport de synthèse (HTML) qui résume les résultats de la vérification, facilitant ainsi le diagnostic des problèmes de données.

## Dépendances Clés

-   **`unittest.mock`**: Les tests s'appuient fortement sur les mocks pour simuler le comportement de fonctions externes comme le chargement de fichiers (`load_source_text`) ou l'extraction de texte (`extract_text_with_markers`). Cela permet d'isoler la logique de vérification et de la tester de manière unitaire et fiable.
