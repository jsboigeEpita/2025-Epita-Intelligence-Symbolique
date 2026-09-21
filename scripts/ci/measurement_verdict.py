#!/usr/bin/env python
"""Tri-état du verdict CI : MESURÉ-PASS / MESURÉ-ÉCHEC / PAS-MESURÉ (#1799).

Le rollup nomme un job ``automated-tests`` dont le nom ne porte qu'un bit :
``FAILURE`` sert à la fois à « les tests ont tourné et ont échoué » et à « les
tests n'ont pas tourné » (Setup Miniconda dépasse son cap de 15 min, `pytest`
n'est jamais invoqué, aucun `pytest_report.xml` n'existe). Ce dernier cas est un
échec qui **n'a rien décidé** — le lire comme un verdict de code envoie
l'opérateur révéler un défaut inexistant, ou merger en contournant un flake
fantôme.

Ce script lit le RUN (pas le résumé) et rend le tri-état, avec le motif :

* ``measured-pass``   — la suite a tourné, aucun échec ;
* ``measured-fail``   — la suite a tourné, des tests ont échoué (vrai verdict) ;
* ``not-measured``   — la suite n'a PAS tourné (approvisionnement, timeout,
  garde fail-loud) : raison nommée, **pas** un verdict de code.

Sortie : une ligne par job + un verdict global ; codes de sortie
``0`` (mesuré-pass) / ``1`` (mesuré-échec) / ``2`` (pas-mesuré) — scriptable.

Le classement s'appuie exclusivement sur les **steps** du job, jamais sur son
seul ``conclusion`` : c'est la distinction step-level qui porte l'information
que le nom du check écrase.

Usage :
    python scripts/ci/measurement_verdict.py --run 32116717942
    python scripts/ci/measurement_verdict.py --jobs-json jobs.json   # hors ligne
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

MEASURED_PASS = "measured-pass"
MEASURED_FAIL = "measured-fail"
NOT_MEASURED = "not-measured"
# Un job qui ne mesure pas de tests (lint, build) n'a pas à peser sur le
# verdict : il est hors périmètre, ni pass ni pas-mesuré.
NOT_APPLICABLE = "not-applicable"

# Un step dont l'échec signifie « la mesure n'a pas eu lieu » plutôt que « la
# mesure est rouge ». Comparaison sur le nom de step normalisé.
PROVISIONING_STEPS = ("setup miniconda", "setup python", "install dependencies")
MEASUREMENT_STEPS = ("run automated tests", "run tests", "pytest")
# Le garde fail-loud du workflow (#1799, ci.yml) : il transforme une absence de
# rapport en échec explicite — donc en PAS-MESURÉ, pas en verdict de code.
GUARD_STEPS = ("generate test summary",)


def _norm(name: str) -> str:
    return (name or "").strip().lower()


def _step_outcome(step: dict) -> str:
    return (step.get("conclusion") or step.get("status") or "").lower()


def classify_job(job: dict) -> tuple[str, str]:
    """Rend (verdict, raison) pour un job de run GitHub Actions."""
    name = job.get("name", "?")
    steps = job.get("steps") or []
    conclusion = (job.get("conclusion") or "").lower()

    if conclusion in ("skipped", "cancelled") or job.get("status") == "skipped":
        return NOT_MEASURED, f"job {name!r} non exécuté (conclusion={conclusion})"

    failed_steps = [s for s in steps if _step_outcome(s) in ("failure", "timed_out")]
    measurement_ran = any(
        _norm(s.get("name")).startswith(MEASUREMENT_STEPS) for s in steps
    )
    measurement_ok = any(
        _norm(s.get("name")).startswith(MEASUREMENT_STEPS)
        and _step_outcome(s) == "success"
        for s in steps
    )

    if conclusion == "success":
        if measurement_ok or measurement_ran:
            return MEASURED_PASS, f"suite exécutée, aucun échec (job {name!r})"
        if "test" not in _norm(name):
            return NOT_APPLICABLE, f"job {name!r} ne mesure pas de tests"
        return NOT_MEASURED, (
            f"job {name!r} vert mais aucun step de mesure exécuté — vert par vacuité"
        )

    # conclusion == failure (ou autre non-succès) : QUI a échoué décide du sens.
    for step in failed_steps:
        step_name = _norm(step.get("name"))
        outcome = _step_outcome(step)
        if step_name.startswith(PROVISIONING_STEPS):
            return NOT_MEASURED, (
                f"approvisionnement échoué ({step.get('name')!r}, {outcome}) — "
                "la suite n'a pas tourné : échec qui ne décide rien du code"
            )
        if step_name.startswith(GUARD_STEPS):
            return NOT_MEASURED, (
                f"garde fail-loud déclenché ({step.get('name')!r}) — pas de "
                "rapport de test : suite non exécutée, pas échouée"
            )
        if step_name.startswith(MEASUREMENT_STEPS):
            return MEASURED_FAIL, (
                f"suite exécutée puis en échec ({step.get('name')!r}, {outcome}) "
                "— verdict de code réel"
            )
    return NOT_MEASURED, (
        f"job {name!r} en échec hors step de mesure "
        f"({[s.get('name') for s in failed_steps]}) — pas un verdict de tests"
    )


def verdict_from_jobs(jobs: list[dict]) -> tuple[str, list[tuple[str, str, str]]]:
    """Verdict global : le plus fort l'emporte (échec mesuré > pas-mesuré > pass)."""
    rows = [(j.get("name", "?"), *classify_job(j)) for j in jobs]
    verdicts = {v for _, v, _ in rows}
    verdicts.discard(NOT_APPLICABLE)  # hors périmètre : ni pass ni pas-mesuré
    if not verdicts:
        return NOT_APPLICABLE, rows
    if MEASURED_FAIL in verdicts:
        overall = MEASURED_FAIL
    elif NOT_MEASURED in verdicts:
        overall = NOT_MEASURED
    else:
        overall = MEASURED_PASS
    return overall, rows


def fetch_jobs(run_id: str) -> list[dict]:
    proc = subprocess.run(
        [
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}/jobs",
            "--jq",
            "[.jobs[] | {name, status, conclusion, steps}]",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"gh api a échoué (rc={proc.returncode}) : {proc.stderr.strip()}"
        )
    return json.loads(proc.stdout)


EXIT_CODES = {MEASURED_PASS: 0, MEASURED_FAIL: 1, NOT_MEASURED: 2, NOT_APPLICABLE: 3}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", help="identifiant de run GitHub Actions")
    group.add_argument("--jobs-json", type=Path, help="payload de jobs déjà collecté")
    args = parser.parse_args(argv)

    jobs = (
        json.loads(args.jobs_json.read_text(encoding="utf-8"))
        if args.jobs_json
        else fetch_jobs(args.run)
    )
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs", jobs)

    overall, rows = verdict_from_jobs(jobs)
    for name, verdict, reason in rows:
        print(f"{verdict:14s} {name}: {reason}")
    print(f"VERDICT GLOBAL: {overall}")
    if overall == NOT_MEASURED:
        print(
            "→ 'FAILURE' de ce run ne dit RIEN du code : ne pas le lire comme un verdict de tests."
        )
    return EXIT_CODES[overall]


if __name__ == "__main__":
    sys.exit(main())
