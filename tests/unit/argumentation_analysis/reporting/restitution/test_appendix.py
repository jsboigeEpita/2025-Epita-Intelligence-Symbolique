"""Tests for the dimensional appendix — provenance counts + leak stripping.

Privacy HARD is the contract here: the appendix summarises counts/verdicts and
must never echo corpus plaintext. ``raw_text`` and snippet keys are stripped
defensively even when the caller asks for the full-state JSON.
"""

from __future__ import annotations

import json

from argumentation_analysis.reporting.restitution.appendix import (
    _provenance_counts,
    _strip_leak_keys,
    render_appendix,
)


def _sample_state():
    return {
        "identified_arguments": {"arg_1": "thèse A", "arg_2": "soutien B"},
        "identified_fallacies": {"f_1": {"type": "ad hominem"}},
        "counter_arguments": [{"counter_content": "x"}],
        "argument_quality_scores": {"arg_1": {"overall": 2.0}},
        "fol_analysis_results": {"consistent": True, "formulas": ["a", "b", "c"]},
        "propositional_analysis_results": {"something": 1},
        "modal_analysis_results": None,
        "dung_frameworks": [],
        "aspic_results": {},
        "narrative_synthesis": "une synthèse",
        "formal_synthesis_reports": None,
        # leak-capable keys that must NEVER reach the appendix
        "raw_text": "SECRET CORPUS PLAINTEXT",
        "raw_text_snippet": "SECRET snippet",
        "full_text": "more secret",
    }


class TestProvenanceCounts:

    def test_counts_reflect_state(self):
        counts = _provenance_counts(_sample_state())
        assert counts["arguments_extraits"] == 2
        assert counts["sophismes_localises"] == 1
        assert counts["contre_arguments"] == 1
        assert counts["scores_qualite"] == 1
        assert counts["axe_fol"] == {"consistent": True, "formules": 3}
        assert counts["axe_pl"] == "disponible"
        assert counts["axe_modale"] == "indisponible"
        assert counts["synthese_narrative"] == "présente"
        assert counts["synthese_formelle"] == "absente"


class TestLeakStripping:

    def test_strip_removes_plaintext_keys(self):
        stripped = _strip_leak_keys(_sample_state())
        assert "raw_text" not in stripped
        assert "raw_text_snippet" not in stripped
        assert "full_text" not in stripped
        # non-leak keys preserved
        assert "identified_arguments" in stripped


class TestRenderAppendix:

    def test_folded_details_block(self):
        out = render_appendix(_sample_state())
        assert out.startswith("\n<details>")
        assert "<summary>" in out
        assert "</details>" in out
        assert "arguments_extraits" in out

    def test_no_corpus_plaintext_by_default(self):
        out = render_appendix(_sample_state())
        assert "SECRET" not in out

    def test_full_state_json_opt_in_strips_leaks(self):
        out = render_appendix(_sample_state(), include_full_state_json=True)
        assert "```json" in out
        assert "SECRET" not in out  # leak keys stripped even in full JSON
        # the JSON block is valid and leak-free
        block = out.split("```json")[1].split("```")[0]
        parsed = json.loads(block)
        assert "raw_text" not in parsed
        assert "identified_arguments" in parsed

    def test_none_state_emits_honest_note(self):
        out = render_appendix(None)
        assert "<details>" in out
        assert "indisponible" in out
        assert "SECRET" not in out
