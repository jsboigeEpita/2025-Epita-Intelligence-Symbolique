"""#1914 (Acte II slice) — specialist results carry an evidential role.

The #1894 verdict: the acts expose solver badges and coverage counts without
telling the reader which result CHANGES the judgment. This slice wires the
deterministic four-role classification (decisif / corroborant /
contradictoire / non-discriminant) into the Acte II evidence bundle and
conducted prompt.

What these tests pin (the dispatch DoD):

* the schema — every assignment names one of the four roles and cites its
  opaque anchors, never a bare badge;
* the roles are DERIVED, not asked — each predicate is exercised in both
  directions (the triggering state and the near-miss state);
* the structural difference — two states sharing the SAME corpus, differing
  only in what the specialist axes settled, produce prompts whose
  AFFIRMABLE content differs (a decisive line exists vs structurally
  cannot);
* THE self-contained né-rouge — ``test_act2_evidence_carries_role_assignments``
  imports only modules that exist on main; pre-fix it reddens with
  ``AttributeError`` (missing field), never ``ImportError``.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import specialist_roles as sr
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)


def _base() -> dict:
    """Shared corpus shape (privacy HARD — opaque ids, no corpus tokens).

    Both states of the ± pair build on this SAME corpus (canary discipline
    from #1911/#1939): whatever differs in the assertions below must be
    attributable to the specialist signals, never to an argument appearing
    or disappearing.
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


def _violation_state() -> SimpleNamespace:
    """Same corpus as _settled_state, with discriminating specialist signals:
    FOL refutes a theory, Dung excludes arg_9, a fallacy sits on arg_7 whose
    measured quality is strong (contradiction) and on arg_1 whose quality is
    weak (corroboration). PL settled all-true (non-discriminating)."""
    d = _base()
    d["identified_fallacies"] = {
        "f1": {"target_argument_id": "arg_7", "type": "ad_hominem"},
        "f2": {"target_argument_id": "arg_1", "type": "faux dilemme"},
    }
    d["argument_quality_scores"] = {
        "arg_7": {"overall": 8.0},
        "arg_1": {"overall": 3.0},
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
    """Same corpus, everything settled the OTHER way: FOL verifies (nothing
    refuted), no fallacies, Dung accepts everyone. The only classifiable
    results are non-discriminating."""
    d = _base()
    d["argument_quality_scores"] = {
        "arg_7": {"overall": 8.0},
        "arg_1": {"overall": 6.0},
    }
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
    def test_every_assignment_names_a_role_and_cites_anchors(self):
        assignments = sr.classify_specialist_roles(_violation_state())
        assert assignments, "fixture must produce assignments"
        for a in assignments:
            assert a.role in sr.ROLE_ORDER
            assert a.cites, f"a {a.role} assignment without anchors is untraceable"
            assert a.statement
            assert len(a.statement) <= sr._STATEMENT_CAP

    def test_roles_render_in_descending_evidential_weight(self):
        assignments = sr.classify_specialist_roles(_violation_state())
        order_index = {role: i for i, role in enumerate(sr.ROLE_ORDER)}
        positions = [order_index[a.role] for a in assignments]
        assert positions == sorted(positions)


class TestDecisive:
    def test_formal_violation_is_decisive(self):
        assignments = sr.classify_specialist_roles(_violation_state())
        decisive = [a for a in assignments if a.role == sr.ROLE_DECISIF]
        fol = [a for a in decisive if "FOL" in a.cites]
        assert fol, "a refuted FOL theory must be classified decisive"
        assert "réfuté" in fol[0].statement or "refuté" in fol[0].statement

    def test_dung_exclusion_is_decisive_per_argument(self):
        assignments = sr.classify_specialist_roles(_violation_state())
        dung = [
            a for a in assignments if a.role == sr.ROLE_DECISIF and "arg_9" in a.cites
        ]
        assert dung, "arg_9 excluded from the accepted extension must be decisive"
        assert "Dung" in dung[0].cites[1]

    def test_settled_true_formal_axis_is_not_decisive(self):
        assignments = sr.classify_specialist_roles(_settled_state())
        assert not [a for a in assignments if a.role == sr.ROLE_DECISIF]

    def test_absent_axis_has_no_role(self):
        # An axis that never ran has no role at all — its honest absence
        # stays in the existing channels; absence ≠ non-discriminating.
        state = _ns(_base())  # every formal list empty
        assignments = sr.classify_specialist_roles(state)
        assert assignments == []


class TestContradictory:
    def test_fallacy_with_strong_quality_is_a_contradiction(self):
        assignments = sr.classify_specialist_roles(_violation_state())
        contra = [a for a in assignments if a.role == sr.ROLE_CONTRADICTOIRE]
        assert len(contra) == 1
        assert "arg_7" in contra[0].cites
        assert {"sophisme", "qualite"} <= set(contra[0].cites)

    def test_neutral_quality_is_not_a_contradiction(self):
        # 6.0/10 sits between the weak and strong thresholds — the quality
        # axis says nothing either way, so no cross verdict exists.
        state = _violation_state()
        state.argument_quality_scores = {
            "arg_7": {"overall": 6.0},
            "arg_1": {"overall": 3.0},
        }
        assignments = sr.classify_specialist_roles(state)
        assert not [a for a in assignments if a.role == sr.ROLE_CONTRADICTOIRE]
        # Bilateral, as the docstring promises: arg_7's neutral quality yields
        # no cross verdict AT ALL — neither contradiction nor corroboration
        # (arg_1 at 3.0 legitimately corroborates; the assert targets arg_7).
        # The elif→else mutation (coord R883) must redden here, not pass.
        assert not [
            a
            for a in assignments
            if a.role == sr.ROLE_CORROBORANT and "arg_7" in a.cites
        ]

    def test_strong_quality_without_fallacy_is_not_a_contradiction(self):
        # One method alone is an axis result — a role needs a cross verdict.
        state = _settled_state()
        state.argument_quality_scores = {"arg_7": {"overall": 9.0}}
        assignments = sr.classify_specialist_roles(state)
        assert not [a for a in assignments if a.role == sr.ROLE_CONTRADICTOIRE]


class TestCorroborant:
    def test_fallacy_with_weak_quality_corroborates(self):
        assignments = sr.classify_specialist_roles(_violation_state())
        corrob = [a for a in assignments if a.role == sr.ROLE_CORROBORANT]
        assert len(corrob) == 1
        assert "arg_1" in corrob[0].cites

    def test_weak_quality_without_fallacy_corroborates_nothing(self):
        state = _settled_state()
        state.argument_quality_scores = {"arg_1": {"overall": 2.0}}
        assignments = sr.classify_specialist_roles(state)
        assert not [a for a in assignments if a.role == sr.ROLE_CORROBORANT]


class TestNonDiscriminating:
    def test_all_settled_true_axis_moves_nothing(self):
        assignments = sr.classify_specialist_roles(_violation_state())
        nd = [a for a in assignments if a.role == sr.ROLE_NON_DISCRIMINANT]
        assert any(
            "PL" in a.cites for a in nd
        ), "all-satisfiable PL is non-discriminating"

    def test_undecodable_extension_is_non_discriminating(self):
        state = _settled_state()
        state.dung_frameworks = {
            "d1": {
                "name": "verification_grounded",
                "arguments": ["arg_1"],
                "attacks": [],
                "extensions": {"weird_shape": 42},
            }
        }
        assignments = sr.classify_specialist_roles(state)
        nd = [a for a in assignments if a.role == sr.ROLE_NON_DISCRIMINANT]
        assert any("Dung grounded" in a.cites for a in nd)


class TestBudget:
    def test_each_role_is_capped(self):
        d = _base()
        args = {f"arg_{i}": "weak" for i in range(20)}
        d["identified_arguments"] = args
        d["identified_fallacies"] = {
            f"f{i}": {"target_argument_id": f"arg_{i}", "type": "ad_hominem"}
            for i in range(20)
        }
        d["argument_quality_scores"] = {f"arg_{i}": {"overall": 2.0} for i in range(20)}
        d["dung_frameworks"] = {
            "d1": {
                "name": "verification_grounded",
                "arguments": [f"arg_{i}" for i in range(20)],
                "attacks": [],
                "extensions": {"all_members": []},
            }
        }
        assignments = sr.classify_specialist_roles(_ns(d))
        by_role: dict = {}
        for a in assignments:
            by_role.setdefault(a.role, []).append(a)
        for role, items in by_role.items():
            assert len(items) <= sr._MAX_PER_ROLE, f"{role} exceeds the budget"


class TestActsConsumeTheHierarchy:
    def test_act2_evidence_and_prompt_carry_the_roles(self):
        evidence = build_act2_evidence(_violation_state())
        assert evidence.role_assignments, "the classifier must run on the state"
        prompt = build_act2_prompt(evidence)
        assert "RÔLES DES RÉSULTATS DE SPÉCIALISTES" in prompt
        assert "[DÉCISIF]" in prompt
        assert "[CONTRADICTOIRE]" in prompt
        assert "arg_7" in prompt
        assert "ancres" in prompt

    def test_difference_is_structural_not_decorative(self):
        """The dispatch DoD pair: same corpus ± what the axes settled.

        In the violation state the prompt carries a DÉCISIF line (a formal
        refutation exists — the narrative CAN claim a tested theory fails)
        and a CONTRADICTOIRE line. In the settled state neither line exists
        and the FOL axis renders NON-DISCRIMINANT — the narrative
        structurally cannot claim any formal finding moves the judgment.
        """
        violation = build_act2_prompt(build_act2_evidence(_violation_state()))
        settled = build_act2_prompt(build_act2_evidence(_settled_state()))
        assert "[DÉCISIF]" in violation
        assert "[CONTRADICTOIRE]" in violation
        assert "arg_9" in violation
        assert "[DÉCISIF]" not in settled
        assert "[CONTRADICTOIRE]" not in settled
        assert "[CORROBORANT]" not in settled
        assert "[NON-DISCRIMINANT]" in settled
        # the Dung-excluded argument keeps its corpus presence in both
        # states — only the ROLE line disappears (canary discipline).
        assert "arg_9" in settled

    def test_clean_state_renders_honest_absence(self):
        prompt = build_act2_prompt(build_act2_evidence(_ns(_base())))
        assert "RÔLES DES RÉSULTATS DE SPÉCIALISTES" in prompt
        assert "aucun résultat de spécialiste" in prompt
        assert "[DÉCISIF]" not in prompt

    def test_prompt_section_stays_bounded(self):
        evidence = build_act2_evidence(_violation_state())
        section = "\n".join(a.statement for a in evidence.role_assignments)
        assert len(section) <= 4 * sr._MAX_PER_ROLE * sr._STATEMENT_CAP
