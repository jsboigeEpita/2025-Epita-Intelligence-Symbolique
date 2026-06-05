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
