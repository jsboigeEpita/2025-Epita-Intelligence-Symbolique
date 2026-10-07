"""#2967 — the units a writer is asked to discuss reach it WHOLE.

A fixed 220-character head cut showed the Act II narrative and the
deep-synthesis briefing the *setup* of a long unit and dropped what it
*concludes*: on the 06/10 authorized pass the governance winner kept 31 %
of its text, its operative clause sitting past character 340 (#1914).

The fix is a budget ALLOCATION, not a global raise: cited units (attack
targets, counter targets, governance winner) get their full text up to
``CITED_UNIT_TEXT_CAP``; every other unit keeps the short cap, so the
prompt does not grow with N (positive control below). No cut is silent
anymore, and no cut lands mid-word.

Every witness is born-red on main: the distinctive token sits past the
short cap, inside the cited budget. Synthetic content only — no corpus
sentence, opaque ids only.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)

# A filler sentence is ~52 chars; 8 of them push the distinctive token past
# 400 — well beyond the 220 short cap, well inside the cited budget. The
# unit then carries ~6 more sentences to ~730 chars.
_FILLER = "Phrase synthetique numero {:02d} pour occuper la longueur. "
_TOKEN = "TOKEN_DISTINCTIF_AU_MILIEU"


def _long_unit(token_pos: int = 8) -> str:
    """A ~730-char synthetic unit whose distinctive token sits at ~416."""
    parts = [_FILLER.format(i) for i in range(token_pos)]
    parts.append(_TOKEN + " conclut l'unite en declarant sa clause operative.")
    parts.extend(_FILLER.format(i) for i in range(token_pos, token_pos + 6))
    return "".join(parts)


def _state(*cited_builders) -> UnifiedAnalysisState:
    real = UnifiedAnalysisState("2967 synthetic probe")
    for build in cited_builders:
        build(real)
    return real


def _with_governance_winner(winner: str) -> callable:
    def build(real: UnifiedAnalysisState) -> None:
        real.governance_decisions.append(
            {"method": "copeland", "winner": winner, "scores": {winner: 3.0}}
        )

    return build


class TestCitedWinnerReachesTheWriters:
    """The issue's witness: a 700-char governance winner, token past 400."""

    def _state(self) -> UnifiedAnalysisState:
        def build(real: UnifiedAnalysisState) -> None:
            real.add_argument(_long_unit(), producer="kb_heuristic")
            real.add_argument("Unite courte synthetique sans enjeu de coupe.")

        return _state(_with_governance_winner("arg_1"), build)

    def test_winner_text_reaches_the_act2_prompt(self) -> None:
        prompt = build_act2_prompt(build_act2_evidence(self._state()))
        assert _TOKEN in prompt

    def test_winner_text_reaches_the_deep_synthesis_briefing(self) -> None:
        briefing = DeepSynthesisAgent.build_artifact_briefing(self._state())
        assert _TOKEN in briefing

    def test_uncited_long_unit_keeps_the_short_cap(self) -> None:
        """Positive control (issue Expected 2): the allocation is not a
        global raise — an UNCITED unit of the same length stays short, on
        both surfaces, so the prompt does not grow with N.

        Refounded for the #2989 rework: the cited winner's text now travels
        on TWO surfaces of the Act II prompt (its movement beat — #2967 —
        and the governance line, which carries the winner's text the way
        Acte III already does). The old ``count == 1`` proxy conflated the
        two and no longer measures the intent. The invariant that does: the
        prompt's text budget is UNCHANGED by adding an uncited long unit.
        """
        without_uncited = build_act2_prompt(build_act2_evidence(self._state()))
        state = self._state()
        # arg_3: same length, cited by nothing
        state.add_argument(_long_unit(), producer="kb_heuristic")
        prompt = build_act2_prompt(build_act2_evidence(state))
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert prompt.count(_TOKEN) == without_uncited.count(_TOKEN), (
            "adding an UNCITED long unit must not raise the prompt's text "
            "budget — the allocation is targeted, not global"
        )
        assert briefing.count(_TOKEN) == 1
        uncited = next(
            a
            for a in build_act2_evidence(state).movements[0].arguments
            if a.arg_id == "arg_3"
        )
        assert len(uncited.description) <= 220 + len(" […]")


class TestOtherCitedPopulations:
    """Attack targets and counter targets get the cited budget too."""

    def _state(self) -> UnifiedAnalysisState:
        def build(real: UnifiedAnalysisState) -> None:
            real.add_argument(_long_unit(), producer="kb_heuristic")  # arg_1
            real.add_argument(_long_unit(), producer="kb_heuristic")  # arg_2
            real.add_argument(_long_unit(), producer="kb_heuristic")  # arg_3
            real.add_fallacy(
                fallacy_type="Ad hominem",
                justification="synthetic",
                target_arg_id="arg_2",
            )
            real.counter_arguments.append(
                {"target_arg_id": "arg_3", "counter_content": "synthetic counter"}
            )

        return _state(build)

    def test_fallacy_and_counter_targets_reach_the_briefing(self) -> None:
        briefing = DeepSynthesisAgent.build_artifact_briefing(self._state())
        assert briefing.count(_TOKEN) == 2  # arg_2 (attacked) + arg_3 (targeted)

    def test_cited_unit_ids_covers_the_three_populations(self) -> None:
        from argumentation_analysis.reporting.restitution.cited_units import (
            cited_unit_ids,
        )

        assert cited_unit_ids(self._state()) == {"arg_2", "arg_3"}


class TestCutIsVisibleAndBounded:
    """Expected 3 and 4: no silent cut, no mid-word cut."""

    def test_briefing_cut_carries_the_visible_marker(self) -> None:
        state = _state(
            lambda real: real.add_argument(
                _long_unit(), producer="kb_heuristic"
            )  # uncited: stays cut
        )
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert "[artifact:identified_arguments.arg_1]" in briefing
        line = next(
            ln for ln in briefing.splitlines() if "identified_arguments.arg_1" in ln
        )
        assert " […]" in line

    def test_act2_cut_lands_on_a_sentence_boundary(self) -> None:
        """The 220-char point falls mid-word in the 5th sentence (4 fillers
        = 208 chars); the cut must retreat to the sentence boundary at 208,
        never slice a word."""
        state = _state(
            lambda real: real.add_argument(
                _long_unit(), producer="kb_heuristic"
            )  # uncited: stays cut
        )
        evidence = build_act2_evidence(state)
        desc = evidence.movements[0].arguments[0].description
        assert desc.endswith(". […]")

    def test_text_within_the_cap_is_untouched(self) -> None:
        state = _state(
            lambda real: real.add_argument(
                "Unite courte sans aucune coupe possible ici.",
                producer="kb_heuristic",
            )
        )
        evidence = build_act2_evidence(state)
        assert (
            evidence.movements[0].arguments[0].description
            == "Unite courte sans aucune coupe possible ici."
        )

    def test_cited_budget_covers_the_witness_and_stays_under_the_max(self) -> None:
        """Calibration guard: the constant must cover the issue's witness
        (a cited 700-char unit, whole) and stay under doc_A's observed max
        (2 142) — it is an allocation, not an unbounded include."""
        from argumentation_analysis.reporting.restitution.cited_units import (
            CITED_UNIT_TEXT_CAP,
        )

        assert CITED_UNIT_TEXT_CAP >= 700
        assert CITED_UNIT_TEXT_CAP <= 2142


class TestGovernanceWinnerMirror:
    """The winner mirror follows act2's _collect_governance semantics."""

    def test_last_non_trivial_decision_wins(self) -> None:
        from argumentation_analysis.reporting.restitution.cited_units import (
            governance_winner_id,
        )

        state = _state()
        state.governance_decisions.append(
            {"method": "copeland", "winner": "N/A", "scores": {}}
        )
        state.governance_decisions.append(
            {"method": "copeland", "winner": "arg_2", "scores": {"arg_2": 1.0}}
        )
        state.governance_decisions.append(
            {"method": "borda", "winner": "arg_5", "scores": {"arg_5": 2.0}}
        )
        assert governance_winner_id(state) == "arg_5"

    def test_no_method_means_no_winner(self) -> None:
        from argumentation_analysis.reporting.restitution.cited_units import (
            governance_winner_id,
        )

        state = _state()
        state.governance_decisions.append({"method": "", "winner": "arg_1"})
        assert governance_winner_id(state) is None

    def test_empty_decisions_yield_none(self) -> None:
        from argumentation_analysis.reporting.restitution.cited_units import (
            governance_winner_id,
        )

        assert governance_winner_id(_state()) is None
