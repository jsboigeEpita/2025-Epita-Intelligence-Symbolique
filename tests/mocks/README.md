# Mocks pour les Dépendances Externes

## Objectif

Ce répertoire centralise les **mocks** (simulations) pour les bibliothèques externes utilisées dans le projet. L'objectif principal est de permettre l'exécution des tests unitaires de manière rapide et isolée, sans nécessiter l'installation complète de dépendances lourdes comme la JVM (via JPype), NumPy, Pandas, ou Semantic Kernel.

Ces mocks assurent que la logique applicative peut être testée indépendamment de ses dépendances externes, ce qui améliore la stabilité et la vitesse de la suite de tests.

## Composants Mockés

### 1. Simulation de JPype

Le mock de JPype est le plus complexe et est essentiel pour tester le code qui interagit avec des bibliothèques Java (notamment Tweety).

*   **`jpype_mock.py`**: Point d'entrée principal qui orchestre la simulation de JPype.
*   **`activate_jpype_mock.py`**: Script simple pour activer le mock en l'important avant le code de test.
*   **`jpype_components/`**: Répertoire contenant la logique détaillée du mock de JPype, décomposée par fonctionnalité (JVM, JClass, types, exceptions, etc.). Voir le `README.md` de ce sous-répertoire pour plus de détails.

### 2. Simulation des Bibliothèques de Data Science

*   **`pandas_mock.py`**: Fournit une implémentation légère de `pandas`, incluant `DataFrame`, `GroupBy`, et les fonctions de lecture/écriture. Cela permet de tester les manipulations de données sans avoir `pandas` installé.
*   **`numpy_setup.py`**: Met en place un système sophistiqué pour utiliser soit la vraie bibliothèque `NumPy`, soit un mock. Il fournit une fixture `pytest` (`setup_numpy_for_tests_fixture`) qui, marquée par `@pytest.mark.use_mock_numpy`, installe un mock complet de NumPy. Cela est particulièrement utile pour les environnements où NumPy n'est pas disponible ou pour accélérer les tests.
*   **`legacy_numpy_array_mock.py`**: Contient l'implémentation détaillée du mock de `NumPy`, y compris `recarray` et les sous-modules principaux.

### 3. Simulation de Services d'IA

*   **`semantic_kernel_mock.py`**: Simule le framework `semantic-kernel`, y compris le noyau, les plugins, les fonctions et les services de complétion de chat. Cela permet de tester la logique d'orchestration d'IA sans faire de réels appels à des modèles de langage.
*   **`semantic_kernel_agents_mock.py`**: Fournit des mocks spécifiques pour les agents basés sur Semantic Kernel.

### 4. Autres Mocks

*   **`matplotlib_mock.py`**, **`networkx_mock.py`**, **`tensorflow_mock.py`**, **`torch_mock.py`**: Mocks plus simples pour d'autres bibliothèques, qui permettent d'éviter les erreurs d'importation dans les tests qui n'utilisent pas directement leurs fonctionnalités.

## Utilisation

Pour utiliser un mock, il suffit généralement de s'assurer qu'il est importé avant la bibliothèque réelle. Pour les mocks plus complexes comme JPype et NumPy, des mécanismes d'activation spécifiques sont en place :

*   **JPype**: Importez `tests.mocks.activate_jpype_mock` au début de votre fichier de test.
*   **NumPy**: Utilisez le marqueur `@pytest.mark.use_mock_numpy` sur votre fonction ou classe de test pour activer le mock via la fixture `setup_numpy_for_tests_fixture` (définie dans `numpy_setup.py` et généralement disponible globalement via `conftest.py`).

Ces mocks sont essentiels pour maintenir une suite de tests robuste et efficace, découplant la logique métier des dépendances de l'environnement.
