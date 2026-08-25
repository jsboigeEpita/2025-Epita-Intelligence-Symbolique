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
*   **`numpy_mock.py`**: Implementation detaillee du mock de NumPy (`recarray`, sous-modules).
    Deux consommateurs reels : `tests/mocks/numpy_setup.py:113` et
    `tests/utils/common_test_helpers.py:212`.

## Mocks supprimes (#1891)

Neuf fichiers morts -- zero importeur, jamais collectes -- ont ete supprimes
(`ebe2b8b7`) : `bootstrap.py`, `matplotlib_mock.py`, `networkx_mock.py`,
`pydantic_mock.py`, `pytest_mock.py`, `semantic_kernel_mock.py`,
`semantic_kernel_agents_mock.py`, `tensorflow_mock.py`, `torch_mock.py`.

Le motif n'etait pas seulement qu'ils etaient morts : plusieurs **s'installaient
eux-memes dans `sys.modules` au niveau module**. Importer un tel fichier par
accident -- une seule ligne suffit -- remplacait la vraie dependance pour tout le
reste du processus : `networkx_mock` aurait masque le networkx reel dont la
production depend (`argumentation_analysis/services/jtms/jtms_core.py:19`), et
`pytest_mock` aurait remplace pytest lui-meme.

La garde `tests/unit/mocks/test_no_sysmodules_hijack_1891.py` interdit le retour du
mecanisme. Elle ne tient pas une liste de fichiers autorises -- elle epingle une
**distinction** : une ecriture `sys.modules` executee a l'import (statement nu, `try`,
`if`) est interdite ; la meme ecriture **dans le corps d'une fonction**, activee par un
appel ou une fixture explicite, est le patron sanctionne (`numpy_setup.py`,
`pandas_setup.py`). Portee actuelle : `tests/mocks/*.py`, sans les sous-repertoires
(cf. #1895).

## Utilisation

Pour utiliser un mock, il suffit généralement de s'assurer qu'il est importé avant la bibliothèque réelle. Pour les mocks plus complexes comme JPype et NumPy, des mécanismes d'activation spécifiques sont en place :

*   **JPype**: Importez `tests.mocks.activate_jpype_mock` au début de votre fichier de test.
*   **NumPy**: Utilisez le marqueur `@pytest.mark.use_mock_numpy` sur votre fonction ou classe de test pour activer le mock via la fixture `setup_numpy_for_tests_fixture` (définie dans `numpy_setup.py` et généralement disponible globalement via `conftest.py`).

Ces mocks sont essentiels pour maintenir une suite de tests robuste et efficace, découplant la logique métier des dépendances de l'environnement.
