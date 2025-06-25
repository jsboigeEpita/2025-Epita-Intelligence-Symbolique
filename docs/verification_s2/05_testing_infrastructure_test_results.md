# Rapport de Test - Système 5 : Infrastructure de Test

## 1. Résumé de l'Intervention

La campagne de test initialement prévue pour le système "Infrastructure de Test" a rapidement mis en évidence des instabilités critiques au sein de la suite de tests `e2e-python`. Plutôt que de produire un simple rapport d'erreurs face à des échecs non déterministes, il est devenu évident qu'une intervention de fond était nécessaire pour garantir la fiabilité de l'infrastructure de test elle-même. Ce document retrace les problèmes identifiés et les solutions apportées.

## 2. Problèmes Identifiés

### Problème Principal : Conflit de Boucle d'Événements `asyncio`

Le cœur du problème résidait dans un conflit technique entre deux composants asynchrones majeurs :
1.  **Playwright :** Utilisé par l'orchestrateur de l'application pour lancer et gérer les navigateurs et services web.
2.  **`pytest-asyncio` :** Le plugin `pytest` utilisé pour exécuter les tests asynchrones.

Les deux systèmes tentaient de gérer leur propre boucle d'événements `asyncio`, créant une condition de concurrence. Cette situation rendait impossible pour les scripts de test `pytest` de communiquer de manière fiable avec les services web démarrés par l'orchestrateur. La conséquence directe était une incapacité à récupérer les URLs des services, menant à des timeouts et des échecs de tests aléatoires et non reproductibles.

### Problèmes Secondaires

En parallèle de ce problème majeur, l'analyse a révélé d'autres anomalies :
*   **Erreurs dans les Appels API :** Certains tests contenaient des appels API mal formés ou obsolètes.
*   **Conflits de `Fixtures` :** Des `fixtures` `pytest` étaient mal définies, provoquant des conflits de dépendances.
*   **Chargement de Plugins :** Le chargement de certains plugins `pytest` n'était pas correctement configuré, ajoutant à l'instabilité générale.

## 3. Corrections Appliquées

### Solution Principale : Contrat de Communication par Fichier

Pour résoudre le conflit `asyncio`, l'approche consistant à analyser le `stdout` de l'orchestrateur pour en extraire les URLs a été abandonnée. Elle a été remplacée par un **contrat de communication basé sur un fichier intermédiaire**.

Le nouveau mécanisme fonctionne comme suit :
1.  L'orchestrateur, après avoir démarré les services web, écrit leurs URLs respectives dans un fichier `JSON` standardisé : `_temp/service_urls.json`.
2.  Le script `run_tests.ps1`, qui pilote l'exécution, attend que ce fichier soit créé.
3.  Une fois le fichier disponible, `run_tests.ps1` le lit, récupère les URLs et les transmet comme variables d'environnement aux tests `pytest`.

Cette approche découple complètement les deux processus asynchrones, garantissant que les tests disposent d'informations stables et fiables avant même de commencer leur exécution.

### Corrections Additionnelles

*   Les tests individuels ont été revus et corrigés pour utiliser les bonnes signatures d'API.
*   Le fichier `tests/conftest.py` a été ajusté pour optimiser la gestion des `fixtures` et le chargement des plugins.

## 4. Statut Final des Tests

Suite à l'application de ces corrections, l'ensemble des suites de tests critiques, y compris et surtout la suite `e2e-python`, s'exécute désormais de manière stable et réussie. L'infrastructure de test est considérée comme fiable et robuste.