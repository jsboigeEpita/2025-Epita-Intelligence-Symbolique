"""#3658 item 46c — the act-replay fidelity witness, and what it must be able to say.

``scripts/panel/act_replay_fidelity.py`` is the offline witness the act replay
is read with before any paid call: which inputs the judged render has, whether
the harvested records reproduce one text byte for byte, and that the
comparison fails when a text is altered. These guards pin each of those claims
on invented material — no corpus, no cycle directory of the panel, no network,
no JVM, no LLM — so a regression reddens here instead of letting the witness
certify a render it no longer measures.

The fresh-process guards start child interpreters (a few seconds each): they
carry no ``slow`` marker on purpose, since the gate deselects ``slow``.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.dataset.render_campaign_reading_folder import (  # noqa: E402
    _ARTIFACT_ANCHOR_RE,
    doc_facts,
    render_fiche,
)
from scripts.panel import _common as c  # noqa: E402
from scripts.panel import act_replay_fidelity as w  # noqa: E402

#: A pipeline signature as the campaign writes it for an argumentative document.
_PIPELINE_SIGNATURE: Dict[str, Any] = dict(w.SYNTHETIC_SIGNATURE)

#: A non-argumentative document: the metadata carries a value the text holds.
_NON_ARGUMENTATIVE_STATE: Dict[str, Any] = {
    "raw_text": "Texte synthétique : le rapport inventé annonce une décision inventée.",
    "source_metadata": {
        "event": "une décision inventée",
        "participants": ["un rapport inventé"],
        "report_title": "",
    },
    "interpretive_question": "Question synthétique ?",
}

#: A wall-clock cut: upstream material recorded, no act at all.
_CUT_STATE: Dict[str, Any] = {
    "raw_text": "Texte synthétique où figure un extrait inventé du témoin.",
    "identified_arguments": {"arg_1": "un extrait inventé du témoin"},
    "identified_fallacies": {
        "soph_1": {"type": "appel à l'autorité", "justification": "inventée"}
    },
    "stakes_and_stakeholders": {"stakes": [{"description": "un enjeu inventé"}]},
    "strategic_read": {"reading": "une lecture inventée"},
    "historical_context": {"situation": "une situation inventée"},
}

#: The two other engines, as their adapters normalise a record (#3470, #3472).
_CONVERSATION_STATE: Dict[str, Any] = {
    "fallacies": [
        {"type": "appel à l'autorité", "justification": "inventée pour le témoin"}
    ],
    "fallacies_count": 1,
    "fol": {"formulas": ["une formule inventée"], "consistency": True},
    "analysis_errors": ["un incident inventé"],
}
_DELEGATION_STATE: Dict[str, Any] = {
    "objectives": [{"id": "obj_1", "description": "un objectif inventé"}],
    "tasks": [
        {
            "task_id": "t1",
            "capability": "inventée",
            "status": "done",
            "outputs": {"un_champ": "un produit inventé"},
        }
    ],
    "task_counts": {"planned": 2, "productive": 1, "failed": 0, "degraded": 0},
    "conclusion": "une conclusion inventée",
    "degraded": True,
    "degradation_reasons": ["un manque inventé"],
    "partial": False,
}


def _state(**overrides: Any) -> Dict[str, Any]:
    state = dict(w.SYNTHETIC_STATE)
    state.update(overrides)
    return state


def _engine_signature(mode: str) -> Dict[str, Any]:
    return {
        "opaque_id": "corpus_witness",
        "outcome": {"status": "ok"},
        "provenance": {"mode": mode},
    }


def _write_cycle(root: Path, states: Dict[str, Dict[str, Any]]) -> Path:
    """A harvested cycle's two folders, with the signature a harvest writes."""
    cycle = root / "cycle"
    (cycle / "states").mkdir(parents=True)
    (cycle / "signatures").mkdir(parents=True)
    for doc, state in states.items():
        (cycle / "states" / f"state_full_{doc}.json").write_text(
            json.dumps(state, ensure_ascii=False), encoding="utf-8"
        )
        recorded: Dict[str, Any] = {
            key: {"length": len(state.get(key) or ""), "stripped": True}
            for key in w.RENDER_INPUTS
        }
        recorded[w.QUESTION] = state.get(w.QUESTION)
        signature = {
            **w.SYNTHETIC_SIGNATURE,
            "opaque_id": doc,
            "state": recorded,
        }
        (cycle / "signatures" / f"signature_{doc}.json").write_text(
            json.dumps(signature, ensure_ascii=False), encoding="utf-8"
        )
    return cycle


# ---------------------------------------------------------------------------
# One text, byte for byte, and a comparison that can fail
# ---------------------------------------------------------------------------


def test_the_identity_replay_is_byte_equal_through_the_three_constructions() -> None:
    reference = w.judge_render(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE)

    assert "Acte I synthétique" in reference
    assert w.fiche_render(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE) == reference
    assert w.replay_render(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE) == reference


def test_the_replay_never_mutates_the_harvested_record() -> None:
    before = json.dumps(w.SYNTHETIC_STATE, ensure_ascii=False, sort_keys=True)

    w.replayed_state(w.SYNTHETIC_STATE, {"act1_framing": "un autre cadre"})

    assert json.dumps(w.SYNTHETIC_STATE, ensure_ascii=False, sort_keys=True) == before


def test_an_altered_act_moves_its_own_section_and_no_other() -> None:
    reference = w.judge_render(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE)
    altered = _state(act2_narrative=w.SYNTHETIC_STATE["act2_narrative"] + " Ajouté.")
    rebuilt = w.judge_render(altered, w.SYNTHETIC_SIGNATURE)

    diff = w.compare(reference, rebuilt)

    assert diff["equal"] is False
    assert diff["sections_differing"] == ["Acte II — récit"]
    assert diff["sections_only_in_reference"] == []
    assert diff["sections_only_in_rebuilt"] == []
    # The offset counts BYTES: the render carries accented letters and dashes.
    offset = diff["first_diff_offset"]
    assert offset is not None
    left, right = reference.encode("utf-8"), rebuilt.encode("utf-8")
    assert left[:offset] == right[:offset]
    assert left[offset:] != right[offset:]
    assert b"### Acte II" in left[:offset]
    # A character count would land earlier: the text before the difference
    # holds multi-byte letters and dashes.
    char_offset = next(
        index for index, (one, two) in enumerate(zip(reference, rebuilt)) if one != two
    )
    assert char_offset < offset


def test_a_different_text_injected_through_the_replay_breaks_the_comparison() -> None:
    reference = w.judge_render(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE)
    injected = {**w.recorded_acts(w.SYNTHETIC_STATE), "act3_conclusion": w.MARKER}

    diff = w.compare(
        reference, w.replay_render(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE, injected)
    )

    assert diff["equal"] is False
    assert diff["sections_differing"] == ["Acte III — conclusion"]


def test_an_inserted_anchor_moves_every_later_anchored_section_and_the_notes() -> None:
    reference = w.judge_render(w.ANCHORED_STATE, w.SYNTHETIC_SIGNATURE)
    renumbered = dict(w.ANCHORED_STATE, act1_framing=w.ANCHOR_INSERTED)

    diff = w.compare(reference, w.judge_render(renumbered, w.SYNTHETIC_SIGNATURE))

    assert diff["equal"] is False
    assert diff["sections_differing"] == [
        "Acte I — cadrage",
        "Synthèse narrative",
        "Question interprétative",
        w.NOTES_HEADING,
    ]
    assert w.notes_rendered(reference) == 3
    assert w.notes_rendered(w.judge_render(renumbered, w.SYNTHETIC_SIGNATURE)) == 4


def test_the_synthetic_control_holds_and_can_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert w.synthetic_control()["ok"] is True

    real_replay = w.replay_render

    def drifting(state: Any, signature: Any, acts: Any = None) -> str:
        return real_replay(state, signature, acts) + " "

    monkeypatch.setattr(w, "replay_render", drifting)

    control = w.synthetic_control()
    assert control["ok"] is False
    assert control["identity"]["equal"] is False


def test_a_sub_heading_removed_inside_an_act_does_not_shift_the_later_sections() -> (
    None
):
    with_sub_heading = _state(
        act2_narrative="### Un sous-titre de l'acte\n\nUne phrase inventée.\n"
    )
    without = _state(act2_narrative="Une phrase inventée.")

    diff = w.compare(
        w.judge_render(with_sub_heading, w.SYNTHETIC_SIGNATURE),
        w.judge_render(without, w.SYNTHETIC_SIGNATURE),
    )

    assert diff["sections_differing"] == ["Acte II — récit"]
    assert diff["sections_only_in_reference"] == ["Un sous-titre de l'acte"]
    assert diff["sections_only_in_rebuilt"] == []


def test_compare_is_byte_strict() -> None:
    assert w.compare("acte un", "acte un")["equal"] is True
    assert w.compare("acte un", "acte un")["first_diff_offset"] is None

    one_character = w.compare("acte un", "acte deux")
    assert one_character["equal"] is False
    assert one_character["first_diff_offset"] == 5
    # An offset in BYTES: the difference sits at the fourth byte of ``aé b``
    # and at its third character.
    accented = w.compare("aé b", "aé  c")
    assert accented["equal"] is False
    assert accented["first_diff_offset"] == 4
    decomposed = w.compare("un été", "un été")
    # The two arguments of ``decomposed`` read alike and differ in bytes: the
    # second spells its accents with combining characters (U+0301), so the
    # encodings part where the composed ``é`` begins.
    assert decomposed["equal"] is False
    assert decomposed["first_diff_offset"] == 3
    trailing = w.compare("acte un\n", "acte un\n\n")
    assert trailing["equal"] is False
    assert trailing["first_diff_offset"] == 8
    end_of_line = w.compare("acte\r\nun", "acte\nun")
    assert end_of_line["equal"] is False
    assert end_of_line["first_diff_offset"] == 4
    assert w.compare("acte  un", "acte un")["equal"] is False


def test_the_anchor_pattern_is_the_producer_s_own() -> None:
    samples = [
        "Un cadre appuyé sur [artifact:alpha].",
        "[artifact:a_b-1.2] et [artifact:x] mais [artifact:a b] ni [artifact:]",
        "double [artifact:[x]] simple [artifact:y]]",
        "sans ancre",
    ]

    measured = [w.ANCHOR_RE.findall(text) for text in samples]

    assert measured == [_ARTIFACT_ANCHOR_RE.findall(text) for text in samples]
    assert measured[0] == ["alpha"]
    assert measured[1] == ["a_b-1.2", "x"]
    assert measured[2] == ["[x", "y"]
    assert measured[3] == []


# ---------------------------------------------------------------------------
# The inputs: measured by perturbation, compared with the declared sets
# ---------------------------------------------------------------------------


def test_the_acts_branch_reads_exactly_its_declared_inputs() -> None:
    census = w.input_census(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE)

    assert census["branch"] == w.BRANCH_ACTS
    assert census["state"]["measured"] == sorted(w.TEXT_INPUTS)
    assert census["state"]["declared_silent"] == []
    assert census["state"]["undeclared"] == []
    assert census["state"]["crashed"] == []
    assert census["signature"]["measured"] == [
        "document_classification",
        "provenance",
    ]
    assert census["signature"]["gate_keys"] == [
        "document_classification",
        "provenance",
    ]
    assert census["signature"]["undeclared"] == []
    assert census["passed_unread"] == ["opaque_id"]


def test_a_declared_gate_the_record_omits_is_inserted_not_read_as_silence() -> None:
    signature = {
        key: value
        for key, value in w.SYNTHETIC_SIGNATURE.items()
        if key != "document_classification"
    }

    census = w.input_census(w.SYNTHETIC_STATE, signature)

    scope = census["signature"]
    assert scope["absent_from_record"] == ["document_classification"]
    assert scope["inserted"] == ["document_classification"]
    assert scope["measured"] == ["document_classification", "provenance"]
    assert scope["gate_keys"] == ["document_classification", "provenance"]
    assert scope["declared_silent"] == []


def test_the_non_argumentative_branch_reads_exactly_its_declared_inputs() -> None:
    signature = {**_PIPELINE_SIGNATURE, "document_classification": "non_argumentative"}

    census = w.input_census(_NON_ARGUMENTATIVE_STATE, signature)

    assert census["branch"] == w.BRANCH_NON_ARGUMENTATIVE
    assert census["state"]["measured"] == [
        "interpretive_question",
        "raw_text",
        "source_metadata",
    ]
    assert census["state"]["declared_silent"] == []
    assert census["state"]["undeclared"] == []
    assert census["signature"]["measured"] == [
        "document_classification",
        "provenance",
    ]
    assert census["signature"]["undeclared"] == []


def test_a_cut_dump_reads_exactly_its_declared_inputs() -> None:
    signature = {**_PIPELINE_SIGNATURE, "outcome": {"status": "partial"}}

    census = w.input_census(_CUT_STATE, signature)

    assert census["branch"] == w.BRANCH_CUT
    assert census["state"]["measured"] == census["state"]["declared"]
    assert census["state"]["declared_silent"] == []
    assert census["state"]["undeclared"] == []
    assert census["state"]["absent_from_record"] == sorted(w.TEXT_INPUTS)
    # The acts gate the dump: inserted, each one flips the record to its branch.
    assert census["state"]["gate_keys"] == sorted(w.RENDER_INPUTS)
    assert census["signature"]["measured"] == [
        "document_classification",
        "outcome",
        "provenance",
    ]
    assert census["signature"]["undeclared"] == []


def test_a_field_another_field_gates_is_reported_silent_not_hidden() -> None:
    """The cut dump's intro reads ``outcome`` only under a ``partial`` status."""

    census = w.input_census(_CUT_STATE, _PIPELINE_SIGNATURE)

    assert census["branch"] == w.BRANCH_CUT
    assert census["signature"]["declared_silent"] == ["outcome"]
    assert census["signature"]["undeclared"] == []


def test_a_field_the_declaration_does_not_list_is_named_a_hidden_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def render(state: Any, signature: Any) -> str:
        return "x" + str(state.get("mystery"))

    monkeypatch.setattr(w, "judge_render", render)

    census = w.input_census({**w.SYNTHETIC_STATE, "mystery": "une valeur"}, {})

    assert census["state"]["undeclared"] == ["mystery"]
    assert census["state"]["measured"] == ["mystery"]


def test_a_number_read_as_a_threshold_is_still_seen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``+ 1`` never crosses a threshold read from above: zero is tried too."""

    def render(state: Any, signature: Any) -> str:
        return "x" + ("y" if (state.get("turns") or 0) > 0 else "")

    monkeypatch.setattr(w, "judge_render", render)

    census = w.input_census({**w.SYNTHETIC_STATE, "turns": 3}, {})

    assert census["state"]["undeclared"] == ["turns"]


@pytest.mark.parametrize(
    "value, perturbed",
    [
        ("un texte", ["un texte" + w.MARKER, ""]),
        ("", [w.MARKER]),
        ({"a": 1}, [{}, {w.MARKER_KEY: w.MARKER}]),
        ({}, [{w.MARKER_KEY: w.MARKER}]),
        ([1], [[], [w.MARKER]]),
        ([], [[w.MARKER]]),
        (True, [False]),
        (3, [4, 0]),
        (0, [1]),
        (2.5, [3.5, 0.0]),
        (None, [w.MARKER]),
    ],
)
def test_each_perturbation_keeps_the_value_s_type(
    value: Any, perturbed: List[Any]
) -> None:
    measured = w.perturbations(value)

    assert measured == perturbed
    assert [type(item) for item in measured] == [type(item) for item in perturbed]


def test_a_render_that_dies_on_a_perturbed_field_is_reported_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def render(state: Any, signature: Any) -> str:
        return str("x" * state["count"]["n"])

    monkeypatch.setattr(w, "judge_render", render)

    census = w.input_census({**w.SYNTHETIC_STATE, "count": {"n": 2}}, {})

    assert census["state"]["crashed"] == ["count"]
    assert census["state"]["undeclared"] == ["count"]


def test_the_conversation_engine_reads_no_undeclared_input() -> None:
    signature = _engine_signature(w.BRANCH_CONVERSATION_REAL)

    census = w.input_census(_CONVERSATION_STATE, signature)

    assert census["branch"] == w.BRANCH_CONVERSATION_REAL
    assert census["state"]["undeclared"] == []
    assert census["state"]["measured"] == [
        "analysis_errors",
        "fallacies",
        "fol",
    ]
    # The count is the record only when no fallacy is listed entry by entry.
    assert census["state"]["declared_silent"] == ["fallacies_count"]
    assert census["signature"]["measured"] == ["provenance"]
    assert census["signature"]["undeclared"] == []

    counted = w.input_census(
        {**_CONVERSATION_STATE, "fallacies": [], "fallacies_count": 3}, signature
    )
    assert counted["state"]["undeclared"] == []
    assert "fallacies_count" in counted["state"]["measured"]
    assert counted["state"]["declared_silent"] == ["fallacies"]


def test_the_delegation_engine_reads_no_undeclared_input() -> None:
    signature = _engine_signature(w.BRANCH_HIERARCHICAL_DELEGATION)

    census = w.input_census(_DELEGATION_STATE, signature)

    assert census["branch"] == w.BRANCH_HIERARCHICAL_DELEGATION
    assert census["state"]["undeclared"] == []
    assert census["state"]["declared_silent"] == ["partial"]
    assert census["signature"]["undeclared"] == []

    cut = w.input_census(
        {
            **_DELEGATION_STATE,
            "conclusion": "",
            "degraded": False,
            "degradation_reasons": [],
            "partial": True,
        },
        signature,
    )
    assert cut["state"]["undeclared"] == []
    assert "partial" in cut["state"]["measured"]
    assert cut["state"]["declared_silent"] == ["degradation_reasons", "degraded"]


# ---------------------------------------------------------------------------
# The signature's own record of the harvest
# ---------------------------------------------------------------------------


def test_the_recorded_lengths_agree_with_the_state_texts() -> None:
    state = _state()
    recorded = {
        key: {"length": len(state[key]), "stripped": True} for key in w.RENDER_INPUTS
    }
    recorded[w.QUESTION] = state[w.QUESTION]

    rows = w.recorded_lengths(state, {**w.SYNTHETIC_SIGNATURE, "state": recorded})

    assert [rows[key]["equal"] for key in w.TEXT_INPUTS] == [True] * 5
    assert {rows[key]["kind"] for key in w.RENDER_INPUTS} == {"length"}
    assert rows[w.QUESTION]["kind"] == "text"


def test_a_wrong_recorded_length_is_a_named_failure() -> None:
    state = _state()
    recorded = {
        key: {"length": len(state[key]), "stripped": True} for key in w.RENDER_INPUTS
    }
    recorded["act2_narrative"]["length"] += 1
    recorded[w.QUESTION] = state[w.QUESTION] + " "
    signature = {**w.SYNTHETIC_SIGNATURE, "state": recorded}

    rows = w.recorded_lengths(state, signature)

    assert rows["act1_framing"]["equal"] is True
    assert rows["act2_narrative"]["equal"] is False
    assert rows[w.QUESTION]["equal"] is False
    entry: Dict[str, Any] = {
        "branch": w.BRANCH_ACTS,
        "equal": {},
        "inputs": {
            "state": {"undeclared": [], "crashed": []},
            "signature": {"undeclared": [], "crashed": []},
        },
        "recorded_lengths": rows,
        "controls": {"ok": True},
    }
    assert w._failures(entry) == [
        "the signature recorded another act2_narrative",
        f"the signature recorded another {w.QUESTION}",
    ]


def test_a_signature_without_a_sanitised_state_records_nothing() -> None:
    rows = w.recorded_lengths(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE)

    assert {rows[key]["kind"] for key in w.TEXT_INPUTS} == {None}
    assert {rows[key]["equal"] for key in w.TEXT_INPUTS} == {None}
    assert (
        w._failures(
            {
                "branch": w.BRANCH_ACTS,
                "equal": {},
                "inputs": {
                    "state": {"undeclared": [], "crashed": []},
                    "signature": {"undeclared": [], "crashed": []},
                },
                "recorded_lengths": rows,
                "controls": {"ok": True},
            }
        )
        == []
    )


# ---------------------------------------------------------------------------
# The fiche: the section the witness extracts is the producer's own text
# ---------------------------------------------------------------------------


def _fiche(state: Dict[str, Any], signature: Dict[str, Any]) -> str:
    return render_fiche(
        doc_facts(dict(signature), dict(state)),
        state,
        None,
        "abc1234",
        "witness",
        "cmd",
    )


def test_the_fiche_section_the_witness_extracts_is_the_producer_s_own_text() -> None:
    signature = {**_PIPELINE_SIGNATURE, "metadata": {}}
    fiche = _fiche(w.SYNTHETIC_STATE, signature)

    assert w.FICHE_SECTION_START in fiche
    assert w.FICHE_SECTION_END in fiche
    extracted = w.fiche_full_text(fiche)

    assert extracted is not None
    assert extracted == w.judge_render(w.SYNTHETIC_STATE, signature)
    assert extracted == w.replay_render(w.SYNTHETIC_STATE, signature)


def test_a_fiche_without_the_two_headings_is_not_read_as_a_text() -> None:
    assert w.fiche_full_text("## Autre chose\n\ndu texte\n") is None
    assert w.fiche_full_text(w.FICHE_SECTION_START + "\n\ndu texte sans fin\n") is None


def test_the_fiche_caller_does_not_route_the_two_other_engines() -> None:
    """Measured on main: the reader's fiche and the judge's text diverge there.

    The judge's entry point routes ``provenance.mode`` to the engine's own
    producer; ``render_fiche`` calls ``pipeline_full_text``, which has no such
    routing. The witness must name that, never certify one text.
    """
    state = dict(_CONVERSATION_STATE)
    signature = _engine_signature(w.BRANCH_CONVERSATION_REAL)

    judged = w.judge_render(state, signature)
    extracted = w.fiche_full_text(_fiche(state, signature))

    assert "Sophismes relevés par l'agent informel" in judged
    assert extracted is not None
    assert extracted != judged
    assert "absent de l'état — acte i — cadrage non produit" in extracted

    entry = w.witness_document(state, signature)
    assert entry["equal"]["judge_vs_replay"] is True
    assert entry["equal"]["fiche_vs_replay"] is False
    assert w._failures(entry) == [w.FICHE_DOES_NOT_ROUTE]


def test_every_mismatch_the_witness_can_name() -> None:
    entry: Dict[str, Any] = {
        "branch": w.BRANCH_ACTS,
        "equal": {"judge_vs_replay": False, "harvested_vs_judge": False},
        "inputs": {
            "state": {"undeclared": ["mystery"], "crashed": ["count"]},
            "signature": {"undeclared": [], "crashed": []},
        },
        "recorded_lengths": {"act1_framing": {"equal": False}},
        "controls": {"ok": False},
    }

    assert w._failures(entry) == [
        "render mismatch (judge_vs_replay)",
        "render mismatch (harvested_vs_judge)",
        "hidden input (state.mystery)",
        "render died on the perturbed state.count",
        "the signature recorded another act1_framing",
        "branch control did not fire",
    ]


# ---------------------------------------------------------------------------
# The controls on a record of each branch
# ---------------------------------------------------------------------------


def test_the_branch_control_names_the_input_a_record_s_branch_reads() -> None:
    acts = w.branch_controls(
        w.SYNTHETIC_STATE,
        w.SYNTHETIC_SIGNATURE,
        w.judge_render(w.SYNTHETIC_STATE, w.SYNTHETIC_SIGNATURE),
    )
    assert acts["ok"] is True
    assert acts["branch_control"]["input"] == "act1_framing"
    assert acts["branch_control"]["equal"] is False
    assert acts["per_act"]["act2_narrative"]["sections_differing"] == [
        "Acte II — récit"
    ]

    non_argumentative_signature = {
        **_PIPELINE_SIGNATURE,
        "document_classification": "non_argumentative",
    }
    classified = w.branch_controls(
        _NON_ARGUMENTATIVE_STATE,
        non_argumentative_signature,
        w.judge_render(_NON_ARGUMENTATIVE_STATE, non_argumentative_signature),
    )
    assert classified["ok"] is True
    assert classified["branch_control"]["input"] == "source_metadata"
    # An act injected into a non-argumentative document moves nothing: that is
    # the branch, not a hole in the comparison.
    assert all(act["equal"] is True for act in classified["per_act"].values())

    cut_signature = {**_PIPELINE_SIGNATURE, "outcome": {"status": "partial"}}
    cut = w.branch_controls(
        _CUT_STATE,
        cut_signature,
        w.judge_render(_CUT_STATE, cut_signature),
    )
    assert cut["ok"] is True
    assert cut["branch_control"]["input"] == "act1_framing"

    for mode in (w.BRANCH_CONVERSATION_REAL, w.BRANCH_HIERARCHICAL_DELEGATION):
        engine = w.branch_controls(_CONVERSATION_STATE, _engine_signature(mode), "x")
        assert engine["ok"] is True
        assert engine["branch_control"]["skipped"] is True


# ---------------------------------------------------------------------------
# The report on a synthetic cycle, the fresh process, the refusal
# ---------------------------------------------------------------------------


def test_main_holds_on_a_synthetic_cycle(tmp_path: Path) -> None:
    cycle = _write_cycle(tmp_path, {"synth_one": _state()})
    panel = tmp_path / "panel.txt"
    panel.write_text("# un commentaire\nsynth_one  # un autre\n", encoding="utf-8")
    out = tmp_path / "report.json"

    assert (
        w.main(
            ["--cycle-dir", str(cycle), "--panel-file", str(panel), "--out", str(out)]
        )
        == 0
    )

    report = json.loads(out.read_text(encoding="utf-8"))
    assert list(report["documents"]) == ["doc_A"]
    assert report["synthetic"]["ok"] is True
    document = report["documents"]["doc_A"]
    assert document["failures"] == []
    assert document["equal"]["judge_vs_replay"] is True
    assert document["equal"]["fiche_vs_replay"] is True
    assert document["equal"]["harvested_vs_judge"] is None
    assert document["controls"]["ok"] is True
    assert document["inputs"]["state"]["undeclared"] == []
    fresh = report["fresh_process"]
    assert fresh["same"] == {"doc_A": True}
    assert fresh["added_from_dotenv"] == []
    assert fresh["tamper_control"]["differs"] is True
    assert fresh["tamper_control"]["others_unchanged"] is True
    # The panel's ids never reach the report: labels only.
    assert "synth_one" not in out.read_text(encoding="utf-8")
    if w.dotenv_names():
        # A seat that holds a root .env: without the stub the child's import
        # fills its names, so "read no .env" is a measurement, not a silence.
        assert fresh["stub_control"]["names_filled_without_the_stub"]
    else:
        assert "stub_control" not in fresh


def test_the_report_opens_with_its_provenance_header(tmp_path: Path) -> None:
    """#2353: a cited report says which code, which route, which command."""
    cycle = _write_cycle(tmp_path, {"synth_one": _state()})
    panel = tmp_path / "panel.txt"
    panel.write_text("synth_one\n", encoding="utf-8")
    out = tmp_path / "report.json"

    argv = ["--cycle-dir", str(cycle), "--panel-file", str(panel), "--out", str(out)]
    assert w.main(argv) == 0

    report = json.loads(out.read_text(encoding="utf-8"))
    assert list(report)[0] == "provenance"
    header = report["provenance"]
    # The command as it was typed, to be run again from the checkout's root.
    assert header["command"] == [
        "python",
        "scripts/panel/act_replay_fidelity.py",
        *argv,
    ]
    assert header["route"] == {
        "cycle_dir": str(cycle.resolve()),
        "renders_dir": None,
        "panel_file": str(panel.resolve()),
        "labels": "panel order",
    }
    assert header["llm_requests"] == 0
    assert header["python"] == sys.version.split()[0]
    code = header["code"]
    assert (
        code["instrument_sha256"]
        == hashlib.sha256(Path(w.__file__).read_bytes()).hexdigest()
    )
    # A seat with git names the commit; the instrument never invents one.
    assert code["head"] is None or re.fullmatch(r"[0-9a-f]{40}", code["head"])


@pytest.mark.parametrize(
    "status, dirty",
    [("", False), (" M scripts/panel/act_replay_fidelity.py", True)],
)
def test_the_header_says_whether_the_tree_carries_uncommitted_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: str, dirty: bool
) -> None:
    seen: List[Tuple[str, ...]] = []

    def fake(root: Path, *args: str) -> str:
        seen.append(args)
        return "1" * 40 if args == ("rev-parse", "HEAD") else status

    monkeypatch.setattr(w, "_git", fake)
    header = w.provenance(
        ["--cycle-dir", "cycle"], tmp_path / "cycle", None, None, False
    )
    assert ("status", "--porcelain") in seen
    assert header["code"]["head"] == "1" * 40
    assert header["code"]["dirty"] is dirty
    assert header["route"]["labels"] == "opaque ids"


def test_a_seat_where_git_is_missing_says_the_code_is_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(w, "_git", lambda root, *args: None)
    header = w.provenance([], tmp_path, None, None, False)
    assert header["code"]["head"] is None
    assert header["code"]["dirty"] is None


def test_a_digest_another_seat_would_compute_fails_the_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cycle = _write_cycle(tmp_path, {"synth_one": _state()})
    real_digests = w.fresh_process_digests

    def another_seat(cycle_dir: Path, labels: Any, **kwargs: Any) -> Dict[str, Any]:
        child = real_digests(cycle_dir, labels, **kwargs)
        child["digests"]["synth_one"] = "0" * 64
        return child

    monkeypatch.setattr(w, "fresh_process_digests", another_seat)

    assert w.main(["--cycle-dir", str(cycle)]) == 1


def test_a_wrong_recorded_length_fails_the_cycle(tmp_path: Path) -> None:
    cycle = _write_cycle(tmp_path, {"synth_one": _state()})
    signature_path = cycle / "signatures" / "signature_synth_one.json"
    signature = json.loads(signature_path.read_text(encoding="utf-8"))
    signature["state"]["act1_framing"]["length"] += 1
    signature_path.write_text(json.dumps(signature), encoding="utf-8")

    assert w.main(["--cycle-dir", str(cycle), "--no-fresh-process"]) == 1


def test_main_reddens_on_a_tampered_fiche_and_names_the_document(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cycle = _write_cycle(tmp_path, {"synth_one": _state()})
    renders = tmp_path / "renders"
    renders.mkdir()
    fiche = renders / "00_synth_one_un-titre.md"
    state = _state()
    signature = json.loads(
        (cycle / "signatures" / "signature_synth_one.json").read_text(encoding="utf-8")
    )
    genuine = _fiche(state, signature)
    fiche.write_text(genuine, encoding="utf-8")
    argv = [
        "--cycle-dir",
        str(cycle),
        "--renders-dir",
        str(renders),
        "--no-fresh-process",
    ]

    assert w.main(argv) == 0
    assert (
        "the harvested fiches are reproduced byte for byte" in capsys.readouterr().out
    )

    fiche.write_text(
        genuine.replace("Acte II synthétique", "Acte ll synthétique"),
        encoding="utf-8",
    )
    out = tmp_path / "report.json"

    assert w.main([*argv, "--out", str(out)]) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    document = report["documents"]["synth_one"]
    assert document["reference"]["source"] == "harvested-fiche"
    assert document["equal"]["harvested_vs_judge"] is False
    assert document["equal"]["harvested_vs_replay"] is False
    assert document["diff"]["harvested_vs_judge"]["sections_differing"] == [
        "Acte II — récit"
    ]
    assert document["failures"] == [
        "render mismatch (harvested_vs_judge)",
        "render mismatch (harvested_vs_replay)",
    ]
    assert "VERDICT: MISMATCH" in capsys.readouterr().out


def test_a_fiche_no_instrument_can_read_is_a_failure_not_a_pass(
    tmp_path: Path,
) -> None:
    cycle = _write_cycle(tmp_path, {"synth_one": _state()})
    renders = tmp_path / "renders"
    renders.mkdir()
    (renders / "00_synth_one_un-titre.md").write_text(
        "pas une fiche\n", encoding="utf-8"
    )

    assert (
        w.main(
            [
                "--cycle-dir",
                str(cycle),
                "--renders-dir",
                str(renders),
                "--no-fresh-process",
            ]
        )
        == 1
    )


def test_main_refuses_an_output_git_would_track(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cycle = _write_cycle(tmp_path, {"synth_one": _state()})
    tracked = c.REPO_ROOT / "witness_output_not_gitignored.json"

    assert not tracked.exists()
    assert (
        w.main(["--cycle-dir", str(cycle), "--out", str(tracked), "--no-fresh-process"])
        == 2
    )

    assert "refused" in capsys.readouterr().out
    assert not tracked.exists()


def test_main_says_so_when_there_is_nothing_to_witness(tmp_path: Path) -> None:
    assert w.main(["--cycle-dir", str(tmp_path / "absent")]) == 2


def test_the_child_starts_with_the_boot_variables_only() -> None:
    env = w.child_env()

    assert set(env) - {"PYTHONPATH", "PYTHONUTF8", "PYTHONIOENCODING"} <= set(
        w._BOOT_ENV_KEYS
    )
    assert env["PYTHONPATH"] == str(c.REPO_ROOT)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "TEXT_CONFIG_PASSPHRASE"):
        assert name not in env
    assert "PYTHONHASHSEED" not in env
