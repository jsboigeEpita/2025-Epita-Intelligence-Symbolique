"""#3548 wiring (R1203 dispatch, item 35) — a phase ANSWERS corpus_matches.

#3664 delivered the reader (`build_corpus_kb`, `query_corpus_for_claim`,
`corpus_claim_from_state`) but no production call: `git grep` on the merged
head found them called only from tests. This witness drives the REAL phase
(`_invoke_semantic_index`) with a fake loader and a fake `_post_embeddings`:
doc_P's claim records doc_Q's span in `semantic_index_refs` — the producer
reaches the state, one hop past where #3664 stopped.

Seat-free: no key, no network, no real corpus — the planted texts are invented.
The KB is built ONCE PER PROCESS (a context-level holder), never per document.
"""

from __future__ import annotations

import re
import zlib
from types import SimpleNamespace
from typing import Any, Dict, List, Sequence

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_semantic_index_to_state,
)
from argumentation_analysis.services import semantic_retrieval as sr

_DIM = 96


def _vector(text: str) -> List[float]:
    vec = [0.0] * _DIM
    for word in re.findall(r"[0-9a-zà-ÿ]+", text.lower()):
        vec[zlib.crc32(word.encode("utf-8")) % _DIM] += 1.0
    return vec


#: Invented planted texts (same fixture family as test_semantic_corpus_reader).
CLAIM = (
    "les transports en commun gratuits se financeraient eux-mêmes par la baisse "
    "de l'entretien des routes"
)
DOC_P_TEXT = (
    "Notre groupe l'affirme sans détour : des transports en commun gratuits dans "
    "toute l'agglomération se financeraient eux-mêmes. La baisse de la circulation "
    "réduirait l'entretien des routes, et cette économie compenserait la "
    "disparition des billets dès la première année."
)
DOC_Q_TEXT = (
    "Le conseil municipal a adopté trois motions hier soir, dont une sur la voirie. "
    "Une élue de la majorité a défendu des transports en commun gratuits : selon son "
    "calcul, la baisse du trafic paierait l'entretien des routes, moins usées, et la "
    "disparition du ticket suivrait. L'opposition a demandé une étude chiffrée avant "
    "tout arbitrage budgétaire, le maire ayant promis un débat en séance publique."
)


def _definitions() -> List[Dict[str, Any]]:
    return [
        {"source_name": "planted_p", "full_text": DOC_P_TEXT},
        {"source_name": "planted_q", "full_text": DOC_Q_TEXT},
    ]


def _state_for_doc_p() -> UnifiedAnalysisState:
    state = UnifiedAnalysisState(initial_text=DOC_P_TEXT)
    state.set_source_metadata({"source_name": "planted_p"})
    state.defining_moves = {
        "moves": [{"kind": "thesis", "quote": CLAIM, "reading": "", "offset": 0}]
    }
    return state


def _fake_loader(calls):
    def _load(config_file, b64_derived_key, **kwargs):
        calls.append(str(config_file))
        return _definitions()

    return _load


@pytest.fixture
def wired_phase(monkeypatch):
    """Route declared, embedder faked, loader faked, passphrase present."""
    monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
    monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://test/v1")
    monkeypatch.setenv(sr.EMBEDDING_MODEL_ENV, "fake-embed")
    monkeypatch.setenv("TEXT_CONFIG_PASSPHRASE", "test-passphrase")
    monkeypatch.setenv("OPAQUE_ID_SALT", "test-salt")
    monkeypatch.setattr(
        sr, "_post_embeddings", lambda route, texts: [_vector(t) for t in texts]
    )
    loader_calls: List[str] = []
    monkeypatch.setattr(
        "argumentation_analysis.core.io_manager.load_extract_definitions",
        _fake_loader(loader_calls),
    )
    return loader_calls


async def test_doc_qs_span_reaches_semantic_index_refs(wired_phase):
    """The DoD witness: a run of the phase on doc_P's claim records doc_Q's
    span in the state's semantic_index_refs. Red on main: no producer."""
    state = _state_for_doc_p()
    result = await ic._invoke_semantic_index(DOC_P_TEXT, {"_state_object": state})
    assert result.get("corpus_status") == "ran"
    matches = result.get("corpus_matches")
    assert matches, "the phase answered no corpus_matches — the reader is unwired"
    from argumentation_analysis.evaluation.opaque_id import opaque_id

    doc_q_id = opaque_id("planted_q")
    hit = next((m for m in matches if m["doc"] == doc_q_id), None)
    assert hit is not None, f"doc_Q's span absent from {matches}"
    # The producer's output reaches the state through the existing writer.
    _write_semantic_index_to_state(result, state, {})
    refs = state.get_state_snapshot(summarize=False).get("semantic_index_refs")
    assert refs and any(
        r.get("document_id") == doc_q_id for r in refs
    ), f"doc_Q's ref not in the state: {refs}"


async def test_the_analysed_document_never_answers_its_own_query(wired_phase):
    state = _state_for_doc_p()
    result = await ic._invoke_semantic_index(DOC_P_TEXT, {"_state_object": state})
    from argumentation_analysis.evaluation.opaque_id import opaque_id

    doc_p_id = opaque_id("planted_p")
    for match in result.get("corpus_matches") or []:
        assert not str(match["doc"]).startswith(doc_p_id)


async def test_the_kb_is_built_once_per_process(wired_phase):
    """Two phase calls, one loader call: the KB rides the context holder."""
    state = _state_for_doc_p()
    context: Dict[str, Any] = {"_state_object": state}
    await ic._invoke_semantic_index(DOC_P_TEXT, context)
    await ic._invoke_semantic_index(DOC_P_TEXT, context)
    assert len(wired_phase) == 1, f"loader called {len(wired_phase)} times"


async def test_a_missing_passphrase_names_itself_and_makes_no_call(
    wired_phase, monkeypatch
):
    monkeypatch.delenv("TEXT_CONFIG_PASSPHRASE")
    state = _state_for_doc_p()
    result = await ic._invoke_semantic_index(DOC_P_TEXT, {"_state_object": state})
    assert result["corpus_status"] == "skipped: no_corpus_key"
    assert wired_phase == []


async def test_a_document_without_a_claim_skips_the_reader(wired_phase):
    """No strategist claim and no thesis: the reader names the absence and
    loads nothing (driven directly — the phase's own no_reading_query guard
    would return first)."""
    state = UnifiedAnalysisState(initial_text=DOC_P_TEXT)
    state.set_source_metadata({"source_name": "planted_p"})
    state.defining_moves = {"moves": [{"kind": "pivot", "quote": "", "reading": ""}]}
    route = sr.EmbeddingRoute("k", "http://test/v1", "fake-embed", "declared")
    corpus = await ic._corpus_second_reader(state, {}, route)
    assert corpus["status"] == "skipped: no_corpus_claim"
    assert wired_phase == []
