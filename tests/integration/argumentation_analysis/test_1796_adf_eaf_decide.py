# -*- coding: utf-8 -*-
"""#1796: the ADF and EAF axes decide instead of crashing.

Two distinct JAR-API mismatches kept both axes dead even with the JVM warm:

- ADF: ``AbstractBuilder`` has no ``add(Argument)`` overload (only
  ``add(Argument, AcceptanceCondition)`` and ``add(Link)``); the acceptance
  enums are singletons (``.INSTANCE``, not callable); the default builder is
  eager-without-strategy ("missing links") and every reasoner takes an
  ``IncrementalSatSolver``.
- EAF: the framework's no-arg constructor defaults the epistemic constraint
  to ``Possibility(Tautology)`` — the one formula its own evaluator rejects.

The guard runs a fresh subprocess (JVM started through the production entry
point) and requires a real decision from each axis: non-empty interpretations
for ADF, the grounded extension [a, c] for EAF on a->b->c.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

_SCRIPT = r"""
import os
os.environ.pop("PYTEST_RUNNING", None)

from argumentation_analysis.core.jvm_setup import initialize_jvm
initialize_jvm()

from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer

init = TweetyInitializer()
if not init.is_jvm_ready():
    init.ensure_jvm_and_components_are_ready()

from argumentation_analysis.agents.core.logic.adf_handler import ADFHandler
from argumentation_analysis.agents.core.logic.eaf_handler import EAFHandler

adf = ADFHandler(init).analyze_adf(
    statements=["a", "b"],
    acceptance_conditions={"a": "tautology", "b": "negation:a"},
    semantics="grounded",
)
assert adf.get("interpretations"), f"ADF decided nothing: {adf}"
assert adf.get("degraded") is not True, f"ADF degraded on this machine: {adf}"
print("ADF_OK", adf["interpretations"])

eaf = EAFHandler(init).analyze_epistemic_framework(
    arguments=["a", "b", "c"],
    attacks=[["a", "b"], ["b", "c"]],
    epistemic_beliefs={"agent1": ["a", "b", "c"]},
    semantics="grounded",
)
assert ["a", "c"] in eaf.get("extensions", []), f"EAF wrong extensions: {eaf}"
print("EAF_OK", eaf["extensions"])
"""


@pytest.mark.integration
@pytest.mark.no_jvm_session
def test_adf_and_eaf_decide_in_fresh_process(tmp_path):
    script = tmp_path / "probe_1796.py"
    script.write_text(_SCRIPT, encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        timeout=420,
        cwd=str(REPO_ROOT),
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, f"probe failed:\n{combined[-2000:]}"
    assert "ADF_OK" in result.stdout and "EAF_OK" in result.stdout
