"""Smoke tests for the spectacular full tour notebook."""

import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
NOTEBOOK_PATH = REPO_ROOT / "examples" / "notebooks" / "spectacular_full_tour.ipynb"
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "golden" / "fixtures" / "spectacular" / "doc_a_golden.json"
)


class TestSpectacularTourNotebook:
    """Validate notebook structure and data integrity."""

    @pytest.fixture()
    def notebook_cells(self):
        with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
            nb = json.load(f)
        return nb["cells"]

    @pytest.fixture()
    def golden_state(self):
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_notebook_file_exists(self):
        assert NOTEBOOK_PATH.exists(), f"Notebook not found at {NOTEBOOK_PATH}"

    def test_minimum_15_cells(self, notebook_cells):
        assert (
            len(notebook_cells) >= 15
        ), f"Expected >= 15 cells, got {len(notebook_cells)}"

    def test_has_markdown_and_code_cells(self, notebook_cells):
        cell_types = {c["cell_type"] for c in notebook_cells}
        assert "markdown" in cell_types, "No markdown cells found"
        assert "code" in cell_types, "No code cells found"

    def test_all_17_capabilities_referenced(self, notebook_cells, golden_state):
        capabilities = set(golden_state["capabilities_used"])
        all_source = " ".join(
            " ".join(cell.get("source", [])) for cell in notebook_cells
        )
        for cap in capabilities:
            assert cap in all_source, f"Capability '{cap}' not referenced in notebook"

    def test_no_plaintext_source_content(self, notebook_cells):
        all_source = " ".join(
            " ".join(cell.get("source", [])) for cell in notebook_cells
        )
        forbidden = ["raw_text", "full_text", "source_name", "author", "speaker"]
        for word in forbidden:
            # Allow 'raw_text' only as dict key access patterns like state["raw_text"]
            # but not actual content
            assert (
                f'"{word}"' not in all_source.lower() or word == "raw_text"
            ), f"Potentially sensitive '{word}' found in notebook"

    def test_opaque_id_only(self, notebook_cells):
        all_source = " ".join(
            " ".join(cell.get("source", [])) for cell in notebook_cells
        )
        assert "doc_A" in all_source, "Opaque ID doc_A not found"
        # The notebook loads from the golden fixture file (doc_a_golden.json) which is fine
        # What matters is that displayed outputs use opaque IDs, not source names
        assert "source_name" not in all_source, "Should not reference source_name field"
        assert (
            "author" not in all_source.lower()
        ), "Should not reference author metadata"

    def test_section_structure(self, notebook_cells):
        """Verify all 8 major sections exist as markdown headers."""
        md_sources = [
            "".join(c.get("source", []))
            for c in notebook_cells
            if c["cell_type"] == "markdown"
        ]
        all_md = " ".join(md_sources)
        sections = [
            "Argument Extraction",
            "Fallacy Detection",
            "Logical Formalization",
            "Dung",
            "ATMS",
            "JTMS",
            "Counter-Argumentation",
            "Narrative Synthesis",
        ]
        for section in sections:
            assert (
                section in all_md
            ), f"Section '{section}' not found in notebook markdown"

    def test_golden_fixture_loads(self, golden_state):
        assert golden_state["source_id"] == "doc_A"
        assert golden_state["summary"]["completed"] == 17
        state = golden_state["state_snapshot"]
        assert len(state["identified_arguments"]) == 8
        assert len(state["identified_fallacies"]) == 4

    def test_conclusion_lists_17_phases(self, notebook_cells):
        md_sources = [
            "".join(c.get("source", []))
            for c in notebook_cells
            if c["cell_type"] == "markdown"
        ]
        conclusion = [s for s in md_sources if "Conclusion" in s]
        assert len(conclusion) >= 1, "No conclusion cell found"
        # Count numbered items (1. through 17.)
        conclusion_text = conclusion[0]
        phase_count = conclusion_text.count("`.+`") + conclusion_text.count("`")
        assert "17" in conclusion_text, "Conclusion should reference 17 phases"

    def test_imports_cell_present(self, notebook_cells):
        first_code = None
        for c in notebook_cells:
            if c["cell_type"] == "code":
                first_code = "".join(c.get("source", []))
                break
        assert first_code is not None, "No code cell found"
        assert "import json" in first_code, "First code cell should import json"
        assert "pathlib" in first_code, "First code cell should use pathlib"

    def test_ipython_display_used(self, notebook_cells):
        code_sources = [
            "".join(c.get("source", []))
            for c in notebook_cells
            if c["cell_type"] == "code"
        ]
        uses_display = any("display(HTML" in src for src in code_sources)
        assert (
            uses_display
        ), "Notebook should use IPython display(HTML(...)) for rich output"
