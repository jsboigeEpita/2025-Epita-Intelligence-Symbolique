# -*- coding: utf-8 -*-
"""#3311 — Act I handed the writer raw metadata keys, and the renders printed
them.

R1127c (``doc_A``, main ``b5f515b86``): « (era : unknown, year_bucket :
unknown) » and « Le genre du discours (discourse_type) ». Measured on the 90
stored states: 18/90 carry such a token in an act, ALL in Act I, every hit
except ``nl_to_logic`` a metadata key — ``discourse_type`` 11,
``regime_type`` 8, ``year_bucket`` 7, ``source_metadata`` 6 (the block's own
header carried the field name). The writers' instructions forbade exactly
that (« ne recopie JAMAIS un identifiant technique brut »), and no rule read
the acts for it (#3159: a rule the writer can break is not one).

The repair, both halves:

* **source** — the metadata blocks (Act I's and Act III's mirror) present
  reader labels (« type de discours », « régime », « époque », « tranche
  d'années »), humanise unmapped keys, render a placeholder value as
  « non renseigné » (never the raw English ``unknown``), and the header
  names its provenance without the field name. The #3073
  recorded-vs-inferred distinction stays — only the field names leave the
  writer's view.
* **output** — a readability rule counts snake_case field tokens in the
  acts (anchors and « … » quotations excluded — their keys are data; raw
  internal ids stay the #2980 rule's own class), with a motive, never a
  rewrite.

Born red on ``b5f515b86``: the prompt witnesses fail on the raw keys, the
English placeholder and the header's field name; the gate witnesses fail
because no rule read snake_case. The positive controls (a recorded value
still reaches the prompt; the same text without the key stays PASS) pass on
both sides. Synthetic keys and values, opaque ids, no corpus text. No JVM,
no LLM call.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.acts import RestitutionActs
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)

#: The measured vocabulary, synthetic values: two placeholder fields, one
#: recorded value (the DoD's positive control), one unmapped key.
_META = {
    "discourse_type": "unknown",
    "year_bucket": "unknown",
    "era": "era_A",
    "source_channel": "radio",
}


def _state() -> SimpleNamespace:
    return SimpleNamespace(
        source_metadata=dict(_META),
        stakes_and_stakeholders={},
        identified_arguments={},
        deanonymized=True,
    )


# -- DoD 1 — what the Act I writer receives ----------------------------------


class TestTheAct1WriterSeesLabels:
    def test_no_metadata_key_reaches_the_prompt(self):
        """Born red: the four measured keys (and the header's field name)
        all reached the prompt before the repair."""
        prompt = build_act1_prompt(build_act1_evidence(_state()))
        for key in (
            "discourse_type",
            "year_bucket",
            "source_channel",
            "source_metadata",
        ):
            assert key not in prompt, key

    def test_reader_labels_carry_the_fields(self):
        prompt = build_act1_prompt(build_act1_evidence(_state()))
        for label in ("type de discours", "tranche d'années", "époque"):
            assert label in prompt, label

    def test_a_placeholder_reads_non_renseigne_never_unknown(self):
        prompt = build_act1_prompt(build_act1_evidence(_state()))
        assert "non renseigné" in prompt
        assert "unknown" not in prompt

    def test_an_unmapped_key_is_humanised(self):
        """No key shape can reach a prompt, including keys the label map
        does not know: underscores become spaces."""
        prompt = build_act1_prompt(build_act1_evidence(_state()))
        assert "source channel" in prompt

    def test_a_recorded_value_still_reaches_the_prompt(self):
        """DoD positive control, green on both sides: a recorded value is
        labelled as recorded — the #3073 distinction survives the repair."""
        prompt = build_act1_prompt(build_act1_evidence(_state()))
        assert "era_A" in prompt
        assert "[LE TEXTE — métadonnées enregistrées]" in prompt


# -- the Act III mirror (same input defect, same repair) ----------------------


class TestTheAct3MirrorCarriesTheSameLabels:
    def test_no_metadata_key_reaches_the_act3_prompt(self):
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        for key in (
            "discourse_type",
            "year_bucket",
            "source_channel",
            "source_metadata",
        ):
            assert key not in prompt, key

    def test_act3_renders_the_placeholder_and_the_recorded_value(self):
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        assert "non renseigné" in prompt
        assert "era_A" in prompt


# -- DoD 2 — the readability rule ---------------------------------------------


class TestTheGateReadsSnakeCase:
    def test_a_synthetic_act1_carrying_year_bucket_warns(self):
        """Born red: on ``b5f515b86`` this body passed — no rule read
        snake_case in the acts."""
        body = (
            "Le texte s'ouvre sur une archive située (year_bucket : 1930) "
            "et nomme son locuteur avant l'analyse."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band != "PASS"
        assert "#3311" in " ".join(verdict.reasons)
        assert "year_bucket" in " ".join(verdict.reasons)

    def test_the_same_text_without_the_key_passes(self):
        """DoD control, green on both sides."""
        body = (
            "Le texte s'ouvre sur une archive située dans les années 1930 "
            "et nomme son locuteur avant l'analyse."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "PASS"
        assert verdict.reasons == []

    def test_three_keys_fail_the_band(self):
        """WARN at 1–2, FAIL at ≥3 — the #2980/#2031 threshold band: a
        field-name takeover is a jargon takeover."""
        body = (
            "Le cadre cite discourse_type, regime_type puis year_bucket "
            "avant toute lecture."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "FAIL"

    def test_anchors_and_quotations_do_not_count(self):
        """The citation channel's keys are data, and a quoted token is the
        corpus's own word: neither is the writer printing a field name."""
        body = (
            "L'analyse cite ses unités [artifact:identified_arguments.arg_1] "
            "et rappelle « year_bucket » tel qu'écrit ailleurs."
        )
        verdict = ReadabilityGate().check_body(body)
        assert "#3311" not in " ".join(verdict.reasons)

    def test_raw_internal_ids_stay_the_2980_rule_s_own_class(self):
        """``arg_6`` is snake_case-shaped but it is a printed id — the
        #2980 rule owns it; one token never raises two reasons."""
        body = "Le fil avance masqué : l'argument arg_6 détourne l'examen."
        verdict = ReadabilityGate().check_body(body)
        assert "#3311" not in " ".join(verdict.reasons)
        assert "#2980" in " ".join(verdict.reasons)

    def test_the_reason_names_which_act_printed_the_key(self):
        acts = RestitutionActs(
            act1_framing="Le cadre du débat, avec year_bucket en prose.",
            act2_narrative="Le fil du texte, sans clé.",
            act3_conclusion="La conclusion, sans clé.",
        )
        verdict = ReadabilityGate().check_acts(acts)
        assert verdict.band != "PASS"
        assert any("Acte I" in r and "#3311" in r for r in verdict.reasons)


# -- DoD 3 — the provenance paths (found by the 49-state offline replay) ------


class TestTheProvenancePathsStayInternal:
    """The replay found two raw shapes the census had already counted under
    ``source_metadata``: the speaker/arena provenance lines printed the dotted
    path « … — source_metadata.speaker », and the spectrum note printed
    « source : source_metadata.genre ». The #3073 class stays (enregistrée vs
    inférée); the internal path leaves the writer's view."""

    def _recorded_state(self) -> SimpleNamespace:
        return SimpleNamespace(
            source_metadata={
                "speaker": "speaker_A",
                "venue": "arena_B",
                # a taxonomy context, so the DÉRIVÉ spectrum branch prints
                "genre": "politique",
            },
            stakes_and_stakeholders={},
            identified_arguments={},
            deanonymized=True,
        )

    def test_the_speaker_line_keeps_the_class_not_the_path(self):
        prompt = build_act1_prompt(build_act1_evidence(self._recorded_state()))
        assert "Locuteur : speaker_A (provenance : métadonnée enregistrée)" in prompt
        assert "source_metadata.speaker" not in prompt

    def test_the_arena_line_keeps_the_class_not_the_path(self):
        prompt = build_act1_prompt(build_act1_evidence(self._recorded_state()))
        assert (
            "Arène discursive : arena_B (provenance : métadonnée enregistrée)" in prompt
        )
        assert "source_metadata.venue" not in prompt

    def test_the_spectrum_note_names_the_class_not_the_field(self):
        # No venue: an arena value would override the genre in _derive_genre
        # and the DÉRIVÉ branch would not print.
        state = SimpleNamespace(
            source_metadata={"speaker": "speaker_A", "genre": "politique"},
            stakes_and_stakeholders={},
            identified_arguments={},
            deanonymized=True,
        )
        prompt = build_act1_prompt(build_act1_evidence(state))
        assert "source : métadonnée enregistrée" in prompt
        assert "source_metadata." not in prompt

    def test_the_inferred_speaker_line_carries_no_dotted_path_either(self):
        state = SimpleNamespace(
            source_metadata={},
            stakes_and_stakeholders={
                "stakeholders": [
                    {"name": "speaker_D", "role": "speaker", "stance": "pour"}
                ],
            },
            identified_arguments={},
            deanonymized=True,
        )
        prompt = build_act1_prompt(build_act1_evidence(state))
        assert "INFÉRÉE du texte" in prompt
        assert "stakes_and_stakeholders" not in prompt

    def test_no_dotted_metadata_path_reaches_any_prompt(self):
        """The replay's class-level assertion, held as a witness: the dotted
        prefix never appears in either act, whatever the key behind it."""
        for build_ev, build_pr in (
            (build_act1_evidence, build_act1_prompt),
            (build_act3_evidence, build_act3_prompt),
        ):
            prompt = build_pr(build_ev(self._recorded_state()))
            assert "source_metadata." not in prompt

    def test_english_field_names_read_as_french_labels(self):
        """The 49-state key population: ``speaker``/``venue``/``title`` are
        English keys — the same defect one keystroke later; they now read as
        labels (« genre »/« date » are already French and stay as-is)."""
        prompt = build_act1_prompt(build_act1_evidence(self._recorded_state()))
        assert "- locuteur : speaker_A" in prompt
        assert "- lieu : arena_B" in prompt
        assert "- genre : politique" in prompt
