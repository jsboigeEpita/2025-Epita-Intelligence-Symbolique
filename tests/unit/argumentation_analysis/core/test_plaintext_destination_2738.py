"""Plaintext writers refuse a destination git could stage (#2738).

Each writer below puts dataset plaintext, or text derived from it, at a path
its caller chooses. The guard they share refuses a path inside a git work tree
that the tree does not ignore. The witnesses use a throwaway repository and
synthetic definitions only; the fallacy plugin's three trace writers are
witnessed beside its fixtures, in ``TestTracePlaintextDestination2738``.
"""

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.utils.tracer import TracedAgent
from argumentation_analysis.core import plaintext_destination
from argumentation_analysis.core.plaintext_destination import (
    DEFAULT_PLAINTEXT_EXPORT_PATH,
    PlaintextDestinationError,
    check_plaintext_destination,
)
from argumentation_analysis.models.extract_definition import ExtractDefinitions
from argumentation_analysis.services.crypto_service import CryptoService
from argumentation_analysis.services.definition_service import DefinitionService
from argumentation_analysis.ui import extract_utils

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="the guard asks git; no git on PATH"
)

SYNTHETIC = [{"source_name": "src_A", "source_type": "text", "extracts": []}]


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pytest.ini").is_file():
            return candidate
    raise AssertionError("pytest.ini not found above this test")


@pytest.fixture
def work_tree(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text("ignored/\n*_unencrypted*\n", encoding="utf-8")
    return root


# --- the guard ---------------------------------------------------------------


def test_an_unignored_path_in_a_work_tree_is_refused(work_tree):
    with pytest.raises(PlaintextDestinationError, match="not ignored"):
        check_plaintext_destination(work_tree / "plain.json")


def test_an_ignored_path_in_a_work_tree_is_accepted(work_tree):
    assert check_plaintext_destination(work_tree / "ignored" / "plain.json")
    assert check_plaintext_destination(work_tree / "defs_unencrypted.json")


def test_a_tracked_file_is_refused_even_under_an_ignored_name(work_tree):
    tracked = work_tree / "ignored" / "tracked.json"
    tracked.parent.mkdir()
    tracked.write_text("{}", encoding="utf-8")
    subprocess.run(["git", "-C", str(work_tree), "add", "-f", str(tracked)], check=True)
    with pytest.raises(PlaintextDestinationError):
        check_plaintext_destination(tracked)


def test_a_path_outside_every_work_tree_is_accepted(tmp_path):
    assert check_plaintext_destination(tmp_path / "outside" / "plain.json")


def test_git_that_cannot_answer_refuses(work_tree, monkeypatch):
    def no_git(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(plaintext_destination.subprocess, "run", no_git)
    with pytest.raises(PlaintextDestinationError, match="could not say"):
        check_plaintext_destination(work_tree / "ignored" / "plain.json")


def test_this_repository_ignores_the_default_export_and_not_the_old_one():
    root = _repo_root()
    assert check_plaintext_destination(root / DEFAULT_PLAINTEXT_EXPORT_PATH)
    with pytest.raises(PlaintextDestinationError):
        check_plaintext_destination(root / "export_definitions.json")


# --- the writers ---------------------------------------------------------------


def test_extract_export_refuses_and_writes_nothing(work_tree):
    target = work_tree / "plain.json"
    ok, message = extract_utils.export_definitions_to_json(SYNTHETIC, target)
    assert not ok and "not ignored" in message
    assert not target.exists()

    allowed = work_tree / "ignored" / "plain.json"
    ok, _ = extract_utils.export_definitions_to_json(SYNTHETIC, allowed)
    assert ok and allowed.exists()


def test_extract_save_refuses_its_plaintext_fallback(work_tree):
    fallback = work_tree / "fallback.json"
    ok, message = extract_utils.save_extract_definitions_safely(
        SYNTHETIC, work_tree / "ignored" / "defs.enc", None, fallback
    )
    assert not ok and "not ignored" in message
    assert not fallback.exists()


def _definition_service(config_file, fallback_file=None):
    return DefinitionService(
        crypto_service=CryptoService(),  # no key: the plaintext branch
        config_file=config_file,
        fallback_file=fallback_file,
    )


def test_definition_export_refuses_and_writes_nothing(work_tree):
    target = work_tree / "plain.json"
    service = _definition_service(work_tree / "ignored" / "defs.json")
    ok, message = service.export_definitions_to_json(
        ExtractDefinitions.from_dict_list(SYNTHETIC), target
    )
    assert not ok and "not ignored" in message
    assert not target.exists()


def test_definition_save_refuses_its_plaintext_file_and_fallback(work_tree):
    config_file = work_tree / "defs.json"
    fallback = work_tree / "fallback.json"
    service = _definition_service(config_file, fallback)
    ok, message = service.save_definitions(ExtractDefinitions.from_dict_list(SYNTHETIC))
    assert not ok and "not ignored" in message
    assert not config_file.exists() and not fallback.exists()


def test_traced_agent_refuses_its_trace_file(work_tree):
    agent = SimpleNamespace(name="A")
    with pytest.raises(PlaintextDestinationError):
        TracedAgent(agent, str(work_tree / "trace.log"))
    assert not (work_tree / "trace.log").exists()
