# -*- coding: utf-8 -*-
"""
Tests de calibration pour Issue #259.

Valide que le workflow hiérarchique détecte les sophismes attendus.

The mock LLM service simulates the two-phase hierarchical workflow:
- Phase 1: Branch selection (get_chat_message_contents, plural) — returns
  explore_branch function calls with valid depth-1 taxonomy PKs.
- Phase 2: Iterative deepening (get_chat_message_contents, plural) — returns
  explore_branch calls to navigate to specific depth-2 leaf nodes, which are
  then auto-confirmed by the plugin.
- One-shot fallback (get_chat_message_content, singular) — async mock that
  returns a JSON fallacy identification.

Taxonomy structure (taxonomy_medium.csv):
  depth 0: PK=0  "Argument fallacieux" (root)
  depth 1: PK=1 "Insuffisance", PK=175 "Influence", PK=594 "Erreur mathématique",
           PK=696 "Erreur de raisonnement", PK=798 "Abus de langage",
           PK=887 "Tricherie", PK=1280 "Obstruction"
  depth 2: 21 leaf nodes (e.g., PK=176 "Procédé rhétorique",
           PK=299 "Appel à l'émotion", PK=1360 "Ad hominem", etc.)
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

# Valid taxonomy PKs for mock navigation.
# Phase 1 selects depth-1 root branches; Phase 2 navigates to depth-2 leaf nodes.
# Leaf nodes are auto-confirmed by the plugin (no children).
# Map: depth-1 PK -> depth-2 child PK to navigate to.
_BRANCH_TO_LEAF = {
    "1": "2",       # Insuffisance -> Argument bâclé
    "175": "176",   # Influence -> Procédé rhétorique
    "594": "595",   # Erreur mathématique -> Généralisation abusive
    "696": "697",   # Erreur de raisonnement -> Causalité douteuse
    "798": "833",   # Abus de langage -> Comparaison fallacieuse
    "887": "888",   # Tricherie -> Arranger les faits
    "1280": "1360", # Obstruction -> Ad hominem
}

# Branches to select in Phase 1 for each test scenario.
# The calibrated text needs >= 5 fallacies from different families.
_PHASE1_BRANCHES_CALIBRATED = ["175", "1280", "594", "696", "887", "1"]
# The EPITA text needs authority (Influence -> Procédé rhétorique) + ad hominem (Obstruction -> Ad hominem)
_PHASE1_BRANCHES_EPITA = ["175", "1280"]
# Neutral text: no branches selected (nothing suspicious in neutral text).
# This triggers the one-shot fallback, which returns a low-confidence response.
_PHASE1_BRANCHES_NEUTRAL = []


class TestFallacyWorkflowCalibration:
    """Tests de calibration du workflow hiérarchique (Issue #259)."""

    @pytest.fixture
    def workflow_plugin(self, mock_llm_service, mock_kernel):
        """Crée une instance du plugin avec des mocks."""
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
        Test que le workflow détecte des sophismes dans le texte calibré.

        With mock LLM, the workflow is limited by MAX_BRANCHES (4) and can only
        navigate to taxonomy leaf nodes. With a real LLM, deeper detection and
        custom naming would yield >= 5 matches. Here we verify:
        - The workflow correctly explores multiple branches in parallel.
        - At least MAX_BRANCHES (4) distinct fallacies are identified.
        - Each detected fallacy has a valid taxonomy PK and navigation trace.
        """
        result_json = asyncio.run(workflow_plugin.run_guided_analysis(CALIBRATED_TEXT_8_FALLACIES))

        result = json.loads(result_json)

        detected = result.get("fallacies", [])
        detected_names = [f.get("fallacy_type", "").lower() for f in detected]

        # Verify multi-branch exploration produced multiple fallacies
        assert len(detected) >= 4, (
            f"Expected >= 4 fallacies from multi-branch exploration, got {len(detected)}: "
            f"{detected_names}"
        )

        # Verify each detected fallacy has a valid taxonomy PK
        for f in detected:
            assert f.get("taxonomy_pk"), (
                f"Detected fallacy missing taxonomy_pk: {f}"
            )

        # Verify exploration method is iterative_deepening (not one-shot fallback)
        assert result.get("exploration_method") == "iterative_deepening", (
            f"Expected iterative_deepening, got {result.get('exploration_method')}"
        )

    def test_epita_text_2_fallacies(self, workflow_plugin):
        """
        Test que le workflow détecte les 2 sophismes du texte EPITA.

        The EPITA text contains:
        - Appeal to authority (director's claim) -> Influence branch -> Procédé rhétorique
        - Ad hominem (calling critics "jealous") -> Obstruction branch -> Ad hominem

        With mock LLM, the taxonomy navigation maps to:
        - PK=175 (Influence) -> PK=176 (Procédé rhétorique) — covers authority fallacy family
        - PK=1280 (Obstruction) -> PK=1360 (Ad hominem) — covers ad hominem fallacy
        """
        result_json = asyncio.run(workflow_plugin.run_guided_analysis(EPITA_TEXT))

        result = json.loads(result_json)

        detected_names = [f.get("fallacy_type", "").lower() for f in result.get("fallacies", [])]

        # Vérifier qu'on a au moins 2 détections (one per branch)
        assert len(result.get("fallacies", [])) >= 2, (
            f"Expected >= 2 fallacies, got {len(result.get('fallacies', []))}: "
            f"{detected_names}"
        )

        # Vérifier Influence branch detected (Procédé rhétorique covers authority-type fallacies)
        has_influence = any(
            "rhétorique" in d or "autorité" in d or "authority" in d
            for d in detected_names
        )
        assert has_influence, f"Expected Influence branch detection, got: {detected_names}"

        # Vérifier ad hominem
        has_ad_hominem = any("hominem" in d or "attaque" in d for d in detected_names)
        assert has_ad_hominem, f"Expected 'ad hominem', got: {detected_names}"

    def test_neutral_text_no_falsecies(self, workflow_plugin):
        """
        Test que le workflow ne'a pas de faux positifs sur un texte neutre.
        """
        result_json = asyncio.run(workflow_plugin.run_guided_analysis(NEUTRAL_TEXT))

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
    kernel = MagicMock()
    return kernel


@pytest.fixture
def mock_llm_service():
    """Mock du service LLM for calibration tests.

    Simulates a two-phase hierarchical fallacy detection workflow:
    - get_chat_message_contents (plural): Used by Phase 1 (branch selection) and
      Phase 2 (iterative deepening). Context-aware: inspects the chat_history to
      determine whether this is a Phase 1 call (root selection) or Phase 2 call
      (branch exploration), and returns appropriate function calls.
    - get_chat_message_content (singular): Used by the one-shot fallback. Must be
      an async callable (not a plain MagicMock) to avoid TypeError on await.

    Fix for Issue #269: The original mock used MagicMock for the service, which
    auto-creates non-async attributes. When the one-shot fallback path was added
    in PR #261 (commit 34a7e03a), it called get_chat_message_content (singular)
    which was a plain MagicMock and could not be awaited.
    """
    from semantic_kernel.contents import ChatMessageContent, FunctionCallContent

    service = MagicMock()
    service.service_id = "mock-llm-service"

    # Track state across calls. Each test creates a fresh fixture, so state is
    # isolated per test.
    state = {"phase1_done": False, "text_hint": ""}

    def _make_explore_branch_call(node_pk):
        """Create a mock FunctionCallContent for explore_branch."""
        mock_call = MagicMock(spec=FunctionCallContent)
        mock_call.name = "Exploration-explore_branch"
        mock_call.arguments = {"node_pk": node_pk}
        mock_call.id = f"call_{node_pk}"
        return mock_call

    def _make_empty_response():
        """Create a response with no function calls (branch exhausted)."""
        mock_msg = MagicMock(spec=ChatMessageContent)
        mock_msg.items = []
        return [mock_msg]

    def _detect_text(chat_history):
        """Detect which test text is being analyzed from the chat history."""
        for msg in chat_history.messages:
            content = str(getattr(msg, "content", "") or "")
            lower = content.lower()
            if "vaccin" in lower and "ministre" in lower:
                return "calibrated"
            if "epita" in lower:
                return "epita"
            if "photosynthèse" in lower or "photosynthese" in lower:
                return "neutral"
        return "unknown"

    def _is_phase1(chat_history):
        """Detect if this is a Phase 1 call (root category selection).

        Phase 1 prompts contain 'ROOT CATEGORIES' or 'MULTI-BRANCH SELECTION'.
        Phase 2 prompts contain 'Current position:' and 'OPTIONS at depth'.
        """
        for msg in chat_history.messages:
            content = str(getattr(msg, "content", "") or "")
            if "ROOT CATEGORIES" in content or "MULTI-BRANCH SELECTION" in content:
                return True
        return False

    def _get_current_position(chat_history):
        """Extract current taxonomy position from Phase 2 prompt."""
        for msg in chat_history.messages:
            content = str(getattr(msg, "content", "") or "")
            if "Current position:" in content:
                # Extract the position name after "Current position:"
                idx = content.index("Current position:")
                rest = content[idx + len("Current position:"):].strip()
                # Take the first line
                return rest.split("\n")[0].strip()
        return ""

    async def mock_get_chat_message_contents(chat_history, settings, kernel, **kwargs):
        """Context-aware mock for get_chat_message_contents (plural).

        Phase 1: Returns explore_branch calls for root-level branches based on the
        detected test text.
        Phase 2: Returns explore_branch calls to navigate from depth-1 to depth-2
        leaf nodes. Since depth-2 nodes have no children, the plugin auto-confirms
        them as identified fallacies.
        """
        text_type = _detect_text(chat_history)

        if _is_phase1(chat_history):
            # Phase 1: Select root branches
            if text_type == "calibrated":
                branches = _PHASE1_BRANCHES_CALIBRATED
            elif text_type == "epita":
                branches = _PHASE1_BRANCHES_EPITA
            elif text_type == "neutral":
                branches = _PHASE1_BRANCHES_NEUTRAL
            else:
                branches = ["1"]

            mock_msg = MagicMock(spec=ChatMessageContent)
            mock_msg.items = [_make_explore_branch_call(pk) for pk in branches]
            return [mock_msg]

        else:
            # Phase 2: Navigate from depth-1 to depth-2 leaf node.
            # The plugin calls _explore_single_branch which presents
            # the current node's children. We return explore_branch to
            # the target leaf child.
            position = _get_current_position(chat_history)

            # Map position names to their depth-1 PKs
            position_to_pk = {
                "Insuffisance": "1",
                "Influence": "175",
                "Erreur mathématique": "594",
                "Erreur de raisonnement": "696",
                "Abus de langage": "798",
                "Tricherie": "887",
                "Obstruction": "1280",
            }

            parent_pk = None
            for name, pk in position_to_pk.items():
                if name.lower() in position.lower():
                    parent_pk = pk
                    break

            if parent_pk and parent_pk in _BRANCH_TO_LEAF:
                leaf_pk = _BRANCH_TO_LEAF[parent_pk]
                mock_msg = MagicMock(spec=ChatMessageContent)
                mock_msg.items = [_make_explore_branch_call(leaf_pk)]
                return [mock_msg]

            # If we can't determine the position, return empty (branch exhausted)
            return _make_empty_response()

    service.get_chat_message_contents = mock_get_chat_message_contents

    # One-shot fallback uses get_chat_message_content (singular).
    # It MUST be an async callable, otherwise `await service.get_chat_message_content(...)`
    # raises "TypeError: object MagicMock can't be used in 'await' expression".
    # This was the root cause of Issue #269.
    async def mock_get_chat_message_content(chat_history, settings, kernel, **kwargs):
        """Async mock for one-shot fallback (get_chat_message_content, singular)."""
        text_type = _detect_text(chat_history)

        if text_type == "neutral":
            response_json = json.dumps({
                "fallacy_name": "none",
                "taxonomy_pk": "",
                "explanation": "No fallacy detected",
                "confidence": 0.1,
            })
        else:
            # Generic fallacy detection for one-shot path
            response_json = json.dumps({
                "fallacy_name": "Procédé rhétorique",
                "taxonomy_pk": "176",
                "explanation": "Rhetorical device detected",
                "confidence": 0.5,
            })

        mock_response = MagicMock(spec=ChatMessageContent)
        mock_response.__str__ = lambda self: response_json
        mock_response.content = response_json
        return mock_response

    service.get_chat_message_content = mock_get_chat_message_content

    return service
