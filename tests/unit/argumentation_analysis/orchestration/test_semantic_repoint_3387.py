"""#3387 — the semantic index reads the DOCUMENT, and a reader spends it.

The phase used to index the run's own extracted arguments and search them
back (R1300: no corpus ever indexed, no reader outside the writer). The
2026-11-05 decision repointed it: chunk the analysed document's own text, ask
the first reading's central thesis (#3415), and hand the passages that answer
it to the budget selector as ``priority_spans`` — the #3395/#3406 consumer
that already accepts exactly this input.

Privacy: the fixtures are synthetic text with opaque ids; nothing here carries
corpus content, and what the phase returns are OFFSETS, never text.

The embedding endpoint is faked (no network, no paid call): a deterministic
bag-of-words vector, so "does retrieval find the passage that matches the
question" is measured rather than asserted.

Born-red witness: on a long synthetic document whose thesis passage sits past
the point a head-anchored pass ever reaches, the retrieval places a span
there and the selector takes a unit inside it — a unit the declared
``priority_spans`` of a head-only pass could not name.
"""

from __future__ import annotations

import os
import re
import zlib
from typing import Any, Dict, List, Sequence, Tuple
from unittest.mock import patch

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.orchestration.selection import select_for_budget
from argumentation_analysis.services import semantic_retrieval as sr

# ---------------------------------------------------------------------------
# A deterministic, network-free embedder
# ---------------------------------------------------------------------------

_DIM = 96


def _vector(text: str) -> List[float]:
    vec = [0.0] * _DIM
    for word in re.findall(r"[0-9a-zà-ÿ]+", text.lower()):
        vec[zlib.crc32(word.encode("utf-8")) % _DIM] += 1.0
    return vec


def _fake_post_embeddings(route: Any, texts: Sequence[str]) -> List[List[float]]:
    return [_vector(t) for t in texts]


@pytest.fixture(autouse=True)
def _fake_endpoint(monkeypatch):
    """Every witness runs the real code path against a fake embedder."""
    monkeypatch.setattr(sr, "_post_embeddings", _fake_post_embeddings)


#: The sentence the thesis is about — deliberately placed far from the head.
_THESIS_SENTENCE = (
    "Le budget proposé transfère la décision fiscale du parlement vers "
    "l'exécutif sans aucun débat public préalable."
)


def _long_document(filler_sentences: int = 220) -> str:
    """A synthetic document whose thesis sits far past the head."""
    filler = (
        "La séance reprend après une pause et la parole circule entre les "
        "groupes selon un ordre convenu à l'avance."
    )
    head = " ".join(filler for _ in range(filler_sentences // 2))
    tail = " ".join(filler for _ in range(filler_sentences // 2))
    return f"{head} {_THESIS_SENTENCE} {tail}"


class _Reading:
    """Minimal stand-in for the state's reading: ``defining_moves`` shape."""

    def __init__(self, moves: List[Dict[str, Any]]):
        self.defining_moves = {"moves": moves}


def _thesis_state() -> _Reading:
    return _Reading(
        [
            {
                "kind": "thesis",
                "reading": "Le texte déplace la décision fiscale vers l'exécutif.",
                "quote": _THESIS_SENTENCE,
                "offset": None,
            }
        ]
    )


# ---------------------------------------------------------------------------
# The route: one source for the pair, or no route at all
# ---------------------------------------------------------------------------


class TestTheEmbeddingRouteIsAPair:
    def test_a_half_declared_pair_is_refused_and_names_the_missing_half(
        self, monkeypatch
    ):
        monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
        monkeypatch.delenv(sr.EMBEDDING_URL_ENV, raising=False)
        route, reason = sr.resolve_embedding_route()
        assert route is None
        assert sr.EMBEDDING_URL_ENV in reason
        assert "PAIR" in reason

    def test_a_declared_pair_is_used_alone(self, monkeypatch):
        monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
        monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://127.0.0.1:8005/v1")
        monkeypatch.setenv(sr.EMBEDDING_MODEL_ENV, "local-embed")
        with patch(
            "argumentation_analysis.core.llm_service.resolve_chat_endpoint"
        ) as provider:
            route, reason = sr.resolve_embedding_route()
        provider.assert_not_called()  # the declared pair wins, no provider read
        assert reason == ""
        assert route is not None
        assert (route.base_url, route.model, route.source) == (
            "http://127.0.0.1:8005/v1",
            "local-embed",
            "declared",
        )

    def test_no_pair_falls_back_to_the_one_provider_resolver(self, monkeypatch):
        monkeypatch.delenv(sr.EMBEDDING_KEY_ENV, raising=False)
        monkeypatch.delenv(sr.EMBEDDING_URL_ENV, raising=False)
        with patch(
            "argumentation_analysis.core.llm_service.resolve_chat_endpoint",
            return_value=("sk-provider", "https://provider.test/v1", "gpt-x"),
        ):
            route, reason = sr.resolve_embedding_route()
        assert reason == ""
        assert route is not None
        # Key and URL from the SAME resolver — never one from each place.
        assert (route.api_key, route.base_url, route.source) == (
            "sk-provider",
            "https://provider.test/v1",
            "provider",
        )

    def test_no_route_at_all_names_itself(self, monkeypatch):
        monkeypatch.delenv(sr.EMBEDDING_KEY_ENV, raising=False)
        monkeypatch.delenv(sr.EMBEDDING_URL_ENV, raising=False)
        with patch(
            "argumentation_analysis.core.llm_service.resolve_chat_endpoint",
            return_value=("", "", ""),
        ):
            route, reason = sr.resolve_embedding_route()
        assert route is None
        assert "no embedding route" in reason


# ---------------------------------------------------------------------------
# Chunks and spans
# ---------------------------------------------------------------------------


def test_every_chunk_span_points_at_its_own_text():
    text = _long_document(filler_sentences=8)
    chunks = sr.chunk_spans(text)
    assert chunks, "the document yielded no chunk"
    for chunk in chunks:
        assert text[chunk.start : chunk.end] == chunk.text


# ---------------------------------------------------------------------------
# The phase — the document, the reading's question, and honest absence
# ---------------------------------------------------------------------------


async def test_phase_names_a_missing_route(monkeypatch):
    monkeypatch.delenv(sr.EMBEDDING_KEY_ENV, raising=False)
    monkeypatch.delenv(sr.EMBEDDING_URL_ENV, raising=False)
    with patch(
        "argumentation_analysis.core.llm_service.resolve_chat_endpoint",
        return_value=("", "", ""),
    ):
        result = await ic._invoke_semantic_index(
            "un document suffisamment long " * 20, {}
        )
    assert result["status"] == "skipped: no_embedding_route"
    assert result["reason"]


async def test_phase_names_a_missing_question(monkeypatch):
    monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
    monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://test/v1")
    result = await ic._invoke_semantic_index(
        "un document suffisamment long " * 20, {"_state_object": _Reading([])}
    )
    assert result["status"] == "skipped: no_reading_query"
    assert "no defining move" in result["reason"]


async def test_phase_names_a_reading_without_a_thesis(monkeypatch):
    monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
    monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://test/v1")
    state = _Reading([{"kind": "concession", "quote": "un extrait", "offset": 0}])
    result = await ic._invoke_semantic_index(
        "un document suffisamment long " * 20, {"_state_object": state}
    )
    assert result["status"] == "skipped: no_reading_query"
    assert "concession" in result["reason"]  # the kinds it did record


# ---------------------------------------------------------------------------
# Born red — the retrieval reaches what a head-anchored pass never does
# ---------------------------------------------------------------------------


class TestTheRetrievalReachesPastTheHead:
    @pytest.mark.asyncio
    async def test_the_thesis_passage_is_found_far_from_the_head(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
        monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://test/v1")
        document = _long_document()
        result = await ic._invoke_semantic_index(
            document, {"_state_object": _thesis_state()}
        )
        assert result["status"] == "ran", result
        assert result["route_source"] == "declared"
        spans: List[List[int]] = result["priority_spans"]
        assert spans, "aucun span: la récupération n'a rien classé"

        thesis_at = document.index(_THESIS_SENTENCE)
        # The head of this document holds no thesis passage: a pass that only
        # looks at the opening cannot name what the retrieval names.
        assert thesis_at > len(document) // 3, (
            f"le document de témoin place la thèse trop près de l'entête "
            f"({thesis_at}/{len(document)})"
        )

        def overlaps_thesis(span: Sequence[int]) -> bool:
            return span[0] < thesis_at + len(_THESIS_SENTENCE) and thesis_at < span[1]

        assert any(overlaps_thesis(s) for s in spans), (
            "la récupération n'a pas placé de span sur le passage thématique: "
            f"spans={spans} these={thesis_at}"
        )
        best = spans[0]
        assert best[0] > len(document) // 4, (
            "le meilleur span est dans l'entête: la requête n'a pas orienté la "
            f"récupération (span={best}, longueur={len(document)})"
        )

    def test_the_recorded_span_makes_the_selector_take_the_far_unit(self) -> None:
        """The reader half: a span recorded by the phase reaches
        ``select_for_budget`` and pulls a unit the base budget skips.

        #3523 — the span sits on ``unité 27`` (offset 2716, band 3): the
        nested target order takes it only when the span is present. The
        former witness used ``unité 20`` at (2000, 2200); since #3523 the
        base band-2 target at 1/2 (offset 2000) lands on that exact unit,
        so it no longer distinguishes the two runs — the property is the
        same, the witness moved to a unit the base still skips."""
        units = [f"unité {i} du document" for i in range(40)]
        spans = [(2700, 2760)]
        with_spans = select_for_budget(
            _positions(units), 5, text_length=4000, priority_spans=spans
        )
        without = select_for_budget(_positions(units), 5, text_length=4000)
        assert any(
            u.text == "unité 27 du document" for u in with_spans.selected
        ), "le span prioritaire n'a pas été dépensé"
        assert not any(u.text == "unité 27 du document" for u in without.selected)


def _positions(units: List[str]):
    """Units spread evenly over a 4000-char text, as the state's population is."""
    from argumentation_analysis.orchestration.selection import SelectableUnit

    step = 4000 // (len(units) + 1)
    return [
        SelectableUnit(unit_id=f"u{i}", text=text, offset=(i + 1) * step)
        for i, text in enumerate(units)
    ]


# ---------------------------------------------------------------------------
# The writer records offsets, never text
# ---------------------------------------------------------------------------


class TestTheWriterKeepsOffsetsOnly:
    def test_spans_reach_the_state_and_bad_entries_are_dropped(self) -> None:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="texte neutre de remplissage.")
        from argumentation_analysis.orchestration.state_writers import (
            _write_semantic_index_to_state,
        )

        _write_semantic_index_to_state(
            {"status": "ran", "priority_spans": [[10, 20], [30, 30], "bad", [5, 4]]},
            state,
            {},
        )
        assert state.semantic_priority_spans == [(10, 20)]
        # The record holds offsets, not the passages they point at.
        assert all(isinstance(s, tuple) for s in state.semantic_priority_spans)

    def test_an_empty_output_records_nothing(self) -> None:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_semantic_index_to_state,
        )

        state = UnifiedAnalysisState(initial_text="texte neutre de remplissage.")
        _write_semantic_index_to_state(
            {"status": "skipped: no_reading_query"}, state, {}
        )
        assert state.semantic_priority_spans == []
