"""#3389 — a « … » span in the reader's prose is checked against the document.

The v1 panel's cycle 0 measured three facts the report could not see about
itself. Act III printed an invitation between « » that the document does not
carry (one pronoun changed), Act II printed a French translation of an
English document as if it were the document's words while Act III of the same
fiche quoted the English original, and the non-French documents' exact quotes
stayed untranslated inside the French prose.

Nothing compared those spans with the text. ``reader_vocabulary_check``
(#3319) catches a pre-computed verdict printed between « », and the
readability gate treats every « … » as quoted data and skips it
(``_QUOTED_SPAN_RE``) — both assume a span IS the document's words. This
module stops assuming.

**One producer.** The judge's ``document_quote`` check (#3375 tranche 3) and
this render check are the SAME rule: a quote is located when it occurs in the
document after normalising case, whitespace, typographic apostrophes and
quotation marks, with ``[…]`` read as an elision gap. ``normalise_for_citation``
and ``occurs_in_document`` are that one rule; ``judge_panel.is_cited``
delegates to them instead of carrying a second copy.

**Three labels, at write time.** Every span is one of

* ``verbatim`` — a substring of the document (gap-aware);
* ``translation`` — not in the document, and the document's language differs
  from the report's, so the span can only be a rendering of the original;
* ``unverified`` — neither: same-language prose that the document does not
  carry.

The acts run while the text is in memory (``state.raw_text``), so the
classification happens where the prose is produced, not in a later audit.

**The degradation, never the silence.** An ``unverified`` span loses its
guillemets: it reads as the paraphrase it is. A ``translation`` span loses
them too — the policy says the ORIGINAL goes between « », followed by its
French rendering marked ``(trad. : …)``, so a translation is never printed
between « » on its own, and the original is not mechanically recoverable from
it. A ``verbatim`` span is never touched: an exact quote passes byte-identical.

Nothing here is fuzzy (#3385's rule): an approximate match is a guess. The
check never forbids quoting and asks the writer nothing — the writer prompt is
not told to be careful.

**Privacy.** The event carries the act name and counts, never a span: the
audit object holds no text of the document's words, and ``motif`` prints
numbers only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

#: The report's own language. The three acts and the deep synthesis are
#: written in French, so a span can only be a TRANSLATION when the document
#: is in another language.
REPORT_LANGUAGE = "fr"

#: One quotation span. Non-greedy by construction (the class excludes both
#: guillemets), bounded so a malformed pair cannot swallow a whole act.
_SPAN_RE = re.compile(r"«([^«»]{1,4000})»")

#: An elision gap inside a quotation: ``[…]``, ``[...]``, ``[ … ]``. This is
#: the one marker the project already prints when a producer bounds a quote
#: (``cited_units.CUT_MARKER``).
_GAP_RE = re.compile(r"\[\s*(?:…|\.\.\.)\s*\]")

#: A French rendering printed right after the closing guillemet — the form
#: ask 3 of #3389 asks for: ``« original » (trad. : …)``.
_RENDERING_RE = re.compile(r"^[ \t]*\((?:trad|traduction)[^)]{0,400}\)", re.I)

#: Typographic variants folded to their ASCII form before matching. An
#: apostrophe the writer types as ’ and the document carries as ' is the
#: same word; folding it is not fuzzy matching, it is one alphabet.
_FOLD = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "ʼ": "'",
        "´": "'",
        "“": '"',
        "”": '"',
        " ": " ",
        " ": " ",
        "­": "",
    }
)

_WS_RE = re.compile(r"\s+")

#: Labels an audit can count. ``verbatim`` and ``translation`` and
#: ``unverified`` are the issue's three; ``untranslated`` is a verbatim span
#: of a foreign document printed with no ``(trad. : …)`` rendering beside it —
#: exact, but unreadable for the report's reader, and named so the panel can
#: count it.
VERBATIM = "verbatim"
TRANSLATION = "translation"
UNVERIFIED = "unverified"


def normalise_for_citation(text: Any) -> str:
    """The comparison form of ``text``: case, whitespace and quotes folded.

    Case folding is deliberate (#3389 ask 1): capitalisation is typography,
    not wording. Whitespace runs collapse so a line-wrapped quote still
    matches; typographic apostrophes and quotation marks fold to ASCII.
    """
    if not text:
        return ""
    return _WS_RE.sub(" ", str(text).translate(_FOLD)).strip().casefold()


def _fragments(span: str) -> List[str]:
    """The span split on its elision gaps, each fragment normalised."""
    parts = [normalise_for_citation(p) for p in _GAP_RE.split(span)]
    return [p for p in parts if p]


def occurs_in_document(span: Any, document: Any) -> bool:
    """True when ``span`` occurs in ``document`` after normalisation.

    ``[…]`` is a GAP, not a literal: the fragments must occur IN ORDER,
    each after the previous one's end. A span whose fragments are empty
    (nothing but a gap) is not a citation.
    """
    fragments = _fragments(span)
    if not fragments:
        return False
    haystack = normalise_for_citation(document)
    if not haystack:
        return False
    cursor = 0
    for fragment in fragments:
        found = haystack.find(fragment, cursor)
        if found < 0:
            return False
        cursor = found + len(fragment)
    return True


def normalised_quote_in(text: Any, quote: Any) -> bool:
    """The judge's check (#3375) expressed on this module's rule.

    Same floor as before — a word or two is a keyword, not a citation — and
    the same matcher as the render's, gap included, from ONE implementation.
    A judge that elides the middle of its quote with ``[…]`` has still quoted
    the text; without the gap rule its item was dropped by a technicality.
    """
    needle = normalise_for_citation(quote)
    if len(needle) < 8:
        return False
    return occurs_in_document(quote, text)


def document_language(document: Any) -> str:
    """``"fr"``/``"en"``/``"de"``/``"unknown"``/``"unlisted"`` — the one detector.

    #3425 — ``unlisted`` is a real answer, not a fourth language: the probe is
    long enough and no list the heuristic carries covers it. It is the answer
    that licenses :data:`TRANSLATION` below; ``unknown`` never does.

    Lazy on purpose: the import pulls the conversational orchestrator, and
    the common case (a French document, every span verbatim) never asks this
    function at all. A detector that cannot answer returns ``"unknown"``,
    which never licenses the ``translation`` label — an unproven language is
    not a proven translation (anti-#1019).

    No memoisation (R1141): the first cut cached the verdict under the
    document's first 2 000 characters, and the corpus holds documents cut
    from one source — the second twin inherited the first's language. The
    call runs once per act (``sanitize_document_quotes`` resolves the
    language once and passes it to every span), so the cache bought three
    heuristic probes per document and cost the label's ownership.
    """
    text = str(document or "")
    if not text:
        return "unknown"
    try:
        from argumentation_analysis.agents.core.text_scoring import detect_language

        lang = str(detect_language(text) or "unknown")
    except Exception:  # noqa: BLE001 — a probe that cannot run proves nothing
        lang = "unknown"
    return lang


def classify_span(
    span: str,
    document: str,
    lang: Optional[str] = None,
    report_language: str = REPORT_LANGUAGE,
) -> str:
    """``verbatim`` / ``translation`` / ``unverified`` for one span."""
    if occurs_in_document(span, document):
        return VERBATIM
    doc_lang = document_language(document) if lang is None else lang
    # #3425 — the two "no listed language" answers are NOT interchangeable:
    # ``unknown`` (too thin a probe) proves nothing about the document, so the
    # span stays ``unverified`` (anti-#1019); ``unlisted`` (a long probe that
    # no listed language covers) proves the document is NOT in the report's
    # language, which is exactly what licenses a ``translation``. Both are
    # excluded from the named case, only the second falls through to it.
    if doc_lang not in ("unknown", report_language):
        return TRANSLATION
    return UNVERIFIED


@dataclass(frozen=True)
class QuoteAudit:
    """What the check did to one act's prose — counts and the degraded text.

    No span is kept: the record may travel to the appendix, and the document's
    words must not (#3249's rule, #3389's privacy paragraph).
    """

    text: str
    spans: int = 0
    verbatim: int = 0
    untranslated: int = 0
    translation: int = 0
    unverified: int = 0

    @property
    def degraded(self) -> int:
        return self.translation + self.unverified

    def motif(self, act_label: str) -> str:
        """The state's record of the gesture, or ``""`` when nothing moved.

        Wording is counts only. ``untranslated`` is reported even though the
        prose is exact: an exact quote a French reader cannot read is the
        other half of #3389 ask 3, and the panel needs to count it.
        """
        if not self.spans:
            return ""
        parts: List[str] = []
        if self.degraded:
            parts.append(
                f"{self.degraded} citation(s) retirée(s) des guillemets "
                f"({self.translation} traduction(s) de la langue source, "
                f"{self.unverified} non retrouvée(s) dans le document) — "
                "elles se lisent désormais comme des paraphrases"
            )
        if self.untranslated:
            parts.append(
                f"{self.untranslated} citation(s) fidèle(s) restée(s) dans la "
                "langue du document sans rendering français"
            )
        if not parts:
            return ""
        return (
            f"{act_label} : « … » comparés au document à l'écriture — "
            f"{self.verbatim}/{self.spans} fidèle(s) ; "
            + " ; ".join(parts)
            + " (#3389)."
        )


def sanitize_document_quotes(
    text: Any,
    document: Any,
    *,
    report_language: str = REPORT_LANGUAGE,
) -> QuoteAudit:
    """Classify every « … » span of ``text`` and degrade the unproven ones.

    ``verbatim`` spans are left BYTE-IDENTICAL — the render of a document
    quoted exactly is not touched at all. ``translation`` and ``unverified``
    spans keep their words and lose their guillemets, so they read as the
    paraphrase they are.

    No document means no check: an empty ``raw_text`` cannot prove anything,
    and stripping every span against an empty corpus would degrade correct
    prose. The prose is returned unchanged, with zero counts.
    """
    source = str(text or "")
    corpus = str(document or "")
    if not source or not corpus:
        return QuoteAudit(text=source)

    lang: Optional[str] = None
    spans = verbatim = untranslated = translation = unverified = 0
    out: List[str] = []
    cursor = 0
    for match in _SPAN_RE.finditer(source):
        inner = match.group(1)
        spans += 1
        if lang is None:
            lang = document_language(corpus)
        label = classify_span(inner, corpus, lang, report_language)
        out.append(source[cursor : match.start()])
        if label == VERBATIM:
            verbatim += 1
            out.append(match.group(0))
            if lang not in ("unknown", report_language):
                tail = source[match.end() : match.end() + 400]
                if not _RENDERING_RE.match(tail):
                    untranslated += 1
        else:
            if label == TRANSLATION:
                translation += 1
            else:
                unverified += 1
            # The words stay, the guillemets go — and the tight boundary is
            # trimmed so the sentence does not keep a double space where the
            # opening guillemet used to sit.
            out.append(inner.strip())
        cursor = match.end()
    out.append(source[cursor:])
    return QuoteAudit(
        text="".join(out),
        spans=spans,
        verbatim=verbatim,
        untranslated=untranslated,
        translation=translation,
        unverified=unverified,
    )


def sanitize_act_quotes(
    narrative: Any,
    state: Any,
    act_label: str,
    *,
    report_language: str = REPORT_LANGUAGE,
) -> Tuple[str, str]:
    """``(prose, motif)`` for one act — the call the three acts make.

    Reads the document off the state (``raw_text``), the same field the acts
    already bound their reader lines to. ``motif`` is empty when the act
    carries no span, or when every span is an exact quote.
    """
    document = getattr(state, "raw_text", "") or ""
    audit = sanitize_document_quotes(
        narrative, document, report_language=report_language
    )
    return audit.text, audit.motif(act_label)
