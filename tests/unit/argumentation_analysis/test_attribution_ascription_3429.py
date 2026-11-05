# -*- coding: utf-8 -*-
"""#3429 — une vue que le locuteur PRÊTE à un tiers pour la combattre est son
geste, pas une parole rapportée.

Lu sur le panel cycle 2 : sur un document, 5 détections portaient
``move_author="reported"`` et le rendu disait qu'elles étaient « attribuées
aux voix citées » — voix que le document ne porte pas. Le locuteur attribue
lui-même une vue à un groupe pour l'attaquer : l'attribution EST son geste
(or un homme de paille, ou une attribution conspirationniste), ce n'est pas
du discours rapporté. Dans l'autre sens, une définition que le locuteur
impute à un adversaire puis dénonce était dite « redéfinie » par lui.

La définition vivait dans deux descriptions d'outil écrites à la main, qui ne
discriminaient pas les deux cas. Elle vit maintenant dans UNE table
(``MOVE_AUTHOR_DEFINITIONS_FR``) que les deux surfaces lisent.

Témoins :

* la définition discrimine les deux cas, et les deux descriptions d'outil en
  sont LITTÉRALEMENT le texte — pas deux phrases qui se ressemblent ;
* trois unités synthétiques : une citation réelle, une vue prêtée à un groupe
  pour l'attaquer, une reformulation ironique d'une position adverse — les
  deux dernières sont ``speaker`` et, sous ce label, elles comptent dans les
  fautes du locuteur et sortent du bloc rapporté, à l'Acte II comme à
  l'Acte III ;
* côté rédacteur : un ``reported`` SANS label ne devient jamais « les voix
  citées » — aucun tiers n'est nommé ; avec un label, le tiers est nommé.

Anti-pendule : le correctif de #3180 (le geste cité d'un opposant n'est pas
imputé au locuteur) doit tenir — ses témoins sont rejoués dans la même
sélection, inchangés.

Les textes sont synthétiques : aucun nom de source, aucun contenu de corpus.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

# #3429 — les symboles NEUFS (``MOVE_AUTHOR_DEFINITIONS_FR``,
# ``move_author_guidance_fr``) sont importés DANS les témoins qui les lisent :
# sur l'arbre pré-#3429, le fichier doit COLLECTER pour que chaque témoin
# rougisse sur son assertion, jamais sur une erreur de collection qui ne
# mesure rien. Les deux valeurs du vocabulaire, elles, existent depuis #3180.
from argumentation_analysis.core.fallacy_attribution import (
    MOVE_AUTHOR_REPORTED,
    MOVE_AUTHOR_SPEAKER,
    move_author_note,
)


def _definitions() -> dict:
    from argumentation_analysis.core.fallacy_attribution import (
        MOVE_AUTHOR_DEFINITIONS_FR,
    )

    return MOVE_AUTHOR_DEFINITIONS_FR


def _guidance() -> str:
    from argumentation_analysis.core.fallacy_attribution import (
        move_author_guidance_fr,
    )

    return move_author_guidance_fr()


# --- les trois unités synthétiques (opaques, inventées) ----------------------

# (1) une citation RÉELLE : les mots d'un opposant, que le texte relaie.
_QUOTED_OPPONENT = (
    "L'opposant a écrit, dans la note qu'il a rendue publique : « le "
    "dispositif ne tient que par la peur du contrôle »."
)

# (2) une vue que le locuteur PRÊTE à un groupe pour l'attaquer.
_ASCRIBED_TO_GROUP = (
    "Ils prétendent que la réforme ne sert qu'à protéger les commanditaires, "
    "et c'est précisément ce qu'il faut leur opposer."
)

# (3) une reformulation IRONIQUE de la position adverse.
_IRONIC_RESTATEMENT = (
    "Nos détracteurs, paraît-il, trouvent ce texte admirable : on voit ce que "
    "vaut leur admiration."
)

_CASES = (
    # (unit, the author the #3429 definition assigns, the discriminator the
    #   definition must carry for that value)
    (_QUOTED_OPPONENT, MOVE_AUTHOR_REPORTED, "réellement tenues"),
    (_ASCRIBED_TO_GROUP, MOVE_AUTHOR_SPEAKER, "attribue"),
    (_IRONIC_RESTATEMENT, MOVE_AUTHOR_SPEAKER, "ironie"),
)


def _fallacy_record(**overrides):
    record = {
        "type": "Faux dilemme",
        "family": "Présomption",
        "justification": "Le geste décrit est attribué par le locuteur.",
        "target_argument_id": "arg_1",
    }
    record.update(overrides)
    return record


def _state(fallacies=None):
    return SimpleNamespace(
        propositional_analysis_results=None,
        fol_analysis_results=None,
        modal_analysis_results=None,
        raw_text="un texte synthétique quelconque",
        identified_arguments={
            "arg_1": {"id": "arg_1", "description": "Une position du texte."},
        },
        identified_fallacies=fallacies or {},
    )


def _line(text: str, marker: str) -> str:
    start = text.find(marker)
    assert start != -1, f"the prompt carries no {marker!r} block"
    return text[start:]


# ---------------------------------------------------------------------------
# Demande 1 — la définition discrimine les deux cas, en un seul endroit
# ---------------------------------------------------------------------------


class TestTheDefinitionDiscriminatesTheTwoCases:
    def test_the_table_exists_for_the_four_values(self) -> None:
        assert set(_definitions()) == {
            "speaker",
            "reported",
            "character",
            "audience",
        }

    def test_speaker_covers_an_ascription_made_in_order_to_attack(self) -> None:
        text = _definitions()[MOVE_AUTHOR_SPEAKER]
        for word in ("attribue", "adversaire", "ironie", "caricature"):
            assert word in text, (word, text)
        # La distinction est explicite : une attribution n'est pas une parole
        # rapportée.
        assert "pas une parole rapportée" in text

    def test_reported_covers_words_actually_held_by_another_party(self) -> None:
        text = _definitions()[MOVE_AUTHOR_REPORTED]
        assert "réellement tenues" in text
        # ... et l'exclusion est dite, pas laissée au lecteur.
        assert "n'est PAS rapportée" in text

    def test_both_tool_descriptions_are_the_one_text(self) -> None:
        from argumentation_analysis.core.phase_scoped_state import (
            ExtractionPhaseState,
        )
        from argumentation_analysis.core.state_manager_plugin import (
            StateManagerPlugin,
        )

        guidance = _guidance()
        for fn in (
            ExtractionPhaseState.add_identified_fallacy,
            StateManagerPlugin.add_identified_fallacy,
        ):
            description = getattr(fn, "__kernel_function_description__", "")
            assert description == guidance, (
                "the tool description must BE the shared definition, not a "
                "sentence that resembles it"
            )

    def test_an_unlabelled_reported_names_no_party(self) -> None:
        note = move_author_note(_fallacy_record(move_author="reported"))
        assert "tiers" not in note.replace("geste d'un tiers", "")
        assert "«" not in note


# ---------------------------------------------------------------------------
# Demande 2 — trois unités synthétiques, et leur conséquence dans l'état
# ---------------------------------------------------------------------------


class TestTheThreeSyntheticUnitsReachTheRightAuthor:
    def test_the_definition_covers_each_case(self) -> None:
        for unit, expected, discriminator in _CASES:
            assert unit.strip(), "the fixture must carry a unit"
            text = _definitions()[expected]
            assert discriminator in text, (unit[:40], expected, discriminator)

    def test_the_two_ascription_cases_leave_the_reported_block(self) -> None:
        """La conséquence mesurable du label : sous ``speaker``, la détection
        compte dans les fautes du locuteur et ne figure plus dans le bloc
        rapporté — à l'Acte II comme à l'Acte III."""
        for unit, expected, _discriminator in _CASES[1:]:
            record = _fallacy_record(move_author=expected, justification=unit)
            state = _state({"fallacy_1": record})
            act2 = build_act2_evidence(state)
            act3 = build_act3_evidence(state)
            assert act2.fallacies_total == 1
            assert getattr(act2, "reported_fallacies", []) == []
            assert act3.fallacies_total == 1
            assert act3.reported_fallacies_total == 0
            prompt2 = build_act2_prompt(act2)
            prompt3 = build_act3_prompt(act3)
            assert "SOPHISMES RAPPORTÉS" not in prompt2
            assert "SOPHISMES RAPPORTÉS" not in prompt3

    def test_the_quoted_case_stays_reported(self) -> None:
        """Le contrôle qui tient #3180 : une citation réelle reste rapportée —
        elle ne compte pas parmi les fautes du locuteur, et les deux actes
        la nomment comme telle."""
        unit, expected, _discriminator = _CASES[0]
        record = _fallacy_record(
            move_author=expected,
            move_author_label="l'opposant",
            justification=unit,
        )
        state = _state({"fallacy_1": record})
        act2 = build_act2_evidence(state)
        act3 = build_act3_evidence(state)
        assert act2.fallacies_total == 0
        assert len(act2.reported_fallacies) == 1
        assert act3.fallacies_total == 0
        assert act3.reported_fallacies_total == 1


# ---------------------------------------------------------------------------
# Demande 3 — côté rédacteur : pas de label, pas d'attribution
# ---------------------------------------------------------------------------


class TestTheWriterNamesAPartyOnlyWhenTheTextDoes:
    def test_act2_without_a_label_forbids_naming_a_quoted_voice(self) -> None:
        record = _fallacy_record(move_author="reported")
        prompt = build_act2_prompt(build_act2_evidence(_state({"f1": record})))
        block = _line(prompt, "SOPHISMES RAPPORTÉS")
        assert "le texte ne nomme aucun tiers" in block
        assert "voix citée" in block
        # L'instruction périmée qui envoyait le conducteur vers un tiers
        # inexistant est partie.
        assert "au tiers nommé ci-dessous" not in block

    def test_act2_with_a_label_names_it(self) -> None:
        record = _fallacy_record(move_author="reported", move_author_label="l'opposant")
        prompt = build_act2_prompt(build_act2_evidence(_state({"f1": record})))
        block = _line(prompt, "SOPHISMES RAPPORTÉS")
        assert "l'opposant" in block
        assert "au tiers nommé ci-dessous" in block
        assert "le texte ne nomme aucun tiers" not in block

    def test_act3_without_a_label_forbids_naming_a_quoted_voice(self) -> None:
        record = _fallacy_record(move_author="reported")
        prompt = build_act3_prompt(build_act3_evidence(_state({"f1": record})))
        block = _line(prompt, "SOPHISMES RAPPORTÉS")
        assert "le texte ne nomme aucun tiers" in block
        assert "voix citée" in block
        assert "le texte nomme le tiers" not in block

    def test_act3_with_a_label_names_it(self) -> None:
        record = _fallacy_record(move_author="reported", move_author_label="l'opposant")
        prompt = build_act3_prompt(build_act3_evidence(_state({"f1": record})))
        block = _line(prompt, "SOPHISMES RAPPORTÉS")
        assert "« l'opposant »" in block
        assert "le texte ne nomme aucun tiers" not in block

    def test_act3_evidence_carries_distinct_labels_only(self) -> None:
        state = _state(
            {
                "f1": _fallacy_record(
                    move_author="reported", move_author_label="l'opposant"
                ),
                "f2": _fallacy_record(
                    move_author="reported", move_author_label="l'opposant"
                ),
                "f3": _fallacy_record(move_author="reported"),
            }
        )
        act3 = build_act3_evidence(state)
        assert act3.reported_fallacies_total == 3
        assert act3.reported_fallacies_labels == ["l'opposant"]

    def test_the_state_stores_the_speaker_label_the_producer_chose(self) -> None:
        """Le producteur qui suit la nouvelle définition écrit ``speaker``, et
        l'état l'enregistre — la lecture ne diverge pas du stockage."""
        state = UnifiedAnalysisState("un texte synthétique quelconque")
        state.add_argument("Une unité du texte.")
        fid = state.add_fallacy(
            "Homme de paille",
            _ASCRIBED_TO_GROUP,
            "arg_1",
            move_author=MOVE_AUTHOR_SPEAKER,
        )
        assert state.identified_fallacies[fid]["move_author"] == "speaker"
