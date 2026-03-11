# Cartographie de l'infrastructure de test

## 1. Vue d'ensemble

Le projet utilise une approche de test hybride, combinant le framework `pytest` pour sa flexibilité et ses fonctionnalités avancées (fixtures, marqueurs) avec le module standard `unittest` de Python.

L'organisation des tests est principalement centralisée dans deux emplacements :
-   **`tests/`** : Ce répertoire contient la majorité des tests, structurés en sous-répertoires correspondant aux différents types de tests (`unit`, `functional`, `e2e`, etc.).
-   **`argumentation_analysis/`** : Certains tests sont intégrés directement dans le code source de l'application, ce qui permet de tester des composants spécifiques de manière isolée.

## 2. Lancement des Tests

Le script `run_tests.ps1` est le point d'entrée centralisé pour l'exécution de tous les tests. Il accepte plusieurs paramètres pour cibler des types de tests spécifiques.

Voici les principales commandes :

### Tests Unitaires et Fonctionnels

Ces tests sont lancés directement avec `pytest`.

-   **Tests unitaires** :
    ```powershell
    .\run_tests.ps1 -Type unit
    ```
-   **Tests fonctionnels** :
    ```powershell
    .\run_tests.ps1 -Type functional
    ```
-   **Lancer un chemin spécifique** :
    ```powershell
    .\run_tests.ps1 -Type unit -Path tests/unit/test_un_cas.py
    ```
-   **Tous les tests Python (unitaires et fonctionnels)** :
    ```powershell
    .\run_tests.ps1 -Type all
    ```

### Tests End-to-End (E2E)

Le projet distingue deux types de tests E2E :

1.  **Tests E2E avec Playwright (JavaScript/TypeScript)** :
    Ces tests interagissent avec l'interface web de l'application.
    ```powershell
    .\run_tests.ps1 -Type e2e -Browser chromium
    ```
    Les navigateurs supportés sont `chromium`, `firefox`, et `webkit`.

2.  **Tests E2E avec Pytest (Python)** :
    Ces tests sont orchestrés par un script Python qui simule des scénarios complexes.
    ```powershell
    .\run_tests.ps1 -Type e2e-python
    ```

### Tests de Validation

Un ensemble de tests dédiés à la validation de fonctionnalités spécifiques peut être lancé avec :
```powershell
.\run_tests.ps1 -Type validation
```

## 3. Organisation des Tests

L'organisation des tests repose sur une combinaison de structure de répertoires et de l'utilisation de marqueurs `pytest` pour une classification fine.

### Organisation par Répertoires

La structure des répertoires de test est la suivante :

-   **`tests/unit`**: Contient les tests unitaires, qui vérifient les composants de manière isolée.
-   **`tests/functional`**: Contient les tests fonctionnels, qui testent des fonctionnalités complètes, mais sans interaction avec l'interface utilisateur.
-   **`tests/e2e`**: Contient les tests End-to-End, qui simulent des scénarios utilisateur complets.
-   **`tests/validation`**: Contient les tests de validation, qui vérifient des exigences spécifiques.
-   **`argumentation_analysis/`**: Certains tests sont directement intégrés dans les modules de l'application.

### Classification par Marqueurs `pytest`

Le fichier `pyproject.toml` définit un ensemble riche de marqueurs `pytest` qui permettent de filtrer et de catégoriser les tests de manière très précise. Voici quelques-uns des marqueurs les plus importants :

-   **`@pytest.mark.integration`**: Tests qui vérifient l'intégration entre plusieurs composants.
-   **`@pytest.mark.e2e_test`**: Marqueur générique pour les tests End-to-End.
-   **`@pytest.mark.requires_llm`**: Tests qui nécessitent l'accès à un grand modèle de langage (LLM).
-   **`@pytest.mark.playwright`**: Tests spécifiques à l'interface utilisateur utilisant Playwright.
-   **`@pytest.mark.slow`**: Tests dont l'exécution est longue.
-   **`@pytest.mark.validation`**: Tests qui font partie du cycle de validation.

Cette double approche (répertoires et marqueurs) offre une grande flexibilité pour lancer des suites de tests ciblées en fonction des besoins.

## 4. Composants Clés de l'Infrastructure

Plusieurs fichiers et scripts constituent l'épine dorsale de l'infrastructure de test :

-   **`run_tests.ps1`**: Le script d'orchestration principal qui sert de point d'entrée unique pour tous les tests.

-   **`activate_project_env.ps1`**: Un script essentiel, appelé par `run_tests.ps1`, qui est responsable de l'activation de l'environnement de développement (`conda`) pour garantir que toutes les dépendances sont disponibles.

-   **`pytest.ini`**: Ce fichier configure les chemins de test de base et exclut les répertoires non pertinents. Il définit `tests` comme le principal répertoire de tests.

-   **`pyproject.toml`**: Ce fichier étend la configuration de `pytest`. C'est ici que sont définis les chemins de test supplémentaires (comme `argumentation_analysis`) et, surtout, la liste complète des marqueurs `pytest` personnalisés.

-   **`tests/conftest.py`**: C'est le fichier central pour la définition des *fixtures* `pytest` partagées. Les fixtures sont des fonctions qui fournissent des données, des objets ou des configurations réutilisables pour les tests. Ce fichier joue un rôle crucial en initialisant des services (comme le serveur web pour les tests E2E) et en mettant en place des mocks pour isoler les tests. D'autres fichiers `conftest.py` existent dans des sous-répertoires pour des configurations plus spécifiques.

## 5. Couverture et Observations

L'infrastructure de test du projet est mature et bien structurée. Voici quelques observations clés :

-   **Couverture à plusieurs niveaux**: Le projet bénéficie d'une couverture de test à plusieurs niveaux (unitaire, fonctionnel, E2E), ce qui est une bonne pratique pour assurer la qualité du logiciel.
-   **Utilisation avancée de `pytest`**: L'utilisation extensive de marqueurs `pytest` et de fixtures via `conftest.py` démontre une compréhension approfondie de l'outillage et permet une gestion de tests très flexible et granulaire.
-   **Orchestration centralisée**: Le script `run_tests.ps1` simplifie grandement l'exécution des tests et garantit la cohérence en gérant l'activation de l'environnement.
-   **Tests E2E hétérogènes**: La combinaison de tests E2E basés sur Playwright (pour l'interface utilisateur) et sur Python (pour les workflows backend) permet une validation complète des scénarios utilisateur.
-   **Tests de validation dédiés**: L'existence d'une catégorie de tests de `validation` suggère un processus de qualification formel pour certaines fonctionnalités.