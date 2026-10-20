"""#3088 — the belief-revision phase completes on the real-run population.

The issue measured the phase on the 40-unit population #3014 introduced: the
flat minimum-correction-subset sweep walked C(40, k) over the 50-clause base,
exhausted its subset budget during the k=8 pass after ~36 s and returned a bare
``-1``; the Tweety handler then died with ``java.lang.OutOfMemoryError`` (same
probe, JVM up). Every standing pass lost the axis.

These guards pin the repair on both halves:

* the insight DECOMPOSES over connected components — exact (checked
  differentially against the flat sweep on a small mixed base), milliseconds on
  the issue's own shape, cardinality 10 with ``options_total`` 2**10;
* the handler is bounded BY NAME above the measured-safe belief count (ladder:
  8 -> 0.01 s, 16 -> 2.76 s, 24 -> OutOfMemoryError after 112 s), the refusal
  carrying the figure and the measurement;
* every refusal past a bound NAMES ITSELF and its reason — never a bare -1;
* two mutation controls — neutralize the decomposition, neutralize the bound —
  so the witness is shown to measure THOSE, not something else.

Offline, zero spend, no JVM, no API key. Opaque synthetic atoms only.
"""

from __future__ import annotations

import time
from itertools import combinations
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from argumentation_analysis.agents.core.logic.belief_revision_insight import (
    build_belief_base,
    minimal_retractions,
    shape_minimal_retraction,
)

_BRIDGE_BR = (
    "argumentation_analysis.agents.core.logic.belief_revision_handler."
    "BeliefRevisionHandler"
)
_JVM_STARTED = "argumentation_analysis.core.jvm_setup.is_jvm_started"


def _run(coro):
    import asyncio

    return asyncio.run(coro)


# The issue's own shape: 40 units (the #3014 population), 10 of them targeted by
# a fallacy — 50 clauses, 10 independent clash pairs.
_N_UNITS = 40
_N_TARGETED = 10
# The stated budget this witness holds the phase to. The pre-repair phase spent
# ~36 s in the insight sweep alone and then timed out at the phase's 180 s wall.
_STATED_BUDGET_S = 30.0


def _issue_shape_texts() -> List[str]:
    return [
        f"Unite {i} : enonce synthetique distinct, opaque, sans contenu de corpus."
        for i in range(1, _N_UNITS + 1)
    ]


def _issue_shape_context() -> Dict[str, object]:
    targets = [f"arg_{i}" for i in range(1, _N_TARGETED + 1)]
    return {
        "arguments": _issue_shape_texts(),
        "phase_hierarchical_fallacy_output": {
            "fallacies": [
                {
                    "target_argument": t,
                    "type": "ad_hominem",
                    "fallacy_type": "ad_hominem",
                }
                for t in targets
            ]
        },
        "revision_method": "dalal",
    }


def _flat_mcs(base: List[List[int]]) -> Tuple[int, int]:
    """The pre-#3088 flat sweep, kept HERE as an independent oracle.

    Exact on a small base (where C(n, k) is tiny), unusable on a real one —
    which is the whole point. Returns ``(cardinality, option_count)``, or
    ``(-1, 0)`` when a bound stopped it.
    """
    from argumentation_analysis.agents.core.logic.belief_revision_insight import (
        _MAX_SEARCH_K,
        _MAX_SUBSET_BUDGET,
        _is_satisfiable,
    )

    if _is_satisfiable(base):
        return 0, 1
    n = len(base)
    budget = _MAX_SUBSET_BUDGET
    for k in range(1, min(_MAX_SEARCH_K, n) + 1):
        winners = 0
        for drop in combinations(range(n), k):
            budget -= 1
            if budget < 0:
                return -1, 0
            kept = [base[i] for i in range(n) if i not in drop]
            if _is_satisfiable(kept):
                winners += 1
        if winners:
            return k, winners
    return -1, 0


# A small mixed base: three unsatisfiable components (cardinality 1, 1 and 2 —
# so the summed answer is 4 and the product of options 3*2*4 = 24) and one
# satisfiable component that must contribute to neither.
_MIXED_BASE: List[List[int]] = [
    [1],
    [-1, 2],
    [-2],  # chain cluster: cardinal 1, three options
    [5],
    [-5],  # bare contradiction: cardinal 1, two options
    [7, 8],
    [-7, 9],  # satisfiable chain — contributes nothing
    [11],
    [12],
    [-11],
    [-12],  # two pairs, one component: cardinal 2, four options
]


class TestIssueShapeThroughTheProductionCallable:
    """DoD item 1: the exact issue shape, through the production callable."""

    def test_forty_units_ten_targets_completes_under_budget(self):
        """Cardinality 10, ``options_total`` 2**10, inside the stated budget.

        Pre-repair on the same shape: ``cardinality -1`` after ~36 s of sweep
        (the issue's measurement), and the handler OOM instead of returning.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )

        mock_handler = MagicMock()
        mock_handler.revise.return_value = {
            "method": "dalal",
            "original": [],
            "revised": [],
        }
        with patch(_BRIDGE_BR, return_value=mock_handler), patch(
            _JVM_STARTED, return_value=True
        ):
            started = time.perf_counter()
            result = _run(_invoke_belief_revision("text", _issue_shape_context()))
            elapsed = time.perf_counter() - started

        assert elapsed < _STATED_BUDGET_S, (
            f"the phase took {elapsed:.1f} s on the issue's shape; the stated "
            f"budget is {_STATED_BUDGET_S:.0f} s (pre-repair: ~36 s and no answer)"
        )
        mr = result["minimal_retraction"]
        assert mr["cardinality"] == _N_TARGETED, (
            "10 targeted units = 10 independent clash pairs: the minimal "
            f"retraction is cardinal 10, got {mr['cardinality']}"
        )
        assert mr["options_total"] == 2**_N_TARGETED
        assert mr["degraded"] is False
        # 40 units + 10 negations = 50 clauses; the 20 clash clauses are the
        # only ones any minimal option touches.
        assert mr["base_size"] == _N_UNITS + _N_TARGETED
        assert mr["touched_count"] == 2 * _N_TARGETED

    def test_the_handler_refusal_is_by_name_with_its_figure(self):
        """DoD item 4: 40 beliefs are past the measured-safe handler bound, and
        the result says so — the bound, the figure and the measurement."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_belief_revision,
        )

        mock_handler = MagicMock()
        with patch(_BRIDGE_BR, return_value=mock_handler), patch(
            _JVM_STARTED, return_value=True
        ):
            result = _run(_invoke_belief_revision("text", _issue_shape_context()))

        assert result["degraded"] is True
        assert result["absent_reason"] == "handler_size_bound"
        assert result["revised"] == []  # tri-state: not computed
        assert result["statistics"]["bound"] == "beliefs <= 16"
        assert "OutOfMemoryError" in result["statistics"]["measured"]
        assert "40 beliefs" in result["message"]
        mock_handler.revise.assert_not_called()
        # The insight — computed JVM-free — still reaches the state entry.
        assert result["minimal_retraction"]["cardinality"] == _N_TARGETED

    def test_bound_mutation_control_lets_the_handler_run_again(self):
        """Mutation control for the bound row: neutralize it and the handler IS
        called — so the witness above measures the bound, not a stub."""
        from argumentation_analysis.orchestration import invoke_callables as ic

        mock_handler = MagicMock()
        mock_handler.revise.return_value = {
            "method": "dalal",
            "original": [],
            "revised": [],
        }
        with patch.object(ic, "_HANDLER_MAX_BELIEFS", 10**6), patch(
            _BRIDGE_BR, return_value=mock_handler
        ), patch(_JVM_STARTED, return_value=True):
            result = _run(ic._invoke_belief_revision("text", _issue_shape_context()))

        mock_handler.revise.assert_called_once()
        assert result.get("absent_reason") != "handler_size_bound"

    def test_the_bound_is_the_measured_safe_count(self):
        """The bound is a MEASUREMENT, not a guess: the ladder that fixes it."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _HANDLER_MAX_BELIEFS,
        )

        assert _HANDLER_MAX_BELIEFS == 16, (
            "the ladder measured 8 beliefs -> 0.01 s, 16 -> 2.76 s and 24 -> "
            "java.lang.OutOfMemoryError after 112 s (fresh JVM, 2 GB heap); the "
            "bound sits at the largest measured-safe count. Re-measure before "
            "moving it."
        )


class TestDecompositionIsExact:
    """DoD item 3: the decomposition answers exactly, and small cases do not move."""

    def test_issue_shape_at_the_insight_level(self):
        base, names = build_belief_base(
            [f"arg_{i}" for i in range(1, _N_UNITS + 1)], list(range(_N_TARGETED))
        )
        started = time.perf_counter()
        result = minimal_retractions(base)
        elapsed = time.perf_counter() - started

        assert result.cardinality == _N_TARGETED
        assert result.options_total == 2**_N_TARGETED
        assert result.refusal is None
        assert result.degraded is False
        assert elapsed < 5.0, f"the decomposed sweep took {elapsed:.2f} s"
        shaped = shape_minimal_retraction(result, names)
        assert shaped["options_total"] == 2**_N_TARGETED
        assert shaped["touched_count"] == 2 * _N_TARGETED

    def test_decomposition_equals_the_flat_sweep(self):
        """Differential: on a base small enough for both, the decomposed answer
        IS the flat sweep's — cardinality and option count alike. The
        decomposition is an identity on the answer, not an approximation."""
        flat_card, flat_count = _flat_mcs(_MIXED_BASE)
        assert (flat_card, flat_count) == (4, 24), (
            "the oracle itself must see the mixed base's answer "
            f"(4, 24); got ({flat_card}, {flat_count})"
        )
        result = minimal_retractions(_MIXED_BASE)
        assert result.cardinality == flat_card
        assert result.options_total == flat_count

    def test_planted_cardinal_one_and_two_do_not_regress(self):
        """The docstring examples and the planted scales, unchanged."""
        b1 = minimal_retractions([[1], [-1, 2], [-2]])
        assert b1.cardinality == 1 and b1.options_total == 3
        # B-3: the clash is repaired without ever touching the conclusions.
        b3 = minimal_retractions([[1], [-1], [5], [6]])
        assert b3.cardinality == 1
        assert all(i in (0, 1) for opt in b3.options for i in opt)
        # Two independently negated beliefs: cardinal 2, four options.
        base, _names = build_belief_base(["x", "y"], [0, 1])
        two = minimal_retractions(base)
        assert two.cardinality == 2 and two.options_total == 4

    def test_flat_sweep_control_would_refuse_the_issue_shape(self):
        """Mutation control for the decomposition row: force the flat sweep back
        (one component) under a small budget and the issue's shape refuses —
        proving the decomposition is what makes it answer."""
        from argumentation_analysis.agents.core.logic import (
            belief_revision_insight as bri,
        )

        base, _names = build_belief_base(
            [f"arg_{i}" for i in range(1, _N_UNITS + 1)], list(range(_N_TARGETED))
        )
        with patch.object(
            bri, "_clause_components", lambda b: [list(range(len(b)))]
        ), patch.object(bri, "_MAX_SUBSET_BUDGET", 50):
            flat = minimal_retractions(base)

        assert flat.cardinality == -1
        assert flat.refusal == "subset_budget"
        assert "component of 50 clauses" in flat.refusal_detail


class TestRefusalsNameTheirBound:
    """DoD item 4: no refusal is ever a bare -1."""

    def test_search_k_refusal_names_the_component(self, monkeypatch):
        from argumentation_analysis.agents.core.logic import (
            belief_revision_insight as bri,
        )

        monkeypatch.setattr(bri, "_MAX_SEARCH_K", 1)
        result = minimal_retractions([[1], [1], [-1], [-1]])

        assert (result.cardinality, result.options) == (-1, [])
        assert result.refusal == "search_k"
        assert "4 clauses" in result.refusal_detail
        shaped = shape_minimal_retraction(result, ["a", "b", "c", "d"])
        assert shaped["degraded"] is True
        assert shaped["refusal"] == "search_k"
        assert shaped["refusal_detail"] == result.refusal_detail

    def test_subset_budget_refusal_names_its_figures(self, monkeypatch):
        from argumentation_analysis.agents.core.logic import (
            belief_revision_insight as bri,
        )

        monkeypatch.setattr(bri, "_MAX_SUBSET_BUDGET", 0)
        result = minimal_retractions([[1], [-1]])

        assert result.cardinality == -1
        assert result.refusal == "subset_budget"
        assert "budget 0" in result.refusal_detail
        assert "k=1" in result.refusal_detail

    @pytest.mark.parametrize("refusal", ["search_k", "subset_budget"])
    def test_no_refusal_survives_without_its_name(self, monkeypatch, refusal):
        """The shaped entry of a refused search always names the bound and the
        measured reason — the bare -1 the issue opened on cannot come back."""
        from argumentation_analysis.agents.core.logic import (
            belief_revision_insight as bri,
        )

        if refusal == "search_k":
            monkeypatch.setattr(bri, "_MAX_SEARCH_K", 1)
            base: List[List[int]] = [[1], [1], [-1], [-1]]
        else:
            monkeypatch.setattr(bri, "_MAX_SUBSET_BUDGET", 0)
            base = [[1], [-1]]
        result = minimal_retractions(base)
        shaped: Optional[Dict[str, object]] = shape_minimal_retraction(
            result, [f"clause_{i}" for i in range(len(base))]
        )
        assert shaped is not None
        assert shaped["cardinality"] == -1
        assert shaped["degraded"] is True
        assert shaped["refusal"] == refusal
        assert shaped["refusal_detail"], "a refusal must carry its measured reason"
