"""#2928 — the Dung-arbitration stage joins the spectacular workflow as a statement.

Coordinator decision (13/11, on the cycle-6 measurement: 8 of 9 documents
carry contested detections): the stage joins spectacular WITHOUT the neural
tier, every detection stays in the report, and the act sentence says which
detections a rival family contests on the same unit, and which of these
contests the stage leaves undecided. Its witness on the cycle-6 states: the
report lists the same number of detections with and without the stage.

What this file pins:

- the spectacular workflow declares the phase, scoped ON through the
  ``parameters`` overlay — the callable's default stays OFF, so no other
  invocation of the capability changes behavior;
- the executor overlay: a phase's ``parameters`` reach ITS invoke merged as
  a copy, and a LATER phase's invoke does not see them (no leak into the
  shared ctx) — the channel used to be assigned and never read;
- the stage output carries candidate provenance (id → family + target
  unit), so a render can name families and units instead of opaque ids;
- the state writer persists it beside the verdict;
- ``native_dung.arbitration_note`` renders the coordinator's sentence —
  decided contests, undecided contests, honest absence — and returns ""
  on a state whose stage never ran (or ran OFF): byte-identical prompt,
  the issue's control;
- Act II carries the note, and the statement is PURELY ADDITIVE: with the
  stage's framework added to a state, every other evidence field is
  unchanged — the report lists the same detections (the issue's witness,
  at evidence level).
"""

from __future__ import annotations

import asyncio
from dataclasses import fields
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseStatus,
    WorkflowBuilder,
    WorkflowExecutor,
)

# ============================================================================
# Helpers
# ============================================================================


class _FakeRegistration:
    """Mimics ComponentRegistration for the executor tests."""

    def __init__(self, name: str, invoke: Any) -> None:
        self.name = name
        self.invoke = invoke


def _registry(*caps: Any) -> MagicMock:
    registry = MagicMock()
    mapping: Dict[str, List[_FakeRegistration]] = {}
    for cap, name, fn in caps:
        mapping.setdefault(cap, []).append(_FakeRegistration(name, fn))
    registry.find_for_capability = MagicMock(
        side_effect=lambda cap: mapping.get(cap, [])
    )
    return registry


def _capturing_invoke(sink: List[Dict[str, Any]]):
    async def invoke(inp: Any, ctx: Dict[str, Any]) -> Dict[str, Any]:
        sink.append(dict(ctx))
        return {"ok": True}

    return invoke


#: Two anchored detections on the SAME unit (``arg_3``), different families
#: and confidences — the rivalry shape the stage arbitrates. Families are
#: taxonomy vocabulary, targets are opaque unit ids: never corpus text.
_RIVAL_DETECTIONS: List[Dict[str, Any]] = [
    {
        "fallacy_type": "ad_hominem",
        "target_argument": "arg_3",
        "confidence": 0.9,
    },
    {
        "fallacy_type": "appeal_to_authority",
        "target_argument": "arg_3",
        "confidence": 0.4,
    },
]


def _hierarchical_output() -> Dict[str, Any]:
    return {
        "extraction_method": "per_argument",
        "per_argument_fallacies": [dict(d) for d in _RIVAL_DETECTIONS],
    }


#: The framework the writer files for a DECIDED contest on ``arg_3``
#: (higher-confidence family survives, rival is set aside).
_DECIDED_FRAMEWORK = {
    "name": "dung_arbitration",
    "arguments": ["per_argument_0", "per_argument_1"],
    "attacks": [["per_argument_0", "per_argument_1"]],
    "extensions": {
        "enabled": True,
        "honest_absent": False,
        "surviving_ids": ["per_argument_0"],
        "eliminated_ids": {"per_argument_1": "per_argument_0"},
        "input_count": 2,
        "surviving_count": 1,
        "candidates_provenance": [
            {
                "id": "per_argument_0",
                "family": "ad_hominem",
                "target_argument": "arg_3",
            },
            {
                "id": "per_argument_1",
                "family": "appeal_to_authority",
                "target_argument": "arg_3",
            },
        ],
    },
}


#: Same rivalry, both candidates survive the grounded extension.
_UNDECIDED_FRAMEWORK = {
    **_DECIDED_FRAMEWORK,
    "extensions": {
        **_DECIDED_FRAMEWORK["extensions"],
        "surviving_ids": ["per_argument_0", "per_argument_1"],
        "eliminated_ids": {},
        "surviving_count": 2,
    },
}


def _state_with(framework: Dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(dung_frameworks={"dung_1": framework})


# ============================================================================
# The workflow declares the phase — statement, never a filter
# ============================================================================


class TestSpectacularDeclaresThePhase:
    def test_the_phase_is_declared_scoped_on_and_optional(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        phase = build_spectacular_workflow().get_phase("dung_arbitration")

        assert phase is not None, "spectacular must declare dung_arbitration"
        assert phase.capability == "dung_arbitration"
        # Its only source is the hierarchical pass's per-argument detections
        # — the stage joins WITHOUT the neural tier.
        assert "hierarchical_fallacy" in phase.depends_on
        assert phase.optional is True
        # Scoped ON through the overlay: the callable's default stays OFF.
        assert phase.parameters == {"dung_arbitration": True}

    def test_no_other_phase_gains_parameters(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        others = [
            p.name
            for p in build_spectacular_workflow().phases
            if p.name != "dung_arbitration" and p.parameters
        ]
        assert others == [], f"unexpected overlay on {others}"


# ============================================================================
# The executor overlay — parameters reach the invoke, scoped to the phase
# ============================================================================


class TestTheParametersOverlay:
    async def test_a_phase_parameters_reach_its_invoke(self):
        seen: List[Dict[str, Any]] = []
        registry = _registry(("cap_x", "prov_x", _capturing_invoke(seen)))
        wf = (
            WorkflowBuilder("overlay_on")
            .add_phase("p1", capability="cap_x", parameters={"dung_arbitration": True})
            .build()
        )

        results = await WorkflowExecutor(registry).execute(wf, input_data="t")

        assert results["p1"].status == PhaseStatus.COMPLETED
        assert len(seen) == 1
        assert seen[0].get("dung_arbitration") is True

    async def test_a_later_phase_does_not_see_the_overlay(self):
        seen: List[Dict[str, Any]] = []
        registry = _registry(
            ("cap_x", "prov_x", _capturing_invoke(seen)),
            ("cap_y", "prov_y", _capturing_invoke(seen)),
        )
        wf = (
            WorkflowBuilder("overlay_leak")
            .add_phase("p1", capability="cap_x", parameters={"dung_arbitration": True})
            .add_phase("p2", capability="cap_y", depends_on=["p1"])
            .build()
        )

        await WorkflowExecutor(registry).execute(wf, input_data="t")

        by_presence = [ctx.get("dung_arbitration") for ctx in seen]
        assert by_presence == [True, None], (
            "the selector must be scoped to p1's invoke — no leak into the "
            "shared ctx a later phase reads"
        )


# ============================================================================
# Provenance — the verdict speaks in ids, the render names families and units
# ============================================================================


class TestTheStageCarriesProvenance:
    async def test_the_output_joins_candidate_ids_to_families_and_units(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_dung_arbitration,
        )

        out = await _invoke_dung_arbitration(
            "",
            {
                "dung_arbitration": True,
                "phase_hierarchical_fallacy_output": _hierarchical_output(),
            },
        )

        prov = out["candidates_provenance"]
        assert {p["id"] for p in prov} == {"per_argument_0", "per_argument_1"}
        by_id = {p["id"]: p for p in prov}
        assert by_id["per_argument_0"]["family"] == "ad_hominem"
        assert by_id["per_argument_1"]["family"] == "appeal_to_authority"
        assert by_id["per_argument_0"]["target_argument"] == "arg_3"
        assert by_id["per_argument_1"]["target_argument"] == "arg_3"
        # The rivalry fired on the shared unit — the stage had something to
        # arbitrate (the statement is not rendered over an honest-absent run).
        assert out["verdict"]["attacks"]

    async def test_a_second_detection_batch_keeps_the_join_honest(self):
        """The join is made only while candidates == the single source batch."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_dung_arbitration,
        )

        out = await _invoke_dung_arbitration("", {"dung_arbitration": False})

        assert out["candidates_provenance"] == []


class TestTheWriterPersistsProvenance:
    def test_the_framework_extensions_carry_the_join(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_dung_arbitration_to_state,
        )

        captured: Dict[str, Any] = {}

        def add_dung_framework(**kwargs: Any) -> str:
            captured.update(kwargs)
            return "dung_1"

        def add_trace_entry(**kwargs: Any) -> None:
            return None

        state = SimpleNamespace(
            add_dung_framework=add_dung_framework,
            add_trace_entry=add_trace_entry,
        )
        output = {
            "verdict": {
                "enabled": True,
                "surviving_ids": ["per_argument_0"],
                "eliminated_ids": {"per_argument_1": "per_argument_0"},
                "attacks": [["per_argument_0", "per_argument_1"]],
                "honest_absent": False,
                "input_count": 2,
                "surviving_count": 1,
            },
            "candidates_provenance": [
                {
                    "id": "per_argument_0",
                    "family": "ad_hominem",
                    "target_argument": "arg_3",
                },
                {
                    "id": "per_argument_1",
                    "family": "appeal_to_authority",
                    "target_argument": "arg_3",
                },
            ],
        }

        _write_dung_arbitration_to_state(output, state, {})

        prov = captured["extensions"]["candidates_provenance"]
        assert {p["id"] for p in prov} == {"per_argument_0", "per_argument_1"}
        assert prov[0]["family"] == "ad_hominem"
        assert prov[0]["target_argument"] == "arg_3"


# ============================================================================
# The note — the coordinator's sentence, and its honest absences
# ============================================================================


class TestTheNoteRendersTheStatement:
    """Imports live INSIDE each test so the file collects on ``main``: the
    feature tests redden on the missing symbol while the control arm stays
    green there — the born-red measurement keeps its controls."""

    def test_a_decided_contest_names_the_families_the_unit_and_the_outcome(self):
        from argumentation_analysis.reporting.restitution.native_dung import (
            arbitration_note,
        )

        note = arbitration_note(_state_with(_DECIDED_FRAMEWORK))

        assert "ARBITRAGE DUNG" in note
        assert "éclairage" in note and "JAMAIS un filtre" in note
        assert "ad_hominem" in note and "appeal_to_authority" in note
        assert "arg_3" in note
        # Decided: the grounded extension set the rival aside — and the
        # set-aside detection STAYS in the report (statement, not filter).
        assert "écarte appeal_to_authority" in note
        assert "au bénéfice de ad_hominem" in note
        assert "RESTE dans le rapport" in note

    def test_an_undecided_contest_is_named_as_undecided(self):
        from argumentation_analysis.reporting.restitution.native_dung import (
            arbitration_note,
        )

        note = arbitration_note(_state_with(_UNDECIDED_FRAMEWORK))

        assert "INDÉCIDÉ" in note
        assert "ad_hominem" in note and "appeal_to_authority" in note
        assert "écarte" not in note

    def test_a_symmetric_attack_pair_is_one_contest(self):
        from argumentation_analysis.reporting.restitution.native_dung import (
            arbitration_note,
        )

        fw = {
            **_DECIDED_FRAMEWORK,
            "attacks": [
                ["per_argument_0", "per_argument_1"],
                ["per_argument_1", "per_argument_0"],
            ],
        }

        note = arbitration_note(_state_with(fw))

        assert note.count("•") == 1, "a mutual rivalry is ONE contest, one line"

    def test_honest_absence_renders_one_line(self):
        from argumentation_analysis.reporting.restitution.native_dung import (
            arbitration_note,
        )

        fw = {
            **_DECIDED_FRAMEWORK,
            "attacks": [],
            "extensions": {
                **_DECIDED_FRAMEWORK["extensions"],
                "honest_absent": True,
                "surviving_ids": ["per_argument_0", "per_argument_1"],
                "eliminated_ids": {},
            },
        }

        note = arbitration_note(_state_with(fw))

        assert "aucune famille rivale ne conteste" in note
        assert "toutes les détections restent dans le rapport" in note


class TestTheNoteHonestAbsences:
    def test_a_state_whose_stage_never_ran_renders_nothing(self):
        from argumentation_analysis.reporting.restitution.native_dung import (
            arbitration_note,
        )

        # A pre-#2928 state: only another formalism's framework, or none.
        assert arbitration_note(SimpleNamespace(dung_frameworks={})) == ""
        assert (
            arbitration_note(
                SimpleNamespace(
                    dung_frameworks={
                        "dung_1": {"name": "verification_grounded", "extensions": {}}
                    }
                )
            )
            == ""
        )

    def test_a_disabled_stage_renders_nothing(self):
        from argumentation_analysis.reporting.restitution.native_dung import (
            arbitration_note,
        )

        fw = {
            **_DECIDED_FRAMEWORK,
            "extensions": {**_DECIDED_FRAMEWORK["extensions"], "enabled": False},
        }

        assert arbitration_note(_state_with(fw)) == ""


# ============================================================================
# Act II carries the note — and the statement is purely additive
# ============================================================================


def _act2_state(dung_frameworks: Dict[str, Any]) -> SimpleNamespace:
    """A minimal Act II state with the rivalry shape: one unit, two rival
    detections. Invented text, taxonomy vocabulary, opaque ids."""
    return SimpleNamespace(
        identified_arguments={
            "arg_3": {
                "text": "Une unité synthétique, inventée de toutes pièces.",
                "start": 0,
                "end": 44,
            }
        },
        identified_fallacies={
            "f_1": {
                "target_argument_id": "arg_3",
                "type": "ad_hominem",
                "family": "ad_hominem",
                "justification": "Un justificatif synthétique.",
                "confidence": 0.9,
            },
            "f_2": {
                "target_argument_id": "arg_3",
                "type": "appeal_to_authority",
                "family": "appeal_to_authority",
                "justification": "Un second justificatif synthétique.",
                "confidence": 0.4,
            },
        },
        dung_frameworks=dung_frameworks,
    )


class TestActTwoCarriesTheStatement:
    def test_the_evidence_and_prompt_carry_the_note(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )

        evidence = build_act2_evidence(_act2_state({"dung_1": _DECIDED_FRAMEWORK}))
        prompt = build_act2_prompt(evidence)

        assert "ARBITRAGE DUNG" in evidence.dung_arbitration
        assert "appeal_to_authority" in evidence.dung_arbitration
        assert "ARBITRAGE DUNG" in prompt

    def test_without_the_stage_the_prompt_names_no_arbitration(self):
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
            build_act2_prompt,
        )

        evidence = build_act2_evidence(_act2_state({}))
        prompt = build_act2_prompt(evidence)

        # The issue's control: a stage-free state renders byte-identically —
        # the note is the ONLY thing the stage adds to the prompt.
        assert evidence.dung_arbitration == ""
        assert "ARBITRAGE DUNG" not in prompt

    def test_the_statement_is_purely_additive_the_detections_are_unchanged(self):
        """The issue's witness at evidence level: with and without the stage,
        the report carries the SAME detections — same total, same movements,
        same everything except the note itself."""
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_evidence,
        )

        without = build_act2_evidence(_act2_state({}))
        with_stage = build_act2_evidence(_act2_state({"dung_1": _DECIDED_FRAMEWORK}))

        for f in fields(without):
            if f.name == "dung_arbitration":
                assert getattr(without, f.name) == ""
                assert getattr(with_stage, f.name) != ""
                continue
            assert getattr(without, f.name) == getattr(with_stage, f.name), (
                f"the stage must not change evidence.{f.name} — it is a "
                "statement, never a filter"
            )
        # The detection count itself, the invariant the coordinator named.
        assert without.fallacies_total == with_stage.fallacies_total == 2
        assert without.reported_fallacies == with_stage.reported_fallacies == []
