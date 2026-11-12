# -*- coding: utf-8 -*-
"""#3513 — the reported-position qualifier has a producer and one shared reader.

Cycle 5 measured the whole dead chain: the extraction prompt asks for
``move_author`` (#3265) and ``add_argument`` gates it (#3162), yet 0 of 1,487
``argument_provenance`` entries in the 10 c5 states carry the field — because
the k-window normalizer rebuilds each argument with ``text`` and
``source_quote`` only, dropping the field one hop before the writer. And the
reader that prevents the M2 misreading (a rejected reported position narrated
as the speaker's weakened support) was wired to SETAF lines only.

What this file pins, all synthetic (no LLM answer, no corpus token):

* the normalizer KEEPS a stated ``move_author`` (the dead wire, fixed);
* ONE qualifier function in ``core/fallacy_attribution`` (next to the
  vocabulary it reads) is what every verdict surface calls — read raw, never
  defaulted (#1019);
* the Dung rejection weak point carries the qualifier and the defeat-direction
  rule follows it anywhere it appears (not just SETAF);
* the ABA contrary pair, keyed by unit id (#3014), carries the qualifier too.
"""

from types import SimpleNamespace

from argumentation_analysis.core.fallacy_attribution import MOVE_AUTHOR_REPORTED
from argumentation_analysis.orchestration.invoke_callables import (
    _normalize_items_with_quotes,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_QUALIFIER = "(position rapportée)"
_RULE_MARKER = "jamais une faiblesse de l'attaquant"


def _rich_state(**fields):
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
        argument_provenance={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _dung_rejection_state(move_author):
    """A genuine native Dung rejection (arg_2 attacks arg_1, the extension
    keeps arg_2 only) whose rejected unit carries the stated author."""
    state = _rich_state(
        identified_arguments={
            "arg_1": "Position rapportée par le texte.",
            "arg_2": "Le locuteur la conteste.",
        },
        dung_frameworks={
            "fw_native": {
                "name": "verification_preferred",
                "arguments": ["arg_1", "arg_2"],
                "attacks": [["arg_2", "arg_1"]],
                "extensions": {"all_members": ["arg_2"]},
            }
        },
    )
    entry = {"producer": "llm_extract"}
    if move_author is not None:
        entry["move_author"] = move_author
    state.argument_provenance = {"arg_1": entry}
    return state


def _dung_weak_points(state):
    evidence = build_act3_evidence(state)
    return [wp for wp in evidence.weak_points if wp.source == "dung"]


def test_the_normalizer_keeps_a_stated_move_author():
    """The producer's one wire: the k-window merge rebuilds items with text
    and source_quote — the stated author must survive that rebuild, or the
    writer (which would pass it) never sees it. 0/1,487 in c5."""
    items = _normalize_items_with_quotes(
        [
            {
                "text": "the other camp claims the file was reopened",
                "source_quote": "the other camp claims",
                "move_author": MOVE_AUTHOR_REPORTED,
            }
        ]
    )
    assert items[0]["move_author"] == MOVE_AUTHOR_REPORTED


def test_the_normalizer_leaves_an_absent_author_absent():
    items = _normalize_items_with_quotes(
        [{"text": "a position", "source_quote": "a position"}]
    )
    assert "move_author" not in items[0]


def test_one_qualifier_function_reads_the_field_raw():
    from argumentation_analysis.core.fallacy_attribution import (
        reported_position_qualifier,
    )

    state = _rich_state(
        argument_provenance={
            "arg_1": {"producer": "llm_extract", "move_author": "reported"},
            "arg_2": {"producer": "llm_extract", "move_author": "speaker"},
            "arg_3": {"producer": "llm_extract"},
            "arg_4": {"producer": "llm_extract", "move_author": "someone-else"},
        }
    )
    assert reported_position_qualifier(state, "arg_1") == f" {_QUALIFIER}"
    for unit in ("arg_2", "arg_3", "arg_4"):
        assert reported_position_qualifier(state, unit) == "", unit
    assert reported_position_qualifier(_rich_state(), "arg_1") == ""
    assert reported_position_qualifier(None, "arg_1") == ""


def test_a_reported_dung_rejection_carries_the_qualifier():
    points = _dung_weak_points(_dung_rejection_state("reported"))
    assert points, "the fixture must yield a Dung weak point"
    assert _QUALIFIER in points[0].label


def test_a_speaker_dung_rejection_claims_no_side():
    points = _dung_weak_points(_dung_rejection_state("speaker"))
    assert points
    assert _QUALIFIER not in points[0].label


def test_the_rule_follows_the_qualifier_wherever_it_appears():
    """A qualified DUNG line (not a SETAF one) brings the defeat-direction
    rule — the M2 sentence was written on a Dung verdict surface."""
    prompt = build_act3_prompt(build_act3_evidence(_dung_rejection_state("reported")))
    assert _RULE_MARKER in prompt


def test_no_qualifier_no_rule_on_the_dung_surface():
    prompt = build_act3_prompt(build_act3_evidence(_dung_rejection_state("speaker")))
    assert _RULE_MARKER not in prompt


def test_an_aba_contrary_keyed_by_unit_carries_the_qualifier():
    """#3014 keys the contraries by unit id — the shared function resolves it
    exactly as it resolves a SETAF target."""
    state = _dung_rejection_state("reported")
    state.dung_frameworks = {
        "dung_1": {
            "name": "aba_preferred",
            "formalism_specific": {"contraries": {"arg_1": "la phrase contraire"}},
        }
    }
    evidence = build_act3_evidence(state)
    (finding,) = [
        f for f in evidence.structured_findings if f.capability == "aba_reasoning"
    ]
    assert _QUALIFIER in finding.statement
