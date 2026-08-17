"""#1777 — l'axe FOL/modal de KBToTweetyPlugin rend un verdict calculé, et une
étiquette inconnue rend « non évalué » (tri-état #1634), jamais un verdict.

Red control (DoD item 2, on main at branch time, JVM up): the validators pass
labels the bridge does not route (``"fol"`` vs ``"first_order"``, ``"modal_k"``
vs naked codes ``K/T/S4/S5``), so every call lands in the bridge's else-branch
-> ``(None, "Unknown logic type: …")`` -> 3 retries -> ``is_valid: false`` on a
well-formed formula. An unknown ``logic_type`` additionally renders
``is_valid: true`` from the else-branch of ``_translate_with_retry`` without
any computation (the #1773 form surviving in the very file of the fix).

This module requires the real JVM session (like the #1774 vocabulary tests):
the JVM-free suite cannot reach this path, which is precisely why the defect
survived.
"""

import json

import pytest

from argumentation_analysis.plugins.kb_to_tweety_plugin import (
    KBToTweetyPlugin,
    _validate_fol,
    _validate_modal,
)

pytestmark = pytest.mark.tweety


class TestFolModalRoutingRendersComputedVerdict:
    """DoD item 2 + semantic decision: a well-formed FOL/modal formula parses.

    ``is_valid`` measures parseability into Tweety (uniform with ``_validate_pl``),
    not consistency — a well-formed contradictory formula is valid syntax.
    """

    async def test_validate_fol_parses_valid_formula(
        self, tweety_bridge_fixture
    ) -> None:
        is_valid, msg = _validate_fol("forall X: (Human(X) => Mortal(X))")
        assert is_valid is True, f"well-formed FOL rejected: {msg}"
        assert "Unknown logic type" not in msg

    async def test_validate_modal_parses_valid_formula(
        self, tweety_bridge_fixture
    ) -> None:
        is_valid, msg = _validate_modal("[](p => q)")
        assert is_valid is True, f"well-formed modal rejected: {msg}"
        assert "Unknown logic type" not in msg

    async def test_translate_fol_renders_computed_verdict(
        self, tweety_bridge_fixture
    ) -> None:
        plugin = KBToTweetyPlugin()
        result = json.loads(
            await plugin.translate_to_tweety(
                json.dumps({"text": "Socrate est mortel", "logic_type": "fol"})
            )
        )
        assert result["is_valid"] is True, result["validation_message"]
        assert "Unknown logic type" not in result["validation_message"]
        assert result["attempts"] == 1

    async def test_well_formed_contradiction_is_valid_parses(
        self, tweety_bridge_fixture
    ) -> None:
        """``p && !p`` is well-formed: validity is not consistency, no retries."""
        is_valid, msg = _validate_fol("forall X: (Human(X) => !Mortal(X))")
        assert is_valid is True, f"well-formed contradictory FOL rejected: {msg}"


class TestUnknownLogicTypeIsNotEvaluated:
    """Constat B (DoD item 3): an unknown label is not valid and not invalid —
    it was never evaluated (tri-state #1634), and the message names it.
    """

    async def test_unknown_logic_type_is_null_not_true(
        self, tweety_bridge_fixture
    ) -> None:
        plugin = KBToTweetyPlugin()
        result = json.loads(
            await plugin.translate_to_tweety(
                json.dumps({"text": "Socrate est mortel", "logic_type": "zzz"})
            )
        )
        assert result["is_valid"] is None, result["validation_message"]
        assert "zzz" in result["validation_message"]
        assert "heuristic" not in result["validation_message"]
