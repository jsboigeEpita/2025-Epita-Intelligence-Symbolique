# tests/unit/argumentation_analysis/agents/core/counter_argument/test_strategies_extended.py
"""Extended tests for RhetoricalStrategies — all strategy methods and edge cases."""

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


def _make_arg(content="Un argument", premises=None, conclusion="Donc c'est vrai"):
    return Argument(
        content=content,
        premises=premises or ["Une prémisse"],
        conclusion=conclusion,
        argument_type="deductive",
        confidence=0.7,
    )


# ── get_strategy_prompt ──


class TestGetStrategyPrompt:
    def test_socratic(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.SOCRATIC_QUESTIONING)
        assert "Socratic" in prompt

    def test_reductio(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.REDUCTIO_AD_ABSURDUM)
        assert "absurd" in prompt.lower() or "contradictory" in prompt.lower()

    def test_analogical(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.ANALOGICAL_COUNTER)
        assert "analogy" in prompt.lower()

    def test_authority(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.AUTHORITY_APPEAL)
        assert "authorit" in prompt.lower() or "expert" in prompt.lower()

    def test_statistical(self, strategies):
        prompt = strategies.get_strategy_prompt(RhetoricalStrategy.STATISTICAL_EVIDENCE)
        assert "statistic" in prompt.lower() or "data" in prompt.lower()


# ── suggest_strategy ──


class TestSuggestStrategy:
    def test_deductive_returns_reductio(self, strategies):
        assert (
            strategies.suggest_strategy("deductive", "simple")
            == RhetoricalStrategy.REDUCTIO_AD_ABSURDUM
        )

    def test_inductive_returns_authority(self, strategies):
        assert (
            strategies.suggest_strategy("inductive", "simple")
            == RhetoricalStrategy.AUTHORITY_APPEAL
        )

    def test_abductive_returns_analogical(self, strategies):
        assert (
            strategies.suggest_strategy("abductive", "simple")
            == RhetoricalStrategy.ANALOGICAL_COUNTER
        )

    def test_unknown_type_returns_socratic(self, strategies):
        assert (
            strategies.suggest_strategy("unknown", "simple")
            == RhetoricalStrategy.SOCRATIC_QUESTIONING
        )

    def test_statistical_content_overrides_type(self, strategies):
        result = strategies.suggest_strategy(
            "deductive", "Les statistiques montrent que"
        )
        assert result == RhetoricalStrategy.STATISTICAL_EVIDENCE

    def test_donnees_content_overrides_type(self, strategies):
        result = strategies.suggest_strategy("inductive", "Les données indiquent que")
        assert result == RhetoricalStrategy.STATISTICAL_EVIDENCE

    def test_universal_content_overrides_type(self, strategies):
        result = strategies.suggest_strategy(
            "deductive", "Tous les humains sont mortels"
        )
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_chaque_content_overrides_type(self, strategies):
        result = strategies.suggest_strategy("inductive", "Chaque personne sait que")
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_statistique_checked_before_tous(self, strategies):
        # "statistique" check comes first
        result = strategies.suggest_strategy(
            "deductive", "Tous les statistiques montrent"
        )
        assert result == RhetoricalStrategy.STATISTICAL_EVIDENCE


# ── get_best_strategy ──


class TestGetBestStrategy:
    def test_direct_refutation(self, strategies):
        arg = _make_arg()
        result = strategies.get_best_strategy(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert result == RhetoricalStrategy.STATISTICAL_EVIDENCE

    def test_counter_example(self, strategies):
        arg = _make_arg()
        result = strategies.get_best_strategy(arg, CounterArgumentType.COUNTER_EXAMPLE)
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_alternative_explanation(self, strategies):
        arg = _make_arg()
        result = strategies.get_best_strategy(
            arg, CounterArgumentType.ALTERNATIVE_EXPLANATION
        )
        assert result == RhetoricalStrategy.ANALOGICAL_COUNTER

    def test_premise_challenge(self, strategies):
        arg = _make_arg()
        result = strategies.get_best_strategy(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert result == RhetoricalStrategy.SOCRATIC_QUESTIONING

    def test_reductio(self, strategies):
        arg = _make_arg()
        result = strategies.get_best_strategy(
            arg, CounterArgumentType.REDUCTIO_AD_ABSURDUM
        )
        assert result == RhetoricalStrategy.REDUCTIO_AD_ABSURDUM


# ── apply_strategy: Socratic ──


class TestApplySocratic:
    def test_no_premises(self, strategies):
        arg = Argument(
            content="Un argument sans prémisse",
            premises=[],
            conclusion="Conclusion",
            argument_type="deductive",
            confidence=0.7,
        )
        result = strategies.apply_strategy(
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            arg,
            CounterArgumentType.PREMISE_CHALLENGE,
        )
        assert "evidence" in result.lower() or "What" in result

    def test_premise_challenge_with_generalization(self, strategies):
        arg = _make_arg(premises=["Tous les oiseaux volent"])
        result = strategies.apply_strategy(
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            arg,
            CounterArgumentType.PREMISE_CHALLENGE,
        )
        assert "exception" in result.lower() or "certain" in result.lower()

    def test_premise_challenge_without_generalization(self, strategies):
        arg = _make_arg(premises=["Le ciel est bleu"])
        result = strategies.apply_strategy(
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            arg,
            CounterArgumentType.PREMISE_CHALLENGE,
        )
        assert "basis" in result.lower() or "question" in result.lower()

    def test_direct_refutation(self, strategies):
        arg = _make_arg(conclusion="La terre est plate")
        result = strategies.apply_strategy(
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert "reconcile" in result.lower() or "conclusion" in result.lower()

    def test_default_counter_type(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            arg,
            CounterArgumentType.ALTERNATIVE_EXPLANATION,
        )
        assert "inevitable" in result.lower() or "perspective" in result.lower()


# ── apply_strategy: Reductio ad Absurdum ──


class TestApplyReductio:
    def test_toujours_in_conclusion(self, strategies):
        arg = _make_arg(conclusion="On doit toujours faire cela")
        result = strategies.apply_strategy(
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            arg,
            CounterArgumentType.REDUCTIO_AD_ABSURDUM,
        )
        assert "absurd" in result.lower()

    def test_tous_in_conclusion(self, strategies):
        arg = _make_arg(conclusion="Tous les gens pensent ainsi")
        result = strategies.apply_strategy(
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            arg,
            CounterArgumentType.REDUCTIO_AD_ABSURDUM,
        )
        assert "absurd" in result.lower()

    def test_doit_in_conclusion(self, strategies):
        arg = _make_arg(conclusion="On doit nécessairement accepter")
        result = strategies.apply_strategy(
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            arg,
            CounterArgumentType.REDUCTIO_AD_ABSURDUM,
        )
        assert "obligation" in result.lower() or "universal" in result.lower()

    def test_default_conclusion(self, strategies):
        arg = _make_arg(conclusion="Le soleil est chaud")
        result = strategies.apply_strategy(
            RhetoricalStrategy.REDUCTIO_AD_ABSURDUM,
            arg,
            CounterArgumentType.REDUCTIO_AD_ABSURDUM,
        )
        assert "extreme" in result.lower() or "limits" in result.lower()


# ── apply_strategy: Analogical Counter ──


class TestApplyAnalogical:
    def test_counter_example(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.ANALOGICAL_COUNTER,
            arg,
            CounterArgumentType.COUNTER_EXAMPLE,
        )
        assert "similar" in result.lower() or "same reasoning" in result.lower()

    def test_alternative_explanation(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.ANALOGICAL_COUNTER,
            arg,
            CounterArgumentType.ALTERNATIVE_EXPLANATION,
        )
        assert "analogous" in result.lower() or "alternative" in result.lower()

    def test_default_type(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.ANALOGICAL_COUNTER,
            arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert "like saying" in result.lower() or "limits" in result.lower()


# ── apply_strategy: Authority Appeal ──


class TestApplyAuthority:
    def test_direct_refutation(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.AUTHORITY_APPEAL,
            arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert "expert" in result.lower() or "incorrect" in result.lower()

    def test_premise_challenge(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.AUTHORITY_APPEAL,
            arg,
            CounterArgumentType.PREMISE_CHALLENGE,
        )
        assert "research" in result.lower() or "specialist" in result.lower()

    def test_default_type(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.AUTHORITY_APPEAL,
            arg,
            CounterArgumentType.ALTERNATIVE_EXPLANATION,
        )
        assert "consensus" in result.lower() or "studies" in result.lower()


# ── apply_strategy: Statistical Evidence ──


class TestApplyStatistical:
    def test_direct_refutation(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.STATISTICAL_EVIDENCE,
            arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert "15%" in result or "contradict" in result.lower()

    def test_premise_challenge(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.STATISTICAL_EVIDENCE,
            arg,
            CounterArgumentType.PREMISE_CHALLENGE,
        )
        assert "data" in result.lower() or "empirical" in result.lower()

    def test_default_type(self, strategies):
        arg = _make_arg()
        result = strategies.apply_strategy(
            RhetoricalStrategy.STATISTICAL_EVIDENCE,
            arg,
            CounterArgumentType.ALTERNATIVE_EXPLANATION,
        )
        assert "numbers" in result.lower() or "15%" in result


# ── Helper generators ──


class TestHelperGenerators:
    def test_absurd_consequence_toujours(self, strategies):
        arg = _make_arg(conclusion="Toujours vrai")
        result = strategies._generate_absurd_consequence(arg)
        assert "exception" in result.lower() or "impossible" in result.lower()

    def test_absurd_consequence_tous(self, strategies):
        arg = _make_arg(conclusion="Tous sont coupables")
        result = strategies._generate_absurd_consequence(arg)
        assert "exception" in result.lower() or "impossible" in result.lower()

    def test_absurd_consequence_jamais(self, strategies):
        arg = _make_arg(conclusion="Jamais cela n'arrive")
        result = strategies._generate_absurd_consequence(arg)
        assert "occurrence" in result.lower() or "impossible" in result.lower()

    def test_absurd_consequence_aucun(self, strategies):
        arg = _make_arg(conclusion="Aucun cas n'existe")
        result = strategies._generate_absurd_consequence(arg)
        assert "occurrence" in result.lower() or "impossible" in result.lower()

    def test_absurd_consequence_doit(self, strategies):
        arg = _make_arg(conclusion="On doit faire cela")
        result = strategies._generate_absurd_consequence(arg)
        assert "freedom" in result.lower() or "choice" in result.lower()

    def test_absurd_consequence_default(self, strategies):
        arg = _make_arg(conclusion="Le soleil brille")
        result = strategies._generate_absurd_consequence(arg)
        assert "contradictory" in result.lower() or "false" in result.lower()

    def test_analogy_tous(self, strategies):
        arg = _make_arg(content="Tous les oiseaux volent")
        result = strategies._generate_analogy(arg)
        assert "bird" in result.lower() or "penguin" in result.lower()

    def test_analogy_chaque(self, strategies):
        arg = _make_arg(content="Chaque personne sait")
        result = strategies._generate_analogy(arg)
        assert "bird" in result.lower() or "penguin" in result.lower()

    def test_analogy_toujours(self, strategies):
        arg = _make_arg(content="Le soleil se lève toujours à l'est")
        result = strategies._generate_analogy(arg)
        assert "sun" in result.lower() or "pole" in result.lower()

    def test_analogy_default(self, strategies):
        arg = _make_arg(content="Le ciel est bleu")
        result = strategies._generate_analogy(arg)
        assert "shortest" in result.lower() or "detour" in result.lower()

    def test_statistical_counter(self, strategies):
        arg = _make_arg()
        result = strategies._generate_statistical_counter(arg)
        assert "15%" in result

    def test_fallback_direct_refutation(self, strategies):
        arg = _make_arg()
        result = strategies._fallback_counter_argument(
            arg, CounterArgumentType.DIRECT_REFUTATION
        )
        assert "incorrect" in result.lower()

    def test_fallback_counter_example(self, strategies):
        arg = _make_arg()
        result = strategies._fallback_counter_argument(
            arg, CounterArgumentType.COUNTER_EXAMPLE
        )
        assert "cases" in result.lower() or "contradict" in result.lower()

    def test_fallback_premise_challenge(self, strategies):
        arg = _make_arg(premises=["La terre est ronde"])
        result = strategies._fallback_counter_argument(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert "premise" in result.lower() or "La terre" in result

    def test_fallback_premise_challenge_no_premises(self, strategies):
        arg = _make_arg(premises=[])
        result = strategies._fallback_counter_argument(
            arg, CounterArgumentType.PREMISE_CHALLENGE
        )
        assert "main" in result.lower() or "premise" in result.lower()

    def test_fallback_alternative(self, strategies):
        arg = _make_arg()
        result = strategies._fallback_counter_argument(
            arg, CounterArgumentType.ALTERNATIVE_EXPLANATION
        )
        assert "alternative" in result.lower()

    def test_fallback_reductio(self, strategies):
        arg = _make_arg()
        result = strategies._fallback_counter_argument(
            arg, CounterArgumentType.REDUCTIO_AD_ABSURDUM
        )
        assert "absurd" in result.lower()


# ── apply_strategy fallback ──


class TestApplyStrategyFallback:
    def test_unknown_strategy_uses_fallback(self, strategies):
        """If strategy not in self.strategies dict, fallback is used."""
        arg = _make_arg()
        # Remove a strategy entry to force fallback
        strategies.strategies.pop(RhetoricalStrategy.SOCRATIC_QUESTIONING, None)
        result = strategies.apply_strategy(
            RhetoricalStrategy.SOCRATIC_QUESTIONING,
            arg,
            CounterArgumentType.DIRECT_REFUTATION,
        )
        assert len(result) > 10


# ── init ──


class TestInit:
    def test_all_strategies_registered(self, strategies):
        assert len(strategies.strategies) == 5
        for s in RhetoricalStrategy:
            assert s in strategies.strategies

    def test_each_has_name_and_apply(self, strategies):
        for s, info in strategies.strategies.items():
            assert "name" in info
            assert "apply" in info
            assert callable(info["apply"])
