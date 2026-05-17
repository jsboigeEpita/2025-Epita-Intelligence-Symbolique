# Investigation : Réparation de la Suite E2E Playwright (2025-08-31)

Ce document détaille le processus d'investigation et de réparation de la suite de tests E2E Playwright qui marquait tous les tests comme "SKIPPED".

## 1. Contexte et Hypothèse

- **Problème :** L'exécution de la suite de tests E2E via le `TestRunner` unifié (`project_core/test_runner.py --type e2e`) résulte en tous les tests marqués comme "SKIPPED".
- **Hypothèse Initiale :** Une régression a introduit une condition qui provoque le saut systématique des tests `pytest-playwright`. Le fichier `tests/conftest.py`, qui gère la configuration globale de pytest, est le principal suspect.

## 2. Analyse de la Configuration de Test

### Fichiers Clés Analysés :
- `project_core/test_runner.py`: Orchestrateur principal qui lance `pytest` pour le répertoire `tests/e2e`.
- `tests/e2e/conftest.py`: Configuration `pytest` locale au répertoire E2E. Ne contient pas de logique de skip, mais récupère les URLs des services.
- `tests/conftest.py`: Fichier de configuration `pytest` global.

### Découverte Principale :
L'analyse de `tests/conftest.py` a révélé le mécanisme suivant :
1.  Le hook `pytest_collection_finish` détecte si des tests marqués `e2e` sont présents.
2.  Si c'est le cas, il met en cache une valeur `is_e2e_session = True`.
3.  Le hook `pytest_sessionstart` lit cette valeur et, si elle est `True`, il **saute délibérément l'initialisation de la JVM**.
4.  La fixture `jvm_session` est configurée pour vérifier si la JVM a démarré. Si un test dépend de cette fixture et que la JVM n'a pas démarré, le test est sauté via `pytest.skip()`.

**Cause Racine Suspectée :** Des tests dans le répertoire `tests/e2e/python` ont une dépendance (directe ou indirecte) à la fixture `jvm_session` alors qu'ils ne devraient pas, puisque la JVM n'est pas censée être initialisée pour les tests E2E.

## 3. Investigation via l'Historique Git

L'analyse de l'historique Git a identifié le commit `fffb2bbf` comme la source de la régression. Ce commit a remplacé un `@pytest.mark.skipif` par un marqueur personnalisé `@pytest.mark.jvm_test`, introduisant involontairement une dépendance à la fixture `jvm_session` dans la suite de tests E2E.

## 4. Correctif

Le correctif a été appliqué en plusieurs étapes :
1.  **Modification de `tests/conftest.py`**: La fixture `jvm_session` a été modifiée pour ne plus skipper les tests en mode E2E, résolvant ainsi le problème de "skip" global.
2.  **Correction de l'Agent `InformalFallacyAgent`**: La signature de la méthode `invoke_single` a été corrigée pour accepter un argument `history` optionnel, résolvant une `TypeError` dans le backend.
3.  **Mise à jour de l'Endpoint d'API**: L'appel à l'API dans `tests/e2e/python/test_api_dung_integration.py` a été mis à jour de `/api/framework` à `/api/v1/framework/analyze` pour refléter les changements récents dans le routing de l'API.
4.  **Réactivation des tests**: Les marqueurs `@pytest.mark.skip` ont été retirés de la suite de tests `TestFrameworkBuilder` pour la réinclure dans l'exécution.
5.  **Correction du format des données**: Le format des données envoyées à l'API dans `tests/e2e/python/test_api_dung_integration.py` a été corrigé pour correspondre au schéma de validation Pydantic du backend.

Ces modifications ont permis de rendre la suite de tests E2E de nouveau opérationnelle.
