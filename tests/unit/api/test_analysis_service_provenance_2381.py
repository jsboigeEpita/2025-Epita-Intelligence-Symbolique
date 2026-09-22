"""#2381 — la réponse HTTP ne nomme un modèle que si l'analyse en a servi un.

`api/dependencies.py` annonçait `"model_used": "gpt-5.6-luna"` (chemin
authentique) et `"gpt-5.6-luna-mock"` (mode mock) dans des littéraux — la même
fabrication de provenance que #2377, hors du périmètre de sa garde. Le chemin
authentique **observe** désormais le modèle servi depuis le résultat du
``OrchestrationServiceManager`` (le chemin hiérarchique y porte ``model``
depuis #2377) ; le mode mock n'annonce rien — aucun service n'a été consulté.

Sur ``main`` d'avant réparation, chaque test de divergence échoue **en
valeur** : le littéral au lieu de l'observé, la clé présente au lieu
d'absente. Le manager est doublé — aucun egress.
"""

import asyncio
from typing import Any, Dict

from api.dependencies import AnalysisService, MockAnalysisService


class _ManagerDouble:
    """Double du OrchestrationServiceManager — rend un résultat figé."""

    def __init__(self, service_result: Dict[str, Any]):
        self._result = service_result

    async def analyze_text(self, text: str) -> Dict[str, Any]:
        return self._result


def _authentic(manager_result: Dict[str, Any]) -> Dict[str, Any]:
    """Appelle le chemin authentique sous un résultat de manager donné."""
    service = AnalysisService(manager=_ManagerDouble(manager_result))  # type: ignore[arg-type]
    return asyncio.run(service.analyze_text("Un argument quelconque."))


def test_authentic_path_observes_the_served_model():
    """Le chemin authentique rend le modèle que le manager a servi.

    Avant réparation : ``model_used == "gpt-5.6-luna"`` — le littéral, pas
    l'observé.
    """
    result = _authentic(
        {
            "results": {
                "hierarchical": {"model": "mock_served_model", "status": "completed"}
            }
        }
    )

    assert (
        result["analysis_metadata"]["model_used"] == "mock_served_model"
    ), f"provenance non observée: {result['analysis_metadata']!r}"


def test_authentic_path_without_served_model_announces_nothing():
    """Pas de modèle servi ⇒ pas de clé ``model_used`` (jamais un littéral).

    Avant réparation : la clé portait le littéral même sans modèle servi.
    """
    result = _authentic({"results": {"hierarchical": {"status": "completed"}}})

    assert (
        "model_used" not in result["analysis_metadata"]
    ), f"une provenance est annoncée sans modèle servi: {result['analysis_metadata']!r}"


def test_mock_path_announces_no_model():
    """Le mode mock n'a consulté aucun service — il ne nomme aucun modèle.

    Avant réparation : ``model_used == "gpt-5.6-luna-mock"``.
    """
    result = asyncio.run(MockAnalysisService().analyze_text("un texte"))

    assert (
        "model_used" not in result["analysis_metadata"]
    ), f"le mock annonce un modèle qu'il n'a pas consulté: {result['analysis_metadata']!r}"
    assert result["analysis_metadata"][
        "fallback_reason"
    ], "le mode doit rester documenté"
