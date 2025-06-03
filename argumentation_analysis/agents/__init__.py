"""
Package `agents` pour le système d'analyse argumentative.

Ce package est le conteneur principal pour tous les agents spécialisés
utilisés dans l'application. Il organise les agents en sous-packages
basés sur leur fonctionnalité principale, notamment :
    - `core`: Contient les classes de base abstraites et les agents
              fondamentaux (extraction, logique formelle, analyse informelle).
    - `tools`: Pourrait contenir des agents ou des plugins agissant comme des outils
               spécifiques (par exemple, analyse de sentiment, vérification de faits).
               (Note: ce sous-package n'est pas explicitement importé ici mais
               fait partie de la structure typique d'un tel système).

L'objectif est de fournir une structure modulaire pour faciliter le développement,
la maintenance et l'extension des capacités agentiques du système.
"""

# Importations des sous-modules principaux pour qu'ils soient reconnus
# dans le package 'agents'.
try:
    from . import core
    # L'import de 'argumentation_analysis.core' était potentiellement une erreur
    # ou une ancienne structure. Si 'core' est un sous-module de 'agents',
    # l'importation correcte est 'from . import core'.

    # Si des agents spécifiques doivent être directement accessibles via 'agents.SpecificAgent',
    # ils seraient importés ici depuis leurs modules respectifs.
    # Exemple :
    # from .core.extract.extract_agent import ExtractAgent
    # from .core.logic.propositional_logic_agent import PropositionalLogicAgent

    __all__ = [
        "core",
        # "ExtractAgent", # Si exposé directement
        # "PropositionalLogicAgent", # Si exposé directement
    ]

except ImportError as e:
    import logging
    logging.warning(f"Un sous-module de 'agents' n'a pas pu être importé: {e}")
    __all__ = []

# Note: Le commentaire sur 'extract' étant un vrai module est pertinent
# et reflète une évolution de la structure.