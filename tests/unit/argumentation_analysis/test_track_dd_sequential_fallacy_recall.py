"""Tests for Track DD (#690): sequential pipeline fallacy-recall parity.

Covers:
  1. _merge_fallacy_results: deduplication by taxonomy_pk, highest-confidence wins
  2. _extract_arguments_for_parallel: context key fix (phase_extract_output not phase_extraction_output)
  3. _invoke_hierarchical_fallacy: per-argument enrichment pass union
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import importlib.util
from pathlib import Path

_DEMO_ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "invoke_callables",
    _DEMO_ROOT / "argumentation_analysis" / "orchestration" / "invoke_callables.py",
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

_merge_fallacy_results = _MOD._merge_fallacy_results
_extract_arguments_for_parallel = _MOD._extract_arguments_for_parallel


class TestMergeFallacyResults:
    """Verify _merge_fallacy_results deduplication and union logic."""

    def test_empty_inputs(self):
        assert _merge_fallacy_results([], []) == []

    def test_wide_net_only(self):
        wide = [
            {"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.9},
            {"fallacy_type": "straw man", "taxonomy_pk": "SM.01", "confidence": 0.8},
        ]
        result = _merge_fallacy_results(wide, [])
        assert len(result) == 2

    def test_per_arg_extras_added(self):
        wide = [
            {"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.9},
        ]
        per_arg = [
            {
                "fallacy_type": "slippery slope",
                "taxonomy_pk": "SS.01",
                "confidence": 0.85,
            },
            {
                "fallacy_type": "false dilemma",
                "taxonomy_pk": "FD.01",
                "confidence": 0.7,
            },
        ]
        result = _merge_fallacy_results(wide, per_arg)
        assert len(result) == 3
        pks = {f["taxonomy_pk"] for f in result}
        assert pks == {"AH.01", "SS.01", "FD.01"}

    def test_dedup_keeps_highest_confidence(self):
        wide = [
            {"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.7},
        ]
        per_arg = [
            {"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.95},
        ]
        result = _merge_fallacy_results(wide, per_arg)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.95

    def test_dedup_wide_net_higher_kept(self):
        wide = [
            {"fallacy_type": "straw man", "taxonomy_pk": "SM.01", "confidence": 0.9},
        ]
        per_arg = [
            {"fallacy_type": "straw man", "taxonomy_pk": "SM.01", "confidence": 0.6},
        ]
        result = _merge_fallacy_results(wide, per_arg)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.9

    def test_fallacy_type_used_as_fallback_key(self):
        """fallacy_type is used as fallback when taxonomy_pk is absent."""
        wide = [{"fallacy_type": "unknown_type", "confidence": 0.5}]
        per_arg = [{"confidence": 0.8}]
        result = _merge_fallacy_results(wide, per_arg)
        assert len(result) == 1
        assert result[0]["fallacy_type"] == "unknown_type"

    def test_truly_no_key_skipped(self):
        """Entries with neither taxonomy_pk nor fallacy_type are skipped."""
        wide = [{"confidence": 0.5}]
        per_arg = [{"confidence": 0.8}]
        result = _merge_fallacy_results(wide, per_arg)
        assert len(result) == 0

    def test_non_dict_entries_skipped(self):
        wide = [
            "not a dict",
            {"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.8},
        ]
        per_arg = [42, None]
        result = _merge_fallacy_results(wide, per_arg)
        assert len(result) == 1
        assert result[0]["taxonomy_pk"] == "AH.01"


class TestExtractArgumentsForParallel:
    """Verify _extract_arguments_for_parallel uses correct context key."""

    def test_reads_phase_extract_output_key(self):
        context = {
            "phase_extract_output": {
                "arguments": [
                    {
                        "text": "First argument about policy that is long enough to pass filter"
                    },
                    {"text": "Second argument about economy that meets minimum length"},
                ],
            },
        }
        result = _extract_arguments_for_parallel("fallback text", context)
        assert len(result) == 2
        assert result[0][0] == "arg_1"
        assert result[1][0] == "arg_2"

    def test_old_key_phase_extraction_output_not_matched(self):
        """Verify the old buggy key does NOT work (regression guard)."""
        context = {
            "phase_extraction_output": {
                "arguments": [
                    {
                        "text": "Argument from wrong key that is long enough to pass filter"
                    },
                ],
            },
        }
        result = _extract_arguments_for_parallel("fallback text", context)
        # Should NOT find arguments from the typo key
        assert len(result) == 0

    def test_state_object_takes_priority(self):
        state = MagicMock()
        state.identified_arguments = {
            "arg_1": "State argument one that is long enough for the filter",
            "arg_2": "State argument two that meets the minimum length requirement",
        }
        context = {
            "_state_object": state,
            "phase_extract_output": {
                "arguments": [{"text": "Extract argument that should be ignored"}],
            },
        }
        result = _extract_arguments_for_parallel("text", context)
        assert len(result) == 2
        assert result[0][0] == "arg_1"

    def test_paragraph_fallback(self):
        context = {}
        text = "First paragraph that is sufficiently long for the filter to pass\n\nSecond paragraph also long enough to meet the threshold"
        result = _extract_arguments_for_parallel(text, context)
        assert len(result) == 2
        assert result[0][0] == "paragraph_1"

    def test_empty_context_returns_empty(self):
        result = _extract_arguments_for_parallel("short", {})
        assert result == []

    def test_max_10_arguments(self):
        args = [
            {"text": f"Argument number {i} that is long enough for the filter"}
            for i in range(15)
        ]
        context = {"phase_extract_output": {"arguments": args}}
        result = _extract_arguments_for_parallel("text", context)
        assert len(result) == 10


class TestInvokeHierarchicalFallacyEnrichment:
    """Verify _invoke_hierarchical_fallacy runs per-arg enrichment and merges."""

    @pytest.mark.asyncio
    async def test_enrichment_pass_called(self):
        """Wide-net result is enriched with per-argument extras."""
        invoke_mod = _MOD

        per_arg_result = {
            "fallacies": [
                {
                    "fallacy_type": "slippery slope",
                    "taxonomy_pk": "SS.01",
                    "confidence": 0.85,
                },
                {
                    "fallacy_type": "false dilemma",
                    "taxonomy_pk": "FD.01",
                    "confidence": 0.7,
                },
            ],
            "exploration_method": "per_argument_parallel",
        }

        with patch.object(
            invoke_mod,
            "_invoke_hierarchical_fallacy_per_argument",
            new_callable=AsyncMock,
            return_value=per_arg_result,
        ) as mock_per_arg, patch(
            "argumentation_analysis.core.llm_service.create_llm_service",
        ) as mock_llm, patch(
            "argumentation_analysis.plugins.fallacy_workflow_plugin.FallacyWorkflowPlugin"
        ) as mock_plugin_cls:
            mock_llm.return_value = MagicMock()
            mock_plugin = MagicMock()
            mock_plugin.run_guided_analysis = AsyncMock(
                return_value='{"fallacies": [{"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.9}], "exploration_method": "guided"}'
            )
            mock_plugin_cls.return_value = mock_plugin

            result = await invoke_mod._invoke_hierarchical_fallacy("test text", {})
            mock_per_arg.assert_called_once()
            assert len(result["fallacies"]) == 3
            assert result["extraction_method"] == "widenet+perarg_union"
            # #2920 (R1063 review): the per-argument detections ALSO leave
            # under their own key, byte-for-byte — the Dung stage's source.
            assert result["per_argument_fallacies"] == per_arg_result["fallacies"]

    @pytest.mark.asyncio
    async def test_enrichment_failure_keeps_wide_net(self):
        """If per-arg enrichment fails, wide-net results are kept."""
        invoke_mod = _MOD

        with patch.object(
            invoke_mod,
            "_invoke_hierarchical_fallacy_per_argument",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API timeout"),
        ), patch(
            "argumentation_analysis.core.llm_service.create_llm_service",
        ) as mock_llm, patch(
            "argumentation_analysis.plugins.fallacy_workflow_plugin.FallacyWorkflowPlugin"
        ) as mock_plugin_cls:
            mock_llm.return_value = MagicMock()
            mock_plugin = MagicMock()
            mock_plugin.run_guided_analysis = AsyncMock(
                return_value='{"fallacies": [{"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.9}], "exploration_method": "guided"}'
            )
            mock_plugin_cls.return_value = mock_plugin

            result = await invoke_mod._invoke_hierarchical_fallacy("test text", {})
            assert len(result["fallacies"]) == 1
            assert result["extraction_method"] == "guided"
            # Per-argument pass failed: the key stays ABSENT (honest-absent
            # for the Dung stage — no fabricated targeted detections).
            assert "per_argument_fallacies" not in result


class TestMergeKeyStaysPkOnly:
    """R1063 review: the merged ``fallacies`` list is byte-identical to main.

    11 handlers, the state writer and the sherlock orchestrator consume this
    list on every real run; #2920's first route (key = (pk, target)) changed
    its counts and re-introduced wide-net/per-argument duplicates, so it was
    sent back. The per-argument detections now leave the phase under their
    own key (``per_argument_fallacies`` — see TestInvokeHierarchicalFallacy-
    Enrichment) and the Dung stage reads THAT. These tests pin the pk-only
    merge so the key cannot move again by accident: any change to the key or
    the output shape reddens here.
    """

    def test_same_pk_two_arguments_collapses_to_main_output(self):
        """The review's witness: same pk on two arguments, merged unchanged.

        Byte-identical to main's pk-only behavior: one entry, the wide-net
        floor (higher confidence), in the wide-net position.
        """
        wide = [
            {"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.9},
        ]
        per_arg = [
            {
                "fallacy_type": "ad hominem",
                "taxonomy_pk": "AH.01",
                "target_argument": "arg_2",
                "confidence": 0.7,
            },
            {
                "fallacy_type": "ad hominem",
                "taxonomy_pk": "AH.01",
                "target_argument": "arg_5",
                "confidence": 0.6,
            },
        ]
        result = _merge_fallacy_results(wide, per_arg)
        assert result == [wide[0]]

    def test_same_pk_two_arguments_no_wide_floor(self):
        per_arg = [
            {
                "fallacy_type": "ad hominem",
                "taxonomy_pk": "AH.01",
                "target_argument": "arg_2",
                "confidence": 0.7,
            },
            {
                "fallacy_type": "ad hominem",
                "taxonomy_pk": "AH.01",
                "target_argument": "arg_5",
                "confidence": 0.95,
            },
        ]
        result = _merge_fallacy_results([], per_arg)
        assert len(result) == 1
        assert result[0]["confidence"] == 0.95

    def test_wide_net_floor_and_per_arg_same_pk_make_one_entry(self):
        """The (pk, target) route kept both — a duplicate in every narrative
        prompt. Main's semantics: one entry, the higher-confidence dict."""
        wide = [
            {
                "fallacy_type": "slippery slope",
                "taxonomy_pk": "SS.01",
                "confidence": 0.8,
            },
        ]
        per_arg = [
            {
                "fallacy_type": "slippery slope",
                "taxonomy_pk": "SS.01",
                "target_argument": "arg_1",
                "confidence": 0.5,
            },
        ]
        result = _merge_fallacy_results(wide, per_arg)
        assert result == [wide[0]]

    def test_distinct_pks_union_shape_pinned(self):
        wide = [
            {"fallacy_type": "ad hominem", "taxonomy_pk": "AH.01", "confidence": 0.9},
        ]
        per_arg = [
            {
                "fallacy_type": "slippery slope",
                "taxonomy_pk": "SS.01",
                "target_argument": "arg_1",
                "confidence": 0.85,
            },
            {
                "fallacy_type": "false dilemma",
                "taxonomy_pk": "FD.01",
                "target_argument": "arg_2",
                "confidence": 0.7,
            },
        ]
        result = _merge_fallacy_results(wide, per_arg)
        # Wide-net floor first, per-argument extras in source order.
        assert [f["taxonomy_pk"] for f in result] == ["AH.01", "SS.01", "FD.01"]
