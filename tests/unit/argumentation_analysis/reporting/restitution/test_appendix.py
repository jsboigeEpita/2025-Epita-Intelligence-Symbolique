"""Tests for the dimensional appendix — provenance counts + leak stripping.

Privacy HARD is the contract here: the appendix summarises counts/verdicts and
must never echo corpus plaintext. ``raw_text`` and snippet keys are stripped
defensively even when the caller asks for the full-state JSON.
"""

from __future__ import annotations

import json

from argumentation_analysis.reporting.restitution.appendix import (
    _fol_axis_status,
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


class TestFolAxisStatusListShape:
    """#1290: the pipeline stores ``fol_analysis_results`` as a *list* of
    per-theory dicts (the shape Acte II reads). The appendix used to recognise
    only a Mapping and labelled every list "indisponible", contradicting the
    prose that cited a real FOL verdict. The axis status must agree with the
    narrative: decided when the reasoner decided, honest-degraded otherwise.
    """

    def test_list_all_consistent_is_decided(self):
        # corpus_A real shape: two theories, both consistent (EProver).
        fol = [
            {"consistent": True, "message": None},
            {
                "consistent": True,
                "message": "FOL consistency check (EProver): consistent",
            },
        ]
        status = _fol_axis_status(fol)
        assert status == {
            "verdict": "décidé",
            "consistantes": 2,
            "inconsistantes": 0,
            "verifiees": 2,
        }

    def test_list_mixed_verdict_is_decided(self):
        # corpus_B real shape: one consistent, one inconsistent.
        fol = [
            {"consistent": True, "message": None},
            {
                "consistent": False,
                "message": "FOL consistency check (EProver): inconsistent",
            },
        ]
        status = _fol_axis_status(fol)
        assert status["verdict"] == "décidé"
        assert status["consistantes"] == 1
        assert status["inconsistantes"] == 1

    def test_list_all_degraded_is_not_decided(self):
        # After the fol_handler #1290 fix, a parse-fail yields consistent=None
        # (degraded). A list of only-None entries must NOT read as decided, and
        # must NOT collapse None→False (#1019/#1278).
        fol = [
            {
                "consistent": None,
                "message": "Degraded: FOL consistency check error (...)",
            },
            {"consistent": None, "message": "Degraded: reasoner unavailable"},
        ]
        status = _fol_axis_status(fol)
        assert status == "indisponible (aucun verdict décidé — dégradé)"

    def test_list_decided_ignores_degraded_entries(self):
        # corpus_C post-fix: one genuinely consistent + one parse-fail degraded.
        # The degraded entry drops out of the decided counts — no fabricated
        # "inconsistante" from a parse error.
        fol = [
            {"consistent": True, "message": None},
            {
                "consistent": None,
                "message": "Degraded: FOL consistency check error (parse)",
            },
        ]
        status = _fol_axis_status(fol)
        assert status["verdict"] == "décidé"
        assert status["consistantes"] == 1
        assert status["inconsistantes"] == 0
        assert status["verifiees"] == 1

    def test_empty_and_none_are_indisponible(self):
        assert _fol_axis_status([]) == "indisponible"
        assert _fol_axis_status(None) == "indisponible"

    def test_legacy_mapping_shape_preserved(self):
        # Back-compat: the old Mapping shape still produces the old summary.
        status = _fol_axis_status({"consistent": True, "formulas": ["a", "b"]})
        assert status == {"consistent": True, "formules": 2}


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
