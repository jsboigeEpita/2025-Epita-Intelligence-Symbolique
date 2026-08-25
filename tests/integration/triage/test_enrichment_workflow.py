"""Tests for the enrichment workflow CLI and docs (Issue #413, #1813).

Validates:
- tasks.py CLI parses commands and flags correctly
- Graceful error when a dependent script path is missing (injected — the
  C.1-C.4 scripts are delivered now, so the "not yet available" premise
  of the original tests is dead; the guarantee itself stays)
- The delivered C.1-C.4 scripts are dispatched with the right argv, with
  the subprocess intercepted so no real run fires from this file (the
  pre-fix version executed build_pattern_report.py for real, which is
  where the native abort of #1813 lived)
- Enrichment doc exists and contains key sections
- README points to Discourse Pattern Mining
- Privacy guard catches intentional leaks
"""

import importlib.util
import pathlib
import subprocess
import sys
import types

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
TASKS_CLI = REPO_ROOT / "scripts" / "dataset" / "tasks.py"
ENRICH_DOC = REPO_ROOT / "docs" / "security" / "dataset_enrichment.md"
README = REPO_ROOT / "README.md"


def _load_tasks_module():
    spec = importlib.util.spec_from_file_location("dataset_tasks", TASKS_CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestTasksCLI:
    """Tests for scripts/dataset/tasks.py."""

    def test_tasks_script_exists(self):
        assert TASKS_CLI.is_file()

    def test_pattern_add_requires_args(self):
        result = subprocess.run(
            [sys.executable, str(TASKS_CLI), "pattern-add"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "--source" in result.stderr or "--source" in result.stdout

    def test_pattern_rerun_graceful_missing_script(self, monkeypatch, capsys):
        tasks = _load_tasks_module()
        monkeypatch.setattr(
            tasks, "BATCH_SCRIPT", tasks.SCRIPTS_DIR / "definitely_missing_1813.py"
        )
        rc = tasks.cmd_pattern_rerun(types.SimpleNamespace(skip_existing=True))
        assert rc == 1
        assert "not found" in capsys.readouterr().err.lower()

    def test_pattern_report_graceful_missing_script(self, monkeypatch, capsys):
        tasks = _load_tasks_module()
        monkeypatch.setattr(
            tasks, "REPORT_SCRIPT", tasks.SCRIPTS_DIR / "definitely_missing_1813.py"
        )
        rc = tasks.cmd_pattern_report(types.SimpleNamespace())
        assert rc == 1
        assert "not found" in capsys.readouterr().err.lower()

    def test_delivered_scripts_exist(self):
        tasks = _load_tasks_module()
        assert tasks.ADD_SCRIPT.is_file(), "C.1-C.4 delivered: add_extract.py"
        assert tasks.BATCH_SCRIPT.is_file(), "C.1-C.4 delivered: run_corpus_batch.py"
        assert (
            tasks.REPORT_SCRIPT.is_file()
        ), "C.1-C.4 delivered: build_pattern_report.py"

    def test_pattern_rerun_dispatches_delivered_script(self, monkeypatch):
        tasks = _load_tasks_module()
        captured = []
        monkeypatch.setattr(
            tasks,
            "subprocess",
            types.SimpleNamespace(call=lambda cmd: captured.append(cmd) or 0),
        )
        rc = tasks.cmd_pattern_rerun(types.SimpleNamespace(skip_existing=True))
        assert rc == 0
        assert captured == [
            [
                sys.executable,
                str(tasks.BATCH_SCRIPT),
                "--workflow",
                "spectacular",
                "--skip-existing",
            ]
        ]

    def test_pattern_report_dispatches_delivered_script(self, monkeypatch):
        tasks = _load_tasks_module()
        captured = []
        monkeypatch.setattr(
            tasks,
            "subprocess",
            types.SimpleNamespace(call=lambda cmd: captured.append(cmd) or 0),
        )
        rc = tasks.cmd_pattern_report(types.SimpleNamespace())
        assert rc == 0
        assert captured == [[sys.executable, str(tasks.REPORT_SCRIPT)]]

    def test_invalid_command_exits_error(self):
        result = subprocess.run(
            [sys.executable, str(TASKS_CLI), "nonexistent"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0


class TestEnrichmentDoc:
    """Tests for docs/security/dataset_enrichment.md."""

    def test_doc_exists(self):
        assert ENRICH_DOC.is_file()

    def test_doc_has_metadata_schema(self):
        content = ENRICH_DOC.read_text(encoding="utf-8")
        assert "discourse_type" in content
        assert "era" in content

    def test_doc_has_privacy_section(self):
        content = ENRICH_DOC.read_text(encoding="utf-8")
        assert "opaque" in content.lower()
        assert "privacy" in content.lower() or "Privacy" in content

    def test_doc_has_task_reference(self):
        content = ENRICH_DOC.read_text(encoding="utf-8")
        assert "pattern-add" in content
        assert "pattern-rerun" in content
        assert "pattern-report" in content

    def test_doc_under_80_lines(self):
        lines = ENRICH_DOC.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= 80, f"Doc has {len(lines)} lines, exceeds 80"


class TestReadmePointer:
    """Tests for README Discourse Pattern Mining pointer."""

    def test_readme_has_pattern_mining_section(self):
        content = README.read_text(encoding="utf-8")
        assert "Discourse Pattern Mining" in content

    def test_readme_links_enrichment_doc(self):
        content = README.read_text(encoding="utf-8")
        assert "dataset_enrichment" in content

    def test_readme_links_report(self):
        content = README.read_text(encoding="utf-8")
        assert "discourse_patterns" in content


class TestPrivacyGuard:
    """Privacy guard for enrichment artifacts."""

    def test_enrichment_doc_no_plaintext_refs(self):
        content = ENRICH_DOC.read_text(encoding="utf-8")
        for forbidden in ("full_text", "raw_text", "source_name"):
            assert forbidden not in content, f"LEAK: {forbidden} found in doc"

    def test_readme_no_plaintext_refs_in_pattern_section(self):
        content = README.read_text(encoding="utf-8")
        idx = content.find("Discourse Pattern Mining")
        if idx == -1:
            return
        section = content[idx : idx + 2000]
        for forbidden in ("full_text", "raw_text", "source_name"):
            assert (
                forbidden not in section
            ), f"LEAK: {forbidden} in README pattern section"
