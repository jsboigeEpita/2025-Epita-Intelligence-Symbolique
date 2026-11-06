"""#3465 — the citation rule folds markdown markup, never content.

Measured on the third-family judge's one-document probe (panel B): **7 of
7 items dropped**, every one ``quote_not_in_zeroshot_text``. The zero-shot
answer is markdown; that judge quotes the RENDERED text (emphasis markers
dropped, lines re-flowed), and ``normalise_for_citation`` (#3389) read
``* _ \\` # >`` and list bullets as CONTENT. Once those markers fold on
both sides, 6 of the 7 quotes are found; the 7th is a genuine miss and
must still drop.

The dispatch's DoD, one witness per clause:

- a quote of the rendered form of a markdown answer is found — emphasis,
  headings, blockquotes, list bullets, inline code, guillemets as prose
  quotes;
- a quote with one changed word is NOT (folding goes no further: no fuzzy
  matching, no edit distance);
- a span that only exists by joining two separate emphasised fragments is
  NOT found;
- the length floor of ``is_cited`` stays;
- one rule, one producer (#3389): the render's « … » check follows the same
  rule — its exact-verbatim path is untouched, and a fabricated span still
  fails.

Synthetic texts only — no corpus content. **Born red on main.**
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from argumentation_analysis.reporting.restitution.quote_fidelity import (  # noqa: E402
    normalise_for_citation,
    normalised_quote_in,
    occurs_in_document,
    sanitize_document_quotes,
)

# A synthetic markdown answer, in the shape the zero-shot arm produces:
# emphasis, a heading, a blockquote, a bullet list, inline code.
MARKDOWN_ANSWER = """## Ce que le document soutient

Le document défend la **réforme de 1998** en trois mouvements :

- d'abord, il rappelle que *le déficit a été réduit de moitié* ;
- ensuite, il soutient que cette mesure **n'a jamais été contestée** sur
  le principe ;
- enfin, il note que `l'impôt unique` reste une proposition.

> La thèse centrale tient en une phrase : la mesure a réduit le déficit
> de moitié, et le texte appuie cette affirmation sur trois chiffres datés.

L'_argument principal_ est donc **calibré** sur la chronologie.

Le rapport conclut : « une décision mesurable reste à prendre ».
"""

# The same content as a reader (or a judge quoting the rendered text)
# reads it: markers gone, words identical.
RENDERED_QUOTE = (
    "le document défend la réforme de 1998 en trois mouvements : "
    "d'abord, il rappelle que le déficit a été réduit de moitié"
)


class TestTheRenderedQuoteIsFound:
    def test_a_quote_of_the_rendered_text_matches_its_markdown_source(self):
        assert normalised_quote_in(MARKDOWN_ANSWER, RENDERED_QUOTE), (
            "a judge quoting the rendered form of a markdown answer is "
            "dropped for formatting alone (#3465: 6/7 of the probe's items)"
        )

    @pytest.mark.parametrize(
        "quote",
        [
            # emphasis spans inside a running sentence
            "il soutient que cette mesure n'a jamais été contestée sur le principe",
            # a heading's words read as prose
            "Ce que le document soutient",
            # blockquote, re-flowed onto one line
            "La thèse centrale tient en une phrase : la mesure a réduit le déficit "
            "de moitié, et le texte appuie cette affirmation sur trois chiffres datés.",
            # inline code read as plain words
            "il note que l'impôt unique reste une proposition",
            # single-underscore emphasis, the other markdown form
            "L'argument principal est donc calibré sur la chronologie.",
            # a rendered quote stripped of its guillemets
            "une décision mesurable reste à prendre",
        ],
    )
    def test_each_markup_shape_folds(self, quote):
        assert normalised_quote_in(MARKDOWN_ANSWER, quote)

    def test_both_directions_agree(self):
        """The rule is one normalisation on both sides — a quote that
        carries the markers also matches (nothing became one-way)."""
        marked = "le document défend la **réforme de 1998** en trois mouvements"
        assert normalised_quote_in(MARKDOWN_ANSWER, marked)
        assert normalised_quote_in(
            MARKDOWN_ANSWER, "« une décision mesurable reste à prendre »"
        )

    def test_a_comparison_mid_sentence_remains_content(self):
        """Only a leading ``>`` is a blockquote: a mathematical comparison
        inside a sentence is not markup and must not be folded away."""
        assert normalised_quote_in(
            "Le seuil retenu est n > 3.", "seuil retenu est n > 3"
        )
        assert not normalised_quote_in(
            "Le seuil retenu est n > 3.", "seuil retenu est n 3"
        )

    def test_the_judge_side_of_the_one_rule(self):
        """``judge_panel.is_cited`` delegates here (#3389 one producer) —
        pin that the rendered quote survives the judge's own entry point."""
        from scripts.dataset.judge_panel import is_cited

        assert is_cited(MARKDOWN_ANSWER, RENDERED_QUOTE)


class TestFoldingGoesNoFurther:
    def test_a_quote_with_one_changed_word_is_not_found(self):
        changed = RENDERED_QUOTE.replace("1998", "1999")
        assert not normalised_quote_in(MARKDOWN_ANSWER, changed)

    def test_a_span_that_only_exists_by_joining_two_fragments_is_not_found(self):
        """Two separate emphasised fragments are TWO spans: a judge that
        stitches '**réforme de 1998**' to '**n'a jamais été contestée**'
        invents a sentence the answer never wrote."""
        stitched = "réforme de 1998 n'a jamais été contestée"
        assert not normalised_quote_in(MARKDOWN_ANSWER, stitched)

    def test_the_genuine_miss_still_drops(self):
        """The probe's 7th item was a real absence: folding must not
        rescue it."""
        absent = "le document justifie la réforme par un plébiscite unanime"
        assert not normalised_quote_in(MARKDOWN_ANSWER, absent)

    def test_the_length_floor_stays(self):
        """A word or two is a keyword, not a citation (#3389 floor): even
        a real, emphasised word is too short to count."""
        assert not normalised_quote_in(MARKDOWN_ANSWER, "réforme")
        assert len(normalise_for_citation("réforme")) < 8


class TestOneRuleOneProducer:
    def test_the_renders_span_check_follows_the_same_rule(self):
        """The « … » check of the render (#3389) reads the SAME rule: a
        span quoted from a markdown-shaped document is verbatim."""
        document = (
            "Le texte porte **une affirmation centrale** qui tient en une phrase."
        )
        span = "une affirmation centrale qui tient"
        assert occurs_in_document(span, document)

    def test_a_fabricated_span_still_fails_the_render_check(self):
        document = (
            "Le texte porte **une affirmation centrale** qui tient en une phrase."
        )
        assert not occurs_in_document("une affirmation périphérique", document)
        audit = sanitize_document_quotes(
            "Le rapport cite « une affirmation périphérique » sans preuve.",
            document,
        )
        assert audit.unverified == 1
        assert "«" not in audit.text, "a fabricated span loses its guillemets"

    def test_an_exact_verbatim_span_stays_byte_identical(self):
        """The degradation rule is untouched: what matched before still
        matches, and a verbatim span keeps its guillemets."""
        document = (
            "Le texte porte **une affirmation centrale** qui tient en une phrase."
        )
        prose = "Le rapport cite « **une affirmation centrale** » telle quelle."
        audit = sanitize_document_quotes(prose, document)
        assert audit.verbatim == 1
        assert audit.text == prose

    def test_markup_alone_never_becomes_a_quote(self):
        """Folding markers must not leave an empty needle matching
        everything: a span of pure markup is not a citation."""
        assert not occurs_in_document("** **", MARKDOWN_ANSWER)
        assert not normalised_quote_in(MARKDOWN_ANSWER, "## ##")
