"""
Package principal `argumentation_analysis`.

Ce package fournit un ensemble complet d'outils, d'agents et de pipelines
pour effectuer une analyse approfondie de l'argumentation dans divers types
de textes. Il intègre des capacités de traitement du langage naturel (NLP),
d'interaction avec des modèles de langage à grande échelle (LLM), de raisonnement
logique formel (via TweetyProject et JPype), et d'analyse informelle des arguments.

Fonctionnalités clés :
- Extraction et structuration d'arguments à partir de textes.
- Analyse de la validité logique et détection de sophismes formels.
- Identification et analyse de sophismes informels et de stratégies rhétoriques.
- Orchestration de workflows d'analyse complexes impliquant plusieurs agents.
- Génération de rapports et de visualisations des résultats d'analyse.
- Gestion de la configuration, des services dépendants (JVM, LLM), et des données.

Sous-packages principaux :
- `agents`: Contient les implémentations des différents agents spécialisés (extraction, logique, informel).
- `analytics`: Modules pour les calculs statistiques et l'analyse quantitative de texte.
- `config`: Gestion de la configuration du package et des services externes. (À vérifier si existant)
- `core`: Composants centraux, y compris l'intégration LLM, la gestion de la JVM, et les bases des agents.
- `data`: Gestion des jeux de données, taxonomies, et autres ressources. (À vérifier si existant)
- `models`: Définitions de modèles de données (Pydantic, etc.) utilisés à travers le package.
- `nlp`: Utilitaires spécifiques au traitement du langage naturel (ex: embeddings, tokenisation).
- `orchestration`: Modules pour la coordination et l'exécution de séquences d'analyse complexes.
- `pipelines`: Pipelines préconfigurés pour des tâches d'analyse de bout en bout.
- `reporting`: Outils pour la génération de rapports et la visualisation des résultats.
- `scripts`: Scripts utilitaires ou d'exécution pour des tâches spécifiques.
- `services`: Clients et interfaces pour interagir avec des services externes (ex: API web, cache).
- `service_setup`: Logique pour la configuration et l'initialisation des services.
- `ui`: Composants liés à l'interface utilisateur (si applicable).
- `utils`: Fonctions utilitaires générales partagées à travers le package.

Ce `__init__.py` sert principalement à marquer le répertoire comme un package Python
et peut être utilisé pour exposer une API publique simplifiée si nécessaire.
"""

# Initializer for the argumentation_analysis package

# Exposer sélectivement les composants clés si nécessaire
# from .some_module import SomeClass
# from .agents import SpecificAgent

__all__ = [
    # "SomeClass",
    # "SpecificAgent",
    "agents",
    "analytics",
    "core",
    "models",
    "nlp",
    "orchestration",
    "pipelines",
    "reporting",
    "scripts",
    "services",
    "service_setup",
    "ui",
    "utils",
]

# Log de chargement du package principal
import logging
logger = logging.getLogger(__name__)
logger.info("Package 'argumentation_analysis' chargé.")