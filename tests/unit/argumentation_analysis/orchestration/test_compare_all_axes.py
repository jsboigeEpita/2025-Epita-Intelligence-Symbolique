"""I6 #1437 — compare_all_axes unified multi-axis comparison harness tests.

Mirrors the anti-théâtre contract of all 3 underlying comparators (#1243 FOL,
I5 Dung, I1 sophism): DISAGREEMENT per axis is surfaced, NEVER auto-reconciled
(a disagreement is a result, not a bug to mask). An axis/backend that cannot run
is reported ``available=False`` (fail-loud), never silently omitted. The harness
is a router + uniform-shape aggregator only — it reuses the 3 comparators
(injected here as deterministic fakes) and never re-implements them.

No JVM, no real LLM, synthetic opaque inputs only (privacy HARD).
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    compare_all_axes,
    _invoke_multi_axis_compare,
    _normalize_dung_payload,
    _normalize_fol_payload,
    _normalize_sophism_payload,
)

# -- fake comparators (mirror the NATIVE shapes of the 3 real comparators) -----


def _fol_fake(verdicts: Dict[str, Any], agreement: Any, disagreement: List[str]):
    """Build a fake FOL comparator returning the native FOL shape."""

    async def _fn(belief_set: Any) -> Dict[str, Any]:
        backends = {
            n: {
                "verdict": v,
                "note": "fake",
                "elapsed_ms": 1.0,
                "available": True,
            }
            for n, v in verdicts.items()
        }
        decided = {n: v for n, v in verdicts.items() if isinstance(v, bool)}
        return {
            "backends": backends,
            "decided": decided,
            "agreement": agreement,
            "disagreement": list(disagreement),
        }

    return _fn


def _dung_fake(per_sem: Dict[str, Dict[str, Any]], overall: Any):
    """Build a fake Dung comparator returning the native Dung shape."""

    async def _fn(arguments: List[str], attacks: List[List[str]]) -> Dict[str, Any]:
        return {
            "backends": {
                "tweety": {
                    "extensions": {},
                    "available": True,
                    "note": "fake",
                    "elapsed_ms": 1.0,
                },
                "student": {
                    "extensions": {},
                    "available": True,
                    "note": "fake",
                    "elapsed_ms": 1.0,
                },
            },
            "comparison": {
                "semantics": list(per_sem.keys()),
                "per_semantics": per_sem,
                "overall_agreement": overall,
            },
            "statistics": {
                "arguments_count": len(arguments),
                "attacks_count": len(attacks),
                "backends_count": 2,
            },
        }

    return _fn


def _sophism_fake(eliminated: List[str], honest_absent: bool = False):
    """Build a fake sophism comparator returning a SophismComparison-like dict."""

    async def _fn(candidates: Any, *, span_text_for: Any, **kw: Any) -> Dict[str, Any]:
        neural = [c for c in (candidates or [])]
        neuro = [c for c in neural if c not in eliminated]
        return {
            "neural_ids": frozenset(neural),
            "neuro_symbolic_ids": frozenset(neuro),
            "eliminated_ids": frozenset(eliminated),
            "arbitrated": {"honest_absent": honest_absent},
            "span_coverage": None,
        }

    return _fn


# -- axis selection -----------------------------------------------------------


class TestAxisSelection:
    async def test_default_selects_only_supplied_axes(self):
        # Only dung input supplied → only dung runs.
        r = await compare_all_axes(
            dung_arguments=["s0", "s1"],
            dung_attacks=[["s0", "s1"]],
            dung_compare_fn=_dung_fake(
                {"grounded": {"agreement": True, "decided": ["a"], "disagreement": []}},
                True,
            ),
        )
        assert r["overall"]["axes_run"] == ["dung"]
        assert "fol" not in r["axes"]

    async def test_explicit_axes_overrides_supply_detection(self):
        # Explicit axes=["fol"] even though dung is supplied → only fol runs.
        r = await compare_all_axes(
            axes=["fol"],
            fol_belief_set="dummy",
            fol_compare_fn=_fol_fake({"e": True, "p": True}, True, []),
            dung_arguments=["s0"],
            dung_attacks=[],
            dung_compare_fn=_dung_fake(
                {"grounded": {"agreement": True, "decided": ["a"], "disagreement": []}},
                True,
            ),
        )
        assert r["overall"]["axes_run"] == ["fol"]

    async def test_unknown_axis_raises(self):
        with pytest.raises(ValueError, match="Unknown axis"):
            await compare_all_axes(axes=["bogus"])

    async def test_all_three_axes_run(self):
        r = await compare_all_axes(
            fol_belief_set="dummy",
            fol_compare_fn=_fol_fake({"e": True}, True, []),
            dung_arguments=["s0"],
            dung_attacks=[],
            dung_compare_fn=_dung_fake(
                {"grounded": {"agreement": True, "decided": ["a"], "disagreement": []}},
                True,
            ),
            sophism_candidates=["c0"],
            sophism_span_text_for=lambda c: "x",
            sophism_compare_fn=_sophism_fake([], honest_absent=False),
        )
        assert sorted(r["overall"]["axes_run"]) == ["dung", "fol", "sophism"]


# -- per-axis agreement / disagreement ---------------------------------------


class TestPerAxisAgreement:
    async def test_fol_disagreement_surfaced_not_reconciled(self):
        r = await compare_all_axes(
            fol_belief_set="dummy",
            fol_compare_fn=_fol_fake(
                {"e": True, "p": False}, False, ["DISAGREEMENT (NOT reconciled): e=p"]
            ),
        )
        assert r["axes"]["fol"]["agreement"] is False
        assert "NOT reconciled" in r["axes"]["fol"]["disagreements"][0]
        assert r["overall"]["any_disagreement"] is True

    async def test_dung_disagreement_per_semantics_surfaced(self):
        r = await compare_all_axes(
            dung_arguments=["s0", "s1"],
            dung_attacks=[["s0", "s1"]],
            dung_compare_fn=_dung_fake(
                {
                    "grounded": {
                        "agreement": False,
                        "decided": ["t", "s"],
                        "disagreement": ["t vs s"],
                    },
                    "preferred": {
                        "agreement": True,
                        "decided": ["t", "s"],
                        "disagreement": [],
                    },
                },
                False,
            ),
        )
        # Dung disagreements are gathered per-semantics with the [sem] prefix.
        dis = r["axes"]["dung"]["disagreements"]
        assert any("[grounded]" in d and "t vs s" in d for d in dis)
        assert not any("preferred" in d for d in dis)
        assert r["axes"]["dung"]["agreement"] is False
        assert r["overall"]["any_disagreement"] is True

    async def test_sophism_elimination_is_disagreement(self):
        # The symbolic layer eliminated cand-1 → neuro-symbolic != neural.
        r = await compare_all_axes(
            sophism_candidates=["c0", "c1"],
            sophism_span_text_for=lambda c: "x",
            sophism_compare_fn=_sophism_fake(["c1"], honest_absent=False),
        )
        assert r["axes"]["sophism"]["agreement"] is False
        assert any("eliminated: c1" in d for d in r["axes"]["sophism"]["disagreements"])
        assert r["overall"]["any_disagreement"] is True

    async def test_sophism_honest_absent_is_indeterminate_not_agreement(self):
        # No genuine CQ evaluation → honest-absent → agreement None, NOT a
        # fabricated True agreement (anti-théâtre #1019).
        r = await compare_all_axes(
            sophism_candidates=["c0", "c1"],
            sophism_span_text_for=lambda c: "x",
            sophism_compare_fn=_sophism_fake([], honest_absent=True),
        )
        assert r["axes"]["sophism"]["agreement"] is None
        assert r["axes"]["sophism"]["disagreements"] == []
        assert r["overall"]["any_disagreement"] is False

    async def test_full_agreement_all_axes(self):
        r = await compare_all_axes(
            fol_belief_set="dummy",
            fol_compare_fn=_fol_fake({"e": True, "p": True}, True, []),
            dung_arguments=["s0"],
            dung_attacks=[],
            dung_compare_fn=_dung_fake(
                {
                    "grounded": {
                        "agreement": True,
                        "decided": ["a", "b"],
                        "disagreement": [],
                    }
                },
                True,
            ),
            sophism_candidates=["c0"],
            sophism_span_text_for=lambda c: "x",
            sophism_compare_fn=_sophism_fake([], honest_absent=False),
        )
        for axis in ("fol", "dung", "sophism"):
            assert r["axes"][axis]["agreement"] is True
        assert r["overall"]["any_disagreement"] is False


# -- unavailable / fail-loud -------------------------------------------------


class TestUnavailableFailLoud:
    async def test_axis_no_input_reported_unavailable(self):
        # fol explicitly selected but no belief set supplied → available=False,
        # NOT omitted.
        r = await compare_all_axes(axes=["fol"])
        assert r["axes"]["fol"]["available"] is False
        assert r["axes"]["fol"]["agreement"] is None
        assert "no input supplied" in r["axes"]["fol"]["note"]

    async def test_buggy_comparator_reported_not_poisoning(self):
        # A comparator that raises must NOT poison the harness.
        async def _boom(belief_set):
            raise RuntimeError("fol exploded")

        r = await compare_all_axes(
            fol_belief_set="dummy",
            fol_compare_fn=_boom,
            dung_arguments=["s0"],
            dung_attacks=[],
            dung_compare_fn=_dung_fake(
                {"grounded": {"agreement": True, "decided": ["a"], "disagreement": []}},
                True,
            ),
        )
        assert r["axes"]["fol"]["available"] is False
        assert "exploded" in r["axes"]["fol"]["note"]
        # The dung axis still ran.
        assert r["axes"]["dung"]["available"] is True


# -- payload normalizers ------------------------------------------------------


class TestNormalizers:
    def test_fol_normalizer_extracts_timings(self):
        out = _normalize_fol_payload(
            {
                "backends": {
                    "e": {
                        "verdict": True,
                        "note": "n",
                        "elapsed_ms": 5.0,
                        "available": True,
                    }
                },
                "decided": {"e": True},
                "agreement": True,
                "disagreement": [],
            }
        )
        assert out["available"] is True
        assert out["timings_ms"] == {"e": 5.0}
        assert out["agreement"] is True

    def test_dung_normalizer_gathers_per_semantics_disagreements(self):
        out = _normalize_dung_payload(
            {
                "backends": {
                    "t": {
                        "available": True,
                        "elapsed_ms": 2.0,
                        "extensions": {},
                        "note": "",
                    }
                },
                "comparison": {
                    "semantics": ["grounded", "preferred"],
                    "per_semantics": {
                        "grounded": {
                            "agreement": False,
                            "decided": ["t", "s"],
                            "disagreement": ["t vs s"],
                        },
                        "preferred": {
                            "agreement": True,
                            "decided": ["t", "s"],
                            "disagreement": [],
                        },
                    },
                    "overall_agreement": False,
                },
                "statistics": {},
            }
        )
        assert out["agreement"] is False
        assert len(out["disagreements"]) == 1
        assert "[grounded]" in out["disagreements"][0]

    def test_sophism_normalizer_honest_absent(self):
        out = _normalize_sophism_payload(
            {
                "neural_ids": frozenset({"c0"}),
                "neuro_symbolic_ids": frozenset({"c0"}),
                "eliminated_ids": frozenset(),
                "arbitrated": {"honest_absent": True},
            }
        )
        assert out["agreement"] is None  # honest-absent → indeterminate

    def test_normalizers_handle_bad_payload(self):
        for fn in (
            _normalize_fol_payload,
            _normalize_dung_payload,
            _normalize_sophism_payload,
        ):
            out = fn("not-a-dict")
            assert out["available"] is False
            assert out["agreement"] is None
            assert out["disagreements"] == []


# -- I6 PR2: pipeline-selectable handler wiring ------------------------------


class TestMultiAxisCompareHandler:
    """_invoke_multi_axis_compare wraps compare_all_axes and exposes it as a
    pipeline-selectable capability. Inputs are read from context["multi_axis"];
    DI comparators keep it JVM/LLM-free."""

    async def test_handler_routes_to_comparison_with_uniform_shape(self):
        ctx = {
            "multi_axis": {
                "fol_belief_set": "dummy",
                "fol_compare_fn": _fol_fake({"e": True}, True, []),
                "sophism_candidates": ["c0"],
                "sophism_span_text_for": lambda c: "x",
                "sophism_compare_fn": _sophism_fake([], honest_absent=False),
            }
        }
        out = await _invoke_multi_axis_compare("source text", ctx)
        assert out["semantics"] == "multi_axis_compare"
        assert out["comparison"]["overall"]["axes_run"] == ["fol", "sophism"]
        assert "NEVER auto-reconciled" in out["note"]

    async def test_handler_dung_inputs_derived_from_upstream(self):
        # dung axis explicitly selected, no explicit dung_arguments → derived
        # from phase_extract_output via the same helpers _invoke_dung_extensions
        # uses.
        ctx = {
            "phase_extract_output": {"arguments": ["s0", "s1"]},
            "multi_axis": {
                "axes": ["dung"],
                "dung_compare_fn": _dung_fake(
                    {
                        "grounded": {
                            "agreement": True,
                            "decided": ["a"],
                            "disagreement": [],
                        }
                    },
                    True,
                ),
            },
        }
        out = await _invoke_multi_axis_compare("source text", ctx)
        # The dung axis ran (inputs derived) and the fake comparator was called.
        assert out["comparison"]["overall"]["axes_run"] == ["dung"]
        assert out["comparison"]["axes"]["dung"]["available"] is True

    async def test_handler_explicit_axes_filter(self):
        ctx = {
            "multi_axis": {
                "axes": ["fol"],
                "fol_belief_set": "dummy",
                "fol_compare_fn": _fol_fake({"e": True, "p": True}, True, []),
                "sophism_candidates": ["c0"],  # supplied but filtered out
                "sophism_span_text_for": lambda c: "x",
                "sophism_compare_fn": _sophism_fake([], honest_absent=False),
            }
        }
        out = await _invoke_multi_axis_compare("source text", ctx)
        assert out["comparison"]["overall"]["axes_run"] == ["fol"]

    async def test_handler_empty_config_is_honest_absent(self):
        # No multi_axis cfg, no upstream extraction → no axis decided → NOT a
        # fabricated agreement (anti-théâtre #1019).
        out = await _invoke_multi_axis_compare("source text", {})
        assert out["semantics"] == "multi_axis_compare"
        assert out["comparison"]["overall"]["axes_run"] == []
        assert out["comparison"]["overall"]["any_disagreement"] is False

    async def test_handler_surfaces_disagreement_not_reconciled(self):
        ctx = {
            "multi_axis": {
                "fol_belief_set": "dummy",
                "fol_compare_fn": _fol_fake(
                    {"e": True, "p": False}, False, ["NOT reconciled: e vs p"]
                ),
            }
        }
        out = await _invoke_multi_axis_compare("source text", ctx)
        fol = out["comparison"]["axes"]["fol"]
        assert fol["agreement"] is False
        assert any("NOT reconciled" in d for d in fol["disagreements"])
        assert out["comparison"]["overall"]["any_disagreement"] is True

    async def test_capability_registered_selectable(self):
        # The handler must be registered under the multi_axis_compare capability
        # so a workflow phase can select it (I6 PR2 DoD). We verify the wiring
        # statically (the service tuple names the capability + handler) rather
        # than building the full registry, which would instantiate JVM agents.
        import inspect

        from argumentation_analysis.orchestration import registry_setup

        src = inspect.getsource(registry_setup)
        # The capability string and the handler are both wired in the source.
        assert "multi_axis_compare" in src
        assert "_invoke_multi_axis_compare" in src
        # And the handler is importable from the module (the import the tuple uses).
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_multi_axis_compare as _h,
        )

        assert callable(_h)


# -- GE-3 #1456: genuinely-reachable neural tier for the sophism axis ----------


class TestGE3NeuralTier:
    """GE-3 (#1456, Epic #1448). The sophism axis is genuinely bilateral only
    when the NEURAL tier decides. These tests pin the honest-degraded contract:
    neural unreachable ⇒ axis available=False (degraded, never a fake agreement);
    neural reachable ⇒ axis runs with the derived candidates. No JVM, no real
    LLM (the detector is monkeypatched)."""

    _NEURAL_DETECT_PATH = (
        "argumentation_analysis.agents.core.informal."
        "neuro_symbolic_arbitrator.llm_neural_detect_async"
    )

    def test_normalize_neural_unreachable_is_degraded(self) -> None:
        """A sophism payload with neural_reachable=False surfaces as available=False
        with a proven degraded cause — NOT as a vacuous agreement (anti-théâtre)."""
        out = _normalize_sophism_payload(
            {
                "neural_ids": frozenset(),
                "neuro_symbolic_ids": frozenset(),
                "eliminated_ids": frozenset(),
                "arbitrated": {"honest_absent": True},
                "span_coverage": {},
                "neural_reachable": False,
            }
        )
        assert out["available"] is False
        assert out["agreement"] is None
        assert out["backends"]["neural"]["available"] is False
        assert "degraded" in out["note"]

    def test_normalize_reachable_with_genuine_split_reports_disagreement(
        self,
    ) -> None:
        """Reachable tier + a genuine symbolic elimination ⇒ available=True and
        agreement=False (a real, unreconciled bilateral disagreement)."""
        out = _normalize_sophism_payload(
            {
                "neural_ids": frozenset({"s0", "s1"}),
                "neuro_symbolic_ids": frozenset({"s1"}),
                "eliminated_ids": frozenset({"s0"}),
                "arbitrated": {"honest_absent": False},
                "span_coverage": {"s0": "expert_opinion"},
                "neural_reachable": True,
            }
        )
        assert out["available"] is True
        assert out["agreement"] is False
        assert out["disagreements"] == ["eliminated: s0"]

    async def test_handler_auto_derives_sophism_from_llm(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DoD #1456 (a): caller opts into the sophism axis without explicit
        candidates ⇒ the handler auto-derives them from the (mocked) reachable
        neural tier and the axis genuinely runs (available=True)."""
        from argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator import (
            SophismCandidate,
        )

        async def _fake_detect(text: str):
            cands = [
                SophismCandidate("s0", "ad_hominem", "span_a", 0.9),
                SophismCandidate("s1", "straw_man", "span_b", 0.7),
            ]
            return cands, lambda c: "passage text", True

        monkeypatch.setattr(self._NEURAL_DETECT_PATH, _fake_detect)

        ctx = {"multi_axis": {"axes": ["sophism"]}}
        out = await _invoke_multi_axis_compare("source text", ctx)
        ax = out["comparison"]["axes"]["sophism"]
        assert ax["available"] is True
        assert ax["backends"]["neural"]["available"] is True

    async def test_handler_neural_unreachable_is_degraded(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DoD #1456 (b): neural tier genuinely unavailable (no key / call failed)
        ⇒ the sophism axis is degraded (available=False), NEVER presented as a
        genuine comparison (anti-théâtre #1019)."""
        from argumentation_analysis.agents.core.informal.neuro_symbolic_arbitrator import (
            SophismCandidate,
        )

        async def _fake_unreachable(text: str):
            return [], lambda c: "", False

        monkeypatch.setattr(self._NEURAL_DETECT_PATH, _fake_unreachable)

        ctx = {"multi_axis": {"axes": ["sophism"]}}
        out = await _invoke_multi_axis_compare("source text", ctx)
        ax = out["comparison"]["axes"]["sophism"]
        assert ax["available"] is False  # degraded, NOT a fake comparison
        assert ax["agreement"] is None
        assert ax["backends"]["neural"]["available"] is False
        assert "degraded" in ax.get("note", "")

    async def test_handler_explicit_candidates_skip_auto_derivation(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the caller supplies explicit candidates, auto-derivation is NOT
        triggered (the detector must not be called) — anti-pendule: don't run an
        LLM call the caller did not ask for."""

        async def _boom(text: str):
            raise AssertionError("auto-derivation must not run when candidates given")

        monkeypatch.setattr(self._NEURAL_DETECT_PATH, _boom)

        ctx = {
            "multi_axis": {
                "axes": ["sophism"],
                "sophism_candidates": ["c0"],
                "sophism_span_text_for": lambda c: "x",
                "sophism_compare_fn": _sophism_fake([], honest_absent=True),
            }
        }
        out = await _invoke_multi_axis_compare("source text", ctx)
        ax = out["comparison"]["axes"]["sophism"]
        assert ax["available"] is True  # injected comparator ran, no LLM call

