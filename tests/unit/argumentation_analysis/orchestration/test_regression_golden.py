"""Golden regression tests for pipeline output (#309).

Validates that the pipeline infrastructure produces state with minimum
thresholds when invoke callables return realistic outputs. Prevents
regressions in state wiring, state writers, and cross-KB integration.

Thresholds (from #309 spec):
  - min_arguments ≥ 3
  - min_fallacies ≥ 1
  - min_quality_scores ≥ 2
  - min_fol_formulas ≥ 1

Two test layers:
  1. Unit-level: mocked invoke callables → state populated correctly
  2. Integration: real pipeline run with LLM (slow, requires_api)
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowExecutor,
    PhaseResult,
    PhaseStatus,
)
from argumentation_analysis.core.capability_registry import CapabilityRegistry

# ── Golden input text (known to contain fallacies + arguments) ────────────

GOLDEN_TEXT = (
    "Le Premier ministre a déclaré que la réforme des retraites est nécessaire "
    "car tous les pays européens l'ont déjà faite. C'est un argument d'autorité "
    "qui ne tient pas compte des différences structurelles entre les systèmes. "
    "De plus, affirmer que « si nous n'agissons pas maintenant, le système "
    "s'effondrera dans cinq ans » est un appel à la peur classique. "
    "Les syndicats rétorquent que le gouvernement utilise un sophisme naturaliste "
    "en prétendant que travailler plus longtemps est « dans l'ordre des choses ». "
    "Par ailleurs, le ministre des finances a présenté des chiffres montrant "
    "que le déficit atteindra 2.3% du PIB d'ici 2030, mais cette projection "
    "repose sur des hypothèses de croissance optimistes de 1.8% par an. "
    "L'opposition dénonce un homme de paille : personne n'a proposé de supprimer "
    "les retraites, seulement de les réformer différemment. Enfin, le recours "
    "à l'argument « pensez à vos enfants » constitue un appel à l'émotion "
    "qui détourne le débat des questions techniques de financement."
)


# ── Realistic mock outputs for each pipeline phase ────────────────────────

# Mock outputs formatted to match what each state writer expects.
# See _write_*_to_state in unified_pipeline.py for format specs.

MOCK_EXTRACTION_OUTPUT = {
    # _write_fact_extraction_to_state reads "arguments" (list of {text, source_quote?})
    "arguments": [
        {
            "text": "La réforme des retraites est nécessaire car tous les pays européens l'ont déjà faite."
        },
        {
            "text": "Si nous n'agissons pas maintenant, le système s'effondrera dans cinq ans."
        },
        {"text": "Travailler plus longtemps est dans l'ordre des choses."},
        {"text": "Le déficit atteindra 2.3% du PIB d'ici 2030."},
        {"text": "Pensez à vos enfants — il faut agir pour leur avenir."},
    ],
    "claims": [
        {"text": "Tous les pays européens ont déjà fait la réforme."},
        {"text": "Le système s'effondrera dans cinq ans sans action."},
    ],
}

MOCK_HIERARCHICAL_FALLACY_OUTPUT = {
    # _write_hierarchical_fallacy_to_state reads "fallacies" (list of dicts)
    "fallacies": [
        {
            "type": "Argument d'autorité",
            "confidence": 0.85,
            "explanation": "Appel à l'autorité des autres pays",
            "taxonomy_pk": "4",
        },
        {
            "type": "Appel à la peur",
            "confidence": 0.92,
            "explanation": "Menace d'effondrement du système",
            "taxonomy_pk": "340",
        },
    ],
}

MOCK_QUALITY_OUTPUT = {
    # _write_quality_to_state reads "per_argument_scores" (dict arg_id → {scores_par_vertu, note_finale, llm_assessment})
    "per_argument_scores": {
        "arg_1": {
            "scores_par_vertu": {"clarity": 0.6, "relevance": 0.5},
            "note_finale": 0.45,
            "llm_assessment": "Weak authority argument",
        },
        "arg_2": {
            "scores_par_vertu": {"clarity": 0.7, "relevance": 0.4},
            "note_finale": 0.35,
            "llm_assessment": "Fear-based",
        },
        "arg_3": {
            "scores_par_vertu": {"clarity": 0.5, "relevance": 0.3},
            "note_finale": 0.30,
            "llm_assessment": "Naturalistic fallacy",
        },
        "arg_4": {
            "scores_par_vertu": {"clarity": 0.8, "relevance": 0.7},
            "note_finale": 0.65,
            "llm_assessment": "Quantitative but assumption-based",
        },
        "arg_5": {
            "scores_par_vertu": {"clarity": 0.6, "relevance": 0.2},
            "note_finale": 0.25,
            "llm_assessment": "Emotional appeal",
        },
    },
}

MOCK_COUNTER_OUTPUT = {
    # _write_counter_argument_to_state reads "llm_counter_arguments" (list of dicts)
    "llm_counter_arguments": [
        {
            "target_argument": "La réforme est nécessaire car tous les pays européens l'ont faite.",
            "counter_argument": "L'argument d'autorité ignore les spécificités nationales.",
            "strategy_used": "counter_example",
            "strength": "strong",
        },
        {
            "target_argument": "Le système s'effondrera dans cinq ans.",
            "counter_argument": "Les projections à 5 ans sont rarement fiables.",
            "strategy_used": "reductio_ad_absurdum",
            "strength": "moderate",
        },
        {
            "target_argument": "Travailler plus longtemps est dans l'ordre des choses.",
            "counter_argument": "Ce qui est 'naturel' n'est pas nécessairement juste.",
            "strategy_used": "distinction",
            "strength": "strong",
        },
    ],
}

MOCK_JTMS_OUTPUT = {
    # _write_jtms_to_state reads "beliefs" (dict name → {valid, justifications})
    "beliefs": {
        "reform_necessary": {"valid": True, "justifications": ["european_precedent"]},
        "system_collapse": {"valid": False, "justifications": ["fear_projection"]},
        "deficit_projection": {"valid": True, "justifications": ["minister_data"]},
    },
}

MOCK_NL_TO_LOGIC_OUTPUT = {
    # _write_nl_to_logic_to_state reads "translations" (list of {formula, logic_type, is_valid, ...})
    "translations": [
        {
            "original_text": "Si réforme européenne alors réforme française nécessaire",
            "formula": "european_reform => french_reform_needed",
            "logic_type": "propositional",
            "is_valid": True,
            "confidence": 0.8,
        },
        {
            "original_text": "Si croissance 1.8% alors déficit 2.3%",
            "formula": "growth_1_8 => deficit_2_3",
            "logic_type": "propositional",
            "is_valid": True,
            "confidence": 0.7,
        },
    ],
}

MOCK_PL_OUTPUT = {
    # _write_propositional_to_state reads "formulas", "satisfiable", "model"
    "formulas": [
        "european_reform => french_reform_needed",
        "growth_1_8 => deficit_2_3",
    ],
    "satisfiable": True,
    "model": {"european_reform": True, "french_reform_needed": True},
}

MOCK_FOL_OUTPUT = {
    # _write_fol_to_state reads "formulas", "consistent", "inferences", "confidence"
    "formulas": [
        "forall x (EuropeanCountry(x) => ReformDone(x)) => ReformNeeded(France)"
    ],
    "consistent": True,
    "inferences": ["ReformNeeded(France)"],
    "confidence": 0.85,
}

MOCK_DEBATE_OUTPUT = {
    # _write_debate_to_state reads "winner", "llm_debate_assessment.key_exchanges"
    "winner": "Opponent",
    "llm_debate_assessment": {
        "key_exchanges": [
            {"point": "Reform is necessary", "rebuttal": "Reform model is flawed"},
            {
                "point": "All countries did it",
                "rebuttal": "National specificities differ",
            },
        ],
    },
}

MOCK_GOVERNANCE_OUTPUT = {
    # _write_governance_to_state reads "llm_governance_assessment.stakeholder_analysis"
    "llm_governance_assessment": {
        "stakeholder_analysis": [
            {"agent": "government", "influence": 0.7},
            {"agent": "unions", "influence": 0.5},
            {"agent": "citizens", "influence": 0.3},
        ],
    },
    "vote_results": {"method": "copeland", "winner": "alternative_reform"},
}

MOCK_CAMEMBERT_OUTPUT = {
    # _write_camembert_to_state reads "detections" (list of {text, label, confidence})
    "detections": [
        {
            "text": "Pensez à vos enfants",
            "label": "Appel à l'émotion",
            "confidence": 0.78,
        },
    ],
}


# ============================================================
# Helper: build a registry with mocked invoke callables
# ============================================================


def _build_golden_registry() -> CapabilityRegistry:
    """Create a registry with mocked invoke callables returning golden data.

    Overrides ALL registrations matching each capability so that no real
    LLM/Tweety/network calls are made during golden tests.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        setup_registry,
    )

    # Start with real registry (so workflow phases resolve correctly)
    registry = setup_registry(include_optional=True)

    # Override invoke callables with mocks returning golden data
    mock_map = {
        "fact_extraction": MOCK_EXTRACTION_OUTPUT,
        "hierarchical_fallacy_detection": MOCK_HIERARCHICAL_FALLACY_OUTPUT,
        "argument_quality": MOCK_QUALITY_OUTPUT,
        "counter_argument_generation": MOCK_COUNTER_OUTPUT,
        "belief_maintenance": MOCK_JTMS_OUTPUT,
        "nl_to_logic_translation": MOCK_NL_TO_LOGIC_OUTPUT,
        "propositional_logic": MOCK_PL_OUTPUT,
        "fol_reasoning": MOCK_FOL_OUTPUT,
        "adversarial_debate": MOCK_DEBATE_OUTPUT,
        "governance_simulation": MOCK_GOVERNANCE_OUTPUT,
        "neural_fallacy_detection": MOCK_CAMEMBERT_OUTPUT,
    }

    for cap_name, mock_output in mock_map.items():
        # Override ALL registrations matching this capability (not just the first)
        for reg_name, reg in registry._registrations.items():
            if cap_name in reg.capabilities:

                async def _mock_invoke(input_text, context, _out=mock_output):
                    return _out

                reg.invoke = _mock_invoke

    # Also override any remaining registrations that have real invoke callables
    # but aren't in our mock map (e.g. speech, semantic_indexing, etc.)
    # — set them to return empty dicts so they don't make real calls
    for reg_name, reg in registry._registrations.items():
        has_mock = any(cap in mock_map for cap in reg.capabilities)
        if not has_mock and reg.invoke is not None:

            async def _noop_invoke(input_text, context):
                return {}

            reg.invoke = _noop_invoke

    return registry


# ============================================================
# Layer 1: Golden state population tests (no LLM)
# ============================================================


@pytest.mark.unit
class TestGoldenStatePipeline:
    """Verify that pipeline with golden mock data produces state meeting thresholds."""

    @pytest.fixture
    def golden_registry(self):
        return _build_golden_registry()

    @pytest.fixture
    def golden_state(self):
        return UnifiedAnalysisState(GOLDEN_TEXT)

    async def test_standard_workflow_populates_arguments(
        self, golden_registry, golden_state
    ):
        """Standard workflow extracts ≥3 arguments into state."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(golden_registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=golden_state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        assert (
            len(golden_state.identified_arguments) >= 3
        ), f"Expected ≥3 arguments, got {len(golden_state.identified_arguments)}"

    async def test_standard_workflow_populates_fallacies(
        self, golden_registry, golden_state
    ):
        """Standard workflow detects ≥1 fallacy into state."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(golden_registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=golden_state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        assert (
            len(golden_state.identified_fallacies) >= 1
        ), f"Expected ≥1 fallacy, got {len(golden_state.identified_fallacies)}"

    async def test_standard_workflow_populates_quality_scores(
        self, golden_registry, golden_state
    ):
        """Standard workflow produces ≥2 quality scores."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(golden_registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=golden_state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        assert (
            len(golden_state.argument_quality_scores) >= 2
        ), f"Expected ≥2 quality scores, got {len(golden_state.argument_quality_scores)}"

    async def test_standard_workflow_populates_fol_results(
        self, golden_registry, golden_state
    ):
        """Standard workflow produces ≥1 FOL analysis result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(golden_registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=golden_state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        assert (
            len(golden_state.fol_analysis_results) >= 1
        ), f"Expected ≥1 FOL result, got {len(golden_state.fol_analysis_results)}"

    async def test_standard_workflow_populates_counter_arguments(
        self, golden_registry, golden_state
    ):
        """Standard workflow produces counter-arguments."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(golden_registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=golden_state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        assert (
            len(golden_state.counter_arguments) >= 1
        ), f"Expected ≥1 counter-argument, got {len(golden_state.counter_arguments)}"

    async def test_standard_workflow_populates_jtms_beliefs(
        self, golden_registry, golden_state
    ):
        """Standard workflow produces JTMS beliefs."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(golden_registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=golden_state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        assert (
            len(golden_state.jtms_beliefs) >= 1
        ), f"Expected ≥1 JTMS belief, got {len(golden_state.jtms_beliefs)}"

    async def test_standard_workflow_populates_debate(
        self, golden_registry, golden_state
    ):
        """Standard workflow produces debate transcript."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(golden_registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=golden_state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        assert (
            len(golden_state.debate_transcripts) >= 1
        ), f"Expected ≥1 debate transcript, got {len(golden_state.debate_transcripts)}"

    async def test_standard_workflow_populates_governance(
        self, golden_registry, golden_state
    ):
        """Standard workflow produces governance decisions."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(golden_registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=golden_state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        assert (
            len(golden_state.governance_decisions) >= 1
        ), f"Expected ≥1 governance decision, got {len(golden_state.governance_decisions)}"


# ============================================================
# Layer 1b: Golden snapshot consistency tests
# ============================================================


@pytest.mark.unit
class TestGoldenSnapshotConsistency:
    """Verify that state snapshot accurately reflects populated state."""

    async def test_snapshot_reflects_all_golden_fields(self):
        """State snapshot summarize=True shows non-zero counts for all golden fields."""
        registry = _build_golden_registry()
        state = UnifiedAnalysisState(GOLDEN_TEXT)

        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        snapshot = state.get_state_snapshot(summarize=True)

        # Core fields from #309 thresholds
        assert (
            snapshot.get("argument_count", 0) >= 3
        ), f"argument_count: {snapshot.get('argument_count', 0)}"
        assert (
            snapshot.get("fallacy_count", 0) >= 1
        ), f"fallacy_count: {snapshot.get('fallacy_count', 0)}"
        assert (
            snapshot.get("quality_scores_count", 0) >= 2
        ), f"quality_scores_count: {snapshot.get('quality_scores_count', 0)}"

    async def test_snapshot_has_correct_keys(self):
        """State snapshot has all expected summary keys."""
        state = UnifiedAnalysisState("Test text")
        snapshot = state.get_state_snapshot(summarize=True)

        expected_keys = [
            "counter_argument_count",
            "quality_scores_count",
            "jtms_belief_count",
            "debate_transcript_count",
            "governance_decision_count",
            "fol_analysis_count",
            "propositional_analysis_count",
        ]
        for key in expected_keys:
            assert key in snapshot, f"Missing key: {key}"

    async def test_full_workflow_meets_thresholds(self):
        """Full workflow also meets golden thresholds."""
        registry = _build_golden_registry()
        state = UnifiedAnalysisState(GOLDEN_TEXT)

        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(registry)
        workflow = build_full_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        snapshot = state.get_state_snapshot(summarize=True)
        assert snapshot.get("argument_count", 0) >= 3
        assert snapshot.get("fallacy_count", 0) >= 1
        assert snapshot.get("quality_scores_count", 0) >= 2


# ============================================================
# Layer 1c: Cross-referencing golden tests (#302)
# ============================================================


@pytest.mark.unit
class TestGoldenCrossReferencing:
    """Verify cross-referencing works on golden state."""

    async def test_enrichment_summary_has_coverage(self):
        """get_enrichment_summary() returns non-zero coverage after golden pipeline."""
        registry = _build_golden_registry()
        state = UnifiedAnalysisState(GOLDEN_TEXT)

        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        summary = state.get_enrichment_summary()
        assert summary["total_arguments"] >= 3
        # At least some arguments should have quality scores
        assert summary.get("with_quality_score", 0) >= 1

    async def test_argument_profile_available(self):
        """get_argument_profile() works on golden state arguments."""
        registry = _build_golden_registry()
        state = UnifiedAnalysisState(GOLDEN_TEXT)

        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        executor = WorkflowExecutor(registry)
        workflow = build_standard_workflow()
        await executor.execute(
            workflow,
            input_data=GOLDEN_TEXT,
            state=state,
            state_writers=CAPABILITY_STATE_WRITERS,
        )

        if state.identified_arguments:
            first_arg_id = next(iter(state.identified_arguments))
            profile = state.get_argument_profile(first_arg_id)
            assert profile is not None
            assert profile.arg_id == first_arg_id


# ============================================================
# Layer 2: run_unified_analysis integration (needs LLM)
# ============================================================


@pytest.mark.slow
@pytest.mark.requires_api
@pytest.mark.unit
class TestGoldenIntegration:
    """Full pipeline integration — requires LLM API key.

    These tests are skipped in CI without API keys but serve as
    regression guards when run locally or in dedicated test runs.
    """

    async def test_run_unified_analysis_standard_thresholds(self):
        """run_unified_analysis('standard') meets minimum thresholds."""
        import os

        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(
            GOLDEN_TEXT,
            workflow_name="standard",
        )

        state = result.get("unified_state")
        assert state is not None, "Pipeline did not produce unified_state"

        snapshot = state.get_state_snapshot(summarize=True)
        assert (
            snapshot.get("argument_count", 0) >= 3
        ), f"Expected ≥3 arguments, got {snapshot.get('argument_count', 0)}"
        assert (
            snapshot.get("fallacy_count", 0) >= 1
        ), f"Expected ≥1 fallacy, got {snapshot.get('fallacy_count', 0)}"

    async def test_run_unified_analysis_returns_state_snapshot(self):
        """run_unified_analysis returns state_snapshot in result dict."""
        import os

        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(
            GOLDEN_TEXT,
            workflow_name="light",
        )

        assert "state_snapshot" in result
        assert result["state_snapshot"] is not None
        assert "workflow_name" in result
        assert result["summary"]["completed"] >= 1


# ============================================================
# Layer 1d: Workflow structure golden tests
# ============================================================


@pytest.mark.unit
class TestGoldenWorkflowStructure:
    """Verify workflow definitions have expected minimum phase counts."""

    def test_standard_workflow_phase_count(self):
        """Standard workflow has ≥10 phases."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        assert (
            len(wf.phases) >= 10
        ), f"Expected ≥10 phases, got {len(wf.phases)}: {[p.name for p in wf.phases]}"

    def test_full_workflow_phase_count(self):
        """Full workflow has ≥12 phases."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        assert (
            len(wf.phases) >= 12
        ), f"Expected ≥12 phases, got {len(wf.phases)}: {[p.name for p in wf.phases]}"

    def test_standard_workflow_has_required_capabilities(self):
        """Standard workflow includes core capabilities."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        capabilities = [p.capability for p in wf.phases]
        required = [
            "fact_extraction",
            "argument_quality",
            "counter_argument_generation",
            "belief_maintenance",
        ]
        for cap in required:
            assert cap in capabilities, f"Missing required capability: {cap}"

    def test_light_workflow_is_subset_of_standard(self):
        """Light workflow capabilities are a subset of standard."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_light_workflow,
            build_standard_workflow,
        )

        light = build_light_workflow()
        standard = build_standard_workflow()

        light_caps = set(p.capability for p in light.phases)
        standard_caps = set(p.capability for p in standard.phases)
        assert light_caps.issubset(
            standard_caps
        ), f"Light has caps not in standard: {light_caps - standard_caps}"

    def test_state_writers_cover_standard_capabilities(self):
        """All standard workflow capabilities have state writers."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
            CAPABILITY_STATE_WRITERS,
        )

        wf = build_standard_workflow()
        for phase in wf.phases:
            if not phase.optional:
                assert phase.capability in CAPABILITY_STATE_WRITERS, (
                    f"Non-optional phase '{phase.name}' capability "
                    f"'{phase.capability}' has no state writer"
                )

    def test_workflow_catalog_completeness(self):
        """Workflow catalog has at least 3 named workflows."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        catalog = get_workflow_catalog()
        assert len(catalog) >= 3, f"Expected ≥3 workflows, got {len(catalog)}"
        assert "light" in catalog
        assert "standard" in catalog
        assert "full" in catalog
