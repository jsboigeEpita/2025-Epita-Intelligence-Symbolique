# Tests Unitaires pour l'Extraction d'Arguments

## Objectif

Ce répertoire contient les tests unitaires pour les composants centraux de l'extraction d'arguments. L'objectif est de garantir la fiabilité, la robustesse et la précision des mécanismes chargés d'identifier et d'extraire des portions de texte spécifiques (arguments, prémisses, conclusions) sur la base de définitions sémantiques.

Les tests couvrent deux domaines principaux :

1.  **L'agent d'extraction (`ExtractAgent`)** : Valider la logique de l'agent qui orchestre le processus d'extraction, de la recherche dans des textes volumineux à la validation des résultats.
2.  **Les définitions et structures de données (`ExtractDefinition`, `ExtractResult`, `ExtractAgentPlugin`)** : Assurer que les objets de données utilisés pour définir les extractions et stocker leurs résultats sont cohérents et fonctionnels.

## Fonctionnalités Testées

### `ExtractAgent`

-   **Extraction nominale** : Vérification du flux d'extraction complet dans des conditions idéales, incluant l'appel au modèle sémantique et la validation du résultat.
-   **Gestion des textes volumineux** : Test de la capacité de l'agent à traiter de grands volumes de texte en utilisant des stratégies de segmentation et de recherche dichotomique.
-   **Gestion des erreurs** :
    -   Scénarios où le modèle de langage retourne une réponse mal formée (non-JSON), déclenchant les mécanismes de réparation.
    -   Gestion des exceptions levées par les dépendances (comme le `Kernel` de Semantic Kernel).
-   **Réparation des extraits** : Test de la capacité de l'agent à relancer une extraction lorsque les marqueurs de délimitation (`start_marker`, `end_marker`) d'un extrait existant sont invalides.
-   **Mise à jour et ajout d'extraits** : Validation des fonctions utilitaires pour la manipulation des définitions d'extraction après une opération réussie ou échouée.

### `ExtractDefinition`, `ExtractResult` et `ExtractAgentPlugin`

-   **Initialisation et sérialisation** : Test de la création des objets de données et de leur conversion vers et depuis des dictionnaires Python (`to_dict`, `from_dict`), y compris la gestion des champs manquants.
-   **Utilitaires de recherche (`ExtractAgentPlugin`)** :
    -   `find_similar_markers` : Validation de la recherche de marqueurs textuels similaires.
    -   `search_text_dichotomically` : Test de l'algorithme de recherche dichotomique pour localiser rapidement un terme dans un grand texte.
    -   `extract_blocks` : Vérification de la segmentation de texte en blocs avec chevauchement.

## Dépendances Clés

-   **`unittest.mock`** : Utilisé intensivement pour mocker les dépendances externes et isoler les composants testés. Les `MagicMock` et `AsyncMock` sont essentiels pour simuler le comportement du `Kernel` de Semantic Kernel et des fonctions asynchrones.
-   **`semantic_kernel`** : Les tests simulent les interactions avec le `Kernel` et ses composants (`FunctionResult`, `ChatCompletionClientBase`), sans nécessiter une véritable instance du kernel ou un appel à un LLM.
-   **Fonctions utilitaires locales** : Des fonctions comme `load_source_text` et `extract_text_with_markers` sont mockées pour contrôler les entrées et sorties des tests de l'agent.
