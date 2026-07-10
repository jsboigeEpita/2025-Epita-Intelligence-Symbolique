"""I5 #1430 — compare_dung_backends multi-backend Dung comparison unit tests.

Mirrors the anti-théâtre contract of the FOL multi-prover frame (#1243):
- DISAGREEMENT between backends is surfaced, NEVER auto-reconciled (a
  disagreement is a result, not a bug to mask).
- A backend that cannot run is reported ``available=False`` (fail-loud), never
  silently omitted.
- Extension SETS compare order-independently (a Dung extension is a set).

No JVM, no real LLM, synthetic opaque AFs only (privacy HARD — no corpus tokens).
"""

from __future__ import annotations

from typing import Any, Dict, List

from argumentation_analysis.orchestration.invoke_callables import (
    _compare_dung_backends,
    _default_student_dung_backend,
    _extensions_key,
    _normalize_extensions,
    _pairs,
)


# -- helpers ------------------------------------------------------------------


def _backend(
    extensions: Dict[str, List[List[str]]], available: bool = True, note: str = ""
):
    """Build an injected fake backend callable returning a fixed payload."""

    async def _fn(arguments: List[str], attacks: List[List[str]]) -> Dict[str, Any]:
        return {"extensions": extensions, "available": available, "note": note}

    return _fn


# -- _normalize_extensions / _extensions_key / _pairs -------------------------


class TestHelpers:
    def test_normalize_extensions_flat_dict(self):
        raw = {"grounded": [["a", "b"]], "preferred": [["a"], ["b"]]}
        out = _normalize_extensions(raw, ("grounded",))
        assert out == [["a", "b"]]

    def test_normalize_extensions_nested_under_extensions(self):
        raw = {"extensions": {"grounded": [["a"]]}}
        assert _normalize_extensions(raw, ("grounded",)) == [["a"]]

    def test_normalize_extensions_drops_error_and_nonlist(self):
        raw = {"grounded": {"error": "boom"}, "preferred": "nope", "stable": [["c"]]}
        assert _normalize_extensions(raw, ("grounded", "preferred", "stable")) == [
            ["c"]
        ]

    def test_normalize_extensions_bad_shape_returns_empty(self):
        assert _normalize_extensions("nope", ("grounded",)) == []
        assert _normalize_extensions(42, ("grounded",)) == []

    def test_extensions_key_order_independent(self):
        assert _extensions_key([["a", "b"]]) == _extensions_key([["b", "a"]])
        assert _extensions_key([["a"], ["b"]]) == _extensions_key([["b"], ["a"]])

    def test_pairs_unordered(self):
        assert _pairs(["a", "b", "c"]) == [("a", "b"), ("a", "c"), ("b", "c")]
        assert _pairs([]) == []
        assert _pairs(["solo"]) == []


# -- agreement ----------------------------------------------------------------


class TestAgreement:
    async def test_full_agreement_order_independent(self):
        # Both backends agree on grounded/preferred despite different listing order.
        be1 = _backend({"grounded": [["a", "b"]], "preferred": [["a", "b"]]})
        be2 = _backend({"grounded": [["b", "a"]], "preferred": [["b", "a"]]})
        r = await _compare_dung_backends(
            ["a", "b"], [["a", "b"]], backends={"A": be1, "B": be2}
        )
        assert r["comparison"]["per_semantics"]["grounded"]["agreement"] is True
        assert r["comparison"]["per_semantics"]["preferred"]["agreement"] is True
        assert r["comparison"]["overall_agreement"] is True
        assert r["comparison"]["per_semantics"]["grounded"]["disagreement"] == []

    async def test_disagreement_surfaced_never_reconciled(self):
        # Grounded extension differs between backends → disagreement listed verbatim.
        be1 = _backend({"grounded": [["a", "b"]]})
        be2 = _backend({"grounded": [["a"]]})  # smaller extension
        r = await _compare_dung_backends(
            ["a", "b"], [["a", "b"]], backends={"A": be1, "B": be2}
        )
        per = r["comparison"]["per_semantics"]["grounded"]
        assert per["agreement"] is False
        assert len(per["disagreement"]) == 1
        assert "A" in per["disagreement"][0] and "B" in per["disagreement"][0]
        assert r["comparison"]["overall_agreement"] is False

    async def test_mixed_agreement_per_semantics(self):
        # Agree on grounded, disagree on preferred → overall False (any disagree).
        be1 = _backend({"grounded": [["a"]], "preferred": [["a", "b"]]})
        be2 = _backend({"grounded": [["a"]], "preferred": [["a"]]})
        r = await _compare_dung_backends(
            ["a", "b"], [["a", "b"]], backends={"A": be1, "B": be2}
        )
        assert r["comparison"]["per_semantics"]["grounded"]["agreement"] is True
        assert r["comparison"]["per_semantics"]["preferred"]["agreement"] is False
        assert r["comparison"]["overall_agreement"] is False

    async def test_three_backends_pairwise_disagreement(self):
        be1 = _backend({"grounded": [["a", "b"]]})
        be2 = _backend({"grounded": [["a", "b"]]})
        be3 = _backend({"grounded": [["a"]]})
        r = await _compare_dung_backends(
            ["a", "b"], [["a", "b"]], backends={"A": be1, "B": be2, "C": be3}
        )
        per = r["comparison"]["per_semantics"]["grounded"]
        assert per["agreement"] is False
        # A↔C and B↔C differ (2 disagree notes), A↔B agrees.
        assert len(per["disagreement"]) == 2


# -- unavailable / fail-loud --------------------------------------------------


class TestUnavailableFailLoud:
    async def test_unavailable_backend_reported_not_omitted(self):
        # Backend B cannot run → available=False, kept in the report, agreement None.
        be1 = _backend({"grounded": [["a", "b"]]})
        be2 = _backend({}, available=False, note="unavailable: JVM down")
        r = await _compare_dung_backends(
            ["a", "b"], [["a", "b"]], backends={"A": be1, "B": be2}
        )
        assert r["backends"]["B"]["available"] is False
        assert "JVM down" in r["backends"]["B"]["note"]
        assert r["backends"]["B"] in r["backends"].values()  # NOT omitted
        # Only one decided backend → agreement indeterminate.
        assert r["comparison"]["per_semantics"]["grounded"]["agreement"] is None
        assert r["comparison"]["overall_agreement"] is None

    async def test_all_unavailable_overall_none(self):
        be1 = _backend({}, available=False)
        be2 = _backend({}, available=False)
        r = await _compare_dung_backends(
            ["a", "b"], [["a", "b"]], backends={"A": be1, "B": be2}
        )
        assert r["comparison"]["overall_agreement"] is None
        assert r["statistics"]["backends_count"] == 2

    async def test_backend_exception_caught_as_unavailable(self):
        # A buggy backend (raises) must NOT poison the comparison.

        async def _boom(arguments, attacks):
            raise RuntimeError("backend exploded")

        be_ok = _backend({"grounded": [["a"]]})
        r = await _compare_dung_backends(
            ["a", "b"], [["a", "b"]], backends={"ok": be_ok, "boom": _boom}
        )
        assert r["backends"]["boom"]["available"] is False
        assert "exploded" in r["backends"]["boom"]["note"]


# -- structure / statistics ---------------------------------------------------


class TestStructure:
    async def test_default_semantics_are_the_four_common(self):
        be = _backend({"grounded": [["a"]]})
        r = await _compare_dung_backends(["a"], [], backends={"A": be})
        assert r["comparison"]["semantics"] == [
            "grounded",
            "preferred",
            "stable",
            "complete",
        ]

    async def test_custom_semantics(self):
        be1 = _backend({"only_sem": [["a"]]})
        be2 = _backend({"only_sem": [["a"]]})
        r = await _compare_dung_backends(
            ["a"], [], backends={"A": be1, "B": be2}, semantics=("only_sem",)
        )
        assert r["comparison"]["semantics"] == ["only_sem"]
        assert r["comparison"]["per_semantics"]["only_sem"]["agreement"] is True

    async def test_statistics_counts(self):
        be = _backend({"grounded": [["a", "b"]]})
        r = await _compare_dung_backends(
            ["a", "b", "c"], [["a", "b"], ["b", "c"]], backends={"A": be, "B": be}
        )
        assert r["statistics"]["arguments_count"] == 3
        assert r["statistics"]["attacks_count"] == 2
        assert r["statistics"]["backends_count"] == 2

    async def test_per_semantics_decided_lists_backends(self):
        be1 = _backend({"grounded": [["a"]]})
        be2 = _backend({"grounded": [["a"]]})
        r = await _compare_dung_backends(
            ["a"], [], backends={"A": be1, "B": be2}
        )
        assert sorted(r["comparison"]["per_semantics"]["grounded"]["decided"]) == [
            "A",
            "B",
        ]


# -- wiring into _invoke_dung_extensions (I5 PR2) ----------------------------


class TestDungCompareWiring:
    """dung_mode="compare" routes _invoke_dung_extensions through the
    multi-backend comparison, surfacing agreement (never reconciled) without a
    JVM — the real backends are monkeypatched to deterministic fakes."""

    async def test_compare_mode_routes_to_comparison(self, monkeypatch):
        from argumentation_analysis.orchestration import invoke_callables as ic

        # Monkeypatch the real comparison fn → deterministic fake (no JVM).
        fake_comparison = {
            "backends": {
                "tweety": {"extensions": {"grounded": [["a", "b"]]}, "available": True},
                "student": {"extensions": {"grounded": [["a"]]}, "available": True},
            },
            "comparison": {
                "semantics": ["grounded"],
                "per_semantics": {
                    "grounded": {
                        "agreement": False,
                        "decided": ["tweety", "student"],
                        "disagreement": ["tweety vs student"],
                    }
                },
                "overall_agreement": False,
            },
            "statistics": {"arguments_count": 2, "attacks_count": 1, "backends_count": 2},
        }

        async def _fake_compare(arguments, attacks, **kwargs):
            return fake_comparison

        monkeypatch.setattr(ic, "_compare_dung_backends", _fake_compare)

        ctx = {
            "phase_extract_output": {"arguments": ["a", "b"]},
            "dung_mode": "compare",
        }
        out = await ic._invoke_dung_extensions("source text", ctx)

        assert out["semantics"] == "multi_compare"
        assert out["comparison"]["overall_agreement"] is False
        assert out["statistics"]["backends_count"] == 2
        # Disagreement surfaced verbatim, never reconciled.
        assert out["comparison"]["per_semantics"]["grounded"]["disagreement"] == [
            "tweety vs student"
        ]
        assert "NEVER auto-reconciled" in out["note"]

    async def test_default_mode_does_not_compare(self, monkeypatch):
        # Without dung_mode="compare", the comparison fn is NEVER invoked.
        from argumentation_analysis.orchestration import invoke_callables as ic

        called = {"n": 0}

        async def _fake_compare(arguments, attacks, **kwargs):
            called["n"] += 1
            return {}

        monkeypatch.setattr(ic, "_compare_dung_backends", _fake_compare)
        # Monkeypatch the native AFHandler path so no JVM is needed: make the
        # try-block raise → degraded honest-absent return (the real fallback).
        monkeypatch.setattr(
            ic.asyncio, "to_thread", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no JVM"))
        )

        ctx = {"phase_extract_output": {"arguments": ["a", "b"]}}
        out = await ic._invoke_dung_extensions("source text", ctx)

        assert called["n"] == 0  # compare fn never invoked (default mode)
        assert out["semantics"] == "unavailable"  # degraded honest-absent (no JVM)

    async def test_compare_mode_available_backend_unavailable_reported(self, monkeypatch):
        # Even in compare mode, an unavailable backend is reported, not omitted.
        from argumentation_analysis.orchestration import invoke_callables as ic

        fake_comparison = {
            "backends": {
                "tweety": {"extensions": {}, "available": False, "note": "no JVM"},
                "student": {"extensions": {}, "available": False, "note": "no JVM"},
            },
            "comparison": {
                "semantics": ["grounded"],
                "per_semantics": {"grounded": {"agreement": None, "decided": [], "disagreement": []}},
                "overall_agreement": None,
            },
            "statistics": {"arguments_count": 1, "attacks_count": 0, "backends_count": 2},
        }

        async def _fake_compare(arguments, attacks, **kwargs):
            return fake_comparison

        monkeypatch.setattr(ic, "_compare_dung_backends", _fake_compare)

        ctx = {
            "phase_extract_output": {"arguments": ["a"]},
            "dung_mode": "compare",
        }
        out = await ic._invoke_dung_extensions("source text", ctx)
        # Both backends reported unavailable (fail-loud), agreement indeterminate.
        assert out["backends"]["tweety"]["available"] is False
        assert out["backends"]["student"]["available"] is False
        assert out["comparison"]["overall_agreement"] is None


# -- PR3 regression: student backend shape normalization ---------------------
#
# PR3 firsthand probing (real JVM, both backends) caught a spurious-disagreement
# bug: DungStudentProvider.compute_extensions returns per-semantics extensions
# nested under ``all_extensions`` (each value a ``{extensions, count, sizes,
# all_members}`` wrapper), and the top-level ``extensions`` is only the DEFAULT
# set, also wrapped. _default_student_dung_backend used to read that wrapper raw,
# so _normalize_extensions extracted [] → a FALSE disagreement even when both
# backends compute the identical extension set. These tests lock the fix using
# the REAL observed shape (not an injected fake with the hoped-for shape).


_STUDENT_REAL_SHAPE = {
    "provider": "abs_arg_dung_student",
    "semantics": "multi",
    "extensions": {  # default-semantics wrapper (NOT the per-semantics dict)
        "extensions": [["arg0", "arg2"]],
        "count": 1,
        "sizes": [2],
        "all_members": ["arg0", "arg2"],
    },
    "all_extensions": {  # the actual per-semantics payload
        sem: {
            "extensions": [["arg0", "arg2"]],
            "count": 1,
            "sizes": [2],
            "all_members": ["arg0", "arg2"],
        }
        for sem in ("grounded", "preferred", "stable", "complete")
    },
}


class TestStudentBackendNormalization:
    """The student backend must normalize the all_extensions wrapper into the
    {sem: [[args]]} contract, or the comparison reads a spurious disagreement."""

    async def test_backend_returns_per_semantics_dict(self, monkeypatch):
        from argumentation_analysis.adapters import dung_student_provider as dsp

        class _FakeProvider:
            async def compute_extensions(self, arguments, attacks):
                return _STUDENT_REAL_SHAPE

        monkeypatch.setattr(dsp, "DungStudentProvider", _FakeProvider)

        out = await _default_student_dung_backend(
            ["arg0", "arg1", "arg2"], [["arg0", "arg1"], ["arg1", "arg2"]]
        )
        assert out["available"] is True
        # Per-semantics dict extracted, not the raw wrapper.
        assert out["extensions"]["grounded"] == [["arg0", "arg2"]]
        assert out["extensions"]["preferred"] == [["arg0", "arg2"]]
        assert out["extensions"]["stable"] == [["arg0", "arg2"]]
        assert out["extensions"]["complete"] == [["arg0", "arg2"]]
        # Wrapper keys must NOT leak into the per-semantics dict.
        assert "count" not in out["extensions"]
        assert "all_members" not in out["extensions"]

    async def test_normalization_yields_genuine_agreement(self, monkeypatch):
        """With the fix, two backends computing the SAME set AGREE — the
        spurious disagreement is gone (anti-théâtre #1019)."""
        from argumentation_analysis.adapters import dung_student_provider as dsp

        ext_set = [["arg0", "arg2"]]

        class _FakeProvider:
            async def compute_extensions(self, arguments, attacks):
                shape = {
                    "extensions": {"extensions": ext_set, "count": 1,
                                   "sizes": [2], "all_members": ["arg0", "arg2"]},
                    "all_extensions": {
                        sem: {"extensions": ext_set, "count": 1, "sizes": [2],
                              "all_members": ["arg0", "arg2"]}
                        for sem in ("grounded", "preferred", "stable", "complete")
                    },
                }
                return shape

        monkeypatch.setattr(dsp, "DungStudentProvider", _FakeProvider)

        tweety = _backend(
            {sem: ext_set for sem in ("grounded", "preferred", "stable", "complete")}
        )
        r = await _compare_dung_backends(
            ["arg0", "arg1", "arg2"], [["arg0", "arg1"], ["arg1", "arg2"]],
            backends={"tweety": tweety,
                      "abs_arg_dung_student": _default_student_dung_backend},
        )
        # BEFORE the fix this was False (spurious); AFTER it is True (genuine).
        assert r["comparison"]["overall_agreement"] is True
        assert r["comparison"]["per_semantics"]["grounded"]["agreement"] is True
        assert r["comparison"]["per_semantics"]["grounded"]["disagreement"] == []

    async def test_real_disagreement_still_surfaced_with_student_normalized(
        self, monkeypatch
    ):
        """Normalization does not mask a GENUINE disagreement: when the student
        computes a different set than Tweety, it is still surfaced verbatim."""
        from argumentation_analysis.adapters import dung_student_provider as dsp

        class _FakeProvider:
            async def compute_extensions(self, arguments, attacks):
                return {
                    "extensions": {"extensions": [["arg0"]], "count": 1,
                                   "sizes": [1], "all_members": ["arg0"]},
                    "all_extensions": {
                        sem: {"extensions": [["arg0"]], "count": 1, "sizes": [1],
                              "all_members": ["arg0"]}
                        for sem in ("grounded", "preferred", "stable", "complete")
                    },
                }

        monkeypatch.setattr(dsp, "DungStudentProvider", _FakeProvider)

        tweety = _backend(
            {sem: [["arg0", "arg2"]] for sem in
             ("grounded", "preferred", "stable", "complete")}
        )
        r = await _compare_dung_backends(
            ["arg0", "arg1", "arg2"], [["arg0", "arg1"], ["arg1", "arg2"]],
            backends={"tweety": tweety,
                      "abs_arg_dung_student": _default_student_dung_backend},
        )
        per = r["comparison"]["per_semantics"]["grounded"]
        assert per["agreement"] is False  # genuine disagreement, not masked
        assert len(per["disagreement"]) == 1
