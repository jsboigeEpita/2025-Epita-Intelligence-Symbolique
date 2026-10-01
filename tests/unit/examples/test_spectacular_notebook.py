"""Smoke tests for spectacular_analysis_tour.ipynb — #362.

#2864 — these six tests sat in the gate argv since #519 while skipping on
every run: ``nbformat``/``jupyter`` were never provisioned, so a green gate
checked nothing about the notebook (not even the privacy guard below). Both
dependencies are now declared in ``environment.yml`` (#1803 lock), so a
missing dependency is a COLLECTION ERROR, loud, not a skip — the module
level imports below are that fail-loud contract.

The headless execution is hermetic: it writes a kernelspec into the pytest
tmp_path, pinned to ``sys.executable`` and discovered through
``JUPYTER_PATH``, because the default ``python3`` kernelspec resolves
``python`` through PATH — on a default Windows 11 seat that is the
WindowsApps 3.13 stub, which has no ``ipykernel_launcher`` and kills the
kernel before it replies (measured: "Kernel died before replying to
kernel_info"). Measured with the hermetic spec: returncode 0 in ~4 s,
0 error cells, and 0 LLM egress by construction — the notebook drives
``MOCK_SPECTACULAR_RESULT`` from a stdlib-only demo module and never
constructs a client.

The ``NOTEBOOK.exists()``/``SCRIPT.exists()`` skips went with the rest:
both files are tracked, and a missing tracked file is a broken repo the
guard should report, not a green run.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import nbconvert  # noqa: F401  # declared dep (#2864): absence must fail loudly
import nbformat

NOTEBOOK = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "notebooks/spectacular_analysis_tour.ipynb"
)
SCRIPT = Path(__file__).resolve().parent.parent.parent.parent / (
    "examples/02_core_system_demos/scripts_demonstration/demonstration_epita_spectacular.py"
)


class TestSpectacularNotebook:
    """Verify the Jupyter companion notebook structure and execution."""

    def test_notebook_is_valid_json(self):
        nb = nbformat.read(NOTEBOOK, as_version=4)
        assert nb.nbformat == 4

    def test_notebook_has_expected_cells(self):
        nb = nbformat.read(NOTEBOOK, as_version=4)
        code_cells = [c for c in nb.cells if c.cell_type == "code"]
        md_cells = [c for c in nb.cells if c.cell_type == "markdown"]
        assert len(code_cells) >= 7, f"Expected >= 7 code cells, got {len(code_cells)}"
        assert len(md_cells) >= 6, f"Expected >= 6 markdown cells, got {len(md_cells)}"

    def test_notebook_covers_all_steps(self):
        nb = nbformat.read(NOTEBOOK, as_version=4)
        all_text = " ".join(c.source for c in nb.cells)
        for step_name in (
            "Extraction",
            "Formal Logic",
            "Fallacy",
            "Dung",
            "JTMS",
            "Adversarial",
            "Synthesis",
        ):
            assert step_name in all_text, f"Notebook missing: {step_name}"

    def test_notebook_no_sensitive_data(self):
        nb = nbformat.read(NOTEBOOK, as_version=4)
        all_text = " ".join(c.source for c in nb.cells)
        # No raw API keys or env vars
        assert "OPENAI_API_KEY" not in all_text
        assert "TEXT_CONFIG_PASSPHRASE" not in all_text
        # Uses mock data, not real sources
        assert "MOCK_SPECTACULAR_RESULT" in all_text

    def test_notebook_imports_from_demo_module(self):
        nb = nbformat.read(NOTEBOOK, as_version=4)
        code_text = " ".join(c.source for c in nb.cells if c.cell_type == "code")
        assert "demonstration_epita_spectacular" in code_text
        assert "MOCK_SPECTACULAR_RESULT" in code_text

    def test_notebook_executes_headless(self, tmp_path: Path) -> None:
        """Execute the notebook via nbconvert and verify no errors.

        Writes the executed notebook — and the kernelspec it needs — into
        pytest tmp_path so the source tree stays clean and parallel runs
        don't collide (review #377). The kernel is pinned to
        ``sys.executable`` (see module docstring): the test must not depend
        on which ``python`` PATH resolves first on the seat.
        """
        kernelspec = tmp_path / "kernels" / "spectacular-test"
        kernelspec.mkdir(parents=True)
        (kernelspec / "kernel.json").write_text(
            json.dumps(
                {
                    "argv": [
                        sys.executable,
                        "-m",
                        "ipykernel_launcher",
                        "-f",
                        "{connection_file}",
                    ],
                    "display_name": "Spectacular test kernel",
                    "language": "python",
                }
            ),
            encoding="utf-8",
        )
        executed = tmp_path / "spectacular_analysis_tour_executed.ipynb"
        # The kernel must not be able to egress even if the notebook drifts
        # from its mock data one day: the watched keys never reach it, and a
        # notebook that legitimately needed one fails here instead of at the
        # gate (#2444's 0 stays true by construction, not by hope).
        scrubbed = {
            k: v
            for k, v in os.environ.items()
            if k not in {"OPENAI_API_KEY", "OPENROUTER_API_KEY"}
        }
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "nbconvert",
                "--to",
                "notebook",
                "--execute",
                "--ExecutePreprocessor.timeout=60",
                "--ExecutePreprocessor.kernel_name=spectacular-test",
                str(NOTEBOOK),
                "--output",
                str(executed),
            ],
            capture_output=True,
            text=True,
            timeout=120,
            env={**scrubbed, "JUPYTER_PATH": str(tmp_path)},
        )
        assert (
            result.returncode == 0
        ), f"Notebook execution failed:\n{result.stderr[:500]}"
        assert executed.exists()

        nb = nbformat.read(executed, as_version=4)
        error_cells = [
            c
            for c in nb.cells
            if c.cell_type == "code"
            and any(o.get("output_type") == "error" for o in c.get("outputs", []))
        ]
        assert (
            len(error_cells) == 0
        ), f"Cells with errors: {[c.source[:50] for c in error_cells]}"


# --- the fail-loud contract (#2864): a declared dependency never skips -----
# The guard below keeps the retirement honest: if someone reintroduces a
# capability probe or a skip tied to a missing dependency, the workaround
# shape #519 installed comes back, and the gate goes green while checking
# nothing.


def test_no_capability_probe_skips_remain() -> None:
    """The #519 skips are gone: dependency absence must fail at collection
    (the module-level imports above), never skip a test.

    The needles are built at runtime so this guard's own source cannot
    satisfy itself — the same discipline as the leak detectors' self-tests.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    probe = "find_" + "spec("
    skip_mark = "mark." + "skipif"
    runtime_skip = "pytest." + "skip("
    assert probe not in source, "a capability probe is back (#519 shape)"
    assert skip_mark not in source, "a conditional skip is back (#519 shape)"
    assert runtime_skip not in source, "a runtime skip is back (#519 shape)"
