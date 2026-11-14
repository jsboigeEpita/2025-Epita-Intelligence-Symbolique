"""#3544 — the bipolar articulation sentence names TEXT and the player, not bare ids.

The planted op-ed (issue ask 1): six units on a town's bridge budget. The
aside — « the last inspection report is a year old and found no fault » — is
the ONLY support of two claims; every other claim has two supports. The
strategist's players carry one player whose quote sits on the aside's ground
and one elsewhere.

Chain under witness (the reader hop, through the real evidence seam):
``build_act3_evidence`` → the bipolar ``StructuredArgFinding`` — its
statement names the node and its dependents by their ``argument_labels``
text, falls back to the id only when no label exists, and names the player
whose case rests on the point — a located quote overlapping the node (they
quote the aside) or a dependent (they quote the claim only the aside
supports) — or no player at all when none is recorded.
"""

from __future__ import annotations

import types

from argumentation_analysis.agents.core.reading import ANCHOR_UNRELATED
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
)

ASIDE = "the last inspection report is a year old and found no fault"
CLAIM_A = "the bridge needs no work this year"
CLAIM_B = "the repair budget can fund the library"
RESERVES = "the town's reserves are healthy"
AUDIT = "the regional audit already cleared the schedule"
FARES = "bus fares cover the maintenance fund"

LABELS = {
    "arg_1": RESERVES,
    "arg_2": ASIDE,
    "arg_3": CLAIM_A,
    "arg_4": CLAIM_B,
    "arg_5": "the maintenance plan can wait a decade",
    "arg_6": FARES,
}

# The aside (arg_2) alone carries claim A and claim B; the aside itself is a
# root (presented as an aside, supported by nothing), and every other claim
# (arg_5) has two supports.
SUPPORTS = [
    ("arg_2", "arg_3"),
    ("arg_2", "arg_4"),
    ("arg_1", "arg_5"),
    ("arg_6", "arg_5"),
]

PROVENANCE = {
    "arg_1": {"producer": "llm_extract", "offset": 0, "source_quote": RESERVES[:30]},
    # The aside sits at 400; the grounded player quotes the same stretch.
    "arg_2": {"producer": "llm_extract", "offset": 400, "source_quote": ASIDE},
    "arg_3": {"producer": "llm_extract", "offset": 700, "source_quote": CLAIM_A[:30]},
    "arg_4": {"producer": "llm_extract", "offset": 900, "source_quote": CLAIM_B[:30]},
    "arg_5": {
        "producer": "llm_extract",
        "offset": 1100,
        "source_quote": "the maintenance",
    },
    "arg_6": {"producer": "llm_extract", "offset": 1300, "source_quote": FARES[:30]},
}

GROUNDED_PLAYER = {
    "name": "la conseillère Ada",
    "role": "élue locale",
    "stance": "for",
    "quote": ASIDE,
    "offset": 400,
    "basis": "text",
}
# Quotes claim A (arg_3, offset 700) — the claim ONLY the aside supports: the
# case rests on the articulation point through its dependent.
DEPENDENT_PLAYER = {
    "name": "la maire Sol",
    "role": "élue locale",
    "stance": "for",
    "quote": CLAIM_A,
    "offset": 700,
    "basis": "text",
}
DISTANT_PLAYER = {
    "name": "l'entrepreneur Bolt",
    "role": "prestataire",
    "stance": "against",
    "quote": FARES,
    "offset": 1300,
    "basis": "text",
}


def _state(
    labels: dict | None = None,
    players: list | None = None,
    provenance: dict | None = None,
    cycles: list | None = None,
) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        bipolar_results=[
            {
                "supports": [list(p) for p in SUPPORTS],
                "support_cycles": cycles or [],
                "articulation_points": [
                    {"node": "arg_2", "dependents": ["arg_3", "arg_4"]}
                ],
                "argument_labels": dict(labels if labels is not None else LABELS),
            }
        ],
        strategic_read={"players": players},
        argument_provenance=dict(provenance if provenance is not None else PROVENANCE),
    )


def _bipolar_statement(state: types.SimpleNamespace) -> str:
    evidence = build_act3_evidence(state)
    for finding in evidence.structured_findings:
        if finding.capability == "bipolar_argumentation":
            return finding.statement
    return ""


class TestArticulationText:
    def test_the_statement_names_the_texts_not_the_ids(self):
        statement = _bipolar_statement(_state(players=[GROUNDED_PLAYER]))
        assert ASIDE in statement, statement
        assert CLAIM_A in statement, statement
        assert CLAIM_B in statement, statement

    def test_the_statement_names_the_player_whose_quote_carries_the_node(self):
        statement = _bipolar_statement(
            _state(players=[DISTANT_PLAYER, GROUNDED_PLAYER])
        )
        assert "la conseillère Ada" in statement, statement
        assert "Bolt" not in statement, statement

    def test_the_statement_names_the_player_whose_quote_carries_a_dependent(self):
        # The dependent player quotes claim A (offset 700), which ONLY the
        # aside supports — that case rests on the point through its dependent.
        statement = _bipolar_statement(
            _state(players=[DISTANT_PLAYER, DEPENDENT_PLAYER])
        )
        assert "la maire Sol" in statement, statement
        assert "Bolt" not in statement, statement

    def test_no_recorded_player_names_no_player(self):
        statement = _bipolar_statement(_state(players=[]))
        assert ASIDE in statement, statement
        assert "dont le cas de" not in statement, statement

    def test_no_strategic_read_names_no_player(self):
        state = _state(players=[])
        delattr(state, "strategic_read")
        statement = _bipolar_statement(state)
        assert ASIDE in statement, statement
        assert "dont le cas de" not in statement, statement

    def test_an_unlocated_player_is_not_named(self):
        unlocated = dict(GROUNDED_PLAYER, offset=None)
        statement = _bipolar_statement(_state(players=[unlocated]))
        assert "dont le cas de" not in statement, statement

    def test_an_unrelated_anchor_is_not_the_players_ground(self):
        """#3556 minor: the marker reaches act III.

        ``anchor="unrelated"`` keeps the quote and its offset as the record
        of what was offered, so an overlap test alone still names the player
        whose case rests on the point — through another party's passage. The
        producer refused that passage; act III honours the refusal.
        """
        unrelated = dict(GROUNDED_PLAYER, anchor=ANCHOR_UNRELATED)
        statement = _bipolar_statement(_state(players=[unrelated]))
        assert "dont le cas de" not in statement, statement
        assert ASIDE in statement, statement

    def test_an_unlabelled_dependent_falls_back_to_its_id(self):
        labels = dict(LABELS)
        del labels["arg_4"]
        statement = _bipolar_statement(_state(labels=labels, players=[GROUNDED_PLAYER]))
        assert ASIDE in statement, statement
        assert "arg_4" in statement, statement
        assert CLAIM_B not in statement, statement

    def test_an_unprovenanced_point_names_no_player(self):
        statement = _bipolar_statement(_state(players=[GROUNDED_PLAYER], provenance={}))
        assert ASIDE in statement, statement
        assert "dont le cas de" not in statement, statement


class TestCycleText:
    def test_a_support_cycle_renders_texts_not_ids(self):
        state = _state(
            players=[],
            cycles=[["arg_1", "arg_6"]],
        )
        # Drop the articulation points so the cycle branch is the finding.
        state.bipolar_results[0]["articulation_points"] = []
        statement = _bipolar_statement(state)
        assert RESERVES in statement, statement
        assert FARES in statement, statement
        assert "arg_1" not in statement, statement
        assert "arg_6" not in statement, statement


class TestPromptHop:
    def test_the_act3_prompt_carries_the_aside_text(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            build_act3_prompt,
        )

        prompt = build_act3_prompt(
            build_act3_evidence(_state(players=[GROUNDED_PLAYER]))
        )
        assert ASIDE in prompt
        assert "la conseillère Ada" in prompt

    def test_the_act3_prompt_carries_the_figure(self):
        # Positive control (the issue's ask): « point d'articulation » is in
        # the assembled prompt on ``main`` too — this reproduces the measured
        # reader hop (8/8 panel docs with points) and must STAY green.
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            build_act3_prompt,
        )

        prompt = build_act3_prompt(
            build_act3_evidence(_state(players=[GROUNDED_PLAYER]))
        )
        assert "point d'articulation" in prompt
