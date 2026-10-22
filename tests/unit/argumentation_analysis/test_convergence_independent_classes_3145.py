"""#3145 + #3133 remaining leg: convergence counts independent signal CLASSES.

The R1106 paid pass measured it on a real render: ``compute_argument_convergence``
counts five signals as methods, but two of them are not independent witnesses
of anything —

* ``JTMS retracte`` is SET by the fallacy (``_invoke_jtms`` step 4 creates a
  defeat justification per detected fallacy and retracts the targeted
  argument: the retraction is the fallacy, re-encoded);
* ``contre-argument`` fired on 10/10 sampled units of the run — the counter
  phase reads the same stratified selection as the per-argument fallacy
  reading, so on that run the signal discriminates nothing (#1942 shape on
  the counter axis).

So arg units showed "three independent methods" for one fallacy detection,
its JTMS echo, and membership in the sample. The remaining leg of #3133 is
the twin reader ``specialist_roles``, still on the penalised
``quality_fraction``.

Contract tested here (offline, synthetic, no corpus text, no LLM, no JVM):

* ``score`` counts INDEPENDENT classes only: ``sophisme``, ``qualite faible``
  (unpenalised, #3133), ``rejet Dung`` (its attack graph drops every
  fallacy-minted source before evaluation — #1698 measured — so a rejection
  that fires was not caused by a fallacy edge);
* ``contre-argument`` counts only when the counter axis discriminates on the
  run (some unit of the counter phase's recorded sample got no counter);
* ``JTMS retracte`` is DERIVED: still listed, never counted, labelled as
  what it is;
* ``specialist_roles`` reads the unpenalised fractions in both branches.
"""

from types import SimpleNamespace

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    build_convergent_synthesis,
    compute_argument_convergence,
)
from argumentation_analysis.reporting.restitution.global_projection import (
    project_global_findings,
)
from argumentation_analysis.reporting.restitution.specialist_roles import (
    ROLE_CONTRADICTOIRE,
    ROLE_CORROBORANT,
    classify_specialist_roles,
)


def _state(
    args,
    fallacies=None,
    quality=None,
    counters=None,
    jtms_invalid=None,
    counter_sample=None,
):
    """A state namespace shaped exactly like the fields convergence reads."""
    jtms = {}
    for arg_id in jtms_invalid or []:
        jtms[f"b_{arg_id}"] = {"name": f"{arg_id}:excerpt", "valid": False}
    coverage = {}
    if counter_sample is not None:
        coverage["counter"] = {
            "k": len(counter_sample),
            "N": 10,
            "bands_covered": 3,
            "bands_total": 3,
            "unit_ids": list(counter_sample),
        }
    return SimpleNamespace(
        identified_arguments=dict(args),
        identified_fallacies=dict(fallacies or {}),
        argument_quality_scores=dict(quality or {}),
        counter_arguments=list(counters or []),
        jtms_beliefs=jtms,
        dung_frameworks={},
        analysis_coverage=coverage,
    )


def _fallacy(arg_id, ftype="ad_hominem"):
    return {"f1": {"target_argument_id": arg_id, "type": ftype}}


def _scored(fraction, penalty_applied=False, original=None):
    """A stored quality entry whose fraction comes out at ``fraction``.

    ``original`` is the unpenalised SUM (the scale ``overall`` lives on):
    ``independent_quality_fraction`` divides it by ``len(scores)``.
    """
    scores = {"clarte": 1.0, "pertinence": 1.0}
    overall = fraction * len(scores)
    entry = {"scores": scores, "overall": overall}
    if penalty_applied:
        entry["fallacy_penalty"] = {
            "applied": True,
            "fallacies": ["ad_hominem"],
            "penalty_factor": 0.7,
            "original_score": original if original is not None else overall,
        }
    return entry


class TestConvergenceCountsIndependentClasses:
    def test_jtms_echo_and_vacuous_counter_are_not_independent(self):
        # The #3145 witness: fallacy + its JTMS retraction + a counter, on a
        # run where EVERY sampled unit got a counter → 1 independent method.
        state = _state(
            {"arg_1": "texte un", "arg_2": "texte deux"},
            fallacies=_fallacy("arg_1"),
            counters=[
                {"counter_argument": "c1", "target_arg_id": "arg_1"},
                {"counter_argument": "c2", "target_arg_id": "arg_2"},
            ],
            jtms_invalid=["arg_1"],
            counter_sample=["arg_1", "arg_2"],
        )
        out = compute_argument_convergence(state)
        assert out["arg_1"]["score"] == 1
        assert [m for m, _ in out["arg_1"]["independent_signals"]] == ["sophisme"]
        cited = {m for m, _ in out["arg_1"]["cited_signals"]}
        assert "JTMS retracte" in cited
        assert "contre-argument" in cited

    def test_unpenalised_weak_quality_still_counts(self):
        # Control: fallacy + genuinely weak unpenalised quality → 2 methods.
        state = _state(
            {"arg_1": "texte un", "arg_2": "texte deux"},
            fallacies=_fallacy("arg_1"),
            quality={
                "arg_1": _scored(0.3),
                # a spanning unit keeps the #1942 gate open
                "arg_2": _scored(0.9),
            },
        )
        out = compute_argument_convergence(state)
        assert out["arg_1"]["score"] == 2
        assert [m for m, _ in out["arg_1"]["independent_signals"]] == [
            "sophisme",
            "qualite faible",
        ]

    def test_discriminating_counter_still_counts(self):
        # Control: some sampled unit got NO counter → the axis discriminates.
        state = _state(
            {"arg_1": "texte un", "arg_2": "texte deux"},
            fallacies=_fallacy("arg_1"),
            counters=[{"counter_argument": "c1", "target_arg_id": "arg_1"}],
            jtms_invalid=["arg_1"],
            counter_sample=["arg_1", "arg_2"],
        )
        out = compute_argument_convergence(state)
        assert out["arg_1"]["score"] == 2
        assert [m for m, _ in out["arg_1"]["independent_signals"]] == [
            "sophisme",
            "contre-argument",
        ]
        # The JTMS echo stays visible as content, never as a witness.
        assert "JTMS retracte" in {m for m, _ in out["arg_1"]["cited_signals"]}

    def test_derived_jtms_detail_names_what_it_is(self):
        state = _state(
            {"arg_1": "texte un"},
            fallacies=_fallacy("arg_1"),
            jtms_invalid=["arg_1"],
        )
        out = compute_argument_convergence(state)
        jtms_entries = [
            d for m, d in out["arg_1"]["cited_signals"] if m == "JTMS retracte"
        ]
        assert jtms_entries and "derive" in jtms_entries[0]


class TestWordingFollowsTheCount:
    def test_no_independence_claim_over_derived_signals(self):
        # arg_1: fallacy + JTMS echo + vacuous counter → the synthesis must
        # not present a multi-method convergence on it.
        state = _state(
            {"arg_1": "texte un", "arg_2": "texte deux"},
            fallacies=_fallacy("arg_1"),
            counters=[
                {"counter_argument": "c1", "target_arg_id": "arg_1"},
                {"counter_argument": "c2", "target_arg_id": "arg_2"},
            ],
            jtms_invalid=["arg_1"],
            counter_sample=["arg_1", "arg_2"],
        )
        synthesis = build_convergent_synthesis(state)
        assert "arg_1" not in synthesis["convergent_verdicts"]
        assert "une seule methode" in synthesis["conclusion"]

    def test_insight_counts_independent_methods_only(self):
        state = _state(
            {"arg_1": "texte un", "arg_2": "texte deux"},
            fallacies=_fallacy("arg_1"),
            counters=[{"counter_argument": "c1", "target_arg_id": "arg_1"}],
            jtms_invalid=["arg_1"],
            counter_sample=["arg_1", "arg_2"],
        )
        synthesis = build_convergent_synthesis(state)
        assert synthesis["convergent_verdicts"]["arg_1"]["score"] == 2
        insight = synthesis["emergent_insights"][0]
        assert "2 methodes independantes" in insight
        # The JTMS echo is cited as content, never as a concurring method.
        assert "JTMS" in insight
        assert "maintenance de verite (JTMS)" not in insight.split("concourent")[0]

    def test_substantive_insight_explains_the_methods_that_count(self):
        # R1107 rework witness: the >=3 insight carries, after "perspective :",
        # the REASON of each independent method — and none of the derived
        # ones. On 729a192 the clause had lost every reason (only the cited
        # tail explained anything) — this witness is red there.
        state = _state(
            {"arg_1": "texte un", "arg_2": "texte deux"},
            fallacies=_fallacy("arg_1"),
            quality={
                "arg_1": _scored(0.3),
                "arg_2": _scored(0.9),
            },
            counters=[{"counter_argument": "c1", "target_arg_id": "arg_1"}],
            jtms_invalid=["arg_1"],
            counter_sample=["arg_1", "arg_2"],
        )
        synthesis = build_convergent_synthesis(state)
        assert synthesis["convergent_verdicts"]["arg_1"]["score"] == 3
        insight = synthesis["emergent_insights"][0]
        assert "3 methodes independantes" in insight
        clause, _, tail = insight.partition("Par ailleurs")
        assert "perspective :" in clause
        # Each INDEPENDENT method's reason is explained in the clause.
        assert "la detection rhetorique a identifie un probleme" in clause
        assert "le scoring de qualite signale une faiblesse" in clause
        assert "un contre-argument solide a ete oppose" in clause
        # No derived reason may pose as a perspective in that clause.
        assert "maintenance de verite" not in clause
        assert "JTMS" not in clause
        # The derived JTMS reason stays where it belongs — the cited tail.
        assert "maintenance de verite" in tail


class TestGlobalProjectionCountsIndependent:
    def test_projection_statement_counts_independent_methods(self):
        state = _state(
            {"arg_1": "texte un", "arg_2": "texte deux"},
            fallacies=_fallacy("arg_1"),
            counters=[{"counter_argument": "c1", "target_arg_id": "arg_1"}],
            jtms_invalid=["arg_1"],
            counter_sample=["arg_1", "arg_2"],
        )
        findings = project_global_findings(state)
        conv = [f for f in findings if f.kind == "convergence" and "arg_1" in f.cites]
        assert conv, "a 2-independent-method convergence must project"
        assert "2 méthodes indépendantes convergent" in conv[0].statement
        assert "JTMS" not in conv[0].statement


class TestSpecialistRolesReadUnpenalisedQuality:
    """#3133 remaining leg: the twin reader, both branches."""

    @staticmethod
    def _roles_state(quality):
        return SimpleNamespace(
            identified_arguments={"arg_1": "texte un", "arg_2": "texte deux"},
            identified_fallacies=_fallacy("arg_1"),
            argument_quality_scores=quality,
            propositional_analysis_results=[],
            first_order_logic_results=[],
            modal_logic_results=[],
            dung_frameworks={},
        )

    def test_weak_only_through_penalty_gets_no_corroboration(self):
        # Penalised 0.3, unpenalised 0.7: the fallacy did the whole drop —
        # quality corroborates nothing it did not independently measure.
        state = self._roles_state(
            {
                "arg_1": _scored(0.3, penalty_applied=True, original=1.4),
                "arg_2": _scored(0.9),
            }
        )
        roles = classify_specialist_roles(state)
        assert not any(r.role == ROLE_CORROBORANT and "arg_1" in r.cites for r in roles)

    def test_genuinely_weak_unit_keeps_the_corroboration(self):
        state = self._roles_state(
            {
                "arg_1": _scored(0.3),
                "arg_2": _scored(0.9),
            }
        )
        roles = classify_specialist_roles(state)
        assert any(r.role == ROLE_CORROBORANT and "arg_1" in r.cites for r in roles)

    def test_penalty_may_not_erase_a_real_tension(self):
        # Unpenalised 0.8 (solid), penalised 0.5: the CONTRADICTOIRE branch
        # must see the solid quality — a penalty may not bury the tension
        # under a fallacy-adjusted number.
        state = self._roles_state(
            {
                "arg_1": _scored(0.5, penalty_applied=True, original=1.6),
                "arg_2": _scored(0.9),
            }
        )
        roles = classify_specialist_roles(state)
        assert any(r.role == ROLE_CONTRADICTOIRE and "arg_1" in r.cites for r in roles)
