"""#2855: importing ``api.main`` must not drag the visualization stack.

Measured on ``main`` (warm, po-2023): ``import api.main`` costs 9.96 s, of which
3.24 s is the ``argumentation_analysis.core`` package ``__init__`` (its eager
``llm_service`` re-export pulls ``semantic_kernel``, 2.24 s) and 719 ms the
``argumentation_analysis.utils`` one (30 eager siblings). The ``utils`` chain
matters twice over: ``agents.core.informal.informal_definitions`` imports only
``taxonomy_loader``, but the package body ran ``reporting_utils ->
visualization_generator -> seaborn`` anyway, plus 75 ``scipy.stats`` modules,
and ``services.jtms.jtms_core``'s module-level pyvis import dragged IPython
(111 modules) and jsonpickle.

Two fresh-subprocess witnesses: the #2855 DoD end-to-end claim, and the cheap
mechanism pin. Both are born red on ``main`` (seaborn and IPython sit in
``sys.modules`` after the import).
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HEAVY = ("seaborn", "IPython", "ipywidgets")

_PROBE = """
import importlib
import sys

importlib.import_module({module!r})
print("PRESENT:" + ",".join(sorted(n for n in {heavy!r} if n in sys.modules)))
"""


def _clean_env():
    # Same shape as tests/unit/webapp/test_detached_backend_cwd_2751.py.
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


def test_api_main_does_not_import_the_visualization_stack():
    """#2855 DoD: after ``import api.main``, none of the three heavy modules is
    in ``sys.modules`` — the package ``__init__``\\ s on its path re-export
    lazily, and ``jtms_core`` imports pyvis at call time."""
    present = _heavy_modules_after("api.main")
    assert present == "", (
        f"import api.main dragged {present} in — the package __init__s and "
        "module-level optional imports on its path must stay lazy (#2855)"
    )


def test_taxonomy_loader_alone_stays_light():
    """The mechanism: ``informal_definitions`` imports ``taxonomy_loader`` and
    nothing else from ``utils``. Running the other 29 sibling module bodies on
    the way (reporting_utils -> visualization_generator -> seaborn) was pure
    import-time waste."""
    present = _heavy_modules_after("argumentation_analysis.utils.taxonomy_loader")
    assert present == "", f"taxonomy_loader alone dragged {present} in (#2855)"
