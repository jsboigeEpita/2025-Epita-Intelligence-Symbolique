"""
Package `service_setup` pour la configuration et l'initialisation des services.

Ce package est responsable de la mise en place et de l'initialisation des
services et composants majeurs requis par l'application d'analyse d'argumentation.
Cela inclut typiquement :
    - La configuration et l'instanciation des services de modèles de langage (LLM).
    - L'initialisation et la gestion de la Machine Virtuelle Java (JVM) pour
      l'interaction avec des bibliothèques Java comme TweetyProject.
    - La configuration d'autres services externes ou partagés.

Modules clés :
    - `analysis_services`: Contient les fonctions pour initialiser les services
                           nécessaires à l'analyse.
"""

# Exposer les fonctions ou classes importantes si nécessaire
# from .analysis_services import initialize_all_services

__all__ = [
    # "initialize_all_services",
]

import logging

logger = logging.getLogger(__name__)
logger.info("Package 'argumentation_analysis.service_setup' chargé.")
