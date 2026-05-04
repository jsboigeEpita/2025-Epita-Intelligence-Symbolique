# Tests de Vérification de l'Environnement

Ce répertoire contient des tests conçus pour vérifier la configuration de l'environnement de développement et s'assurer que toutes les dépendances et configurations de chemin sont correctes. Ces tests sont cruciaux pour diagnostiquer rapidement les problèmes de setup.

## Objectif des Tests

L'objectif principal est de valider que l'environnement d'exécution est sain avant de lancer la suite de tests complète. Cela inclut :
- La vérification de la présence et de l'importabilité de toutes les dépendances externes majeures.
- La validation que les modules internes du projet sont accessibles, ce qui confirme une configuration correcte du `PYTHONPATH`.

## Fichiers de Test

- **[`test_core_dependencies.py`](test_core_dependencies.py:1)**: Ce test s'assure que toutes les bibliothèques tierces essentielles (comme `jpype`, `numpy`, `torch`, `transformers`, `semantic_kernel`, etc.) peuvent être importées sans erreur. Il est paramétré pour couvrir une liste exhaustive de dépendances.

- **[`test_project_module_imports.py`](test_project_module_imports.py:1)**: Ce test tente d'importer une liste de modules clés du projet `argumentation_analysis`. Un succès à ce test indique que le `PYTHONPATH` est correctement configuré pour que les modules internes puissent se trouver les uns les autres.

- **[`test_pythonpath.py`](test_pythonpath.py:1)**: Il s'agit plus d'un script de diagnostic que d'un test formel. Il affiche le contenu actuel de `sys.path` (le `PYTHONPATH`) et tente d'importer le module racine du projet. Il est utile pour le débogage manuel des problèmes de chemin.

## Utilisation

Ces tests sont généralement exécutés au début d'une session de développement ou d'intégration continue pour garantir que l'environnement est prêt. Ils permettent d'éviter des erreurs d'importation obscures dans les tests unitaires ou fonctionnels plus complexes.