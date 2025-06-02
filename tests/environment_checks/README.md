# Tests de Vérification de l'Environnement

Ce répertoire contient des tests conçus pour vérifier la configuration de base de l'environnement de développement et de test. Ces tests s'assurent notamment que les dépendances critiques du projet sont correctement installées et importables.

Tests inclus :
- [`test_core_dependencies.py`](test_core_dependencies.py:1): Vérifie l'importation de toutes les dépendances majeures du projet, y compris JPype, NumPy, Pandas, SciPy, Scikit-learn, NLTK, SpaCy, PyTorch, Transformers, Pydantic, Requests, Matplotlib, Seaborn, NetworkX, python-dotenv, Semantic Kernel, Pytest, Coverage.py, et Cryptography.
- [`test_project_module_imports.py`](test_project_module_imports.py:1): Vérifie l'importation des modules internes clés du projet `argumentation_analysis` ainsi que certaines dépendances externes critiques pour leur fonctionnement.
- [`test_pythonpath.py`](test_pythonpath.py:1): S'assure que le PYTHONPATH est configuré de manière à ce que les modules du projet soient correctement accessibles, en particulier pour les exécutions hors IDE (ex: en ligne de commande, scripts).