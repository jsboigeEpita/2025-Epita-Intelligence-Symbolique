# Tests du Projet d'Intelligence Symbolique

Ce répertoire contient les tests unitaires, d'intégration et fonctionnels du projet d'Intelligence Symbolique. L'objectif principal de ces tests est de garantir la robustesse, la fiabilité et la correction du code à travers différentes couches du système.

## Structure des Tests

Le répertoire des tests est organisé comme suit pour refléter les meilleures pratiques et faciliter la navigation et la maintenance :

-   **`tests/unit/`**: Contient les tests unitaires. Ces tests vérifient le comportement de petites unités de code isolées (fonctions, méthodes, classes). La structure de ce répertoire miroir celle du code source du projet (par exemple, `project_core`, `argumentation_analysis`, etc.) pour une correspondance claire entre le code et ses tests.
-   **`tests/integration/`**: Contient les tests d'intégration. Ces tests vérifient que différents modules ou composants du système interagissent correctement entre eux. Cela inclut notamment les tests d'intégration avec des composants externes comme JPype pour TweetyLib.
-   **`tests/functional/`**: Contient les tests fonctionnels. Ces tests valident des workflows complets ou des fonctionnalités spécifiques du point de vue de l'utilisateur, assurant que le système répond aux exigences fonctionnelles.
-   **`tests/fixtures/`**: Contient les fixtures Pytest partagées. Les fixtures sont utilisées pour initialiser des données ou des états nécessaires à l'exécution des tests, favorisant la réutilisabilité et la clarté.
-   **`tests/mocks/`**: Contient les mocks réutilisables. Les mocks simulent le comportement de dépendances externes ou de parties complexes du système, permettant d'isoler le code testé.
-   **`tests/support/`**: Contient les outils et scripts de support pour les tests. Par exemple, cela peut inclure des scripts pour installer des dépendances spécifiques nécessaires à certains tests (comme un installeur Octave).
-   **`tests/conftest.py`**: Ce fichier à la racine du répertoire `tests/` est utilisé par Pytest pour les configurations globales, les hooks et les fixtures qui sont disponibles pour tous les tests du projet. Il permet de centraliser la configuration des tests.

## Exécution des Tests

Avant d'exécuter les tests, il est impératif d'activer l'environnement virtuel du projet. Utilisez le script suivant à la racine du projet :

```powershell
. .\activate_project_env.ps1
```

Une fois l'environnement activé, vous pouvez utiliser Pytest pour lancer les tests.

### Commandes Pytest de base :

-   **Exécuter tous les tests du projet :**
    ```bash
    pytest
    ```

-   **Exécuter tous les tests dans un répertoire spécifique (par exemple, les tests unitaires) :**
    ```bash
    pytest tests/unit/
    ```

-   **Exécuter tous les tests dans un fichier spécifique :**
    ```bash
    pytest tests/unit/mon_module/test_ma_fonction.py
    ```

-   **Exécuter un test spécifique (une fonction ou une méthode) dans un fichier :**
    ```bash
    pytest tests/unit/mon_module/test_ma_fonction.py::test_cas_particulier
    ```

### Utilisation des Marqueurs Pytest :

Pytest permet d'utiliser des marqueurs (`@pytest.mark.<nom_marqueur>`) pour catégoriser les tests. Vous pouvez ensuite exécuter sélectivement des tests basés sur ces marqueurs.

-   **Exécuter les tests marqués comme `slow` :**
    ```bash
    pytest -m slow
    ```

-   **Exécuter les tests qui ne sont PAS marqués comme `slow` :**
    ```bash
    pytest -m "not slow"
    ```
    Consultez la documentation de Pytest et le fichier [`tests/conftest.py`](tests/conftest.py:1) pour voir les marqueurs personnalisés disponibles dans ce projet.

### Tests avec Couverture de Code

Pour exécuter les tests et générer un rapport de couverture de code :

```bash
pytest --cov=project_core --cov=argumentation_analysis --cov-report=html
```
(Adaptez les modules `--cov` en fonction des répertoires principaux de votre code source.)
Le rapport HTML sera généré dans un répertoire `htmlcov/`.

## Bonnes Pratiques de Test

Pour des directives détaillées sur l'écriture et la maintenance des tests, veuillez consulter le document [Bonnes Pratiques pour les Tests (`BEST_PRACTICES.md`)](BEST_PRACTICES.md:1). Ce document couvre les principes généraux, l'organisation, la gestion des dépendances, l'utilisation des fixtures, et des conseils spécifiques pour les tests d'intégration et fonctionnels.

## Documentation Associée

-   [Plan d'action pour l'amélioration des tests](../docs/tests/plan_action_tests.md)
-   [Rapport sur l'état du dépôt et la couverture des tests](../docs/reports/etat_depot_couverture_tests.md)