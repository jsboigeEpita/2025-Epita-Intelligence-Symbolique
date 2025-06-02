# Plan d'Analyse et Actions Proposées - Nettoyage Tests Lot 1

Ce document résume l'analyse effectuée et les actions proposées pour le Lot 1 du nettoyage des tests, concernant les fichiers situés principalement à la racine du répertoire `tests/`.

## Contexte
L'objectif est d'améliorer l'organisation, la documentation, et la réutilisabilité des fichiers de test.

## Fichiers Traités et Actions

### 1. `tests/async_test_case.py`

*   **Analyse :** Utilitaire de test asynchrone, potentiellement obsolète car non utilisé et `pytest-asyncio` est préféré.
*   **Actions Documentaires (Mode Architecte) :**
    *   Ajout d'une note dans `tests/BEST_PRACTICES.md` clarifiant l'usage de `@pytest.mark.anyio` pour les tests asynchrones et la dépréciation de `AsyncTestCase`.
*   **Actions de Code Proposées (Mode Code) :**
    *   Supprimer l'import inutile de `AsyncTestCase` dans `tests/functional/test_fallacy_detection_workflow.py`.
    *   Supprimer le fichier `tests/async_test_case.py`.
*   **Commit Proposé (après actions code) :** `Refactor(tests): Remove obsolete AsyncTestCase and update best practices for async testing`

### 2. `tests/standalone_mock_tests.py`

*   **Analyse :** Script de test autonome avec des mocks internes pour une logique de communication. Redondant car des composants de communication équivalents existent dans `argumentation_analysis/core/communication/` et sont testés.
*   **Actions Documentaires (Mode Architecte) :**
    *   Mise à jour de la description dans `tests/README.md` pour indiquer son statut et la nécessité d'évaluation pour refactorisation/suppression.
*   **Actions de Code Proposées (Mode Code - potentiellement tâche dédiée) :**
    *   Évaluer les scénarios de test uniques/pertinents.
    *   Migrer ces scénarios pour tester les composants réels de `core/communication` en utilisant `pytest`.
    *   Supprimer `tests/standalone_mock_tests.py`.
    *   Mettre à jour `tests/README.md` pour supprimer la référence.
*   **Proposition d'Extraction Complexe :** La migration des tests de ce fichier pour couvrir `core/communication` est une tâche de refactorisation plus importante.
*   **Commit Proposé (après actions code) :** `Refactor(tests): Remove standalone_mock_tests.py and integrate relevant scenarios into core communication tests`

### 3. `tests/test_crypto_errors.py`

*   **Analyse :** Script de test manuel pour un `CryptoService` local. Redondant car un `CryptoService` plus complet existe dans `argumentation_analysis/services/crypto_service.py` et possède déjà des tests `pytest` (`argumentation_analysis/tests/test_crypto_service.py`) qui couvrent les cas d'erreur.
*   **Actions Documentaires (Mode Architecte) :** Aucune modification de README effectuée pour ce fichier spécifiquement, car le fichier de test principal est ailleurs.
*   **Actions de Code Proposées (Mode Code) :**
    *   Supprimer le fichier `tests/test_crypto_errors.py`.
*   **Commit Proposé (après actions code) :** `Refactor(tests): Remove redundant test_crypto_errors.py`

### 4. `tests/test_dependencies.py`

*   **Analyse :** Script de diagnostic pour vérifier l'importabilité des dépendances et tester `jpype`. Fait double emploi avec les scripts de `scripts/setup/` et les tests d'intégration `jpype` existants.
*   **Actions Documentaires (Mode Architecte) :**
    *   Ajout d'une note dans `tests/README.md` indiquant son évaluation pour refactorisation/remplacement.
*   **Actions de Code Proposées (Mode Code) :**
    *   Créer un nouveau test `pytest` (ex: `tests/core/test_project_imports.py`) pour vérifier l'import de toutes les dépendances listées.
    *   Confirmer que les tests `jpype` (JVM, imports Java) sont bien couverts par `tests/integration/jpype_tweety/test_jvm_stability.py` et `conftest.py`.
    *   Supprimer `tests/test_dependencies.py`.
    *   Mettre à jour `tests/README.md` pour refléter ces changements.
*   **Commit Proposé (après actions code) :** `Refactor(tests): Replace test_dependencies.py script with dedicated pytest import checks`

### 5. `tests/test_enhanced_complex_fallacy_analyzer.py`
### 6. `tests/test_enhanced_contextual_fallacy_analyzer.py`
### 7. `tests/test_enhanced_fallacy_severity_evaluator.py`

*   **Analyse (commune aux trois) :** Tests unitaires pour les analyseurs améliorés, style hybride `unittest`/`pytest`. Actuellement à la racine de `tests/`.
*   **Actions Documentaires (Mode Architecte) :**
    *   Mise à jour des chemins dans `tests/README.md` pour pointer vers le nouvel emplacement proposé : `tests/agents/tools/analysis/enhanced/`.
*   **Actions de Code Proposées (Mode Code) :**
    *   Refactoriser les classes de test en style `pytest` pur.
    *   Déplacer les trois fichiers vers `tests/agents/tools/analysis/enhanced/`.
    *   Créer un `README.md` dans `tests/agents/tools/analysis/enhanced/` pour décrire ces tests.
*   **Commit Proposé (après actions code pour les trois fichiers) :** `Refactor(tests): Migrate enhanced analyzer tests to pytest style and new location tests/agents/tools/analysis/enhanced/`

### 8. `tests/test_error_recovery.py`

*   **Analyse :** Script de test exploratoire pour une logique de gestion et de récupération d'erreurs, avec des classes `StateManager` et `ErrorRecoveryManager` locales. `StateManager` a un équivalent plus complexe dans le code source ; `ErrorRecoveryManager` introduit une logique non centralisée actuellement.
*   **Actions Documentaires (Mode Architecte) :**
    *   Ajout d'une note dans `tests/README.md` indiquant son statut de script exploratoire à évaluer.
*   **Actions de Code Proposées (Mode Code - à discuter) :**
    *   **Option A (Extraction) :** Concevoir et implémenter un `ErrorRecoveryManager` centralisé. Adapter les scénarios de ce script en tests `pytest` pour le nouveau composant. Supprimer `tests/test_error_recovery.py`.
    *   **Option B (Conservation exploratoire) :** Déplacer vers `tests/exploratory/`, nettoyer, et documenter son rôle.
    *   **Option C (Suppression) :** Si la logique n'est pas jugée pertinente.
    *   Mettre à jour `tests/README.md` en conséquence.
*   **Proposition d'Extraction Complexe :** L'extraction et la conception d'un `ErrorRecoveryManager` robuste.
*   **Commit Proposé (si Option A) :** `Feat(core): Implement ErrorRecoveryManager and add tests` (suivi de `Refactor(tests): Remove exploratory test_error_recovery.py`)

### 9. `tests/test_extract_agent_adapter.py`

*   **Analyse :** Tests unitaires pour `ExtractAgentAdapter`. Déjà bien placé dans `tests/orchestration/hierarchical/operational/adapters/`. Utilise un style `pytest` moderne. Contient une manipulation de `sys.path` à vérifier.
*   **Actions Documentaires (Mode Architecte) :**
    *   Ajout d'une référence spécifique au fichier dans `tests/README.md` sous la section du module prioritaire.
*   **Actions de Code Proposées (Mode Code) :**
    *   Vérifier et potentiellement supprimer la manipulation de `sys.path`.
    *   Créer un `README.md` dans `tests/orchestration/hierarchical/operational/adapters/`.
*   **Commit Proposé (après actions code) :** `Chore(tests): Cleanup sys.path in test_extract_agent_adapter` et `Docs(tests): Add README for operational agent adapter tests`

### 10. `tests/test_fallacy_analyzer.py`

*   **Analyse :** Tests unitaires obsolètes, marqué `@pytest.mark.skip` dans le code car il teste un `FallacyDetector` qui n'existe plus.
*   **Actions Documentaires (Mode Architecte) :**
    *   Référence dans `tests/README.md` marquée comme obsolète et pour suppression.
*   **Actions de Code Proposées (Mode Code) :**
    *   Supprimer le fichier `tests/test_fallacy_analyzer.py`.
    *   Mettre à jour `tests/README.md` pour retirer complètement la référence.
*   **Commit Proposé (après actions code) :** `Refactor(tests): Remove obsolete test_fallacy_analyzer.py`

## Prochaines Étapes
1.  Validation de ce plan.
2.  Passage à un mode "Code" pour implémenter les actions de code proposées.
3.  Commits et push réguliers des changements.
4.  Rédaction du rapport final pour ce lot.