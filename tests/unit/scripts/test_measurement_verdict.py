"""Tri-état du verdict CI (#1799) — la forme du run 32116717942 doit rendre PAS-MESURÉ.

Le défaut : ``automated-tests`` conclus ``FAILURE`` alors qu'aucun test n'a
tourné (Setup Miniconda coupé à 15 min). Un lecteur du rollup ne peut pas
distinguer « mesuré et rouge » de « pas mesuré ». Ces tests épinglent le
classement sur des payloads de jobs **synthétiques reproduisant les formes
mesurées** — aucun réseau, aucun gh requis.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.ci.measurement_verdict import (
    EXIT_CODES,
    MEASURED_FAIL,
    MEASURED_PASS,
    NOT_APPLICABLE,
    NOT_MEASURED,
    classify_job,
    verdict_from_jobs,
)


def _job(name, conclusion, steps, status="completed"):
    return {
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "steps": [
            {"name": n, "status": "completed", "conclusion": c} for n, c in steps
        ],
    }


# Forme mesurée du run 32116717942 (#1799) : Setup Miniconda timed_out, pytest
# jamais invoqué, garde « Generate test summary » en échec.
RUN_1799_NOT_MEASURED = [
    _job(
        "lint-and-format",
        "success",
        [("Setup Miniconda", "success"), ("Lint", "success")],
    ),
    _job(
        "automated-tests",
        "failure",
        [
            ("Checkout", "success"),
            ("Setup Miniconda", "timed_out"),
            ("Run automated tests", "skipped"),
            ("Generate test summary", "failure"),
        ],
    ),
]


class TestNotMeasured:
    def test_provisioning_timeout_is_not_a_test_verdict(self):
        """Born-red du défaut #1799 : le job est FAILURE, mais rien n'a été mesuré."""
        verdict, reason = classify_job(RUN_1799_NOT_MEASURED[1])
        assert verdict == NOT_MEASURED, reason
        assert "approvisionnement" in reason

    def test_overall_verdict_is_not_measured_and_exit_code_is_2(self):
        overall, rows = verdict_from_jobs(RUN_1799_NOT_MEASURED)
        assert overall == NOT_MEASURED
        assert EXIT_CODES[NOT_MEASURED] == 2
        assert (
            rows[0][1] == "not-applicable"
        )  # lint: hors périmètre, ni pass ni pas-mesuré

    def test_guard_failure_without_measurement_step_is_not_measured(self):
        """Le garde fail-loud (aucun rapport de test) est un PAS-MESURÉ, pas un verdict."""
        job = _job(
            "automated-tests",
            "failure",
            [("Setup Miniconda", "success"), ("Generate test summary", "failure")],
        )
        verdict, reason = classify_job(job)
        assert verdict == NOT_MEASURED
        assert "fail-loud" in reason

    def test_skipped_job_is_not_measured(self):
        verdict, _ = classify_job(
            {
                "name": "automated-tests",
                "status": "skipped",
                "conclusion": "skipped",
                "steps": [],
            }
        )
        assert verdict == NOT_MEASURED

    def test_green_job_that_ran_nothing_is_not_measured(self):
        """Anti-théâtre : vert par vacuité n'est pas un pass."""
        job = _job("automated-tests", "success", [("Checkout", "success")])
        verdict, reason = classify_job(job)
        assert verdict == NOT_MEASURED
        assert "vacuité" in reason


class TestMeasuredVerdicts:
    def test_real_test_failure_is_measured_fail(self):
        job = _job(
            "automated-tests",
            "failure",
            [
                ("Setup Miniconda", "success"),
                ("Run automated tests", "failure"),
                ("Generate test summary", "success"),
            ],
        )
        verdict, reason = classify_job(job)
        assert verdict == MEASURED_FAIL
        assert "verdict de code réel" in reason

    def test_all_green_is_measured_pass(self):
        overall, _ = verdict_from_jobs(
            [
                _job("lint-and-format", "success", [("Lint", "success")]),
                _job(
                    "automated-tests",
                    "success",
                    [
                        ("Setup Miniconda", "success"),
                        ("Run automated tests", "success"),
                    ],
                ),
            ]
        )
        assert overall == MEASURED_PASS
        assert EXIT_CODES[MEASURED_PASS] == 0

    def test_measured_fail_dominates_not_measured_in_overall(self):
        """Un vrai échec de tests l'emporte : c'est le seul verdict qui parle du code."""
        overall, _ = verdict_from_jobs(
            RUN_1799_NOT_MEASURED
            + [
                _job(
                    "integration",
                    "failure",
                    [("Run automated tests", "failure")],
                )
            ]
        )
        assert overall == MEASURED_FAIL
