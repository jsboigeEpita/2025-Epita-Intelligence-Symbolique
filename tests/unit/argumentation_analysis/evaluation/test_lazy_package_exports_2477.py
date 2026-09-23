"""#2477 — reaching ``leak_patterns`` by its package path costs no LLM stack.

``leak_patterns`` must stay import-effect-free, but importing it runs
``evaluation/__init__`` first, which imported ``model_registry`` eagerly and
with it ``semantic_kernel`` and ``openai`` (2 945 modules, measured). The
probes run in a fresh child process: in a pytest session those modules are
already loaded by other tests, so an in-process check could not fail.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

_HEAVY = (
    "semantic_kernel",
    "openai",
    "argumentation_analysis.evaluation.model_registry",
)


def _child(code: str):
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_leak_patterns_by_package_path_loads_no_llm_stack():
    loaded = _child(
        "import json, sys\n"
        "import argumentation_analysis.evaluation.leak_patterns\n"
        "import scripts.cassettes.privacy\n"
        f"print(json.dumps([m for m in {_HEAVY!r} if m in sys.modules]))\n"
    )
    assert loaded == [], f"the package path still loads {loaded}"


def test_every_export_still_resolves():
    # Each name of __all__, a star import, and a submodule reached by
    # ``from package import submodule`` — the three spellings the tree uses.
    report = _child(
        "import json\n"
        "import argumentation_analysis.evaluation as ev\n"
        "wrong = [n for n in ev.__all__ if getattr(ev, n).__name__ != n]\n"
        "ns = {}\n"
        "exec('from argumentation_analysis.evaluation import *', ns)\n"
        "missing = [n for n in ev.__all__ if n not in ns]\n"
        "from argumentation_analysis.evaluation import capability_eval\n"
        "try:\n"
        "    ev.NoSuchExport\n"
        "    unknown = 'resolved'\n"
        "except AttributeError:\n"
        "    unknown = 'AttributeError'\n"
        "print(json.dumps([wrong, missing, capability_eval.__name__, unknown, len(ev.__all__)]))\n"
    )
    wrong, missing, submodule, unknown, exported = report
    assert wrong == [] and missing == [], (wrong, missing)
    assert submodule == "argumentation_analysis.evaluation.capability_eval"
    assert unknown == "AttributeError"
    assert exported == 6
