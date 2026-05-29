import warnings

# L'import en étoile est intentionnel ici pour la compatibilité ascendante.
from argumentation_analysis.core.utils import *

warnings.warn(
    "Le paquet 'argumentation_analysis.utils.core_utils' est déprécié. "
    "Veuillez utiliser 'argumentation_analysis.core.utils' à la place.",
    DeprecationWarning,
    stacklevel=2,
)
