# -*- coding: utf-8 -*-
"""#3560 follow-up — the contract's motif and reason state each count ONCE.

Measured on the recorded c11 and c12 panel archives: the motif rendered
« 1 1 mouvement absent du récit sur 8 » — the template prepended the count
before :func:`accord`, which already carries it. The same doubled shape sat
in ``check_render_contract``'s FAIL reason. This witness pins the exact
strings: one count, in the recorded vocabulary, nothing doubled. The count
LINE (``render_count_line``) never doubled — it is the positive control.
"""

import pytest

from argumentation_analysis.reporting.restitution.movement_render_contract import (
    RenderContractReading,
    check_render_contract,
    render_contract_motif,
    render_count_line,
)


def _reading(**kwargs) -> RenderContractReading:
    """A reading built directly — the string templates are the object here,
    not the measure that fills them."""
    base = dict(
        movements_total=8,
        movements_treated=7,
        untreated_movement_themes=("Tricherie",),
        items_total=15,
        items_treated=8,
        items_measured=False,
        stated_movement_drops=None,
        stated_item_drops=None,
    )
    base.update(kwargs)
    return RenderContractReading(**base)


class TestMotifStatesEachCountOnce:
    def test_singular_motif_exact(self):
        """The archived c11 motif, un-doubled — byte for byte. The
        unmeasured-items clause now carries the deterministic split
        (#3560 item 23b), with the reading's default reading all items
        on examined units."""
        motif = render_contract_motif(_reading())
        assert motif == (
            "Acte II : 1 mouvement absent du récit sur 8 remis sans compte "
            "exact du rédacteur ; 15 constats de couverture remis au "
            "rédacteur : 15 sur unités examinées, 0 sur unités non "
            "examinées, mesure non éprouvée sur ce canal — aucun compte "
            "énoncé (#3560)"
        )

    def test_singular_reason_exact(self):
        verdict = check_render_contract(_reading())
        assert verdict.band == "FAIL"
        assert verdict.reasons == [
            "1 mouvement absent du récit sur 8 remis, compte du rédacteur : "
            "aucun (#3560)"
        ]


class TestPluralAndStatedCount:
    def test_plural_motif_with_stated_count(self):
        """A WRONG stated count (the writer said 1, the measure reads 2) —
        the clause fires, and states the writer's number once, the measured
        number once."""
        motif = render_contract_motif(
            _reading(
                movements_total=3,
                movements_treated=1,
                stated_movement_drops=1,
            )
        )
        assert "2 2" not in motif
        assert motif.startswith(
            "Acte II : 2 mouvements absents du récit sur 3 remis sans compte "
            "exact du rédacteur, compte lu : 1"
        )

    def test_items_clause_when_measured(self):
        """The items clause, should the channel's measure ever be proven —
        one count there too."""
        motif = render_contract_motif(
            _reading(items_total=6, items_treated=4, items_measured=True)
        )
        assert "2 constats de couverture non repris sur 6" in motif
        assert "2 2" not in motif
        verdict = check_render_contract(
            _reading(items_total=6, items_treated=4, items_measured=True)
        )
        assert verdict.reasons[-1] == (
            "2 constats de couverture non repris sur 6, compte du rédacteur : "
            "aucun (#3560)"
        )


class TestCountLineNeverDoubled:
    def test_count_line_positive_control(self):
        """The producer's count line was never doubled — it must not move."""
        line = render_count_line(_reading())
        assert (
            line
            == "(Compte du récit : 8 mouvements remis au rédacteur, 7 traités ici.)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
