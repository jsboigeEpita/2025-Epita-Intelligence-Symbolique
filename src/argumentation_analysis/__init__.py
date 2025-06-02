"""
Package `argumentation_analysis`.

Ce package fournit les outils et pipelines nécessaires pour effectuer une analyse
approfondie de l'argumentation dans des textes. Il comprend des modules pour :
- Le traitement et la préparation des données textuelles.
- L'intégration avec des modèles de langage (LLM) pour l'analyse sémantique et rhétorique.
- L'interaction avec des systèmes de logique formelle (via JVM et TweetyProject) pour
  l'évaluation de la cohérence et la détection de sophismes.
- La génération d'embeddings de texte.
- Le calcul de statistiques et la génération de rapports d'analyse.
- La configuration et l'initialisation des services dépendants.

Sous-packages principaux :
- `analytics`: Modules pour les calculs statistiques et l'analyse de texte.
- `core`: Composants centraux comme l'intégration LLM et la gestion JVM.
- `nlp`: Utilitaires pour le traitement du langage naturel (ex: embeddings).
- `orchestration`: Modules pour orchestrer des séquences d'analyse complexes.
- `pipelines`: Pipelines complets pour des tâches d'analyse spécifiques (ex: génération de rapports).
- `service_setup`: Configuration et initialisation des services.
- `ui`: Composants liés à l'interface utilisateur (si applicable).
- `utils`: Fonctions utilitaires générales pour le package.
"""

# Initializer for the argumentation_analysis package