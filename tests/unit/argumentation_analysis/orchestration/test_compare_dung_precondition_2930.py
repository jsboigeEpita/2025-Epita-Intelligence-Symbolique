"""#2930 — the provable-blow-up ceiling on the Dung backend comparison.

The residual #2921 left open: on an AF whose preferred-extension count provably
explodes, BOTH engines cost minutes (measured 2026-10-04, po-2025: 1024
preferred extensions -> 46.7 s student / 78.2 s tweety at N=20) and nothing
stopped them, in silence. The ceiling refuses BEFORE any engine runs, from the
AF's shape alone, and names itself in the comparison report.

Every backend below is an injected sentinel: the witnesses measure the guard,
not the engines, so no JVM is needed and the suite stays fast.
"""

import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    _DUNG_PROVABLE_EXTENSION_CEILING,
    _compare_dung_backends,
    _provable_preferred_extension_floor,
)


def mutual_pairs(pairs: int):
    """``pairs`` disjoint mutual pairs: exactly 2**pairs preferred extensions."""
    arguments = []
    attacks = []
    for i in range(pairs):
        a, b = f"a{2 * i}", f"a{2 * i + 1}"
        arguments += [a, b]
        attacks += [[a, b], [b, a]]
    return arguments, attacks


class Sentinel:
    """A backend that records every call it receives."""

    def __init__(self, name: str = "sentinel"):
        self.name = name
        self.calls = []

    async def __call__(self, arguments, attacks):
        self.calls.append((list(arguments), [list(a) for a in attacks]))
        return {
            "extensions": {"preferred": [[arguments[0]]]},
            "available": True,
            "note": "sentinel",
            "elapsed_ms": 1.0,
        }


class TestProvablePreferredFloor:
    def test_p_disjoint_mutual_pairs_prove_two_to_the_p(self):
        for pairs in (1, 3, 9, 10):
            args, attacks = mutual_pairs(pairs)
            assert _provable_preferred_extension_floor(args, attacks) == 2**pairs

    def test_a_single_directed_attack_proves_one(self):
        assert _provable_preferred_extension_floor(["a", "b"], [["a", "b"]]) == 1

    def test_a_complete_graph_is_one_component_and_proves_one(self):
        args = ["a", "b", "c", "d"]
        attacks = [[x, y] for x in args for y in args if x != y]
        assert _provable_preferred_extension_floor(args, attacks) == 1

    def test_a_three_cycle_proves_one(self):
        args = ["a", "b", "c"]
        attacks = [["a", "b"], ["b", "c"], ["c", "a"]]
        assert _provable_preferred_extension_floor(args, attacks) == 1

    def test_a_mutual_pair_beside_an_isolated_argument_proves_two(self):
        assert (
            _provable_preferred_extension_floor(
                ["a", "b", "c"], [["a", "b"], ["b", "a"]]
            )
            == 2
        )

    def test_self_loops_short_attacks_and_unknown_names_prove_nothing(self):
        args = ["a", "b"]
        attacks = [["a", "a"], ["a", "ghost"], ["a"], ["b", "b"]]
        assert _provable_preferred_extension_floor(args, attacks) == 1

    def test_the_shift_is_capped_so_a_pathological_input_stays_finite(self):
        args, attacks = mutual_pairs(100)
        assert _provable_preferred_extension_floor(args, attacks) == 1 << 62


class TestCeilingRefusesBeforePaying:
    @pytest.mark.asyncio
    async def test_a_provable_blow_up_never_reaches_a_backend(self):
        args, attacks = mutual_pairs(10)  # proves 1024 = the ceiling
        sentinels = {"tweety": Sentinel("tweety"), "student": Sentinel("student")}

        result = await _compare_dung_backends(args, attacks, backends=sentinels)

        assert sentinels["tweety"].calls == []
        assert sentinels["student"].calls == []
        for name in ("tweety", "student"):
            backend = result["backends"][name]
            assert backend["available"] is False
            assert "refused before running (#2930)" in backend["note"]
            assert str(_DUNG_PROVABLE_EXTENSION_CEILING) in backend["note"]
            assert backend["elapsed_ms"] == 0.0

    @pytest.mark.asyncio
    async def test_the_refusal_is_reported_not_silently_empty(self):
        args, attacks = mutual_pairs(10)
        sentinels = {"tweety": Sentinel("tweety"), "student": Sentinel("student")}

        result = await _compare_dung_backends(args, attacks, backends=sentinels)

        assert result["comparison"]["overall_agreement"] is None
        for sem in result["comparison"]["semantics"]:
            assert result["comparison"]["per_semantics"][sem]["agreement"] is None
            assert result["comparison"]["per_semantics"][sem]["decided"] == []
        stats = result["statistics"]
        assert stats["provable_preferred_floor"] == _DUNG_PROVABLE_EXTENSION_CEILING
        assert stats["precondition_refused"] is True
        assert stats["arguments_count"] == 20

    @pytest.mark.asyncio
    async def test_the_ceiling_is_what_refused_not_the_shape(self):
        """The born-red pair: same AF, guard removed -> the engines ARE called."""
        args, attacks = mutual_pairs(10)
        sentinels = {"tweety": Sentinel("tweety"), "student": Sentinel("student")}

        await _compare_dung_backends(
            args,
            attacks,
            backends=sentinels,
            max_provable_preferred_extensions=None,
        )

        assert len(sentinels["tweety"].calls) == 1
        assert len(sentinels["student"].calls) == 1


class TestNoFalseRefusalOnRealLoadShapes:
    @pytest.mark.asyncio
    async def test_a_sparse_framework_of_fifty_arguments_is_not_refused(self):
        """Creux N=50 measured ~1.2 s: a round N ceiling would refuse it for nothing."""
        args = [f"a{i}" for i in range(50)]
        sentinel = Sentinel()

        result = await _compare_dung_backends(args, [], backends={"only": sentinel})

        assert len(sentinel.calls) == 1
        assert result["backends"]["only"]["available"] is True
        assert result["statistics"]["precondition_refused"] is False

    @pytest.mark.asyncio
    async def test_the_measured_two_point_seven_second_case_is_left_to_run(self):
        """512 preferred extensions (p=9) measured 2.7 s — deliberately under the ceiling."""
        args, attacks = mutual_pairs(9)
        sentinel = Sentinel()

        result = await _compare_dung_backends(
            args, attacks, backends={"only": sentinel}
        )

        assert len(sentinel.calls) == 1
        assert result["statistics"]["provable_preferred_floor"] == 512
        assert result["statistics"]["precondition_refused"] is False

    @pytest.mark.asyncio
    async def test_two_agreeing_backends_still_agree(self):
        args = ["a", "b", "c"]
        attacks = [["a", "b"], ["b", "c"], ["c", "a"]]

        result = await _compare_dung_backends(
            args, attacks, backends={"x": Sentinel("x"), "y": Sentinel("y")}
        )

        assert result["comparison"]["overall_agreement"] is True
        assert result["backends"]["x"]["available"] is True
        assert result["backends"]["y"]["available"] is True
        assert result["statistics"]["precondition_refused"] is False
