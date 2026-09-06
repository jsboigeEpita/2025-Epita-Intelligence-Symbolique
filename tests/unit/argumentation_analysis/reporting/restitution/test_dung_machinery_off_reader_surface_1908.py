"""#1908 — Dung machinery off the reader surface, digested into the body.

The measured defect (corpus B, R931): Act II recopied the raw Dung payload —
extension enumeration, accepted/rejected IDs, serialized attack edges — and
the framework's ``arguments`` list could carry English position texts
(measured: English descriptions in the rejected set). The reader-met a
solver dump, not a consequence.

This pins the digest contract: the body carries the consequence + the
epistemic caveat (first mention) + an appendix reference; the machinery lives
in the appendix (reconstructable by a forensic reader); non-canonical
argument entries never reach the body; and the readability gate FAILs a
pre-fix artifact in BOTH its July `[tags]` form and its September « » form
(the round's anti-trap).
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)

# --- synthetic state reproducing the measured corpus-B shapes (privacy HARD:
# synthetic opaque English, not real corpus text) -----------------------------


def _state(*, with_english_args: bool = True) -> SimpleNamespace:
    fw_args = (
        [
            "Strictly speaking the deputy overstates the budget impact",
            "The witness is in another city and cannot have seen this",
            "The conclusion does not follow from the premises",
        ]
        if with_english_args
        else ["arg_1", "arg_2"]
    )
    return SimpleNamespace(
        dung_frameworks={
            "fw1": {
                "name": "verification_preferred",
                "arguments": fw_args,
                "attacks": [["arg_1", "arg_3"]],
                "extensions": {"all_members": ["arg_1", "arg_2"]},
            }
        },
        identified_arguments={
            "arg_1": "L'orateur écarte l'opposant par une attaque personnelle.",
            "arg_2": "Une revendication étayée par un raisonnement causal.",
            "arg_3": "Un procès d'intention sur les motifs de l'opposant.",
        },
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        governance_decisions=[],
        debate_transcripts=[],
    )


def _dung_findings(state):
    from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
        _collect_formal_findings,
    )

    return [f for f in _collect_formal_findings(state) if f.kind == "dung"]


# --- negative controls for the gate (rouge d'abord) ---------------------------


class TestGateDetectorNegativeControls:
    """Pre-fix shapes must FAIL the gate — otherwise the detector is inert."""

    def test_measured_dump_verbatim_fails(self):
        # The corpus-B pre-fix dump shape (R931 verbatim, synthetic args).
        body = (
            "Le graphe d'extension preferred : 8 retenu(s), 1 rejeté(s). "
            "Rejetés [Strictly speaking the deputy overstates the budget "
            "impact]. Attaques clés : arg_3→arg_1."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "FAIL"

    def test_guillemets_solver_chain_fails(self):
        # September live form: solver chains in « » instead of [tags].
        body = (
            "La tenue formelle confirme « 2 inférence(s) PL inconsistantes sur "
            "3 vérifiée(s) » et « l'extension grounded ne retient aucun "
            "argument »."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "FAIL"

    def test_july_tags_form_fails(self):
        body = "[PL: 2 inférence(s) inconsistantes] rejetés [arg_1]"
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "FAIL"


class TestGateDetectorAcceptsDigestedBody:
    def test_plain_narrative_prose_passes(self):
        body = (
            "La thèse centrale garde son assise face aux attaques reçues, le "
            "graphe construit sur les arguments extraits ne la fragilise pas. "
            "Le lecteur peut conclure sans jargon de solveur (annexe pour la "
            "traçabilité)."
        )
        verdict = ReadabilityGate().check_body(body)
        assert verdict.band == "PASS"


# --- the digest contract ------------------------------------------------------


class TestAct2DungDigest:
    def test_body_carries_no_machinery(self):
        findings = _dung_findings(_state())
        assert findings, "a decodable graph with rejected args must yield a finding"
        text = findings[0].verdict + " " + findings[0].detail
        for marker in (
            "acceptés [",
            "rejetés [",
            "attaques clés",
            "→",
            "retenu(s)",
            "rejeté(s)",
        ):
            assert marker not in text, f"machinery marker leaked into body: {marker}"

    def test_noncanonical_english_never_reaches_body(self):
        findings = _dung_findings(_state())
        text = findings[0].verdict + " " + findings[0].detail
        for english in (
            "Strictly speaking",
            "cannot have seen this",
            "overstates the budget impact",
        ):
            assert english not in text, f"raw argument text leaked into body: {english}"

    def test_caveat_at_first_mention(self):
        from argumentation_analysis.reporting.restitution.dung_reader import (
            EPISTEMIC_CAVEAT,
        )

        findings = _dung_findings(_state())
        assert EPISTEMIC_CAVEAT in findings[0].verdict

    def test_appendix_reference_names_the_semantics(self):
        findings = _dung_findings(_state())
        assert "Annexe Dung[preferred]" in findings[0].detail

    def test_zero_rejection_still_says_survival(self):
        findings = _dung_findings(_state(with_english_args=False))
        assert findings, "a graph with zero rejections still deserves its finding"
        assert "sans fragiliser aucun argument" in findings[0].verdict


class TestSharedHelperDivergence:
    def test_act2_and_act3_import_the_same_meanings(self):
        from argumentation_analysis.reporting.restitution import (
            act2_narrative_plugin,
            act3_conclusion_plugin,
            dung_reader,
        )

        assert act2_narrative_plugin.EPISTEMIC_CAVEAT is dung_reader.EPISTEMIC_CAVEAT
        assert act2_narrative_plugin.REJECTED_MEANS is dung_reader.REJECTED_MEANS
        assert act2_narrative_plugin.ACCEPTED_MEANS is dung_reader.ACCEPTED_MEANS
        assert act3_conclusion_plugin.REJECTED_MEANS is dung_reader.REJECTED_MEANS


class TestDungAppendixReconstructs:
    def test_appendix_carries_the_extension_and_edges(self):
        from argumentation_analysis.reporting.restitution.appendix import (
            render_appendix,
        )

        state = _state()
        as_dict = {
            "dung_frameworks": state.dung_frameworks,
        }
        html = render_appendix(as_dict)
        assert "Annexe Dung[preferred]" in html
        assert "arg_1 → arg_3" in html  # decisive edge present
        assert "verification_" in html  # protocol / writer provenance

    def test_default_mode_withholds_raw_texts(self):
        from argumentation_analysis.reporting.restitution.appendix import (
            render_appendix,
        )

        state = _state()
        as_dict = {"dung_frameworks": state.dung_frameworks}
        default_html = render_appendix(as_dict)
        assert "cannot have seen this" not in default_html
        full_html = render_appendix(as_dict, include_full_state_json=True)
        assert "cannot have seen this" in full_html
