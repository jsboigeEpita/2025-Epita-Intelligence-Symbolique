"""#3050 follow-up — the sized enumeration is wired through the CALLABLE.

The #3050 witnesses enter at ``AFHandler.analyze_multi_semantics``; the
coordinator's review on PR #3055 named the gap and this file closes it: one
test through ``_invoke_dung_extensions`` itself — scripted attack derivation
(the offline fixture), REAL JVM, real enrichment and passthrough.

On the 17-node attack chain, ``preferred`` must return ONE extension of 9
ids through the G ∪ G⁺ reduction: #3055's flat component cap refused this
exact frame (the measured cliff — base `f385fa662` solved it instantly with
the same single extension), and the wiring must carry the repair, not just
the handler. ``conflict_free`` keeps the flat cap on the same frame: its
named refusal must travel WHOLE through the callable's passthrough.
"""

from __future__ import annotations

import asyncio

import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_dung_extensions,
)

pytestmark = [
    pytest.mark.jpype,
    pytest.mark.tweety,
    pytest.mark.usefixtures("dung_attacks_offline"),
]


class TestDungExtensionsSizedWiring:
    @pytest.mark.timeout(120)
    def test_chain_17_preferred_through_the_callable(self, dung_attacks_offline):
        labels = [f"claim {i}" for i in range(1, 18)]
        edges = [[labels[i], labels[i + 1]] for i in range(16)]
        dung_attacks_offline.return_value = edges

        result = asyncio.run(
            _invoke_dung_extensions("synthetic corpus", {"arguments": labels})
        )

        # The reduction verdict, at the wiring level: ONE preferred extension
        # holding the 9 odd-position unit ids — not a refusal.
        preferred = result["all_extensions"]["preferred"]
        assert isinstance(preferred, dict), preferred
        assert "refused" not in preferred, preferred
        assert preferred["count"] == 1
        extension = preferred["extensions"][0]
        assert len(extension) == 9
        assert all(a.startswith("arg_") for a in extension)

        # The same frame's conflict_free keeps the flat cap, and the refusal
        # dict travels whole (named, sized, #3050) — never flattened.
        conflict = result["all_extensions"]["conflict_free"]
        assert isinstance(conflict, dict) and conflict.get("refused") is True
        assert conflict["largest_component_nodes"] == 17
        assert "17 nodes" in conflict["error"]

        # Primary is the enriched preferred block, never the refusal.
        assert result["extensions"]["count"] == 1
        # The caller seam minted 17 nodes and the derived edges all resolved.
        assert result["statistics"]["arguments_count"] == 17
