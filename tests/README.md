# Tests du Projet d'Analyse d'Argumentation

Ce répertoire contient l'ensemble des tests (unitaires, d'intégration, fonctionnels) pour le projet d'analyse d'argumentation. L'objectif de cette suite de tests est de garantir la robustesse, la fiabilité et la correction du code à travers les différentes couches du système, depuis les interactions de bas niveau avec la JVM jusqu'aux workflows d'analyse complets.

## Philosophie de Test

Notre approche de test est basée sur la pyramide des tests. Nous privilégions une large base de **tests unitaires** rapides et isolés, complétée par des **tests d'intégration** ciblés pour vérifier les interactions entre les composants, et enfin quelques **tests fonctionnels** de bout en bout pour valider les scénarios utilisateurs clés.

## Structure des Tests

Le répertoire `tests` est organisé pour refléter les différentes natures de tests et faciliter la navigation :

-   **[`agents/`](agents/README.md)**: Contient les tests pour les agents, qui sont les acteurs principaux du système. Les tests sont subdivisés par type d'agent (logique, informel, etc.).

-   **[`environment_checks/`](environment_checks/README.md)**: Une suite de tests de diagnostic pour valider la configuration de l'environnement local (dépendances, `PYTHONPATH`).

-   **[`fixtures/`](fixtures/README.md)**: Contient les fixtures Pytest partagées, utilisées pour initialiser des données ou des états nécessaires à l'exécution des tests.

-   **[`functional/`](functional/README.md)**: Contient les tests fonctionnels qui valident des workflows complets du point de vue de l'utilisateur.

-   **[`integration/`](integration/README.md)**: Contient les tests d'intégration qui vérifient que différents modules interagissent correctement.
    -   **[`integration/jpype_tweety/`](integration/jpype_tweety/README.md)**: Tests spécifiques à l'intégration avec la bibliothèque Java Tweety via JPype.

-   **[`minimal_jpype_tweety_tests/`](minimal_jpype_tweety_tests/README.md)**: Tests de très bas niveau pour la communication directe Python-Java, utiles pour le débogage de la couche JPype.

-   **[`mocks/`](mocks/README.md)**: Contient des mocks réutilisables qui simulent le comportement de dépendances externes (ex: `numpy`, `pandas`, `jpype`) pour isoler le code testé.

-   **[`support/`](support/README.md)**: Contient des outils et scripts de support pour les tests, comme un installeur de dépendances portables (ex: GNU Octave).

-   **[`unit/`](unit/README.md)**: Contient les tests unitaires qui vérifient de petites unités de code isolées. La structure de ce répertoire miroir celle du code source du projet.

-   **[`ui/`](ui/README.md)**: Contient les tests pour la logique sous-jacente de l'interface utilisateur.

-   **[`conftest.py`](conftest.py)**: Fichier de configuration global pour Pytest, contenant les hooks et les fixtures disponibles pour tous les tests.

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

-   **Exécuter un test spécifique (une fonction ou une méthode) dans un fichier :**
    ```bash
    pytest tests/unit/mon_module/test_ma_fonction.py::test_cas_particulier
    ```

### Utilisation des Marqueurs Pytest :

Des marqueurs (`@pytest.mark.<nom_marqueur>`) sont utilisés pour catégoriser les tests.

-   **Exécuter les tests marqués comme `slow` :**
    ```bash
    pytest -m slow
    ```

-   **Exécuter les tests qui ne sont PAS marqués comme `slow` :**
    ```bash
    pytest -m "not slow"
    ```
    Consultez le fichier [`tests/conftest.py`](conftest.py) pour voir les marqueurs personnalisés disponibles.

### Tests avec Couverture de Code

Pour exécuter les tests et générer un rapport de couverture de code :

```bash
pytest --cov=argumentation_analysis --cov-report=html
```
Le rapport HTML sera généré dans un répertoire `htmlcov/`.

## Bonnes Pratiques et Documentation

-   **Bonnes Pratiques**: Pour des directives détaillées sur l'écriture et la maintenance des tests, veuillez consulter le document [`BEST_PRACTICES.md`](BEST_PRACTICES.md).
-   **Plan d'action**: [Plan d'action pour l'amélioration des tests](../docs/tests/plan_action_tests.md)
-   **Rapport de couverture**: [Rapport sur l'état du dépôt et la couverture des tests](../docs/reports/etat_depot_couverture_tests.md)