"""
Package `core` pour les agents d'analyse argumentative.

Ce package regroupe les composants fondamentaux et les implémentations de base
des agents utilisés dans le système. Il inclut :
- Des définitions abstraites pour les agents (`abc`).
- Des agents spécialisés pour l'extraction d'informations (`extract`).
- Des agents pour l'analyse informelle des arguments (`informal`).
- Des agents basés sur différentes logiques formelles (`logic`), tels que
  la logique propositionnelle, la logique du premier ordre et la logique modale.
- L'agent de synthèse unifié (`synthesis`) qui coordonne les analyses formelles et informelles.

Les importations des sous-modules sont gérées avec des blocs `try-except`
pour permettre une initialisation partielle en cas de dépendances manquantes
pour un sous-module spécifique.
"""

# Importations des sous-modules
try:
    from . import extract
except ImportError as e:
    import logging

    logging.warning(
        f"Le sous-module 'extract' de 'agents.core' n'a pas pu être importé: {e}"
    )

try:
    from . import informal
except ImportError as e:
    import logging

    logging.warning(
        f"Le sous-module 'informal' de 'agents.core' n'a pas pu être importé: {e}"
    )

try:
    from . import logic
except ImportError as e:
    import logging

    logging.warning(
        f"Le sous-module 'logic' de 'agents.core' n'a pas pu être importé: {e}"
    )

try:
    from . import pl
except ImportError as e:
    import logging

    logging.warning(
        f"Le sous-module 'pl' de 'agents.core' n'a pas pu être importé: {e}"
    )

try:
    from . import pm
except ImportError as e:
    import logging

    logging.warning(
        f"Le sous-module 'pm' de 'agents.core' n'a pas pu être importé: {e}"
    )

try:
    from . import synthesis
except ImportError as e:
    import logging

    logging.warning(
        f"Le sous-module 'synthesis' de 'agents.core' n'a pas pu être importé: {e}"
    )
