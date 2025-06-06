# Tests Unitaires pour les Outils d'Analyse d'Arguments

## Objectif

Ce répertoire contient les tests unitaires pour les outils d'analyse avancée des sophismes. Ces outils vont au-delà de la simple détection pour identifier des structures argumentatives complexes et évaluer la pertinence des sophismes en fonction du contexte.

L'objectif est de garantir que les analyseurs peuvent non seulement identifier des sophismes isolés, mais aussi comprendre comment ils interagissent entre eux et comment leur signification change en fonction du domaine discursif.

## Fonctionnalités Testées

### `ComplexFallacyAnalyzer`

-   **Identification de Sophismes Combinés** :
    -   Test de la capacité à détecter des combinaisons prédéfinies de sophismes (ex: "Appel à l'autorité" + "Appel à la popularité").
    -   Validation du calcul de la sévérité aggravée pour ces combinaisons.

-   **Analyse de Sophismes Structurels** :
    -   **Contradictions** : Test de la détection de contradictions logiques entre plusieurs arguments.
    -   **Arguments Circulaires** : Test de l'identification de raisonnements où la conclusion est déjà supposée dans les prémisses.

-   **Identification de Motifs (Patterns)** :
    -   **Alternance** : Test de la détection de l'alternance régulière entre deux types de sophismes (ex: autorité/émotion/autorité/émotion).
    -   **Escalade** : Test de l'identification d'une séquence de sophismes dont l'intensité ou l'agressivité augmente au fil du texte.

### `ContextualFallacyAnalyzer`

-   **Chargement de la Taxonomie** : Validation du chargement et de la préparation de la taxonomie des sophismes, qui sert de base de connaissances.

-   **Analyse Contextuelle** :
    -   **Détermination du Contexte** : Test de la capacité à classifier un texte dans une catégorie contextuelle (ex: "politique", "scientifique", "commercial").
    -   **Identification de Sophismes Potentiels** : Validation de la détection initiale de sophismes basée sur des mots-clés et des expressions.
    -   **Filtrage par Contexte** : Test du mécanisme qui ajuste le score de confiance et la pertinence d'un sophisme potentiel en fonction du contexte. Par exemple, un "Appel à l'autorité" est plus pertinent dans un contexte scientifique que dans un débat général.

## Dépendances Clés

-   **`unittest.mock`** : Massivement utilisé pour isoler les analyseurs de leurs dépendances.
    -   Le `ContextualFallacyAnalyzer` et le `FallacySeverityEvaluator` sont mockés lors du test du `ComplexFallacyAnalyzer`.
    -   Le chargement de la taxonomie depuis le système de fichiers (`pandas.read_csv`, `get_taxonomy_path`) est mocké pour les tests du `ContextualFallacyAnalyzer`.
-   **Données de Configuration** : Les tests du `ComplexFallacyAnalyzer` reposent sur des dictionnaires internes définissant les combinaisons de sophismes, les sophismes structurels et les motifs, qui sont chargés au moment de l'initialisation.
