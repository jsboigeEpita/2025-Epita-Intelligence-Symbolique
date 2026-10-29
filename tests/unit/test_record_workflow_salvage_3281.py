"""A failed record run must not discard what it paid for (#3281).

Record run 40668986102 spent 17 min and 637 real requests, failed on 3
tests, and skipped both the export and the cost step: the diskcache DB
died with the runner and the spend left nothing behind. Second occurrence
(40607307597 first), so the shape is a defect, not an accident.

The user-approved fix (issue #3281, comment c6504768201) salvages the
artifacts without weakening anything: the export and cost steps run
``if: always()`` — no ``continue-on-error`` anywhere, so a red record step
still fails the job and a red privacy audit on a green run still blocks —
and the optional cassettes-PR step only fires when the record step itself
succeeded, because partial cassettes are never automatically admitted
(the artifact is the deliverable; admission stays a human decision).

This guard pins those four properties on the parsed workflow so a future
edit cannot quietly retire the salvage.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RECORD_YML = ROOT / ".github" / "workflows" / "record-llm-cassettes.yml"

RECORD_STEP = "Record run (bills real API usage)"
EXPORT_STEP = "Export cassettes + blocking privacy audit"
COST_STEP = "Cost artifact + fail-loud token cap"
PR_STEP = "Open cassettes PR (optional, needs CASSETTES_PR_TOKEN)"


def _steps() -> dict:
    workflow = yaml.safe_load(RECORD_YML.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    assert len(jobs) == 1, f"expected one job, found {sorted(jobs)}"
    (job,) = jobs.values()
    return {s["name"]: s for s in job["steps"]}


class TestSalvageAfterFailedRecord:
    def test_export_and_cost_run_regardless_of_the_record_outcome(self):
        steps = _steps()
        assert steps[EXPORT_STEP]["if"] == "always()", (
            "the export step must run after a failed record run (#3281): "
            "skipping it discards the paid DB with the runner"
        )
        assert steps[COST_STEP]["if"] == "always()", (
            "the cost step must run after a failed record run (#3281): "
            "without it the run's spend is unmeasured"
        )

    def test_the_record_step_is_addressable_by_id(self):
        steps = _steps()
        assert steps[RECORD_STEP]["id"] == "record", (
            "the salvage gates read steps.record.outcome; the record step "
            "must carry id: record"
        )

    def test_no_step_swallows_its_failure(self):
        for name, step in _steps().items():
            assert "continue-on-error" not in step, (
                f"step {name!r} sets continue-on-error: a failed record run "
                "must keep failing the job, and a failed privacy audit on a "
                "green run must keep blocking it (#3281, user scope)"
            )

    def test_partial_cassettes_never_open_a_pr_by_themselves(self):
        steps = _steps()
        condition = steps[PR_STEP]["if"]
        assert condition == "always() && steps.record.outcome == 'success'", (
            "the cassettes-PR step must fire only on a successful record "
            "run: partial cassettes are not automatically admitted (#3281)"
        )

    def test_the_export_never_skips_the_privacy_audit(self):
        script = _steps()[EXPORT_STEP]["run"]
        assert "--skip-audit" not in script, (
            "the salvage must not buy itself a skipped privacy audit (#1603)"
        )
