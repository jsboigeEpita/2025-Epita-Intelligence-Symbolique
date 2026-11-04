# -*- coding: utf-8 -*-
"""#3390 — l'attribution d'un geste passe d'un rédacteur au suivant.

Lu sur le panel v1 cycle 0 : une détection RAPPORTÉE (le locuteur cite le
geste d'un tiers) atteignait la synthèse comme l'une des « vulnérabilités
structurelles » du locuteur ; un document d'arène fictionnelle (une pièce)
voyait ses personnages agrégés dans « le discours attribué à » l'auteur ; et
un document unilocuteur avec interjections du public déclenchait deux fois
la prudence deux-voix #2845 sur une attribution correcte. Trois rédacteurs,
trois lectures du même enregistrement — parce que le dossier ne PORTAIT pas
l'attribution : le briefing l'imprimait en jeton brut (``move_author=
reported``), les lignes d'arguments ne la portaient pas du tout, et le
vocabulaire fermé n'avait que deux valeurs (``speaker``, ``reported``).

Les témoins ci-dessous sont la DoD de l'issue :

* un sophisme RAPPORTÉ n'est pas attribué au locuteur par le dossier de
  synthèse — la ligne porte la PHRASE, pas le jeton ;
* une arène de fiction atteint le briefing ET l'Acte II, avec l'unique
  conséquence énoncée une fois : les personnages argumentent, l'auteur
  n'asserte pas ;
* une interjection du public n'est pas une seconde voix pour la prudence
  #2845 — le doute nomme un vrai second locuteur ou se tait ;
* le vocabulaire fermé s'étend (``character``, ``audience``) et vit en UN
  seul endroit (``MOVE_AUTHORS``), lu par les deux portes de l'état.

Nés rouges sur ``main`` : la phrase n'existait pas (jeton brut), la ligne
ARÈNE DE FICTION n'existait nulle part, la caution était inconditionnelle
sur la branche inférée, et ``add_fallacy``/``add_argument`` laissaient
tomber ``character``/``audience``.

Les libellés ici sont synthétiques : aucun nom de source, aucun texte de
corpus.
"""

from types import SimpleNamespace

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.speaker_record import (
    build_speaker_record,
    format_speaker_line,
)

# Les symboles NEUFS du fix (``MOVE_AUTHORS``, ``is_fiction_arena``) sont
# importés DANS les seuls tests qui les testent : sur ``main``, le fichier
# doit collecter pour que les témoins rougissent sur leurs ASSERTIONS, et
# les contrôles mesurent vert-des-deux-côtés — pas une erreur de collecte
# qui ne prouve rien.

_REPORTED_SENTENCE = (
    "RAPPORTÉ : le locuteur rapporte ce geste, il ne le commet pas "
    "(tiers : l'opposant)"
)


def _fallacy_record(**overrides):
    record = {
        "type": "Tu quoque",
        "family": "Obstruction",
        "justification": "Le geste décrit est rapporté, pas commis.",
        "target_argument_id": "arg_1",
    }
    record.update(overrides)
    return record


def _state(fallacies=None, provenance=None, arena=None, stakeholders=None):
    state = SimpleNamespace(
        propositional_analysis_results=None,
        fol_analysis_results=None,
        modal_analysis_results=None,
        raw_text="un texte synthétique quelconque",
        identified_arguments={
            "arg_1": {"id": "arg_1", "description": "Une position du texte."},
            "arg_2": {"id": "arg_2", "description": "Un geste rapporté d'un tiers."},
        },
        identified_fallacies=fallacies or {},
    )
    if provenance is not None:
        state.argument_provenance = provenance
    stakes = {}
    if arena is not None:
        stakes["discursive_arena"] = arena
    if stakeholders is not None:
        stakes["stakeholders"] = stakeholders
    if stakes:
        state.stakes_and_stakeholders = stakes
    return state


class TestTheBriefingLineCarriesTheAttributionSentence:
    """Le témoin central : le dossier de synthèse porte la PHRASE, pas le
    jeton. Un jeton n'est pas une phrase — la synthèse du cycle 0 a lu
    ``move_author=reported`` et inscrit la détection parmi les vulnérabilités
    du locuteur."""

    def test_a_reported_fallacy_carries_the_sentence_not_a_token(self):
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(
                fallacies={
                    "fallacy_1": _fallacy_record(
                        move_author="reported", move_author_label="l'opposant"
                    )
                }
            )
        )
        assert _REPORTED_SENTENCE in briefing
        assert "move_author=reported" not in briefing

    def test_a_reported_unit_carries_the_sentence(self):
        """La ligne d'ARGUMENT porte aussi l'attribution : le cycle 0 a vu une
        position rapportée agrégée aux mouvements du locuteur."""
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(
                provenance={
                    "arg_2": {
                        "move_author": "reported",
                        "move_author_label": "l'opposant",
                    }
                }
            )
        )
        assert "arg_2" in briefing
        assert _REPORTED_SENTENCE in briefing

    def test_the_attribution_survives_the_text_cut(self):
        """La note est apposée APRÈS la coupe (#2967) : le cap borne le
        texte-document, jamais la phrase d'attribution. Une note composée
        avant le cap pouvait être tronquée par lui — la ligne perdait
        exactement ce qu'elle existe pour porter."""
        state = _state(
            provenance={
                "arg_2": {"move_author": "reported", "move_author_label": "l'opposant"}
            }
        )
        state.identified_arguments["arg_2"]["description"] = (
            "Une phrase de position remise à un tiers, répétée pour dépasser "
            "le budget de la ligne. " * 12
        )
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert " […]" in briefing, "the long unit must actually be cut"
        assert _REPORTED_SENTENCE in briefing

    def test_a_character_fallacy_carries_the_personnage_sentence(self):
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(fallacies={"fallacy_1": _fallacy_record(move_author="character")})
        )
        assert "PERSONNAGE : geste commis par un personnage de la fiction" in briefing

    def test_an_audience_fallacy_carries_the_public_sentence(self):
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(fallacies={"fallacy_1": _fallacy_record(move_author="audience")})
        )
        assert "PUBLIC : interjection du public, pas le fait du locuteur" in briefing

    def test_a_silent_record_prints_no_author(self):
        """Contrôle : le silence reste silencieux (#1019) — vert des deux
        côtés, il mesure l'absence d'effet de bord."""
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(fallacies={"fallacy_1": _fallacy_record()})
        )
        assert "move_author" not in briefing
        assert "RAPPORTÉ" not in briefing
        assert "PERSONNAGE" not in briefing
        assert "PUBLIC" not in briefing

    def test_a_speaker_move_prints_no_note(self):
        """Le locuteur est le défaut historique de chaque ligne : une note
        sur chaque ligne enterrerait celles qui comptent. Le jeton
        ``move_author=speaker`` que ``main`` imprimait disparaît avec le fix
        — la phrase ne remplace le jeton que lorsqu'elle porte une
        information (RAPPORTÉ, PERSONNAGE, PUBLIC)."""
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(fallacies={"fallacy_1": _fallacy_record(move_author="speaker")})
        )
        assert "move_author=speaker" not in briefing
        assert "RAPPORTÉ" not in briefing


class TestTheClosedVocabularyLivesInOnePlace:
    """``MOVE_AUTHORS`` est LE vocabulaire fermé : les deux portes de l'état
    (``add_argument``, ``add_fallacy``) le lisent, donc l'étendre ne peut pas
    dériver entre elles. Avant, sept copies littérales du couple à deux
    valeurs auraient dérivé en sept portes."""

    def test_the_vocabulary_lists_four_values(self):
        from argumentation_analysis.core.fallacy_attribution import MOVE_AUTHORS

        assert MOVE_AUTHORS == ("speaker", "reported", "character", "audience")

    def test_add_fallacy_stores_a_character_move(self):
        state = UnifiedAnalysisState("un texte quelconque")
        state.add_argument("Une unité du texte.")
        fid = state.add_fallacy(
            "Tu quoque",
            "Un geste commis par un personnage.",
            "arg_1",
            move_author="character",
        )
        assert state.identified_fallacies[fid]["move_author"] == "character"

    def test_add_argument_stores_an_audience_move(self):
        state = UnifiedAnalysisState("un texte quelconque")
        state.add_argument(
            "Une interjection du public.",
            producer="llm_extract",
            move_author="audience",
        )
        assert state.argument_provenance["arg_1"]["move_author"] == "audience"


class TestTheFictionArenaReachesEveryWriter:
    """L'arène fictionnelle atteint le briefing de synthèse ET l'Acte II,
    avec l'unique conséquence énoncée une fois : les personnages
    argumentent, l'auteur n'asserte pas. Les marqueurs sont étroits à dessein
    — « débat » ou « dialogue » ne nomme pas une fiction, et une ligne
    ARÈNE DE FICTION de trop exempterait les gestes d'un vrai locuteur."""

    def test_the_briefing_states_the_fiction_arena(self):
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            _state(arena="une pièce de théâtre en trois actes")
        )
        assert "ARÈNE DE FICTION" in briefing
        assert "ceux des PERSONNAGES" in briefing

    def test_act2_carries_the_arena_and_its_fiction_line(self):
        prompt = build_act2_prompt(
            build_act2_evidence(_state(arena="une pièce de théâtre"))
        )
        assert "Arène discursive :" in prompt
        assert "ARÈNE DE FICTION : les gestes détectés sont ceux des " in prompt

    def test_a_debate_arena_is_not_fiction(self):
        """Témoin des marqueurs étroits : « débat » ne nomme pas une pièce —
        une arène réelle ne doit pas lever le cadre fictionnel."""
        from argumentation_analysis.reporting.restitution.arena_record import (
            build_arena_record,
            is_fiction_arena,
        )

        state = _state(arena="un débat télévisé entre deux candidats")
        assert not is_fiction_arena(build_arena_record(state))

    def test_a_debate_arena_raises_no_fiction_line(self):
        """Contrôle anti-pendule, vert des deux côtés : une ligne ARÈNE DE
        FICTION de trop exempterait les gestes d'un vrai locuteur."""
        state = _state(arena="un débat télévisé entre deux candidats")
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert "ARÈNE DE FICTION" not in briefing
        act2 = build_act2_prompt(build_act2_evidence(state))
        assert "ARÈNE DE FICTION" not in act2


class TestThePromptTeachesAttribution:
    """La règle 7 dit au rédacteur ce que les mentions RAPPORTÉ /
    PERSONNAGE / PUBLIC licencient : rien de tout cela n'est le geste du
    locuteur. Elle vit dans la variante opaque ET dans la variante
    désanonymisée (le swap ne touche que la règle 5)."""

    def test_rule_7_names_the_markers_and_the_fiction_arena(self):
        prompt = DeepSynthesisAgent.GROUNDED_SYNTHESIS_PROMPT
        assert "7. ATTRIBUTION" in prompt
        for marker in ("RAPPORTÉ", "PERSONNAGE", "PUBLIC"):
            assert marker in prompt
        assert "ne l'inscris jamais dans ses vulnérabilités" in prompt
        assert "ARÈNE DE FICTION" in prompt

    def test_rule_7_travels_to_the_deanonymized_variant(self):
        prompt = DeepSynthesisAgent.grounded_synthesis_prompt(deanonymized=True)
        assert "7. ATTRIBUTION" in prompt


class TestAnAudienceInterjectionIsNotASecondVoice:
    """Le témoin #2845 : un document unilocuteur avec interjections du
    public ne déclenche PAS la prudence deux-voix — une interjection du
    public n'est pas la seconde voix du document. Sur ``main``, la caution
    était inconditionnelle sur la branche inférée."""

    _AUDIENCE_STATE = _state(
        stakeholders=[
            {"name": "Speaker_A", "role": "speaker"},
            {"name": "Un membre du public", "role": "audience"},
        ]
    )
    _OPPONENT_STATE = _state(
        stakeholders=[
            {"name": "Speaker_A", "role": "speaker"},
            {"name": "l'opposant", "role": "opponent"},
        ]
    )

    def test_an_audience_stakeholder_alone_raises_no_caution(self):
        line = format_speaker_line(build_speaker_record(self._AUDIENCE_STATE))
        assert "prudence #2845" not in line

    def test_the_caution_still_names_a_real_opponent(self):
        """Contrôle : un vrai second locuteur déclenche toujours la prudence."""
        line = format_speaker_line(build_speaker_record(self._OPPONENT_STATE))
        assert "prudence #2845" in line

    def test_the_gate_reaches_the_briefings_speaker_line(self):
        """Le briefing de synthèse cite la même ligne (en mode désanonymisé,
        #3336) — le doute y est gated aussi, pas seulement dans les actes."""
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            self._AUDIENCE_STATE, deanonymized=True
        )
        assert "prudence #2845" not in briefing
        briefing_opponent = DeepSynthesisAgent.build_artifact_briefing(
            self._OPPONENT_STATE, deanonymized=True
        )
        assert "prudence #2845" in briefing_opponent
