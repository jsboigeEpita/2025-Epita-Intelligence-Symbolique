# -*- coding: utf-8 -*-
"""#3180 — a fallacy the detector places in REPORTED speech was credited to the
speaker on every surface.

Read on the paid pass R1108 (doc_A): ``fallacy_29`` (tu quoque, family
Obstruction, ``target_argument_id: arg_86``) reaches Act II as « Speaker_A
retourne l'accusation » and the deep synthesis as one of « the discourse's own
moves ». The detector's own justification says the opposite: it describes a
move by the OTHER party that the speaker reports, and finds the speaker's reply
sound. The record had no field for that, so attribution fell back silently on
``target_argument_id`` — a denunciation became a self-incrimination.

The witnesses below are the issue's DoD:

* a record whose ``move_author`` is the reported party fails on main: Act II
  builds no movement out of it, counts it in no speaker tally, and names it
  apart with the party the text names; the synthesis line carries the author;
* a record with NO field keeps today's attribution and invents no party
  (#1019 tri-state: the absent case stays absent, it does not become
  ``speaker`` by decree).

The labels here are synthetic: no source name, no corpus text.
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
from argumentation_analysis.reporting.restitution.virtuous_identification import (
    detect_virtuous_mode,
)

_TARGET = "arg_86"


def _fallacy_record(**overrides):
    record = {
        "type": "Tu quoque",
        "family": "Obstruction",
        "justification": "Le locuteur rapporte une riposte d'un tiers, et sa "
        "réponse est correcte : le sophisme est dans le geste décrit.",
        "target_argument_id": _TARGET,
    }
    record.update(overrides)
    return record


def _state(fallacies):
    return SimpleNamespace(
        propositional_analysis_results=None,
        fol_analysis_results=None,
        modal_analysis_results=None,
        identified_arguments={
            _TARGET: {"id": _TARGET, "description": "Une unité du texte."},
        },
        identified_fallacies=fallacies,
    )


def _prompt(fallacies):
    return build_act2_prompt(build_act2_evidence(_state(fallacies)))


class TestTheReportedMoveIsNotTheSpeakers_:
    """The measured record: a tu quoque the text reports."""

    def _reported(self):
        return {
            "fallacy_29": _fallacy_record(
                move_author="reported", move_author_label="l'opposant"
            )
        }

    def test_it_is_carried_apart_from_the_speaker_fallacies(self):
        evidence = build_act2_evidence(_state(self._reported()))
        assert [f.fallacy_id for f in evidence.reported_fallacies] == ["fallacy_29"]
        assert evidence.fallacies_total == 0, (
            "a reported fallacy must not enter the speaker's fallacy count"
        )

    def test_it_builds_no_movement(self):
        """The Procédé line is where the report makes the speaker commit it."""
        prompt = _prompt(self._reported())
        assert "Procédé : « Tu quoque »" not in prompt

    def test_the_prompt_names_the_report_and_the_party(self):
        prompt = _prompt(self._reported())
        assert "SOPHISMES RAPPORTÉS, NON COMMIS PAR LE LOCUTEUR" in prompt
        assert "l'opposant" in prompt
        assert "le locuteur les RAPPORTE" in prompt

    def test_it_keeps_its_target_unit_visible(self):
        """Surfaced, not dropped (#1019): the reader still learns which unit
        reports the move."""
        evidence = build_act2_evidence(_state(self._reported()))
        assert evidence.reported_fallacies[0].target_arg_id == _TARGET


class TestASpeakerMoveIsUnchanged:
    def test_a_speaker_fallacy_still_builds_its_movement_and_its_count(self):
        evidence = build_act2_evidence(
            _state({"fallacy_1": _fallacy_record(move_author="speaker")})
        )
        # getattr default: the control must test TODAY's attribution on main,
        # not the presence of the new field (green both sides).
        assert getattr(evidence, "reported_fallacies", []) == []
        assert evidence.fallacies_total == 1
        assert "Procédé : « Tu quoque »" in build_act2_prompt(evidence)

    def test_a_speaker_fallacy_still_has_a_party_label_when_given(self):
        evidence = build_act2_evidence(
            _state(
                {
                    "fallacy_1": _fallacy_record(
                        move_author="speaker", move_author_label="le locuteur"
                    )
                }
            )
        )
        assert evidence.fallacies_total == 1
        # getattr default: the control must test TODAY's attribution on main,
        # not the presence of the new field (green both sides).
        assert getattr(evidence, "reported_fallacies", []) == []


class TestTheAbsentFieldStaysAbsent:
    """Older states carry no field. They keep today's attribution."""

    def test_no_field_keeps_todays_attribution(self):
        evidence = build_act2_evidence(_state({"fallacy_29": _fallacy_record()}))
        # getattr default: the control must test TODAY's attribution on main,
        # not the presence of the new field (green both sides).
        assert getattr(evidence, "reported_fallacies", []) == []
        assert evidence.fallacies_total == 1
        assert "Procédé : « Tu quoque »" in build_act2_prompt(evidence)

    def test_no_party_is_invented(self):
        prompt = _prompt({"fallacy_29": _fallacy_record()})
        assert "SOPHISMES RAPPORTÉS" not in prompt

    def test_an_unknown_value_falls_back_to_the_speaker(self):
        """A value outside the pair is not a third state invented on the fly;
        it reads as the silent case, which is today's attribution."""
        evidence = build_act2_evidence(
            _state({"fallacy_29": _fallacy_record(move_author="someone else")})
        )
        # getattr default: the control must test TODAY's attribution on main,
        # not the presence of the new field (green both sides).
        assert getattr(evidence, "reported_fallacies", []) == []
        assert evidence.fallacies_total == 1


class TestTheSynthesisBriefingCarriesTheAuthor:
    def _briefing(self, fallacies):
        return DeepSynthesisAgent.build_artifact_briefing(_state(fallacies))

    def test_a_reported_move_says_so(self):
        briefing = self._briefing(
            {
                "fallacy_29": _fallacy_record(
                    move_author="reported", move_author_label="l'opposant"
                )
            }
        )
        assert "move_author=reported" in briefing
        assert "move_author_label=l'opposant" in briefing

    def test_a_silent_record_says_nothing_about_an_author(self):
        briefing = self._briefing({"fallacy_29": _fallacy_record()})
        assert "move_author" not in briefing


class TestTheVirtuousVerdictCountsTheSpeakersOwnMoves:
    """``detect_virtuous_mode`` drives Act I framing, Act II's centre and
    Act III's titling — the most consequential reader of the speaker's count.
    A text whose only fallacy detection sits in REPORTED speech is the
    virtuous text par excellence: it denounced the move."""

    def _virtuous_state(self, **fallacy_overrides):
        return SimpleNamespace(
            identified_arguments={_TARGET: {"id": _TARGET}},
            identified_fallacies={
                "fallacy_29": _fallacy_record(**fallacy_overrides)
            },
            argument_quality_scores={_TARGET: {"scores": {"clarte": 0.8}}},
            analysis_coverage={
                "fallacy_per_argument": {"unit_ids": [_TARGET]}
            },
            propositional_analysis_results=None,
            fol_analysis_results=None,
        )

    def test_a_reported_move_does_not_count_against_virtue(self):
        assessment = detect_virtuous_mode(
            self._virtuous_state(move_author="reported", move_author_label="l'opposant")
        )
        assert assessment.fallacy_count == 0
        assert getattr(assessment, "reported_fallacy_count", 0) == 1
        assert assessment.is_virtuous

    def test_a_speaker_move_still_disqualifies(self):
        assessment = detect_virtuous_mode(self._virtuous_state(move_author="speaker"))
        assert assessment.fallacy_count == 1
        assert getattr(assessment, "reported_fallacy_count", 0) == 0
        assert not assessment.is_virtuous

    def test_the_reasoning_names_the_reported_detection(self):
        """Named in every branch — a detection the report drops silently is
        the #1019 defect this family is about."""
        assessment = detect_virtuous_mode(
            self._virtuous_state(move_author="reported", move_author_label="l'opposant")
        )
        assert "RAPPORTÉ" in assessment.reasoning
        assert "1 sophisme RAPPORTÉ" in assessment.reasoning

    def test_a_state_with_no_marker_never_reports_one(self):
        assessment = detect_virtuous_mode(self._virtuous_state())
        assert getattr(assessment, "reported_fallacy_count", 0) == 0
        assert "RAPPORTÉ" not in assessment.reasoning


class TestTheWritersCarryTheAuthor:
    """The field must survive the journey from the detection output to the
    state — a pass-through that drops it puts every reader back on today's
    implicit attribution, silently."""

    def test_the_pipeline_writer_carries_the_author(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_hierarchical_fallacy_to_state,
        )

        state = UnifiedAnalysisState("un texte quelconque")
        state.add_argument("Une unité du texte.")
        _write_hierarchical_fallacy_to_state(
            {
                "fallacies": [
                    {
                        "type": "Tu quoque",
                        "explanation": "Le locuteur rapporte le geste d'un tiers.",
                        "target_argument_id": "arg_1",
                        "move_author": "reported",
                        "move_author_label": "l'opposant",
                    }
                ]
            },
            state,
            {},
        )
        reported = [
            e
            for e in state.identified_fallacies.values()
            if e.get("move_author") == "reported"
        ]
        assert reported and reported[0]["move_author_label"] == "l'opposant"

    def test_the_pipeline_writer_keeps_silence_silent(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_hierarchical_fallacy_to_state,
        )

        state = UnifiedAnalysisState("un texte quelconque")
        state.add_argument("Une unité du texte.")
        _write_hierarchical_fallacy_to_state(
            {
                "fallacies": [
                    {
                        "type": "Tu quoque",
                        "explanation": "Une justification.",
                        "target_argument_id": "arg_1",
                    }
                ]
            },
            state,
            {},
        )
        for entry in state.identified_fallacies.values():
            assert "move_author" not in entry


class TestTheMarkerSurvivesTheState:
    """The writer stores the marker only when it was stated (#1019)."""

    def test_a_reported_marker_is_stored_with_its_party(self):
        state = UnifiedAnalysisState("un texte quelconque")
        state.add_argument("Une unité du texte.")
        fid = state.add_fallacy(
            "Tu quoque",
            "Le locuteur rapporte le geste d'un tiers.",
            "arg_1",
            move_author="reported",
            move_author_label="l'opposant",
        )
        entry = state.identified_fallacies[fid]
        assert entry["move_author"] == "reported"
        assert entry["move_author_label"] == "l'opposant"

    def test_no_marker_is_stored_when_the_detector_said_nothing(self):
        state = UnifiedAnalysisState("un texte quelconque")
        state.add_argument("Une unité du texte.")
        fid = state.add_fallacy("Tu quoque", "Une justification.", "arg_1")
        entry = state.identified_fallacies[fid]
        assert "move_author" not in entry
        assert "move_author_label" not in entry
