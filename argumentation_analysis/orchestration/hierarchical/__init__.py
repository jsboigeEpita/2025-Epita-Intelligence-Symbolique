"""
Module d'orchestration hiérarchique à trois niveaux pour le système d'analyse rhétorique.

Ce module implémente une architecture hiérarchique à trois niveaux (stratégique, tactique, opérationnel)
pour améliorer la scalabilité, la modularité et l'efficacité du système d'analyse rhétorique.

L'architecture est structurée comme suit:
- Niveau stratégique: Responsable de la planification globale et de la définition des objectifs
- Niveau tactique: Responsable de la coordination et de la décomposition des objectifs en tâches
- Niveau opérationnel: Responsable de l'exécution des tâches spécifiques d'analyse
"""

# Imports des modules hiérarchiques
try:
    from . import strategic
    from . import tactical
    from . import operational
    from . import interfaces
    from . import templates
except ImportError as e:
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(f"Erreur d'import dans le module hiérarchique: {e}")

# Exposition des modules principaux
__all__ = ["strategic", "tactical", "operational", "interfaces", "templates"]
