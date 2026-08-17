# -*- coding: utf-8 -*-
"""#1737 step 2 — unit tests for the reading-head selector.

The load-bearing tests are the two independence proofs: the selector and
the head-nature classifier must be ABLE to disagree in both directions,
otherwise the acceptance test "classifier says prose at the selected head"
cannot fail and proves nothing (coordinator R817 trap).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from measure_1737_head_nature import classify_head, head_features  # noqa: E402

from argumentation_analysis.core.reading_window import (  # noqa: E402
    STATUS_EMPTY_INPUT,
    STATUS_NO_PUNCTUATED_SPAN,
    STATUS_SELECTED,
    STATUS_SHORT_INPUT,
    select_reading_head,
)


def _prose_like(n_chars: int, commas: bool = True) -> str:
    """Synthetic prose: long VARIED sentences (rotation keeps 5-gram
    repetition below the classifier's boilerplate threshold), alphabetic,
    one paragraph line."""
    sentences = [
        "Le raisonnement déployé ici soutient une thèse précise, "
        "appuyée sur des prémisses explicites, que l'auditoire peut examiner",
        "Cette argumentation progressait par étapes successives, "
        "chacune annoncée comme décisive, et pourtant toujours révisable",
        "L'orateur concédait volontiers l'apparence d'une objection, "
        "avant d'en retourner la force contre celui qui l'avait formulée",
        "Une pareille construction suppose un auditoire patient, "
        "disposé à suivre l'enchaînement des preuves jusqu'à sa conclusion",
        "Le propos ne cherchait pas la conciliation, mais l'épreuve, "
        "et cette préférence se lisait dans chaque transition du discours",
        "Face à cette accumulation d'arguments circonstanciels, "
        "la conclusion paraissait inévitable, bien qu'elle ne fût jamais dite",
    ]
    if not commas:
        sentences = [s.replace(",", "") for s in sentences]
    out = []
    total = 0
    i = 0
    while total < n_chars:
        out.append(sentences[i % len(sentences)] + ". ")
        total += len(sentences[i % len(sentences)]) + 2
        i += 1
    return "".join(out)


def _toc_like(n_chars: int, punctuated: bool = False) -> str:
    """Synthetic TOC: short title lines, one per line."""
    entries = [
        "Discours de Marseille 14 juillet 1990",
        "Discours de Lyon 8 juin 1991",
        "Allocution de Paris 12 mai 1992",
        "Déclaration de Lille 3 mars 1993",
    ]
    sep = ", page " if punctuated else " page "
    out = []
    total = 0
    i = 0
    while total < n_chars:
        line = entries[i % len(entries)] + sep + str(10 + i) + "\n"
        out.append(line)
        total += len(line)
        i += 1
    return "".join(out)


class TestIndependenceFromClassifier:
    """The selector does NOT embed the classifier (R817 trap, defused)."""

    def test_classifier_blesses_what_selector_refuses(self):
        """Comma-less clean prose: classifier says prose, selector finds no
        punctuated span. A circular selector (reusing classifier features)
        would have selected offset 0 here — this test cannot pass for it."""
        text = _prose_like(6000, commas=False)
        assert classify_head(head_features(text[:3000])) == "prose"
        sel = select_reading_head(text, 3000)
        assert sel.status == STATUS_NO_PUNCTUATED_SPAN

    def test_selector_accepts_what_classifier_condemns(self):
        """Comma-dense year list: selector selects, classifier says
        metadata (year density). The two verdicts cross here."""
        text = _toc_like(6000, punctuated=True)
        sel = select_reading_head(text, 3000)
        assert sel.status == STATUS_SELECTED
        assert classify_head(head_features(text[sel.offset : sel.offset + 3000])) in (
            "metadata",
            "mixed",
        )


class TestSelection:
    def test_prose_head_selected_at_zero(self):
        # Ordinary prose head: nothing moves (non-regression property).
        sel = select_reading_head(_prose_like(8000), 3000)
        assert sel.offset == 0
        assert sel.status == STATUS_SELECTED

    def test_offset_zero_never_snapped(self):
        # A newline inside the first stride must NOT move an offset-0
        # selection (multi-paragraph prose corpus head): reproducing
        # today's window exactly is the non-regression contract.
        paras = _prose_like(400) + "\n" + _prose_like(6000)
        sel = select_reading_head(paras, 3000)
        assert sel.offset == 0
        assert sel.status == STATUS_SELECTED

    def test_skips_toc_to_find_prose(self):
        toc = _toc_like(30000)
        prose = _prose_like(8000)
        text = toc + prose
        sel = select_reading_head(text, 3000)
        assert sel.status == STATUS_SELECTED
        assert sel.offset >= 30000 - 500  # at most one stride before prose
        window = text[sel.offset : sel.offset + 3000]
        # The selected window contains no TOC entry — a boundary mix would.
        assert "juillet" not in window

    def test_all_metadata_reports_loudly(self):
        # Fail loud, never a silent window: a TOC-only text is reported.
        sel = select_reading_head(_toc_like(50000), 3000)
        assert sel.status == STATUS_NO_PUNCTUATED_SPAN
        assert sel.offset == 0

    def test_empty_input(self):
        sel = select_reading_head("", 3000)
        assert sel.status == STATUS_EMPTY_INPUT
        assert sel.offset == 0

    def test_short_input(self):
        sel = select_reading_head("Court texte sans structure.", 3000)
        assert sel.status == STATUS_SHORT_INPUT
        assert sel.offset == 0

    def test_short_punctuated_input_selects(self):
        text = _prose_like(2000)
        sel = select_reading_head(text, 3000)
        assert sel.status == STATUS_SELECTED

    def test_invalid_window_raises(self):
        with pytest.raises(ValueError):
            select_reading_head("texte", 0)

    def test_determinism(self):
        text = _toc_like(20000) + _prose_like(8000)
        a = select_reading_head(text, 4000)
        b = select_reading_head(text, 4000)
        assert a == b
