# Tests de Vérification de l'Environnement

Ce répertoire contient des tests conçus pour vérifier la configuration de base de l'environnement de développement et de test. Ces tests s'assurent notamment que les dépendances critiques du projet sont correctement installées et importables.

Tests inclus :
- [`test_core_dependencies.py`](test_core_dependencies.py:1): Vérifie l'importation des bibliothèques Python essentielles (JPype, NumPy, PyTorch, Transformers, NetworkX).
- [`test_project_module_imports.py`](test_project_module_imports.py:1): Vérifie l'importation des modules internes clés du projet `argumentation_analysis` ainsi que certaines dépendances externes critiques pour leur fonctionnement.