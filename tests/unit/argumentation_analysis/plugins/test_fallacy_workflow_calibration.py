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

# Import is deferred inside the workflow_plugin fixture to avoid the
# ``tests/conftest.py`` semantic_kernel auto-marker picking this file up as a
# real-LLM integration test (the auto-marker deactivates the mock LLM service
# at runtime). This is a calibration test that uses a fully mocked LLM — see
# the fixture body for the deferred import.

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
    "1": "2",  # Insuffisance -> Argument bâclé
    "175": "176",  # Influence -> Procédé rhétorique
    "594": "595",  # Erreur mathématique -> Généralisation abusive
    "696": "697",  # Erreur de raisonnement -> Causalité douteuse
    "798": "833",  # Abus de langage -> Comparaison fallacieuse
    "887": "888",  # Tricherie -> Arranger les faits
    "1280": "1360",  # Obstruction -> Ad hominem
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
        # Deferred import: ``from semantic_kernel.kernel import Kernel`` at
        # module scope triggers conftest's ``llm_integration`` auto-marker,
        # which then deactivates the mock LLM at runtime (see fixture-level
        # comment).
        from semantic_kernel.kernel import Kernel

        taxonomy_path = (
            Path(project_root_for_test)
            / "argumentation_analysis"
            / "data"
            / "taxonomy_medium.csv"
        )

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

        With the wide-net Phase 1 dispatch (PR #578) and a mock LLM that
        confirms every leaf it is shown, the workflow identifies 6 distinct
        fallacies from 6 wide-net candidates (one per depth-2 leaf). The
        exploration method label is ``wide_net_parallel`` since PR #578 (it
        was ``iterative_deepening`` before that refactor). The mock LLM
        confirms every leaf via ``confirm_fallacy`` per PR #471.
        """
        result_json = asyncio.run(
            workflow_plugin.run_guided_analysis(CALIBRATED_TEXT_8_FALLACIES)
        )

        result = json.loads(result_json)

        detected = result.get("fallacies", [])
        detected_names = [f.get("fallacy_type", "").lower() for f in detected]

        # Verify multi-branch exploration produced multiple fallacies.
        # With the wide-net + leaf-confirm mock, 6 leaves → 6 distinct fallacies.
        assert len(detected) >= 4, (
            f"Expected >= 4 fallacies from multi-branch exploration, got {len(detected)}: "
            f"{detected_names}"
        )

        # Verify each detected fallacy has a valid taxonomy PK
        for f in detected:
            assert f.get("taxonomy_pk"), f"Detected fallacy missing taxonomy_pk: {f}"

        # Verify exploration method is wide_net_parallel (PR #578 dispatch)
        assert (
            result.get("exploration_method") == "wide_net_parallel"
        ), f"Expected wide_net_parallel, got {result.get('exploration_method')}"

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

        detected_names = [
            f.get("fallacy_type", "").lower() for f in result.get("fallacies", [])
        ]

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
        assert (
            has_influence
        ), f"Expected Influence branch detection, got: {detected_names}"

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
                assert (
                    confidence < 0.5
                ), f"False positive detected with high confidence: {f}"


# Fixtures mock
@pytest.fixture
def mock_kernel():
    """Mock du kernel Semantic Kernel."""
    kernel = MagicMock()
    return kernel


@pytest.fixture
def mock_llm_service():
    """Mock du service LLM for calibration tests.

    Simulates the wide-net hierarchical fallacy detection workflow (since PR #578):
    - get_chat_message_content (singular, wide-net Phase 1): detects the wide-net
      prompt ("List EVERY fallacy" / "Available root categories") and returns a
      JSON-array of candidate fallacies (one entry per expected Phase 2 branch).
    - get_chat_message_contents (plural, Phase 2 + leaf confirmation): returns
      explore_branch calls to navigate depth-1 → depth-2 leaves, then returns
      confirm_fallacy calls at leaf nodes (the prod asks the LLM to confirm,
      not auto-confirm — see PR #471).

    Fixes for Issue #269: MagicMock auto-created non-async attributes. After
    PR #261 (one-shot fallback) and PR #578 (wide-net Phase 1), the mock must
    be async callable. Stale fixture detected in CI R564 — singular was
    returning a single object when the prod now expects a JSON-array.
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

        Phase 1 prompts contain the wide-net signature from PR #578:
        - 'List EVERY fallacy' (the wide-net prompt preamble), OR
        - 'Available root categories' (the root list in the prompt), OR
        - the legacy triggers 'ROOT CATEGORIES' / 'MULTI-BRANCH SELECTION'.

        Phase 2 prompts contain 'Current position:' and 'OPTIONS at depth'.
        """
        for msg in chat_history.messages:
            content = str(getattr(msg, "content", "") or "")
            if (
                "List EVERY fallacy" in content
                or "Available root categories" in content
                or "ROOT CATEGORIES" in content
                or "MULTI-BRANCH SELECTION" in content
            ):
                return True
        return False

    def _is_leaf_prompt(chat_history):
        """Detect if this is the leaf confirmation prompt (PR #471).

        Prod presents a leaf confirmation prompt containing
        'You reached a LEAF node in the fallacy taxonomy.' The LLM is asked to
        return a `confirm_fallacy` function call. Earlier fixtures auto-confirmed
        leaves (PR #471 changed that); if we return an empty items list here the
        leaf is abandoned and the multi-branch test sees 0 fallacies.
        """
        for msg in chat_history.messages:
            content = str(getattr(msg, "content", "") or "")
            if "You reached a LEAF node" in content:
                return True
        return False

    def _make_confirm_fallacy_call(node_pk):
        """Create a mock FunctionCallContent for confirm_fallacy (leaf hit).

        The prod ``ExplorationPlugin.confirm_fallacy(node_pk, confidence, justification)``
        returns a JSON string containing ``"confirmed": True``. The mock must
        only pass kwargs the real method accepts — passing ``confirmed=True`` as
        a kwarg triggers "got an unexpected keyword argument 'confirmed'"
        because that field is added to the result dict by the method body, not
        accepted as input.
        """
        mock_call = MagicMock(spec=FunctionCallContent)
        mock_call.name = "Exploration-confirm_fallacy"
        mock_call.arguments = {
            "node_pk": node_pk,
            "confidence": "high",
            "justification": "Mock leaf confirmation for calibration test",
        }
        mock_call.id = f"confirm_{node_pk}"
        return mock_call

    def _get_current_position(chat_history):
        """Extract current taxonomy position from Phase 2 prompt."""
        for msg in chat_history.messages:
            content = str(getattr(msg, "content", "") or "")
            if "Current position:" in content:
                # Extract the position name after "Current position:"
                idx = content.index("Current position:")
                rest = content[idx + len("Current position:") :].strip()
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

        elif _is_leaf_prompt(chat_history):
            # Phase 2 leaf: prod asks for a confirm_fallacy decision (PR #471).
            # The prod's leaf prompt contains "Node: <leaf_name> (PK: <leaf_pk>)"
            # — extract the PK directly to avoid name→PK indirection. The leaf
            # is a depth-2 node (PK is a key in ``_BRANCH_TO_LEAF.values()``).
            leaf_pk = None
            for msg in chat_history.messages:
                content = str(getattr(msg, "content", "") or "")
                if "Node:" in content and "PK:" in content:
                    # Format: "Node: <name> (PK: <pk>)"
                    try:
                        pk_segment = content.split("(PK:")[1]
                        leaf_pk = pk_segment.split(")")[0].strip()
                        break
                    except (IndexError, ValueError):
                        continue
            if not leaf_pk or leaf_pk not in _BRANCH_TO_LEAF.values():
                # Fallback: confirm a known leaf rather than abandon
                leaf_pk = "176"  # Procédé rhétorique (a depth-2 leaf)
            mock_msg = MagicMock(spec=ChatMessageContent)
            mock_msg.items = [_make_confirm_fallacy_call(leaf_pk)]
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
        """Async mock for get_chat_message_content (singular).

        Two call paths:
        - Wide-net Phase 1 (PR #578): the prompt contains "List EVERY fallacy" or
          "Available root categories". Prod parses a JSON-array of candidate
          fallacies; the parser does `raw.find("[")` then `json.loads`. Returning
          a single JSON object (the prior stale fixture) made the parser fail
          silently → empty candidates → fallback to one-shot. Fix: return an
          array of objects matching the per-test expected branches.
        - One-shot fallback (PR #261): plain-text or single-object response.
        """
        text_type = _detect_text(chat_history)

        if _is_phase1(chat_history):
            # Wide-net Phase 1 — return a JSON-array the prod parser can read.
            if text_type == "calibrated":
                candidates = [
                    {"fallacy_name": "Appel à l'autorité", "root_category": "Influence", "confidence": 0.9},
                    {"fallacy_name": "Ad hominem", "root_category": "Obstruction", "confidence": 0.9},
                    {"fallacy_name": "Généralisation abusive", "root_category": "Erreur mathématique", "confidence": 0.85},
                    {"fallacy_name": "Causalité douteuse", "root_category": "Erreur de raisonnement", "confidence": 0.85},
                    {"fallacy_name": "Arranger les faits", "root_category": "Tricherie", "confidence": 0.8},
                    {"fallacy_name": "Argument bâclé", "root_category": "Insuffisance", "confidence": 0.8},
                ]
            elif text_type == "epita":
                candidates = [
                    {"fallacy_name": "Appel à l'autorité", "root_category": "Influence", "confidence": 0.9},
                    {"fallacy_name": "Ad hominem", "root_category": "Obstruction", "confidence": 0.9},
                ]
            elif text_type == "neutral":
                candidates = []
            else:
                candidates = [
                    {"fallacy_name": "Procédé rhétorique", "root_category": "Influence", "confidence": 0.5},
                ]
            response_json = json.dumps(candidates)
        elif text_type == "neutral":
            response_json = json.dumps(
                {
                    "fallacy_name": "none",
                    "taxonomy_pk": "",
                    "explanation": "No fallacy detected",
                    "confidence": 0.1,
                }
            )
        else:
            # Generic fallacy detection for one-shot path
            response_json = json.dumps(
                {
                    "fallacy_name": "Procédé rhétorique",
                    "taxonomy_pk": "176",
                    "explanation": "Rhetorical device detected",
                    "confidence": 0.5,
                }
            )

        mock_response = MagicMock(spec=ChatMessageContent)
        mock_response.__str__ = lambda self: response_json
        mock_response.content = response_json
        return mock_response

    service.get_chat_message_content = mock_get_chat_message_content

    return service
