"""#2046 — internal vocabulary and uncomputed agreement off the reader surface.

Four deterministic defects, all testable without an LLM (per the issue's DoD,
a deterministic guard must redden on each of the four):

* **A** — internal bracket tags (``[pl]``, ``[fol]``, ``[modal]``,
  ``[NON-DISCRIMINANT]``…) fed to the conducted model inside the evidence,
  then recited verbatim into reader prose — the untreated brother channels of
  #2031. The tag must become the readable name (translate, never delete).
* **B** — « N truc(s) » gabarits at sites where the count is in hand at the
  interpolation site: the agreement is computed. The readability gate itself
  tracks ``word(s)`` as a machinery marker (#1908), so every surface that can
  reach the reader must stop carrying the alternation.
* **C** — the degraded-motif join stacking ``.;`` (motifs end with a period,
  the join adds ``"; "``), and the pipeline self-diagnosis (the deterministic
  repair note family) which belongs in the appendix, not the reader
  blockquote — the readable fact (dimension non évaluée) stays with the reader.
* **D** — internal spec pointers (``spec §4``, ``Self-check §4``) off the
  reader surfaces (permanent header line 3, gate-verdict block, per-act
  self-check motifs).
"""

import asyncio
import re

import pytest

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_prompt,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_narrative,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.appendix import render_appendix
from argumentation_analysis.reporting.restitution.pipeline_adapter import (
    build_restitution_acts,
    render_spectacular_restitution,
)
from argumentation_analysis.reporting.restitution.readability_gate import (
    ReadabilityGate,
)
from argumentation_analysis.reporting.restitution.renderer import (
    render_restitution_report,
)
from argumentation_analysis.reporting.restitution.acts import RestitutionActs


class _State:
    """Attribute bag — every restitution reader goes through ``getattr``."""


def _act2_state(
    pl_sat=1,
    pl_unsat=1,
    fol_sat=2,
    fol_unsun=None,
    modal_valid=1,
    modal_invalid=0,
    unattributed=1,
    with_quality=True,
):
    st = _State()
    st.identified_arguments = {
        "arg_1": "première position",
        "arg_2": "seconde position",
    }
    fallacies = {
        "f_1": {
            "type": "appel_a_la_peur",
            "target_argument_id": "arg_1",
            "justification": "j",
        }
    }
    for i in range(unattributed):
        fallacies[f"f_unattr_{i}"] = {
            "type": "autre",
            "target_argument_id": "",
            "justification": "j",
        }
    st.identified_fallacies = fallacies
    st.argument_quality_scores = (
        {"arg_2": {"scores": {"clarte": 0.9, "pertinence": 0.2}, "overall": 2.0}}
        if with_quality
        else {}
    )
    st.propositional_analysis_results = [
        {"id": f"pl_{i}", "satisfiable": True} for i in range(pl_sat)
    ] + [{"id": f"plx_{i}", "satisfiable": False} for i in range(pl_unsat)]
    st.fol_analysis_results = [
        {"id": f"fol_{i}", "consistent": True} for i in range(fol_sat)
    ] + [{"id": f"folx_{i}", "consistent": False} for i in range(fol_unsun or 0)]
    st.modal_analysis_results = [
        {"id": f"m_{i}", "valid": True} for i in range(modal_valid)
    ] + [{"id": f"mx_{i}", "valid": False} for i in range(modal_invalid)]
    st.counter_arguments = []
    st.dung_frameworks = None
    st.deanonymized = True
    st.workflow_results = None
    st.identified_fallacies_families = None
    return st


_MORPHOLOGY_S = re.compile(r"\S\(s\)")
_BRACKET_TAG = re.compile(
    r"\[(pl|fol|modal|dung|convergence|gate|DÉCISIF|CORROBORANT|"
    r"CONTRADICTOIRE|NON-DISCRIMINANT)\]"
)


# --- Défaut A : plus aucune étiquette interne entre crochets dans l'évidence ---


class TestDefectABracketTags:
    def test_act2_prompt_carries_no_internal_bracket_tags(self):
        prompt = build_act2_prompt(build_act2_evidence(_act2_state()))
        assert not _BRACKET_TAG.search(prompt), _BRACKET_TAG.findall(prompt)

    def test_readable_axis_names_carry_instead_of_tags(self):
        prompt = build_act2_prompt(build_act2_evidence(_act2_state()))
        assert "logique propositionnelle" in prompt
        assert "logique du premier ordre" in prompt
        assert "logique modale" in prompt

    def test_role_lines_carry_readable_leads_not_labels(self):
        # decisif via the PL refutation, non-discriminant via the FOL pass
        prompt = build_act2_prompt(build_act2_evidence(_act2_state()))
        assert "Décisif" in prompt
        assert "Non discriminant" in prompt
        # the readable statement the label used to prefix survives untouched
        assert "L'axe PL a réfuté" in prompt

    def test_global_findings_carry_readable_leads(self):
        st = _act2_state()
        # arg_1 carries the fallacy (from _act2_state) AND weak quality → a
        # genuine cross-axis convergence; arg_2 spans the population so the
        # #1942 non-vacuity gate lets the weak signal mean something.
        st.argument_quality_scores = {
            "arg_1": {"scores": {"clarte": 0.1, "pertinence": 0.1}, "overall": 0.5},
            "arg_2": {"scores": {"clarte": 0.9, "pertinence": 0.9}, "overall": 4.0},
        }
        st.workflow_results = {"deep_synthesis_value_gates": {"VG1": True}}
        prompt = build_act2_prompt(build_act2_evidence(st))
        assert not _BRACKET_TAG.search(prompt)
        assert "convergence inter-axes" in prompt
        assert "gate de synthèse" in prompt


# --- Défaut B : l'accord singulier/pluriel se calcule depuis le compte ----------


class TestDefectBAgreement:
    def test_pl_verdict_agrees_with_counts(self):
        ev = build_act2_evidence(_act2_state(pl_sat=1, pl_unsat=1))
        assert (
            "1 inférence PL inconsistante sur 2 vérifiées"
            in ev.formal_findings[0].verdict
        )
        # total == 1 → the trailing participle agrees too (not « sur 1 vérifiées »)
        ev1 = build_act2_evidence(_act2_state(pl_sat=0, pl_unsat=1))
        assert (
            "1 inférence PL inconsistante sur 1 vérifiée"
            in ev1.formal_findings[0].verdict
        )
        ev2 = build_act2_evidence(_act2_state(pl_sat=0, pl_unsat=2))
        assert (
            "2 inférences PL inconsistantes sur 2 vérifiées"
            in ev2.formal_findings[0].verdict
        )
        ev3 = build_act2_evidence(_act2_state(pl_sat=3, pl_unsat=0))
        assert "3 inférences PL consistantes" in ev3.formal_findings[0].verdict

    def test_fol_verdict_agrees_with_counts(self):
        ev = build_act2_evidence(_act2_state(fol_sat=1))
        assert "1 théorie FOL consistante" in ev.formal_findings[1].verdict
        ev2 = build_act2_evidence(_act2_state(fol_sat=2))
        assert "2 théories FOL consistantes" in ev2.formal_findings[1].verdict

    def test_modal_verdict_agrees_with_counts(self):
        ev = build_act2_evidence(_act2_state(modal_valid=1))
        assert "1 théorie modale consistante" in ev.formal_findings[2].verdict
        ev2 = build_act2_evidence(_act2_state(modal_valid=2))
        assert "2 théories modales consistantes" in ev2.formal_findings[2].verdict

    def test_quality_observation_line_agrees(self):
        # 1 evaluated virtue → singular noun AND singular verb
        st = _act2_state()
        st.argument_quality_scores = {
            "arg_2": {"scores": {"clarte": 0.9}, "overall": 1.0}
        }
        prompt = build_act2_prompt(build_act2_evidence(st))
        assert "1 dimension sur" in prompt and "était jugeable" in prompt
        st2 = _act2_state()
        st2.argument_quality_scores = {
            "arg_2": {"scores": {"clarte": 0.9, "pertinence": 0.2}, "overall": 2.0}
        }
        prompt2 = build_act2_prompt(build_act2_evidence(st2))
        assert "2 dimensions sur" in prompt2 and "étaient jugeables" in prompt2

    def test_unattributed_block_agrees(self):
        ev = build_act2_evidence(_act2_state(unattributed=1))
        assert ev.unattributed_fallacies == 1
        prompt = build_act2_prompt(ev)
        assert "1 sophisme détecté" in prompt
        ev2 = build_act2_evidence(_act2_state(unattributed=2))
        assert "2 sophismes détectés" in build_act2_prompt(ev2)

    def test_act1_inventory_agrees(self):
        st = _act2_state()
        prompt = build_act1_prompt(build_act1_evidence(st))
        assert "2 arguments extraits" in prompt
        st2 = _act2_state()
        st2.identified_arguments = {"arg_1": "seule position"}
        assert "1 argument extrait" in build_act1_prompt(build_act1_evidence(st2))

    def test_act3_absent_dimensions_motif_agrees(self):
        # Through the REAL builder: the #1605 motif is filed in
        # build_act3_conclusion's weaving path, so the agreement must be
        # proven on the filed degraded dict, not on evidence labels alone.
        async def llm(prompt):
            return "### Synthèse\n" + "Une prose honnête ancrée sur les axes. " * 20

        st = _State()
        st.identified_arguments = {"arg_1": "position"}
        st.identified_fallacies = {}
        st.argument_quality_scores = {}
        st.propositional_analysis_results = None
        st.fol_analysis_results = None
        st.modal_analysis_results = None
        st.counter_arguments = []
        st.dung_frameworks = None
        st.deanonymized = True
        st.workflow_results = None
        st.structured_arg_status = {
            "bipolar_support_reasoning": {
                "capability": "bipolar_support_reasoning",
                "status": "not_evaluated",
                "degraded": True,
                "reason": "translator raised",
            }
        }
        st.source_metadata = {}
        st.stakes_and_stakeholders = None
        st.interpretive_question = ""
        result = asyncio.run(build_act3_conclusion(st, llm_callable=llm))
        assert result.degraded["act3_absent_dimensions"].startswith(
            "1 dimension non évaluée sur ce corpus"
        )

        st2 = _State()
        for k, v in vars(st).items():
            setattr(st2, k, v)
        st2.structured_arg_status = {
            "bipolar_support_reasoning": {
                "status": "not_evaluated",
                "degraded": True,
                "reason": "translator raised",
            },
            "aspic_plus_reasoning": {
                "status": "not_evaluated",
                "degraded": True,
                "reason": "empty environment",
            },
        }
        result2 = asyncio.run(build_act3_conclusion(st2, llm_callable=llm))
        assert result2.degraded["act3_absent_dimensions"].startswith(
            "2 dimensions non évaluées sur ce corpus"
        )

    def test_gate_reasons_agree(self):
        gate = ReadabilityGate()
        body_one = "### Titre\n" + "Le cadre Tweety appuie le récit. " * 8
        body_two = (
            "### Titre\n"
            + "Le cadre Tweety appuie le récit. Le cadre Dung appuie le récit. " * 8
        )
        acts = RestitutionActs(
            act1_framing=body_one * 3,
            act2_narrative=body_two,
            act3_conclusion=body_one * 3,
            source_id="doc_X",
        )
        report = render_restitution_report(acts)
        assert not _MORPHOLOGY_S.search(report.markdown), _MORPHOLOGY_S.findall(
            report.markdown
        )

    def test_appendix_raw_entries_agree(self):
        state = {
            "dung_frameworks": {
                "verification_dung": {
                    "name": "verification_dung",
                    "arguments": [
                        "arg_1",
                        "Some raw English position text ending with a period.",
                    ],
                    "attacks": [
                        [
                            "arg_1",
                            "Some raw English position text ending with a period.",
                        ]
                    ],
                    "extensions": {"preferred": ["arg_1"]},
                }
            }
        }
        appendix = render_appendix(state)
        assert not _MORPHOLOGY_S.search(appendix), _MORPHOLOGY_S.findall(appendix)

    def test_act2_prompt_sweep_no_morphology_s(self):
        prompt = build_act2_prompt(build_act2_evidence(_act2_state()))
        assert not _MORPHOLOGY_S.search(prompt), _MORPHOLOGY_S.findall(prompt)

    def test_act1_prompt_sweep_no_morphology_s(self):
        prompt = build_act1_prompt(build_act1_evidence(_act2_state()))
        assert not _MORPHOLOGY_S.search(prompt), _MORPHOLOGY_S.findall(prompt)


# --- Défaut C : jointure et routage de l'auto-diagnostic ------------------------


def _degraded_state():
    st = _State()
    st.act1_framing = ""
    st.act2_narrative = ""
    st.act3_conclusion = ""
    st.source_metadata = {}
    st.restitution_acts_degraded = {
        "act3_conclusion": {
            "act3_absent_dimensions": (
                "1 dimension non évaluée sur ce corpus : la force pondérée des "
                "attaques."
            ),
            "act3_scope_note_appended": (
                "La prose conduite ne rattachait aucune limitation aux axes "
                "perdus — paragraphe de portée ajouté de façon déterministe."
            ),
        }
    }
    return st


class TestDefectCJoinAndRouting:
    def test_join_does_not_stack_period_and_semicolon(self):
        acts = build_restitution_acts(_degraded_state())
        motif = acts.degraded["act3_conclusion"]
        assert ".;" not in motif
        assert motif.endswith(".")

    def test_fabrication_note_off_the_reader_blockquote(self):
        acts = build_restitution_acts(_degraded_state())
        assert "déterministe" not in acts.degraded.get("act3_conclusion", "")

    def test_fabrication_note_rendered_in_appendix(self):
        report = render_spectacular_restitution(_degraded_state())
        appendix = report.markdown[report.markdown.find("<details>") :]
        assert "paragraphe de portée ajouté" in appendix

    def test_readable_fact_stays_with_the_reader(self):
        report = render_spectacular_restitution(_degraded_state())
        body = report.markdown[: report.markdown.find("<details>")]
        assert "1 dimension non évaluée" in body

    def test_appendix_attack_edges_do_not_stack_period_and_semicolon(self):
        state = {
            "dung_frameworks": {
                "verification_dung": {
                    "name": "verification_dung",
                    "arguments": [
                        "arg_1",
                        "First raw position.",
                        "Second raw position.",
                    ],
                    "attacks": [
                        ["arg_1", "First raw position."],
                        ["arg_1", "Second raw position."],
                    ],
                    "extensions": {"preferred": ["arg_1"]},
                }
            }
        }
        appendix = render_appendix(state)
        assert ".;" not in appendix


# --- Défaut D : références de spec hors des surfaces lecteur -------------------


class TestDefectDSpecRefs:
    def _rendered(self):
        body = "### Titre\n" + "Une prose tissée et ancrée qui conduit le récit. " * 10
        acts = RestitutionActs(
            act1_framing=body,
            act2_narrative=body,
            act3_conclusion=body,
            source_id="doc_X",
        )
        return render_restitution_report(acts)

    def test_header_carries_no_spec_ref(self):
        md = self._rendered().markdown
        assert "spec §4" not in md

    def test_verdict_block_carries_no_spec_ref(self):
        md = self._rendered().markdown
        assert "§4" not in md

    @pytest.mark.asyncio
    async def test_gate_self_check_motif_carries_no_spec_ref(self):
        async def llm(prompt):
            return "Court."  # thin body → gate band != PASS → motif filed

        result = await build_act2_narrative(_act2_state(), llm_callable=llm)
        motifs = " ".join(result.degraded.values())
        if "Self-check" in motifs or "Autocontr" in motifs:
            assert "§4" not in motifs

    @pytest.mark.asyncio
    async def test_gate_self_check_motif_off_reader_blockquote(self):
        async def llm(prompt):
            return "Court."

        result = await build_act2_narrative(_act2_state(), llm_callable=llm)
        st = _act2_state()
        st.act1_framing = "x" * 200
        st.act2_narrative = "y" * 200
        st.act3_conclusion = "z" * 200
        st.source_metadata = {}
        st.restitution_acts_degraded = {
            "act2_narrative": result.degraded,
        }
        report = render_spectacular_restitution(st)
        body = report.markdown[: report.markdown.find("<details>")]
        gate_motif_keys = (k for k in result.degraded if "gate" in k)
        for key in gate_motif_keys:
            assert result.degraded[key] not in body
