"""
Tests for counter-argument generation package.

Tests cover: imports, CapabilityRegistry registration, argument parsing,
vulnerability analysis, rhetorical strategies, counter-argument evaluation,
and the agent pipeline (with and without LLM).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

# ── Import tests ──────────────────────────────────────────────────


class TestCounterArgumentImport:
    """Verify all public symbols are importable."""

    def test_import_definitions(self):
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            Argument,
            ArgumentStrength,
            CounterArgument,
            CounterArgumentType,
            EvaluationResult,
            RhetoricalStrategy,
            ValidationResult,
            Vulnerability,
        )

        assert CounterArgumentType.DIRECT_REFUTATION.value == "direct_refutation"
        assert ArgumentStrength.STRONG.value == "strong"
        assert RhetoricalStrategy.SOCRATIC_QUESTIONING.value == "socratic_questioning"

    def test_import_parser(self):
        from argumentation_analysis.agents.core.counter_argument.parser import (
            ArgumentParser,
            VulnerabilityAnalyzer,
            parse_llm_response,
            parse_structured_text,
        )

        assert callable(ArgumentParser)
        assert callable(parse_llm_response)

    def test_import_strategies(self):
        from argumentation_analysis.agents.core.counter_argument.strategies import (
            RhetoricalStrategies,
        )

        assert callable(RhetoricalStrategies)

    def test_import_evaluator(self):
        from argumentation_analysis.agents.core.counter_argument.evaluator import (
            CounterArgumentEvaluator,
        )

        assert callable(CounterArgumentEvaluator)

    def test_import_agent(self):
        from argumentation_analysis.agents.core.counter_argument.counter_agent import (
            CounterArgumentAgent,
        )

        assert callable(CounterArgumentAgent)

    def test_import_from_package(self):
        from argumentation_analysis.agents.core.counter_argument import (
            CounterArgumentAgent,
            ArgumentParser,
            RhetoricalStrategies,
            CounterArgumentEvaluator,
        )

        assert CounterArgumentAgent is not None


# ── Registration tests ────────────────────────────────────────────


class TestCounterArgumentRegistration:
    """Verify CapabilityRegistry integration."""

    def test_register_with_registry(self):
        from argumentation_analysis.core.capability_registry import CapabilityRegistry
        from argumentation_analysis.agents.core.counter_argument import (
            register_with_capability_registry,
        )

        registry = CapabilityRegistry()
        register_with_capability_registry(registry)

        agents = registry.find_agents_for_capability("counter_argument_generation")
        assert len(agents) >= 1
        assert agents[0].name == "counter_argument_agent"

    def test_register_multiple_capabilities(self):
        from argumentation_analysis.core.capability_registry import CapabilityRegistry
        from argumentation_analysis.agents.core.counter_argument import (
            register_with_capability_registry,
        )

        registry = CapabilityRegistry()
        register_with_capability_registry(registry)

        for cap in [
            "counter_argument_generation",
            "argument_parsing",
            "vulnerability_analysis",
            "rhetorical_strategy",
            "counter_argument_evaluation",
        ]:
            agents = registry.find_agents_for_capability(cap)
            assert len(agents) >= 1, f"Missing capability: {cap}"


# ── Parser tests ──────────────────────────────────────────────────


class TestArgumentParser:
    """Test argument parsing and structure extraction."""

    def setup_method(self):
        from argumentation_analysis.agents.core.counter_argument.parser import (
            ArgumentParser,
        )

        self.parser = ArgumentParser()

    def test_parse_simple_argument(self):
        text = "Les vaccins sont sûrs car des études le prouvent"
        arg = self.parser.parse_argument(text)
        assert arg.content == text
        assert len(arg.premises) >= 1
        assert arg.conclusion != ""
        assert arg.confidence > 0

    def test_parse_deductive_argument(self):
        text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
        arg = self.parser.parse_argument(text)
        assert arg.argument_type == "deductive"

    def test_parse_inductive_argument(self):
        text = "Plusieurs études montrent que l'exercice est bénéfique pour la santé."
        arg = self.parser.parse_argument(text)
        assert arg.argument_type == "inductive"

    def test_parse_abductive_argument(self):
        text = "La meilleure explication de ce phénomène est le changement climatique."
        arg = self.parser.parse_argument(text)
        assert arg.argument_type == "abductive"

    def test_confidence_with_markers(self):
        # With both premise and conclusion markers → high confidence
        text = "Puisque les données le montrent, donc la conclusion est valide."
        arg = self.parser.parse_argument(text)
        assert arg.confidence >= 0.7

    def test_confidence_without_markers(self):
        # Even a simple sentence gets premises+conclusion auto-extracted,
        # but with markers the confidence is higher
        text_with = "Puisque les données le montrent, donc la conclusion est valide."
        text_without = "Le ciel est bleu"
        arg_with = self.parser.parse_argument(text_with)
        arg_without = self.parser.parse_argument(text_without)
        assert arg_with.confidence >= arg_without.confidence


# ── Vulnerability tests ───────────────────────────────────────────


class TestVulnerabilityAnalyzer:
    """Test vulnerability identification."""

    def setup_method(self):
        from argumentation_analysis.agents.core.counter_argument.parser import (
            ArgumentParser,
        )
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            Argument,
        )

        self.parser = ArgumentParser()
        self.Argument = Argument

    def test_detect_generalization(self):
        arg = self.Argument(
            content="Tous les politiciens sont corrompus",
            premises=["Tous les politiciens sont corrompus"],
            conclusion="Il ne faut faire confiance à aucun politicien",
            argument_type="deductive",
            confidence=0.7,
        )
        vulns = self.parser.identify_vulnerabilities(arg)
        assert len(vulns) >= 1
        types = [v.type for v in vulns]
        assert "generalisation_abusive" in types

    def test_detect_unfounded_hypothesis(self):
        arg = self.Argument(
            content="Évidemment la terre est plate",
            premises=["Évidemment la terre est plate"],
            conclusion="La terre est plate",
            argument_type="deductive",
            confidence=0.5,
        )
        vulns = self.parser.identify_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "hypothese_non_fondee" in types

    def test_detect_slippery_slope(self):
        arg = self.Argument(
            content="Si on autorise cela, ça mènera à la catastrophe",
            premises=["Si on autorise cela, ça mènera à la catastrophe"],
            conclusion="Il faut interdire",
            argument_type="deductive",
            confidence=0.5,
        )
        vulns = self.parser.identify_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "pente_glissante" in types

    def test_vulnerabilities_sorted_by_score(self):
        arg = self.Argument(
            content="Tous les experts disent évidemment que c'est vrai",
            premises=["Tous les experts disent évidemment que c'est vrai"],
            conclusion="C'est vrai",
            argument_type="deductive",
            confidence=0.5,
        )
        vulns = self.parser.identify_vulnerabilities(arg)
        if len(vulns) >= 2:
            assert vulns[0].score >= vulns[1].score

    def test_no_premises_vulnerability(self):
        arg = self.Argument(
            content="Conclusion sans prémisses",
            premises=[],
            conclusion="Conclusion sans prémisses",
            argument_type="inductive",
            confidence=0.3,
        )
        vulns = self.parser.identify_vulnerabilities(arg)
        types = [v.type for v in vulns]
        assert "manque_de_premisses" in types


# ── Strategy tests ────────────────────────────────────────────────


class TestRhetoricalStrategies:
    """Test rhetorical strategy selection and application."""

    def setup_method(self):
        from argumentation_analysis.agents.core.counter_argument.strategies import (
            RhetoricalStrategies,
        )
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            Argument,
            CounterArgumentType,
            RhetoricalStrategy,
        )

        self.strategies = RhetoricalStrategies()
        self.Argument = Argument
        self.CounterArgumentType = CounterArgumentType
        self.RhetoricalStrategy = RhetoricalStrategy

    def test_suggest_for_deductive(self):
        strategy = self.strategies.suggest_strategy("deductive", "simple argument")
        assert strategy == self.RhetoricalStrategy.REDUCTIO_AD_ABSURDUM

    def test_suggest_for_inductive(self):
        strategy = self.strategies.suggest_strategy("inductive", "simple argument")
        assert strategy == self.RhetoricalStrategy.AUTHORITY_APPEAL

    def test_suggest_for_statistical_content(self):
        strategy = self.strategies.suggest_strategy(
            "inductive", "Les statistiques montrent..."
        )
        assert strategy == self.RhetoricalStrategy.STATISTICAL_EVIDENCE

    def test_get_strategy_prompt(self):
        prompt = self.strategies.get_strategy_prompt(
            self.RhetoricalStrategy.SOCRATIC_QUESTIONING
        )
        assert "Socratic" in prompt or "question" in prompt.lower()

    def test_apply_socratic(self):
        arg = self.Argument(
            content="Tous les X sont Y",
            premises=["Tous les X sont Y"],
            conclusion="Donc Z",
            argument_type="deductive",
            confidence=0.7,
        )
        result = self.strategies.apply_strategy(
            self.RhetoricalStrategy.SOCRATIC_QUESTIONING,
            arg,
            self.CounterArgumentType.PREMISE_CHALLENGE,
        )
        assert len(result) > 10

    def test_apply_reductio(self):
        arg = self.Argument(
            content="On doit toujours suivre cette règle",
            premises=["On doit toujours suivre cette règle"],
            conclusion="On doit toujours suivre cette règle",
            argument_type="deductive",
            confidence=0.7,
        )
        result = self.strategies.apply_strategy(
            self.RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            arg,
            self.CounterArgumentType.REDUCTIO_AD_ABSURDUM,
        )
        assert "absurd" in result.lower() or "extreme" in result.lower()

    def test_apply_statistical(self):
        arg = self.Argument(
            content="Cela cause toujours des problèmes",
            premises=["Cela cause toujours des problèmes"],
            conclusion="Cela cause toujours des problèmes",
            argument_type="inductive",
            confidence=0.5,
        )
        result = self.strategies.apply_strategy(
            self.RhetoricalStrategy.STATISTICAL_EVIDENCE,
            arg,
            self.CounterArgumentType.DIRECT_REFUTATION,
        )
        assert "15%" in result or "statistic" in result.lower()

    def test_get_best_strategy(self):
        arg = self.Argument(
            content="test",
            premises=["test"],
            conclusion="test",
            argument_type="inductive",
            confidence=0.5,
        )
        strategy = self.strategies.get_best_strategy(
            arg, self.CounterArgumentType.PREMISE_CHALLENGE
        )
        assert strategy == self.RhetoricalStrategy.SOCRATIC_QUESTIONING


# ── Evaluator tests ───────────────────────────────────────────────


class TestCounterArgumentEvaluator:
    """Test counter-argument quality evaluation."""

    def setup_method(self):
        from argumentation_analysis.agents.core.counter_argument.evaluator import (
            CounterArgumentEvaluator,
        )
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            Argument,
            ArgumentStrength,
            CounterArgument,
            CounterArgumentType,
        )

        self.evaluator = CounterArgumentEvaluator()
        self.original = Argument(
            content="Le changement climatique est causé par l'activité humaine",
            premises=["Les émissions de CO2 augmentent", "La température augmente"],
            conclusion="Le changement climatique est d'origine humaine",
            argument_type="inductive",
            confidence=0.8,
        )
        self.counter = CounterArgument(
            original_argument=self.original,
            counter_type=CounterArgumentType.PREMISE_CHALLENGE,
            counter_content=(
                "Les émissions de CO2 ne sont pas la seule cause possible. "
                "Des études montrent que les cycles solaires et les variations "
                "naturelles expliquent une partie significative du changement. "
                "Par conséquent, attribuer le réchauffement uniquement à l'activité "
                "humaine est une simplification."
            ),
            target_component="premise_0",
            strength=ArgumentStrength.MODERATE,
            confidence=0.7,
            rhetorical_strategy="socratic_questioning",
        )

    def test_evaluate_returns_result(self):
        result = self.evaluator.evaluate(self.original, self.counter)
        assert hasattr(result, "overall_score")
        assert hasattr(result, "relevance")
        assert hasattr(result, "logical_strength")
        assert hasattr(result, "persuasiveness")
        assert hasattr(result, "originality")
        assert hasattr(result, "clarity")

    def test_scores_in_range(self):
        result = self.evaluator.evaluate(self.original, self.counter)
        for attr in [
            "relevance",
            "logical_strength",
            "persuasiveness",
            "originality",
            "clarity",
            "overall_score",
        ]:
            score = getattr(result, attr)
            assert 0.0 <= score <= 1.0, f"{attr} out of range: {score}"

    def test_overall_is_weighted_sum(self):
        result = self.evaluator.evaluate(self.original, self.counter)
        expected = (
            result.relevance * 0.25
            + result.logical_strength * 0.25
            + result.persuasiveness * 0.20
            + result.originality * 0.15
            + result.clarity * 0.15
        )
        assert abs(result.overall_score - expected) < 0.01

    def test_recommendations_generated(self):
        result = self.evaluator.evaluate(self.original, self.counter)
        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) >= 1

    def test_logical_strength_with_markers(self):
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            CounterArgument,
            CounterArgumentType,
            ArgumentStrength,
        )

        # Counter with logical markers should score higher
        counter_with_logic = CounterArgument(
            original_argument=self.original,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content=(
                "Cet argument est faux car les preuves montrent le contraire. "
                "Donc, la conclusion ne tient pas."
            ),
            target_component="conclusion",
            strength=ArgumentStrength.STRONG,
            confidence=0.8,
            rhetorical_strategy="statistical_evidence",
        )
        counter_without_logic = CounterArgument(
            original_argument=self.original,
            counter_type=CounterArgumentType.DIRECT_REFUTATION,
            counter_content="Non.",
            target_component="conclusion",
            strength=ArgumentStrength.WEAK,
            confidence=0.3,
            rhetorical_strategy="",
        )
        r1 = self.evaluator.evaluate(self.original, counter_with_logic)
        r2 = self.evaluator.evaluate(self.original, counter_without_logic)
        assert r1.logical_strength > r2.logical_strength


# ── Agent pipeline tests ──────────────────────────────────────────


class TestCounterArgumentAgent:
    """Test the counter-argument agent pipeline."""

    def setup_method(self):
        from argumentation_analysis.agents.core.counter_argument.counter_agent import (
            CounterArgumentAgent,
        )

        self.AgentClass = CounterArgumentAgent

    def test_create_agent_no_llm(self):
        agent = self.AgentClass()
        assert agent._llm_client is None
        assert agent.parser is not None
        assert agent.strategies is not None
        assert agent.evaluator is not None

    def test_generate_fallback_no_llm(self):
        """Agent generates template-based counter without LLM."""
        agent = self.AgentClass()
        result = asyncio.get_event_loop().run_until_complete(
            agent.generate_counter_argument(
                "Tous les oiseaux peuvent voler car ils ont des ailes."
            )
        )
        assert "argument" in result
        assert "vulnerabilities" in result
        assert "counter_argument" in result
        assert "evaluation" in result

        # Counter content should be non-empty (template fallback)
        assert len(result["counter_argument"].counter_content) > 10

    def test_generate_with_mock_llm(self):
        """Agent uses LLM when available."""
        mock_client = MagicMock()
        mock_client.chat_completion = AsyncMock(
            return_value="This argument fails because the premise is unfounded."
        )

        agent = self.AgentClass(llm_client=mock_client)
        result = asyncio.get_event_loop().run_until_complete(
            agent.generate_counter_argument(
                "Tous les politiciens sont corrompus car c'est évident."
            )
        )
        assert "counter_argument" in result
        assert "unfounded" in result["counter_argument"].counter_content.lower()
        mock_client.chat_completion.assert_called_once()

    def test_generate_multiple(self):
        """Generate multiple counter-arguments."""
        agent = self.AgentClass()
        results = asyncio.get_event_loop().run_until_complete(
            agent.generate_multiple(
                "Le réchauffement climatique est un mythe car il a neigé hier.",
                count=3,
            )
        )
        assert len(results) == 3
        # Should be sorted by score (best first)
        scores = [r["evaluation"].overall_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_llm_failure_falls_back(self):
        """Agent falls back to template when LLM fails."""
        mock_client = MagicMock()
        mock_client.chat_completion = AsyncMock(side_effect=RuntimeError("API error"))

        agent = self.AgentClass(llm_client=mock_client)
        result = asyncio.get_event_loop().run_until_complete(
            agent.generate_counter_argument("Argument simple pour tester.")
        )
        # Should still produce a result via template fallback
        assert len(result["counter_argument"].counter_content) > 10

    def test_specific_counter_type(self):
        """Specify counter-argument type explicitly."""
        from argumentation_analysis.agents.core.counter_argument.definitions import (
            CounterArgumentType,
        )

        agent = self.AgentClass()
        result = asyncio.get_event_loop().run_until_complete(
            agent.generate_counter_argument(
                "Tous les chats sont noirs car j'en ai vu un.",
                counter_type=CounterArgumentType.REDUCTIO_AD_ABSURDUM,
            )
        )
        assert (
            result["counter_argument"].counter_type
            == CounterArgumentType.REDUCTIO_AD_ABSURDUM
        )


# ── Parser utility tests ─────────────────────────────────────────


class TestParserUtilities:
    """Test LLM response parsing utilities."""

    def test_parse_json_response(self):
        from argumentation_analysis.agents.core.counter_argument.parser import (
            parse_llm_response,
        )

        result = parse_llm_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_structured_text(self):
        from argumentation_analysis.agents.core.counter_argument.parser import (
            parse_structured_text,
        )

        text = "Type: deductive\nConfidence: high"
        result = parse_structured_text(text)
        assert "type" in result
        assert result["type"] == "deductive"
        assert result["confidence"] == "high"

    def test_parse_fallback_to_structured(self):
        from argumentation_analysis.agents.core.counter_argument.parser import (
            parse_llm_response,
        )

        result = parse_llm_response("Key: value\nOther: data")
        assert "key" in result
