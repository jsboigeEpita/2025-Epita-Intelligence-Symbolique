"""Section 8 of the deep synthesis says why it is empty, and only what it knows (#2344).

No phase writes ``state.cross_text_parallels``: the section is empty on every
run. The renderer used to explain that emptiness with a cause it cannot know
("single-corpus analysis"), so "configured single-corpus" and "never computed"
printed the same sentence. The report now records whether a producer ran
(``cross_text_parallels_status``), and the renderer prints the matching sentence.
"""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    DeepSynthesisReport,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
S8_HEADING = "## 8. Cross-Text Rhetorical Parallels"


def _section_8(report: DeepSynthesisReport) -> str:
    md = DeepSynthesisAgent.render_markdown(report)
    start = md.index(S8_HEADING)
    return md[start : md.index("\n## ", start + 1)]


class TestStatus:
    def test_state_without_the_field_is_not_computed(self):
        state = SimpleNamespace()
        assert DeepSynthesisAgent._cross_text_parallels_status(state) == (
            "not_computed"
        )
        assert DeepSynthesisAgent._build_cross_text_parallels(state) == []

    def test_state_carrying_the_field_is_computed_even_when_empty(self):
        state = SimpleNamespace(cross_text_parallels=[])
        assert DeepSynthesisAgent._cross_text_parallels_status(state) == "computed"

    def test_computed_parallels_are_built(self):
        state = SimpleNamespace(
            cross_text_parallels=[
                {
                    "corpus_x": "corpus_A",
                    "corpus_y": "corpus_B",
                    "move_x": "appeal to fear",
                    "move_y": "appeal to fear",
                    "parallel_type": "analogy",
                }
            ]
        )
        assert DeepSynthesisAgent._cross_text_parallels_status(state) == "computed"
        (parallel,) = DeepSynthesisAgent._build_cross_text_parallels(state)
        assert (parallel.corpus_x, parallel.corpus_y) == ("corpus_A", "corpus_B")

    def test_status_travels_in_to_dict(self):
        report = DeepSynthesisReport(cross_text_parallels_status="not_computed")
        assert report.to_dict()["cross_text_parallels_status"] == "not_computed"


class TestRenderedSentence:
    @pytest.mark.parametrize("status", ["not_computed", ""])
    def test_not_computed_says_so_and_invents_no_cause(self, status):
        s8 = _section_8(DeepSynthesisReport(cross_text_parallels_status=status))
        assert "not computed" in s8
        assert "single-corpus" not in s8

    def test_computed_and_empty_says_none_were_found(self):
        s8 = _section_8(DeepSynthesisReport(cross_text_parallels_status="computed"))
        assert "No cross-text parallels found" in s8
        assert "not computed" not in s8
        assert "single-corpus" not in s8

    def test_unknown_status_raises(self):
        report = DeepSynthesisReport(cross_text_parallels_status="skipped")
        with pytest.raises(ValueError, match="cross_text_parallels_status"):
            DeepSynthesisAgent.render_markdown(report)


def _production_files():
    for root in ("argumentation_analysis", "scripts"):
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            if "_archived" in path.parts:
                continue
            text = path.read_text(encoding="utf-8-sig")
            if "cross_text_parallels" in text:
                yield path, text


def _sites_missing_the_status():
    """Every place that fills Section 8 must record its status next to it.

    Two shapes fill it: ``DeepSynthesisReport(cross_text_parallels=...)`` and
    ``<report>.cross_text_parallels = ...`` inside a function. The first needs
    the ``cross_text_parallels_status`` keyword in the same call, the second an
    assignment to ``<report>.cross_text_parallels_status`` in the same function.
    """
    sites, missing = [], []
    for path, text in _production_files():
        tree = ast.parse(text, filename=str(path))
        rel = path.relative_to(REPO_ROOT).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                kws = {k.arg for k in node.keywords}
                if "cross_text_parallels" in kws:
                    sites.append(f"{rel}:{node.lineno}")
                    if "cross_text_parallels_status" not in kws:
                        missing.append(f"{rel}:{node.lineno}")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assigned = {}
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Attribute):
                                assigned.setdefault(t.attr, []).append(sub.lineno)
                for lineno in assigned.get("cross_text_parallels", []):
                    sites.append(f"{rel}:{lineno}")
                    if "cross_text_parallels_status" not in assigned:
                        missing.append(f"{rel}:{lineno}")
    return sites, missing


def test_every_site_that_fills_section_8_records_its_status():
    sites, missing = _sites_missing_the_status()
    # Positive control: the agent, the static-builder path of invoke_callables
    # and the isolate-mode stub of run_fb32 all fill the section.
    assert len(sites) >= 3, sites
    assert missing == [], missing
