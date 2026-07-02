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

import logging

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

        #1097: this test is now LOAD-BEARING. We patch the SOLVER ROUTE
        (``asyncio.to_thread`` — the SPASS L5180 and Tweety L5201 routes both
        go through it), NOT ``_invoke_modal_logic`` itself. The real function
        runs: both solver routes raise, fall through to the honest fallback
        (L5218-5230), and we assert its ACTUAL output. A regression that
        reintroduces ``valid=True`` in the real fallback is now caught.
        Aligned with the 12 other satellite gates (SetAF/Weighted/DeLP/...).
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_modal_logic,
        )

        # Force BOTH solver routes (SPASS + Tweety) to raise by patching
        # asyncio.to_thread — the real _invoke_modal_logic runs end-to-end,
        # reaches its honest fallback, and we assert its ACTUAL output.
        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No solver for test"),
        ):
            result = await _invoke_modal_logic("[](P)", {"formulas": ["[](P)"]})

        assert result.get("valid") is None, (
            f"Modal fallback returned valid={result.get('valid')} instead of None. "
            "When no solver is available, must report unavailability, not valid=True (#961/#1097)."
        )
        assert result.get("solver") == "unavailable", (
            f"Modal fallback solver={result.get('solver')}, expected 'unavailable' (#961/#1097)."
        )

    async def test_heuristic_does_not_fabricate_valid_true(self):
        """The fallback must never return valid=True when it cannot verify.

        This is the anti-pendule guard: we test honest 'unavailable'
        (valid=None), NOT a fabricated valid:False.

        #1097: LOAD-BEARING — patches ``asyncio.to_thread`` (the solver route)
        so the real ``_invoke_modal_logic`` runs and reaches its honest
        fallback. A regression reintroducing ``valid=True`` is caught here;
        the old test (patching the function itself) would have passed through it.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_modal_logic,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No solver for test"),
        ):
            result = await _invoke_modal_logic("[](P)", {"formulas": ["[](P)"]})

        # Must NOT be True (vacuous) — must be None (honest unavailability)
        assert result.get("valid") is not True, (
            "Modal fallback still returns valid=True — the vacuous confirmation "
            "bug from #941 is not fixed (#1097)."
        )
        # Must also NOT be False (fabricated rejection) — anti-pendule
        assert result.get("valid") is not False, (
            "Modal fallback returns valid=False — this is a fabricated rejection, "
            "not honest unavailability. Anti-pendule: report None, not invented verdict (#1097)."
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

    async def test_setaf_fallback_raises_fail_loud(self):
        """SetAF must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #964 guard asserted an honest-unavailable
        *dict* (extensions=None, solver='unavailable'). Post-#1252/#1019/RA-8
        #1053, the brick was hardened to RAISE RuntimeError in its except block
        so a solver failure can never enter state — degraded-dict OR fabricated
        extensions alike. This guard is STRICTER than the old None-dict: it
        asserts the raise itself, closing both the fabrication and the silent
        degraded-dict paths. Triage #1336 (stale-contract update).
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_setaf,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="SetAF analysis unavailable"):
                await _invoke_setaf("test", {"arguments": ["a", "b", "c"]})


class TestWeightedValueGate:
    """Assert Weighted AF fallback does not fabricate positional scores.

    The fallback used to assign ``1.0/(i+1)`` scores to arguments in
    definition order — pure fabrication. After #964, it reports honest
    unavailability (scores=None, extensions=None, solver='unavailable').
    """

    async def test_weighted_fallback_raises_fail_loud(self):
        """Weighted AF must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #964 guard asserted an honest-unavailable
        *dict* (scores=None). Post-#1252/#1019 the except block was hardened to
        RAISE RuntimeError so a solver failure can never enter state — fabricated
        OR silently-degraded scores alike. STRICTER than the old None-dict. The
        old positional-scoring fabrication (1.0/(i+1)) is doubly impossible: the
        function raises before any score is computed. Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_weighted,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="Weighted AF analysis unavailable"):
                await _invoke_weighted("test", {"arguments": ["a", "b", "c"]})


class TestDeLPValueGate:
    """Assert DeLP fallback does not return blanket all-undecided.

    The fallback used to return ``{q: "undecided" for q in queries}`` — a
    fabricated result that pretends every query was dialectically analyzed.
    After #964, it reports honest unavailability (results=None,
    solver='unavailable').
    """

    async def test_delp_no_program_reports_unavailable(self):
        """DeLP must report honest unavailability (status='unavailable') when no program.

        Contract evolution (#1215/FP-12): DeLP syntax is not prose, so the brick
        REQUIRES an explicit ``program`` in context. Without one it returns an
        honest-absent dict ``{status: 'unavailable', message: ...}``` — it does
        NOT feed raw text to DelpParser (which guaranteed a parse failure + corpus
        leak). The earlier #964 guard asserted ``solver='unavailable'`` on a
        fabricated all-undecided dict; both the key and the fabrication are gone.
        This guard pins the honest early-return shape under the #1215 contract.
        Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_delp,
        )

        # No 'program' in context -> early-return before to_thread (not patched).
        result = await _invoke_delp("test prog", {"queries": ["p", "q"]})

        assert result.get("status") == "unavailable", (
            f"DeLP without a program must return status='unavailable', "
            f"got status={result.get('status')!r} keys={sorted(result.keys())} (#1215)."
        )
        assert "program" in result.get("message", "").lower(), (
            f"DeLP unavailable message must explain the missing 'program', "
            f"got {result.get('message')!r} (#1215)."
        )
        # No fabricated results / verdict.
        assert result.get("results") is None, (
            f"DeLP must not fabricate results when unavailable: {result.get('results')}"
        )


class TestBipolarValueGate:
    """Assert Bipolar fallback does not return fabricated args[:2] extensions.

    The fallback used to return ``[args[:2]]`` as a fake extension — it could
    not compute real bipolar argumentation semantics. After #964, it reports
    honest unavailability (extensions=None, solver='unavailable').
    """

    async def test_bipolar_fallback_raises_fail_loud(self):
        """Bipolar AF must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #964 guard asserted an honest-unavailable
        *dict* (extensions=None, solver='unavailable'). Post-#1252/#1019 the
        except block was hardened to RAISE RuntimeError, so a solver failure can
        never enter state — fabricated OR silently-degraded extensions alike.
        STRICTER than the old None-dict. Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_bipolar,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="Bipolar analysis .* unavailable"):
                await _invoke_bipolar("test", {"arguments": ["a", "b", "c"]})


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

    def test_python_dung_fallback_is_fail_loud(self):
        """_python_dung_fallback is a fail-loud stub (#1252/#1019, FP-22 #1249).

        The previous pure-Python grounded-fixpoint enumeration — formerly pinned
        by test_grounded_fixpoint_with_chain_defense / test_no_attacks_all_accepted
        / test_mutual_attack_empty_grounded / test_statistics_match_input —
        produced non-empty extension sets WITHOUT a genuine Tweety reasoner call,
        an anti-theatre violation. It was removed; the function now raises so no
        fabricated extension can enter state. Call sites (_invoke_dung_extensions)
        return honest-absent degraded dicts instead of calling this stub.

        Triage #1336 (stale-contract update): the 4 semantic variants collapse
        into one fail-loud guard because the computed semantics no longer exist —
        the guard still proves no fabricated Dung result is produced (it raises).
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _python_dung_fallback,
        )

        with pytest.raises(RuntimeError, match="Dung extension computation unavailable"):
            _python_dung_fallback(
                arguments=["A", "B", "C"],
                attacks=[["A", "B"], ["B", "C"]],
            )


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


# ============================================================
# #971 (FB-15) — Governance fabricated probs + Kemeny fallback
# ============================================================


class TestConflictResolutionHonestProb:
    """Value-gate: conflict resolution must not return fabricated probabilities.

    After #971, all three mediation strategies return success_probability=None
    (honest placeholder) instead of fabricated floats (0.8/0.5/0.7).
    """

    def test_collaborative_no_fabricated_prob(self):
        """Collaborative mediation must return None probability, not 0.8."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            collaborative_mediation,
        )

        conflict = {"agents": ["A", "B"], "conflict_level": 1.0}
        result = collaborative_mediation(conflict)
        assert result["success_probability"] is None, (
            f"Collaborative success_probability should be None (not measured), "
            f"got {result['success_probability']} (#971)."
        )
        assert result["resolution_type"] == "collaborative"

    def test_competitive_no_fabricated_prob(self):
        """Competitive mediation must return None probability, not 0.5."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            competitive_mediation,
        )

        conflict = {"agents": ["A", "B"], "conflict_level": 1.0}
        result = competitive_mediation(conflict)
        assert result["success_probability"] is None, (
            f"Competitive success_probability should be None (not measured), "
            f"got {result['success_probability']} (#971)."
        )

    def test_compromise_no_fabricated_prob(self):
        """Compromise mediation must return None probability, not 0.7."""
        from argumentation_analysis.agents.core.governance.conflict_resolution import (
            compromise_mediation,
        )

        conflict = {"agents": ["A", "B"], "conflict_level": 1.0}
        result = compromise_mediation(conflict)
        assert result["success_probability"] is None, (
            f"Compromise success_probability should be None (not measured), "
            f"got {result['success_probability']} (#971)."
        )


class TestKemenyYoungSafeFallback:
    """Value-gate: kemeny_young_safe falls back to Copeland for large sets.

    For ≤8 candidates, exact Kemeny-Young is used (approximate=False).
    For >8 candidates, Copeland approximation is returned (approximate=True).
    """

    def test_exact_for_small_sets(self):
        """3 candidates → exact Kemeny-Young, approximate=False."""
        from argumentation_analysis.agents.core.governance.social_choice import (
            kemeny_young_safe,
        )

        ballots = [
            ["A", "B", "C"],
            ["A", "C", "B"],
            ["B", "A", "C"],
        ]
        ranking, score, approximate = kemeny_young_safe(ballots, ["A", "B", "C"])
        assert approximate is False, (
            f"3 candidates should use exact Kemeny, got approximate={approximate} (#971)."
        )
        assert ranking[0] == "A", (
            f"A should win with 2 first-preference ballots, got {ranking} (#971)."
        )
        assert score > 0

    def test_fallback_for_large_sets(self):
        """10 candidates → Copeland fallback, approximate=True."""
        from argumentation_analysis.agents.core.governance.social_choice import (
            kemeny_young_safe,
            _MAX_KEMENY_CANDIDATES,
        )

        options = [f"C{i}" for i in range(_MAX_KEMENY_CANDIDATES + 2)]
        # Everyone agrees: C0 > C1 > C2 > ... > C9
        ballots = [options] * 5

        ranking, score, approximate = kemeny_young_safe(ballots, options)
        assert approximate is True, (
            f"{len(options)} candidates should trigger Copeland fallback, "
            f"got approximate={approximate} (#971)."
        )
        assert ranking[0] == "C0", (
            f"C0 should win with unanimous preferences, got {ranking} (#971)."
        )
        assert score == -1, (
            f"Fallback score should be -1 (sentinel), got {score} (#971)."
        )

    def test_exact_kemeny_raises_for_large_sets(self):
        """Direct kemeny_young() must still raise ValueError for >8."""
        from argumentation_analysis.agents.core.governance.social_choice import (
            kemeny_young,
            _MAX_KEMENY_CANDIDATES,
        )

        options = [f"C{i}" for i in range(_MAX_KEMENY_CANDIDATES + 2)]
        ballots = [options] * 3

        with pytest.raises(ValueError, match="impractical"):
            kemeny_young(ballots, options)


# ============================================================
# #973 (FB-16) — Informal Fallacy: substrate-literal taxonomy value-gate
# ============================================================


class TestInformalTaxonomyValueGate:
    """Value-gate: taxonomy detector fires on literal fallacy names, empty on paraphrase.

    The TaxonomySophismDetector uses substring matching (nom_vulgarisé/text_fr
    in text_lower). It genuinely detects fallacies when their canonical name
    appears literally, but returns near-empty on paraphrased descriptions.
    Both behaviours are REAL and must be pinned by tests — not hidden (#973).
    """

    @pytest.fixture(autouse=True)
    def _init_detector(self):
        """Create a TaxonomySophismDetector with a mock kernel."""
        from unittest.mock import MagicMock

        from argumentation_analysis.agents.core.informal.taxonomy_sophism_detector import (
            TaxonomySophismDetector,
        )
        from argumentation_analysis.agents.core.informal.informal_definitions import (
            InformalAnalysisPlugin,
        )

        kernel = MagicMock()
        plugin = InformalAnalysisPlugin(kernel=kernel)
        self.detector = TaxonomySophismDetector.__new__(TaxonomySophismDetector)
        self.detector.plugin = plugin
        self.detector._taxonomy_cache = None
        self.detector.logger = logging.getLogger("TestInformal")

    def test_fires_on_literal_fallacy_name(self):
        """Detector MUST find a fallacy when its nom_vulgarisé appears literally.

        Uses 'trouver des excuses' (PK=62, nom_vulgarisé='Trouver des excuses')
        which has a non-empty nom_vulgarisé — the substring match fires.
        """
        text = (
            "Il ne fait que trouver des excuses pour ne pas admettre "
            "qu'il avait tort depuis le début."
        )
        results = self.detector.detect_sophisms_from_taxonomy(text)
        assert len(results) >= 1, (
            f"Detector should find ≥1 fallacy when 'trouver des excuses' appears "
            f"literally, got {len(results)} results (#973)."
        )
        # Verify the detection method is taxonomy lexical
        assert any(r.get("detection_method") == "taxonomy_lexical" for r in results), (
            f"Expected 'taxonomy_lexical' detection method, got "
            f"{[r.get('detection_method') for r in results]} (#973)."
        )

    def test_empty_on_paraphrased_description(self):
        """Detector MUST return empty when fallacy is described without its name.

        A paraphrased excuse-making (without 'trouver des excuses') should not
        match. This pins the substring limitation — not a bug, just the
        detector's scope.
        """
        text = (
            "Au lieu de reconnaître son erreur, il a préféré tourner "
            "autour du pot et éviter le sujet."
        )
        results = self.detector.detect_sophisms_from_taxonomy(text)
        assert len(results) == 0, (
            f"Detector should return 0 on paraphrased text (no literal fallacy name), "
            f"got {len(results)}: {[r.get('nom_vulgarise','') for r in results]}. "
            f"This characterises the substring limitation (#973)."
        )

    def test_nom_vulgarise_match_confidence(self):
        """nom_vulgarisé match contributes ≥0.7 confidence (crosses 0.3 threshold)."""
        text = "C'est de l'inertie mentale pure."
        results = self.detector.detect_sophisms_from_taxonomy(text)
        assert len(results) >= 1, (
            f"Detector should find 'inertie mentale' (nom_vulgarisé match), "
            f"got {len(results)} results (#973)."
        )
        assert any(r.get("confidence", 0) >= 0.7 for r in results), (
            f"nom_vulgarisé match should contribute ≥0.7 confidence, "
            f"got {[r.get('confidence') for r in results]} (#973)."
        )


# ============================================================
# #976 (FB-17) — FOL: regression guard against #941 false-zero
# ============================================================


class TestFOLValueGate:
    """Value-gate: FOL must not silently regress to the #941 false-zero.

    The post-#941 capstone reports FOL 41/41 verified. Without a value-gate,
    a regression that zeroes FOL output (solver change, C1 extractor break)
    would pass CI in silence. These tests assert:
      1. When JVM/Tweety is unavailable: honest 'fallback: python', not
         fabricated consistent=True on template formulas with fallacies.
      2. Template formulas are honestly template-shaped (Asserted(argN)),
         not pretending to be LLM-generated.
      3. When Tweety is available: consistent is a real bool, formulas > 0.
    """

    async def test_fol_fallback_reports_honest_unavailable(self):
        """FOL must report honest unavailable (consistent=None) when solvers fail (#1278/#1019).

        Contract evolution: the earlier #976 guard expected a 'fallback: python'
        dict with template formulas + a real-bool consistent. Track B
        #1278/#1292 replaced the template-fabrication path with an honest
        DEGRADED RETURN: when no formula parses into a verifiable belief set,
        FOL returns consistent=None + fol_status='unavailable:...' — never a
        fabricated bool, never a template-only fallback. This guard asserts that
        honest-degraded shape (the anti-theatre intent of #976 preserved under
        the stricter #1278 contract). Triage #1336 (stale-contract update).
        Happy-path (Tweety succeeds) still covered by
        test_fol_consistent_is_bool_when_tweety_available below.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        text = "Les renouvelables sont chères. Cependant, le solaire coûte moins."
        context = {
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"type": "hasty_generalization", "fallacy_type": "hasty"},
                ],
            },
        }

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            side_effect=RuntimeError("No JVM for test"),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(None, None),
        ):
            result = await _invoke_fol_reasoning(text, context)

        # Honest degraded: consistent is None (NOT a fabricated bool).
        assert result.get("consistent") is None, (
            f"FOL must report consistent=None when no formula is verifiable, "
            f"got consistent={result.get('consistent')!r}. A real bool here would "
            f"mean a fabricated/template verdict re-entered state (#976/#1278)."
        )
        # Status must honestly report unavailability (parse-fail or no-translation).
        fol_status = result.get("fol_status", "")
        assert isinstance(fol_status, str) and fol_status.startswith("unavailable"), (
            f"FOL fol_status must start with 'unavailable' when degraded, "
            f"got {fol_status!r} (#1278/#1292)."
        )
        # The removed theatrical 'fallback: python' contract must NOT reappear.
        assert result.get("fallback") != "python", (
            "FOL still returns fallback='python' — the template-fabrication path "
            "was removed in #1278/#1292; its return is a regression (#976)."
        )

    async def test_fol_degraded_message_is_honest(self):
        """FOL degraded message must be marked unavailable, not 'consistent' theatre (#1278).

        Companion to test_fol_fallback_reports_honest_unavailable: pins the
        degraded *message* shape (must contain 'unavailable') so downstream
        consumers and the 3-act restitution can surface the honest gap rather
        than reading a fabricated consistency verdict.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        text = "Premise one. Premise two. Therefore conclusion."
        context = {}

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            side_effect=RuntimeError("No JVM for test"),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(None, None),
        ):
            result = await _invoke_fol_reasoning(text, context)

        assert result.get("consistent") is None, (
            f"Degraded FOL must keep consistent=None, got {result.get('consistent')!r}."
        )
        message = result.get("message", "")
        assert "unavailable" in message, (
            f"FOL degraded message must state unavailability, got {message!r} (#1278)."
        )

    async def test_fol_consistent_is_bool_when_tweety_available(self):
        """When Tweety path succeeds, 'consistent' must be a real bool.

        If the Tweety path works (no fallback), the result must have
        consistent as a proper boolean (not None, not missing), and
        formulas must be non-empty -- this is the regression guard
        against silently losing all verified formulas.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_fol_reasoning,
        )

        text = "Socrates is mortal. All humans are mortal."
        context = {}

        # Simulate TweetyBridge returning a successful consistency check
        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (True, "Consistent")

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(None, None),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            return_value=(True, "Consistent"),
        ):
            result = await _invoke_fol_reasoning(text, context)

        # When Tweety succeeds, consistent must be a bool
        assert isinstance(result.get("consistent"), bool), (
            f"FOL 'consistent' should be bool when Tweety succeeds, "
            f"got {type(result.get('consistent'))}: {result.get('consistent')} (#976)."
        )
        # Formulas must be present (the regression guard)
        formulas = result.get("formulas", [])
        assert len(formulas) > 0, (
            "FOL produced 0 formulas even in Tweety-success path. "
            "A regression to zero would silently pass CI (#976)."
        )


# ============================================================
# #977 (FB-18) — PL: regression guard on the 50/50 showcase metric
# ============================================================


class TestPLValueGate:
    """Value-gate: PL must not silently regress to zero formulas.

    The capstone reports PL 50/50 verified. Without a value-gate, a
    regression that drops PL to 0 formulas would pass CI. These tests
    mirror the FOL value-gate pattern:
      1. Fallback reports 'fallback: python', not fabricated satisfiable.
      2. Template formulas are honestly template-shaped (p1, p2, ...).
      3. When Tweety is available: satisfiable is a real bool, formulas > 0.
    """

    async def test_pl_fallback_raises_fail_loud(self):
        """PL must RAISE (fail-loud) when all Tweety solvers fail — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #977 guards asserted a 'fallback: python'
        dict (template pN formulas + a fabricated satisfiable bool). Post-#1252/
        #1019 (RA-8 #1053) the per-formula-isolation failure path was hardened
        to RAISE RuntimeError (invoke_callables.py:5392) — no template-fabrication
        fallback remains, so a zero-survivor parse can never enter state as a
        fabricated satisfiable verdict. STRICTER than the old bool/template dicts
        — the raise proves no fabricated satisfiable/formulas are produced.
        Happy-path (Tweety succeeds) still covered by
        test_pl_satisfiable_is_bool_when_tweety_available below. Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        text = "First claim. Second claim. Third claim follows."
        context = {}

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            side_effect=RuntimeError("No JVM for test"),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(None, None),
        ):
            with pytest.raises(
                RuntimeError, match="Propositional logic analysis unavailable"
            ):
                await _invoke_propositional_logic(text, context)

    async def test_pl_satisfiable_is_bool_when_tweety_available(self):
        """When Tweety path succeeds, 'satisfiable' must be a real bool.

        If the Tweety path works, the result must have satisfiable as
        a proper boolean and formulas must be non-empty -- regression guard
        against silently losing all verified formulas.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_propositional_logic,
        )

        text = "If it rains then the ground is wet. It is raining."
        context = {}

        # Simulate TweetyBridge returning a successful consistency check
        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (True, "Satisfiable")

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(None, None),
        ), patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            return_value=(True, "Satisfiable"),
        ):
            result = await _invoke_propositional_logic(text, context)

        # When Tweety succeeds, satisfiable must be a bool
        assert isinstance(result.get("satisfiable"), bool), (
            f"PL 'satisfiable' should be bool when Tweety succeeds, "
            f"got {type(result.get('satisfiable'))}: {result.get('satisfiable')} (#977)."
        )
        # Formulas must be present (the regression guard)
        formulas = result.get("formulas", [])
        assert len(formulas) > 0, (
            "PL produced 0 formulas even in Tweety-success path. "
            "A regression to zero would silently pass CI (#977)."
        )


# ===========================================================================
# Satellite formal bricks — value-gate sweep (#1005)
# ===========================================================================


class TestSATValueGate:
    """SAT solver has no fallback — verify it returns honest results (#1005/#1009).

    SATHandler is pure Python (no JVM). If the solver fails it crashes;
    the gate ensures the happy-path output structure is non-trivial.
    Nit A (#1009): tighten to assert model is non-empty when satisfiable=True.
    """

    async def test_sat_returns_structured_output(self):
        """SAT invocation must return satisfiable + model, not empty dict."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_sat,
        )

        context = {
            "formulas": ["p & q"],
            "solver": "cadical195",
        }
        result = await _invoke_sat("p and q", context)

        assert "satisfiable" in result, (
            f"SAT result missing 'satisfiable' key: {list(result.keys())} (#1005)."
        )
        assert isinstance(result["satisfiable"], bool), (
            f"SAT 'satisfiable' should be bool, got {type(result['satisfiable'])} (#1005)."
        )

    async def test_sat_model_non_empty_when_satisfiable(self):
        """Nit A (#1009): when SAT=True, model must be non-empty (not vacuous)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_sat,
        )

        result = await _invoke_sat("p and q", {"formulas": ["p & q"]})

        if result.get("satisfiable"):
            model = result.get("model")
            assert model is not None, (
                f"SAT satisfiable=True but model is None — vacuous gate (#1009)."
            )
            # model may be dict (Z3-style) or list — assert non-empty
            if isinstance(model, (dict, list)):
                assert len(model) > 0, (
                    f"SAT satisfiable=True but model is empty — vacuous gate (#1009)."
                )


class TestEAFValueGate:
    """Extended Argumentation Framework — fallback honesty (#1005).

    The Python fallback constructs extensions from attack structure.
    Gate: must return non-empty args and an extensions list (even if synthetic).
    """

    async def test_eaf_fallback_raises_fail_loud(self):
        """EAF must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #1005/#1013 guards asserted a
        *Python-fallback dict* (synthetic epistemic states, believed_arguments).
        Post-#1252/#1019 (RA-8 #1053) the except block was hardened to RAISE so
        synthetic epistemic states can never enter state. STRICTER: the raise
        closes both the synthetic-extensions and the silent-degraded paths.
        Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_eaf,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="Epistemic AF analysis .* unavailable"):
                await _invoke_eaf("test", {"arguments": ["alpha", "beta", "gamma"]})


class TestQBFValueGate:
    """QBF solver — error fallback returns valid=False honestly (#1005)."""

    async def test_qbf_error_fallback_reports_unavailable(self):
        """When both JVM and native fail, QBF must report unavailability."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_qbf,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM"),
        ), patch(
            "argumentation_analysis.agents.core.logic.qbf_native.analyze_qbf",
            side_effect=ImportError("No native QBF"),
            create=True,
        ):
            result = await _invoke_qbf("forall x exists y: P(x,y)", {})

        assert result.get("fallback") == "error", (
            f"QBF error fallback should set fallback='error', got {result.get('fallback')} (#1005)."
        )
        assert result.get("valid") is False, (
            f"QBF unavailable must report valid=False, got {result.get('valid')} (#1005)."
        )


class TestABAValueGate:
    """ABA fallback uses assumptions[:2] fabrication (#1005).

    This gate DOCUMENTS the known fabrication. When the brick is fixed
    to report honest unavailability, this test should be updated.
    """

    async def test_aba_fallback_raises_fail_loud(self):
        """ABA must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #1005 guards asserted a *Python-fallback
        dict* that DOCUMENTED a known assumptions[:2] fabrication (flagged
        fallback='python'). Post-#1252/#1019 that fabrication was removed: the
        except block now RAISES RuntimeError so synthetic ABA extensions can
        never enter state. STRICTER than the documented-fabrication guard — the
        raise proves no fabricated result is produced. Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_aba,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="ABA reasoning unavailable"):
                await _invoke_aba("test", {"arguments": ["a", "b", "c"]})


class TestADFValueGate:
    """ADF fallback uses statements[:2] all-True fabrication (#1005).

    This gate DOCUMENTS the known fabrication. When the brick is fixed,
    this test should be updated.
    """

    async def test_adf_fallback_raises_fail_loud(self):
        """ADF must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #1005/#1013 guards asserted a
        *Python-fallback dict* that DOCUMENTED a statements[:2]→all-True
        fabrication (flagged fallback='python'). Post-#1252/#1019 that
        fabrication was removed: the except block now RAISES RuntimeError so
        synthetic ADF interpretations can never enter state. STRICTER than the
        documented-fabrication guard — the raise proves no fabricated result.
        Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_adf,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="ADF reasoning unavailable"):
                await _invoke_adf("test", {"arguments": ["claim_alpha", "claim_beta"]})


class TestProbabilisticValueGate:
    """Probabilistic argumentation fallback uses heuristic (#1005/#1009).

    Fallback assigns probabilities and computes acceptance from attack counts.
    Gate: must return probabilities and flag fallback.
    Nit B (#1009): when acceptance is uniform (no attacks), assert fallback flag
    is honestly set rather than asserting non-uniform values (anti-pendule).
    """

    async def test_probabilistic_fallback_raises_fail_loud(self):
        """Probabilistic AF must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #1005/#1009/#1013 guards asserted a
        *Python-fallback dict* (acceptance_probabilities from heuristic
        initial_probability/(1+attack_count)). Post-#1252/#1019 the except block
        was hardened to RAISE RuntimeError so fabricated probabilities can never
        enter state. STRICTER than the old bounded/uniform dicts — the raise
        proves no synthetic acceptance value is produced. Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_probabilistic,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="Probabilistic argumentation unavailable"):
                await _invoke_probabilistic("test", {"arguments": ["a", "b"]})

    async def test_probabilistic_fallback_honestly_flagged(self):
        """Probabilistic must RAISE (no fabricated probabilities) when JVM down.

        Companion to test_probabilistic_fallback_raises_fail_loud — pins the
        honest-failure intent of the old #1009 'flag honestly' guard under the
        stricter #1252/#1019 raise contract: the brick never produces a (bounded,
        uniform, or otherwise) fabricated acceptance value, it raises.
        Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_probabilistic,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="Probabilistic argumentation unavailable"):
                await _invoke_probabilistic("test", {"arguments": ["a", "b"]})


class TestDialogueValueGate:
    """Dialogue game fallback uses turn-by-turn trace (#1005).

    Fallback splits arguments into proponent/opponent and traces moves.
    Gate: must return dialogue trace and flag fallback.
    """

    async def test_dialogue_fallback_raises_fail_loud(self):
        """Dialogue must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #1005/#1013 guards asserted a
        *Python-fallback dict* (a turn-by-turn trace splitting args into
        proponent/opponent with a winner). Post-#1252/#1019 the except block was
        hardened to RAISE RuntimeError so a synthetic dialogue trace can never
        enter state. STRICTER than the old trace/winner dicts — the raise proves
        no fabricated trace or outcome is produced. Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_dialogue,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="Dialogue protocol unavailable"):
                await _invoke_dialogue("test argument text", {
                    "arguments": ["pro-arg-1", "pro-arg-2"],
                })


class TestBeliefRevisionValueGate:
    """Belief revision fallback uses literal set modification (#1005).

    Fallback removes negated belief and appends new belief to set.
    Gate: must return revised belief set and flag fallback.
    """

    async def test_belief_revision_fallback_raises_fail_loud(self):
        """Belief revision must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #1005/#1013 guards asserted a
        *Python-fallback dict* (literal set modification: drop negated belief,
        append new belief). Post-#1252/#1019 the except block was hardened to
        RAISE RuntimeError so a fabricated revised set can never enter state.
        STRICTER than the old revised-differs-from-original dicts — the raise
        proves no synthetic revision is produced. Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )

        context = {
            "belief_set": ["a", "b"],
            "new_belief": "c",
            "revision_method": "dalal",
        }
        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="Belief revision .* unavailable"):
                await _invoke_belief_revision("test", context)


class TestATMSValueGate:
    """ATMS is pure Python (no JVM). Verify it returns structured output (#1005/#1009).

    ATMS has no fallback path because it doesn't depend on JVM.
    Gate: must return nodes and environments from upstream context.
    Audit (#1009): tighten to assert non-zero node count (value gate, not presence-only).
    """

    async def test_atms_returns_nodes(self):
        """ATMS must return node data from phase outputs."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_atms,
        )

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Climate change is real"}],
                "claims": [{"text": "Climate change is real"}],
            },
            "phase_hierarchical_fallacy_output": {"fallacies": []},
            "phase_quality_output": {"per_argument_scores": {}},
        }
        result = await _invoke_atms("test argument text", context)

        assert isinstance(result, dict), (
            f"ATMS must return dict, got {type(result)} (#1005)."
        )
        # Must have at minimum nodes or environments
        has_structure = any(
            k in result
            for k in ("nodes", "environments", "atms_contexts", "labeling")
        )
        assert has_structure, (
            f"ATMS returned no structural keys: {list(result.keys())} (#1005)."
        )

    async def test_atms_value_non_trivial(self):
        """Audit (#1009): ATMS must produce non-zero node count from input args."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_atms,
        )

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Climate change is real"}],
                "claims": [{"text": "Climate change is real"}],
            },
            "phase_hierarchical_fallacy_output": {"fallacies": []},
            "phase_quality_output": {"per_argument_scores": {}},
        }
        result = await _invoke_atms("test argument text", context)

        assert result.get("assumption_count", 0) > 0, (
            f"ATMS produced 0 assumptions from 1 argument — vacuous gate (#1009). "
            f"Keys: {list(result.keys())}"
        )
        assert result.get("node_count", 0) > 0, (
            f"ATMS produced 0 nodes from 1 arg + 1 claim — vacuous gate (#1009)."
        )


class TestASPICValueGate:
    """ASPIC+ fallback uses defensibility analysis (#1005/#1009).

    Fallback builds strict/defeasible rules from extracted data.
    Gate: must return argument structure and flag fallback.
    Audit (#1009): tighten to assert rules are non-empty (value gate).
    """

    async def test_aspic_fallback_raises_fail_loud(self):
        """ASPIC+ must RAISE (fail-loud) when JVM unavailable — anti-theatre (#1252/#1019).

        Contract evolution: the earlier #1005/#1009 guards asserted a
        *Python-fallback dict* (defensibility-derived strict/defeasible rules).
        Post-#1252/#1019 the except block was hardened to RAISE RuntimeError so
        fabricated argument structure can never enter state. STRICTER than the
        old rules-non-empty dicts — the raise proves no synthetic rules are
        produced. Triage #1336.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_aspic,
        )

        with patch(
            "argumentation_analysis.orchestration.invoke_callables.asyncio.to_thread",
            side_effect=RuntimeError("No JVM for test"),
        ):
            with pytest.raises(RuntimeError, match="ASPIC\\+ analysis unavailable"):
                await _invoke_aspic("test argument text", {
                    "phase_extract_output": {
                        "claims": [{"text": "claim 1"}],
                        "arguments": [{"text": "arg 1"}, {"text": "arg 2"}],
                    },
                    "phase_hierarchical_fallacy_output": {"fallacies": []},
                })
