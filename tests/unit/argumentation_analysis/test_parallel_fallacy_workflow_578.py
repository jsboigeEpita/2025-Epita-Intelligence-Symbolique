"""Tests for #578: Parallel FallacyWorkflowPlugin — wide-net Phase 1 + parallel Phase 2 + dedup."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argumentation_analysis.plugins.identification_models import IdentifiedFallacy


def _make_taxonomy():
    return [
        {"PK": "1", "depth": "1", "text_fr": "Appel à l'autorité", "desc_fr": "Authority"},
        {"PK": "2", "depth": "1", "text_fr": "Ad hominem", "desc_fr": "Attack"},
        {"PK": "3", "depth": "1", "text_fr": "Pente glissante", "desc_fr": "Slippery slope"},
        {"PK": "4", "depth": "1", "text_fr": "Faux dilemme", "desc_fr": "False dilemma"},
        {"PK": "175", "depth": "1", "text_fr": "Manipulation mentale", "desc_fr": "Manipulation"},
        {"PK": "1_1", "depth": "2", "text_fr": "Autorité non pertinente", "parent_PK": "1"},
        {"PK": "2_1", "depth": "2", "text_fr": "Attaque personnelle", "parent_PK": "2"},
        {"PK": "2_1_1", "depth": "3", "text_fr": "Ad hominem abusif", "parent_PK": "2_1"},
    ]


def _make_plugin():
    from argumentation_analysis.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin
    from semantic_kernel.kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    kernel = Kernel()
    mock_service = MagicMock(spec=OpenAIChatCompletion)
    mock_service.service_id = "test-service"
    plugin = FallacyWorkflowPlugin(
        master_kernel=kernel,
        llm_service=mock_service,
        taxonomy_data=_make_taxonomy(),
    )
    return plugin


class TestBuildRootsIndex:
    def test_builds_index_from_taxonomy(self):
        plugin = _make_plugin()
        index = plugin._build_roots_index()
        assert "appel à l'autorité" in index
        assert index["appel à l'autorité"] == "1"
        assert index["ad hominem"] == "2"


class TestMapFallacyToRootPK:
    def test_exact_match(self):
        plugin = _make_plugin()
        index = plugin._build_roots_index()
        assert plugin._map_fallacy_to_root_pk("Ad hominem", index) == "2"

    def test_keyword_match(self):
        plugin = _make_plugin()
        index = plugin._build_roots_index()
        result = plugin._map_fallacy_to_root_pk("attaque personnelle", index)
        assert result == "2"

    def test_no_match_returns_none(self):
        plugin = _make_plugin()
        index = plugin._build_roots_index()
        assert plugin._map_fallacy_to_root_pk("something totally unknown xyz", index) is None


class TestWideNetCandidates:
    def test_parses_json_array_response(self):
        plugin = _make_plugin()
        response_content = json.dumps([
            {"fallacy_name": "Ad hominem abusif", "root_category": "Ad hominem", "confidence": 0.9},
            {"fallacy_name": "Appel à l'émotion", "root_category": "Manipulation mentale", "confidence": 0.7},
        ])
        mock_result = MagicMock()
        mock_result.__str__ = lambda self: response_content
        plugin.llm_service.get_chat_message_content = AsyncMock(return_value=mock_result)

        result = asyncio.get_event_loop().run_until_complete(
            plugin._wide_net_candidates("Some argument text here")
        )
        # Ad hominem maps to a child PK since "ad hominem abusif" contains "ad hominem"
        assert len(result) >= 2
        assert "175" in result  # Manipulation mentale PK

    def test_handles_empty_response(self):
        plugin = _make_plugin()
        mock_result = MagicMock()
        mock_result.__str__ = lambda self: "[]"
        plugin.llm_service.get_chat_message_content = AsyncMock(return_value=mock_result)

        result = asyncio.get_event_loop().run_until_complete(
            plugin._wide_net_candidates("text")
        )
        assert result == []

    def test_handles_llm_failure(self):
        plugin = _make_plugin()
        plugin.llm_service.get_chat_message_content = AsyncMock(side_effect=Exception("API error"))

        result = asyncio.get_event_loop().run_until_complete(
            plugin._wide_net_candidates("text")
        )
        assert result == []

    def test_respects_max_candidates_cap(self):
        plugin = _make_plugin()
        plugin.MAX_CANDIDATES = 2
        candidates = [{"fallacy_name": f"F{i}", "root_category": "Ad hominem"} for i in range(10)]
        response_content = json.dumps(candidates)
        mock_result = MagicMock()
        mock_result.__str__ = lambda self: response_content
        plugin.llm_service.get_chat_message_content = AsyncMock(return_value=mock_result)

        result = asyncio.get_event_loop().run_until_complete(
            plugin._wide_net_candidates("text")
        )
        assert len(result) <= 2


class TestDedupInPhase3:
    def test_dedup_keeps_highest_confidence(self):
        plugin = _make_plugin()

        # Simulate Phase 3 dedup logic
        identified = []
        seen_pks = {}
        branch_results = [
            IdentifiedFallacy(
                fallacy_type="ad_hominem_abusif",
                taxonomy_pk="2_1_1",
                explanation="test1",
                confidence=0.7,
                navigation_trace=["a"],
            ),
            IdentifiedFallacy(
                fallacy_type="ad_hominem_abusif",
                taxonomy_pk="2_1_1",
                explanation="test2",
                confidence=0.9,
                navigation_trace=["b"],
            ),
        ]

        for result in branch_results:
            leaf_pk = result.fallacy_type
            if leaf_pk in seen_pks and seen_pks[leaf_pk].confidence >= result.confidence:
                continue
            seen_pks[leaf_pk] = result
            identified = [r for r in identified if r.fallacy_type != leaf_pk]
            identified.append(result)

        assert len(identified) == 1
        assert identified[0].confidence == 0.9

    def test_different_fallacies_not_deduped(self):
        results = [
            IdentifiedFallacy(
                fallacy_type="ad_hominem",
                taxonomy_pk="2",
                explanation="test",
                confidence=0.8,
                navigation_trace=["a"],
            ),
            IdentifiedFallacy(
                fallacy_type="slippery_slope",
                taxonomy_pk="3",
                explanation="test",
                confidence=0.7,
                navigation_trace=["b"],
            ),
        ]

        identified = []
        seen_pks = {}
        for r in results:
            leaf_pk = r.fallacy_type
            if leaf_pk in seen_pks and seen_pks[leaf_pk].confidence >= r.confidence:
                continue
            seen_pks[leaf_pk] = r
            identified = [i for i in identified if i.fallacy_type != leaf_pk]
            identified.append(r)

        assert len(identified) == 2


class TestDirectConfirmCandidates:
    def test_confirms_matching_fallacy(self):
        plugin = _make_plugin()
        confirm_response = json.dumps({
            "confirmed": True,
            "name": "Ad hominem",
            "explanation": "The text attacks the person",
            "quote": "he is a liar",
            "confidence": 0.85,
        })
        mock_result = MagicMock()
        mock_result.__str__ = lambda self: confirm_response
        plugin.llm_service.get_chat_message_content = AsyncMock(return_value=mock_result)

        result = asyncio.get_event_loop().run_until_complete(
            plugin._direct_confirm_candidates("He is a liar so don't trust him", ["2"])
        )
        assert len(result) == 1
        assert result[0].confidence == 0.85

    def test_rejects_non_matching(self):
        plugin = _make_plugin()
        reject_response = json.dumps({"confirmed": False, "reason": "No fallacy here"})
        mock_result = MagicMock()
        mock_result.__str__ = lambda self: reject_response
        plugin.llm_service.get_chat_message_content = AsyncMock(return_value=mock_result)

        result = asyncio.get_event_loop().run_until_complete(
            plugin._direct_confirm_candidates("Simple factual statement", ["2"])
        )
        assert len(result) == 0


class TestExplorationMethodField:
    def test_wide_net_parallel_method_name(self):
        """Verify the new exploration_method is 'wide_net_parallel'."""
        from argumentation_analysis.plugins.identification_models import FallacyAnalysisResult

        result = FallacyAnalysisResult(
            fallacies=[],
            exploration_method="wide_net_parallel",
            branches_explored=10,
            total_iterations=0,
        )
        assert result.exploration_method == "wide_net_parallel"
