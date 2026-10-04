"""#2921 — the student Dung backend cannot cost 27 minutes in silence.

Measured cause (sparse synthetic AFs a0..aN-1, zero attacks, po-2025,
2026-10-04, per-semantics timings on fresh agents):

- the sanctuary's eager ``_compute_extensions_if_needed`` pays SEVEN
  semantics on the first getter call, of which this adapter consumes FOUR;
- ``SimpleIdealReasoner.getModel`` — internal 2^N subset enumeration,
  Java-side: 41.7 s at N=15, killed at the 420 s process cap at N=20 (the
  ~22-minute term of the issue's 27-minute run);
- ``SimpleAdmissibleReasoner.getModels`` — 2^N extensions materialized, then
  converted element-by-element through the JPype bridge
  (``_format_extensions``): 1 048 576 extensions at N=20, 362 s total
  (213 s Java + 149 s conversion); 32 768 / 4.3 s at N=15;
- the four CONSUMED semantics (grounded/preferred/stable/complete) measure
  ≤ 9.3 ms at every N in {5, 10, 15, 20} on sparse AFs.

BOUNDARY, measured the same day on the dense family (N/2 mutual pairs →
2^(N/2) preferred extensions, `_default_*_dung_backend` on a fresh process per
row): N=12 64 exts → tweety 0.6 s / student 1.6 s; N=16 256 → 2.3 / 2.8;
N=18 512 → 2.7 / 2.7; N=20 1024 → 78.2 / 46.7. At N=20 the dominant term is
`SimplePreferredReasoner` alone (34.5 s Java, internal 2^N enumeration) and
`complete` legitimately returns 59 049 = 3^10 extensions. The residual cost is
the framework's own combinatorics, paid by BOTH engines — the student is
faster than the native one here — so it is out of this adapter's reach and
tracked by #2930 (which also records why an in-thread `asyncio.wait_for`
ceiling would be a false fix).

The witnesses below pin the three DoD points: the eager compute must not
touch the three unconsumed reasoners (sentinel), ``attacks=None`` must fail
with the named error (not a bare ``TypeError``), and under the repair the
two real backends keep agreeing on the measurement AFs (the issue's table
measured ``overall_agreement=True`` pre-repair).

Synthetic opaque AFs only (privacy HARD — no corpus tokens).
"""

from __future__ import annotations

import asyncio
from typing import Any, List

import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    _compare_dung_backends,
)

# -- attacks=None: named precondition, never a bare TypeError ----------------


class TestAttacksNonePrecondition:
    async def test_none_raises_the_named_error(self):
        """A None attacks list is refused with the named error (#2921).

        ``None`` means the attacks were never materialized upstream — it is
        NOT "no attacks" (that would be ``[]``, a materially different AF
        where every argument is accepted). The comparator names the defect
        instead of crashing inside a backend on ``len(NoneType)``.
        """
        from argumentation_analysis.orchestration.invoke_callables import (
            DungAttacksNotMaterializedError,
        )

        with pytest.raises(DungAttacksNotMaterializedError) as excinfo:
            await _compare_dung_backends(["a0", "a1"], None)  # type: ignore[arg-type]
        assert "attacks" in str(excinfo.value)

    async def test_the_named_error_names_the_repair(self):
        """The message says what to derive upstream, not just that it failed."""
        from argumentation_analysis.orchestration.invoke_callables import (
            DungAttacksNotMaterializedError,
        )

        with pytest.raises(DungAttacksNotMaterializedError) as excinfo:
            await _compare_dung_backends(["a0"], None)  # type: ignore[arg-type]
        assert "_derive_dung_attacks" in str(excinfo.value)

    async def test_empty_attacks_is_still_a_valid_af(self):
        """Non-regression of the tri-state: [] is a real AF and runs."""
        from tests.unit.argumentation_analysis.orchestration.test_compare_dung_backends import (
            _backend,
        )

        r = await _compare_dung_backends(
            ["a0", "a1"],
            [],
            backends={
                "A": _backend({"grounded": [["a0", "a1"]]}),
                "B": _backend({"grounded": [["a0", "a1"]]}),
            },
        )
        # two agreeing backends decided — a real comparison, not the None
        # that a single-backend run contractually reports
        assert r["comparison"]["overall_agreement"] is True


# -- the repair: no unconsumed reasoner is paid ------------------------------


class _SentinelReasoner:
    """Raises on ANY use — an unconsumed reasoner must never be touched."""

    def __getattr__(self, name: str) -> Any:
        raise AssertionError(
            f"unconsumed reasoner touched: .{name}() — the eager 7-semantics "
            "compute is back (#2921)"
        )


class TestStudentBackendPaysOnlyWhatItConsumes:
    def test_no_unconsumed_reasoner_is_touched(self):
        """Sentinel witness (#2921): admissible/ideal/semi_stable stay untouched.

        Pre-repair, the first getter call runs the eager 7-semantics compute
        and touches every reasoner — the sentinel reddens. Post-repair, the
        adapter computes exactly the four semantics it consumes.
        """
        from argumentation_analysis.adapters.dung_student_provider import (
            DungStudentProvider,
        )

        provider = DungStudentProvider()
        agent = provider._get_agent()
        sentinel = _SentinelReasoner()
        agent.admissible_reasoner = sentinel  # type: ignore[assignment]
        agent.ideal_reasoner = sentinel  # type: ignore[assignment]
        agent.semi_stable_reasoner = sentinel  # type: ignore[assignment]

        result = asyncio.run(provider.compute_extensions(["a0", "a1", "a2"], []))
        stats = result.get("statistics", {})
        assert stats.get("semantics_computed") == 4
        all_ext = result.get("all_extensions", {})
        assert all_ext.keys() >= {"grounded", "preferred", "stable", "complete"}
        # the sentinel poison must not hide as a recorded per-semantics error
        # either — pre-repair the eager compute swallows it into
        # ``{"error": ...}`` entries and semantics_computed reads 0.
        assert all("error" not in v for v in all_ext.values()), all_ext

    def test_repaired_path_is_bounded_at_the_issues_scale(self):
        """N=20 (the issue's payload scale) completes in seconds, not minutes.

        Pre-repair this same call is the 27-minute run (1 635 080 ms measured
        once, real payload). The bound asserted is 30 s — two orders of
        magnitude under the blowup, loose enough not to flake (the four
        consumed semantics measure ≤ 9.3 ms each at N=20; JVM warmup on the
        first call stays well under the bound).
        """
        import time

        from argumentation_analysis.adapters.dung_student_provider import (
            DungStudentProvider,
        )

        provider = DungStudentProvider()
        args = [f"a{i}" for i in range(20)]
        t0 = time.perf_counter()
        result = asyncio.run(provider.compute_extensions(args, []))
        elapsed = time.perf_counter() - t0
        assert result.get("statistics", {}).get("semantics_computed") == 4
        assert elapsed < 30.0, (
            f"repaired student backend took {elapsed:.1f} s at N=20 — "
            "the eager-compute blowup is back (#2921)"
        )


# -- non-regression: the repair moves no verdict ------------------------------
#
# Pre-repair ground truth, measured on the ORIGINAL adapter (po-2025,
# 2026-10-04, stash-compare): sparse and chain AFs agree overall; the 3-cycle
# DISAGREES on preferred — tweety returns [[]] where the student's
# perfect-cycle correction returns the three singletons. That disagreement is
# a comparison RESULT (never auto-reconciled, #1430): the non-regression is
# that the repair leaves every one of these verdicts bit-for-bit where it
# was, not that it makes them agree.


class TestBiBackendAgreementUnderRepair:
    @pytest.mark.parametrize(
        "label,args,attacks,expected_agreement",
        [
            ("sparse20", [f"a{i}" for i in range(20)], [], True),
            ("chain2", ["a0", "a1"], [["a0", "a1"]], True),
            # pre-existing disagreement (tweety [[]] vs student singletons) —
            # the repair must not move it in either direction
            (
                "cycle3",
                ["a0", "a1", "a2"],
                [["a0", "a1"], ["a1", "a2"], ["a2", "a0"]],
                False,
            ),
        ],
    )
    def test_the_repair_moves_no_verdict(
        self,
        label: str,
        args: List[str],
        attacks: List[List[str]],
        expected_agreement: bool,
    ):
        r = asyncio.run(_compare_dung_backends(args, attacks))
        backends = r["backends"]
        assert backends["tweety"]["available"], backends["tweety"]["note"]
        assert backends["abs_arg_dung_student"]["available"], backends[
            "abs_arg_dung_student"
        ]["note"]
        assert r["comparison"]["overall_agreement"] is expected_agreement, r[
            "comparison"
        ]["per_semantics"]

    def test_the_cycle_disagreement_keeps_its_exact_shape(self):
        """The pinned pre-existing disagreement: tweety [[]] vs the student's
        three singletons on a perfect 3-cycle. If the repair moved either
        side — "fixing" the disagreement would be as much a regression as
        breaking the agreement — this witness reddens."""
        r = asyncio.run(
            _compare_dung_backends(
                ["a0", "a1", "a2"],
                [["a0", "a1"], ["a1", "a2"], ["a2", "a0"]],
            )
        )
        per = r["comparison"]["per_semantics"]["preferred"]
        assert per["agreement"] is False
        assert any("tweety" in d for d in per["disagreement"]), per
        student = r["backends"]["abs_arg_dung_student"]["extensions"]["preferred"]
        assert {frozenset(e) for e in student} == {
            frozenset({"a0"}),
            frozenset({"a1"}),
            frozenset({"a2"}),
        }, student
        tweety = r["backends"]["tweety"]["extensions"]["preferred"]
        assert tweety == [[]], tweety
