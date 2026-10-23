# -*- coding: utf-8 -*-
"""#1109 reader rework — every attribution count site reads ONE predicate.

The writer stores ``move_author`` / ``move_author_label`` on a detection
(``speaker`` | ``reported``). This file pins the READER half: a reported
detection is another party's move that the text denounces or cites — it must
never be counted as the speaker's, never contest the unit that reports it, and
never be buried (it stays surfaced with its third-party author).

Every count site reads :func:`argumentation_analysis.core.fallacy_attribution.is_speaker_move`.
Absent or invalid ``move_author`` keeps the legacy speaker attribution.

Synthetic ids and invented text only — no corpus, no source name.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    ArgumentMapEntry,
    ConvergentVerdict,
    DeepSynthesisReport,
    FallacyDiagnosis,
)
from argumentation_analysis.core.fallacy_attribution import (
    is_reported_move,
    is_speaker_move,
    move_author_label_of,
    move_author_of,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _collect_weak_points,
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.conclusion_salience import (
    _fallacy_target_ids,
)
from argumentation_analysis.reporting.restitution.specialist_roles import (
    _fallacy_targets,
)
from argumentation_analysis.orchestration.conversational_orchestrator import (
    _run_belief_revision_from_state,
)

_TARGET = "arg_1"


def _record(**overrides):
    record = {
        "type": "Tu quoque",
        "family": "Obstruction",
        "justification": "Le locuteur rapporte une riposte d'un tiers.",
        "target_argument_id": _TARGET,
    }
    record.update(overrides)
    return record


# --- the one predicate ----------------------------------------------------


class TestTheSharedPredicate:
    def test_reported_is_not_the_speakers_move(self):
        entry = _record(move_author="reported", move_author_label="l'opposant")
        assert is_speaker_move(entry) is False
        assert is_reported_move(entry) is True
        assert move_author_of(entry) == "reported"
        assert move_author_label_of(entry) == "l'opposant"

    def test_speaker_is_the_speakers_move(self):
        entry = _record(move_author="speaker")
        assert is_speaker_move(entry) is True
        assert is_reported_move(entry) is False

    def test_absent_keeps_the_legacy_speaker_attribution(self):
        entry = _record()
        assert move_author_of(entry) == "speaker"
        assert is_speaker_move(entry) is True
        assert move_author_label_of(entry) == ""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("someone else", "speaker"),
            ("", "speaker"),
            (None, "speaker"),
            (7, "speaker"),
            (" reported ", "reported"),  # whitespace is trimmed
            ("REPORTED", "speaker"),  # the protocol value is lowercase
        ],
    )
    def test_invalid_or_padded_values_never_invent_a_party(self, value, expected):
        entry = _record(move_author=value)
        assert move_author_of(entry) == expected
        assert is_reported_move(entry) is (expected == "reported")

    def test_non_mapping_records_read_as_speaker(self):
        assert is_speaker_move(None) is True
        assert is_speaker_move("not a record") is True


# --- deep synthesis: argument map ----------------------------------------


def _map_state(fallacies):
    return SimpleNamespace(
        identified_arguments={
            "arg_1": {"id": "arg_1", "description": "Une unité du texte."},
            "arg_2": {"id": "arg_2", "description": "Une autre unité."},
        },
        identified_fallacies=fallacies,
        counter_arguments=[],
    )


class TestTheArgumentMapCountsOnlyTheSpeakersAttacks:
    def test_a_reported_move_builds_no_attack_edge(self):
        entries = DeepSynthesisAgent._build_argument_map(
            _map_state(
                {"f1": _record(move_author="reported", move_author_label="l'opposant")}
            )
        )
        by_id = {e.arg_id: e for e in entries}
        assert by_id["arg_1"].attacked_by == []

    def test_a_speaker_move_still_attacks(self):
        entries = DeepSynthesisAgent._build_argument_map(
            _map_state({"f1": _record(move_author="speaker")})
        )
        by_id = {e.arg_id: e for e in entries}
        assert by_id["arg_1"].attacked_by == ["fallacy_f1"]

    @pytest.mark.parametrize("overrides", [{}, {"move_author": "unknown"}])
    def test_absent_or_invalid_keeps_the_legacy_attack(self, overrides):
        entries = DeepSynthesisAgent._build_argument_map(
            _map_state({"f1": _record(**overrides)})
        )
        by_id = {e.arg_id: e for e in entries}
        assert by_id["arg_1"].attacked_by == ["fallacy_f1"]


# --- deep synthesis: diagnoses + deterministic section 3/4 rows ----------


class TestTheDiagnosisCarriesWhoseMove:
    def test_a_reported_record_is_surfaced_with_its_author(self):
        state = _map_state(
            {"f1": _record(move_author="reported", move_author_label="l'opposant")}
        )
        diagnosis = DeepSynthesisAgent._build_fallacy_diagnoses(state)[0]
        assert diagnosis.move_author == "reported"
        assert diagnosis.move_author_label == "l'opposant"

    @pytest.mark.parametrize("overrides", [{}, {"move_author": "unknown"}])
    def test_absent_or_invalid_reads_speaker(self, overrides):
        diagnosis = DeepSynthesisAgent._build_fallacy_diagnoses(
            _map_state({"f1": _record(**overrides)})
        )[0]
        assert diagnosis.move_author == "speaker"
        assert diagnosis.move_author_label == ""


def _diagnosis(fid, family, move_author="speaker", label=""):
    return FallacyDiagnosis(
        fallacy_id=fid,
        family=family,
        taxonomy_path=f"fallacy/{family}/{fid}",
        textual_span="un extrait",
        commentary=f"{fid}: une justification assez longue pour l'exemplaire.",
        impacted_args=["arg_1"],
        move_author=move_author,
        move_author_label=label,
    )


class TestSection3SurfacesTheReportedMoveApart:
    def test_render_markdown_names_the_third_party(self):
        report = DeepSynthesisReport()
        report.fallacy_diagnoses = [
            _diagnosis("f1", "Obstruction", "reported", "l'opposant")
        ]
        rendered = DeepSynthesisAgent.render_markdown(report)
        assert "Auteur du geste" in rendered
        assert "l'opposant" in rendered
        assert "le locuteur ne le commet pas" in rendered

    def test_a_speaker_diagnosis_carries_no_third_party_note(self):
        report = DeepSynthesisReport()
        report.fallacy_diagnoses = [_diagnosis("f1", "Obstruction")]
        assert "Auteur du geste" not in DeepSynthesisAgent.render_markdown(report)


class TestTheAdjudicationDoesNotAdjudicateAReportedFamily:
    def test_a_reported_family_is_not_claimed_or_grounded(self):
        verdicts = [
            ConvergentVerdict(arg_id="arg_1", score=2, methods=["dung", "quality"])
        ]
        rows = DeepSynthesisAgent._build_adjudication_table(
            [_diagnosis("f1", "Obstruction", "reported", "l'opposant")], verdicts
        )
        assert rows == []

    def test_a_speaker_family_is_still_grounded(self):
        verdicts = [
            ConvergentVerdict(arg_id="arg_1", score=2, methods=["dung", "quality"])
        ]
        rows = DeepSynthesisAgent._build_adjudication_table(
            [_diagnosis("f1", "Obstruction")], verdicts
        )
        assert [r["family"] for r in rows] == ["Obstruction"]
        assert rows[0]["status"] == "grounded"


def _section4_prompt(report):
    kernel = create_autospec(Kernel, instance=True)
    kernel.get_prompt_execution_settings_from_service_id = MagicMock(
        return_value=MagicMock()
    )
    capture = AsyncMock(return_value="ok")
    kernel.invoke_prompt = capture
    stub = SimpleNamespace(_llm_service_id="default", kernel=kernel)
    asyncio.run(DeepSynthesisAgent._llm_synthesis(stub, report))
    call = capture.call_args
    return call[1]["prompt"] if call[1] else ""


class TestSection4CountsOnlyTheSpeakersMoves:
    def test_a_reported_diagnosis_is_not_in_the_speaker_count(self):
        report = DeepSynthesisReport()
        report.argument_map = [
            ArgumentMapEntry(arg_id="arg_1", description="Une unité du texte.")
        ]
        report.fallacy_diagnoses = [
            _diagnosis("f1", "Ad Hominem"),
            _diagnosis("f2", "Obstruction", "reported", "l'opposant"),
        ]
        prompt = _section4_prompt(report)
        assert "Fallacies: 1. " in prompt
        assert "Key fallacy families: Ad Hominem. " in prompt
        assert "Reported moves" in prompt
        assert "1; party: l'opposant. Families: Obstruction." in prompt

    def test_the_family_rows_are_deterministic(self):
        report = DeepSynthesisReport()
        report.argument_map = [
            ArgumentMapEntry(arg_id="arg_1", description="Une unité du texte.")
        ]
        # insertion order reversed vs alphabetical — the row must sort
        report.fallacy_diagnoses = [
            _diagnosis("f1", "Slippery Slope"),
            _diagnosis("f2", "Ad Hominem"),
        ]
        prompt = _section4_prompt(report)
        assert "Key fallacy families: Ad Hominem, Slippery Slope. " in prompt

    def test_a_reported_only_report_has_no_speaker_fallacy_and_still_names_it(self):
        report = DeepSynthesisReport()
        report.argument_map = [
            ArgumentMapEntry(arg_id="arg_1", description="Une unité du texte.")
        ]
        report.fallacy_diagnoses = [
            _diagnosis("f1", "Obstruction", "reported", "l'opposant")
        ]
        prompt = _section4_prompt(report)
        assert "Fallacies: 0. " in prompt
        assert "Reported moves" in prompt


# --- Act III: weak points, count, and surfacing --------------------------


def _act3_state(fallacies):
    return SimpleNamespace(
        identified_arguments={_TARGET: "Une unité du texte."},
        identified_fallacies=fallacies,
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )


class TestAct3DoesNotFileAReportedMoveAsTheSpeakersWeakness:
    def test_a_reported_move_is_no_weak_point(self):
        points = _collect_weak_points({"f1": _record(move_author="reported")}, {}, 0, 0)
        assert [p.source for p in points] == []

    def test_a_speaker_move_still_is_a_weak_point(self):
        points = _collect_weak_points({"f1": _record()}, {}, 0, 0)
        assert [p.source for p in points] == ["fallacy"]

    def test_the_evidence_keeps_the_reported_count_apart(self):
        evidence = build_act3_evidence(
            _act3_state(
                {"f1": _record(move_author="reported", move_author_label="l'opposant")}
            )
        )
        assert evidence.fallacies_total == 0
        assert evidence.reported_fallacies_total == 1
        assert [p.source for p in evidence.weak_points] == []

    @pytest.mark.parametrize("overrides", [{}, {"move_author": "unknown"}])
    def test_absent_or_invalid_keeps_the_speaker_count(self, overrides):
        evidence = build_act3_evidence(_act3_state({"f1": _record(**overrides)}))
        assert evidence.fallacies_total == 1
        assert evidence.reported_fallacies_total == 0

    def test_the_prompt_surfaces_the_reported_move(self):
        evidence = build_act3_evidence(
            _act3_state({"f1": _record(move_author="reported")})
        )
        prompt = build_act3_prompt(evidence)
        assert "SOPHISMES RAPPORTÉS" in prompt
        assert "1 sophisme rapporté" in prompt

    def test_a_speaker_run_has_no_reported_block(self):
        evidence = build_act3_evidence(_act3_state({"f1": _record()}))
        assert "SOPHISMES RAPPORTÉS" not in build_act3_prompt(evidence)


# --- salience + specialist roles: the reporting unit is not contested ----


class TestTheReportingUnitIsNotContested:
    def test_salience_ignores_a_reported_target(self):
        state = SimpleNamespace(
            identified_fallacies={"f1": _record(move_author="reported")}
        )
        assert _fallacy_target_ids(state) == set()

    def test_salience_keeps_a_speaker_target(self):
        state = SimpleNamespace(
            identified_fallacies={"f1": _record(move_author="speaker")}
        )
        assert _fallacy_target_ids(state) == {_TARGET}

    def test_specialist_roles_ignore_a_reported_target(self):
        assert _fallacy_targets({"f1": _record(move_author="reported")}) == {}

    def test_specialist_roles_keep_a_speaker_target(self):
        assert _fallacy_targets({"f1": _record()}) == {_TARGET: ["Tu quoque"]}


# --- contraction targeting ------------------------------------------------


def _contraction_state(fallacies):
    calls = []

    def _add(**kwargs):
        calls.append(kwargs)

    state = SimpleNamespace(
        identified_fallacies=fallacies,
        belief_revision_results=[],
        jtms_beliefs={_TARGET: {"name": _TARGET, "valid": True}},
        add_belief_revision_result=_add,
    )
    return state, calls


class TestContractionTargetsOnlyTheSpeakersMoves:
    def test_a_reported_move_contracts_no_belief(self):
        state, calls = _contraction_state({"f1": _record(move_author="reported")})
        assert _run_belief_revision_from_state(state) is None
        assert calls == []

    def test_a_speaker_move_still_contracts(self):
        state, calls = _contraction_state({"f1": _record(move_author="speaker")})
        result = _run_belief_revision_from_state(state)
        assert result is not None
        assert result["method"] == "fallacy_contraction"
        assert calls, "the contraction result must be persisted"

    def test_absent_move_author_contracts_like_before(self):
        state, calls = _contraction_state({"f1": _record()})
        assert _run_belief_revision_from_state(state) is not None
        assert calls


# --- Act II contract (regression of the shared predicate there) ----------


class TestAct2ReadsTheSharedPredicate:
    def test_invalid_value_stays_the_speakers_move(self):
        evidence = build_act2_evidence(
            SimpleNamespace(
                propositional_analysis_results=None,
                fol_analysis_results=None,
                modal_analysis_results=None,
                identified_arguments={_TARGET: {"id": _TARGET}},
                identified_fallacies={"f1": _record(move_author="unknown")},
            )
        )
        assert evidence.fallacies_total == 1
        assert evidence.reported_fallacies == []
