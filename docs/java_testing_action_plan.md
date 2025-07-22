# Plan d'Action pour la Stabilisation des Tests d'Intégration Java

Ce document détaille la stratégie et les étapes pour corriger la suite de tests E2E et assurer une isolation robuste des tests dépendants de la JVM.

## 1. Stratégie Générale

La stratégie repose sur l'isolation des tests basés sur la JVM du reste de la suite de tests en utilisant les marqueurs `pytest`. Cela nous permettra de contrôler précisément quand et comment la JVM est démarrée et d'éviter les conflits avec d'autres bibliothèques ou plugins.

L'objectif est de diviser la suite de tests en deux groupes distincts :
1.  **Tests standards** : Peuvent être exécutés en parallèle (via `pytest-xdist`) car ils n'interagissent pas avec la JVM.
2.  **Tests JVM** : Doivent être exécutés séquentiellement dans un seul processus pour garantir que la JVM est démarrée et arrêtée une seule fois.

## 2. Plan d'Action Détaillé

### Phase 1 : Configuration de l'Environnement

L'objectif de cette phase est de préparer les fichiers de configuration pour reconnaître notre nouvelle stratégie de test.

1.  **Déclarer le marqueur Pytest** :
    *   **Fichier à modifier** : `pytest.ini`
    *   **Action** : Ajouter la ligne suivante sous la section `[pytest]` pour enregistrer le marqueur `jvm_test`.
        ```ini
        markers =
            jvm_test: mark a test as dependent on the JVM.
        ```
    *   **Raison** : Cela évite les avertissements de `pytest` et officialise notre marqueur.

2.  **Assurer la disponibilité de `pytest-xdist`** :
    *   **Fichier à vérifier/modifier** : `pyproject.toml` (ou `requirements-dev.txt`).
    *   **Action** : S'assurer que `pytest-xdist` est listé comme une dépendance de développement.
    *   **Raison** : Ce plugin est essentiel pour exécuter les tests non-JVM en parallèle et accélérer le cycle de feedback.

### Phase 2 : Marquage des Tests Dépendants de la JVM

Cette phase consiste à identifier et marquer tous les tests qui nécessitent que la JVM soit active.

1.  **Identifier les tests concernés** :
    *   **Action** : Parcourir la base de code de test (répertoire `tests/`) et identifier tous les fichiers de test qui :
        *   Importent `jpype`.
        *   Utilisent une fixture qui dépend de la JVM.
        *   Appellent directement ou indirectement le code dans `argumentation_analysis/core/jvm_setup.py`.
    *   **Suggestion d'outil** : Utiliser une recherche globale pour `jpype` ou `jvm_setup` pour accélérer l'identification.

2.  **Appliquer le marqueur `@pytest.mark.jvm_test`** :
    *   **Action** : Pour chaque test ou classe de test identifié, ajouter le décorateur suivant :
        ```python
        import pytest

        @pytest.mark.jvm_test
        def test_qui_utilise_la_jvm():
            # ...
        ```
    *   **Raison** : Ce marqueur est la pierre angulaire de notre stratégie d'isolation.

### Phase 3 : Modification du Code de Test (Fixtures)

Cette phase centralise la gestion du cycle de vie de la JVM dans une fixture `pytest`.

1.  **Créer une fixture de contrôle de la JVM** :
    *   **Fichier à modifier** : `tests/conftest.py`
    *   **Action** : Implémenter une nouvelle fixture `session`-scoped qui gère le démarrage et l'arrêt de la JVM.
        ```python
        import pytest
        from argumentation_analysis.core.jvm_setup import JvmManager

        @pytest.fixture(scope="session", autouse=True)
        def jvm_controller(request):
            """
            Fixture to manage the JVM lifecycle for jvm_test markers.
            The JVM is started only if jvm_test tests are selected.
            """
            if request.config.getoption("-m") and "jvm_test" in request.config.getoption("-m"):
                print("Starting JVM for test session...")
                JvmManager.start_jvm()
                yield
                print("Shutting down JVM for test session...")
                JvmManager.shutdown_jvm()
            else:
                yield # Do nothing if no jvm_test is selected
        ```
    *   **Raison** :
        *   `scope="session"` garantit que la JVM est démarrée une seule fois pour toute la session de test.
        *   `autouse=True` assure que la fixture est active pour toutes les sessions.
        *   La condition `if "jvm_test" in request.config.getoption("-m")` est une optimisation clé : elle ne démarre la JVM que si les tests JVM sont explicitement demandés.

### Phase 4 : Validation de la Nouvelle Stratégie

L'objectif final est de valider que notre nouvelle organisation résout le problème d'instabilité.

1.  **Mettre à jour le script de test** :
    *   **Fichier à modifier/créer** : `run_tests.ps1` (ou un nouveau script `run_e2e_tests.ps1`)
    *   **Action** : Remplacer l'ancienne commande par deux commandes distinctes :
        ```powershell
        # Step 1: Run all non-JVM tests in parallel
        echo "Running non-JVM tests..."
        pytest -m "not jvm_test" -n auto

        # Check if the first command succeeded
        if ($LASTEXITCODE -ne 0) {
            echo "Non-JVM tests failed. Aborting."
            exit $LASTEXITCODE
        }

        # Step 2: Run all JVM tests sequentially
        echo "Running JVM tests..."
        pytest -m "jvm_test" --dist=no # or -n 0

        if ($LASTEXITCODE -ne 0) {
            echo "JVM tests failed."
            exit $LASTEXITCODE
        }

        echo "All tests passed successfully!"
        ```
    *   **Raison** : Cette séquence garantit l'isolation. Les tests rapides et sûrs sont exécutés en premier. Les tests JVM, plus lents et sensibles, sont exécutés ensuite dans un environnement contrôlé et non parallélisé.

2.  **Procédure de validation manuelle** :
    *   Exécuter le script `run_tests.ps1` mis à jour.
    *   Vérifier que les deux blocs de tests s'exécutent.
    *   Confirmer qu'il n'y a pas de crash de la JVM ou d'erreur "access violation".
    *   Exécuter `pytest -m "not jvm_test"` seul et vérifier qu'il est significativement plus rapide.
    *   Exécuter `pytest -m "jvm_test"` seul et vérifier qu'il passe.
