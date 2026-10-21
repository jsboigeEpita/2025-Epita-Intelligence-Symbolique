"""setup-projet-is provisions the CMUdict corpus CI-side (#3093 volet A).

The readability instruments read the NLTK CMUdict corpus (Flesch EN syllable
counts). It is not a conda package, so ``conda-lock.yml`` cannot carry it, and
a runtime ``nltk.download`` in every process is the defect #3093 repairs: it
costs a network round-trip per process and silently degrades when the runner
is offline. The corpus is provisioned once per runner, in the setup action,
right after the env it belongs to exists.

These tests read ``action.yml`` as data — no network, no conda, no nltk — and
make the step's removal (or a regression to a non-idempotent form) red in the
gate.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ACTION = (
    Path(__file__).resolve().parents[2]
    / ".github"
    / "actions"
    / "setup-projet-is"
    / "action.yml"
)


def _cmudict_step() -> dict:
    doc = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    steps = doc["runs"]["steps"]
    for step in steps:
        if "CMUdict" in (step.get("name") or ""):
            return step
    raise AssertionError(
        "no CMUdict provisioning step in setup-projet-is (#3093): the "
        "readability instruments degrade on every CI runner without it"
    )


def test_the_step_exists_after_the_env_install():
    doc = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    names = [s.get("name") or "" for s in doc["runs"]["steps"]]
    install = next(i for i, n in enumerate(names) if "conda-lock.yml" in n)
    provision = next(i for i, n in enumerate(names) if "CMUdict" in n)
    assert provision > install, (
        "the corpus is provisioned after the env that imports nltk exists — "
        "a step before the install has no python to probe with"
    )


def test_the_step_is_idempotent_presence_before_download():
    run = _cmudict_step()["run"]
    probe = run.find("nltk.data.find")
    download = run.find("nltk.download")
    assert (
        probe != -1 and download != -1
    ), "the step must both probe presence and download on absence (#3093)"
    assert probe < download, (
        "the probe must run first: an already-provisioned runner costs one "
        "log line, not a re-download on every job"
    )


def test_the_step_uses_the_env_ci_tests_run_in():
    run = _cmudict_step()["run"]
    assert "conda run -n projet-is" in run, (
        "the probe and the download must run in projet-is — the env the gate "
        "tests import nltk from; another env would provision a corpus the "
        "tests never see"
    )
