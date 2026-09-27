"""Extract-tooling HTML reports refuse a destination git could stage (#2773).

The repair, verification and LLM-verification reports render source and
extract names, markers and diagnostics derived from the encrypted dataset.
They now call the #2738 guard before writing, their defaults carry an ignored
name, and the entry points that spend work before writing check the
destination first. Synthetic names and markers only, in a throwaway
repository; the real ``.gitignore`` is read only through ``git check-ignore``.
"""

import asyncio
import shutil
import subprocess
import sys
from html import escape
from pathlib import Path

import pytest

from argumentation_analysis.core.plaintext_destination import (
    PlaintextDestinationError,
    check_plaintext_destination,
)
from argumentation_analysis.core.utils import cli_utils
from argumentation_analysis.utils.dev_tools import repair_utils, verification_utils
from argumentation_analysis.utils.extract_repair import (
    marker_repair_logic,
    verify_extracts_with_llm,
)

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="the guard asks git; no git on PATH"
)

MARKER = "synthetic <start> & marker"

REPAIR_RESULTS = [
    {
        "source_name": "src_A",
        "extract_name": "ext_0",
        "status": "repaired",
        "message": "synthetic repair",
        "old_start_marker": MARKER,
        "new_start_marker": "synthetic new start",
        "old_end_marker": "synthetic old end",
        "new_end_marker": "synthetic new end",
        "explanation": "synthetic explanation",
    }
]
VERIFY_RESULTS = [
    {
        "source_name": "src_A",
        "extract_name": "ext_0",
        "status": "invalid",
        "message": f"Marqueur de début '{MARKER}' non trouvé",
        "start_found": False,
        "end_found": True,
    }
]
LLM_RESULTS = [
    {
        "source_name": "src_A",
        "extract_name": "ext_0",
        "status": "valid",
        "coherence": 4,
        "relevance": 4,
        "integrity": 4,
        "comments": f"quotes {MARKER}",
    }
]

WRITERS = {
    "repair": (marker_repair_logic.generate_report, REPAIR_RESULTS),
    "verify": (verification_utils.generate_verification_report, VERIFY_RESULTS),
    "llm": (verify_extracts_with_llm.generate_report, LLM_RESULTS),
}

# The default each CLI had before #2773; none of them is ignored here.
OLD_DEFAULTS = {
    "repair": "repair_report.html",
    "verify": "verify_report.html",
    "llm": "verify_extracts_llm_report.html",
}


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pytest.ini").is_file():
            return candidate
    raise AssertionError("pytest.ini not found above this test")


def _cli_defaults(monkeypatch):
    """The ``--output`` default of each CLI that writes one of the reports."""
    from argumentation_analysis.scripts import run_verify_extracts_llm
    from argumentation_analysis.utils import run_verify_extracts_with_llm

    monkeypatch.setattr(sys, "argv", ["prog"])
    return {
        "repair": [cli_utils.parse_extract_repair_arguments().output],
        "verify": [cli_utils.parse_extract_verification_arguments().output],
        "llm": [
            run_verify_extracts_with_llm.build_verify_parser().get_default("output"),
            run_verify_extracts_llm.build_verify_parser().get_default("output"),
        ],
    }


@pytest.fixture
def work_tree(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text("ignored/\n*_unencrypted*\n", encoding="utf-8")
    return root


# --- the writers -------------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(WRITERS))
def test_writer_refuses_an_unignored_path_and_writes_nothing(work_tree, kind):
    write, results = WRITERS[kind]
    target = work_tree / "reports" / f"{kind}.html"
    with pytest.raises(PlaintextDestinationError, match="not ignored"):
        write(results, str(target))
    assert not target.parent.exists()


@pytest.mark.parametrize("kind", sorted(WRITERS))
def test_writer_refuses_its_old_default_in_the_working_directory(
    work_tree, monkeypatch, kind
):
    write, results = WRITERS[kind]
    monkeypatch.chdir(work_tree)
    with pytest.raises(PlaintextDestinationError):
        write(results, OLD_DEFAULTS[kind])
    assert not (work_tree / OLD_DEFAULTS[kind]).exists()


@pytest.mark.parametrize("kind", sorted(WRITERS))
def test_writer_writes_a_complete_report_under_an_ignored_path(work_tree, kind):
    write, results = WRITERS[kind]
    (work_tree / "ignored").mkdir()
    for target in (
        work_tree / "ignored" / f"{kind}.html",
        work_tree / f"{kind}_unencrypted.html",
    ):
        write(results, str(target))
        html = target.read_text(encoding="utf-8")
        assert "src_A" in html and "ext_0" in html
        assert escape(MARKER) in html
        assert html.rstrip().endswith("</html>")


def test_function_defaults_land_on_an_ignored_name(work_tree, monkeypatch):
    monkeypatch.chdir(work_tree)
    marker_repair_logic.generate_report(REPAIR_RESULTS)
    verify_extracts_with_llm.generate_report(LLM_RESULTS)
    written = sorted(p.name for p in work_tree.glob("*.html"))
    assert written == [
        "repair_report_unencrypted.html",
        "verify_extracts_llm_report_unencrypted.html",
    ]


# --- the defaults against this repository's own .gitignore ---------------------


def test_this_repository_ignores_every_cli_default_and_no_old_one(monkeypatch):
    root = _repo_root()
    for kind, defaults in _cli_defaults(monkeypatch).items():
        for default in defaults:
            assert check_plaintext_destination(root / default)
        with pytest.raises(PlaintextDestinationError):
            check_plaintext_destination(root / OLD_DEFAULTS[kind])


# --- entry points check before they spend work ---------------------------------


def _no_work(*args, **kwargs):
    raise AssertionError("work started before the destination was checked")


def test_repair_pipeline_refuses_before_creating_the_llm_service(
    work_tree, monkeypatch
):
    monkeypatch.setattr(repair_utils, "create_llm_service", _no_work)
    with pytest.raises(PlaintextDestinationError):
        asyncio.run(
            repair_utils.run_extract_repair_pipeline(
                work_tree, str(work_tree / "repair.html"), save_changes=False
            )
        )


def test_verification_pipeline_refuses_before_loading_definitions(
    work_tree, monkeypatch
):
    monkeypatch.setattr(verification_utils, "CryptoService", _no_work)
    with pytest.raises(PlaintextDestinationError):
        verification_utils.run_extract_verification_pipeline(
            work_tree, str(work_tree / "verify.html"), None
        )


def test_llm_verify_clis_refuse_before_loading_definitions(work_tree, monkeypatch):
    from argumentation_analysis.core import llm_service
    from argumentation_analysis.scripts import run_verify_extracts_llm
    from argumentation_analysis.ui import extract_utils
    from argumentation_analysis.utils import run_verify_extracts_with_llm

    monkeypatch.setattr(extract_utils, "load_extract_definitions_safely", _no_work)
    monkeypatch.setattr(llm_service, "create_llm_service", _no_work)
    monkeypatch.setattr(
        run_verify_extracts_llm, "load_extract_definitions_safely", _no_work
    )
    monkeypatch.setattr(run_verify_extracts_llm, "create_llm_service", _no_work)
    target = str(work_tree / "llm.html")
    monkeypatch.setattr(sys, "argv", ["prog", "--output", target])
    for main in (run_verify_extracts_with_llm.main, run_verify_extracts_llm.main):
        with pytest.raises(PlaintextDestinationError):
            asyncio.run(main())
    assert not Path(target).exists()
