"""#3548 wiring (R1203 dispatch, item 35, rework R1205) — a phase ANSWERS corpus_matches.

#3664 delivered the reader (`build_corpus_kb`, `query_corpus_for_claim`,
`corpus_claim_from_state`) but no production call. This witness drives the REAL
phase (`_invoke_semantic_index`) with a fake loader and a fake
``_post_embeddings``: doc_P's claim records doc_Q's span in
``semantic_index_refs``.

R1205 rework: the analysed document's id travels by the CONTEXT key the batch
runner plants (``analysed_document_id``), never by ``source_metadata`` — the
407 recorded ``state_full_*.json`` carry no ``source_name`` there, and Act I
renders every key of that block. The states below use the RECORDED shape
(classifier fields only), and a missing id names itself instead of querying.

Seat-free: no key, no network, no real corpus — the planted texts are invented.
The KB is built ONCE PER PROCESS (a module-level holder, reset by the fixture),
the per-document exclusion is applied at query time, and the held vectors are
compact float32 arrays.
"""

from __future__ import annotations

import re
import zlib
from array import array
from typing import Any, Dict, List

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.opaque_id import opaque_id
from argumentation_analysis.orchestration.state_writers import (
    _write_semantic_index_to_state,
)
from argumentation_analysis.services import semantic_retrieval as sr

_DIM = 96

#: The shape the 407 recorded panel states actually carry in source_metadata:
#: the classifier's fields — no source_name, no opaque id (measured, R1205).
_RECORDED_METADATA = {
    "discourse_type": "political",
    "era": "unknown",
    "regime_type": "unknown",
    "year_bucket": "unknown",
}


@pytest.fixture(autouse=True)
def _fresh_module_holder():
    """The module-level KB holder never leaks between tests. Defensive: on a
    head without the holder (born-red measurement), nothing to clear."""
    holder = getattr(ic, "_CORPUS_KB_HOLDER", None)
    if holder is not None:
        holder.clear()
    yield
    if holder is not None:
        holder.clear()


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


def _state_for(text: str) -> UnifiedAnalysisState:
    """A state shaped like the RECORDED panel states: classifier metadata only."""
    state = UnifiedAnalysisState(initial_text=text)
    state.set_source_metadata(dict(_RECORDED_METADATA))
    state.defining_moves = {
        "moves": [{"kind": "thesis", "quote": CLAIM, "reading": "", "offset": 0}]
    }
    return state


def _state_for_doc_p() -> UnifiedAnalysisState:
    return _state_for(DOC_P_TEXT)


def _state_for_doc_q() -> UnifiedAnalysisState:
    return _state_for(DOC_Q_TEXT)


def _phase_context(state: UnifiedAnalysisState, source: str) -> Dict[str, Any]:
    """The context production gives the phase: the state object PLUS the
    analysed document's opaque id, planted by the batch runner (#3548)."""
    return {
        "_state_object": state,
        "analysed_document_id": opaque_id(source),
    }


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
    span in the state's semantic_index_refs — with the RECORDED state shape."""
    state = _state_for_doc_p()
    result = await ic._invoke_semantic_index(
        DOC_P_TEXT, _phase_context(state, "planted_p")
    )
    assert result.get("corpus_status") == "ran"
    matches = result.get("corpus_matches")
    assert matches, "the phase answered no corpus_matches — the reader is unwired"
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
    """R1205: source_metadata carries NO source_name (the recorded shape); the
    exclusion must come from the context id, or the document answers itself."""
    state = _state_for_doc_p()
    result = await ic._invoke_semantic_index(
        DOC_P_TEXT, _phase_context(state, "planted_p")
    )
    doc_p_id = opaque_id("planted_p")
    for match in result.get("corpus_matches") or []:
        assert not str(match["doc"]).startswith(doc_p_id)


async def test_an_ext_suffixed_context_id_excludes_the_base_document(wired_phase):
    """The batch runner names an extract ``<base>_ext<N>``; the KB keys the
    SOURCE by its base id. The suffix must reduce, or the exclusion is inert."""
    state = _state_for_doc_p()
    context = _phase_context(state, "planted_p")
    context["analysed_document_id"] += "_ext1"
    result = await ic._invoke_semantic_index(DOC_P_TEXT, context)
    assert result.get("corpus_status") == "ran", result
    answered_by = sorted({str(m["doc"]) for m in result.get("corpus_matches") or []})
    assert opaque_id("planted_p") not in answered_by, answered_by
    assert opaque_id("planted_q") in answered_by, answered_by


async def test_one_kb_serves_both_documents_of_a_cycle(wired_phase):
    """The review witness (R1204, comment 7075013167): doc_P then doc_Q through
    the REAL phase, each with a FRESH context — as production gives it, since
    WorkflowExecutor copies the context per document. Exactly ONE loader
    call; doc_Q's run never answers doc_Q; doc_Q's run CAN answer doc_P."""
    await ic._invoke_semantic_index(
        DOC_P_TEXT, _phase_context(_state_for_doc_p(), "planted_p")
    )
    result_q = await ic._invoke_semantic_index(
        DOC_Q_TEXT, _phase_context(_state_for_doc_q(), "planted_q")
    )
    assert result_q.get("corpus_status") == "ran", result_q
    assert len(wired_phase) == 1, f"loader called {len(wired_phase)} times"
    doc_p_id = opaque_id("planted_p")
    doc_q_id = opaque_id("planted_q")
    matches = result_q.get("corpus_matches") or []
    answered_by = sorted({str(m["doc"]) for m in matches})
    assert doc_q_id not in answered_by, f"doc_Q answered its own query: {answered_by}"
    assert (
        doc_p_id in answered_by
    ), f"doc_Q's run cannot see doc_P any more: {answered_by}"


async def test_a_missing_passphrase_names_itself_and_makes_no_call(
    wired_phase, monkeypatch
):
    monkeypatch.delenv("TEXT_CONFIG_PASSPHRASE")
    state = _state_for_doc_p()
    result = await ic._invoke_semantic_index(
        DOC_P_TEXT, _phase_context(state, "planted_p")
    )
    assert result["corpus_status"] == "skipped: no_corpus_key"
    assert wired_phase == []


async def test_a_document_without_a_claim_skips_the_reader(wired_phase):
    """No strategist claim and no thesis: the reader names the absence and
    loads nothing (driven directly — the phase's own no_reading_query guard
    would return first)."""
    state = UnifiedAnalysisState(initial_text=DOC_P_TEXT)
    state.set_source_metadata(dict(_RECORDED_METADATA))
    state.defining_moves = {"moves": [{"kind": "pivot", "quote": "", "reading": ""}]}
    route = sr.EmbeddingRoute("k", "http://test/v1", "fake-embed", "declared")
    corpus = await ic._corpus_second_reader(
        state, {"analysed_document_id": opaque_id("planted_p")}, route
    )
    assert corpus["status"] == "skipped: no_corpus_claim"
    assert wired_phase == []


async def test_a_missing_analysed_id_names_itself_and_makes_no_query(wired_phase):
    """R1205 ask 2: with no analysed id, the KB would answer the document's own
    claim — the reader must refuse by name, not run silently. The state keeps
    the RECORDED shape (no source_name to rescue the exclusion)."""
    state = _state_for_doc_p()
    result = await ic._invoke_semantic_index(DOC_P_TEXT, {"_state_object": state})
    assert result["corpus_status"] == "skipped: no_analysed_id", result
    assert "corpus_matches" not in result
    assert wired_phase == []


def test_the_held_vectors_are_compact_float32(wired_phase):
    """R1205 ask 4: 31k chunks x 1536 dims as Python float tuples compute to
    about 1.5 GB held for the process; ``array('f')`` holds the same vectors
    in about a tenth of that."""
    route = sr.EmbeddingRoute("k", "http://test/v1", "fake-embed", "declared")
    definitions = _definitions()
    for definition, name in zip(definitions, ("planted_p", "planted_q")):
        definition["id"] = opaque_id(name)
    entries, reason = sr.build_corpus_kb(definitions, route)
    assert entries and reason == "", reason
    assert all(isinstance(entry.vector, array) for entry in entries)
    assert all(entry.vector.typecode == "f" for entry in entries)
