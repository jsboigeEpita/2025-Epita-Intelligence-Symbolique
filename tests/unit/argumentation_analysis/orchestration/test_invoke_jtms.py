"""Tests for _invoke_jtms with real dependency network (#208-G).

Verifies the JTMS phase builds proper belief networks from upstream phases.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestInvokeJTMS:
    """Tests for _invoke_jtms function."""

    async def test_claims_get_justifications_only_from_recorded_relations(self):
        """#3226: the synthetic all-args IN-list network is gone — a claim
        carries a justification only for a relation the run recorded (a
        stamped source unit), and unrecorded claims are said so."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Evidence supports the claim"},
                    {"text": "Statistical data confirms"},
                ],
                "claims": [
                    {"text": "The policy is effective"},
                    {"text": "The costs are contained", "source_unit": "arg_2"},
                ],
            }
        }
        result = await _invoke_jtms("text", context)

        assert result["belief_count"] >= 4  # 2 args + 2 claims
        # No recorded relation for claim 1: no justification, honest absence.
        unrecorded = result["beliefs"].get("The policy is effective")
        assert unrecorded is not None
        assert unrecorded["justifications"] == []
        assert result["claims_without_recorded_support"] == ["The policy is effective"]
        # The stamped source unit IS the recorded dependency the key counts
        # (it used to measure the synthetic args→claims network).
        assert result["has_real_dependencies"] is True
        # Claim 2's recorded source unit wires exactly one edge.
        recorded = result["beliefs"].get("The costs are contained")
        assert recorded is not None
        in_lists = [j["in_list"] for j in recorded["justifications"]]
        assert in_lists == [["arg_2:Statistical data confirms"]]

    async def test_fallacies_retract_undermined_beliefs(self):
        """A fallacy carrying its target's arg_N id retracts that belief."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "He is wrong because he is biased"}],
                "claims": [],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "fallacy_type": "ad_hominem",
                        "explanation": "Attacks the person",
                        # The hierarchical producer writes the unit's own
                        # identifier here (#1633) — position is not a
                        # resolver (#2968), so without this id the fallacy
                        # undermines nothing.
                        "target_argument": "arg_1",
                    }
                ]
            },
        }
        result = await _invoke_jtms("text", context)

        assert result["undermined_count"] > 0
        assert result["fallacy_count"] == 1
        # Belief names carry an "arg_N:" prefix so compute_argument_convergence
        # can index JTMS signals by arg_id (startswith check).
        arg_belief = result["beliefs"].get("arg_1:He is wrong because he is biased")
        assert arg_belief is not None
        assert arg_belief["valid"] is False

    async def test_fallacy_without_identity_retracts_nothing(self):
        """#2968/#1019: a fallacy naming no target (no id, no quote that
        grounds) undermines nothing — the old positional fallback retracted
        arg_{i+1} and linked a wrong unit."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "He is wrong because he is biased"}],
                "claims": [],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"fallacy_type": "ad_hominem", "explanation": "Attacks the person"}
                ]
            },
        }
        result = await _invoke_jtms("text", context)

        assert result["undermined_count"] == 0
        arg_belief = result["beliefs"].get("arg_1:He is wrong because he is biased")
        assert arg_belief is not None
        assert arg_belief["valid"] is True

    async def test_counter_arguments_create_rebuttals(self):
        """Counter-arguments → rebuttal entries via OUT-list."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Tax cuts always help growth"}],
                "claims": [],
            },
            "phase_counter_output": {
                "llm_counter_arguments": [
                    {
                        "counter_argument": "Tax cuts increase deficit which harms growth",
                        "target_argument": "Tax cuts always help growth",
                    }
                ]
            },
        }
        result = await _invoke_jtms("text", context)

        assert result["counter_argument_count"] == 1
        # Should have beliefs for both the argument and counter-argument
        assert result["belief_count"] >= 2

    async def test_quality_scores_annotated(self):
        """Quality scores from upstream are annotated on beliefs."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "A well-structured argument with evidence"}],
                "claims": [],
            },
            "phase_quality_output": {
                "per_argument_scores": {
                    "arg_1": {
                        "note_finale": 7.5,
                        "scores_par_vertu": {"clarity": 8.0, "coherence": 6.5},
                    }
                }
            },
        }
        result = await _invoke_jtms("text", context)

        arg_belief = result["beliefs"].get(
            "arg_1:A well-structured argument with evidence"
        )
        assert arg_belief is not None
        assert "quality" in arg_belief
        assert arg_belief["quality"]["quality_score"] == 7.5

    async def test_empty_input_graceful(self):
        """No arguments from upstream → fallback to sentence splitting."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {"phase_extract_output": {"arguments": [], "claims": []}}
        text = "This is a first sentence. This is a second sentence."
        result = await _invoke_jtms(text, context)

        # Should have fallen back to sentence splitting
        assert result["belief_count"] >= 2
        assert "beliefs" in result

    async def test_no_separate_claims_uses_synthetic(self):
        """#3226: args without claims manufacture no synthetic conclusion —
        the claim-less ``elif`` branch was the same defect class (all args
        in one IN-list that recorded nothing)."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First supporting point"},
                    {"text": "Second supporting point"},
                ],
                "claims": [],
            }
        }
        result = await _invoke_jtms("text", context)

        assert "overall_argument_validity" not in result["beliefs"]
        assert result["claims_without_recorded_support"] == []

    async def test_beliefs_have_structured_justifications(self):
        """Belief justifications expose in_list and out_list (not just
        repr) — pinned on a RECORDED relation (#3226): the claim's stamped
        source unit."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Premise one"}],
                "claims": [{"text": "Conclusion one", "source_unit": "arg_1"}],
            }
        }
        result = await _invoke_jtms("text", context)

        claim = result["beliefs"].get("Conclusion one")
        assert claim is not None
        assert len(claim["justifications"]) > 0
        j = claim["justifications"][0]
        assert "in_list" in j
        assert "out_list" in j
        assert isinstance(j["in_list"], list)
        assert isinstance(j["out_list"], list)

    async def test_multiple_fallacies_target_different_args(self):
        """Fallacies carrying their targets' ids retract those units — the
        untouched third belief stays valid (#2968)."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument"},
                    {"text": "Second argument"},
                    {"text": "Third argument"},
                ],
                "claims": [],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "fallacy_type": "ad_hominem",
                        "explanation": "attacks person",
                        "target_argument": "arg_1",
                    },
                    {
                        "fallacy_type": "strawman",
                        "explanation": "misrepresents",
                        "target_argument": "arg_2",
                    },
                ]
            },
        }
        result = await _invoke_jtms("text", context)

        assert result["fallacy_count"] == 2
        assert result["undermined_count"] >= 2
        assert result["beliefs"]["arg_1:First argument"]["valid"] is False
        assert result["beliefs"]["arg_2:Second argument"]["valid"] is False
        assert result["beliefs"]["arg_3:Third argument"]["valid"] is True
