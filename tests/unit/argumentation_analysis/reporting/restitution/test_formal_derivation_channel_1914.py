# -*- coding: utf-8 -*-
"""#1914 (constat 1, tranche Acte II) — the formal-derivation channel.

« Solver badges without derivations » : the reader used to receive
« N inférences PL inconsistantes sur M vérifiées » with no hint of WHAT was
tested. The state records carry the tested content (``formulas``) — these
tests pin that both Acte II surfaces now hand it over, and that a
placeholder-only record yields the honest absence instead of a dressed-up
counter.

The synthetic records below mirror the shapes measured on real dumps
(underscored atom identifiers, operator clauses, and the CL/DL/QBF
placeholder strings the writers emit when they carried no real formula).
Opaque/neutral atoms only — no corpus content (privacy HARD).
"""

from types import SimpleNamespace

import pytest

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    _collect_formal_findings,
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.formal_derivation import (
    extract_tested_content,
)
from argumentation_analysis.reporting.restitution.specialist_roles import (
    ROLE_DECISIF,
    classify_specialist_roles,
)


def _pl_verdict(r):
    sat = r.get("satisfiable")
    if sat is None:
        sat = r.get("consistent")
    return sat if isinstance(sat, bool) else None


def _fol_verdict(r):
    v = r.get("consistent")
    return v if isinstance(v, bool) else None


def _modal_verdict(r):
    v = r.get("valid")
    return v if isinstance(v, bool) else None


class TestExtraction:
    """The extraction helper itself — anti-fabrication contract."""

    def test_refuted_record_yields_tested_atoms(self):
        records = [
            {
                "formulas": ["device_is_broken", "economy_strong || borders_safe"],
                "satisfiable": False,
            }
        ]
        out = extract_tested_content(records, _pl_verdict, refuted=True)
        assert out is not None
        assert "device is broken" in out
        assert "economy strong" in out

    def test_refuted_selection_ignores_verified_records(self):
        """The derivation of a refutation is WHAT FAILED — the verified
        record's formulas must not be quoted as the tested content."""
        records = [
            {"formulas": ["verified_atom_a"], "satisfiable": True},
            {"formulas": ["refuted_atom_b"], "satisfiable": False},
        ]
        out = extract_tested_content(records, _pl_verdict, refuted=True)
        assert "refuted atom b" in out
        assert "verified atom a" not in out

    def test_placeholder_only_yields_none(self):
        """CL(/DL:/QBF: status strings and URL-bearing pastes are not
        derivations — None, never a dressed-up counter."""
        records = [
            {
                "formulas": [
                    "CL(0 conditionals): No query specified — KB constructed.",
                    "DL: Knowledge base is consistent.",
                    "QBF: Title: some title | Rev URL Source: https://example.test/x",
                ],
                "satisfiable": False,
            }
        ]
        assert extract_tested_content(records, _pl_verdict, refuted=True) is None

    def test_underscores_become_readable_and_counts_pluralize(self):
        records = [
            {
                "formulas": [
                    "a_first_atom",
                    "b_second_atom",
                    "c_third_atom",
                    "d_fourth_atom",
                    "e_fifth_atom",
                ],
                "satisfiable": False,
            }
        ]
        out = extract_tested_content(records, _pl_verdict, refuted=True)
        assert "a first atom" in out
        assert "(+2 autres formules)" in out

    def test_atom_cap_truncates_long_formulas(self):
        records = [{"formulas": ["x" * 200], "satisfiable": False}]
        out = extract_tested_content(records, _pl_verdict, refuted=True)
        assert out is not None
        assert len(out) < 100  # bounded, never a wall of formula


class TestAct2AnchorChannel:
    """The TENUE FORMELLE anchor carries the derivation (or its absence)."""

    def test_refuted_axis_finding_carries_tested(self):
        state = SimpleNamespace(
            propositional_analysis_results=[
                {"formulas": ["device_is_broken"], "satisfiable": False}
            ],
            fol_analysis_results=None,
            modal_analysis_results=None,
        )
        findings = _collect_formal_findings(state)
        pl = next(f for f in findings if f.kind == "pl")
        assert pl.tested is not None
        assert "device is broken" in pl.tested

    def test_placeholder_axis_finding_tested_is_none(self):
        state = SimpleNamespace(
            propositional_analysis_results=None,
            fol_analysis_results=[
                {"formulas": ["DL: Knowledge base is consistent."], "consistent": False}
            ],
            modal_analysis_results=None,
        )
        findings = _collect_formal_findings(state)
        fol = next(f for f in findings if f.kind == "fol")
        assert fol.tested is None

    def test_all_verified_axis_carries_sample_of_what_passed(self):
        state = SimpleNamespace(
            propositional_analysis_results=[
                {"formulas": ["verified_atom"], "satisfiable": True}
            ],
            fol_analysis_results=None,
            modal_analysis_results=None,
        )
        findings = _collect_formal_findings(state)
        pl = next(f for f in findings if f.kind == "pl")
        assert pl.tested is not None
        assert "verified atom" in pl.tested


class TestPromptWeaving:
    """The conducted prompt carries the derivation AND the contract."""

    @staticmethod
    def _state():
        return SimpleNamespace(
            propositional_analysis_results=[
                {
                    "formulas": ["device_is_broken", "economy_strong || borders_safe"],
                    "satisfiable": False,
                }
            ],
            fol_analysis_results=[
                {"formulas": ["DL: Knowledge base is consistent."], "consistent": False}
            ],
            modal_analysis_results=None,
            identified_arguments={"arg_1": {"id": "arg_1", "description": "d"}},
            identified_fallacies=None,
            argument_quality_scores=None,
        )

    @staticmethod
    def _prompt():
        from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
            build_act2_prompt,
        )

        return build_act2_prompt(build_act2_evidence(TestPromptWeaving._state()))

    def test_prompt_carries_tested_fragment_and_absence(self):
        prompt = self._prompt()
        assert "testé : « device is broken »" in prompt
        # the placeholder-only axis says the honest absence, not a derivation
        assert "contenu testé non disponible dans l'état" in prompt

    def test_prompt_carries_the_derivation_contract(self):
        prompt = self._prompt()
        # the three-part contract binds the conductor
        assert "CE QUI A ÉTÉ TESTÉ" in prompt
        assert "CE QUI A ÉTÉ ÉTABLI" in prompt
        assert "CE QUE ÇA CHANGE" in prompt
        # and forbids inventing a derivation for a bare counter
        assert "INTERDIT de lui inventer" in prompt


class TestDecisifRoleCarriesDerivation:
    """The #1914 role statement — the badge becomes a derivation."""

    def test_decisif_statement_carries_tested_content(self):
        state = SimpleNamespace(
            propositional_analysis_results=[
                {"formulas": ["device_is_broken"], "satisfiable": False}
            ],
            fol_analysis_results=None,
            modal_analysis_results=None,
            identified_arguments={},
            identified_fallacies=None,
            argument_quality_scores=None,
        )
        assignments = classify_specialist_roles(state)
        decisif = [a for a in assignments if a.role == ROLE_DECISIF]
        assert decisif, "a settled PL refutation must classify decisif"
        assert "à l'épreuve : « device is broken »" in decisif[0].statement

    def test_decisif_statement_says_honest_absence_for_placeholders(self):
        state = SimpleNamespace(
            propositional_analysis_results=None,
            fol_analysis_results=[
                {"formulas": ["DL: Knowledge base is consistent."], "consistent": False}
            ],
            modal_analysis_results=None,
            identified_arguments={},
            identified_fallacies=None,
            argument_quality_scores=None,
        )
        assignments = classify_specialist_roles(state)
        decisif = [
            a for a in assignments if a.role == ROLE_DECISIF and "FOL" in a.cites
        ]
        assert decisif
        assert "contenu testé non disponible" in decisif[0].statement
