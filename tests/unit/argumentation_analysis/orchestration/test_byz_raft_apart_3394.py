"""#3394 (tranche R1145) — the band counts SCRUTINS; the protocols are named apart.

The coordinator's tranche on the R1309 measurement: « La bande compte les
scrutins seuls, et les deux protocoles de consensus sont nommés à part
(« 9 des 10 scrutins, plus deux protocoles de consensus »). Le verdict déclaré
ne les lit jamais, et CLAUDE.md les classe hors scrutins. Cela s'applique
aussi à ``methods_by_option`` : la liste nommée dans la bande ne doit pas
ranger Raft parmi les « méthodes de vote ». »

What this file pins, end to end on a synthetic 12-method state:

* the CATEGORY lives with the governance methods (``CONSENSUS_PROTOCOLS``),
  not with the RNG flag — "stochastic" is how they run, not what they are;
* the PRODUCER's support population is the deciding SCRUTINS
  (``n_methods_decided``), and the two protocols' verdicts travel apart in
  ``consensus_protocols``; the divergence set still reads every decided
  method (unchanged — a protocol landing elsewhere IS a divergence);
* the WRITER's tallies skip the protocols (a protocol's choice is not a
  vote's support) and its named list never carries one;
* the BAND reads « … des 10 scrutins », and closes with « , plus deux
  protocoles de consensus » — never counting them in the fraction;
* honest absence at every step: no protocol in the record, no protocol
  clause; a protocol that did not decide is not named.

Born-red discipline: every symbol born in this PR is imported INSIDE its
test. Everything is synthetic — invented ids, no LLM, no JVM, no network.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.governance.governance_agent import Agent
from argumentation_analysis.orchestration.invoke_callables import (
    _aggregate_governance_votes,
)
from argumentation_analysis.orchestration.state_writers import (
    _write_governance_to_state,
)

_SCRUTINS = (
    "majority",
    "plurality",
    "borda",
    "condorcet",
    "quadratic",
    "approval",
    "stv",
    "copeland",
    "schulze",
    "condorcet_winner",
)
_PROTOCOLS = ("byzantine", "raft")


def _agents() -> list:
    return [
        Agent("e1", "stubborn", ["arg_1", "arg_2", "arg_3"]),
        Agent("e2", "stubborn", ["arg_1", "arg_2", "arg_3"]),
        Agent("e3", "stubborn", ["arg_1", "arg_3", "arg_2"]),
    ]


def _aggregate() -> dict:
    agents = _agents()
    options = ["arg_1", "arg_2", "arg_3"]
    ballots = [list(a.preferences) for a in agents]
    return _aggregate_governance_votes(agents, options, ballots)


# ---------------------------------------------------------------------------
# The category — declared where the methods live, not where the RNG lives
# ---------------------------------------------------------------------------


def test_the_category_is_the_two_protocols_and_they_are_governance_methods():
    from argumentation_analysis.agents.core.governance.governance_methods import (
        CONSENSUS_PROTOCOLS,
        GOVERNANCE_METHODS,
    )

    assert set(CONSENSUS_PROTOCOLS) == set(_PROTOCOLS), (
        "the category is exactly byzantine and raft — CLAUDE.md: "
        "« 5 voting rules + 2 distributed-consensus protocols »"
    )
    assert set(CONSENSUS_PROTOCOLS) <= set(
        GOVERNANCE_METHODS
    ), "the protocols are governance methods; what they are NOT is scrutins"


# ---------------------------------------------------------------------------
# The producer — the population is the scrutins, the protocols travel apart
# ---------------------------------------------------------------------------


def test_the_support_population_counts_scrutins_only():
    verdict = _aggregate()
    wpm = verdict["winners_per_method"]

    scrutins_decided = {
        m for m, w in wpm.items() if w is not None and m not in _PROTOCOLS
    }
    assert verdict["n_methods_decided"] == len(scrutins_decided), (
        "the band's denominator counts the deciding SCRUTINS — counting the "
        "two protocols inflated it by two (12 instead of 10)"
    )
    assert verdict["n_methods_decided"] == 10, (
        "on a 3-elector concordant profile all ten scrutins decide; a 12 "
        "here means the protocols were counted as votes again"
    )


def test_the_protocols_verdicts_travel_apart_and_named():
    verdict = _aggregate()

    protocols = verdict["consensus_protocols"]
    assert isinstance(protocols, dict)
    assert set(protocols) == set(_PROTOCOLS), (
        "both protocols decide on a concordant profile; each verdict is "
        "recorded APART from the vote's support"
    )
    assert all(
        verdict["winners_per_method"][name] == winner
        for name, winner in protocols.items()
    ), "the apart record must be the protocols' OWN verdicts, not a recompute"


def test_the_divergence_set_still_reads_every_decided_method():
    """The tranche does not touch divergence: a protocol that lands elsewhere
    IS a divergence, and the declared-winner tiers never read them (#2300)."""
    agents = [
        Agent("e1", "stubborn", ["arg_1", "arg_2", "arg_3"]),
        Agent("e2", "stubborn", ["arg_2", "arg_1", "arg_3"]),
        Agent("e3", "stubborn", ["arg_3", "arg_1", "arg_2"]),
    ]
    options = ["arg_1", "arg_2", "arg_3"]
    verdict = _aggregate_governance_votes(
        agents, options, [list(a.preferences) for a in agents]
    )

    decided_all = {
        str(w) for w in verdict["winners_per_method"].values() if w is not None
    }
    assert set(verdict["distinct_winners"]) == decided_all, (
        "distinct_winners covers every decided method, protocols included — "
        "the tranche scopes the BAND's population, not the divergence"
    )


# ---------------------------------------------------------------------------
# The writer — no protocol in the tallies, none in the named list
# ---------------------------------------------------------------------------


def _twelve_method_output() -> dict:
    """Ten scrutins choose arg_7; the two protocols land elsewhere."""
    wpm = {m: "arg_7" for m in _SCRUTINS}
    wpm["byzantine"] = "arg_9"
    wpm["raft"] = "arg_11"
    return {
        "recommended_method": "condorcet",
        "vote_result": {
            "winner": "arg_7",
            "votes": [w for w in wpm.values()],
            "method": "formal-aggregation",
            "results": {
                "winners_per_method": wpm,
                "n_methods_decided": 10,
                "consensus_protocols": {"byzantine": "arg_9", "raft": "arg_11"},
                "distinct_winners": ["arg_7", "arg_9", "arg_11"],
                "inter_method_disagreement": True,
                "condorcet_winner": "arg_7",
                "winner": "arg_7",
                "winner_basis": "condorcet",
            },
        },
    }


def _written_state(output: dict):
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    state = UnifiedAnalysisState("filler text for the witness, no corpus content.")
    _write_governance_to_state(output, state, {})
    state.identified_arguments = {
        "arg_7": "Première position synthétique.",
        "arg_9": "Seconde position synthétique.",
        "arg_11": "Troisième position synthétique.",
    }
    return state


def test_the_writer_does_not_tally_a_protocols_choice_as_support():
    record = _written_state(_twelve_method_output()).governance_decisions[-1]

    assert record["support_by_option"] == {"arg_7": 10}, (
        "the protocols' choices (arg_9, arg_11) are not the vote's support — "
        "a protocol is not a scrutin"
    )
    assert record["n_methods_decided"] == 10


def test_the_writer_never_ranks_a_protocol_among_the_voting_methods():
    record = _written_state(_twelve_method_output()).governance_decisions[-1]

    named = [name for names in record["methods_by_option"].values() for name in names]
    assert named, "the ten scrutins are named"
    for protocol in _PROTOCOLS:
        assert protocol not in named, (
            f"« {protocol} » must not sit in the list of methods that "
            "carried the winner (#3441's named list)"
        )


def test_the_writer_persists_the_protocols_apart():
    record = _written_state(_twelve_method_output()).governance_decisions[-1]

    assert record["consensus_protocols"] == {
        "byzantine": "arg_9",
        "raft": "arg_11",
    }


def test_an_old_record_without_protocols_stores_no_key():
    """Honest absence: a pre-tranche verdict carries no protocols, and the
    writer invents none."""
    output = _twelve_method_output()
    del output["vote_result"]["results"]["consensus_protocols"]
    record = _written_state(output).governance_decisions[-1]

    assert "consensus_protocols" not in record
    assert record["support_by_option"] == {"arg_7": 10}, (
        "the tally still excludes the protocols — the category is read from "
        "the method names, never from the record's optional clause"
    )


def test_a_protocol_that_did_not_decide_is_not_named():
    output = _twelve_method_output()
    output["vote_result"]["results"]["consensus_protocols"] = {
        "byzantine": "arg_9",
        "raft": None,
    }
    record = _written_state(output).governance_decisions[-1]

    assert record["consensus_protocols"] == {"byzantine": "arg_9"}, (
        "a protocol that produced no verdict is an honest absence — naming "
        "it would advertise a procedure the record cannot show"
    )


# ---------------------------------------------------------------------------
# The band — scrutins counted, protocols named apart, in both Acts
# ---------------------------------------------------------------------------


def _band_of(prompt: str) -> str:
    """The support-band SENTENCE only.

    The lead keeps running after it (divergence clause, per-unit status), and
    those continuations legitimately differ between the Acts — the band is
    what must not. The band holds no full stop of its own, so the first one
    closes it.
    """
    marker = "Le soutien de ce verdict :"
    start = prompt.find(marker)
    assert start != -1, "the prompt carries no support band"
    stop = prompt.find(".", start)
    assert stop != -1, "the band sentence never closes"
    return prompt[start : stop + 1]


def test_the_band_counts_scrutins_and_names_the_protocols_apart():
    from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
        build_act3_evidence,
        build_act3_prompt,
    )

    state = _written_state(_twelve_method_output())
    band = _band_of(build_act3_prompt(build_act3_evidence(state)))

    assert (
        "des 10 scrutins" in band
    ), "the denominator is the ten scrutins — 12 was the defect"
    assert (
        "plus deux protocoles de consensus" in band
    ), "the protocols ran: the reader must see them, named as what they are"
    assert "byzantine" not in band and "Raft" not in band, (
        "named apart means NAMED AS PROTOCOLS — never listed among the "
        "voting methods that carried the winner"
    )


def test_both_acts_carry_the_same_band():
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        build_act2_evidence,
        build_act2_prompt,
    )
    from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
        build_act3_evidence,
        build_act3_prompt,
    )

    state = _written_state(_twelve_method_output())
    act2 = _band_of(build_act2_prompt(build_act2_evidence(state)))
    act3 = _band_of(build_act3_prompt(build_act3_evidence(state)))

    assert act2 == act3, "one renderer, no drift (cited_units.render_governance_lead)"


def test_a_record_without_protocols_renders_no_protocol_clause():
    output = _twelve_method_output()
    del output["vote_result"]["results"]["consensus_protocols"]
    from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
        build_act3_evidence,
        build_act3_prompt,
    )

    band = _band_of(build_act3_prompt(build_act3_evidence(_written_state(output))))

    assert "des 10 scrutins" in band
    assert (
        "protocole" not in band
    ), "a record that carries no protocol renders no clause — honest absence"


def test_a_scrutin_only_state_keeps_the_pre_tranche_shape_but_for_the_noun():
    """Control: a state with no protocols in its record reads exactly as
    before, with the population's true name."""
    from argumentation_analysis.reporting.restitution.cited_units import (
        qualitative_support_band,
    )

    assert qualitative_support_band(10, 10) == (
        "à l'unanimité des scrutins qui ont décidé (10 des 10 scrutins)"
    )
    assert qualitative_support_band(9, 10) == (
        "par une large majorité des scrutins (9 des 10 scrutins)"
    )
