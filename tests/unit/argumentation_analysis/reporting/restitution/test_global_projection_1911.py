"""#1911 — the global synthesis's structured findings reach Acts II/III.

The projection channel: ``global_projection.project_global_findings`` derives
bounded, cited findings (cross-axis convergences + deep-synthesis value gates)
from lower-level state; both acts carry them into their conducted prompts.

What these tests pin (#1911 DoD):

* the schema — every finding is a named kind with non-empty anchors, never a
  text blob, never a boolean;
* traceability — a convergence cites the argument AND the independent methods;
* the measurable difference — same lower-level state ± the flagged axes yields
  prompts that differ substantively (an anchored convergence line vs the honest
  absence line), not decoratively;
* the budget — the rendered section stays bounded whatever the corpus size.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import global_projection as gp
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)


def _flagged_state() -> SimpleNamespace:
    """Synthetic state (privacy HARD — opaque ids, no corpus tokens) where
    arg_7 is flagged by THREE independent methods (fallacy, low quality,
    counter-argument) while arg_1 is clean, and the deep synthesis left its
    value gates in the workflow bag."""
    return SimpleNamespace(
        identified_arguments={"arg_1": "these clean", "arg_7": "these weak"},
        identified_fallacies={
            "f1": {"target_argument_id": "arg_7", "type": "ad_hominem"}
        },
        argument_quality_scores={"arg_7": {"overall": 3.0}},
        counter_arguments=[{"target_arg_id": "arg_7", "counter_content": "c"}],
        jtms_beliefs={},
        dung_frameworks={},
        workflow_results={"deep_synthesis_value_gates": {"VG1": True, "VG2": False}},
    )


def _clean_state() -> SimpleNamespace:
    """Same shape, no signal: no finding may emerge (honest absence)."""
    return SimpleNamespace(
        identified_arguments={"arg_1": "these clean"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        workflow_results={},
    )


class TestSchema:
    def test_every_finding_cites_its_anchors(self):
        findings = gp.project_global_findings(_flagged_state())
        assert findings, "fixture must produce findings"
        for f in findings:
            assert f.kind in ("convergence", "gate")
            assert f.cites, f"a {f.kind} finding without anchors is untraceable"
            assert f.statement

    def test_not_a_boolean_not_a_blob(self):
        for f in gp.project_global_findings(_flagged_state()):
            assert isinstance(f, gp.GlobalFinding)
            assert len(f.statement) <= gp._STATEMENT_CAP


class TestTraceability:
    def test_convergence_cites_argument_and_methods(self):
        findings = gp.project_global_findings(_flagged_state())
        conv = [f for f in findings if f.kind == "convergence"]
        assert len(conv) == 1
        f = conv[0]
        assert "arg_7" in f.cites
        # three independent methods flagged the argument; the finding must name
        # at least the methods, not just the count
        methods = [c for c in f.cites if c != "arg_7"]
        assert len(methods) >= 2
        assert "arg_1" not in f.cites, "a clean argument must not be cited"

    def test_gates_come_from_the_deep_synthesis_ledger(self):
        findings = gp.project_global_findings(_flagged_state())
        gates = {f.cites[0]: f for f in findings if f.kind == "gate"}
        assert set(gates) == {"VG1", "VG2"}
        assert "True" in gates["VG1"].statement
        assert "False" in gates["VG2"].statement

    def test_no_workflow_bag_no_gates(self):
        state = _flagged_state()
        state.workflow_results = {}
        kinds = {f.kind for f in gp.project_global_findings(state)}
        assert "gate" not in kinds


class TestHonestAbsence:
    def test_clean_state_yields_no_findings(self):
        assert gp.project_global_findings(_clean_state()) == []

    def test_single_signal_is_not_a_global_finding(self):
        # One method flagging an argument is an axis result the acts already
        # carry through their per-axis extractors — the projection must not
        # re-badge it as global convergence.
        state = _flagged_state()
        state.argument_quality_scores = {}
        state.counter_arguments = []
        kinds = {f.kind for f in gp.project_global_findings(state)}
        assert "convergence" not in kinds


class TestBudget:
    def test_convergences_are_capped(self):
        args = {f"arg_{i}": "weak" for i in range(20)}
        state = SimpleNamespace(
            identified_arguments=args,
            identified_fallacies={
                f"f{i}": {"target_argument_id": f"arg_{i}", "type": "ad_hominem"}
                for i in range(20)
            },
            argument_quality_scores={f"arg_{i}": {"overall": 2.0} for i in range(20)},
            counter_arguments=[],
            jtms_beliefs={},
            dung_frameworks={},
            workflow_results={},
        )
        findings = gp.project_global_findings(state)
        conv = [f for f in findings if f.kind == "convergence"]
        assert len(conv) == gp._MAX_CONVERGENCE_FINDINGS
        # each rendered line stays one bounded line
        for f in findings:
            assert len(f.statement) <= gp._STATEMENT_CAP


class TestActsConsumeTheProjection:
    def test_act3_evidence_and_prompt_carry_the_projection(self):
        evidence = build_act3_evidence(_flagged_state())
        assert evidence.global_findings, "the collector must run on the state"
        prompt = build_act3_prompt(evidence)
        assert "CONVERGENCES GLOBALES" in prompt
        assert "arg_7" in prompt
        assert "ancres" in prompt

    def test_act2_evidence_and_prompt_carry_the_projection(self):
        evidence = build_act2_evidence(_flagged_state())
        assert evidence.global_findings
        prompt = build_act2_prompt(evidence)
        assert "CONVERGENCES GLOBALES" in prompt
        assert "arg_7" in prompt

    def test_difference_is_substantive_not_decorative(self):
        """The DoD pair: same shape ± the flagged axes.

        The flagged-state prompt carries the anchored convergence line (the
        argument id + the independent methods) and the honest-absence variant
        does not; the clean prompt instead carries the explicit absence line.
        That is a difference in what the conclusion can CLAIM, not a
        decorative « a synthesis exists » sentence.
        """
        flagged = build_act3_prompt(build_act3_evidence(_flagged_state()))
        clean = build_act3_prompt(build_act3_evidence(_clean_state()))
        assert "arg_7" in flagged
        assert "méthodes indépendantes convergent" in flagged
        assert "arg_7" not in clean
        assert "aucune convergence inter-axes" in clean

    def test_prompt_section_stays_bounded(self):
        evidence = build_act3_evidence(_flagged_state())
        section = "\n".join(f.statement for f in evidence.global_findings)
        assert len(section) <= 6 * gp._STATEMENT_CAP
