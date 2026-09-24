"""#2344: the counter-argument module's two unnamed promises.

``get_best_strategy`` took an argument and never read it: every counter type
answered with the first entry of a fixed list. It now ranks that list with the
argument's own content suggestion, so two arguments can get two strategies.

``ArgumentStrength.DECISIVE`` was weighed by the evaluator and mapped from a
model answer, but the prompt offered only three marks, so it could only arrive
when the model answered off the schema. The prompt now offers every mark the
enum defines, with a criterion for the fourth, and a strength the scale does
not know is recorded as assumed instead of silently scored as moderate.
"""

import json
from types import SimpleNamespace

from argumentation_analysis.agents.core.counter_argument.definitions import (
    Argument,
    ArgumentStrength,
    CounterArgumentType,
    RhetoricalStrategy,
)
from argumentation_analysis.agents.core.counter_argument.strategies import (
    RhetoricalStrategies,
)
import argumentation_analysis.orchestration.invoke_callables as invoke_mod
import argumentation_analysis.orchestration.state_writers as writers_mod


def _argument(content: str, argument_type: str = "deductive") -> Argument:
    return Argument(
        content=content,
        premises=[content],
        conclusion=content,
        argument_type=argument_type,
        confidence=0.5,
    )


class TestGetBestStrategyReadsTheArgument:
    def test_two_arguments_same_counter_type_two_strategies(self):
        strategies = RhetoricalStrategies()
        from_type = _argument("Le projet coûte cher.", argument_type="inductive")
        from_data = _argument("Les données montrent une baisse.")

        assert (
            strategies.get_best_strategy(
                from_type, CounterArgumentType.DIRECT_REFUTATION
            )
            == RhetoricalStrategy.AUTHORITY_APPEAL
        )
        assert (
            strategies.get_best_strategy(
                from_data, CounterArgumentType.DIRECT_REFUTATION
            )
            == RhetoricalStrategy.STATISTICAL_EVIDENCE
        )

    def test_the_content_reaches_a_later_candidate(self):
        strategies = RhetoricalStrategies()
        argument = _argument("Les données montrent une baisse.")

        assert (
            strategies.get_best_strategy(
                argument, CounterArgumentType.PREMISE_CHALLENGE
            )
            == RhetoricalStrategy.STATISTICAL_EVIDENCE
        )

    def test_a_suggestion_off_the_list_leaves_the_first_candidate(self):
        strategies = RhetoricalStrategies()
        argument = _argument("Les données montrent une baisse.")

        assert (
            strategies.get_best_strategy(
                argument, CounterArgumentType.REDUCTIO_AD_ABSURDUM
            )
            == RhetoricalStrategy.REDUCTIO_AD_ABSURDUM
        )


def _client_answering(answer):
    """A client whose one method records the messages and returns ``answer``."""
    calls = []

    async def create(**kwargs):
        calls.append(kwargs)
        message = SimpleNamespace(content=json.dumps(answer))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    return client, calls


class TestTheStrengthScale:
    async def test_the_prompt_offers_every_mark_the_enum_defines(self):
        answer = [{"counter_argument": "c", "strength": "strong"}]
        client, calls = _client_answering(answer)

        await invoke_mod._generate_counters_for_targets(client, "model", ["arg"])

        system_prompt = calls[0]["messages"][0]["content"]
        scale = "|".join(s.value for s in ArgumentStrength)
        assert f'"strength": "{scale}"' in system_prompt
        assert 'Use "decisive" only when' in system_prompt

    def test_the_state_writer_scores_every_mark(self):
        scores = writers_mod._COUNTER_STRENGTH_SCORE
        assert set(scores) == {s.value for s in ArgumentStrength}
        ordered = [scores[s.value] for s in ArgumentStrength]
        assert ordered == sorted(ordered)

    def test_each_mark_moves_the_evaluation(self):
        # A short counter keeps the logical score below its 1.0 ceiling, so
        # every step of the scale is visible, decisive above strong included.
        counters = [
            {"counter_argument": "Non.", "strength": s.value} for s in ArgumentStrength
        ]

        invoke_mod._evaluate_counter_arguments(counters, "Tous les X sont Y.")

        scores = [c["evaluation"]["logical_strength"] for c in counters]
        assert scores == sorted(set(scores)), scores
        assert all("strength_assumed" not in c["evaluation"] for c in counters)

    def test_an_unknown_strength_is_recorded_as_assumed(self):
        counters = [
            {"counter_argument": "Un contre-exemple.", "strength": "overwhelming"},
            {"counter_argument": "Un contre-exemple."},
        ]

        invoke_mod._evaluate_counter_arguments(counters, "Tous les X sont Y.")

        assert counters[0]["evaluation"]["strength_assumed"] == {
            "answered": "overwhelming",
            "scored_as": "moderate",
        }
        assert counters[1]["evaluation"]["strength_assumed"] == {
            "answered": None,
            "scored_as": "moderate",
        }
