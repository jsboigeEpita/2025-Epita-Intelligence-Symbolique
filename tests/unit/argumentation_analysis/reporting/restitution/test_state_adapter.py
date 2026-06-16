"""Tests for the state adapter + the public render_restitution_report shorthand."""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import (
    RestitutionActs,
    render_restitution_report,
    state_to_appendix_mapping,
)

_WOVEN = {
    1: (
        "Le discours analysé (source doc_A) est un propos politique à visée "
        "persuasive. L'orateur cherche à mobiliser l'auditoire; l'asymétrie "
        "d'information joue en sa faveur. Un auditeur averti doit guetter "
        "l'appel à l'autorité typique de ce genre."
    ),
    2: (
        "Le premier mouvement appuie la thèse sur une autorité externe. Cette "
        "autorité ne satisfait pas la question critique de fiabilité: c'est une "
        "exception au scheme ExpertOpinion (ancrage AIF/Walton), et le solveur "
        "Tweety confirme l'inconsistance de l'inférence sous-jacente."
    ),
    3: (
        "L'analyse conclut à un discours fragile sur l'axe formel. La synthèse "
        "honnête, gated par les dimensions non-triviales, caractérise un propos "
        "qui cède sur la logique. Pour contrer: viser la fiabilité."
    ),
}


class TestStateAdapter:

    def test_reads_attributes_off_namespace(self):
        ns = SimpleNamespace(
            identified_arguments={"arg_1": "x"},
            identified_fallacies={"f_1": {}},
            raw_text="SECRET",
        )
        mapping = state_to_appendix_mapping(ns)
        assert mapping["identified_arguments"] == {"arg_1": "x"}
        # raw_text is NOT a spec §2 key → never copied
        assert "raw_text" not in mapping

    def test_reads_keys_off_dict(self):
        mapping = state_to_appendix_mapping({"identified_arguments": {"a": "b"}})
        assert mapping == {"identified_arguments": {"a": "b"}}

    def test_missing_keys_omitted(self):
        mapping = state_to_appendix_mapping(SimpleNamespace())
        assert mapping == {}


class TestPublicShorthand:

    def test_render_restitution_report_one_call(self):
        acts = RestitutionActs(
            act1_framing=_WOVEN[1],
            act2_narrative=_WOVEN[2],
            act3_conclusion=_WOVEN[3],
            source_id="doc_C",
        )
        report = render_restitution_report(acts)
        assert "doc_C" in report.markdown
        assert report.verdict.band == "PASS"
        assert "Gate lisibilité" in report.markdown

    def test_shorthand_with_state_adapter_roundtrip(self):
        ns = SimpleNamespace(identified_arguments={"arg_1": "x"})
        acts = RestitutionActs(
            act1_framing=_WOVEN[1],
            act2_narrative=_WOVEN[2],
            act3_conclusion=_WOVEN[3],
        )
        report = render_restitution_report(acts, state=state_to_appendix_mapping(ns))
        assert "<details>" in report.markdown
        assert "arguments_extraits" in report.markdown
