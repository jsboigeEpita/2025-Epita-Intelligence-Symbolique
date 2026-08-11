"""#1646 incr 4 — paired-run: minimal-retraction end-to-end on producer-built states.

Incr 1+2+3 (PRs #1689, #1691, #1701) computed the minimal-retraction as a pure
function, wired it through the producer / state / bridge / reader pipeline, and
proved it on unit fixtures. What remains unmeasured is the **end-to-end
differential**: given a real producer invocation, does the insight say something
that the upstream evidence (the planted fallacies) does not already say?

The R791 framing refinement is the heart of this test: on real corpora, the
upstream argument inventory is empty (0/21 propositions, #1710) — so any
contradiction measured today comes from a *planted* fallacy. The question is
therefore **not** "did the retraction find something?" (the plant guarantees
yes) but **"what does the insight name that the plant did not put there?"**

The test is **paired**: a control run with no fallacies (the D-forensic baseline
where the base is consistent and the insight is empty) and a planted run where
the base is genuinely inconsistent (one or two fallacies on distinct beliefs).
The differential is the concrete answer to R791:

| Planted | Insight (planted) | Insight (control) | What the insight says the plant did not |
|---|---|---|---|
| 1 fallacy on 1 belief | cardinality 1, options touch the clashing pair | empty (no fallacy path) | **the base is inconsistent** + **the cardinality is 1**, not "there is a fallacy" — the fallacy is the upstream input, the inconsistency is the property the insight derives |
| 2 fallacies on 2 beliefs | cardinality 2, options isolated to the 2 clash pairs | empty | **the two clashes are independent** (both must be given up, no single removal restores consistency) — the plant says "two fallacies", the insight says "two independent inconsistencies" |
| 1 fallacy on 1 belief + 5 inert beliefs | cardinality 1, options never touch the 5 inert beliefs | empty | **the contradiction is inert** w.r.t. the unrevised beliefs — the discrimination is "what survives?", not "what clashes?" |

This is the B-3 inert-contradiction output the reader cannot produce from any
of PL/UNSAT, the LLM "find contradictions" prompt, or the Tweety Levi handler.
The paired-run is the first place those properties are measured *as a
differential against a real run*, not as a property of an isolated pure function.

The harness deliberately bypasses the corpus runner (#1697 / no live JVM on this
worker) and calls the producer directly on a state built by the real
``add_jtms_belief`` / ``add_fallacy`` public APIs. The fixtures are producer-
faithful (the producer is the one wired by #1701): every shape is the shape it
runs on, the only difference between the two runs is the planted fallacy.

Privacy HARD: no fixture carries NL source text. The belief names are synthetic
opaque labels (the producer treats them as opaque; the reader renders them
verbatim into the Acte III finding, which is the entire point of B-1 — the
insight names the rupture point in the corpus' own vocabulary, not in a
privatised form). The artefact paths are gitignored.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.conversational_orchestrator import (
    _run_belief_revision_from_state,
)

# Synthetic opaque belief labels — never NL source text. The producer treats
# these as opaque strings; the reader uses them as the rupture-point name in
# the Acte III finding (insight B-1). The fact that they are *not* real NL is
# what makes the privacy claim honest in this test.
BELIEF_LABELS = [
    "claim_alpha",
    "claim_beta",
    "claim_gamma",
    "claim_delta",
    "claim_epsilon",
]


def _build_state(fallacy_targets: List[str]) -> UnifiedAnalysisState:
    """Build a producer-fed state with the given planted fallacy targets.

    ``fallacy_targets`` is a list of **belief names** the fallacy undermines.
    Empty list = control run (no fallacies ⇒ producer returns None, the
    ``belief_revision_results`` stays empty — the D-forensic baseline where the
    base is trivially consistent and the minimal-retraction insight is ∅).

    Each belief is a valid JTMS belief in the upstream inventory; the producer
    consumes ``state.jtms_beliefs`` to build the original-belief list that
    ``build_belief_base`` operates on. The ``target_argument_id`` argument of
    ``add_fallacy`` is the belief name as the producer matches it (l.3202:
    ``bname == target_arg or target_arg in bname``), so setting it to the
    belief name is the honest way to plant the contradiction.
    """
    state = UnifiedAnalysisState("initial text")
    for name in BELIEF_LABELS:
        state.add_jtms_belief(name, valid=True, justifications=[f"src:{name}"])
    for i, target in enumerate(fallacy_targets):
        state.add_fallacy(
            fallacy_type="ad_hominem",
            justification=f"planted fallacious attack targeting {target}",
            target_arg_id=target,
            family="relevance",
            taxonomy_path="relevance.ad_hominem",
        )
    return state


def _drain_state(state: UnifiedAnalysisState) -> List[Dict[str, Any]]:
    """Return belief_revision_results as a list of plain dicts (test-friendly)."""
    return [dict(entry) for entry in state.belief_revision_results]


class TestPairedRunNoFallacyIsTheBaseline:
    """Control: no fallacy ⇒ empty belief_revision_results, no insight.

    The D-forensic measured that without fallacies the base is trivially
    consistent and the producer returns ``None`` (the first guard, l.3160).
    This pins the runner contract: the planted-run differential is measured
    against a *non-empty* baseline, not a fabricated one.
    """

    def test_control_returns_nothing(self) -> None:
        state = _build_state(fallacy_targets=[])
        result = _run_belief_revision_from_state(state)
        assert result is None, (
            "the first producer guard is `if not fallacies: return None`; the "
            "control run must not produce a result entry, else the differential "
            "below is noise on a non-empty baseline."
        )
        assert _drain_state(state) == [], (
            "control run must leave belief_revision_results empty; a non-empty "
            "baseline would mean every other 'delta' is a fabrication."
        )


class TestPairedRunCardinalityOne:
    """Planted: 1 fallacy on 1 belief ⇒ cardinality 1, options isolate the clash.

    The plant puts ONE fallacy on ONE belief. The differential = the base is
    inconsistent (the insight) + the cardinality is 1 (the insight) + the
    rupture point is *the clashing pair* (the belief OR its negation — the
    retraction choices are structural, not planted).
    """

    def test_planted_run_is_non_empty(self) -> None:
        state = _build_state(fallacy_targets=[BELIEF_LABELS[0]])
        result = _run_belief_revision_from_state(state)
        # The producer must populate the entry (the planted contradiction is real).
        assert (
            result is not None
        ), "planted run with a real fallacy produced None — the wiring is dead."
        entries = _drain_state(state)
        assert len(entries) == 1
        # The original-beleifs list is the full JTMS inventory (5 names).
        assert len(entries[0]["original"]) == len(BELIEF_LABELS)

    def test_minimal_retraction_is_non_empty(self) -> None:
        # R791 DoD item 1: the retraction is non-empty on the planted run.
        state = _build_state(fallacy_targets=[BELIEF_LABELS[0]])
        _run_belief_revision_from_state(state)
        entry = _drain_state(state)[0]
        mr = entry["minimal_retraction"]
        assert mr is not None, (
            "minimal_retraction is missing from the planted-run entry — the "
            "wiring did not carry the insight through. #1701 said it would."
        )

    def test_insight_is_not_just_a_plant_echo(self) -> None:
        """R791 DoD item 3: the insight says something the plant did not put there.

        The plant put ONE fallacy on ONE belief. The insight reports a
        **cardinality** (1) and **options** (which beliefs to give up). Both are
        aspects of the *structure* of the base, not aspects of the upstream
        evidence: the plant says "fallacy on alpha", the insight says
        "the base is inconsistent at cardinality 1, with these rupture options".
        That difference IS the minimal-retraction contribution.
        """
        state = _build_state(fallacy_targets=[BELIEF_LABELS[0]])
        _run_belief_revision_from_state(state)
        mr = _drain_state(state)[0]["minimal_retraction"]

        # The plant specifies a fallacy on alpha; the insight isolates the
        # clash. The clash has TWO relief points (alpha OR ¬alpha) — the
        # plant says "alpha is undermined", the insight says "to restore
        # consistency you must choose: drop alpha OR drop the negation that
        # fallacy added (call it ¬alpha)". The multiplicity is structural.
        assert mr["cardinality"] == 1, (
            f"cardinality {mr['cardinality']} != 1 — one fallacy on one belief "
            "yields exactly one remaining clause to retract."
        )
        # Every option is a single belief (the cardinality-1 guarantee).
        assert all(len(opt) == 1 for opt in mr["options"]), (
            f"options {mr['options']} are not all singletons — the "
            "cardinality-1 guarantee is violated."
        )
        # The optional readings are limited to the clashing pair (alpha or its
        # negation). NO inert belief (beta, gamma, delta, epsilon) ever
        # appears in any option — this is B-3 inert-contradiction in practice.
        clashing = {BELIEF_LABELS[0], f"¬{BELIEF_LABELS[0]}"}
        for opt in mr["options"]:
            for belief in opt:
                assert belief in clashing, (
                    f"belief {belief!r} is NOT in the clashing pair {clashing} — "
                    "the insight is going wider than the plant, which means the "
                    "minimal-retraction has reached beyond the contradiction "
                    "(the base has more than one clash, contradicting the "
                    "test premise)."
                )

    def test_structural_property_base_size_and_touched_count(self) -> None:
        """R791 DoD item 4: every number carries its n.

        The insight carries three integers: cardinality, base_size, touched_count.
        Their meanings are:
        - cardinality = 1 (the answer)
        - base_size = 6 (5 original + 1 negation from the plant)
        - touched_count = 2 (the two singletons-alpha + ¬alpha — both are
          "touched" by the answer, even though only one is dropped)

        The plant put ONE fallacy. The insight says the answer is "1 of these 6,
        but EVERY option touches either alpha or ¬alpha". The 2 of the 6 is
        derivable from the plant (the negation clause was added by the plant),
        but the *answer set* (alpha OR ¬alpha, never both, never anything else)
        is not in the plant.
        """
        state = _build_state(fallacy_targets=[BELIEF_LABELS[0]])
        _run_belief_revision_from_state(state)
        mr = _drain_state(state)[0]["minimal_retraction"]
        assert mr["base_size"] == len(BELIEF_LABELS) + 1, (
            f"base_size {mr['base_size']} != {len(BELIEF_LABELS) + 1} — "
            "5 original beliefs + 1 negation from the plant."
        )
        assert (
            mr["touched_count"] == 2
        ), f"touched_count {mr['touched_count']} != 2 — should be alpha + ¬alpha."
        assert mr["degraded"] is False


class TestPairedRunCardinalityTwo:
    """Planted: 2 fallacies on 2 beliefs ⇒ cardinality 2, options isolate the 2.

    The plant puts TWO fallacies on TWO distinct beliefs. The differential:
    the two clashes are **independent** (no single removal restores
    consistency; both must be given up). The plant says "two fallacies", the
    insight says "these are two independent inconsistencies" — independence is
    not in the plant.
    """

    def test_two_independent_clashes_need_cardinality_two(self) -> None:
        state = _build_state(fallacy_targets=[BELIEF_LABELS[0], BELIEF_LABELS[1]])
        _run_belief_revision_from_state(state)
        mr = _drain_state(state)[0]["minimal_retraction"]
        assert mr["cardinality"] == 2, (
            f"cardinality {mr['cardinality']} != 2 — two independent clashes "
            "require two removals; the insight is reporting one. This is the "
            "minimality guarantee: the search did not stop at a non-restoring "
            "cardinal-1 guess."
        )
        # Every option is a pair.
        assert all(len(opt) == 2 for opt in mr["options"])
        # The clashing pairs are mirror-symmetric: (alpha OR ¬alpha) AT LEAST
        # one is in every option, AND (beta OR ¬beta) AT LEAST one is in every
        # option. The plant does not say "one from each clash", only "fallacy on
        # alpha and fallacy on beta" — the *distribution* across clashes is
        # structural: each option must touch both.
        clashing_a = {BELIEF_LABELS[0], f"¬{BELIEF_LABELS[0]}"}
        clashing_b = {BELIEF_LABELS[1], f"¬{BELIEF_LABELS[1]}"}
        for opt in mr["options"]:
            touches_a = any(b in clashing_a for b in opt)
            touches_b = any(b in clashing_b for b in opt)
            assert touches_a and touches_b, (
                f"option {opt} does not touch BOTH clashes — insight is "
                "missing one of the two independent inconsistencies."
            )
        # base_size = 5 original + 2 negations = 7; touched_count = 4.
        assert mr["base_size"] == len(BELIEF_LABELS) + 2
        assert mr["touched_count"] == 4


class TestPairedRunInertBeliefsSurvive:
    """Differential on inert beliefs: the retraction never touches them.

    The reader's B-3 inert-contradiction insight — "the contradiction is real
    but its retraction leaves the unrevised beliefs untouched" — is exactly
    the asymmetry the plant does not state. Five beliefs, one fallacy (on
    alpha). The plant says "alpha is undermined". The insight says "alpha
    clashes; beta, gamma, delta, epsilon are inert under this retraction".
    """

    @pytest.mark.parametrize("target", BELIEF_LABELS)
    def test_inert_beliefs_never_appear_in_any_option(self, target: str) -> None:
        """Parametrised over the planted target — the inert set is invariant.

        Whatever belief is targeted, the options never reach the others. This
        is the B-3 inert-contradiction: the rupture is local to the targeted
        pair, the rest of the base is untouched. The plant says "this belief";
        the insight says "ONLY this belief (and its negation)". The "only" is
        the structural contribution.
        """
        state = _build_state(fallacy_targets=[target])
        _run_belief_revision_from_state(state)
        mr = _drain_state(state)[0]["minimal_retraction"]
        inert = set(BELIEF_LABELS) - {target}
        for opt in mr["options"]:
            for belief in opt:
                assert belief not in inert, (
                    f"option {opt} contains inert belief {belief!r} — the "
                    "minimal-retraction is reaching beyond the clashing pair."
                )


class TestPairedRunNonVacuous:
    """The producer wiring is exercised; the test is not vacuous.

    If the producer's wiring of ``minimal_retraction`` is dead (e.g. a
    refactor that drops the call to ``build_belief_base`` /
    ``minimal_retractions``), the planted run still returns a result entry
    (the AGM contraction path runs), but without the insight. The previous
    tests pin the entry's *shape*; this one pins the *insight-bearing slot*
    — if it is missing, the wiring is broken even if the AGM path is alive.
    """

    def test_contraction_result_carries_minimal_retraction_slot(self) -> None:
        state = _build_state(fallacy_targets=[BELIEF_LABELS[0]])
        _run_belief_revision_from_state(state)
        entries = _drain_state(state)
        assert len(entries) == 1
        assert "minimal_retraction" in entries[0], (
            "the producer ran the contraction but did not carry the "
            "minimal_retraction slot — the #1701 wiring is broken on the "
            "conversational path (R787 insight measured surviving both producers)."
        )

    def test_degraded_flag_is_false_on_healthy_run(self) -> None:
        """A degraded dossier (cardinality -1, no options) would mean the
        pysat import failed (#1697 cascade) — the reader would have nothing to
        name. On this worker the import is healthy; the test is the control
        that catches an environment regression.
        """
        state = _build_state(fallacy_targets=[BELIEF_LABELS[0]])
        _run_belief_revision_from_state(state)
        mr = _drain_state(state)[0]["minimal_retraction"]
        assert mr["degraded"] is False, (
            "minimal_retraction.degraded=True on a healthy python-sat env "
            "— the import guard fired unexpectedly. The reader would be "
            "mute on this run; investigate the #1697 cascade at the entry."
        )
