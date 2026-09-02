"""#1983 — parity oracle for the ``designate`` runtime-export contract.

The external analysis (relay 2026-09-01) proposed replacing "reuse EPITA"
with a tiny runtime-export contract around six operations; this issue opens
ONLY the first, ``designate``. This module is the oracle half: a spec
(``argumentation_analysis/evaluation/designate_contract.py``) plus an
extraction of the four issue-numbered ground-truth tests, each assertion
pointing to the test it was derived from.

DoD coverage:
- [ ] spec executable (module docstring + injectable checks)
- [ ] parity oracle derived from the 4 tests, each assertion pointing at its
      source test
- [ ] oracle passes against the current implementation WITHOUT modifying it
- [ ] negative control: the oracle reddens on a degraded implementation
      (designation without motivation, or without backfill)
- [ ] no autonomous implementation in this issue
"""

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.designate_contract import (
    assess_designate_motivation_mirror,
    assess_designate_room_policy,
    assess_designate_subject,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)


def _state():
    return UnifiedAnalysisState("Texte argumentatif de test.")


def _tactical():
    return TacticalState()


# ---------------------------------------------------------------------------
# Oracle passes against the CURRENT implementation, unchanged
# ---------------------------------------------------------------------------


class TestOraclePassesAgainstCurrentImplementation:
    """The oracle is an extraction, not a rewrite — it must be green here."""

    def test_convc_subject_checks_all_pass(self):
        assessment = assess_designate_subject(_state)
        assert assessment.passed, (
            "the designate contract oracle must pass against the current "
            f"shared_state.py; failed: {[c.observable for c in assessment.failed]}"
        )
        assert len(assessment.checks) >= 9

    def test_every_convc_check_points_at_a_ground_truth_test(self):
        assessment = assess_designate_subject(_state)
        for check in assessment.checks:
            assert check.test_source.startswith(
                "tests/unit/argumentation_analysis/"
            ), f"check {check.observable} does not cite its source test: {check.test_source}"

    def test_tactical_mirror_checks_all_pass(self):
        assessment = assess_designate_motivation_mirror(_tactical)
        assert assessment.passed, (
            f"the tactical motivated-designation mirror must pass; failed: "
            f"{[c.observable for c in assessment.failed]}"
        )

    def test_room_policy_checks_all_pass(self):
        assessment = assess_designate_room_policy()
        assert assessment.passed, (
            f"the room-policy checks must pass; failed: "
            f"{[c.observable for c in assessment.failed]}"
        )


# ---------------------------------------------------------------------------
# Negative control: a degraded implementation must make the oracle redden
# ---------------------------------------------------------------------------


class _NoMotivationState(UnifiedAnalysisState):
    """Degraded implementation: ``record_designation`` drops the motivation.

    The "why" of the designation is lost — the exact defect the motivated-
    designation requirement (CONV-C + tactical mirror #1735) forbids.
    """

    def record_designation(self, agent, motivation, trigger, turn=None):
        return super().record_designation(agent, "", trigger, turn=turn)


class _NoBackfillState(UnifiedAnalysisState):
    """Degraded implementation: ``backfill_last_designation_for`` lies.

    It claims to have closed the record (returns True) but never writes
    ``state_fingerprint_after``/``delta_summary``, so the audit cannot tell
    whether the designated agent actually returned.
    """

    def backfill_last_designation_for(self, agent):
        return True


class TestOracleReddensOnDegradedImplementation:
    """Without this the oracle is a tautology: it must *detect* the defect."""

    def test_reddens_on_designation_without_motivation(self):
        assessment = assess_designate_subject(lambda: _NoMotivationState("Texte."))
        failed = {c.observable for c in assessment.failed}
        assert not assessment.passed, (
            "the oracle did not redden on a designation recorded WITHOUT its "
            "motivation — the motivation check is not discriminating"
        )
        assert (
            "designation_motivation_carried" in failed
        ), f"the motivation check must be the one that reddens, failed: {sorted(failed)}"

    def test_reddens_on_designation_without_backfill(self):
        assessment = assess_designate_subject(lambda: _NoBackfillState("Texte."))
        failed = {c.observable for c in assessment.failed}
        assert not assessment.passed, (
            "the oracle did not redden on a designation whose backfill never "
            "closes the record — the backfill checks are not discriminating"
        )
        assert any(
            obs.startswith("designation_backfill_") for obs in failed
        ), f"a backfill check must redden, failed: {sorted(failed)}"
