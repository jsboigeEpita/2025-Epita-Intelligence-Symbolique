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
        Test que le workflow detecte des sophismes diversifies sur texte calibre.

        Avec le mock LLM, 3 branches sont explorees et confirment:
        - Appel a l'emotion (PK=299), Ad hominem (PK=1360),
          Generalisation abusive (PK=595)

        Critères de succès Issue #259 (adapté au mock):
        - ≥ 3 fallacies detectees via le workflow
        - Au moins 2 noms differents (diversite)
        - Exploration methode = iterative_deepening (pas fallback)
        """
        import asyncio

        result_json = asyncio.run(workflow_plugin.run_guided_analysis(CALIBRATED_TEXT_8_FALLACIES))

        import json
        result = json.loads(result_json)

        detected_names = [f.get("fallacy_type", "").lower() for f in result.get("fallacies", [])]

        # Vérifier qu'on a au moins 3 détections (3 branches mockees)
        assert len(result.get("fallacies", [])) >= 3, (
            f"Expected ≥ 3 fallacies, got {len(result.get('fallacies', []))}: "
            f"{detected_names}"
        )

        # Vérifier la diversité (au moins 2 noms différents)
        unique_names = set(detected_names)
        assert len(unique_names) >= 2, (
            f"Expected ≥ 2 different fallacy types, got {len(unique_names)}: "
            f"{detected_names}"
        )

        # Vérifier que l'exploration s'est faite via iterative_deepening
        assert result.get("exploration_method") == "iterative_deepening", (
            f"Expected iterative_deepening, got {result.get('exploration_method')}"
        )

        # Vérifier que les branches explorées correspondent aux PK mockés
        assert result.get("branches_explored") >= 2, (
            f"Expected ≥ 2 branches explored, got {result.get('branches_explored')}"
        )

    def test_epita_text_2_fallacies(self, workflow_plugin):
        """
        Test que le workflow détecte les 2 sophismes du texte EPITA.

        Avec le mock LLM, les branches Influence (175) et Obstruction (1280)
        sont explorees et confirment Ad hominem (PK=1360).

        Critères de succès Issue #259 (adapté au mock):
        - ≥ 2 fallacies detectees via le workflow
        - Au moins une contient "ad hominem"
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

        # Vérifier ad hominem (present dans la taxonomy medium)
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

    Simule un LLM qui navigue la taxonomy de facon realiste:
    - Phase 1: selectionne 3 branches (Influence, Obstruction, Erreur mathematique)
    - Phase 2: chaque branche confirme un sophisme different selon le prompt
    - Texte neutre: conclude_no_fallacy sur toutes les branches
    - One-shot fallback: retourne un JSON valide
    """
    from unittest.mock import MagicMock, AsyncMock
    from semantic_kernel.contents import ChatMessageContent, FunctionCallContent

    service = MagicMock()
    service.service_id = "mock-llm-service"

    call_count = [0]

    def _make_function_call(name, arguments):
        """Helper to create a mock FunctionCallContent."""
        mock_call = MagicMock(spec=FunctionCallContent)
        mock_call.name = name
        mock_call.id = f"call_{call_count[0]}"
        mock_call.arguments = arguments
        return mock_call

    def _is_neutral_text(chat_history):
        """Detect if the analyzed text is the neutral one."""
        for msg in chat_history.messages:
            content = str(getattr(msg, 'content', '') or '')
            if 'photosynthèse' in content.lower() or 'chloroplastes' in content.lower():
                return True
        return False

    def _detect_branch_from_prompt(chat_history):
        """Detect which taxonomy branch the LLM is currently exploring."""
        for msg in chat_history.messages:
            content = str(getattr(msg, 'content', '') or '')
            # The iterative deepening prompt includes "Current position: <name>"
            if 'Influence' in content:
                return "175"
            if 'Obstruction' in content:
                return "1280"
            if 'Erreur math' in content:
                return "594"
        return None

    # Map branch -> child leaf to confirm (depth=2 leaves under each family)
    _BRANCH_CONFIRMATIONS = {
        "175": {"node_pk": "299", "justification": "Appel a l'emotion detecte"},      # Influence -> Appel à l'émotion
        "1280": {"node_pk": "1360", "justification": "Ad hominem detecte"},           # Obstruction -> Ad hominem
        "594": {"node_pk": "595", "justification": "Generalisation abusive detectee"}, # Erreur math -> Généralisation abusive
    }

    async def mock_get_chat_message_contents(chat_history, settings, kernel, **kwargs):
        call_count[0] += 1
        mock_msg = MagicMock(spec=ChatMessageContent)
        mock_msg.items = []

        is_neutral = _is_neutral_text(chat_history)

        # Phase 1 (call 1): Root selection — pick 3 depth=1 families
        if call_count[0] == 1:
            mock_msg.items = [
                _make_function_call("Exploration-explore_branch", {"node_pk": "175"}),
                _make_function_call("Exploration-explore_branch", {"node_pk": "1280"}),
                _make_function_call("Exploration-explore_branch", {"node_pk": "594"}),
            ]
        elif is_neutral:
            # Neutral text: abandon all branches (no fallacies)
            mock_msg.items = [
                _make_function_call(
                    "Exploration-conclude_no_fallacy",
                    {"reason": "No fallacy pattern found in scientific text"},
                ),
            ]
        else:
            # Phase 2: confirm a fallacy based on which branch we're exploring
            branch = _detect_branch_from_prompt(chat_history)
            if branch and branch in _BRANCH_CONFIRMATIONS:
                conf = _BRANCH_CONFIRMATIONS[branch]
                mock_msg.items = [
                    _make_function_call(
                        "Exploration-confirm_fallacy",
                        {
                            "node_pk": conf["node_pk"],
                            "justification": conf["justification"],
                            "confidence": "high",
                        },
                    ),
                ]
            else:
                # Fallback: confirm Ad hominem
                mock_msg.items = [
                    _make_function_call(
                        "Exploration-confirm_fallacy",
                        {"node_pk": "1360", "justification": "Fallacy detected", "confidence": "medium"},
                    ),
                ]

        return [mock_msg]

    service.get_chat_message_contents = mock_get_chat_message_contents

    # One-shot fallback (singular form used by _run_one_shot)
    async def mock_get_chat_message_content(chat_history, settings, kernel, **kwargs):
        return '{"fallacy_name": "Appel à l\'autorité", "taxonomy_pk": "176", "explanation": "Mock one-shot", "confidence": 0.3}'

    service.get_chat_message_content = mock_get_chat_message_content

    return service
