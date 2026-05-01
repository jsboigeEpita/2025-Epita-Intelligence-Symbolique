"""Smoke tests for spectacular_analysis_tour.ipynb — #362"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

NOTEBOOK = Path(__file__).resolve().parent.parent.parent.parent / "notebooks/spectacular_analysis_tour.ipynb"
SCRIPT = Path(__file__).resolve().parent.parent.parent.parent / (
    "examples/02_core_system_demos/scripts_demonstration/demonstration_epita_spectacular.py"
)


@pytest.mark.skipif(not NOTEBOOK.exists(), reason="Notebook not found")
class TestSpectacularNotebook:
    """Verify the Jupyter companion notebook structure and execution."""

    def test_notebook_is_valid_json(self):
        import nbformat

        nb = nbformat.read(NOTEBOOK, as_version=4)
        assert nb.nbformat == 4

    def test_notebook_has_expected_cells(self):
        import nbformat

        nb = nbformat.read(NOTEBOOK, as_version=4)
        code_cells = [c for c in nb.cells if c.cell_type == "code"]
        md_cells = [c for c in nb.cells if c.cell_type == "markdown"]
        assert len(code_cells) >= 7, f"Expected >= 7 code cells, got {len(code_cells)}"
        assert len(md_cells) >= 6, f"Expected >= 6 markdown cells, got {len(md_cells)}"

    def test_notebook_covers_all_steps(self):
        import nbformat

        nb = nbformat.read(NOTEBOOK, as_version=4)
        all_text = " ".join(c.source for c in nb.cells)
        for step_name in ("Extraction", "Formal Logic", "Fallacy", "Dung", "JTMS",
                          "Adversarial", "Synthesis"):
            assert step_name in all_text, f"Notebook missing: {step_name}"

    def test_notebook_no_sensitive_data(self):
        import nbformat

        nb = nbformat.read(NOTEBOOK, as_version=4)
        all_text = " ".join(c.source for c in nb.cells)
        # No raw API keys or env vars
        assert "OPENAI_API_KEY" not in all_text
        assert "TEXT_CONFIG_PASSPHRASE" not in all_text
        # Uses mock data, not real sources
        assert "MOCK_SPECTACULAR_RESULT" in all_text

    def test_notebook_imports_from_demo_module(self):
        import nbformat

        nb = nbformat.read(NOTEBOOK, as_version=4)
        code_text = " ".join(c.source for c in nb.cells if c.cell_type == "code")
        assert "demonstration_epita_spectacular" in code_text
        assert "MOCK_SPECTACULAR_RESULT" in code_text

    @pytest.mark.skipif(
        not SCRIPT.exists(),
        reason="Demo script dependency not found"
    )
    def test_notebook_executes_headless(self):
        """Execute the notebook via nbconvert and verify no errors."""
        result = subprocess.run(
            [
                sys.executable, "-m", "jupyter", "nbconvert",
                "--to", "notebook", "--execute",
                "--ExecutePreprocessor.timeout=60",
                str(NOTEBOOK),
                "--output", "spectacular_analysis_tour_executed.ipynb",
            ],
            capture_output=True, text=True, timeout=120,
            cwd=NOTEBOOK.parent,
        )
        assert result.returncode == 0, f"Notebook execution failed:\n{result.stderr[:500]}"

        executed = NOTEBOOK.parent / "spectacular_analysis_tour_executed.ipynb"
        assert executed.exists()
        try:
            import nbformat
            nb = nbformat.read(executed, as_version=4)
            error_cells = [
                c for c in nb.cells
                if c.cell_type == "code"
                and any(
                    o.get("output_type") == "error"
                    for o in c.get("outputs", [])
                )
            ]
            assert len(error_cells) == 0, f"Cells with errors: {[c.source[:50] for c in error_cells]}"
        finally:
            executed.unlink(missing_ok=True)
