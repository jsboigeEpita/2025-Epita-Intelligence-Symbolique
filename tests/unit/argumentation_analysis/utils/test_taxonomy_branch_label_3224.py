# -*- coding: utf-8 -*-
"""#3224 — a fallacy label names the taxonomy branch that carries the category.

The Act III prompt rebuilt from the stored R1110 state carried the detection as
« Effet cigogne (famille Erreur de raisonnement) » — the leaf (4.1.3) and the
root (4) — and dropped the branch (4.1) « Causalité douteuse » that names the
category the Act I question asked about. The reader answered the question's
causal half "no" while its own evidence held a causal detection.

``fallacy_taxonomy_label`` is the one father of the three label sites. It
resolves the stored dotted address against the vendored taxonomy and renders
the node NAMES (never the address itself — #2031), capped at root > branch >
leaf. A detection with no usable path keeps today's two-level label: no guess.

The taxonomy is the repository's tracked CSV — deterministic, no network.
"""

from __future__ import annotations

from argumentation_analysis.utils.taxonomy_loader import (
    fallacy_taxonomy_label,
    taxonomy_chain,
)


class TestTheChainNamesTheCategory:
    def test_a_three_level_path_yields_root_branch_and_leaf(self):
        assert taxonomy_chain("4.1.3") == [
            "Erreur de raisonnement",
            "Causalité douteuse",
            "Effet cigogne",
        ]

    def test_a_two_level_path_does_not_repeat_a_node(self):
        """5.1's branch IS its leaf — the chain says it once."""
        chain = taxonomy_chain("5.1")
        assert chain is not None
        assert len(chain) == 2
        assert chain[-1] == "Définition biaisée"

    def test_a_deep_path_is_capped_at_root_branch_leaf(self):
        chain = taxonomy_chain("6.1.1.1.1.2")
        assert chain == [
            "Tricherie",
            "Présentation trompeuse des faits",
            "Exagération",
        ]

    def test_a_root_only_path_yields_the_root(self):
        assert taxonomy_chain("4") == ["Erreur de raisonnement"]

    def test_an_unreadable_taxonomy_never_crashes_a_render(self, monkeypatch):
        """The loader downloads a missing file; a download failure must not
        propagate into a label or a reading check — the caller keeps its own
        label. Proven by making the loader raise."""
        import argumentation_analysis.utils.taxonomy_loader as loader

        def _boom():
            raise RuntimeError("taxonomy unavailable")

        monkeypatch.setattr(loader, "get_taxonomy_path", _boom)
        assert taxonomy_chain("4.1.3") is None
        assert (
            fallacy_taxonomy_label("Effet cigogne", "Erreur de raisonnement", "4.1.3")
            == "Effet cigogne (famille Erreur de raisonnement)"
        )


class TestTheLabelCarriesTheBranch:
    def test_the_label_names_the_branch_that_categorises_the_detection(self):
        """The issue's witness: drop the branch from the label and this reddens
        (a mutation replacing the ancestors by ``chain[0]`` alone loses
        « Causalité douteuse »)."""
        label = fallacy_taxonomy_label(
            "Effet cigogne", "Erreur de raisonnement", "4.1.3"
        )
        assert "Causalité douteuse" in label
        assert "Effet cigogne" in label
        assert "4.1.3" not in label  # #2031 — the address never enters the label

    def test_the_label_keeps_todays_shape_when_no_path_is_recorded(self):
        assert (
            fallacy_taxonomy_label("Effet cigogne", "Erreur de raisonnement", None)
            == "Effet cigogne (famille Erreur de raisonnement)"
        )

    def test_an_unresolvable_path_keeps_todays_label_with_no_guess(self):
        """The synthesizer writes ``fallacy/<family>/<type>`` for entries with
        no address (deep_synthesis_agent); an unknown node resolves to None."""
        for path in (
            "fallacy/Erreur de raisonnement/Effet cigogne",
            "99.9",
            "4.1.3.9.9.9",
        ):
            assert (
                fallacy_taxonomy_label("Effet cigogne", "Erreur de raisonnement", path)
                == "Effet cigogne (famille Erreur de raisonnement)"
            )
        assert taxonomy_chain("fallacy/x/y") is None
        assert taxonomy_chain("") is None

    def test_a_root_only_path_labels_the_root_as_the_family(self):
        assert (
            fallacy_taxonomy_label("Effet cigogne", "inconnu", "4")
            == "Effet cigogne (famille Erreur de raisonnement)"
        )

    def test_a_recorded_family_the_root_does_not_carry_keeps_travelling(self):
        """#2031's contract: the reader gets what the record says. A family
        that names something other than the taxonomy root is printed ALONGSIDE
        the chain — the branch resolution never silences the record."""
        label = fallacy_taxonomy_label(
            "Tirer une mauvaise conclusion", "confusion de causalité", "4.3.1.1.3"
        )
        assert "famille confusion de causalité" in label
        assert "Erreur de raisonnement > Déduction invalide" in label

    def test_a_family_repeating_the_root_is_not_printed_twice(self):
        label = fallacy_taxonomy_label(
            "Effet cigogne", "Erreur de raisonnement", "4.1.3"
        )
        assert label.count("Erreur de raisonnement") == 1

    def test_the_movement_line_typography_quotes_the_name_only(self):
        """The Act II Procédé line keeps its pre-#3224 shape: the name in
        guillemets, the qualifier outside."""
        label = fallacy_taxonomy_label(
            "Effet cigogne", "Erreur de raisonnement", "4.1.3", quoted=True
        )
        assert label.startswith("« Effet cigogne » (")
