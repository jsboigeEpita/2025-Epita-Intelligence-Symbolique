# -*- coding: utf-8 -*-
"""#1737 step 3 — wiring tests: site -> shared state -> report reader.

The DoD's load-bearing test is the chain: a non-prose head must produce a
STATUS that is recorded on the shared state by the site's helper call AND
rendered by the report's reader (a status nobody displays is the #1019
shape). The reader is verified at the report construction site
(``build_narrative``), not in the module that writes the status.

Non-regression at site level: on an already-prose corpus the helper must
return EXACTLY the old fixed-head slice (``text[:N]``) — nothing moves.
"""

import pytest

from argumentation_analysis.core.reading_window import (
    STATUS_NO_PUNCTUATED_SPAN,
    STATUS_SELECTED,
    reading_state_from_context,
    selected_text,
)
from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    build_narrative,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _prose_like(n_chars: int) -> str:
    """Synthetic prose: long VARIED sentences (see test_reading_window.py)."""
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
    out = []
    total = 0
    i = 0
    while total < n_chars:
        out.append(sentences[i % len(sentences)] + ". ")
        total += len(sentences[i % len(sentences)]) + 2
        i += 1
    return "".join(out)


def _toc_like(n_chars: int) -> str:
    """Synthetic TOC: short title lines (one per line), no sub-clause
    punctuation — the corpus_B head shape (dates + page numbers)."""
    entries = [
        "Discours de Marseille 14 juillet 1990",
        "Discours de Lyon 8 juin 1991",
        "Allocution de Paris 12 mai 1992",
        "Déclaration de Lille 3 mars 1993",
    ]
    out = []
    total = 0
    i = 0
    while total < n_chars:
        line = entries[i % len(entries)] + " page " + str(10 + i) + "\n"
        out.append(line)
        total += len(line)
        i += 1
    return "".join(out)


class TestChainToReader:
    """The status travels site -> state -> report and is VISIBLE there."""

    def test_toc_head_status_is_rendered_by_the_report(self):
        state = UnifiedAnalysisState(_toc_like(500))
        toc = _toc_like(12000)

        captured = selected_text(toc, 3000, "fact_extraction", state=state)

        recorded = state.reading_window_status["fact_extraction"]
        assert recorded["status"] == STATUS_NO_PUNCTUATED_SPAN
        assert recorded["offset"] == 0
        # Old behaviour preserved on a refused head: offset stays 0.
        assert captured == toc[:3000]

        narrative = build_narrative(state)
        assert "Avertissement fenetre de lecture" in narrative
        assert "fact_extraction=no_punctuated_span_found" in narrative

    def test_prose_head_is_not_flagged_and_slice_is_identical(self):
        state = UnifiedAnalysisState(_prose_like(500))
        prose = _prose_like(12000)

        captured = selected_text(prose, 3000, "fact_extraction", state=state)

        recorded = state.reading_window_status["fact_extraction"]
        assert recorded["status"] == STATUS_SELECTED
        assert recorded["offset"] == 0
        # Site-level non-regression: exactly the old fixed-head slice.
        assert captured == prose[:3000]

        narrative = build_narrative(state)
        assert "Avertissement fenetre de lecture" not in narrative
        assert "Fenetre de lecture" not in narrative

    def test_moved_window_is_reported_as_information(self):
        state = UnifiedAnalysisState(_prose_like(500))
        text = _toc_like(10000) + _prose_like(10000)

        selected_text(text, 3000, "fact_extraction", state=state)

        recorded = state.reading_window_status["fact_extraction"]
        assert recorded["status"] == STATUS_SELECTED
        assert recorded["offset"] > 0

        narrative = build_narrative(state)
        assert "la lecture a ete deplacee" in narrative
        assert "fact_extraction (offset" in narrative

    def test_multiple_sites_all_surface(self):
        state = UnifiedAnalysisState(_toc_like(500))
        toc = _toc_like(12000)

        selected_text(toc, 2000, "governance", state=state)
        selected_text(toc, 1500, "debate_analysis", state=state)

        narrative = build_narrative(state)
        assert "governance=no_punctuated_span_found" in narrative
        assert "debate_analysis=no_punctuated_span_found" in narrative


class TestStateResolutionAndFailLoud:
    """The wiring helper resolves the state; an unrelated object fails loud."""

    def test_reading_state_from_context_prefers_state_object(self):
        state = UnifiedAnalysisState("seed")
        assert reading_state_from_context({"_state_object": state}) is state

    def test_reading_state_from_context_falls_back_to_unified_state(self):
        state = UnifiedAnalysisState("seed")
        assert reading_state_from_context({"unified_state": state}) is state

    def test_reading_state_from_context_none_without_state(self):
        assert reading_state_from_context({}) is None
        assert reading_state_from_context(None) is None
        assert reading_state_from_context({"unified_state": "not-a-state"}) is None

    def test_unrelated_state_object_fails_loud(self):
        class NotAState:
            pass

        with pytest.raises(TypeError, match="has no record_reading_window"):
            selected_text(_prose_like(500), 1000, "x", state=NotAState())
