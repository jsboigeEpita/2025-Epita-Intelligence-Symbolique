# tests/unit/abs_arg_dung/test_aif_adapter.py
"""Unit tests for the AIF → Dung adapter.

These tests cover:

1. Pure projection (``aif_attacks_to_dung_af``):
   - the Nixon Diamond via AIF relations
   - the AIF "all-three-kinds" mixed attack pattern
   - duplicate-attack de-duplication
   - implicit-argument auto-registration (mirrors ICCMA parser)
   - unknown-kind rejection
   - self-attack preservation (anti-#1019: silent drops forbidden)

2. Backend verification (``verify_aif_to_dung``):
   - the projection is reachable through ``verify_aif_to_dung``
   - the pure-Python backend always runs and reports an ``available=True``
     ``backend_python`` slot
   - the Tweety backend is either available (and agrees) or honestly
     degraded (no fabricated verdict)
   - disagreements are reported verbatim, never reconciled (I5 / #1502)
"""

from __future__ import annotations

import pytest

from abs_arg_dung.aif_adapter import (
    AIF_KIND_REBUT,
    AIF_KIND_UNDERCUT,
    AIF_KIND_UNDERMINE,
    AIFAttack,
    aif_attacks_to_dung_af,
    verify_aif_to_dung,
)


# ---------------------------------------------------------------------------
# Pure projection
# ---------------------------------------------------------------------------


def test_nixon_diamond_via_aif_undermines() -> None:
    """A→B→C→A (each via undermine) is the canonical AIF reduction of
    the Nixon Diamond. The projection must produce the three-edge
    cycle and recover the same grounded extension the Dung backend
    would deliver on the flat framework."""
    args = ["arg_A", "arg_B", "arg_C"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_A", AIF_KIND_UNDERMINE),
    ]
    proj_args, proj_atts = aif_attacks_to_dung_af(args, attacks)
    assert proj_args == ["arg_A", "arg_B", "arg_C"]
    assert proj_atts == [
        ("arg_A", "arg_B"),
        ("arg_B", "arg_C"),
        ("arg_C", "arg_A"),
    ]


def test_mixed_aif_kinds_collapse_to_binary() -> None:
    """The three AIF kinds must collapse to the same flat edge in Dung.

    The information loss is structural — the projection preserves the
    *fact* of attack but not the *kind*. Verifies that mixing kinds
    targeting the same pair does not produce duplicate Dung edges.
    """
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERCUT),
    ]
    _, proj_atts = aif_attacks_to_dung_af(["arg_A", "arg_B"], attacks)
    assert proj_atts == [("arg_A", "arg_B")]


def test_duplicate_aif_attacks_dedup() -> None:
    """Two identical AIF attacks must not produce two Dung edges."""
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
    ]
    _, proj_atts = aif_attacks_to_dung_af(["arg_A", "arg_B"], attacks)
    assert proj_atts == [("arg_A", "arg_B")]


def test_implicit_argument_autoregistered() -> None:
    """Arguments appearing only in attack edges must be auto-registered
    (mirrors the ICCMA parser behaviour)."""
    _, proj_atts = aif_attacks_to_dung_af(
        ["arg_A"],
        [AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT)],
    )
    assert proj_atts == [("arg_A", "arg_B")]


def test_unknown_aif_kind_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown AIF attack kind"):
        aif_attacks_to_dung_af(
            ["arg_A", "arg_B"],
            [AIFAttack("arg_A", "arg_B", "doxelclash")],
        )


def test_self_attack_preserved() -> None:
    """Self-attacks are semantically meaningful in Dung (an argument
    that attacks itself is in no admissible set). They must NOT be
    silently dropped — silent drops are a classic anti-#1019 trap."""
    attacks = [AIFAttack("arg_A", "arg_A", AIF_KIND_REBUT)]
    _, proj_atts = aif_attacks_to_dung_af(["arg_A"], attacks)
    assert proj_atts == [("arg_A", "arg_A")]


# ---------------------------------------------------------------------------
# Backend verification
# ---------------------------------------------------------------------------


def test_verify_aif_to_dung_nixon_returns_python_report() -> None:
    """``verify_aif_to_dung`` must run the pure-Python backend and
    expose its report. The Tweety slot is either populated (and agrees)
    or empty (honest degradation). Never a fabricated verdict."""
    args = ["arg_A", "arg_B", "arg_C"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_UNDERMINE),
        AIFAttack("arg_B", "arg_C", AIF_KIND_UNDERMINE),
        AIFAttack("arg_C", "arg_A", AIF_KIND_UNDERMINE),
    ]
    summary = verify_aif_to_dung(args, attacks)

    py = summary["backend_python"]
    assert py["backend"] == "python"
    assert py["available"] is True
    assert "grounded" in py["extensions"]

    # Grounded extension of the Nixon Diamond is empty (mutual attack
    # cycle, no argument is acceptable). Cross-check with the documented
    # Dung semantics.
    assert py["extensions"]["grounded"] == [[]]

    # ``agree`` is either True (Tweety ran + agreed) or None (Tweety
    # unavailable / JVM not initialised). It must NEVER be False-with-fake
    # agreement: if Tweety is unavailable the comparison is indeterminate.
    assert summary["agree"] in (True, None)
    if summary["agree"] is True:
        assert summary["disagreements"] == []


def test_verify_aif_to_dung_empty_attack_set() -> None:
    """Empty AIF attack list with two isolated arguments: every argument
    is acceptable, grounded = full set."""
    args = ["arg_A", "arg_B"]
    summary = verify_aif_to_dung(args, [])

    py = summary["backend_python"]
    assert sorted(py["extensions"]["grounded"][0]) == ["arg_A", "arg_B"]


def test_verify_aif_to_dung_reports_disagreements_verbatim() -> None:
    """If the two backends ever disagree, the disagreement strings
    must be returned to the caller — never silently reconciled.
    I5 / #1502 invariant."""
    args = ["arg_A", "arg_B", "arg_C", "arg_D"]
    attacks = [
        AIFAttack("arg_A", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_C", "arg_B", AIF_KIND_REBUT),
        AIFAttack("arg_D", "arg_A", AIF_KIND_REBUT),
    ]
    summary = verify_aif_to_dung(args, attacks)
    # ``disagreements`` is always a list — empty if they agree, populated
    # if they diverge.
    assert isinstance(summary["disagreements"], list)
    if summary["agree"] is False:
        # Disagreements must surface a human-readable hint per divergent
        # semantic.
        assert len(summary["disagreements"]) >= 1
        for d in summary["disagreements"]:
            assert ":" in d
            assert "python=" in d and "tweety=" in d