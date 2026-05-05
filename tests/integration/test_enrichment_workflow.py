"""Tests for the enrichment workflow CLI and docs (Issue #413).

Validates:
- tasks.py CLI parses commands and flags correctly
- Graceful error when dependent scripts (C.1–C.4) are not yet available
- Enrichment doc exists and contains key sections
- README points to Discourse Pattern Mining
- Privacy guard catches intentional leaks
"""

import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TASKS_CLI = REPO_ROOT / "scripts" / "dataset" / "tasks.py"
ENRICH_DOC = REPO_ROOT / "docs" / "security" / "dataset_enrichment.md"
README = REPO_ROOT / "README.md"


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

    def test_pattern_rerun_graceful_missing_script(self):
        result = subprocess.run(
            [sys.executable, str(TASKS_CLI), "pattern-rerun", "--skip-existing"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()

    def test_pattern_report_graceful_missing_script(self):
        result = subprocess.run(
            [sys.executable, str(TASKS_CLI), "pattern-report"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "not found" in result.stderr.lower()

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
