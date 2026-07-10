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
    SophismComparison,
    _CQ_CHALLENGER_PREFIX,
    _grounded_extension_pure,
    _llm_cq_evaluator_async,
    arbitrate,
    build_dung_framework,
    compare_sophism_backends,
    default_conflict_policy,
    make_dung_agent_solver,
    make_llm_cq_evaluator,
    pure_python_solver,
    walton_cq_bridge,
)
from argumentation_analysis.agents.core.debate.argumentation_schemes import (
    classify_scheme,
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


class TestWaltonCqBridge:
    # A span that deterministically matches the expert_opinion scheme keyword set
    # ["expert", "domaine"] so tests get a real scheme with real CQs.
    _EXPERT_SPAN = "Selon un expert du domaine, la mesure est efficace."

    def test_no_scheme_leaves_candidate_unchanged(self) -> None:
        enriched, coverage = walton_cq_bridge(
            [_cand("s0")], span_text_for=lambda c: "zzzzz"
        )
        assert enriched[0].failed_critical_questions == ()
        assert coverage == {"s0": ""}

    def test_default_evaluator_is_honest_absent(self) -> None:
        enriched, coverage = walton_cq_bridge(
            [_cand("s0")], span_text_for=lambda c: self._EXPERT_SPAN
        )
        # Default evaluator declares nothing → no CQ, but the scheme is recorded.
        assert enriched[0].failed_critical_questions == ()
        assert coverage == {"s0": "expert_opinion"}

    def test_canonical_cq_is_propagated(self) -> None:
        scheme = classify_scheme(self._EXPERT_SPAN)
        assert scheme is not None
        canonical_cq = scheme.critical_questions[0]

        def ev(_t: str, _s: object, _c: SophismCandidate) -> tuple[str, ...]:
            return (canonical_cq,)

        enriched, _ = walton_cq_bridge(
            [_cand("s0")], span_text_for=lambda c: self._EXPERT_SPAN, cq_evaluator=ev
        )
        assert canonical_cq in enriched[0].failed_critical_questions

    def test_non_canonical_cq_is_dropped_anti_fabrication(self) -> None:
        def ev(_t: str, _s: object, _c: SophismCandidate) -> tuple[str, ...]:
            # A question the expert_opinion scheme never asks — must be dropped.
            return ("Cette question n'existe dans aucun scheme Walton",)

        enriched, _ = walton_cq_bridge(
            [_cand("s0")], span_text_for=lambda c: self._EXPERT_SPAN, cq_evaluator=ev
        )
        assert enriched[0].failed_critical_questions == ()

    def test_injected_classifier_is_used(self) -> None:
        from argumentation_analysis.agents.core.debate.argumentation_schemes import (
            ArgumentationScheme,
        )

        fake = ArgumentationScheme(
            key="fake_scheme",
            label="Fake",
            premises_pattern=[],
            conclusion_pattern="",
            strength=1.0,
            critical_questions=["FAKE_Q"],
        )

        def fake_cls(_text: str) -> ArgumentationScheme:
            return fake

        def ev(_t: str, _s: object, _c: SophismCandidate) -> tuple[str, ...]:
            return ("FAKE_Q",)

        enriched, coverage = walton_cq_bridge(
            [_cand("s0")],
            span_text_for=lambda c: "x",
            classifier=fake_cls,
            cq_evaluator=ev,
        )
        assert coverage == {"s0": "fake_scheme"}
        assert enriched[0].failed_critical_questions == ("FAKE_Q",)


class TestCompareSophismBackends:
    def test_honest_absent_neural_equals_neuro_symbolic(self) -> None:
        cands = [_cand("s0", span="x"), _cand("s1", span="y")]
        cmp = compare_sophism_backends(cands, span_text_for=lambda c: "zzzzz")
        assert isinstance(cmp, SophismComparison)
        assert cmp.neural_ids == frozenset({"s0", "s1"})
        assert cmp.neuro_symbolic_ids == cmp.neural_ids
        assert cmp.eliminated_ids == frozenset()
        assert cmp.arbitrated.honest_absent is True

    def test_cq_defeat_surfaces_in_delta(self) -> None:
        # One candidate fails a canonical CQ (eliminated), the other does not.
        scheme = classify_scheme("Selon un expert du domaine cela fonctionne.")
        assert scheme is not None
        canonical_cq = scheme.critical_questions[0]

        def ev(_t: str, _s: object, c: SophismCandidate) -> tuple[str, ...]:
            return (canonical_cq,) if c.candidate_id == "s0" else ()

        cands = [_cand("s0", span="x"), _cand("s1", span="y")]
        cmp = compare_sophism_backends(
            cands,
            span_text_for=lambda c: "Selon un expert du domaine cela fonctionne.",
            cq_evaluator=ev,
        )
        assert cmp.eliminated_ids == frozenset({"s0"})
        assert cmp.neuro_symbolic_ids == frozenset({"s1"})
        assert cmp.neural_ids - cmp.neuro_symbolic_ids == cmp.eliminated_ids
        assert cmp.arbitrated.honest_absent is False

    def test_coverage_reports_classified_scheme_keys(self) -> None:
        cmp = compare_sophism_backends(
            [_cand("s0")],
            span_text_for=lambda c: "Selon un expert du domaine la chose est vraie.",
        )
        assert cmp.span_coverage == {"s0": "expert_opinion"}


class TestLlmCqEvaluator:
    """PR3 — production wiring of the LLM-backed CQ evaluator.

    These tests are JVM/LLM-free by design: they cover the fail-soft paths (no
    API key, no running loop, invalid input) and the lazy-import contract. The
    genuine LLM path is exercised end-to-end by the PR3 probe (scratchpad,
    gitignored) on real-corpus text.
    """

    _EXPERT_SPAN = "Selon un expert du domaine, la mesure est efficace."

    def test_factory_returns_callable(self) -> None:
        ev = make_llm_cq_evaluator()
        assert callable(ev)

    @pytest.mark.asyncio
    async def test_async_helper_returns_empty_when_no_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No API key configured ⇒ async helper returns () (honest-absent)."""

        def _no_client() -> tuple[object, str]:
            return None, ""

        monkeypatch.setattr(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            _no_client,
        )
        scheme = classify_scheme(self._EXPERT_SPAN)
        assert scheme is not None
        out = await _llm_cq_evaluator_async(self._EXPERT_SPAN, scheme, _cand("s0"))
        assert out == ()

    @pytest.mark.asyncio
    async def test_async_helper_validates_against_canonical(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LLM response that declares a non-canonical CQ is dropped (anti-fab)."""

        import json

        scheme = classify_scheme(self._EXPERT_SPAN)
        assert scheme is not None
        canonical = scheme.critical_questions[0]
        declared_non_canonical = "Question jamais posée par aucun schème Walton"
        # json.dumps produces strictly valid JSON (escapes the French apostrophe
        # and any other specials). repr() would emit Python-style single quotes
        # that _parse_json_from_llm rejects, masking the anti-fabrication path.
        payload = json.dumps({"failed": [canonical, declared_non_canonical]})

        # Fake LLM plumbing: a stub client + a guarded completion that returns
        # the canned JSON, plus the real parse_json_from_llm.

        class _Msg:
            def __init__(self, content: str) -> None:
                self.content = content

        class _Choice:
            def __init__(self, content: str) -> None:
                self.message = _Msg(content)

        class _Resp:
            def __init__(self, content: str) -> None:
                self.choices = [_Choice(content)]

        async def _fake_completion(*_a: object, **_k: object) -> _Resp:
            return _Resp(payload)

        def _fake_client() -> tuple[object, str]:
            return object(), "fake-model"

        import argumentation_analysis.orchestration.invoke_callables as ic

        monkeypatch.setattr(ic, "_get_openai_client", _fake_client)
        monkeypatch.setattr(ic, "_guarded_chat_completion", _fake_completion)
        monkeypatch.setattr(ic, "_get_determinism_params", lambda: {})

        out = await _llm_cq_evaluator_async(self._EXPERT_SPAN, scheme, _cand("s0"))
        assert canonical in out
        assert declared_non_canonical not in out
        # The bridge re-validates too, but this is the helper's own defence.
        assert all(q in scheme.critical_questions for q in out)

    def test_sync_wrapper_fails_soft_when_no_api_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        ev = make_llm_cq_evaluator()
        scheme = classify_scheme(self._EXPERT_SPAN)
        assert scheme is not None
        # Force the no-key path: stub the async helper directly to mirror the
        # "no client" behaviour end-to-end.
        import asyncio

        async def _empty(*_a: object, **_k: object) -> tuple[str, ...]:
            return ()

        monkeypatch.setattr(
            "argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator._llm_cq_evaluator_async",
            _empty,
        )
        # Sync path (no running loop): the wrapper awaits the async helper.
        assert ev(self._EXPERT_SPAN, scheme, _cand("s0")) == ()


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
