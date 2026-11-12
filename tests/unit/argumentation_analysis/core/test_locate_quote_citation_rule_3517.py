"""#3517 — one predicate: a quote the citation rule accepts has an offset.

Two functions decided whether a model's quote "occurs" in the document, and
they disagreed. The citation rule (``quote_fidelity.normalised_quote_in``,
#3389/#3465) folds case, typographic apostrophes and quotation marks,
markdown markup and elision gaps ``[…]``; ``reading_window.locate_quote``
(#3376) folded whitespace runs and nothing else. A quote that differed by an
apostrophe, a capital or a gap was KEPT by the rule and positioned by
nothing: on the R1165 paid witness, 21 of 188 kept entries (11 %) carried
``offset: None``, hiding 5 of the 39 central passages — the selector's
priority, the residue and the descent window all saw nothing there.

The repair follows the rule, never the reverse (anti-pendulum: the rule is
the contract). The fold-with-offsets is ONE implementation now —
``reading_window.folded_words`` — shared by the locator and the #3415 anchor
scan, so "found" and "anchored" read the same words.

Callers (the census, each with its effect):

* ``first_reading`` (the move offset) — an entry the rule kept is no longer
  rendered ``unpositioned``; the selector can prefer its span and the
  residue stops filing it ``unpositioned``;
* ``strategist`` (#3430, a stance anchor) — a stance anchored by a folded
  variant positions instead of falling to 0;
* ``descent_selection`` (#3376) — the descent window CENTRES on a folded
  match where it fell back to the document's head (measured effect on the
  replay band: to re-measure; if it drifts, the coordinator re-records);
* ``invoke_callables`` (the extraction span) — an extract whose quote
  differs by form alone carries a span.

Synthetic document, no corpus content. Born red on main: every variant
below returns -1 from the whitespace-only locator.
"""

from argumentation_analysis.core.reading_window import (
    STATUS_CENTRED_ON_QUOTE,
    STATUS_HEAD_FALLBACK,
    descent_selection,
    locate_quote,
)
from argumentation_analysis.reporting.restitution.quote_fidelity import (
    normalised_quote_in,
    split_on_elision_gaps,
)

# A synthetic document: one of each fold the rule performs — a typographic
# apostrophe (’ vs '), an initial capital, markdown emphasis, and two
# fragments an elided quote can bridge.
DOC = (
    "Le rapport ouvre sur une concession avant d’affirmer sa thèse. "
    "L’effort considérable demandé aux régions **porte ses fruits** dit "
    "l’auteur, chiffre unique à l’appui. La conclusion enfin invite "
    "chacun à choisir son camp."
)


class TestOnePredicate:
    """For any (text, quote): the rule accepting implies an offset."""

    def _implies_offset(self, quote: str) -> int:
        assert normalised_quote_in(DOC, quote), "fixture: the rule must accept"
        index = locate_quote(DOC, quote)
        assert index >= 0, "the rule accepts, the locator must locate"
        return index

    def test_apostrophe_variant(self):
        """The document carries ’, the quote ' — one alphabet, one offset."""
        index = self._implies_offset("avant d'affirmer sa thèse")
        assert DOC[index:].startswith("avant")

    def test_case_variant(self):
        """A capital is typography, not wording (#3389 ask 1)."""
        index = self._implies_offset("le rapport ouvre sur une concession")
        assert DOC[index:].startswith("Le rapport")

    def test_markup_variant(self):
        """Emphasis markers are form (#3465): the passage is where they sit.
        The offset names the quote's own first character — the ``**`` is
        form, dropped by the fold, so the offset sits just past it."""
        index = self._implies_offset("porte ses fruits dit")
        assert index == DOC.index("porte")  # inside "**porte", at the quote's own start
        assert DOC[index:].startswith("porte")

    def test_gap_variant(self):
        """An elided quote locates at its FIRST fragment's start."""
        index = self._implies_offset("Le rapport ouvre […] choisir son camp")
        assert index == DOC.index("Le rapport")


class TestTheOffsetAddressesTheDocument:
    def test_the_offset_names_original_characters(self):
        """``text[offset:]`` starts the passage — never a folded copy."""
        for quote, head in (
            ("avant d'affirmer sa thèse", "avant"),
            ("le rapport ouvre sur une concession", "Le rapport"),
            ("porte ses fruits dit", "porte"),
        ):
            index = locate_quote(DOC, quote)
            assert index >= 0
            assert DOC[index:].startswith(head)

    def test_the_fold_keeps_original_offsets(self):
        from argumentation_analysis.core.reading_window import folded_words

        words = folded_words(DOC)
        # every start/end pair addresses the raw document
        for _folded, start, end in words:
            assert 0 <= start < end <= len(DOC)
            assert DOC[start:end].strip()  # a real, non-empty run


class TestTheOldBehaviourIsPreserved:
    def test_exact_match_keeps_its_byte_identical_offset(self):
        quote = "Le rapport ouvre sur une concession"
        assert locate_quote(DOC, quote) == DOC.find(quote)

    def test_whitespace_runs_still_stand_for_each_other(self):
        index = locate_quote("alpha\n   beta", "alpha beta")
        assert index == 0

    def test_empty_inputs_stay_minus_one(self):
        assert locate_quote(DOC, "") == -1
        assert locate_quote("", DOC) == -1
        assert locate_quote(DOC, "   ") == -1


class TestNoFuzzyMatching:
    """The fold is the rule's, character for character — a changed word
    misses, whatever its distance."""

    def test_a_changed_word_stays_unlocated(self):
        quote = "avant d’affirmait sa thèse"  # a different word
        assert not normalised_quote_in(DOC, quote)
        assert locate_quote(DOC, quote) == -1

    def test_gap_fragments_out_of_order_stay_unlocated(self):
        quote = "choisir son camp […] Le rapport ouvre"
        assert locate_quote(DOC, quote) == -1

    def test_a_resemblance_is_not_a_location(self):
        assert locate_quote(DOC, "un effort tout à fait considérable") == -1


class TestTheGapSplitter:
    def test_one_splitter_for_the_rule_and_the_locator(self):
        assert split_on_elision_gaps("a […] b") == ["a ", " b"]
        assert split_on_elision_gaps("sans trouée") == ["sans trouée"]
        assert split_on_elision_gaps("[ … ]") == []
        assert split_on_elision_gaps(None) == []


class TestTheCallers:
    def test_descent_centres_on_a_folded_match(self):
        """The descent window (#3376) no longer falls back to the head for
        a quote the rule accepts: it centres where the passage sits. Born
        red — the whitespace-only locator returned -1 and the window read
        the document's opening."""
        selection = descent_selection(DOC, "porte ses fruits dit", window=60)
        assert selection.status == STATUS_CENTRED_ON_QUOTE
        window = DOC[selection.offset : selection.offset + selection.window]
        assert "porte ses fruits" in window  # centred on the passage

    def test_descent_still_falls_back_when_the_quote_is_absent(self):
        selection = descent_selection(DOC, "citation absente du document", window=60)
        assert selection.status == STATUS_HEAD_FALLBACK
