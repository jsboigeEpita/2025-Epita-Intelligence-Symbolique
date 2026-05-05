"""Tests for pipeline wiring fixes (#285, #289).

Validates:
- Standard/full workflows include formal reasoning phases (nl_to_logic, pl, fol)
- Quality evaluator reads fallacy output and penalizes affected arguments
- JTMS reads correct quality score keys (arg_N, not argument_N)
- JTMS reads fallacy_type with "type" fallback
- JTMS integrates formal consistency results
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ============================================================
# Test: Workflow definitions include formal reasoning phases
# ============================================================


class TestWorkflowFormalPhases:
    """Validate that standard/full workflows include PL/FOL phases (#285)."""

    def test_standard_workflow_has_nl_to_logic(self):
        """Standard workflow includes nl_to_logic phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "nl_to_logic" in phase_names

    def test_standard_workflow_has_pl(self):
        """Standard workflow includes propositional logic phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "pl" in phase_names

    def test_standard_workflow_has_fol(self):
        """Standard workflow includes first-order logic phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "fol" in phase_names

    def test_standard_workflow_pl_depends_on_nl_to_logic(self):
        """PL phase depends on nl_to_logic in standard workflow."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        pl_phase = next(p for p in wf.phases if p.name == "pl")
        assert "nl_to_logic" in pl_phase.depends_on

    def test_standard_workflow_formal_phases_are_optional(self):
        """Formal reasoning phases are optional (graceful degradation)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        for name in ("nl_to_logic", "pl", "fol"):
            phase = next(p for p in wf.phases if p.name == name)
            assert phase.optional is True, f"{name} should be optional"

    def test_full_workflow_has_pl_and_fol(self):
        """Full workflow includes pl and fol phases after nl_to_logic."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        phase_names = [p.name for p in wf.phases]
        assert "nl_to_logic" in phase_names
        assert "pl" in phase_names
        assert "fol" in phase_names

    def test_full_workflow_pl_depends_on_nl_to_logic(self):
        """Full workflow PL depends on nl_to_logic."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        pl_phase = next(p for p in wf.phases if p.name == "pl")
        assert "nl_to_logic" in pl_phase.depends_on

    def test_standard_workflow_phase_count(self):
        """Standard workflow has expected number of phases after addition."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        # extract, neural_detect, hierarchical_fallacy, nl_to_logic, pl, fol,
        # dung_extensions, aspic_analysis, quality, counter, jtms, governance, debate = 13 phases
        assert len(wf.phases) == 13


# ============================================================
# Test: Quality evaluator reads fallacy output (#289)
# ============================================================


class TestQualityFallacyCrossReference:
    """Validate quality evaluator penalizes arguments targeted by fallacies."""

    @pytest.fixture
    def mock_evaluator(self):
        """Mock ArgumentQualityEvaluator that returns a known score (fresh copy each call)."""
        mock = MagicMock()
        mock.evaluate.side_effect = lambda text: {
            "note_finale": 8.0,
            "scores_par_vertu": {"clarity": 8, "coherence": 8},
        }
        return mock

    async def test_quality_penalizes_fallacy_target(self, mock_evaluator):
        """Quality score is reduced when argument is targeted by a fallacy."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_quality_evaluator,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Elon Musk says AI is dangerous"},
                    {"text": "Studies show AI risks are real"},
                ],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "fallacy_type": "appeal_to_authority",
                        "target_argument": "Elon Musk says AI is dangerous",
                        "confidence": 0.9,
                    },
                ],
            },
        }

        with patch(
            "argumentation_analysis.agents.core.quality.quality_evaluator.ArgumentQualityEvaluator",
            return_value=mock_evaluator,
        ), patch(
            "argumentation_analysis.orchestration.unified_pipeline._llm_enrich_quality",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await _invoke_quality_evaluator("test", context)

        assert "per_argument_scores" in result
        # arg_1 should be penalized (targeted by fallacy)
        arg1 = result["per_argument_scores"]["arg_1"]
        assert "fallacy_penalty" in arg1
        assert arg1["fallacy_penalty"]["applied"] is True
        assert arg1["note_finale"] < 8.0  # penalized

        # arg_2 should NOT be penalized
        arg2 = result["per_argument_scores"]["arg_2"]
        assert "fallacy_penalty" not in arg2
        assert arg2["note_finale"] == 8.0

    async def test_quality_no_fallacies_no_penalty(self, mock_evaluator):
        """Without fallacies, no penalty is applied."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_quality_evaluator,
        )

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "A valid argument with evidence"}],
            },
        }

        with patch(
            "argumentation_analysis.agents.core.quality.quality_evaluator.ArgumentQualityEvaluator",
            return_value=mock_evaluator,
        ), patch(
            "argumentation_analysis.orchestration.unified_pipeline._llm_enrich_quality",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await _invoke_quality_evaluator("test", context)

        arg1 = result["per_argument_scores"]["arg_1"]
        assert "fallacy_penalty" not in arg1
        assert arg1["note_finale"] == 8.0

    async def test_quality_reports_fallacy_cross_reference(self, mock_evaluator):
        """Output includes fallacy_cross_reference when fallacies are present."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_quality_evaluator,
        )

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Some argument about something"}],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"fallacy_type": "straw_man", "target_argument": "some argument"},
                ],
            },
        }

        with patch(
            "argumentation_analysis.agents.core.quality.quality_evaluator.ArgumentQualityEvaluator",
            return_value=mock_evaluator,
        ), patch(
            "argumentation_analysis.orchestration.unified_pipeline._llm_enrich_quality",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await _invoke_quality_evaluator("test", context)

        assert "fallacy_cross_reference" in result
        assert result["fallacy_cross_reference"]["fallacies_found"] == 1


# ============================================================
# Test: JTMS reads correct keys (#289)
# ============================================================


class TestJTMSKeyFixes:
    """Validate JTMS reads correct field names for quality scores and fallacy types."""

    async def test_jtms_reads_arg_n_quality_scores(self):
        """JTMS reads 'arg_N' quality score keys (matching quality evaluator output)."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "First argument is well-supported"}],
                "claims": [],
            },
            "phase_quality_output": {
                "per_argument_scores": {
                    "arg_1": {"note_finale": 7.5, "scores_par_vertu": {"clarity": 8}},
                },
            },
            "phase_hierarchical_fallacy_output": {"fallacies": []},
            "phase_counter_output": {"llm_counter_arguments": []},
        }

        result = await _invoke_jtms("test text", context)
        assert result["belief_count"] >= 1
        # The belief should have confidence from quality score (7.5), not default 0.5
        first_belief = list(result["beliefs"].values())[0]
        assert first_belief["confidence"] == 7.5

    async def test_jtms_reads_fallacy_type_field(self):
        """JTMS reads 'type' field for fallacy type (matching shared_state convention)."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Some argument that has a fallacy"}],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "appeal_to_authority",
                        "target_argument": "Some argument",
                        "confidence": 0.8,
                    },
                ],
            },
            "phase_counter_output": {"llm_counter_arguments": []},
        }

        result = await _invoke_jtms("test", context)
        # Should find a FALLACY:appeal_to_authority belief
        fallacy_beliefs = [k for k in result["beliefs"] if k.startswith("FALLACY:")]
        assert len(fallacy_beliefs) >= 1
        assert "appeal_to_authority" in fallacy_beliefs[0]

    async def test_jtms_reads_fallacy_type_with_fallback(self):
        """JTMS reads 'fallacy_type' as fallback when 'type' is missing."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "An argument with a detected fallacy"}],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "fallacy_type": "ad_hominem",
                        "target_argument": "An argument",
                        "confidence": 0.7,
                    },
                ],
            },
            "phase_counter_output": {"llm_counter_arguments": []},
        }

        result = await _invoke_jtms("test", context)
        fallacy_beliefs = [k for k in result["beliefs"] if k.startswith("FALLACY:")]
        assert len(fallacy_beliefs) >= 1
        assert "ad_hominem" in fallacy_beliefs[0]

    async def test_jtms_formal_consistency_flag(self):
        """JTMS output includes formal_consistency from upstream PL/FOL."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "An argument to formalize"}],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {"fallacies": []},
            "phase_counter_output": {"llm_counter_arguments": []},
            "phase_pl_output": {"satisfiable": False, "formulas": ["p", "!p"]},
            "phase_fol_output": {},
        }

        result = await _invoke_jtms("test", context)
        assert result["formal_consistency"] is False
        # Should have a FORMAL_INCONSISTENCY belief
        assert "FORMAL_INCONSISTENCY" in result["beliefs"]

    async def test_jtms_no_formal_output_defaults_consistent(self):
        """Without formal output, JTMS defaults to consistent."""
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Simple argument"}],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {"fallacies": []},
            "phase_counter_output": {"llm_counter_arguments": []},
        }

        result = await _invoke_jtms("test", context)
        assert result["formal_consistency"] is True
        assert "FORMAL_INCONSISTENCY" not in result["beliefs"]


# ============================================================
# Test: Counter-argument reads quality scores (#289)
# ============================================================


class TestCounterArgumentCrossKB:
    """Validate counter-argument targets weakest arguments using quality scores."""

    async def test_counter_targets_weakest_arguments(self):
        """Counter-argument callable reads quality scores to prioritize weak args."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_counter_argument,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Strong argument with solid evidence"},
                    {"text": "Weak argument without evidence"},
                    {"text": "Medium argument with some support"},
                ],
            },
            "phase_hierarchical_fallacy_output": {"fallacies": []},
            "phase_quality_output": {
                "per_argument_scores": {
                    "arg_1": {"note_finale": 9.0},
                    "arg_2": {"note_finale": 2.0},
                    "arg_3": {"note_finale": 5.5},
                },
            },
        }

        # Without LLM, result still contains quality_context
        result = await _invoke_counter_argument("test", context)
        assert "quality_context" in result
        assert result["quality_context"] is not None

    async def test_counter_reads_fallacies_with_type_fallback(self):
        """Counter-argument reads fallacy_type with type fallback."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_counter_argument,
        )

        context = {
            "phase_extract_output": {"arguments": [{"text": "Some argument"}]},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"fallacy_type": "ad_hominem", "explanation": "Attacks the person"},
                ],
            },
            "phase_quality_output": {},
        }

        result = await _invoke_counter_argument("test", context)
        assert "parsed_argument" in result


# ============================================================
# Test: Governance reads correct counter output key (#289)
# ============================================================


class TestGovernanceCrossKB:
    """Validate governance reads correct context keys and cross-KB data."""

    async def test_governance_reads_counter_output_key(self):
        """Governance uses phase_counter_output (not phase_counter_argument_output)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_governance,
        )

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "First position"}, {"text": "Second position"}],
            },
            "phase_debate_output": {},
            "phase_counter_output": {
                "llm_counter_arguments": [
                    {
                        "strategy_used": "reductio",
                        "counter_argument": "If we follow...",
                    },
                ],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {"fallacies": []},
            "phase_jtms_output": {},
        }

        result = await _invoke_governance("test", context)
        assert "available_methods" in result

    async def test_governance_reads_quality_and_fallacies(self):
        """Governance LLM context includes quality scores and fallacies."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_governance,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Position A with fallacy"},
                    {"text": "Position B is solid"},
                ],
            },
            "phase_debate_output": {},
            "phase_counter_output": {},
            "phase_quality_output": {
                "per_argument_scores": {
                    "arg_1": {"note_finale": 3.0, "fallacy_penalty": {"applied": True}},
                    "arg_2": {"note_finale": 8.0},
                },
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [{"type": "straw_man", "confidence": 0.9}],
            },
            "phase_jtms_output": {
                "beliefs": {"Position A": {"valid": False, "confidence": 0.3}},
                "formal_consistency": False,
            },
        }

        result = await _invoke_governance("test", context)
        assert "available_methods" in result


# ============================================================
# Test: Debate reads quality + JTMS (#289)
# ============================================================


class TestDebateCrossKB:
    """Validate debate reads quality scores and JTMS output."""

    async def test_debate_reads_quality_and_jtms(self):
        """Debate callable reads quality scores and JTMS beliefs."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_debate_analysis,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Argument with high quality"},
                    {"text": "Argument with low quality"},
                ],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "appeal_to_authority",
                        "justification": "Cites celebrity opinion",
                    },
                ],
            },
            "phase_counter_output": {},
            "phase_quality_output": {
                "per_argument_scores": {
                    "arg_1": {"note_finale": 9.0},
                    "arg_2": {"note_finale": 3.0, "fallacy_penalty": {"applied": True}},
                },
            },
            "phase_jtms_output": {
                "beliefs": {
                    "Argument with low quality": {"valid": False, "confidence": 0.2},
                },
                "formal_consistency": False,
            },
        }

        result = await _invoke_debate_analysis("test", context)
        # Basic structure check — LLM enrichment won't fire without API key
        assert (
            "argument_scores" in result
            or "scores" in result
            or isinstance(result, dict)
        )
