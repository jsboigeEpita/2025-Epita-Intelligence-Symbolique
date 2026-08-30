"""#1914 (Acte III slice) — the conclusion ranks what carries the verdict.

The #1894 reader-chair verdict, conclusion side: coverage without salience —
every label enumerated at the same level, nothing saying which finding moves
the interpretation, nothing saying what the pipeline established beyond a
strong single-pass reading. This slice derives, deterministically, the
salience ranking (P1 decisif → P2 tension → P3 corroboré/unchallenged
strength) and the zero-shot surplus split (established vs procedural-only),
and wires both into the Acte III evidence bundle and conducted prompt.

What these tests pin (the contract's Act III lines):

* the schema — every ranked item carries a weight, a kind and its opaque
  anchors; ordering is by descending evidential weight;
* non-discriminating results are EXCLUDED from the ranking (ranking an
  all-verified axis anywhere would reintroduce the badge without derivation);
* strengths earn a rank only when unchallenged (strong quality, no localized
  fallacy, not Dung-rejected) — a contested strength is already a tension;
* the reader-chair acceptance criterion — when the only multi-agent matter
  is counters/labels, ``established`` is EMPTY and the rendered prompt
  carries the honest refusal (no interpretive surplus may be claimed);
* the ± pair — same corpus, differing only in what the axes settled: the
  violation prompt can found its verdict on a P1 finding, the settled one
  structurally cannot (canary discipline from #1911/#1939).

The sister file ``test_act3_salience_channel_nered_1914.py`` carries THE
self-contained né-rouge; this file imports ``conclusion_salience``
module-level and would fail wholesale on pre-fix content.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import conclusion_salience as cs
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    StructuredArgFinding,
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.global_projection import GlobalFinding


def _base() -> dict:
    """Shared corpus shape (privacy HARD — opaque ids, no corpus tokens).

    Both states of the ± pair build on this SAME corpus: whatever differs in
    the assertions below must be attributable to the specialist signals,
    never to an argument appearing or disappearing.
    """
    return dict(
        identified_arguments={
            "arg_1": "these A",
            "arg_7": "these B",
            "arg_9": "these C",
        },
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={},
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
        workflow_results={},
    )


def _ns(d: dict) -> SimpleNamespace:
    return SimpleNamespace(**d)


def _q(overall: float, n: int = 10) -> dict:
    """Post-#1923 entry shape: ``overall`` is a SUM over n evaluated virtues
    (#1942) — readers normalize by ``len(scores)``."""
    return {"overall": overall, "scores": {f"vertu_{i}": 0.5 for i in range(n)}}


def _violation_state() -> SimpleNamespace:
    """Same corpus, discriminating signals: FOL refutes a theory, Dung
    excludes arg_9, a fallacy sits on arg_7 with strong quality (tension)
    and on arg_1 with weak quality (corroboration). PL settled all-true."""
    d = _base()
    d["identified_fallacies"] = {
        "f1": {"target_argument_id": "arg_7", "type": "ad_hominem"},
        "f2": {"target_argument_id": "arg_1", "type": "faux dilemme"},
    }
    d["argument_quality_scores"] = {
        "arg_7": _q(8.0),
        "arg_1": _q(3.0),
    }
    d["fol_analysis_results"] = [{"consistent": False, "message": "incoherent"}]
    d["propositional_analysis_results"] = [{"satisfiable": True}]
    d["dung_frameworks"] = {
        "d1": {
            "name": "verification_grounded",
            "arguments": ["arg_1", "arg_9"],
            "attacks": [["arg_9", "arg_1"]],
            "extensions": {"all_members": ["arg_1"]},
        }
    }
    return _ns(d)


def _settled_state() -> SimpleNamespace:
    """Same corpus, everything settled the other way: FOL verifies, no
    fallacies, Dung accepts everyone, one arg has neutral quality."""
    d = _base()
    d["argument_quality_scores"] = {"arg_7": _q(6.0)}
    d["fol_analysis_results"] = [{"consistent": True, "message": "ok"}]
    d["dung_frameworks"] = {
        "d1": {
            "name": "verification_grounded",
            "arguments": ["arg_1", "arg_9"],
            "attacks": [],
            "extensions": {"all_members": ["arg_1", "arg_9"]},
        }
    }
    return _ns(d)


class TestSchema:
    def test_every_ranked_item_carries_weight_kind_and_anchors(self):
        sal = cs.assess_conclusion_salience(_violation_state())
        assert sal.ranked, "fixture must produce ranked items"
        for item in sal.ranked:
            assert item.weight in (1, 2, 3)
            assert item.kind in (
                cs.KIND_VULNERABILITY,
                cs.KIND_TENSION,
                cs.KIND_STRENGTH,
            )
            assert item.cites, f"a {item.kind} item without anchors is untraceable"
            assert item.statement
            assert len(item.statement) <= cs._STATEMENT_CAP

    def test_ranked_ordering_is_descending_evidential_weight(self):
        sal = cs.assess_conclusion_salience(_violation_state())
        weights = [item.weight for item in sal.ranked]
        assert weights == sorted(weights)

    def test_clean_state_ranks_nothing(self):
        sal = cs.assess_conclusion_salience(_ns(_base()))
        assert sal.ranked == []


class TestRanking:
    def test_formal_refutation_ranks_p1(self):
        sal = cs.assess_conclusion_salience(_violation_state())
        p1 = [i for i in sal.ranked if i.weight == 1]
        assert any("FOL" in i.cites for i in p1)

    def test_dung_exclusion_ranks_p1(self):
        sal = cs.assess_conclusion_salience(_violation_state())
        p1 = [i for i in sal.ranked if i.weight == 1]
        assert any("arg_9" in i.cites for i in p1)

    def test_unresolved_tension_ranks_p2(self):
        sal = cs.assess_conclusion_salience(_violation_state())
        p2 = [i for i in sal.ranked if i.weight == 2]
        assert len(p2) == 1
        assert "arg_7" in p2[0].cites
        assert p2[0].kind == cs.KIND_TENSION

    def test_settled_state_ranks_nothing(self):
        sal = cs.assess_conclusion_salience(_settled_state())
        assert sal.ranked == [], "an all-verified run must carry no ranked finding"

    def test_non_discriminating_result_is_excluded_from_the_ranking(self):
        sal = cs.assess_conclusion_salience(_violation_state())
        # PL settled all-true — non-discriminating; it must not appear as a
        # ranked finding (only inside the surplus's procedural half).
        for item in sal.ranked:
            assert not (
                item.weight == 3
                and "PL" in item.cites
                and "satisfiab" in item.statement
            )


class TestStrengths:
    def test_unchallenged_strong_quality_ranks_as_strength(self):
        state = _settled_state()
        state.argument_quality_scores = {"arg_7": _q(9.0)}
        sal = cs.assess_conclusion_salience(state)
        strengths = [i for i in sal.ranked if i.kind == cs.KIND_STRENGTH]
        assert len(strengths) == 1
        assert "arg_7" in strengths[0].cites
        assert strengths[0].weight == 3

    def test_contested_strong_quality_is_not_a_strength(self):
        # arg_7 carries a fallacy AND strong quality — the classifier already
        # carries it as a tension; ranking it a second time as settled ground
        # would present a contested move as a strength.
        sal = cs.assess_conclusion_salience(_violation_state())
        strengths = [i for i in sal.ranked if i.kind == cs.KIND_STRENGTH]
        assert not any("arg_7" in i.cites for i in strengths)

    def test_dung_rejected_argument_is_not_a_strength(self):
        state = _settled_state()
        state.argument_quality_scores = {
            "arg_9": _q(9.0),
            "arg_7": _q(6.0),
        }
        state.dung_frameworks = {
            "d1": {
                "name": "verification_grounded",
                "arguments": ["arg_1", "arg_9"],
                "attacks": [["arg_1", "arg_9"]],
                "extensions": {"all_members": ["arg_1"]},
            }
        }
        sal = cs.assess_conclusion_salience(state)
        strengths = [i for i in sal.ranked if i.kind == cs.KIND_STRENGTH]
        assert not any("arg_9" in i.cites for i in strengths)

    def test_neutral_quality_is_not_a_strength(self):
        sal = cs.assess_conclusion_salience(_settled_state())
        assert not [i for i in sal.ranked if i.kind == cs.KIND_STRENGTH]


class TestSurplus:
    def test_decisive_findings_are_surplus(self):
        sal = cs.assess_conclusion_salience(_violation_state())
        assert sal.surplus.established, "a formal refutation is zero-shot surplus"
        assert any("FOL" in s.cites for s in sal.surplus.established)

    def test_structured_findings_are_surplus(self):
        finding = StructuredArgFinding(
            capability="bipolar_argumentation",
            label="les relations de soutien",
            statement="un cycle de soutien (autorité circulaire)",
        )
        sal = cs.assess_conclusion_salience(
            _settled_state(), structured_findings=[finding]
        )
        assert any("cycle" in s.statement for s in sal.surplus.established)

    def test_llm_only_convergence_is_not_surplus(self):
        # fallacy + weak quality both flag arg_1 — two LLM labelling methods
        # agreeing is convergence, not zero-shot surplus (reader-chair).
        finding = GlobalFinding(
            kind="convergence",
            statement="arg_1 : 2 méthodes indépendantes convergent",
            cites=("arg_1", "qualite faible", "sophisme"),
        )
        sal = cs.assess_conclusion_salience(_settled_state(), global_findings=[finding])
        assert sal.surplus.established == []

    def test_convergence_with_dung_signal_is_surplus(self):
        finding = GlobalFinding(
            kind="convergence",
            statement="arg_1 : 2 méthodes indépendantes convergent",
            cites=("arg_1", "qualite faible", "rejet Dung"),
        )
        sal = cs.assess_conclusion_salience(_settled_state(), global_findings=[finding])
        assert any("convergent" in s.statement for s in sal.surplus.established)

    def test_value_gates_are_not_surplus(self):
        # A gate is the pipeline grading itself — self-assessment, not
        # evidence it beat a reading (#1914 condemns it in the acts).
        finding = GlobalFinding(kind="gate", statement="VG1 : True", cites=("VG1",))
        sal = cs.assess_conclusion_salience(_settled_state(), global_findings=[finding])
        assert sal.surplus.established == []

    def test_counters_are_procedural_not_surplus(self):
        sal = cs.assess_conclusion_salience(_settled_state(), counters_total=4)
        assert sal.surplus.established == []
        assert any("contre-argument" in line for line in sal.surplus.procedural_only)
        assert any("4" in line for line in sal.surplus.procedural_only)

    def test_all_verified_axis_is_procedural(self):
        sal = cs.assess_conclusion_salience(_settled_state())
        assert any(
            "FOL" in line for line in sal.surplus.procedural_only
        ), "an all-verified FOL axis lands in the procedural half"

    def test_surplus_stays_bounded(self):
        findings = [
            cs.SurplusItem(statement=f"r{i}", cites=(f"a{i}",)) for i in range(20)
        ]
        sal = cs.assess_conclusion_salience(
            _violation_state(), structured_findings=findings
        )
        assert len(sal.surplus.established) <= cs._MAX_SURPLUS


class TestReaderChair:
    """The acceptance criterion: a report whose only multi-agent surplus is
    counters/labels must not claim a changed interpretive conclusion."""

    def _labels_and_counters_only_state(self) -> SimpleNamespace:
        # Fallacies localized, quality never ran (no cross verdict), no
        # formal result, Dung accepts everyone, counters generated. The only
        # multi-agent matter is counters + fallacy labels.
        d = _base()
        d["identified_fallacies"] = {
            "f1": {"target_argument_id": "arg_1", "type": "ad_hominem"},
        }
        d["counter_arguments"] = [
            {"target_arg_id": "arg_1", "counter_content": "contre"}
        ]
        return _ns(d)

    def test_no_surplus_established_when_only_counters_and_labels(self):
        state = self._labels_and_counters_only_state()
        sal = cs.assess_conclusion_salience(state, counters_total=1)
        assert sal.surplus.established == []
        assert sal.surplus.procedural_only

    def test_prompt_carries_the_honest_refusal(self):
        state = self._labels_and_counters_only_state()
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "SURPLUS MULTI-AGENTS" in prompt
        assert "RIEN au-delà d'une lecture attentive" in prompt
        assert "NE SONT PAS un surplus" in prompt
        # the counters line itself must land in the procedural half
        assert "PUREMENT PROCÉDURAL" in prompt


class TestBudget:
    def test_ranking_is_capped(self):
        d = _base()
        args = {f"arg_{i}": "weak" for i in range(20)}
        d["identified_arguments"] = args
        d["identified_fallacies"] = {
            f"f{i}": {"target_argument_id": f"arg_{i}", "type": "ad_hominem"}
            for i in range(20)
        }
        # arg_0 at 0.6 spans the weak bar — else the #1942 non-vacuity gate
        # suppresses every corroboration and the cap goes unexercised.
        d["argument_quality_scores"] = {
            f"arg_{i}": _q(6.0 if i == 0 else 2.0) for i in range(20)
        }
        sal = cs.assess_conclusion_salience(_ns(d))
        assert len(sal.ranked) <= cs._MAX_RANKED


class TestActsConsumeTheSalience:
    def test_act3_evidence_and_prompt_carry_the_salience(self):
        evidence = build_act3_evidence(_violation_state())
        assert evidence.salience is not None
        assert evidence.salience.ranked
        prompt = build_act3_prompt(evidence)
        assert "HIÉRARCHIE DU VERDICT" in prompt
        assert "- P1 [" in prompt
        assert "[tension]" in prompt
        assert "SURPLUS MULTI-AGENTS" in prompt
        assert "ÉTABLI" in prompt
        assert "ancres" in prompt

    def test_four_orders_directive_is_rendered(self):
        prompt = build_act3_prompt(build_act3_evidence(_ns(_base())))
        assert "QUATRE ORDRES DE JUGEMENT" in prompt
        assert "VÉRITÉ FACTUELLE" in prompt
        assert "ACCEPTABILITÉ ARGUMENTATIVE" in prompt
        assert "EFFICACITÉ RHÉTORIQUE" in prompt
        assert "PRÉFÉRENCE DE SOLVEUR" in prompt

    def test_difference_is_structural_not_decorative(self):
        """The ± pair: same corpus, only what the axes settled differs.

        The violation prompt can FOUND its verdict on a P1 finding and
        claims established surplus; the settled prompt structurally cannot —
        no P1 line, and the surplus block carries the honest refusal.
        """
        violation = build_act3_prompt(build_act3_evidence(_violation_state()))
        settled = build_act3_prompt(build_act3_evidence(_settled_state()))
        # the rendered DATA line (a ranked finding), not the consigne text
        # which legitimately mentions "les P1 d'abord".
        assert "- P1 [" in violation
        assert "RIEN au-delà d'une lecture attentive" not in violation
        assert "- P1 [" not in settled
        assert "RIEN au-delà d'une lecture attentive" in settled
        # the Dung-excluded argument keeps its corpus presence in both
        # states — the claim excerpt renders in Acte III, only the ranked
        # line disappears (canary discipline; act3 surfaces the claim TEXT,
        # not the arg id, so the canary is the claim itself).
        assert "these C" in settled
        assert "these C" in violation
