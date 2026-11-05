"""#3394 cycle 2 — four reader-surface repairs, one witness class per item.

The coordinator's cycle-2 census measured four classes on the panel renders:

(a) the vote was invoked without its methods being named — 7 renders said
    « à l'unanimité des méthodes » with no method named;
(b) the reading record's ORGAN labels (« large filet », « descente »,
    « repli en un appel ») — code vocabulary copied onto the reader surface;
(c) Dung annex anchors with no annex (« Annexe Dung[...] » cited, no annex
    in the full text), and one proposition sent to [preferred] in Act II and
    [multi] in Act III with the difference never said;
(d) the coverage section printed up to three times in one full text.

Each witness below fails on main for its own reason: a kwarg the function
does not take (a), labels the table did not carry (b), anchors the text kept
(c), repeats the assembly let through (d).

Offline: synthetic states, opaque ids, no corpus, no key, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.cited_units import (
    qualitative_support_band,
    render_divergence_clause,
    render_governance_lead,
)
from argumentation_analysis.reporting.restitution.reading_record import (
    SITE_LABELS_FR,
    ReadingLine,
    ReadingRecord,
    _fallacy_fed,
    format_reading_block,
)

_NINE = [
    "majority",
    "plurality",
    "borda",
    "condorcet",
    "quadratic",
    "approval",
    "stv",
    "copeland",
    "schulze",
]
_NINE_FR = (
    "majorité, pluralité, Borda, Condorcet, vote quadratique, "
    "vote par approbation, vote unique transférable, Copeland, Schulze"
)
_ALL_TWELVE_FR = _NINE_FR + ", vainqueur de Condorcet, consensus byzantin, Raft"


# ---------------------------------------------------------------------------
# Item (a) — the vote names its methods
# ---------------------------------------------------------------------------


class TestTheVoteNamesItsMethods:
    def test_the_band_carries_the_methods_beside_their_count(self):
        band = qualitative_support_band(9, 12, None, supporting_methods=_NINE)
        assert band == (
            f"par une large majorité des méthodes (9 des 12 méthodes : {_NINE_FR})"
        )

    def test_unanimity_names_every_method(self):
        twelve = _NINE + ["condorcet_winner", "byzantine", "raft"]
        band = qualitative_support_band(12, 12, None, supporting_methods=twelve)
        assert band == (
            "à l'unanimité des méthodes qui ont décidé "
            f"(12 des 12 méthodes : {_ALL_TWELVE_FR})"
        )

    def test_an_unknown_method_prints_as_itself_never_dropped(self):
        band = qualitative_support_band(
            2, 12, None, supporting_methods=["majority", "landauer"]
        )
        assert band == (
            "par une partie seulement des méthodes (2 des 12 méthodes : majorité, landauer)"
        )

    def test_names_that_disagree_with_the_count_stay_home(self):
        # The count is the measured half; a name list of another length
        # describes a different vote — printing both would be false.
        band = qualitative_support_band(
            9, 12, None, supporting_methods=["majority", "borda"]
        )
        assert band == "par une large majorité des méthodes (9 des 12 méthodes)"

    def test_a_band_without_names_is_unchanged(self):
        # Honest absence: a pre-cycle-2 record keeps its count-only band,
        # byte-identical.
        assert (
            qualitative_support_band(9, 12, None)
            == "par une large majorité des méthodes (9 des 12 méthodes)"
        )

    def test_the_lead_names_the_methods_of_the_verdict(self):
        _warning, lead = render_governance_lead(
            "majority",
            "arg_1",
            "le texte dit ceci",
            "vote_aggregate",
            support_by_option={"arg_1": 9},
            methods_by_option={"arg_1": _NINE},
            n_methods_decided=12,
        )
        assert f"(9 des 12 méthodes : {_NINE_FR})" in lead

    def test_each_divergent_winner_carries_its_own_methods(self):
        clause = render_divergence_clause(
            [("arg_2", "le texte dit cela"), ("arg_3", "le texte dit ceci")],
            support_by_option={"arg_2": 5, "arg_3": 4},
            methods_by_option={
                "arg_2": ["borda", "schulze", "copeland", "approval", "stv"],
                "arg_3": ["majority", "plurality", "quadratic", "condorcet"],
            },
            n_methods_decided=12,
        )
        assert (
            "(5 des 12 méthodes : Borda, Schulze, Copeland, vote par approbation, "
            "vote unique transférable)" in clause
        )
        assert (
            "(4 des 12 méthodes : majorité, pluralité, vote quadratique, Condorcet)"
            in clause
        )

    def test_the_state_entry_persists_the_names_and_only_then(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("texte")
        state.add_governance_decision(
            method="majority",
            winner="arg_1",
            scores={},
            winner_provenance="vote_aggregate",
            support_by_option={"arg_1": 9},
            methods_by_option={"arg_1": _NINE},
            n_methods_decided=12,
        )
        entry = state.governance_decisions[0]
        assert entry["methods_by_option"] == {"arg_1": _NINE}
        # Honest absence: a caller that passes none stores no empty key.
        state2 = UnifiedAnalysisState("texte")
        state2.add_governance_decision(
            method="majority", winner="arg_1", scores={}, n_methods_decided=12
        )
        assert "methods_by_option" not in state2.governance_decisions[0]

    def test_the_names_reach_the_acts_prompts(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            build_act3_evidence,
            build_act3_prompt,
        )

        state = SimpleNamespace(
            governance_decisions=[
                {
                    "id": "gov_1",
                    "method": "majority",
                    "winner": "arg_1",
                    "scores": {},
                    "winner_provenance": "vote_aggregate",
                    "support_by_option": {"arg_1": 9},
                    "methods_by_option": {"arg_1": _NINE},
                    "n_methods_decided": 12,
                }
            ]
        )
        assert f"(9 des 12 méthodes : {_NINE_FR})" in build_act2_prompt(
            build_act2_evidence(state)
        )
        assert f"(9 des 12 méthodes : {_NINE_FR})" in build_act3_prompt(
            build_act3_evidence(state)
        )


# ---------------------------------------------------------------------------
# Item (b) — the organ labels speak to the reader
# ---------------------------------------------------------------------------


class TestOrganLabelsSpeakToTheReader:
    def test_the_three_organ_labels_carry_reader_words(self):
        assert (
            SITE_LABELS_FR["fallacy_widenet"]
            == "détection de sophismes — premier balayage du texte entier"
        )
        assert (
            SITE_LABELS_FR["fallacy_descent"]
            == "détection de sophismes — examen approfondi par fenêtres"
        )
        assert (
            SITE_LABELS_FR["fallacy_one_shot"]
            == "détection de sophismes — lecture en un seul appel"
        )

    def test_no_organ_name_survives_in_the_label_table(self):
        for value in SITE_LABELS_FR.values():
            assert "filet" not in value
            assert "descente" not in value
            assert "repli" not in value

    def test_the_reading_block_names_what_each_pass_did(self):
        record = ReadingRecord(
            lines=[
                ReadingLine(site="fallacy_widenet", status="selected", window=8000),
                ReadingLine(site="fallacy_descent", status="selected", window=500),
                ReadingLine(site="fallacy_one_shot", status="selected", window=8000),
            ],
            source_chars=12000,
        )
        block = format_reading_block(record)
        assert "premier balayage du texte entier" in block
        assert "examen approfondi par fenêtres" in block
        assert "lecture en un seul appel" in block
        assert "filet" not in block and "descente" not in block and "repli" not in block

    def test_the_fed_phrases_speak_the_same_vocabulary(self):
        state = SimpleNamespace(
            identified_fallacies={
                "f1": {"detection_paths": ["one_shot", "fallacy_per_argument"]},
                "f2": {"detection_paths": ["fallacy_per_argument"]},
                "f3": {"detection_paths": ["fallacy_descent"]},
            }
        )
        one_shot = _fallacy_fed("fallacy_one_shot", state)
        assert "lecture en un seul appel" in one_shot
        assert "repli" not in one_shot
        per_arg = _fallacy_fed("fallacy_per_argument", state)
        # The shared clause names the other reading in the same words.
        assert "l'examen approfondi par fenêtres" in per_arg
        assert "la descente" not in per_arg

    def test_the_act2_weaving_bullet_drops_the_organ_word(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )

        prompt = build_act2_prompt(build_act2_evidence(SimpleNamespace()))
        assert "procédé + examen approfondi + contre-argument" in prompt
        assert "procédé + descente" not in prompt


# ---------------------------------------------------------------------------
# Item (c) — a Dung ref cites an annex that prints
# ---------------------------------------------------------------------------


def _fw(name: str, extensions=None) -> dict:
    return {
        "name": name,
        "arguments": ["arg_1", "arg_2"],
        "attacks": [["arg_1", "arg_2"]],
        "extensions": (
            extensions if extensions is not None else {"all_members": ["arg_1"]}
        ),
    }


class TestTheDungRefCitesAPrintedAnnex:
    def test_citable_refs_mirror_the_appendix_derivation(self):
        from argumentation_analysis.reporting.restitution.dung_reader import (
            citable_appendix_refs,
        )

        state = SimpleNamespace(
            dung_frameworks={
                "d1": _fw("verification_preferred"),
                "d2": _fw("verification_multi"),
                "d3": _fw("aba_theory"),  # a sidecar: never native Dung
                "d4": _fw("verification_unavailable", extensions=None),
            }
        )
        assert citable_appendix_refs(state) == {
            "Annexe Dung[preferred]",
            "Annexe Dung[multi]",
        }
        # The renderer's appendix state is a plain mapping — same answer.
        assert citable_appendix_refs(
            {"dung_frameworks": {"d1": _fw("verification_preferred")}}
        ) == {"Annexe Dung[preferred]"}

    def test_a_citable_text_is_demoted_nowhere(self):
        from argumentation_analysis.reporting.restitution.dung_reader import (
            demote_uncitable_dung_refs,
        )

        text = (
            "Annexe Dung[preferred] — composition exacte de l'extension ; "
            "gloss. Annexe Dung[multi] — autre mention."
        )
        assert (
            demote_uncitable_dung_refs(
                text, {"Annexe Dung[preferred]", "Annexe Dung[multi]"}
            )
            == text
        )

    def test_an_anchor_without_target_states_its_result_in_place(self):
        from argumentation_analysis.reporting.restitution.dung_reader import (
            demote_uncitable_dung_refs,
        )

        text = (
            "machinerie complète et protocole : Annexe Dung[grounded] ; "
            "réserve épistémique. Autre ligne : Annexe Dung[grounded] — gloss."
        )
        out = demote_uncitable_dung_refs(text, set())
        assert "Annexe Dung[" not in out
        assert "protocole : annexe non imprimée ;" in out
        assert "Autre ligne : gloss." in out

    def test_the_render_pass_gates_on_the_mapping_actually_rendered(self):
        # The measured class: acts built from the raw state cite refs, the
        # renderer's mapping carries no frameworks — the anchors dangle in
        # the full text. The assembly pass gates on the mapping actually
        # rendered (wiring witness: the demotion runs inside the render,
        # on the appendix mapping — constructible divergence through this
        # entry point is impossible by design, hence the source check).
        import inspect

        from argumentation_analysis.reporting.restitution import pipeline_adapter

        src = inspect.getsource(pipeline_adapter.render_spectacular_restitution)
        assert "demote_uncitable_dung_refs" in src
        assert "citable_appendix_refs(appendix_state)" in src

    def test_act3_names_the_semantics_divergence_with_act2(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _collect_weak_points,
        )

        points = _collect_weak_points(
            {},
            {"arg_2": "multi"},
            0,
            0,
            None,
            None,
            citable_refs={"Annexe Dung[multi]"},
            primary_semantics="preferred",
        )
        assert len(points) == 1
        assert points[0].detail.startswith("Annexe Dung[multi] — ")
        assert (
            "le verdict principal (Acte II) est énoncé sous la sémantique "
            "preferred" in points[0].detail
        )

    def test_act3_adds_no_note_when_the_semantics_agree(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _collect_weak_points,
        )
        from argumentation_analysis.reporting.restitution.dung_reader import (
            REJECTED_MEANS,
        )

        points = _collect_weak_points(
            {},
            {"arg_2": "preferred"},
            0,
            0,
            None,
            None,
            citable_refs={"Annexe Dung[preferred]"},
            primary_semantics="preferred",
        )
        # Same semantics, citable ref: the line is exactly the pre-cycle-2
        # one — the note is earned by a divergence, never unconditional.
        assert points[0].detail == f"Annexe Dung[preferred] — {REJECTED_MEANS}"

    def test_act3_states_the_result_in_place_when_the_ref_is_uncitable(self):
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            _collect_weak_points,
        )

        points = _collect_weak_points(
            {}, {"arg_2": "multi"}, 0, 0, None, None, citable_refs=set()
        )
        assert "conséquence énoncée en place" in points[0].detail
        assert "Annexe Dung[" not in points[0].detail


# ---------------------------------------------------------------------------
# Item (d) — the coverage section prints once
# ---------------------------------------------------------------------------

_H = "**Couverture de l'analyse (chiffres du pipeline)**"


class TestTheCoverageBlockPrintsOnce:
    def test_copies_in_later_acts_are_stripped(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            dedupe_coverage_passage_across_acts,
        )

        a1 = f"prose un.\n\n{_H}\nde 6 à 10 arguments."
        a2 = f"prose deux.\n\n{_H}\ncopie tronquée"
        a3 = f"prose trois.\n\n{_H}\nautre copie"
        out1, out2, out3 = dedupe_coverage_passage_across_acts(a1, a2, a3)
        assert _H in out1 and "de 6 à 10 arguments." in out1
        assert _H not in out2 and "prose deux." in out2
        assert _H not in out3 and "prose trois." in out3

    def test_without_act1_the_first_block_across_ii_iii_stays(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            dedupe_coverage_passage_across_acts,
        )

        a2 = f"prose deux.\n\n{_H}\npremière.\n\n{_H}\nseconde."
        a3 = f"prose trois.\n\n{_H}\ncopie"
        out1, out2, out3 = dedupe_coverage_passage_across_acts("", a2, a3)
        assert out1 == ""
        assert out2.count(_H) == 1 and "première." in out2
        assert _H not in out3

    def test_the_assembly_prints_the_section_once_in_the_full_text(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            COVERAGE_HEADING,
        )
        from argumentation_analysis.reporting.restitution.pipeline_adapter import (
            build_restitution_acts,
        )

        state = SimpleNamespace(
            act1_framing=f"récit.\n\n{_H}\nde 6 à 15 arguments.",
            act2_narrative=f"récit.\n\n{_H}\ncopie de l'acte deux",
            act3_conclusion=f"récit.\n\n{_H}\ncopie de l'acte trois",
        )
        acts = build_restitution_acts(state)
        joined = "\n".join(
            [acts.act1_framing, acts.act2_narrative, acts.act3_conclusion]
        )
        assert joined.count(COVERAGE_HEADING) == 1
        assert COVERAGE_HEADING in acts.act1_framing

    def test_a_text_without_the_section_is_untouched(self):
        from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
            dedupe_coverage_passage_across_acts,
        )

        a2 = "prose deux, sans section."
        out1, out2, out3 = dedupe_coverage_passage_across_acts("", a2, "")
        assert (out1, out2, out3) == ("", a2, "")
