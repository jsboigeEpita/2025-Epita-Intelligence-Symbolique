"""BO-2 #1472 residual DoD: the democratech demo renders a FIRSTHAND verdict per
proposition, with a readable output — proven firsthand, not asserted.

The demo bundle (``examples/democratech_deliberation/``) runs the ``democratech``
workflow E2E over synthetic domain-public propositions and prints a per-prop
verdict. This test exercises the demo's own driver on 2 propositions to prove:
  - each proposition DECIDES firsthand (real agents, ``governance_decided_firsthand``);
  - the verdict is readable (winner + ≥1 voting method + consensus);
  - the table renderer does not crash on real output.

Privacy HARD: synthetic domain-public propositions only (no corpus). Marked
``requires_api``+``slow``: the workflow needs a real LLM per proposition.
"""

import os

import pytest


@pytest.fixture(autouse=True)
def _demo_on_path(monkeypatch):
    """Make the examples package importable so the driver's intra-package import resolves."""
    import pathlib

    demo_dir = pathlib.Path(__file__).resolve().parents[3] / "examples" / "democratech_deliberation"
    monkeypatch.syspath_prepend(str(demo_dir))
    yield


@pytest.mark.requires_api
@pytest.mark.slow
class TestDemocratechDemo:
    """DoD: demo renders a firsthand, readable verdict per proposition."""

    @pytest.mark.asyncio
    async def test_demo_renders_firsthand_verdict_per_prop(self):
        # Import after syspath_prepend.
        from run_democratech_demo import _print_table, run_demo

        # 2 propositions = enough to prove "per prop" while staying within the
        # slow timeout (~150s/prop live).
        results = await run_demo(limit=2)

        assert len(results) == 2, "demo should process the 2 requested propositions"

        for r in results:
            v = r["verdict"]
            assert v["decided_firsthand"] is True, (
                f"{r['id']} did not decide firsthand — demo must render a genuine "
                f"verdict (anti-théâtre #1019), not a fabricated one"
            )
            assert v["winner"] is not None, f"{r['id']}: no winner rendered"
            assert v["n_methods"] >= 1, f"{r['id']}: 0 voting methods decided"
            assert v["methods"], f"{r['id']}: empty winners_per_method"

        # The readable table renderer must not crash on real output.
        _print_table(results)

    def test_synthetic_propositions_are_domain_public(self):
        """Privacy HARD: fixtures contain no real-name / corpus markers."""
        from synthetic_proposals import SYNTHETIC_PROPOSITIONS

        forbidden = ("raw_text", "discours", "source_quote")  # corpus-field markers
        assert len(SYNTHETIC_PROPOSITIONS) >= 3, "demo needs ≥3 propositions"
        for pid, label, text in SYNTHETIC_PROPOSITIONS:
            assert pid.startswith("prop_"), f"non-opaque id: {pid}"
            low = (text or "").lower()
            for marker in forbidden:
                assert marker not in low, f"{pid}: forbidden marker {marker!r}"
