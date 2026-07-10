"""Unit tests for the neuro-symbolic arbitrator (Track I1 #1429).

Pure-python, JVM/LLM-free: synthetic opaque atoms (``s0``, ``family_a``,
``span_0``) only. The default ``pure_python_solver`` (grounded) is exercised
throughout; the real ``abs_arg_dung`` adapter is covered for its lazy-import /
no-JVM contract without spinning up a JVM.

These tests pin the two anti-fabrication guarantees of the module:

* honest-absent — no declared signal ⇒ no attack ⇒ arbitrated == neural;
* no invented defeats — every rejection traces to a declared failed Walton
  critical question or a declared same-span rivalry.
"""

from __future__ import annotations

import pytest

from argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator import (
    ArbitrationResult,
    SophismCandidate,
    _CQ_CHALLENGER_PREFIX,
    _grounded_extension_pure,
    arbitrate,
    build_dung_framework,
    default_conflict_policy,
    make_dung_agent_solver,
    pure_python_solver,
)


def _cand(
    cid: str,
    *,
    family: str = "family_a",
    span: str = "span_0",
    confidence: float = 0.5,
    cqs: tuple[str, ...] = (),
) -> SophismCandidate:
    """Compact opaque-atom builder for readable test fixtures."""

    return SophismCandidate(
        candidate_id=cid,
        family=family,
        span_id=span,
        confidence=confidence,
        failed_critical_questions=cqs,
    )


class TestBuildDungFramework:
    def test_clean_batch_yields_no_attacks(self) -> None:
        cands = [_cand("s0", span="span_0"), _cand("s1", span="span_1")]
        args, attacks, challenger_for = build_dung_framework(cands)
        assert args == {"s0", "s1"}
        assert attacks == set()
        assert challenger_for == {}

    def test_failed_cq_creates_unattacked_challenger(self) -> None:
        cands = [_cand("s0", cqs=("Is the expert really competent?",))]
        args, attacks, challenger_for = build_dung_framework(cands)
        assert len(challenger_for) == 1
        challenger = next(iter(challenger_for))
        assert challenger.startswith(_CQ_CHALLENGER_PREFIX)
        assert challenger_for[challenger] == "s0"
        assert (challenger, "s0") in attacks
        # The challenger is unattacked (nothing attacks it).
        assert not any(tgt == challenger for _, tgt in attacks)

    def test_duplicate_critical_question_yields_single_challenger(self) -> None:
        cands = [_cand("s0", cqs=("Q1", "Q1"))]
        _, attacks, challenger_for = build_dung_framework(cands)
        assert len(challenger_for) == 1
        assert sum(1 for _, tgt in attacks if tgt == "s0") == 1

    def test_same_span_different_family_directed_by_confidence(self) -> None:
        cands = [
            _cand("s0", family="ad_hominem", span="x", confidence=0.8),
            _cand("s1", family="straw_man", span="x", confidence=0.4),
        ]
        attacks = default_conflict_policy(cands)
        assert attacks == {("s0", "s1")}

    def test_same_span_same_family_no_conflict(self) -> None:
        cands = [
            _cand("s0", family="ad_hominem", span="x", confidence=0.8),
            _cand("s1", family="ad_hominem", span="x", confidence=0.4),
        ]
        assert default_conflict_policy(cands) == set()

    def test_same_span_tie_yields_mutual_attack(self) -> None:
        cands = [
            _cand("s0", family="ad_hominem", span="x", confidence=0.5),
            _cand("s1", family="straw_man", span="x", confidence=0.5),
        ]
        assert default_conflict_policy(cands) == {("s0", "s1"), ("s1", "s0")}

    def test_distinct_spans_never_conflict(self) -> None:
        cands = [
            _cand("s0", family="a", span="x", confidence=0.9),
            _cand("s1", family="b", span="y", confidence=0.1),
        ]
        assert default_conflict_policy(cands) == set()

    def test_candidate_id_colliding_with_prefix_rejected(self) -> None:
        with pytest.raises(ValueError, match="collides with the reserved"):
            SophismCandidate(
                candidate_id=_CQ_CHALLENGER_PREFIX + "s0",
                family="a",
                span_id="x",
                confidence=0.5,
            )


class TestGroundedExtensionPure:
    def test_no_attackers_all_accepted(self) -> None:
        accepted = _grounded_extension_pure({"a", "b", "c"}, set())
        assert accepted == frozenset({"a", "b", "c"})

    def test_two_cycle_neither_accepted(self) -> None:
        attacks = {("a", "b"), ("b", "a")}
        assert _grounded_extension_pure({"a", "b"}, attacks) == frozenset()

    def test_unattacked_attacker_defeats_target(self) -> None:
        # c attacks b, nothing attacks c → b rejected, c and a accepted.
        attacks = {("c", "b")}
        assert _grounded_extension_pure({"a", "b", "c"}, attacks) == frozenset(
            {"a", "c"}
        )

    def test_defender_reinstates_attacked_argument(self) -> None:
        # c attacks b, a attacks c → a survives (unattacked), b is defended by a
        # (reinstated), c is defeated by a. Grounded = {a, b}.
        attacks = {("c", "b"), ("a", "c")}
        assert _grounded_extension_pure({"a", "b", "c"}, attacks) == frozenset(
            {"a", "b"}
        )

    def test_pure_solver_rejects_non_grounded_semantics(self) -> None:
        with pytest.raises(NotImplementedError, match="only grounded"):
            pure_python_solver({"a"}, set(), semantics="preferred")


class TestArbitrate:
    def test_honest_absent_keeps_all_candidates(self) -> None:
        cands = [_cand("s0", span="x"), _cand("s1", span="y"), _cand("s2", span="z")]
        res = arbitrate(cands)
        assert isinstance(res, ArbitrationResult)
        assert res.honest_absent is True
        assert res.arbitrated_ids == frozenset({"s0", "s1", "s2"})
        assert res.rejected == {}
        assert res.neural_count == 3
        assert res.arbitrated_count == 3

    def test_candidate_with_failed_cq_is_rejected(self) -> None:
        cands = [
            _cand("s0", span="x", cqs=("Is the source independent?",)),
            _cand("s1", span="y"),
        ]
        res = arbitrate(cands)
        assert res.honest_absent is False
        assert res.arbitrated_ids == frozenset({"s1"})
        assert res.rejected == {"s0": "defeated_by_unsatisfied_critical_question"}

    def test_rival_loser_rejected_winner_kept(self) -> None:
        cands = [
            _cand("s0", family="ad_hominem", span="x", confidence=0.9),
            _cand("s1", family="straw_man", span="x", confidence=0.3),
        ]
        res = arbitrate(cands)
        assert res.arbitrated_ids == frozenset({"s0"})
        assert res.rejected == {"s1": "defeated_by_rival_candidate"}

    def test_mixed_cq_and_rival_dimensions(self) -> None:
        # s0 fails a CQ (rejected); s1 and s2 rival on span x, s1 wins.
        cands = [
            _cand("s0", span="y", cqs=("Q?",)),
            _cand("s1", family="a", span="x", confidence=0.9),
            _cand("s2", family="b", span="x", confidence=0.2),
        ]
        res = arbitrate(cands)
        assert res.arbitrated_ids == frozenset({"s1"})
        assert set(res.rejected) == {"s0", "s2"}

    def test_custom_conflict_policy_can_disable_rivalry(self) -> None:
        cands = [
            _cand("s0", family="a", span="x", confidence=0.9),
            _cand("s1", family="b", span="x", confidence=0.2),
        ]
        res = arbitrate(cands, conflict_policy=lambda _c: set())
        # No rivalry, no CQ → honest-absent, both kept.
        assert res.honest_absent is True
        assert res.arbitrated_ids == frozenset({"s0", "s1"})

    def test_injected_solver_with_multiple_extensions_is_skeptical(self) -> None:
        # Custom solver returns 2 preferred extensions; only the candidate in
        # BOTH survives the skeptical intersection.
        cands = [_cand("s0"), _cand("s1")]

        def two_ext(
            arguments: set[str],
            attacks: set[tuple[str, str]],
            *,
            semantics: str,
        ) -> list[set[str]]:
            return [{"s0", "s1"}, {"s0"}]

        res = arbitrate(cands, solver=two_ext, semantics="preferred")
        assert res.arbitrated_ids == frozenset({"s0"})
        assert res.semantics == "preferred"

    def test_attacks_recorded_on_result(self) -> None:
        cands = [
            _cand("s0", span="x", cqs=("Q?",)),
            _cand("s1", family="b", span="x", confidence=0.1),
        ]
        res = arbitrate(cands)
        # At least one challenger→s0 attack and the rivalry edge s0→s1.
        assert any(
            a.startswith(_CQ_CHALLENGER_PREFIX) and b == "s0" for a, b in res.attacks
        )
        assert ("s0", "s1") in res.attacks


class TestDungAgentSolverAdapter:
    def test_factory_does_not_touch_jvm_at_import(self) -> None:
        # Building the solver closure must be cheap and JVM-free; only calling
        # it (in PR2/PR3 with a live JVM) should touch jpype.
        solver = make_dung_agent_solver()
        assert callable(solver)

    def test_solver_raises_without_jvm(self) -> None:
        import jpype

        if jpype.isJVMStarted():
            pytest.skip(
                "JVM already started in this process; cannot assert the no-JVM path"
            )
        solver = make_dung_agent_solver()
        with pytest.raises(RuntimeError, match="La JVM doit être démarrée"):
            solver({"a"}, set(), semantics="grounded")
