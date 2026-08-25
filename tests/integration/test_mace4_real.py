"""Real (non-mocked) Mace4 model-finder integration test — FP-19 #1243.

Mace4 is wired as a **selectable, comparable** FOL backend (mandate R468:
"tous les solvers handy … pour comparer les résultats"). It is the SOUND
CONSISTENT side of the comparison: it proves a KB consistent by exhibiting a
finite model, complementing the refutation provers (EProver/Prover9, which are
sound on the INCONSISTENT side).

This file runs the REAL vendored Mace4 binary (``libs/prover9/bin/mace4.exe``,
sibling of Prover9, sharing ``cygwin1.dll``) — NO mock of the binary, reasoner,
or settings — at two levels:

1. **Runner level** (``run_mace4`` + ``interpret_mace4_output``, no JVM): the
   firsthand verdict contract — a satisfiable KB yields a model (CONSISTENT);
   a ground contradiction exhausts the bounded search (no finite model).
2. **Production path** (``settings.solver = MACE4`` → ``TweetyBridge.
   check_consistency(bs, "first_order")`` → ``FOLHandler`` → Mace4 subprocess):
   the same KB decided end-to-end through the real pipeline.

Anti-théâtre contract (#1019): where the binary is present the test must
EXECUTE it — it must NOT be "green by skipping everywhere". A ground
contradiction must NEVER be reported consistent (the fabrication #1019 forbids);
an honest degraded outcome is ``None``, never a fabricated ``True``.

Two firsthand facts (po-2025, 2026-06-23, synthetic atoms) that shape the
contract under test:
* an UNBOUNDED Mace4 search hangs forever on an inconsistent KB — so the runner
  must be bounded + hard-timeout (verified: ``{P(a),-P(a)}`` climbs domain sizes
  660, 661, … without terminating);
* bounded, it terminates cleanly: ``{P(a)}`` → model (consistent),
  ``{P(a),-P(a)}`` → exhausted (no finite model ≤ bound).

Privacy HARD: synthetic atoms only (``P(a)``, ``Mortal(socrate)``), 0 corpus.
"""

import pytest

from argumentation_analysis.core import mace4_runner
from argumentation_analysis.core.mace4_runner import (
    interpret_mace4_output,
    run_mace4,
)


def _mace4_binary_present() -> bool:
    """True iff the vendored Mace4 binary is on disk."""
    return mace4_runner.MACE4_EXECUTABLE.is_file()


# Skip cleanly where the binary is absent — the model-finder cannot run there.
pytestmark = pytest.mark.skipif(
    not _mace4_binary_present(),
    reason="Mace4 binary not present at libs/prover9/bin/mace4.exe — cannot run "
    "this real model-finder integration test.",
)


# --------------------------------------------------------------------------- #
# Runner level — the firsthand verdict contract (no JVM needed).
# --------------------------------------------------------------------------- #
class TestMace4RunnerContract:
    def test_satisfiable_kb_yields_model_consistent(self):
        """A satisfiable KB ``{P(a)}`` must yield a finite MODEL ⇒ CONSISTENT
        (``True``). This is Mace4's SOUND direction — a model is a witness."""
        out = run_mace4("formulas(assumptions).\nP(a).\nend_of_list.\n")
        verdict, note = interpret_mace4_output(out)
        assert verdict is True, (
            f"satisfiable {{P(a)}} must yield a model (consistent); got "
            f"({verdict!r}, {note!r}). Raw tail:\n{out[-300:]!r}"
        )

    def test_ground_contradiction_exhausts_inconsistent(self):
        """A ground contradiction ``{P(a), -P(a)}`` has no model at any domain
        size — the bounded search must report ``exhausted`` ⇒ ``False``. The note
        makes the epistemic status explicit (bounded model search, NOT a
        refutation proof)."""
        out = run_mace4("formulas(assumptions).\nP(a).\n-P(a).\nend_of_list.\n")
        verdict, note = interpret_mace4_output(out)
        assert verdict is False, (
            f"ground contradiction {{P(a),-P(a)}} must exhaust (no finite model); "
            f"got ({verdict!r}, {note!r}). Raw tail:\n{out[-300:]!r}"
        )
        # The honest-labelling invariant: an exhausted verdict must NOT be sold as
        # a refutation proof — it is "no model up to the domain bound".
        assert "refutation proof" in note.lower(), (
            f"exhausted note must disclose it is a bounded model search, not a "
            f"refutation proof; got {note!r}."
        )

    def test_bounded_search_terminates_fast(self):
        """Regression teeth for the firsthand UNBOUNDED-hang finding: a bounded
        run on an inconsistent KB must TERMINATE (not hang). If a future change
        drops the ``-N`` bound, ``run_mace4`` would hang and its hard timeout
        would raise ``RuntimeError`` — either way this test stops being a silent
        green (#1019/#1240 in the Mace4 dimension)."""
        # A direct ground contradiction exhausts at tiny domain sizes — well under
        # the default timeout. Reaching this assertion at all proves termination.
        out = run_mace4(
            "formulas(assumptions).\nP(a).\n-P(a).\nend_of_list.\n", max_domain=4
        )
        verdict, _ = interpret_mace4_output(out)
        assert verdict is False


# --------------------------------------------------------------------------- #
# Production path — settings.solver = MACE4 through the real bridge (needs JVM).
# --------------------------------------------------------------------------- #
@pytest.fixture
def mace4_solver():
    """Force ``settings.solver = MACE4`` for the test, then restore. A REAL
    runtime config change (not a mock of ``settings``): the Mace4 binary and the
    Tweety JVM (for belief-set parsing) both execute for real."""
    from argumentation_analysis.core.config import settings, SolverChoice

    previous = settings.solver
    settings.solver = SolverChoice.MACE4
    try:
        yield
    finally:
        settings.solver = previous


@pytest.fixture(scope="module")
def fol_bridge():
    """Start the JVM (idempotent) and build a ``TweetyBridge`` once."""
    from argumentation_analysis.core.jvm_setup import initialize_jvm, is_jvm_started
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

    initialize_jvm()
    if not is_jvm_started():
        pytest.skip("JVM not started — cannot parse FOL belief sets for Mace4.")
    return TweetyBridge()


class TestRealMace4ProductionPath:
    def test_consistent_kb_decides_consistent_via_mace4(self, fol_bridge, mace4_solver):
        """A consistent ground FOL KB must yield ``is_consistent = True`` via the
        REAL Mace4 binary, traceable to Mace4 (so the verdict is a real decision,
        not a degraded fallback)."""
        consistent_kb = (
            "human = {socrate}\n" "type(Mortal(human))\n" "\n" "Mortal(socrate)\n"
        )
        verdict, msg = fol_bridge.check_consistency(consistent_kb, "first_order")
        assert verdict is True, (
            f"consistent KB must decide consistent via Mace4; got "
            f"({verdict!r}, {msg!r})."
        )
        assert (
            "Mace4" in msg
        ), f"verdict must be traceable to the Mace4 model-finder; got msg={msg!r}."

    def test_contradiction_never_fabricated_consistent_via_mace4(
        self, fol_bridge, mace4_solver
    ):
        """A ground contradiction must NEVER be reported consistent via Mace4.
        Honest outcomes: inconsistent (``False``, bounded exhaustion) or
        fail-loud (``None``). A fabricated ``True`` is the #1019 failure."""
        inconsistent_kb = (
            "human = {socrate}\n"
            "type(Mortal(human))\n"
            "\n"
            "Mortal(socrate)\n"
            "!Mortal(socrate)\n"
        )
        verdict, msg = fol_bridge.check_consistency(inconsistent_kb, "first_order")
        assert verdict in (False, None), (
            f"contradiction reported CONSISTENT (verdict={verdict!r}) via Mace4 — "
            f"a fabricated verdict (#1019). Honest: inconsistent (False) or "
            f"fail-loud (None). msg={msg!r}"
        )


# --------------------------------------------------------------------------- #
# Comparison surface — compare_fol_backends cross-validates all backends.
# --------------------------------------------------------------------------- #
class TestFolBackendComparison:
    def test_compare_surfaces_all_backends_and_agreement(self, fol_bridge):
        """``compare_fol_backends`` (mandate R468) must run EVERY backend on the
        same KB and report a structured comparison: per-backend verdict + timing,
        a ``decided`` map, and an ``agreement`` flag. On a clearly-consistent KB,
        the backends that genuinely decide must AGREE on consistent — and any
        disagreement is surfaced explicitly, never silently reconciled (#1019)."""
        import asyncio

        consistent_kb = (
            "human = {socrate}\n"
            "type(Mortal(human))\n"
            "type(Human(human))\n"
            "\n"
            "Human(socrate)\n"
            "Mortal(socrate)\n"
        )
        result = asyncio.new_event_loop().run_until_complete(
            fol_bridge.compare_fol_backends(consistent_kb)
        )
        # Structure: all four backends are represented, each with a verdict slot
        # and a measured elapsed_ms (timing is part of the comparison value).
        backends = result["backends"]
        assert set(backends) == {
            "tweety",
            "eprover",
            "prover9",
            "mace4",
        }, f"comparison must cover every FOL backend; got {sorted(backends)}."
        for name, info in backends.items():
            assert (
                "verdict" in info and "elapsed_ms" in info
            ), f"backend {name!r} missing verdict/timing: {info!r}."

        # At least one backend must have actually DECIDED (otherwise the whole
        # comparison is degraded — that would be a no-op, not a cross-validation).
        decided = result["decided"]
        assert decided, (
            f"no FOL backend decided the consistent KB — comparison is fully "
            f"degraded: {backends!r}."
        )
        # Every backend that decided this clearly-consistent KB must say consistent
        # (True). Mace4 finds a model; EProver/Prover9/Tweety find no contradiction.
        assert all(v is True for v in decided.values()), (
            f"a backend reported the clearly-consistent KB inconsistent: "
            f"{decided!r} — investigate before trusting the comparison."
        )
        # With ≥2 deciders agreeing, the agreement flag must be True and there is
        # no disagreement to surface.
        if len(decided) >= 2:
            assert result["agreement"] is True, (
                f"≥2 backends agree consistent but agreement={result['agreement']!r}; "
                f"disagreement={result['disagreement']!r}."
            )
            assert result["disagreement"] == [], (
                f"backends agree yet a disagreement was surfaced: "
                f"{result['disagreement']!r}."
            )
