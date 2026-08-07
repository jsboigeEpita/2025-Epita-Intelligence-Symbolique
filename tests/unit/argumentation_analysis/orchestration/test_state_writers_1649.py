"""#1649 — Regression tests pinning the ASPIC+ writer must carry ``attacks``.

ASPIC+ is the unique singular contribution of the structured-argumentation
axes (#1649): its attacks carry a **scope** (undercut / rebut / undermine /
unresolved) that Dung has no equivalent for. Pre-fix the handler at
``aspic_handler.analyze_aspic_framework`` (post-#1679) emits the qualified
list — but the writer ``_write_aspic_to_state`` threw it away, so the state
saw ``aspic_results[0]["attacks"] = []`` and the axis projected as a Dung
copy. A reader aggregating attacks saw zero ASPIC+ arbitration even when the
handler had qualified several.

Anti-#1019 discipline (R761 #1643, R764 #1636, R765 #1662, R767 #1648): the
writer is real, the handler is stubbed. A mocked writer would just agree
with itself.

Privacy: synthetic atoms only (no corpus tokens).
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_aspic_to_state,
)


def _new_state() -> UnifiedAnalysisState:
    """A fresh state for a single writer probe."""
    return UnifiedAnalysisState("aspic-writer-1649 synthetic probe")


def _stub_post1679_output() -> Dict[str, Any]:
    """Mirror of ``ASPICHandler.analyze_aspic_framework`` after #1679/#1649.

    Carries the qualified attacks list — three scopes coexisting in one
    framework, plus the matching statistics. Synthetic atoms only.
    """
    return {
        "reasoner_type": "simple",
        "extensions": [["a"], ["b"]],
        "attacks": [
            {
                "attacker_rule": "r_neg_main",
                "attacker_premises": ["p", "q"],
                "target": "r_main",
                "scope": "undercut",
            },
            {
                "attacker_rule": "r_neg_main",
                "attacker_premises": ["p", "q"],
                "target": "concl_x",
                "scope": "rebut",
            },
            {
                "attacker_rule": "r_neg_main",
                "attacker_premises": ["p", "q"],
                "target": "p",
                "scope": "undermine",
            },
        ],
        "statistics": {
            "strict_rules_count": 1,
            "defeasible_rules_count": 1,
            "axioms_count": 2,
            "extensions_count": 2,
            "attacks_count": 3,
            "dung_attacks_count": 3,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# TestAspicWriterCarriesAttacks1649 — the writer must surface attacks
# ─────────────────────────────────────────────────────────────────────────────


class TestAspicWriterCarriesAttacks1649:
    """ASPIC+ writer must surface the qualified attacks list post-#1679."""

    def test_writer_surfaces_attacks_top_level(self) -> None:
        """The qualified attacks list survives ``_write_aspic_to_state``.

        Pre-fix the writer dropped ``output["attacks"]`` on the floor; the
        entry was persisted with no ``attacks`` field at all. Post-fix
        ``entry["attacks"]`` mirrors the handler's qualified list, top-level.
        """
        state = _new_state()
        output = _stub_post1679_output()
        _write_aspic_to_state(output, state, {})

        assert len(state.aspic_results) == 1
        entry = state.aspic_results[0]
        assert "attacks" in entry, (
            "writer dropped the qualified attacks list — #1649 loss: "
            "ASPIC+ projected as a Dung copy with no arbitration signal"
        )
        assert isinstance(entry["attacks"], list)
        assert len(entry["attacks"]) == 3, (
            f"expected 3 qualified attacks (undercut/rebut/undermine), "
            f"got {len(entry['attacks'])}: {entry['attacks']!r}"
        )

    def test_writer_preserves_attack_shape_and_scope(self) -> None:
        """Each attack keeps ``scope`` (the singular contribution of ASPIC+)."""
        state = _new_state()
        _write_aspic_to_state(_stub_post1679_output(), state, {})

        attacks = state.aspic_results[0]["attacks"]
        scopes = sorted(a["scope"] for a in attacks)
        assert scopes == ["rebut", "undercut", "undermine"], (
            f"expected undercut+rebut+undermine, got {scopes}"
        )
        for attack in attacks:
            assert set(attack.keys()) >= {
                "attacker_rule",
                "attacker_premises",
                "target",
                "scope",
            }, f"attack missing required key: {attack!r}"
            assert isinstance(attack["attacker_premises"], list)

    def test_writer_attacks_empty_when_handler_returns_no_attacks(self) -> None:
        """When the handler produced no Dung edges, ``attacks`` is ``[]``,
        not ``None`` (so downstream readers never see the distinction)."""
        state = _new_state()
        output = _stub_post1679_output()
        output["attacks"] = []
        output["statistics"]["attacks_count"] = 0
        output["statistics"]["dung_attacks_count"] = 0
        _write_aspic_to_state(output, state, {})

        entry = state.aspic_results[0]
        assert entry["attacks"] == []
        assert "attacks" in entry, (
            "writer must serialize an empty attacks list as a present key"
        )

    def test_writer_ignores_non_list_attacks(self) -> None:
        """Defensive: a malformed ``attacks`` (e.g. a string) is normalized
        to ``None`` so the entry serializes ``[]`` rather than crashing."""
        state = _new_state()
        output = _stub_post1679_output()
        output["attacks"] = "not-a-list"
        _write_aspic_to_state(output, state, {})

        assert state.aspic_results[0]["attacks"] == []


# ─────────────────────────────────────────────────────────────────────────────
# TestAspicWriterBackwardsCompat1649 — the 3-arg signature stays alive
# ─────────────────────────────────────────────────────────────────────────────


class TestAspicWriterBackwardsCompat1649:
    """``add_aspic_result(reasoner, ext, stats)`` must keep working."""

    def test_add_aspic_result_3arg_unchanged(self) -> None:
        """The 3-arg form (no ``attacks``) keeps the legacy contract."""
        state = _new_state()
        aid = state.add_aspic_result("grounded", ["ext1"], {"time_ms": 42})
        assert aid.startswith("aspic_")
        entry = state.aspic_results[0]
        assert entry["reasoner_type"] == "grounded"
        assert entry["statistics"]["time_ms"] == 42
        # The new field defaults to ``[]`` (serialized None), not missing:
        assert entry["attacks"] == []
        assert "attacks" in entry