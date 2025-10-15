import logging
import sys
from unittest.mock import MagicMock

# from itertools import chain, combinations # Supprimé car la logique de calcul d'extension est retirée

# Importations relatives
from . import types  # MockJavaCollection est maintenant dans types.py
from .jclass_core import MockJClassCore

# Pour éviter une dépendance circulaire immédiate avec jpype_mock pour JClass,
# on va supposer que JClass("java.util.HashSet") est passé ou accessible.
# Pour l'instant, on va le définir localement ou le passer en argument.

# Configuration du logging pour ce module
mock_logger = logging.getLogger(__name__)
if not mock_logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[MOCK JPYPE TWEETY_REASONERS LOG] %(asctime)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    mock_logger.addHandler(handler)
mock_logger.setLevel(logging.DEBUG)

# --- Helpers de sémantique d'argumentation (SUPPRIMÉS) ---
# La logique de calcul des extensions est retirée conformément au plan de refactoring.
# Les mocks ne réimplémentent plus la logique interne de Tweety.
# Les tests doivent utiliser les vraies classes Java via jpype.JClass.

# --- Configuration functions for specific reasoners ---


def configure_complete_reasoner_mock(
    reasoner_instance_mock, dung_theory_instance, JClass_provider
):
    """
    Configure le mock pour CompleteReasoner.
    JClass_provider est une fonction (comme le JClass global) qui peut créer des JClass mocks.
    """
    mock_logger.debug(
        f"[CONFIGURE CompleteReasoner] pour {reasoner_instance_mock} avec théorie {dung_theory_instance}"
    )
    models_coll = reasoner_instance_mock._collections.get("models")
    if models_coll is None:
        mock_logger.error(
            "[CONFIGURE CompleteReasoner] _collections['models'] non trouvée sur l'instance du reasoner."
        )
        reasoner_instance_mock._collections["models"] = []  # Initialiser si manquant
        models_coll = reasoner_instance_mock._collections["models"]

    models_coll.clear()  # Vider les modèles précédents

    # Simplification: Ne plus calculer d'extensions.
    mock_logger.info(
        f"[CONFIGURE CompleteReasoner] Configuration simplifiée. Les calculs d'extensions sont retirés."
    )


def configure_stable_reasoner_mock(
    reasoner_instance_mock, dung_theory_instance, JClass_provider
):
    mock_logger.debug(
        f"[CONFIGURE StableReasoner] pour {reasoner_instance_mock} avec théorie {dung_theory_instance}"
    )
    models_coll = reasoner_instance_mock._collections.get("models")
    if models_coll is None:
        mock_logger.error(
            "[CONFIGURE StableReasoner] _collections['models'] non trouvée."
        )
        reasoner_instance_mock._collections["models"] = []
        models_coll = reasoner_instance_mock._collections["models"]
    models_coll.clear()

    # Simplification: Ne plus calculer d'extensions.
    mock_logger.info(
        f"[CONFIGURE StableReasoner] Configuration simplifiée. Les calculs d'extensions sont retirés."
    )


def configure_preferred_reasoner_mock(
    reasoner_instance_mock, dung_theory_instance, JClass_provider
):
    mock_logger.debug(
        f"[CONFIGURE SimplePreferredReasoner] pour {reasoner_instance_mock} avec théorie {dung_theory_instance}"
    )
    models_coll = reasoner_instance_mock._collections.get("models")
    if models_coll is None:
        mock_logger.error(
            "[CONFIGURE SimplePreferredReasoner] _collections['models'] non trouvée."
        )
        reasoner_instance_mock._collections["models"] = []
        models_coll = reasoner_instance_mock._collections["models"]
    models_coll.clear()

    mock_logger.info(
        f"[CONFIGURE SimplePreferredReasoner] Configuration simplifiée pour {reasoner_instance_mock} avec théorie {dung_theory_instance}. Les calculs d'extensions sont retirés."
    )


def configure_grounded_reasoner_mock(
    reasoner_instance_mock, dung_theory_instance, JClass_provider
):
    mock_logger.debug(
        f"[CONFIGURE GroundedReasoner] pour {reasoner_instance_mock} avec théorie {dung_theory_instance}"
    )
    models_coll = reasoner_instance_mock._collections.get("models")
    if models_coll is None:
        mock_logger.error(
            "[CONFIGURE GroundedReasoner] _collections['models'] non trouvée."
        )
        reasoner_instance_mock._collections["models"] = []
        models_coll = reasoner_instance_mock._collections["models"]
    models_coll.clear()

    mock_logger.info(
        f"[CONFIGURE GroundedReasoner] Configuration simplifiée pour {reasoner_instance_mock} avec théorie {dung_theory_instance}. Les calculs d'extensions sont retirés."
    )

    if hasattr(reasoner_instance_mock, "getModel"):
        empty_model = MagicMock(spec=types.MockJavaCollection)
        empty_model.size = MagicMock(return_value=0)
        empty_model.isEmpty = MagicMock(return_value=True)
        empty_model.iterator = MagicMock(return_value=iter([]))
        reasoner_instance_mock.getModel.return_value = empty_model
        mock_logger.debug(
            f"[CONFIGURE GroundedReasoner] getModel() configuré pour retourner un mock d'ensemble vide/simple."
        )


mock_logger.info("Module jpype_components.tweety_reasoners initialisé.")
