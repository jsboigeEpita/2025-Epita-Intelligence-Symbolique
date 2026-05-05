"""Tests for _invoke_jtms with real dependency network (#208-G).

Verifies the JTMS phase builds proper belief networks from upstream phases.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestInvokeJTMS:
    """Tests for _invoke_jtms function."""

    async def test_args_and_claims_produce_in_list_justifications(self):
        """Arguments collectively support claims (not sequential chain)."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Evidence supports the claim"},
                    {"text": "Statistical data confirms"},
                ],
                "claims": [{"text": "The policy is effective"}],
            }
        }
        result = await _invoke_jtms("text", context)

        assert result["has_real_dependencies"] is True
        assert result["belief_count"] >= 3  # 2 args + 1 claim
        # The claim should have justifications with in_list containing the arguments
        claim_belief = result["beliefs"].get("The policy is effective")
        assert claim_belief is not None
        assert len(claim_belief["justifications"]) > 0
        # Check in_list contains both arguments
        in_list = claim_belief["justifications"][0]["in_list"]
        assert len(in_list) == 2

    async def test_fallacies_retract_undermined_beliefs(self):
        """Detected fallacies → beliefs are retracted."""
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

        assert result["undermined_count"] > 0
        assert result["fallacy_count"] == 1
        # The argument belief should be invalid
        arg_belief = result["beliefs"].get("He is wrong because he is biased")
        assert arg_belief is not None
        assert arg_belief["valid"] is False

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

        arg_belief = result["beliefs"].get("A well-structured argument with evidence")
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
        """Args without claims → overall_argument_validity conclusion."""
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

        # Should create synthetic conclusion
        assert "overall_argument_validity" in result["beliefs"]
        synth = result["beliefs"]["overall_argument_validity"]
        assert len(synth["justifications"]) > 0
        # Both args should be in the IN-list
        in_list = synth["justifications"][0]["in_list"]
        assert len(in_list) == 2

    async def test_beliefs_have_structured_justifications(self):
        """Belief justifications expose in_list and out_list (not just repr)."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Premise one"}],
                "claims": [{"text": "Conclusion one"}],
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
        """Multiple fallacies target different arguments by index."""
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
                    {"fallacy_type": "ad_hominem", "explanation": "attacks person"},
                    {"fallacy_type": "strawman", "explanation": "misrepresents"},
                ]
            },
        }
        result = await _invoke_jtms("text", context)

        assert result["fallacy_count"] == 2
        assert result["undermined_count"] >= 2
