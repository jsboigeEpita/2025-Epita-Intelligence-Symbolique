# Tests Minimaux d'Intégration JPype-Tweety

Ce répertoire contient une suite de tests d'intégration de bas niveau conçus pour valider la communication fondamentale entre Python et la bibliothèque de raisonnement logique Java [Tweety](https://tweetyproject.org/) via le pont [JPype](https://jpype.readthedocs.io/).

## Objectif des Tests

L'objectif principal de ces tests est de s'assurer que l'environnement JPype est correctement configuré et que les fonctionnalités de base de Tweety sont accessibles depuis Python. Ils servent de première ligne de défense pour diagnostiquer les problèmes liés à la JVM, au classpath, aux versions des JARs ou à l'API de Tweety.

Ces tests sont "minimaux" car ils n'impliquent pas la couche d'abstraction des agents du projet. Ils interagissent directement avec les classes Java de Tweety.

## Fichiers de Test

- **[`test_load_theory.py`](test_load_theory.py:1)**: Vérifie la capacité à démarrer la JVM, à instancier un parser logique de Tweety (`PlParser`) et à charger une base de connaissances à partir d'un fichier de théorie (`.lp`).

- **[`test_reasoner_query.py`](test_reasoner_query.py:1)**: Teste la capacité à construire une base de connaissances par programmation, à instancier un raisonneur (`SimplePlReasoner`) et à exécuter une requête simple pour vérifier si une formule est une conséquence logique de la base de connaissances.

- **[`test_list_models.py`](test_list_models.py:1)**: Valide la capacité à énumérer tous les modèles (c'est-à-dire les interprétations qui satisfont toutes les formules) d'une base de connaissances donnée, en utilisant un énumérateur de modèles de Tweety (`SimpleModelEnumerator`).

## Scripts et Données de Support

- **[`sample_theory.lp`](sample_theory.lp:1)**: Un petit fichier de théorie en logique propositionnelle utilisé par les tests pour le chargement.
- **`run_test_*.ps1`**: Des scripts PowerShell pour exécuter chaque test individuellement, utiles pour le débogage.
- **[`temp_minimal_jvm_test.py`](temp_minimal_jvm_test.py:1)**: Un fichier de test temporaire ou de brouillon pour des expériences rapides.

## Exécution

Ces tests nécessitent que la JVM soit démarrée avec le bon classpath pointant vers les fichiers JAR de Tweety. La fixture `integration_jvm` (définie dans `tests/conftest.py`) est responsable de la gestion du cycle de vie de la JVM pour ces tests.
