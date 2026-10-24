# -*- coding: utf-8 -*-
"""#3215 — `counter_on_wrong_unit` must bind on a real join, not on generic words.

#3202 made `_index_units` read the str shape real states store, so the #3151
weave checks read real units for the first time. On the R1109 doc_A render
`counter_on_wrong_unit` raised **32 flags, none of them a counter placed on
the wrong unit**: the render's units are stored in the source language while
the prose is French, so 80 of 87 units can never be "present" and every cited
counter flags; and "cited" meant two shared tokens, generic French words
included (« contre », « deux », « quand », « après », « faire », « mieux »,
« puis »).

Measured here (0 LLM, six stored renders): 22 flags, **0** with any
distinctive token of the target unit in the paragraph. The flags never reach
the reader — they are logged as warnings and stored in
`value_gates["read_license"]` — but a review that reads them sees binding
defects that are not there.

Two sound bars replace the token overlap:

* a counter is **CITED** when the paragraph carries at least two of its
  distinctive tokens AND at least a third of them (something only that
  counter carries, not a generic word);
* a unit is **BOUND** in a paragraph on at least two of its distinctive
  tokens — a single shared word places nothing.

A flag then means: a counter whose content the render carries sits in a
paragraph that clearly discusses ANOTHER unit and never binds its own target.
The check no longer reads the TARGET's presence by tokens across languages —
that is the half no lexical join can see.

* witness — the R1109 shape (French prose, source-language units) with a
  counter carried on generic words raises no flag (red on the pre-fix code:
  it raised one).
* controls — the #3151 positive case still flags; the same counter in its
  own unit's paragraph passes; a two-of-eight match is not a citation.
* mutation — restoring the two-token bar reddens the generic-words witness.

Synthetic vocabularies only (no corpus content, privacy HARD).
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.reading_license import (
    check_reading_license,
)


def _state(units, counters):
    return SimpleNamespace(
        identified_arguments=units,
        counter_arguments=counters,
        argument_quality_scores={},
    )


# --- the R1109 shape: French prose, source-language units -------------------

_SOURCE_LANG_UNITS = {
    "arg_1": "The harbour bell announces the tide, the keeper swears by it.",
    "arg_2": "Toll receipts cover the dredging, the council argues each year.",
}

_ONE_FRENCH_COUNTER = [
    {
        "id": "ca_1",
        "target_arg_id": "arg_1",
        "counter_content": (
            "Deux mesures valent mieux que trois : quand le port change, il "
            "faut faire mieux après, puis deux fois contre toute attente."
        ),
        "strategy": "distinguo",
        "score": 0.5,
    }
]

#: French prose that binds NO unit (one shared word « council » at most) and
#: carries only the counter's generic vocabulary.
_GENERIC_PROSE = (
    "Le rapport note que la cloche annonce la marée ; quand le port change, "
    "il faut faire mieux après, puis deux fois contre toute attente, dit le "
    "council."
)


class TestTheGenericWordsAreNoCitation:
    def test_a_counter_carried_on_generic_words_raises_no_flag(self):
        """Red on the pre-fix code: « quand / faire / mieux / après / puis /
        deux / contre » are two-plus shared tokens, and one unit word
        (« council ») made the paragraph "about" arg_2 — the exact shape the
        R1109 render produced 32 times."""
        result = check_reading_license(
            _GENERIC_PROSE, _state(_SOURCE_LANG_UNITS, _ONE_FRENCH_COUNTER)
        )
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_on_wrong_unit" not in kinds

    def test_a_paragraph_that_binds_no_unit_places_no_counter(self):
        """Red on the pre-fix code: a SINGLE shared token made the paragraph
        "about" arg_2 (the target absent from it), while the counter is
        genuinely cited. One word places nothing."""
        units = {
            "arg_1": "Le registre du port consigne chaque marée depuis 1900.",
            "arg_2": "La jetée nord abrite les chaloupes des sauniers.",
        }
        counters = [
            {
                "id": "ca_1",
                "target_arg_id": "arg_1",
                "counter_content": (
                    "Les houles d'automne décident des marées, pas la cloche "
                    "du port."
                ),
                "score": 0.3,
            }
        ]
        prose = (
            "La jetée accueille les barques ; les houles d'automne décident "
            "des marées, pas la cloche."
        )
        result = check_reading_license(prose, _state(units, counters))
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_on_wrong_unit" not in kinds

    def test_two_of_eleven_tokens_is_not_a_citation(self):
        """The share bar: a counter with a large distinctive set is not
        "cited" by the two words a French sentence happens to share with it
        (2/11 here, measured on the R1109 render's own failure mode).

        The paragraph BINDS arg_2 on two distinctive tokens and never binds
        the target, so the bind bar does not decide this case: only the
        share bar keeps it silent (measured — with the share bar removed
        this witness flags, which is what makes it a witness for it).
        """
        units = {
            "arg_1": "Le registre du port consigne chaque marée depuis 1900.",
            "arg_2": "La jetée nord abrite les chaloupes des sauniers.",
        }
        counters = [
            {
                "id": "ca_1",
                "target_arg_id": "arg_1",
                "counter_content": (
                    "Le registre consigne les houles, mais aucune source ne "
                    "mentionne le relevé des cotes ni la hauteur officielle "
                    "des basses mers."
                ),
                "score": 0.3,
            }
        ]
        prose = (
            "La jetée accueille les chaloupes ; les houles et le relevé "
            "d'automne sont consignés au tableau."
        )
        result = check_reading_license(prose, _state(units, counters))
        kinds = [f["kind"] for f in result["flags"]]
        assert "counter_on_wrong_unit" not in kinds


class TestTheSoundJoinStillFlags:
    def test_a_clearly_cited_counter_in_another_units_paragraph_flags(self):
        """The #3151 positive case, re-pinned: the paragraph binds arg_alpha
        on four distinctive tokens and carries four of ca_1's six."""
        units = {
            "arg_alpha": "Le phare octogonal d'alpha domine la baie.",
            "arg_bravo": "Le fournil de bravo pétille dès l'aube.",
        }
        counters = [
            {
                "id": "ca_1",
                "target_arg_id": "arg_bravo",
                "counter_content": (
                    "Le fournil ne pétille que si la bonde océane reste ouverte."
                ),
                "score": 0.59,
            }
        ]
        weave = (
            "Le phare octogonal domine la baie, personne ne le conteste ; "
            "pourtant la bonde océane reste ouverte, et c'est là l'objection."
        )
        result = check_reading_license(weave, _state(units, counters))
        flags = [f for f in result["flags"] if f["kind"] == "counter_on_wrong_unit"]
        assert len(flags) == 1
        assert flags[0]["measured"]["target_arg_id"] == "arg_bravo"
        assert flags[0]["measured"]["paragraph_units"] == ["arg_alpha"]

    def test_its_own_units_paragraph_passes(self):
        """Control — the paragraph binds arg_bravo and cites ca_1, its own
        target: the counter sits where it belongs."""
        units = {
            "arg_alpha": "Le phare octogonal d'alpha domine la baie.",
            "arg_bravo": "Le fournil de bravo pétille dès l'aube.",
        }
        counters = [
            {
                "id": "ca_1",
                "target_arg_id": "arg_bravo",
                "counter_content": (
                    "Le fournil ne pétille que si la bonde océane reste ouverte."
                ),
                "score": 0.59,
            }
        ]
        weave = (
            "Le fournil de bravo pétille dès l'aube ; la bonde océane reste "
            "ouverte, dit l'objection."
        )
        result = check_reading_license(weave, _state(units, counters))
        assert [
            f["kind"] for f in result["flags"] if f["kind"] == "counter_on_wrong_unit"
        ] == []


class TestTheTraceSaysWhyItStaysSilent:
    def test_the_report_states_how_many_units_are_bound(self):
        """A silent check must not read as a clean one: the `checked` trace
        states how many units the render binds on the sound bar."""
        result = check_reading_license(
            _GENERIC_PROSE, _state(_SOURCE_LANG_UNITS, _ONE_FRENCH_COUNTER)
        )
        assert result["checked"]["units_bound_two_tokens"] == 0

    def test_a_bound_render_is_counted(self):
        units = {
            "arg_alpha": "Le phare octogonal d'alpha domine la baie.",
        }
        weave = "Le phare octogonal domine la baie depuis toujours."
        result = check_reading_license(weave, _state(units, []))
        assert result["checked"]["units_bound_two_tokens"] == 1
