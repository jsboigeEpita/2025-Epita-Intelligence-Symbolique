# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.core.counter_argument.strategies
Covers RhetoricalStrategies: init, get_strategy_prompt, apply_strategy,
suggest_strategy, get_best_strategy, strategy implementations, helpers.
"""

import pytest

from argumentation_analysis.agents.core.counter_argument.strategies import (
    RhetoricalStrategies,
)
from argumentation_analysis.agents.core.counter_argument.definitions import (
    Argument,
    CounterArgumentType,
    RhetoricalStrategy,
)


@pytest.fixture
def strategies():
    return RhetoricalStrategies()


def _make_argument(**overrides):
    defaults = dict(
        content="Tous les étudiants doivent réussir.",
        premises=["Tous les étudiants travaillent dur"],
        conclusion="Tous les étudiants doivent réussir",
        argument_type="deductive",
        confidence=0.8,
    )
    defaults.update(overrides)
    return Argument(**defaults)


# ============================================================
# Initialization
# ============================================================

class TestInit:
    def test_creates_instance(self, strategies):
        assert isinstance(strategies, RhetoricalStrategies)

    def test_has_five_strategies(self, strategies):
        assert len(strategies.strategies) == 5

    def test_all_strategies_have_apply(self, strategies):
        for key, info in strategies.strategies.items():
            assert "apply" in info
            assert callable(info["apply"])

    def test_all_strategies_have_name(self, strategies):
        for key, info in strategies.strategies.items():
            assert "name" in info
            assert isinstance(info["name"], str)


# ============================================================
# get_strategy_prompt
# ============================================================

class TestGetStrategyPrompt:
    def test_socratic(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.SOCRATIC_QUESTIONING)
        assert "Socratic" in prompt or "questions" in prompt

    def test_reductio(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.REDUCTIO_AD_ABSURDUM)
        assert "absurd" in prompt or "contradictory" in prompt

    def test_analogical(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.ANALOGICAL_COUNTER)
        assert "analogy" in prompt

    def test_authority(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.AUTHORITY_APPEAL)
        assert "authorities" in prompt or "experts" in prompt

    def test_statistical(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.STATISTICAL_EVIDENCE)
        assert "statistical" in prompt.lower() or "data" in prompt.lower()

    def test_unknown_fallback(self, strategies):
        prompt = strategies.get_strategy_prompt("unknown_strategy")
        assert "appropriate" in prompt.lower()


# ============================================================
# apply_strategy
# ============================================================

class TestApplyStrategy:
    def test_socratic_returns_string(self, strategies):
        arg = _make_argument()
        result = strategies.apply_strategy(
            RhetoricalStrategy.SOCRATIC_QUESTIONING, arg,
            CounterArgumentType.PREMISE_CHALLENGE,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_reductio_returns_string(self, strategies):
        arg = _make_argument()
        result = strategies.apply_strategy(
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM, arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert isinstance(result, str)

    def test_analogical_returns_string(self, strategies):
        arg = _make_argument()
        result = strategies.apply_strategy(
            RhetoricalStrategy.ANALOGICAL_COUNTER, arg,
            CounterArgumentType.COUNTER_EXAMPLE,
        )
        assert isinstance(result, str)

    def test_authority_returns_string(self, strategies):
        arg = _make_argument()
        result = strategies.apply_strategy(
            RhetoricalStrategy.AUTHORITY_APPEAL, arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert isinstance(result, str)

    def test_statistical_returns_string(self, strategies):
        arg = _make_argument()
        result = strategies.apply_strategy(
            RhetoricalStrategy.STATISTICAL_EVIDENCE, arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert isinstance(result, str)

    def test_unknown_uses_fallback(self, strategies):
        arg = _make_argument()
        result = strategies.apply_strategy(
            "unknown", arg, CounterArgumentType.DIRECT_REFUTATION,
        )
        assert isinstance(result, str)


# ============================================================
# suggest_strategy
# ============================================================

class TestSuggestStrategy:
    def test_statistical_content(self, strategies):
        result = strategies.suggest_strategy("inductive", "Les statistiques montrent")
        assert result == RhetoricalStrategy.STATISTICAL_EVIDENCE

    def test_donnees_content(self, strategies):
        result = strategies.suggest_strategy("inductive", "Les données indiquent")
        assert result == RhetoricalStrategy.STATISTICAL_EVIDENCE

    def test_tous_content(self, strategies):
        result = strategies.suggest_strategy("deductive", "Tous les hommes")
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_chaque_content(self, strategies):
        result = strategies.suggest_strategy("deductive", "Chaque élève")
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_deductive_type(self, strategies):
        result = strategies.suggest_strategy("deductive", "Un texte neutre")
        assert result == RhetoricalStrategy.REDUCTIO_AD_ABSURDUM

    def test_inductive_type(self, strategies):
        result = strategies.suggest_strategy("inductive", "Un texte neutre")
        assert result == RhetoricalStrategy.AUTHORITY_APPEAL

    def test_abductive_type(self, strategies):
        result = strategies.suggest_strategy("abductive", "Un texte neutre")
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_unknown_type_fallback(self, strategies):
        result = strategies.suggest_strategy("unknown", "Un texte neutre")
        assert result == RhetoricalStrategy.SOCRATIC_QUESTIONING


# ============================================================
# get_best_strategy
# ============================================================

class TestGetBestStrategy:
    def test_direct_refutation(self, strategies):
        arg = _make_argument()
        result = strategies.get_best_strategy(arg, CounterArgumentType.DIRECT_REFUTATION)
        assert result == RhetoricalStrategy.STATISTICAL_EVIDENCE

    def test_counter_example(self, strategies):
        arg = _make_argument()
        result = strategies.get_best_strategy(arg, CounterArgumentType.COUNTER_EXAMPLE)
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_alternative_explanation(self, strategies):
        arg = _make_argument()
        result = strategies.get_best_strategy(arg, CounterArgumentType.ALTERNATIVE_EXPLANATION)
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_premise_challenge(self, strategies):
        arg = _make_argument()
        result = strategies.get_best_strategy(arg, CounterArgumentType.PREMISE_CHALLENGE)
        assert result == RhetoricalStrategy.SOCRATIC_QUESTIONING

    def test_reductio(self, strategies):
        arg = _make_argument()
        result = strategies.get_best_strategy(arg, CounterArgumentType.REDUCTIO_AD_ABSURDUM)
        assert result == RhetoricalStrategy.REDUCTIO_AD_ABSURDUM


# ============================================================
# Strategy implementations
# ============================================================

class TestSocraticQuestioning:
    def test_no_premises(self, strategies):
        arg = _make_argument(premises=[])
        result = strategies._apply_socratic_questioning(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert "evidence" in result.lower()

    def test_premise_challenge_with_generalization(self, strategies):
        arg = _make_argument(premises=["Tous les experts confirment"])
        result = strategies._apply_socratic_questioning(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert "exception" in result.lower() or "counter-example" in result.lower()

    def test_premise_challenge_no_generalization(self, strategies):
        arg = _make_argument(premises=["Les données existent"])
        result = strategies._apply_socratic_questioning(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert "basis" in result.lower() or "premise" in result.lower()

    def test_direct_refutation(self, strategies):
        arg = _make_argument()
        result = strategies._apply_socratic_questioning(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "conclusion" in result.lower()

    def test_other_type_fallback(self, strategies):
        arg = _make_argument()
        result = strategies._apply_socratic_questioning(
            arg, CounterArgumentType.COUNTER_EXAMPLE
        )
        assert "conclusion" in result.lower() or "inevitable" in result.lower()


class TestReductioAdAbsurdum:
    def test_tous_in_conclusion(self, strategies):
        arg = _make_argument(conclusion="Tous les cas sont identiques")
        result = strategies._apply_reductio_ad_absurdum(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "absurd" in result.lower() or "accept" in result.lower()

    def test_doit_in_conclusion(self, strategies):
        arg = _make_argument(conclusion="On doit agir maintenant")
        result = strategies._apply_reductio_ad_absurdum(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "obligation" in result.lower() or "universal" in result.lower()

    def test_generic_conclusion(self, strategies):
        arg = _make_argument(conclusion="Le résultat est clair")
        result = strategies._apply_reductio_ad_absurdum(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "logic" in result.lower() or "extreme" in result.lower()


class TestAnalogicalCounter:
    def test_counter_example_type(self, strategies):
        arg = _make_argument()
        result = strategies._apply_analogical_counter(
            arg, CounterArgumentType.COUNTER_EXAMPLE
        )
        assert "similar" in result.lower() or "fails" in result.lower()

    def test_alternative_explanation_type(self, strategies):
        arg = _make_argument()
        result = strategies._apply_analogical_counter(
            arg, CounterArgumentType.ALTERNATIVE_EXPLANATION
        )
        assert "analogous" in result.lower() or "alternative" in result.lower()

    def test_other_type_fallback(self, strategies):
        arg = _make_argument()
        result = strategies._apply_analogical_counter(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "like" in result.lower() or "limits" in result.lower()


class TestAuthorityAppeal:
    def test_direct_refutation(self, strategies):
        arg = _make_argument()
        result = strategies._apply_authority_appeal(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "experts" in result.lower()

    def test_premise_challenge(self, strategies):
        arg = _make_argument()
        result = strategies._apply_authority_appeal(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert "research" in result.lower() or "specialists" in result.lower()

    def test_other_fallback(self, strategies):
        arg = _make_argument()
        result = strategies._apply_authority_appeal(
            arg, CounterArgumentType.COUNTER_EXAMPLE
        )
        assert "consensus" in result.lower() or "studies" in result.lower()


class TestStatisticalEvidence:
    def test_direct_refutation(self, strategies):
        arg = _make_argument()
        result = strategies._apply_statistical_evidence(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "statistics" in result.lower() or "contradict" in result.lower()

    def test_premise_challenge(self, strategies):
        arg = _make_argument()
        result = strategies._apply_statistical_evidence(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert "data" in result.lower() or "empirical" in result.lower()

    def test_other_fallback(self, strategies):
        arg = _make_argument()
        result = strategies._apply_statistical_evidence(
            arg, CounterArgumentType.COUNTER_EXAMPLE
        )
        assert "numbers" in result.lower() or "story" in result.lower()


# ============================================================
# Helper generators
# ============================================================

class TestHelperGenerators:
    def test_absurd_consequence_toujours(self, strategies):
        arg = _make_argument(conclusion="C'est toujours vrai")
        result = strategies._generate_absurd_consequence(arg)
        assert "exception" in result.lower()

    def test_absurd_consequence_jamais(self, strategies):
        arg = _make_argument(conclusion="Jamais cela ne change")
        result = strategies._generate_absurd_consequence(arg)
        assert "impossible" in result.lower()

    def test_absurd_consequence_doit(self, strategies):
        arg = _make_argument(conclusion="On doit le faire")
        result = strategies._generate_absurd_consequence(arg)
        assert "freedom" in result.lower() or "choice" in result.lower()

    def test_absurd_consequence_generic(self, strategies):
        arg = _make_argument(conclusion="Le résultat est clair")
        result = strategies._generate_absurd_consequence(arg)
        assert "contradictory" in result.lower() or "false" in result.lower()

    def test_analogy_tous(self, strategies):
        arg = _make_argument(content="Tous les oiseaux volent")
        result = strategies._generate_analogy(arg)
        assert "birds" in result.lower() or "penguins" in result.lower()

    def test_analogy_toujours(self, strategies):
        arg = _make_argument(content="C'est toujours vrai")
        result = strategies._generate_analogy(arg)
        assert "sun" in result.lower()

    def test_analogy_generic(self, strategies):
        arg = _make_argument(content="Un texte neutre")
        result = strategies._generate_analogy(arg)
        assert "path" in result.lower() or "detour" in result.lower()

    def test_statistical_counter(self, strategies):
        arg = _make_argument()
        result = strategies._generate_statistical_counter(arg)
        assert "15%" in result

    def test_fallback_counter(self, strategies):
        arg = _make_argument()
        result = strategies._fallback_counter_argument(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "incorrect" in result.lower() or "conclusion" in result.lower()

    def test_fallback_counter_premise(self, strategies):
        arg = _make_argument()
        result = strategies._fallback_counter_argument(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert "premise" in result.lower() or "supported" in result.lower()
