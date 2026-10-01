"""#2867: importing ``api.main`` must not drag pandas at import time.

Measured on ``main`` (warm, po-2025): ``import api.main`` costs 13.4 s, of
which pandas is 541 ms (297 modules). The ``builtins.__import__`` spy (the
issue's instrument — ``-X importtime`` logs are sorted by cumulative time, so
parentage cannot be read off them) names the first importer
``agents.core.informal.informal_definitions``. The measured set of pandas
entry points on the ``api.main`` path was four, in two classes:

- three first-party module-level ``import pandas`` sites —
  ``informal_definitions``, ``taxonomy_sophism_detector``, and
  ``agents.tools.analysis.contextual_fallacy_analyzer``. None of them needs
  pandas to *define* anything: the bodies touch pandas only inside the
  private helpers and ``_internal_*`` methods, so the import moved to call
  time (the pattern PR #2866 used for pyvis in ``jtms_core``), and the
  annotations carry ``from __future__ import annotations`` so def-time no
  longer resolves ``pd.Series`` either. The ``@kernel_function`` surface is
  untouched: its signatures are plain ``str``/``int``, so nothing Semantic
  Kernel introspects at registration ever mentioned pandas.
- one dead third-party import: the plugins homonym
  ``plugins.analysis_tools.logic.contextual_fallacy_analyzer`` imported
  ``sklearn.metrics.pairwise.cosine_similarity`` with no consumer anywhere in
  the codebase — and sklearn drags scipy *and* pandas
  (``sklearn.utils.fixes``). The line is removed, not deferred.

After both, ``import api.main`` no longer enters pandas, scipy or sklearn
(warm 13.4 s -> 11.5 s on po-2025), and what remains in ``sys.modules`` is the
intended preload (torch, transformers via ``core.dll_guard``), the structural
one (semantic_kernel, next slice) and matplotlib (139 ms, next slice).

Two fresh-subprocess witnesses, both born red on ``main`` (pandas sits in
``sys.modules`` after either import).
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HEAVY = ("pandas",)

_PROBE = """
import importlib
import sys

importlib.import_module({module!r})
print("PRESENT:" + ",".join(sorted(n for n in {heavy!r} if n in sys.modules)))
"""


def _clean_env():
    # Same shape as tests/unit/api/test_api_main_import_cost_2855.py.
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    for name in ("OPENAI_API_KEY", "OPENROUTER_API_KEY", "GH_TOKEN"):
        env[name] = ""
    return env


def _heavy_modules_after(module: str) -> str:
    probe = _PROBE.format(module=module, heavy=HEAVY)
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        env=_clean_env(),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    markers = [
        line for line in result.stdout.splitlines() if line.startswith("PRESENT:")
    ]
    assert markers, result.stdout[-500:]
    return markers[-1].split(":", 1)[1]


def test_api_main_does_not_import_pandas():
    """#2867 slice 1: after ``import api.main``, pandas is not in
    ``sys.modules`` — every module-level pandas import on its path moved to
    call time."""
    present = _heavy_modules_after("api.main")
    assert present == "", (
        f"import api.main dragged {present} in — pandas belongs behind a "
        "call-time import on the api.main path (#2867)"
    )


def test_informal_definitions_alone_stays_light():
    """The mechanism: ``informal_definitions`` (the measured first importer)
    defines its plugin without pandas — only its private helpers and
    ``_internal_*`` methods touch it, at call time."""
    present = _heavy_modules_after(
        "argumentation_analysis.agents.core.informal.informal_definitions"
    )
    assert present == "", f"informal_definitions alone dragged {present} in (#2867)"
