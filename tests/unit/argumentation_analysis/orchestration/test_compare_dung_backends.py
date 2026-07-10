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
