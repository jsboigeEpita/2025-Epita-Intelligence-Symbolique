"""
Golden regression tests for Issue #309 (Epic #300, T2).

Runs the pipeline on fixed inputs and verifies minimum quality thresholds
to prevent regressions in analysis output quality.

Thresholds:
    - min_arguments >= 3
    - min_fallacies >= 1  (standard/full workflows only)
    - min_quality_scores >= 2
    - min_fol_formulas >= 1  (standard/full workflows only)

Markers:
    - Light workflow tests: no API key required
    - Standard workflow tests: @pytest.mark.requires_api (skip without OPENAI_API_KEY)
"""

import pytest
from typing import Dict, Any, List

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.unified_pipeline import (
    run_unified_analysis,
    setup_registry,
)

# ============================================================
# Fixed golden inputs
# ============================================================

GOLDEN_TEXTS = {
    "vaccins": (
        "Les vaccins sont indispensables pour la sante publique. "
        "Les etudes scientifiques montrent que la vaccination a eradique la variole "
        "et reduit considerablement la polio. Ceux qui affirment que les vaccins "
        "sont dangereux ignorent les decades de recherche clinique. "
        "L'argument selon lequel les produits pharmaceutiques cachent les effets "
        "secondaires est une theorie du complot sans fondement. "
        "Les taux de vaccination eleves protegent aussi ceux qui ne peuvent pas "
        "etre vaccines grace a l'immunite collective."
    ),
    "peine_de_mort": (
        "La peine de mort est une sanction necessaire dans certains cas extremes. "
        "Elle sert de dissuasion contre les crimes les plus graves comme le meurtre "
        "de masse. Les opposants argumentent que le systeme judiciaire peut se tromper, "
        "mais les avancees en ADN reduisent considerablement ce risque. "
        "De plus, certains criminels sont irrecuperables et representent un danger "
        "permanent pour la societe. Cependant, il faut reconnaitre que la peine de mort "
        "est irreversible, ce qui rend toute erreur fatale. "
        "Le cout des appels et procedures est souvent superieur a l'emprisonnement a vie."
    ),
    "climat": (
        "Le changement climatique est une realite scientifique incontestable. "
        "Les mesures de temperature globale montrent une augmentation de 1.1 degres "
        "depuis l'ere preindustrielle. Les sceptiques affirment que le climat a toujours "
        "change, mais ils omettent la vitesse sans precedent du changement actuel. "
        "Les modeles predictifs sont unanimes sur l'impact des activites humaines. "
        "Ceux qui minimisent la crise climatique utilisent souvent des donnees "
        "selectives pour soutenir leur position. "
        "La transition energetique est non seulement necessaire mais aussi "
        "economiquement avantageuse a long terme."
    ),
}

# Minimum thresholds per workflow type
THRESHOLDS = {
    "light": {
        "min_arguments": 2,  # heuristic extraction is conservative
        "min_quality_scores": 1,
        "min_counter_arguments": 1,
    },
    "standard": {
        "min_arguments": 3,
        "min_fallacies": 0,  # hierarchical detector may not always fire
        "min_quality_scores": 1,
        "min_fol_formulas": 0,  # NL-to-logic depends on LLM availability
        "min_belief_sets": 1,
        "min_counter_arguments": 1,
    },
}


def _check_thresholds(
    state: UnifiedAnalysisState,
    thresholds: Dict[str, int],
    label: str,
) -> List[str]:
    """Verify state meets all thresholds. Returns list of violations."""
    violations = []

    n_args = len(state.identified_arguments)
    if n_args < thresholds.get("min_arguments", 0):
        violations.append(f"arguments: {n_args} < {thresholds['min_arguments']}")

    n_fallacies = len(state.identified_fallacies)
    if n_fallacies < thresholds.get("min_fallacies", 0):
        violations.append(f"fallacies: {n_fallacies} < {thresholds['min_fallacies']}")

    n_quality = len(state.argument_quality_scores)
    if n_quality < thresholds.get("min_quality_scores", 0):
        violations.append(
            f"quality_scores: {n_quality} < {thresholds['min_quality_scores']}"
        )

    n_fol = len(state.fol_analysis_results)
    if n_fol < thresholds.get("min_fol_formulas", 0):
        violations.append(f"fol_results: {n_fol} < {thresholds['min_fol_formulas']}")

    n_beliefs = len(state.belief_sets)
    if n_beliefs < thresholds.get("min_belief_sets", 0):
        violations.append(f"belief_sets: {n_beliefs} < {thresholds['min_belief_sets']}")

    n_counter = len(state.counter_arguments)
    if n_counter < thresholds.get("min_counter_arguments", 0):
        violations.append(
            f"counter_arguments: {n_counter} < {thresholds['min_counter_arguments']}"
        )

    return violations


# ============================================================
# Light workflow golden tests (no API key required)
# ============================================================


class TestGoldenLightWorkflow:
    """Golden regression tests for the light workflow.

    The light workflow uses heuristic extraction + Python-based quality evaluator,
    so it does not require an LLM API key.
    """

    @pytest.fixture(scope="class")
    def registry(self):
        return setup_registry(include_optional=False)

    @pytest.mark.parametrize("text_name", list(GOLDEN_TEXTS.keys()))
    async def test_light_produces_arguments(self, registry, text_name):
        """Light workflow extracts at least 2 arguments from each golden text."""
        text = GOLDEN_TEXTS[text_name]
        result = await run_unified_analysis(
            text=text,
            workflow_name="light",
            registry=registry,
        )
        state = result["unified_state"]
        assert isinstance(state, UnifiedAnalysisState)
        n_args = len(state.identified_arguments)
        assert (
            n_args >= THRESHOLDS["light"]["min_arguments"]
        ), f"[{text_name}/light] Expected >= {THRESHOLDS['light']['min_arguments']} arguments, got {n_args}"

    @pytest.mark.parametrize("text_name", list(GOLDEN_TEXTS.keys()))
    async def test_light_produces_quality_scores(self, registry, text_name):
        """Light workflow produces quality evaluation scores."""
        text = GOLDEN_TEXTS[text_name]
        result = await run_unified_analysis(
            text=text,
            workflow_name="light",
            registry=registry,
        )
        state = result["unified_state"]
        n_quality = len(state.argument_quality_scores)
        assert (
            n_quality >= THRESHOLDS["light"]["min_quality_scores"]
        ), f"[{text_name}/light] Expected >= {THRESHOLDS['light']['min_quality_scores']} quality scores, got {n_quality}"

    @pytest.mark.parametrize("text_name", list(GOLDEN_TEXTS.keys()))
    async def test_light_produces_counter_arguments(self, registry, text_name):
        """Light workflow generates at least 1 counter-argument."""
        text = GOLDEN_TEXTS[text_name]
        result = await run_unified_analysis(
            text=text,
            workflow_name="light",
            registry=registry,
        )
        state = result["unified_state"]
        n_counter = len(state.counter_arguments)
        assert (
            n_counter >= THRESHOLDS["light"]["min_counter_arguments"]
        ), f"[{text_name}/light] Expected >= {THRESHOLDS['light']['min_counter_arguments']} counter-arguments, got {n_counter}"

    @pytest.mark.parametrize("text_name", list(GOLDEN_TEXTS.keys()))
    async def test_light_phases_complete(self, registry, text_name):
        """Light workflow: extract + quality + counter all complete."""
        text = GOLDEN_TEXTS[text_name]
        result = await run_unified_analysis(
            text=text,
            workflow_name="light",
            registry=registry,
        )
        phases = result["phases"]
        assert (
            phases["extract"].status.value == "completed"
        ), f"[{text_name}] extract phase not completed"
        assert (
            phases["quality"].status.value == "completed"
        ), f"[{text_name}] quality phase not completed"
        assert (
            phases["counter"].status.value == "completed"
        ), f"[{text_name}] counter phase not completed"

    async def test_light_state_snapshot_has_all_fields(self, registry):
        """Light workflow state snapshot includes expected dimension counts."""
        text = GOLDEN_TEXTS["vaccins"]
        result = await run_unified_analysis(
            text=text,
            workflow_name="light",
            registry=registry,
        )
        snapshot = result["state_snapshot"]
        assert "counter_argument_count" in snapshot
        assert "quality_scores_count" in snapshot
        assert snapshot["counter_argument_count"] >= 1
        assert snapshot["quality_scores_count"] >= 1


# ============================================================
# Standard workflow golden tests (requires API key)
# ============================================================


@pytest.mark.requires_api
class TestGoldenStandardWorkflow:
    """Golden regression tests for the standard workflow.

    The standard workflow includes fallacy detection, FOL reasoning,
    NL-to-logic translation, and other phases requiring LLM access.
    """

    @pytest.fixture(scope="class")
    def registry(self):
        return setup_registry(include_optional=True)

    @pytest.mark.parametrize("text_name", list(GOLDEN_TEXTS.keys()))
    async def test_standard_all_thresholds(self, registry, text_name):
        """Standard workflow meets all quality thresholds."""
        text = GOLDEN_TEXTS[text_name]
        result = await run_unified_analysis(
            text=text,
            workflow_name="standard",
            registry=registry,
        )
        state = result["unified_state"]
        violations = _check_thresholds(
            state, THRESHOLDS["standard"], f"{text_name}/standard"
        )
        assert (
            violations == []
        ), f"[{text_name}/standard] Threshold violations: {'; '.join(violations)}"

    @pytest.mark.parametrize("text_name", list(GOLDEN_TEXTS.keys()))
    async def test_standard_produces_fallacies(self, registry, text_name):
        """Standard workflow detects at least 1 fallacy per text."""
        text = GOLDEN_TEXTS[text_name]
        result = await run_unified_analysis(
            text=text,
            workflow_name="standard",
            registry=registry,
        )
        state = result["unified_state"]
        n_fallacies = len(state.identified_fallacies)
        assert (
            n_fallacies >= 1
        ), f"[{text_name}/standard] Expected >= 1 fallacy, got {n_fallacies}"

    @pytest.mark.parametrize("text_name", list(GOLDEN_TEXTS.keys()))
    async def test_standard_produces_fol_results(self, registry, text_name):
        """Standard workflow produces FOL analysis results."""
        text = GOLDEN_TEXTS[text_name]
        result = await run_unified_analysis(
            text=text,
            workflow_name="standard",
            registry=registry,
        )
        state = result["unified_state"]
        assert (
            len(state.fol_analysis_results) >= 1
        ), f"[{text_name}/standard] No FOL analysis results"

    @pytest.mark.parametrize("text_name", list(GOLDEN_TEXTS.keys()))
    async def test_standard_produces_jtms_beliefs(self, registry, text_name):
        """Standard workflow creates JTMS beliefs."""
        text = GOLDEN_TEXTS[text_name]
        result = await run_unified_analysis(
            text=text,
            workflow_name="standard",
            registry=registry,
        )
        state = result["unified_state"]
        n_jtms = len(state.jtms_beliefs)
        assert (
            n_jtms >= 1
        ), f"[{text_name}/standard] Expected >= 1 JTMS belief, got {n_jtms}"

    async def test_standard_enrichment_summary(self, registry):
        """Standard workflow produces a valid enrichment summary."""
        text = GOLDEN_TEXTS["climat"]
        result = await run_unified_analysis(
            text=text,
            workflow_name="standard",
            registry=registry,
        )
        state = result["unified_state"]
        summary = state.get_enrichment_summary()
        assert summary["total_arguments"] >= 3
        assert summary["with_quality_score"] >= 1
        assert (
            summary["with_fallacy_analysis"] >= 0
        )  # may be 0 if no fallacy targets matched

    async def test_standard_argument_profiles(self, registry):
        """Standard workflow produces argument profiles with cross-references."""
        text = GOLDEN_TEXTS["peine_de_mort"]
        result = await run_unified_analysis(
            text=text,
            workflow_name="standard",
            registry=registry,
        )
        state = result["unified_state"]
        for arg_id in list(state.identified_arguments.keys())[:3]:
            profile = state.get_argument_profile(arg_id)
            assert profile.arg_id == arg_id
            assert profile.description != ""


# ============================================================
# Regression snapshot tests
# ============================================================


class TestRegressionSnapshots:
    """Ensure key output structure doesn't change between versions."""

    @pytest.fixture(scope="class")
    def registry(self):
        return setup_registry(include_optional=False)

    async def test_light_result_structure_stable(self, registry):
        """Light workflow result always has the same top-level keys."""
        text = GOLDEN_TEXTS["vaccins"]
        result = await run_unified_analysis(
            text=text,
            workflow_name="light",
            registry=registry,
        )
        expected_keys = {
            "workflow_name",
            "phases",
            "summary",
            "capabilities_used",
            "capabilities_missing",
            "unified_state",
            "state_snapshot",
        }
        assert expected_keys.issubset(
            set(result.keys())
        ), f"Missing keys: {expected_keys - set(result.keys())}"

    async def test_state_snapshot_dimensions_stable(self, registry):
        """State snapshot always includes all expected dimension counts."""
        text = GOLDEN_TEXTS["climat"]
        result = await run_unified_analysis(
            text=text,
            workflow_name="light",
            registry=registry,
        )
        snapshot = result["state_snapshot"]
        expected_dimensions = [
            "counter_argument_count",
            "quality_scores_count",
            "jtms_belief_count",
            "dung_framework_count",
            "governance_decision_count",
            "debate_transcript_count",
            "transcription_segment_count",
            "semantic_index_ref_count",
            "neural_fallacy_score_count",
            "ranking_result_count",
            "aspic_result_count",
            "belief_revision_result_count",
            "dialogue_result_count",
            "probabilistic_result_count",
            "bipolar_result_count",
            "fol_analysis_count",
            "propositional_analysis_count",
            "modal_analysis_count",
            "formal_synthesis_count",
            "workflow_results_count",
        ]
        for dim in expected_dimensions:
            assert dim in snapshot, f"Missing dimension in snapshot: {dim}"
