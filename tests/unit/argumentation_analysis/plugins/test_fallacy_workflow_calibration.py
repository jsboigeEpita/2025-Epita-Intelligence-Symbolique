# -*- coding: utf-8 -*-
"""
Tests de calibration pour Issue #259.

Valide que le workflow hiérarchique détecte les sophismes attendus.
"""

import pytest
import sys
import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from semantic_kernel.kernel import Kernel

# Ajout pour forcer la reconnaissance du package principal
current_script_path = Path(__file__).resolve()
project_root_for_test = current_script_path.parents[4]
sys.path.insert(0, str(project_root_for_test))

from argumentation_analysis.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin
from tests.fixtures.calibrated_fallacy_texts import (
    CALIBRATED_TEXT_8_FALLACIES,
    EXPECTED_FALLACIES_8,
    EPITA_TEXT,
    EXPECTED_FALLACIES_EPITA,
    NEUTRAL_TEXT,
    EXPECTED_FALLACIES_NEUTRAL,
)


class TestFallacyWorkflowCalibration:
    """Tests de calibration du workflow hiérarchique (Issue #259)."""

    @pytest.fixture
    def workflow_plugin(self, mock_llm_service, mock_kernel):
        """Crée une instance du plugin avec des mocks."""
        from unittest.mock import MagicMock
        from semantic_kernel.kernel import Kernel

        taxonomy_path = Path(project_root_for_test) / "argumentation_analysis" / "data" / "taxonomy_medium.csv"

        # Create a real Kernel instance with mocked service
        kernel = Kernel()
        kernel.add_service(mock_llm_service)

        return FallacyWorkflowPlugin(
            master_kernel=kernel,
            llm_service=mock_llm_service,
            taxonomy_file_path=str(taxonomy_path) if taxonomy_path.exists() else None,
        )

    def test_calibrated_text_8_fallacies(self, workflow_plugin):
        """
        Test que le workflow détecte au moins 5 des 8 sophismes plantés.

        Critères de succès Issue #259:
        - ≥ 5/8 sur texte calibré
        """
        import asyncio

        result_json = asyncio.run(workflow_plugin.run_guided_analysis(CALIBRATED_TEXT_8_FALLACIES))

        import json
        result = json.loads(result_json)

        detected_names = [f.get("fallacy_type", "").lower() for f in result.get("fallacies", [])]

        # Vérifier qu'on a au moins 5 détections
        assert len(result.get("fallacies", [])) >= 5, (
            f"Expected ≥ 5 fallacies, got {len(result.get('fallacies', []))}: "
            f"{detected_names}"
        )

        # Vérifier que les détections correspondent aux attentes
        expected_names = [e["name"].lower() for e in EXPECTED_FALLACIES_8]
        matched = sum(1 for d in detected_names if any(e in d for e in expected_names))

        assert matched >= 5, (
            f"Expected ≥ 5 matched fallacies, got {matched}. "
            f"Detected: {detected_names}, Expected: {expected_names}"
        )

    def test_epita_text_2_fallacies(self, workflow_plugin):
        """
        Test que le workflow détecte les 2 sophismes du texte EPITA.

        Critères de succès Issue #259:
        - ≥ 2/2 sur texte EPITA (appel à l'autorité + ad hominem)
        """
        import asyncio

        result_json = asyncio.run(workflow_plugin.run_guided_analysis(EPITA_TEXT))

        import json
        result = json.loads(result_json)

        detected_names = [f.get("fallacy_type", "").lower() for f in result.get("fallacies", [])]

        # Vérifier qu'on a au moins 2 détections
        assert len(result.get("fallacies", [])) >= 2, (
            f"Expected ≥ 2 fallacies, got {len(result.get('fallacies', []))}: "
            f"{detected_names}"
        )

        # Vérifier appel à l'autorité
        has_authority = any("autorité" in d or "authority" in d for d in detected_names)
        assert has_authority, f"Expected 'appel à l'autorité', got: {detected_names}"

        # Vérifier ad hominem
        has_ad_hominem = any("hominem" in d or "attaque" in d for d in detected_names)
        assert has_ad_hominem, f"Expected 'ad hominem', got: {detected_names}"

    def test_neutral_text_no_falsecies(self, workflow_plugin):
        """
        Test que le workflow ne'a pas de faux positifs sur un texte neutre.
        """
        import asyncio

        result_json = asyncio.run(workflow_plugin.run_guided_analysis(NEUTRAL_TEXT))

        import json
        result = json.loads(result_json)

        # Le texte neutre ne devrait PAS contenir de sophismes
        # Ou au pire, un seul avec très faible confiance
        fallacies = result.get("fallacies", [])

        if fallacies:
            # Si des sophismes sont détectés, ils doivent avoir une faible confiance
            for f in fallacies:
                confidence = f.get("confidence", 1.0)
                assert confidence < 0.5, (
                    f"False positive detected with high confidence: {f}"
                )


# Fixtures mock
@pytest.fixture
def mock_kernel():
    """Mock du kernel Semantic Kernel."""
    from unittest.mock import MagicMock
    kernel = MagicMock()
    return kernel


@pytest.fixture
def mock_llm_service():
    """Mock du service LLM pour les tests de calibration.

    Ce mock simuleule un LLM qui explore correctement les branches.
    """
    from unittest.mock import MagicMock, AsyncMock
    from semantic_kernel.contents import ChatMessageContent, FunctionCallContent

    service = MagicMock()
    service.service_id = "mock-llm-service"

    # Simulate responses that explore branches
    call_count = [0]

    async def mock_get_chat_message_contents(chat_history, settings, kernel, **kwargs):
        call_count[0] += 1

        # Return a mock response with function calls
        mock_msg = MagicMock(spec=ChatMessageContent)
        mock_msg.items = []

        # Only add function calls for first few calls (Phase 1: branch selection)
        if call_count[0] <= 2:
            # Simulate explore_branch calls
            mock_call = MagicMock(spec=FunctionCallContent)
            mock_call.name = "Exploration-explore_branch"
            mock_call.arguments = {"node_pk": "relevance"}
            mock_msg.items = [mock_call]

        return [mock_msg]

    service.get_chat_message_contents = mock_get_chat_message_contents

    return service
