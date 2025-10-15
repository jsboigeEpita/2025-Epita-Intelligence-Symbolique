"""
Tests de contrat pour les modèles Pydantic de l'OrchestrationService.

Ce module garantit la stabilité des interfaces de données (contrats) utilisées
pour la communication avec le service d'orchestration. En validant la structure,
les types et les contraintes des modèles de requête et de réponse, ces tests
agissent comme un garde-fou contre les changements cassants et assurent
une communication inter-services fiable.
"""
import pytest
from pydantic import ValidationError

from src.core.contracts import OrchestrationRequest, OrchestrationResponse


def test_valid_request_creation():
    """
    Vérifie que le modèle OrchestrationRequest peut être instancié avec des données valides.
    """
    valid_data = {
        "mode": "direct_plugin_call",
        "target": "test_plugin.test_capability",
        "payload": {"arg1": "value1", "arg2": 123},
    }
    request = OrchestrationRequest(**valid_data)
    assert request.mode == "direct_plugin_call"
    assert request.target == "test_plugin.test_capability"
    assert request.payload == {"arg1": "value1", "arg2": 123}
    assert request.session_id is None


def test_invalid_request_raises_error():
    """
    Vérifie que le modèle OrchestrationRequest lève une ValidationError pour des données invalides.
    """
    # Cas 1: Mode invalide
    with pytest.raises(ValidationError):
        OrchestrationRequest(mode="invalid_mode", target="t", payload={})

    # Cas 2: Cible manquante
    with pytest.raises(ValidationError):
        OrchestrationRequest(mode="direct_plugin_call", payload={})

    # Cas 3: Payload n'est pas un dictionnaire
    with pytest.raises(ValidationError):
        OrchestrationRequest(
            mode="direct_plugin_call", target="t", payload="not_a_dict"
        )


def test_valid_success_response():
    """
    Vérifie que le modèle OrchestrationResponse peut être instancié pour un cas de succès.
    """
    response_data = {"status": "success", "result": {"data": "some_result"}}
    response = OrchestrationResponse(**response_data)
    assert response.status == "success"
    assert response.result == {"data": "some_result"}
    assert response.error_message is None


def test_valid_error_response():
    """
    Vérifie que le modèle OrchestrationResponse peut être instancié pour un cas d'échec.
    """
    response_data = {"status": "error", "error_message": "Something went wrong"}
    response = OrchestrationResponse(**response_data)
    assert response.status == "error"
    assert response.result is None
    assert response.error_message == "Something went wrong"
