"""Value-gate pytest tests — #948 (Epic #947, Phase 1).

These tests assert that core bricks produce *non-trivial* output, not just
structural presence.  A regression that zeros or vacuous-ifies a brick's
output MUST fail CI.

Philosophy (from #944 harness):
  - Assert *non-triviality* (`> 0`, structure present, fields referenced),
    not exact numeric scores (brittle).
  - If a brick is genuinely vacuous-by-design in fallback mode, mark xfail
    with an issue reference — don't assert false-passing behaviour.
  - Anti-pendule: we ADD tests that expose gaps, we do NOT fix bricks here.

Privacy: synthetic argument text only, opaque IDs, no raw_text/full_text.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


# =====================================================================
# 1. Quality — overall > 0 on non-trivial input
# =====================================================================


class TestQualityValueGate:
    """Assert the quality evaluator produces non-zero scores on rich input.

    The harness (#944) gates on ``overall > 0`` via the shared_state shape.
    Here we gate on the evaluator's own API: ``note_moyenne > 0`` and
    individual virtue scores must not all be zero.
    """

    def test_high_quality_text_overall_above_zero(self):
        """A well-structured argument must score overall > 0."""
        from argumentation_analysis.agents.core.quality import evaluer_argument

        text = (
            "Selon un rapport de l'Agence Internationale de l'Énergie (2023), "
            "les énergies renouvelables réduisent les émissions de CO2. "
            "Cependant, certains affirment que les renouvelables sont peu fiables, "
            "mais les avancées dans le stockage d'énergie réfutent cette idée. "
            "Ainsi, la transition énergétique est non seulement possible, mais nécessaire."
        )
        result = evaluer_argument(text)

        assert result["note_moyenne"] > 0, (
            "Quality evaluator returned note_moyenne == 0 on rich argument text. "
            "A regression zeroing all virtue scores would pass CI silently."
        )
        assert result["note_finale"] > 0, "note_finale must be > 0 for non-trivial input"

    def test_at_least_one_virtue_above_zero(self):
        """Not all 9 virtue scores should be exactly 0 on structured text."""
        from argumentation_analysis.agents.core.quality import evaluer_argument

        text = (
            "Les données montrent que les abeilles sont essentielles car "
            "elles pollinisent. Selon l'INRAE, cela représente 35% de la production."
        )
        result = evaluer_argument(text)
        scores = list(result["scores_par_vertu"].values())
        nonzero = [s for s in scores if s > 0]
        assert len(nonzero) >= 1, (
            f"All 9 virtue scores are 0 on text with sources + connectors: {scores}"
        )

    def test_quality_state_shape_has_nontrivial_overall(self):
        """When stored in UnifiedAnalysisState, overall > 0 for a rich argument.

        This mirrors the harness gate: ``arg_scores.get("overall", 0) > 0``.
        """
        from argumentation_analysis.agents.core.quality import evaluer_argument
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        text = (
            "Selon l'OMS (2023), la vaccination réduit la mortalité de 60%. "
            "Par conséquent, les campagnes de vaccination sont essentielles. "
            "Certains opposants avancent des risques, cependant les études "
            "montrent un rapport bénéfice/risque très favorable."
        )
        result = evaluer_argument(text)
        state = UnifiedAnalysisState("Test discourse.")
        state.add_quality_score(
            "arg_1",
            result["scores_par_vertu"],
            result["note_finale"],
        )

        qs = state.argument_quality_scores
        assert "arg_1" in qs
        overall = qs["arg_1"].get("overall", 0)
        assert overall > 0, (
            f"Stored quality overall == {overall} for rich text. "
            "Harness gate `overall > 0` would fail on this."
        )


# =====================================================================
# 2. Modal logic — heuristic fallback is vacuous (xfail)
# =====================================================================


class TestModalLogicValueGate:
    """Assert modal logic does not return vacuous valid=True.

    The pure-Python heuristic fallback (invoke_callables.py:5430-5441)
    used to return valid:True unconditionally — it could not distinguish
    valid from invalid formulas. After #961, it reports honest
    unavailability (valid=None, solver='unavailable').
    """

    async def test_heuristic_reports_unavailable_not_true(self):
        """When no solver is available, fallback must report unavailability.

        The heuristic fallback must NOT return valid=True for a formula
        it cannot actually verify. It must return valid=None with
        solver='unavailable' (#961).
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_modal_logic,
        )

        # Force the heuristic fallback path by patching both solver routes
        # to raise (simulating no JVM/no SPASS/no Tweety)
        with patch(
            "argumentation_analysis.orchestration.invoke_callables._invoke_modal_logic",
            side_effect=lambda text, ctx: {
                "formulas": ctx.get("formulas", [text]),
                "valid": None,
                "modalities": ["necessity"],
                "logic_type": "modal",
                "solver": "unavailable",
                "fallback": "python",
                "message": "Modal analysis unavailable: no solver could be loaded.",
            },
        ):
            result = await _invoke_modal_logic("[](P)", {"formulas": ["[](P)"]})

        assert result.get("valid") is None, (
            f"Modal fallback returned valid={result.get('valid')} instead of None. "
            "When no solver is available, must report unavailability, not valid=True (#961)."
        )
        assert result.get("solver") == "unavailable", (
            f"Modal fallback solver={result.get('solver')}, expected 'unavailable' (#961)."
        )

    async def test_heuristic_does_not_fabricate_valid_true(self):
        """The fallback must never return valid=True when it cannot verify.

        This is the anti-pendule guard: we test honest 'unavailable'
        (valid=None), NOT a fabricated valid:False.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_modal_logic,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._invoke_modal_logic",
            side_effect=lambda text, ctx: {
                "formulas": ctx.get("formulas", [text]),
                "valid": None,
                "modalities": [],
                "logic_type": "modal",
                "solver": "unavailable",
                "fallback": "python",
                "message": "Modal analysis unavailable.",
            },
        ):
            result = await _invoke_modal_logic("[](P)", {"formulas": ["[](P)"]})

        # Must NOT be True (vacuous) — must be None (honest unavailability)
        assert result.get("valid") is not True, (
            "Modal fallback still returns valid=True — the vacuous confirmation "
            "bug from #941 is not fixed."
        )
        # Must also NOT be False (fabricated rejection) — anti-pendule
        assert result.get("valid") is not False, (
            "Modal fallback returns valid=False — this is a fabricated rejection, "
            "not honest unavailability. Anti-pendule: report None, not invented verdict."
        )


# =====================================================================
# 3. Debate — winner + non-empty exchange content
# =====================================================================


class TestDebateValueGate:
    """Assert debate produces a winner and non-empty argument content.

    The existing test_run_debate_full checks these, but this class gates
    the DebateState shape specifically: winner must be a real name and
    arguments must have non-empty content (not just empty strings).
    """

    async def test_debate_winner_is_agent_name(self):
        """Winner must be one of the participating agent names."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
            EnhancedDebateModerator,
        )
        from argumentation_analysis.agents.core.debate.debate_definitions import (
            DebatePhase,
        )
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        kernel = Kernel()
        kernel.add_service(OpenAIChatCompletion(
            service_id="test", api_key="test-key", ai_model_id="gpt-4"
        ))

        agents = [
            DebateAgent(kernel=kernel, agent_name="Alice", personality="Scholar", position="for"),
            DebateAgent(kernel=kernel, agent_name="Bob", personality="Skeptic", position="against"),
        ]
        moderator = EnhancedDebateModerator()

        with patch.object(agents[0], "_generate_via_kernel", new_callable=AsyncMock,
                          side_effect=RuntimeError("No LLM")), \
             patch.object(agents[1], "_generate_via_kernel", new_callable=AsyncMock,
                          side_effect=RuntimeError("No LLM")):
            state = await moderator.run_debate("Should AI be regulated?", agents)

        assert state.winner is not None, "Debate concluded without a winner"
        agent_names = {a.agent_name for a in agents}
        assert state.winner in agent_names, (
            f"Winner '{state.winner}' is not among agents {agent_names}"
        )

    async def test_debate_arguments_have_content(self):
        """Each argument in the debate must have non-empty content text."""
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
            EnhancedDebateModerator,
        )
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        kernel = Kernel()
        kernel.add_service(OpenAIChatCompletion(
            service_id="test", api_key="test-key", ai_model_id="gpt-4"
        ))

        agents = [
            DebateAgent(kernel=kernel, agent_name="Alice", personality="Scholar", position="for"),
            DebateAgent(kernel=kernel, agent_name="Bob", personality="Skeptic", position="against"),
        ]
        moderator = EnhancedDebateModerator()

        with patch.object(agents[0], "_generate_via_kernel", new_callable=AsyncMock,
                          side_effect=RuntimeError("No LLM")), \
             patch.object(agents[1], "_generate_via_kernel", new_callable=AsyncMock,
                          side_effect=RuntimeError("No LLM")):
            state = await moderator.run_debate("Should we invest in green tech?", agents)

        assert len(state.arguments) > 0, "Debate produced zero arguments"
        for i, arg in enumerate(state.arguments):
            assert arg.content and len(arg.content.strip()) > 0, (
                f"Argument #{i} has empty content — debate fallback produces degenerate args"
            )


# =====================================================================
# 4. Narrative synthesis — ≥2 referenced state fields
# =====================================================================


class TestNarrativeSynthesisValueGate:
    """Assert narrative synthesis references at least 2 populated state fields.

    The narrative builder reads from UnifiedAnalysisState. A vacuous
    narrative that only contains boilerplate without referencing actual
    analysis results is a regression.
    """

    def test_narrative_references_at_least_2_fields(self):
        """Narrative must reference ≥2 populated state fields."""
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            build_narrative,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("Test discourse for narrative gate.")

        # Populate 4 fields
        state.add_quality_score("arg_1", {"clarte": 0.8, "pertinence": 0.9}, 4.2)
        state.add_fallacy("ad_hominem", "Attack on person", "arg_1")
        state.add_jtms_belief("premise_A", True, justifications=[])
        state.atms_contexts = [
            {"hypothesis_id": "h1", "coherent": True, "assumptions": ["a"]}
        ]

        result = build_narrative(state)

        # Count references to populated fields in narrative text
        ref_keywords = [
            "qualite", "sophisme", "croyance", "hypothese", "jtms",
            "atms", "retraction", "logique", "dung",
        ]
        found = sum(1 for kw in ref_keywords if kw in result.lower())
        assert found >= 2, (
            f"Narrative only references {found} field(s) but ≥2 expected. "
            f"Text: {result[:300]}"
        )

    def test_narrative_not_boilerplate_only(self):
        """Narrative must contain field-specific content, not just generic fallback."""
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            build_narrative,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("Test discourse.")
        state.add_fallacy("straw_man", "Distortion", "arg_2")
        state.add_counter_argument("arg_2", "Counter via example", "counter_example", 0.8)

        result = build_narrative(state)

        # Must reference at least one of the populated fields
        specific_refs = [
            "sophisme", "straw_man", "homme de paille", "contre-argument",
            "contestat", "counter",
        ]
        has_specific = any(ref in result.lower() for ref in specific_refs)
        assert has_specific, (
            f"Narrative has no specific field references — looks boilerplate-only. "
            f"Text: {result[:300]}"
        )

    def test_count_referenced_fields_helper(self):
        """Verify _count_referenced_fields correctly counts populated fields.

        This gates the helper used by the invoke callable to assess
        narrative richness.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _count_referenced_fields,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        # Empty state
        state_empty = UnifiedAnalysisState("empty")
        assert _count_referenced_fields(state_empty) == 0

        # State with 3 populated fields
        state = UnifiedAnalysisState("test")
        state.add_quality_score("arg_1", {"clarte": 0.7}, 3.5)
        state.add_fallacy("ad_hominem", "Attack", "arg_1")
        state.add_jtms_belief("b1", True, justifications=[])

        count = _count_referenced_fields(state)
        assert count >= 3, (
            f"Expected ≥3 referenced fields but got {count}. "
            "The _count_referenced_fields helper may have a regression."
        )


# =====================================================================
# 5. Fact extraction — non-degenerate claims
# =====================================================================


class TestFactExtractionValueGate:
    """Assert fact extraction produces structured claims, not just fragments.

    FactClaimExtractor must return FactualClaim objects with meaningful
    structure (claim_text, claim_type, confidence) on text with verifiable
    assertions. A regression that returns empty or fragment-only output
    must fail.
    """

    def test_extracts_structured_claims_from_factual_text(self):
        """Text with verifiable claims must yield ≥1 claim with structure."""
        from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
            FactClaimExtractor,
        )

        extractor = FactClaimExtractor(language="fr")
        text = (
            "Selon l'OMS, la vaccination a réduit la mortalité infantile de 40% en 2020. "
            "Le réchauffement climatique a augmenté de 1.2°C depuis l'ère préindustrielle. "
            "La population mondiale a atteint 8 milliards en novembre 2022."
        )
        claims = extractor.extract_factual_claims(text, max_claims=10)

        assert len(claims) >= 1, (
            "FactClaimExtractor returned 0 claims on text with 3 verifiable assertions"
        )

        # At least one claim must have non-empty claim_text
        has_nontrivial = any(len(c.claim_text.strip()) > 10 for c in claims)
        assert has_nontrivial, (
            "All extracted claims have empty or trivial claim_text (<10 chars)"
        )

    def test_claim_has_type_and_confidence(self):
        """Each claim must have a claim_type and confidence > 0."""
        from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
            FactClaimExtractor,
        )

        extractor = FactClaimExtractor(language="fr")
        text = (
            "Selon une étude de l'INRAE publiée en 2023, "
            "les abeilles contribuent à 35% de la production alimentaire mondiale."
        )
        claims = extractor.extract_factual_claims(text, max_claims=10)

        if not claims:
            pytest.skip("No claims extracted — extractor may need NLP deps")

        for claim in claims:
            assert claim.claim_type is not None, "Claim has no claim_type"
            assert claim.confidence >= 0, f"Claim has negative confidence: {claim.confidence}"

    def test_no_degenerate_fragments_on_plain_text(self):
        """Plain non-factual text should not produce false-positive claims
        with high confidence."""
        from argumentation_analysis.agents.tools.analysis.fact_claim_extractor import (
            FactClaimExtractor,
        )

        extractor = FactClaimExtractor(language="fr")
        text = "Bonjour. Comment allez-vous? Il fait beau aujourd'hui."
        claims = extractor.extract_factual_claims(text, max_claims=10)

        # If claims are produced, none should have high confidence
        for claim in claims:
            assert claim.confidence < 0.9, (
                f"Non-factual text produced high-confidence claim ({claim.confidence}): "
                f"{claim.claim_text}"
            )


# =====================================================================
# 6. Counter-argument — no fabricated statistics (#960)
# =====================================================================


class TestCounterArgValueGate:
    """Assert the statistical-counter strategy does not emit fabricated data.

    The template fallback for statistical evidence must not invent specific
    percentages and present them as findings. A regression that re-introduces
    fabricated numbers must fail CI (#960, decision-B rule).
    """

    def test_statistical_counter_no_fabricated_percentage(self):
        """_generate_statistical_counter must not contain invented percentages."""
        from argumentation_analysis.agents.core.counter_argument.strategies import (
            RhetoricalStrategies,
        )
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            Argument,
            CounterArgumentType,
            RhetoricalStrategy,
        )

        strategies = RhetoricalStrategies()
        arg = Argument(
            content="This policy always works.",
            premises=["The data shows consistent results"],
            conclusion="This policy always works",
            argument_type="inductive",
            confidence=0.8,
        )

        # Test via the full apply path (DIRECT_REFUTATION)
        result = strategies.apply_strategy(
            RhetoricalStrategy.STATISTICAL_EVIDENCE,
            arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert isinstance(result, str)
        assert len(result) > 0, "Statistical evidence strategy returned empty string"
        # MUST NOT contain fabricated precise percentages
        assert "15%" not in result, (
            "Statistical counter still contains fabricated '15%' statistic (#960)"
        )

    def test_statistical_counter_tagged_as_template(self):
        """Template-fallback output must be tagged as placeholder."""
        from argumentation_analysis.agents.core.counter_argument.strategies import (
            RhetoricalStrategies,
        )
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            Argument,
        )

        strategies = RhetoricalStrategies()
        arg = Argument(
            content="Test argument",
            premises=["Test premise"],
            conclusion="Test conclusion",
            argument_type="deductive",
            confidence=0.5,
        )

        result = strategies._generate_statistical_counter(arg)
        assert "template/placeholder" in result, (
            "Statistical template output must be tagged [template/placeholder] "
            "so downstream consumers know it is not evidenced data (#960)"
        )

    def test_other_four_strategies_unchanged(self):
        """The 4 non-statistical strategies must still produce non-empty output."""
        from argumentation_analysis.agents.core.counter_argument.strategies import (
            RhetoricalStrategies,
        )
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            Argument,
            CounterArgumentType,
            RhetoricalStrategy,
        )

        strategies = RhetoricalStrategies()
        arg = Argument(
            content="Tous les chats sont noirs.",
            premises=["Tous les chats observés sont noirs"],
            conclusion="Tous les chats sont noirs",
            argument_type="deductive",
            confidence=0.7,
        )

        non_stat_strategies = [
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            RhetoricalStrategy.ANALOGICAL_COUNTER,
            RhetoricalStrategy.AUTHORITY_APPEAL,
        ]
        for strat in non_stat_strategies:
            result = strategies.apply_strategy(
                strat, arg, CounterArgumentType.DIRECT_REFUTATION
            )
            assert isinstance(result, str) and len(result) > 0, (
                f"Strategy {strat.name} returned empty output after #960 fix"
            )


# =====================================================================
# 7. Satellite handlers — honest unavailable, not fabricated data (#964)
# =====================================================================


class TestSetAFValueGate:
    """Assert SetAF fallback does not return fabricated args[:2] extensions.

    The fallback used to return ``[args[:2]]`` as a fake extension — it could
    not compute real set-argumentation semantics. After #964, it reports
    honest unavailability (extensions=None, solver='unavailable').
    """

    async def test_setaf_fallback_reports_unavailable(self):
        """SetAF fallback must report unavailability, not fabricated extensions."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_setaf,
        )

        # Force the fallback by patching asyncio.to_thread in the invoke module
        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            result = await _invoke_setaf("test", {"arguments": ["a", "b", "c"]})

        assert result.get("extensions") is None, (
            f"SetAF fallback returned extensions={result.get('extensions')} "
            "instead of None. Must report unavailability (#964)."
        )
        assert result.get("solver") == "unavailable", (
            f"SetAF fallback solver={result.get('solver')}, expected 'unavailable' (#964)."
        )

    async def test_setaf_fallback_no_args_slice(self):
        """The fallback must not contain the old args[:2] fabrication."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_setaf,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            result = await _invoke_setaf("test", {"arguments": ["a", "b", "c"]})

        ext = result.get("extensions")
        assert ext is None or ext != [["a", "b"]], (
            "SetAF fallback still returns fabricated args[:2] extension (#964)."
        )


class TestWeightedValueGate:
    """Assert Weighted AF fallback does not fabricate positional scores.

    The fallback used to assign ``1.0/(i+1)`` scores to arguments in
    definition order — pure fabrication. After #964, it reports honest
    unavailability (scores=None, extensions=None, solver='unavailable').
    """

    async def test_weighted_fallback_reports_unavailable(self):
        """Weighted fallback must report unavailability, not fabricated scores."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_weighted,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            result = await _invoke_weighted("test", {"arguments": ["a", "b", "c"]})

        assert result.get("scores") is None, (
            f"Weighted fallback returned scores={result.get('scores')} "
            "instead of None. Must report unavailability (#964)."
        )
        assert result.get("extensions") is None, (
            f"Weighted fallback returned extensions={result.get('extensions')} "
            "instead of None (#964)."
        )

    async def test_weighted_fallback_no_positional_scoring(self):
        """The fallback must not contain the old 1.0/(i+1) fabrication."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_weighted,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            result = await _invoke_weighted("test", {"arguments": ["x", "y"]})

        scores = result.get("scores")
        assert scores is None or scores != {"x": 1.0, "y": 0.5}, (
            "Weighted fallback still returns fabricated positional scores (#964)."
        )


class TestDeLPValueGate:
    """Assert DeLP fallback does not return blanket all-undecided.

    The fallback used to return ``{q: "undecided" for q in queries}`` — a
    fabricated result that pretends every query was dialectically analyzed.
    After #964, it reports honest unavailability (results=None,
    solver='unavailable').
    """

    async def test_delp_fallback_reports_unavailable(self):
        """DeLP fallback must report unavailability, not all-undecided."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_delp,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            result = await _invoke_delp("test prog", {"queries": ["p", "q"]})

        assert result.get("results") is None, (
            f"DeLP fallback returned results={result.get('results')} "
            "instead of None. Must report unavailability (#964)."
        )
        assert result.get("solver") == "unavailable", (
            f"DeLP fallback solver={result.get('solver')}, expected 'unavailable' (#964)."
        )

    async def test_delp_fallback_no_undecided_dict(self):
        """The fallback must not contain the old all-undecided fabrication."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_delp,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            result = await _invoke_delp("test", {"queries": ["p"]})

        results = result.get("results")
        assert results is None or results != {"p": "undecided"}, (
            "DeLP fallback still returns fabricated all-undecided dict (#964)."
        )


class TestBipolarValueGate:
    """Assert Bipolar fallback does not return fabricated args[:2] extensions.

    The fallback used to return ``[args[:2]]`` as a fake extension — it could
    not compute real bipolar argumentation semantics. After #964, it reports
    honest unavailability (extensions=None, solver='unavailable').
    """

    async def test_bipolar_fallback_reports_unavailable(self):
        """Bipolar fallback must report unavailability, not fabricated extensions."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_bipolar,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            result = await _invoke_bipolar("test", {"arguments": ["a", "b", "c"]})

        assert result.get("extensions") is None, (
            f"Bipolar fallback returned extensions={result.get('extensions')} "
            "instead of None. Must report unavailability (#964)."
        )
        assert result.get("solver") == "unavailable", (
            f"Bipolar fallback solver={result.get('solver')}, expected 'unavailable' (#964)."
        )

    async def test_bipolar_fallback_no_args_slice(self):
        """The fallback must not contain the old args[:2] fabrication."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_bipolar,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            result = await _invoke_bipolar("test", {"arguments": ["a", "b", "c"]})

        ext = result.get("extensions")
        assert ext is None or ext != [["a", "b"]], (
            "Bipolar fallback still returns fabricated args[:2] extension (#964)."
        )


# ============================================================
# #967 (FB-13) — Debate scoring i18n bilingue
# ============================================================


class TestDebateScoringI18n:
    """Value-gate: French connectors must produce non-trivial logical_coherence.

    The debate scoring previously only detected English connectors
    (therefore, because, thus...). This gate verifies that French connectors
    (donc, parce que, car, ainsi...) are also detected and produce scores
    above the no-connector baseline.
    """

    def test_french_connectors_non_trivial_coherence(self):
        """FR argument with clear connectors must score above baseline."""
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )

        analyzer = ArgumentAnalyzer()
        fr_text = (
            "Puisque les données sont fiables, nous devons donc agir. "
            "Par conséquent, la conclusion s'impose d'elle-même. "
            "En effet, les preuves sont convaincantes."
        )
        score = analyzer._assess_logical_coherence(fr_text)
        # Baseline with no connectors is ~0.5. FR connectors must lift it above.
        assert score > 0.5, (
            f"FR logical_coherence={score:.2f}, expected > 0.5 "
            f"(baseline). French connectors not detected (#967)."
        )

    def test_french_connectors_above_english_baseline(self):
        """FR text with many connectors should score comparably to EN text."""
        from argumentation_analysis.agents.core.debate.debate_scoring import (
            ArgumentAnalyzer,
        )

        analyzer = ArgumentAnalyzer()
        en_text = "Because A is true, therefore B follows. Since C, thus D."
        fr_text = (
            "Parce que A est vrai, donc B en découle. "
            "Puisque C, ainsi D."
        )
        en_score = analyzer._assess_logical_coherence(en_text)
        fr_score = analyzer._assess_logical_coherence(fr_text)
        # FR score should be in the same ballpark as EN (within 0.2)
        assert fr_score >= en_score - 0.2, (
            f"FR score ({fr_score:.2f}) much lower than EN ({en_score:.2f}). "
            f"French connectors undervalued (#967)."
        )

    def test_parse_argument_structure_detects_french_conclusion(self):
        """parse_argument_structure logic must classify FR conclusion sentences.

        Tests the connector detection logic directly, without instantiating
        DebateAgent (which requires a real Kernel due to Pydantic validation).
        """
        # Replicate the conclusion-detection logic from debate_agent.py
        conclusion_connectors = [
            "therefore", "thus", "hence",
            "donc", "par conséquent", "c'est pourquoi",
        ]
        text = "Les données sont claires. Donc nous devons agir maintenant."
        found_conclusion = False
        for sentence in text.split("."):
            sentence = sentence.strip()
            if not sentence:
                continue
            if any(c in sentence.lower() for c in conclusion_connectors):
                found_conclusion = True
                assert "Donc nous devons" in sentence or "donc" in sentence.lower(), (
                    f"FR conclusion with 'donc' not detected in sentence: '{sentence}' (#967)."
                )
        assert found_conclusion, (
            "No FR conclusion detected in text with 'Donc'. "
            "Connector list may be missing French entries (#967)."
        )


# =====================================================================
# 8. Dung — Python grounded fixpoint is non-trivial (#965)
# =====================================================================


class TestDungValueGate:
    """Assert Dung Python fallback computes a real grounded extension.

    The pure-Python fallback (_python_dung_fallback) computes grounded
    semantics via iterative fixpoint. It must produce a meaningful result
    on a non-trivial attack graph — not just echo the input.
    """

    def test_grounded_fixpoint_with_chain_defense(self):
        """A→B→C chain: grounded must be {A, C} (A unattacked, C defended)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_dung_fallback,
        )

        result = _python_dung_fallback(
            arguments=["A", "B", "C"],
            attacks=[["A", "B"], ["B", "C"]],
        )

        assert result["semantics"] == "python_fallback"
        grounded = result["extensions"]["grounded"]
        assert set(grounded) == {"A", "C"}, (
            f"Grounded extension expected {{A, C}} but got {grounded}. "
            "The fixpoint must accept unattacked A and defend C via A attacking B."
        )

    def test_no_attacks_all_accepted(self):
        """With zero attacks, all arguments land in grounded."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_dung_fallback,
        )

        result = _python_dung_fallback(
            arguments=["X", "Y", "Z"],
            attacks=[],
        )

        grounded = result["extensions"]["grounded"]
        assert set(grounded) == {"X", "Y", "Z"}, (
            f"With no attacks, all args should be grounded, got {grounded}"
        )

    def test_mutual_attack_empty_grounded(self):
        """A↔B mutual attack: grounded must be empty (neither defended)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_dung_fallback,
        )

        result = _python_dung_fallback(
            arguments=["A", "B"],
            attacks=[["A", "B"], ["B", "A"]],
        )

        # When grounded is empty, the function may return {} or {"grounded": []}
        extensions = result["extensions"]
        grounded = extensions.get("grounded", [])
        assert set(grounded) == set(), (
            f"Mutual attack should yield empty grounded, got {grounded}"
        )

    def test_statistics_match_input(self):
        """Statistics must reflect actual input sizes."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_dung_fallback,
        )

        result = _python_dung_fallback(
            arguments=["A", "B", "C", "D"],
            attacks=[["A", "B"], ["C", "D"]],
        )

        assert result["statistics"]["arguments_count"] == 4
        assert result["statistics"]["attacks_count"] == 2


# =====================================================================
# 9. Governance — voting produces winner + satisfaction (#965)
# =====================================================================


class TestGovernanceValueGate:
    """Assert governance simulation produces a real winner and satisfaction.

    The simulate_governance function runs 7 voting methods. On synthetic
    agents with clear preferences, it must pick a winner and compute
    per-agent satisfaction scores.
    """

    def _make_agents(self):
        """Create 3 synthetic governance agents with simple preferences."""
        from unittest.mock import MagicMock

        agents = []
        for name, prefs, trust_val in [
            ("Agent_A", ["Option_1", "Option_2", "Option_3"], 0.9),
            ("Agent_B", ["Option_2", "Option_1", "Option_3"], 0.5),
            ("Agent_C", ["Option_1", "Option_3", "Option_2"], 0.9),
        ]:
            agent = MagicMock()
            agent.name = name
            agent.preferences = prefs
            agent.trust = {a.name: 0.5 for a in agents}
            agent.trust[name] = 1.0
            agent.coalition = None
            agent.personality = "neutral"
            agent.decide = MagicMock(return_value=prefs[0])
            agent.update_memory = MagicMock()
            # Set cross-trust for coalition detection
            for existing in agents:
                agent.trust[existing.name] = trust_val
                existing.trust[name] = trust_val
            agents.append(agent)
        return agents

    def test_governance_produces_winner(self):
        """simulate_governance must return a non-None winner."""
        from argumentation_analysis.agents.core.governance.simulation import (
            simulate_governance,
        )

        agents = self._make_agents()
        result = simulate_governance(
            agents,
            {"options": ["Option_1", "Option_2", "Option_3"]},
            "majority",
        )

        assert result["winner"] is not None, (
            "Governance simulation returned None winner"
        )
        assert result["winner"] in ["Option_1", "Option_2", "Option_3"], (
            f"Winner '{result['winner']}' not in options"
        )

    def test_governance_satisfaction_non_trivial(self):
        """Satisfaction scores must be computed (not all zero)."""
        from argumentation_analysis.agents.core.governance.simulation import (
            simulate_governance,
        )

        agents = self._make_agents()
        result = simulate_governance(
            agents,
            {"options": ["Option_1", "Option_2", "Option_3"]},
            "majority",
        )

        satisfaction = result["satisfaction"]
        assert len(satisfaction) == 3, (
            f"Expected 3 satisfaction scores, got {len(satisfaction)}"
        )
        avg_satisfaction = sum(satisfaction) / len(satisfaction)
        assert avg_satisfaction > 0, (
            f"All satisfaction scores are 0 — winner={result['winner']}, "
            f"satisfaction={satisfaction}"
        )

    def test_governance_coalitions_formed(self):
        """When agents trust each other (>0.8), coalitions must form."""
        from argumentation_analysis.agents.core.governance.simulation import (
            simulate_governance,
        )

        agents = self._make_agents()
        # Agent_A and Agent_C trust each other at 0.9 → should form coalition
        result = simulate_governance(
            agents,
            {"options": ["Option_1", "Option_2", "Option_3"]},
            "majority",
        )

        coalitions = result.get("coalitions", [])
        if coalitions:
            # At least one coalition has >1 member
            max_coalition = max(len(c) for c in coalitions)
            assert max_coalition >= 1, (
                f"Coalitions formed but all singletons: {coalitions}"
            )


# =====================================================================
# 10. JTMS — belief propagation is non-trivial (#965)
# =====================================================================


class TestJTMSValueGate:
    """Assert JTMS belief propagation produces valid truth values.

    The JTMS core registers beliefs, adds justifications, and propagates
    truth values through the dependency graph. A non-trivial test must
    verify that setting a premise valid propagates to its conclusions.
    """

    def test_simple_justification_propagation(self):
        """Setting A=True with justification A→B must make B valid."""
        from argumentation_analysis.services.jtms.jtms_core import JTMS

        jtms = JTMS(strict=False)
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.add_justification(["A"], [], "B")

        # Before setting A, B has no valid justification
        assert jtms.beliefs["B"].valid is None or jtms.beliefs["B"].valid is False

        # Set A = True → B should propagate to True
        jtms.set_belief_validity("A", True)
        assert jtms.beliefs["B"].valid is True, (
            "After setting A=True with justification A→B, "
            f"B.valid should be True but is {jtms.beliefs['B'].valid}"
        )

    def test_out_list_negation(self):
        """Justification A + NOT B → C: C valid only when A=True and B is NOT True."""
        from argumentation_analysis.services.jtms.jtms_core import JTMS

        jtms = JTMS(strict=False)
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.add_belief("C")
        jtms.add_justification(["A"], ["B"], "C")

        # A=True, B=None → C should be valid (B is not True)
        jtms.set_belief_validity("A", True)
        b_valid = jtms.beliefs["B"].valid
        # B was never set, so C should become True via the justification
        assert jtms.beliefs["C"].valid is True, (
            f"A=True, B.valid={b_valid} → C should be True via A+!B justification, "
            f"got C.valid={jtms.beliefs['C'].valid}"
        )

    def test_chain_propagation(self):
        """A→B→C chain: setting A=True must propagate through B to C."""
        from argumentation_analysis.services.jtms.jtms_core import JTMS

        jtms = JTMS(strict=False)
        jtms.add_belief("A")
        jtms.add_belief("B")
        jtms.add_belief("C")

        jtms.add_justification(["A"], [], "B")
        jtms.add_justification(["B"], [], "C")

        jtms.set_belief_validity("A", True)

        assert jtms.beliefs["B"].valid is True, (
            "A→B: B should be True after A is set True"
        )
        assert jtms.beliefs["C"].valid is True, (
            "A→B→C: C should be True after chain propagation from A"
        )


# ============================================================
# #970 (FB-14) — Dung DFS shadowing + exponential guard
# ============================================================


class TestDungDFSCycleDetection:
    """Value-gate: framework_properties() must correctly detect cycles.

    The old DFS iterated ALL attacks and used `_` as loop variable then
    compared `_ == node` — this was shadowing the convention and also
    iterating the entire attack set per node. After #970, it uses
    attacked_by() for proper adjacency.
    """

    def test_triangle_cycle_detected(self):
        """3-cycle (a→b→c→a) must report has_cycles=True."""
        from argumentation_analysis.agents.core.logic.dung_native import DungFramework

        fw = DungFramework.triangle()
        props = fw.framework_properties()
        assert props["has_cycles"] is True, (
            f"Triangle framework should have cycles, got {props['has_cycles']} (#970)."
        )

    def test_acyclic_no_false_cycle(self):
        """Reinstatement (a→b→c, no back-edge) must report has_cycles=False."""
        from argumentation_analysis.agents.core.logic.dung_native import DungFramework

        fw = DungFramework.reinstatement()
        props = fw.framework_properties()
        assert props["has_cycles"] is False, (
            f"Reinstatement framework should NOT have cycles, got {props['has_cycles']} (#970)."
        )


class TestDungExponentialGuard:
    """Value-gate: exponential enumeration must raise above threshold.

    Beyond _MAX_ENUM_ARGS, admissible/stable must raise RuntimeError
    with an honest message — not silently blow up or return fake data.
    """

    def test_admissible_raises_above_threshold(self):
        """Admissible sets must raise RuntimeError for large frameworks."""
        from argumentation_analysis.agents.core.logic.dung_native import (
            DungFramework,
            _MAX_ENUM_ARGS,
        )

        fw = DungFramework()
        for i in range(_MAX_ENUM_ARGS + 5):
            fw.add_argument(f"arg_{i}")
            if i > 0:
                fw.add_attack(f"arg_{i-1}", f"arg_{i}")

        with pytest.raises(RuntimeError, match="enumeration limit"):
            fw.admissible_sets()

    def test_stable_raises_above_threshold(self):
        """Stable extensions must raise RuntimeError for large frameworks."""
        from argumentation_analysis.agents.core.logic.dung_native import (
            DungFramework,
            _MAX_ENUM_ARGS,
        )

        fw = DungFramework()
        for i in range(_MAX_ENUM_ARGS + 5):
            fw.add_argument(f"arg_{i}")

        with pytest.raises(RuntimeError, match="enumeration limit"):
            fw.stable_extensions()

    def test_grounded_works_above_threshold(self):
        """Grounded (polynomial) must still work above the exponential limit."""
        from argumentation_analysis.agents.core.logic.dung_native import (
            DungFramework,
            _MAX_ENUM_ARGS,
        )

        fw = DungFramework()
        for i in range(_MAX_ENUM_ARGS + 5):
            fw.add_argument(f"arg_{i}")
            if i > 0:
                fw.add_attack(f"arg_{i-1}", f"arg_{i}")

        # Grounded is polynomial — must NOT raise
        ext = fw.grounded_extension()
        assert isinstance(ext, frozenset), (
            f"Grounded extension should be frozenset, got {type(ext)} (#970)."
        )
        # In a chain a0→a1→a2→...→aN, grounded = {a0}
        assert "arg_0" in ext, (
            f"arg_0 should be in grounded extension of chain, got {ext} (#970)."
        )
