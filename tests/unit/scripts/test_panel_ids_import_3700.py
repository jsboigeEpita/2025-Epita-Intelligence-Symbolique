"""#3700 — the panel's one parser is importable without the pipeline runtime.

``scripts/panel/_common.read_panel`` needs about thirty lines of ``re`` and
``pathlib`` to name a panel. It used to get them by importing
``scripts.dataset.run_corpus_batch``, which loads the pipeline runtime and
writes the checkout's ``.env`` into the process environment on the way
(measured 2026-11-26 on this seat: 2964 modules and 34 variables against 111
modules and 0 for ``scripts/panel/act_replay_preflight.py``). An instrument
that must stay keyless and model-clientless — the act-replay preflight,
#3658 item 46c — could therefore not use the campaign's one parser, and a
second way to name a panel appeared in a campaign that decided on one
(#3375, "one parser, one list").

The witnesses run in children: whatever a parent test process has already
imported cannot witness an import's own cost. Each child reports names,
counts and booleans only — never an environment value — and its stderr is
kept out of every failure message (the environment manager's startup lines
name two keys' fingerprints).

The last witness is the instrument's own control: the same child, pointed at
the runtime-bearing module, must report the cost this file exists to keep
out. A guard that cannot fail proves nothing.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

# Measured 2026-11-26 in a fresh child (``import scripts.dataset.panel_ids``):
# 7 modules. The ceiling leaves room for a Python version's own bookkeeping
# and stays far below a numeric stack — ``numpy`` alone adds about eighty.
MODULES_DELTA_CEILING = 40

_HEAVY = ("torch", "openai", "semantic_kernel", "jpype", "numpy")

# Names only — no value is read, kept or printed. Removed from the child's
# environment so that a `.env` auto-load shows up as an addition.
_CREDENTIAL_SHAPED = re.compile(r"KEY|TOKEN|SECRET|PASS", re.IGNORECASE)


def _run_child(statement_lines: str, *argv: str) -> Optional[dict]:
    """Run ``statement_lines`` in a fresh interpreter and read its report.

    The report is a JSON object printed on the child's stdout; it carries
    environment variable *names* added since the child started, the module
    count delta, which heavy modules are loaded, whether the runtime-bearing
    corpus batch module is loaded, and whatever the statement left in
    ``result``. The child's stderr is deliberately never read.

    The child starts without the credential-shaped names of the parent's
    environment. Under pytest the parent has already loaded the checkout's
    ``.env`` (``conftest``) and a plain child inherits it: a ``.env``
    auto-load then adds nothing, and a zero would say "already there", not
    "nothing written" — measured on this seat before the names were
    removed: 0 added by the runtime's own import.
    """
    child_env = {
        name: value
        for name, value in os.environ.items()
        if not _CREDENTIAL_SHAPED.search(name)
    }
    code = "\n".join(
        [
            "import json, os, sys",
            "before = set(os.environ)",
            "before_modules = len(sys.modules)",
            "heavy = %r" % (_HEAVY,),
            "result = None",
            statement_lines,
            "print(json.dumps({",
            "    'env_added_names': sorted(set(os.environ) - before),",
            "    'modules_delta': len(sys.modules) - before_modules,",
            "    'heavy': [name for name in heavy if name in sys.modules],",
            "    'runtime_loaded': (",
            "        'scripts.dataset.run_corpus_batch' in sys.modules),",
            "    'result': result,",
            "}))",
        ]
    )
    completed = subprocess.run(
        [sys.executable, "-c", code, *argv],
        cwd=REPO_ROOT,
        env=child_env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert completed.returncode == 0, (
        f"the child failed with rc={completed.returncode}; its stderr is not "
        "reported here on purpose (it can carry key fingerprints) — rerun the "
        "statement by hand if it matters"
    )
    lines = completed.stdout.strip().splitlines()
    assert lines, "the child printed no report"
    return json.loads(lines[-1])


def test_the_parser_module_imports_without_the_runtime() -> None:
    """The new home of ``parse_doc_ids`` costs neither runtime nor ``.env``."""
    facts = _run_child("import scripts.dataset.panel_ids")

    assert facts["env_added_names"] == [], (
        "importing the panel parser wrote environment variables: "
        f"{facts['env_added_names']}"
    )
    assert (
        facts["heavy"] == []
    ), f"importing the panel parser loaded runtime modules: {facts['heavy']}"
    assert facts["modules_delta"] <= MODULES_DELTA_CEILING, (
        f"the parser import loaded {facts['modules_delta']} modules, ceiling "
        f"{MODULES_DELTA_CEILING}"
    )


def test_naming_a_panel_from_the_panel_folder_stays_outside_the_runtime(
    tmp_path: Path,
) -> None:
    """``read_panel`` still parses the file, and no longer reaches the batch."""
    panel = tmp_path / "panel.txt"
    panel.write_text(
        "# the campaign's panel\nb\na\n\nb\n# trailing comment\n", encoding="utf-8"
    )

    facts = _run_child(
        "from scripts.panel import _common as c\nresult = c.read_panel(sys.argv[1])",
        str(panel),
    )

    assert facts["result"] == ["b", "a"], (
        "the panel file is parsed as before: reading order, first occurrence "
        f"wins, comments and blanks ignored; got {facts['result']!r}"
    )
    assert (
        facts["runtime_loaded"] is False
    ), "naming a panel loaded scripts.dataset.run_corpus_batch"
    assert (
        facts["env_added_names"] == []
    ), f"naming a panel wrote environment variables: {facts['env_added_names']}"
    assert (
        facts["heavy"] == []
    ), f"naming a panel loaded runtime modules: {facts['heavy']}"


def test_the_corpus_batch_runner_still_exposes_the_one_parser() -> None:
    """The runner re-exports the parser; it holds no second copy of it.

    Three call sites (``judge_panel``, ``compare_orchestration_modes``, the
    runner itself) import ``parse_doc_ids`` from
    ``scripts.dataset.run_corpus_batch``. The name must be the very same
    function object: two copies of a parser is how two populations drift
    apart (#3375).
    """
    facts = _run_child(
        "import scripts.dataset.panel_ids as p\n"
        "import scripts.dataset.run_corpus_batch as b\n"
        "result = b.parse_doc_ids is p.parse_doc_ids"
    )

    assert facts["result"] is True, (
        "scripts.dataset.run_corpus_batch.parse_doc_ids is not the function "
        "scripts.dataset.panel_ids defines"
    )


def test_the_control_reports_the_cost_the_parser_keeps_out() -> None:
    """The instrument can fail: the runtime-bearing import is still expensive.

    Without this witness a child that measured nothing would look exactly
    like a child that measured zero.
    """
    facts = _run_child("import scripts.dataset.run_corpus_batch")

    assert facts["runtime_loaded"] is True
    assert facts["heavy"], "the runtime import loaded none of the heavy modules"
    assert facts["modules_delta"] > MODULES_DELTA_CEILING, (
        "the control import stayed under the ceiling, so the ceiling measures "
        f"nothing: {facts['modules_delta']} modules"
    )
    # On a seat holding a `.env`, the runtime's auto-load writes variables
    # into the child's environment; the CI gate has no `'.env`, so there the
    # claim is vacuous and only the module counts above carry it.
    if (REPO_ROOT / ".env").is_file():
        assert facts["env_added_names"], (
            "the checkout holds a .env but the runtime import wrote no "
            "environment variable"
        )
