"""Tests for the dimensional appendix — provenance counts + leak stripping.

Privacy HARD is the contract here: the appendix summarises counts/verdicts and
must never echo corpus plaintext. ``raw_text`` and snippet keys are stripped
defensively even when the caller asks for the full-state JSON.
"""

from __future__ import annotations

import json

from argumentation_analysis.reporting.restitution.appendix import (
    _fol_axis_status,
    _modal_axis_status,
    _pl_axis_status,
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

    def test_list_decided_surfaces_degraded_entries(self):
        # corpus_B/C post-fix: one genuinely consistent + one parse-fail degraded.
        # #1276 (po-2023 R487): the degraded entry stays OUT of the decided
        # counts (no fabricated "inconsistante" from a parse error) but MUST be
        # surfaced as ``degradees`` — otherwise ``verifiees: 1`` reads as full
        # coverage while a second theory in fact degraded (silent omission #1019,
        # the annex contradicting the prose's tri-state honesty #1292).
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
        assert status["degradees"] == 1  # the degraded theory is now visible

    def test_list_all_decided_has_no_degradees_key(self):
        # corpus_A: both consistent, no degraded — the ``degradees`` key must be
        # absent (no noise on fully-decided corpora).
        fol = [
            {"consistent": True, "message": None},
            {"consistent": True, "message": None},
        ]
        status = _fol_axis_status(fol)
        assert "degradees" not in status

    def test_empty_and_none_are_indisponible(self):
        assert _fol_axis_status([]) == "indisponible"
        assert _fol_axis_status(None) == "indisponible"

    def test_legacy_mapping_shape_preserved(self):
        # Back-compat: the old Mapping shape still produces the old summary.
        status = _fol_axis_status({"consistent": True, "formulas": ["a", "b"]})
        assert status == {"consistent": True, "formules": 2}


class TestModalAxisStatus:
    """#1276 (po-2023 R487): the modal axis was reduced to a binary presence flag
    even when SPASS decided ``valid=True`` (capstone 3/3). The appendix must
    surface the real tri-state verdict (decided / degraded / unavailable),
    mirroring ``axe_fol`` — never collapse None→False (#1019/#1279).
    """

    def test_list_decided_surfaces_verdict(self):
        # capstone shape: a decided modal theory (valid=True via SPASS)
        modal = [{"valid": True, "message": None}]
        status = _modal_axis_status(modal)
        assert status["verdict"] == "décidé"
        assert status["consistantes"] == 1
        assert status["inconsistantes"] == 0
        assert status["verifiees"] == 1
        assert "degradees" not in status

    def test_list_mixed_decided_and_degraded_surfaces_degradees(self):
        modal = [
            {"valid": True, "message": None},
            {"valid": None, "message": "unavailable:no-translation"},
        ]
        status = _modal_axis_status(modal)
        assert status["verifiees"] == 1
        assert status["degradees"] == 1  # the degraded theory is visible, not dropped

    def test_list_degraded_only_is_honest_unavailable(self):
        # ran but could not decide — NOT a bare "indisponible" (axis never ran)
        modal = [{"valid": None, "message": "unavailable:no-solver"}]
        assert _modal_axis_status(modal) == "indisponible (aucun verdict décidé — dégradé)"

    def test_external_solver_mapping_shape(self):
        # SPASS external-solver path (state_writers external_valid)
        status = _modal_axis_status({"external_solver": "spass", "external_valid": True})
        assert status == {"verdict": "décidé", "consistante": True}

    def test_empty_and_none_are_indisponible(self):
        assert _modal_axis_status([]) == "indisponible"
        assert _modal_axis_status(None) == "indisponible"


class TestPlAxisStatus:
    """#1276 (po-2023 R487): the PL axis was flattened to "disponible" even when
    PySAT decided satisfiability. Surface the verdict tri-state, mirroring
    ``axe_fol``. Canonical key ``satisfiable`` (#1151), legacy ``consistent``.
    """

    def test_list_decided_surfaces_verdict(self):
        pl = [
            {"satisfiable": True},
            {"satisfiable": False},
        ]
        status = _pl_axis_status(pl)
        assert status["verdict"] == "décidé"
        assert status["satisfiables"] == 1
        assert status["insatisfiables"] == 1
        assert status["verifiees"] == 2
        assert "degradees" not in status

    def test_legacy_consistent_key_fallback(self):
        pl = [{"consistent": True}]
        status = _pl_axis_status(pl)
        assert status["satisfiables"] == 1

    def test_list_mixed_decided_and_degraded(self):
        pl = [{"satisfiable": True}, {"satisfiable": None}]
        status = _pl_axis_status(pl)
        assert status["verifiees"] == 1
        assert status["degradees"] == 1

    def test_mapping_without_verdict_stays_disponible(self):
        # back-compat: a non-empty mapping with no parseable verdict is still
        # honestly "disponible" (data present), not a fabricated verdict
        assert _pl_axis_status({"something": 1}) == "disponible"

    def test_empty_and_none_are_indisponible(self):
        assert _pl_axis_status([]) == "indisponible"
        assert _pl_axis_status(None) == "indisponible"


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
