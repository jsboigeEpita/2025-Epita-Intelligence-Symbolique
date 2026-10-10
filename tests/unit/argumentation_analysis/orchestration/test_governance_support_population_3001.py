"""#3001 (a′, R1079) — the GE-4 support population reaches the record and both Acts.

The R1077 census measured that the writer read ``copeland_scores``, a key
GE-4's ``vote_result`` never carries → ``scores == {}`` on every real vote,
and everything that says HOW SOLID the verdict is was dropped between
``_aggregate_governance_votes`` and the record: the per-option support across
methods (tallied from ``winners_per_method``), ``n_methods_decided`` and
``winner_basis`` (the tier that decided — condorcet → majority → plurality,
#2300). "11 methods out of 12" and "the plurality fallback tier only" are two
different verdicts that both Acts rendered with the same sentence.

Coordinator arbitration (R1079, issue comment 6079542976): the dead read
goes, the population gets wired, and ``render_governance_lead`` hands the
writer a QUALITATIVE robustness band for ``kind == "vote"`` only — never a
raw counter, never a badge (#1914).

Producer → state → both Acts on the REAL writer (the R1078 lesson: a
hand-built record certifies a shape the producer does not emit).

Born red on ``c14c7f4ec``: main records no support population, renders a
unanimous vote and a 6/12 plurality-tier vote with the same sentence, and
the CLI prints ``Governance (method):`` with an empty body (``result`` is
never written).

Privacy: invented filler, opaque ids, no corpus sentence. No JVM, no LLM.
"""

from __future__ import annotations

import pytest
from rich.console import Console

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_governance_to_state,
)
from argumentation_analysis.reporting.restitution.cited_units import (
    qualitative_support_band,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# Twelve distinct method names — the shape of a real winners_per_method
# (the aggregate consults the voting rules + social-choice functions).
_METHODS = (
    "majority",
    "plurality",
    "borda",
    "condorcet",
    "quadratic",
    "approval",
    "stv",
    "copeland",
    "kemeny_young",
    "schulze",
    "copeland_safe",
    "kemeny_young_safe",
)

_UNIT_TEXTS = {
    "arg_7": "Première position synthétique sur la clause opératoire.",
    "arg_9": "Seconde position détaillée sur le calendrier.",
    "arg_11": "Troisième position sur le périmètre exact.",
}


def _written_state(output: dict) -> UnifiedAnalysisState:
    """The REAL writer on the REAL state class — the producer boundary."""
    state = UnifiedAnalysisState(
        initial_text="filler text for the witness, no corpus content."
    )
    _write_governance_to_state(output, state, {})
    # The units the winner(s) resolve against — set after the write so the
    # writer decides the record's shape, not this fixture.
    state.identified_arguments = dict(_UNIT_TEXTS)
    return state


def _unanimous_output() -> dict:
    """A GE-4-shaped vote: every deciding method chose the same option."""
    return {
        "recommended_method": "condorcet",
        "vote_result": {
            "winner": "arg_7",
            "votes": ["arg_7"] * 12,
            "method": "formal-aggregation",
            "results": {
                "winners_per_method": {m: "arg_7" for m in _METHODS},
                "n_methods_decided": 12,
                "distinct_winners": ["arg_7"],
                "inter_method_disagreement": False,
                "condorcet_winner": "arg_7",
                "winner": "arg_7",
                "winner_basis": "condorcet",
            },
        },
    }


def _narrow_output() -> dict:
    """6/12 for the winner, the rest split — decided by the plurality tier.

    The coordinator's example: a narrow vote whose winner comes from the
    FALLBACK tier (no condorcet winner, no majority) must not read like a
    unanimous one.
    """
    wpm: dict[str, str] = {m: "arg_7" for m in _METHODS[:6]}
    wpm.update({m: "arg_9" for m in _METHODS[6:10]})
    wpm.update({m: "arg_11" for m in _METHODS[10:]})
    return {
        "recommended_method": "plurality",
        "vote_result": {
            "winner": "arg_7",
            "votes": [w for w in wpm.values()],
            "method": "formal-aggregation",
            "results": {
                "winners_per_method": wpm,
                "n_methods_decided": 12,
                "distinct_winners": ["arg_7", "arg_9", "arg_11"],
                "inter_method_disagreement": True,
                "condorcet_winner": None,
                "winner": "arg_7",
                "winner_basis": "plurality",
            },
        },
    }


_PROMPTS = {
    "act2": lambda st: build_act2_prompt(build_act2_evidence(st)),
    "act3": lambda st: build_act3_prompt(build_act3_evidence(st)),
}


def _deliberation(prompt: str) -> str:
    start = prompt.find("DÉLIBÉRATION COLLECTIVE")
    assert start != -1, "the prompt carries no deliberation block"
    return prompt[start:]


def _gov_line(prompt: str) -> str:
    """The GOUVERNANCE line only — lead + support band + divergence clause
    are ONE string. Negative assertions stay scoped here: the Act III
    template itself says « unanimité » elsewhere, and that is not the band
    under test."""
    text = _deliberation(prompt)
    start = text.find("GOUVERNANCE")
    assert start != -1, "the prompt carries no governance line"
    return text[start : text.find("\n", start)]


class TestTheWriterRecordsTheSupportPopulation:
    """Producer → record: the tally, the count of deciding methods, the tier."""

    def test_a_unanimous_vote_records_support_for_the_winner(self) -> None:
        state = _written_state(_unanimous_output())
        record = state.governance_decisions[-1]
        assert record["winner"] == "arg_7"
        assert record["winner_provenance"] == "vote_aggregate"
        assert record["support_by_option"] == {"arg_7": 12}
        assert record["n_methods_decided"] == 12
        assert record["winner_basis"] == "condorcet"

    def test_a_narrow_vote_records_every_option_and_the_fallback_tier(self) -> None:
        state = _written_state(_narrow_output())
        record = state.governance_decisions[-1]
        assert record["support_by_option"] == {"arg_7": 6, "arg_9": 4, "arg_11": 2}
        assert record["n_methods_decided"] == 12
        assert record["winner_basis"] == "plurality"

    def test_the_dead_copeland_read_is_gone_no_scores_are_invented(self) -> None:
        """The honest shape: a GE-4 vote records NO option scores — the
        legacy read that never fired on a real vote is gone (R1079: measured,
        ``output["vote_result"]`` has one production writer, and it builds
        the key list at invoke_callables.py:2705 without copeland_scores)."""
        state = _written_state(_unanimous_output())
        record = state.governance_decisions[-1]
        assert record["scores"] == {}

    def test_a_vote_without_the_population_adds_no_phantom_fields(self) -> None:
        """Honest absence: a bare vote (no results verdict) stores none of
        the new fields — the population is earned, never defaulted."""
        state = _written_state(
            {"vote_result": {"winner": "arg_7", "method": "formal-aggregation"}}
        )
        record = state.governance_decisions[-1]
        assert record["winner"] == "arg_7"
        for absent in ("support_by_option", "n_methods_decided", "winner_basis"):
            assert absent not in record


@pytest.mark.parametrize("act", ["act2", "act3"])
class TestTheSupportBandReachesTheActs:
    """Record → both Acts: a QUALITATIVE band, never a counter (#1914)."""

    def test_a_unanimous_vote_reads_as_unanimous(self, act: str) -> None:
        state = _written_state(_unanimous_output())
        line = _gov_line(_PROMPTS[act](state))
        assert "unanimité des méthodes" in line
        assert "large majorité" not in line
        assert "de justesse" not in line
        assert "palier de repli" not in line

    def test_a_narrow_plurality_vote_reads_as_narrow(self, act: str) -> None:
        state = _written_state(_narrow_output())
        line = _gov_line(_PROMPTS[act](state))
        assert "de justesse" in line
        assert "palier de repli" in line
        assert "unanimité" not in line
        assert "large majorité" not in line
        # R1080: the winner holds exactly half the methods (6/12) — a tie is
        # not a majority, and the GOUVERNANCE line must not say one
        assert "majorit" not in line

    def test_the_band_is_never_a_raw_counter(self, act: str) -> None:
        """#1914: qualitative only — no "6/12", no "11 méthodes sur 12"."""
        for output in (_unanimous_output(), _narrow_output()):
            state = _written_state(output)
            line = _gov_line(_PROMPTS[act](state))
            assert "/12" not in line
            assert "12 méthodes" not in line

    def test_a_divergent_vote_carries_each_winners_band_next_to_its_text(
        self, act: str
    ) -> None:
        """#2989 + #3001: in a divergence, each winner's support travels
        beside its text, not behind one aggregate number."""
        state = _written_state(_narrow_output())
        line = _gov_line(_PROMPTS[act](state))
        assert "Le vote DIVERGE" in line
        # the winner text and its band share the divergence clause
        assert "Première position synthétique" in line
        # R1080: 6/12, 4/12 and 2/12 hold no majority — each winner's band is
        # the honest no-majority one, and the pinned "majorité étroite" the
        # pre-rework head rendered for all three is gone
        assert "partie seulement des méthodes" in line
        assert "majorit" not in line

    def test_a_lead_winner_below_half_reads_as_no_majority(self, act: str) -> None:
        """R1080: a condorcet-tier winner chosen by fewer than half the
        deciding methods — the tier decided, but the line must not say a
        majority of the methods did. Realistic shape: the pairwise champion
        that only 5 of 12 methods name as their winner."""
        wpm: dict[str, str] = {m: "arg_7" for m in _METHODS[:5]}
        wpm.update({m: "arg_9" for m in _METHODS[5:9]})
        wpm.update({m: "arg_11" for m in _METHODS[9:]})
        output = {
            "recommended_method": "condorcet",
            "vote_result": {
                "winner": "arg_7",
                "votes": [w for w in wpm.values()],
                "method": "formal-aggregation",
                "results": {
                    "winners_per_method": wpm,
                    "n_methods_decided": 12,
                    "distinct_winners": ["arg_7", "arg_9", "arg_11"],
                    "inter_method_disagreement": True,
                    "condorcet_winner": "arg_7",
                    "winner": "arg_7",
                    "winner_basis": "condorcet",
                },
            },
        }
        state = _written_state(output)
        line = _gov_line(_PROMPTS[act](state))
        assert "partie seulement des méthodes" in line
        # no divergent winner holds a majority either (5/4/3) — the whole
        # line is majority-free, by measurement not by scoping
        assert "majorit" not in line


class TestTheBandMatchesTheDefinition:
    """R1080: the band's words are checked against the DEFINITION on the full
    grid — n 1..12 × s 1..n × basis — not against the function's own
    thresholds.

    A majority means strictly more than half: the word "majorité" appears
    iff 2s > n (a tie, 2s == n, is not one); unanimity iff s == n; "large"
    iff 3s >= 2n. On the pre-rework head ``3ae69904b`` this reddens on 144
    cells: 108 that affirmatively claim « une majorité étroite » with
    2s <= n (36 per non-plurality basis — the coordinator's count,
    reproduced on this seat), plus the 36 plurality cells whose « aucune
    majorité claire » carries the word into a support that holds none."""

    def test_every_cell_of_the_grid_matches_the_definition(self) -> None:
        for n in range(1, 13):
            for s in range(1, n + 1):
                for basis in (None, "condorcet", "majority", "plurality"):
                    band = qualitative_support_band(s, n, basis)
                    assert band is not None, (s, n, basis)
                    if s == n:
                        assert "unanimité" in band, (s, n, basis, band)
                        continue
                    assert ("majorit" in band) == (2 * s > n), (s, n, basis, band)
                    assert ("large" in band) == (3 * s >= 2 * n), (
                        s,
                        n,
                        basis,
                        band,
                    )


@pytest.mark.parametrize("act", ["act2", "act3"])
class TestTheBandIsAVoteOnlyClause:
    """The robustness clause grafts onto the ``kind`` framing of #3000 — it
    must NOT fire for the fallback origins, whose winner is not a unit."""

    def test_an_llm_resolution_gets_no_support_band(self, act: str) -> None:
        output = {
            "llm_governance_assessment": {
                "recommended_method": "copeland",
                "recommended_resolution": "compromise",
                "stakeholder_analysis": [
                    {"agent": "elector_a", "position": "x", "influence": 0.5}
                ],
            }
        }
        state = _written_state(output)
        text = _deliberation(_PROMPTS[act](state))
        assert "unanimité des méthodes" not in text
        assert "Le soutien de ce verdict" not in text


class TestTheCliPrintsWhatTheRecordCarries:
    """The dead ``result`` read (never written) is repaired: the CLI line
    prints the winner and its origin, not an empty body."""

    def test_the_governance_line_names_the_winner_and_its_origin(self) -> None:
        from argumentation_analysis.cli.output_formatter import _render_debate

        console = Console(record=True, width=100)
        _render_debate(
            console,
            {
                "debate_transcripts": [],
                "governance_decisions": [
                    {
                        "id": "gov_1",
                        "method": "copeland",
                        "winner": "arg_7",
                        "winner_provenance": "vote_aggregate",
                    }
                ],
            },
        )
        rendered = console.export_text()
        assert "Governance (copeland)" in rendered
        assert "arg_7" in rendered
        assert "vote social-choice" in rendered
        # the dead body is gone: no trailing empty colon line
        assert "Governance (copeland): \n" not in rendered

    def test_an_unrecorded_origin_is_said_not_guessed(self) -> None:
        from argumentation_analysis.cli.output_formatter import _render_debate

        console = Console(record=True, width=100)
        _render_debate(
            console,
            {
                "debate_transcripts": [],
                "governance_decisions": [
                    {"id": "gov_1", "method": "borda", "winner": "arg_9"}
                ],
            },
        )
        rendered = console.export_text()
        assert "arg_9" in rendered
        assert "origine non enregistrée" in rendered
