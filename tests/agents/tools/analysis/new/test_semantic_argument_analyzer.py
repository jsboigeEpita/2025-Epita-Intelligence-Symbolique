import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

import semantic_kernel as sk
from argumentation_analysis.agents.tools.analysis.new.semantic_argument_analyzer import (
    SemanticArgumentAnalyzer,
)
from argumentation_analysis.core.models.toulmin_model import (
    ToulminAnalysisResult,
    ToulminComponent,
)


# Fixture pour initialiser l'analyseur une seule fois pour tous les tests
@pytest.fixture
def analyzer():
    # On mock le Kernel pour ne pas dépendre du service externe
    with patch("semantic_kernel.Kernel") as mock_kernel_class:
        # On simule le comportement de la chaîne d'appel de semantic kernel
        mock_kernel_instance = MagicMock()
        mock_kernel_class.return_value = mock_kernel_instance

        # Le kernel est instancié dans le __init__, donc on doit patcher *avant* de créer l'analyseur
        analyzer_instance = SemanticArgumentAnalyzer()

        # On attache notre kernel mocké à l'instance pour les tests
        analyzer_instance.kernel = mock_kernel_instance
        yield analyzer_instance


@pytest.mark.asyncio
async def test_run_success_with_valid_json(analyzer: SemanticArgumentAnalyzer):
    """
    Test 1: Cas Nominal (Succès)
    Vérifie que l'analyseur parse correctement une réponse JSON valide du kernel.
    """
    # 1. Préparation des données de test (mock)
    mock_json_response = {
        "claim": {
            "text": "Le projet est un succès",
            "confidence_score": 0.95,
            "source_sentences": [0],
        },
        "data": [
            {
                "text": "Le code est bien testé",
                "confidence_score": 0.9,
                "source_sentences": [1],
            }
        ],
        "warrant": {
            "text": "Un code bien testé mène au succès",
            "confidence_score": 0.85,
            "source_sentences": [2],
        },
    }
    mock_json_string = json.dumps(mock_json_response)

    # 2. Configuration du mock du kernel
    # Simuler l'objet retourné par run_async pour avoir un attribut `result`
    mock_run_async_result = MagicMock()
    mock_run_async_result.result = mock_json_string

    # Configurer la méthode run_async du kernel pour retourner notre mock
    # Comme c'est une méthode asynchrone, on utilise AsyncMock pour la simuler
    analyzer.kernel.run_async = AsyncMock(return_value=mock_run_async_result)

    # 3. Exécution de la méthode à tester
    argument_text = "Le projet est un succès car le code est bien testé, et un code bien testé mène au succès."
    result = await analyzer.run(argument_text)

    # 4. Assertions
    assert isinstance(result, ToulminAnalysisResult)
    assert result.claim.text == "Le projet est un succès"
    assert result.claim.confidence_score == 0.95
    assert len(result.data) == 1
    assert result.data[0].text == "Le code est bien testé"
    assert result.warrant.text == "Un code bien testé mène au succès"

    # Vérifier que le kernel a bien été appelé
    analyzer.kernel.run_async.assert_called_once()


@pytest.mark.asyncio
async def test_run_handles_invalid_json(analyzer: SemanticArgumentAnalyzer):
    """
    Test 2: Gestion d'un JSON Invalide
    S'assure que l'analyseur lève une ValueError si le LLM retourne une chaîne non-JSON.
    """
    # 1. Préparation des données de test
    invalid_json_string = "Ceci n'est pas un JSON."

    # 2. Configuration du mock du kernel
    mock_run_async_result = MagicMock()
    mock_run_async_result.result = invalid_json_string
    analyzer.kernel.run_async = AsyncMock(return_value=mock_run_async_result)

    # 3. Exécution et Assertion
    with pytest.raises(ValueError, match="Failed to decode JSON from LLM result"):
        await analyzer.run("un argument quelconque")


@pytest.mark.asyncio
async def test_run_handles_unexpected_return_type(analyzer: SemanticArgumentAnalyzer):
    """
    Test 3: Gestion d'un Type de Retour Inattendu
    Valide la robustesse face à un type de retour imprévu du kernel.
    """
    # 1. Préparation des données de test
    unexpected_return = 12345  # Un entier au lieu d'une chaîne ou d'un dict

    # 2. Configuration du mock du kernel
    mock_run_async_result = MagicMock()
    mock_run_async_result.result = unexpected_return
    analyzer.kernel.run_async = AsyncMock(return_value=mock_run_async_result)

    # 3. Exécution et Assertion
    with pytest.raises(TypeError, match="Unexpected result type from kernel"):
        await analyzer.run("un autre argument")
