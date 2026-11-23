"""#3548 item 35 (R1206 re-review, comment 7087926670) — a failed KB build must not raise.

The R1205 rework left ``build_corpus_kb`` OUTSIDE the reader's ``try``: an
embedding transport failure during the build (claudish answers 404 on
``/v1/embeddings``) propagates out of ``_invoke_semantic_index`` instead of
naming itself, and costs the document its OWN spans too — the corpus reader
runs first so a skip of the spans never costs the corpus its say, but a corpus
failure must not cost the spans theirs.

Asks (coordinator R1206):
1. a transport failure in the build returns a named ``skipped: corpus_failed``
   (exception type + message) and makes no further call;
2. the document's own result (spans, or its own named skip) is still returned
   next to ``corpus_status``;
3. the failed build is remembered for the process, keyed like the KB, so the
   cycle does not retry it per document — the cached status says so;
4. a second document with a fresh context makes no new embedding call.

Seat-free: no key, no network, no real corpus — planted texts are invented.
Born red on the R1205 head (the build raises); green after the fix.
"""

from __future__ import annotations

import re
import zlib
from typing import Any, Dict, List
from urllib.error import HTTPError

import pytest

import argumentation_analysis.orchestration.invoke_callables as ic
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.opaque_id import opaque_id
from argumentation_analysis.services import semantic_retrieval as sr

_DIM = 96

_RECORDED_METADATA = {
    "discourse_type": "political",
    "era": "unknown",
    "regime_type": "unknown",
    "year_bucket": "unknown",
}


@pytest.fixture(autouse=True)
def _fresh_module_holders():
    """Neither the KB holder nor the failure holder leaks between tests."""
    for name in ("_CORPUS_KB_HOLDER", "_CORPUS_KB_FAILED"):
        holder = getattr(ic, name, None)
        if holder is not None:
            holder.clear()
    yield
    for name in ("_CORPUS_KB_HOLDER", "_CORPUS_KB_FAILED"):
        holder = getattr(ic, name, None)
        if holder is not None:
            holder.clear()


def _vector(text: str) -> List[float]:
    vec = [0.0] * _DIM
    for word in re.findall(r"[0-9a-zà-ÿ]+", text.lower()):
        vec[zlib.crc32(word.encode("utf-8")) % _DIM] += 1.0
    return vec


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
    state = UnifiedAnalysisState(initial_text=text)
    state.set_source_metadata(dict(_RECORDED_METADATA))
    state.defining_moves = {
        "moves": [{"kind": "thesis", "quote": CLAIM, "reading": "", "offset": 0}]
    }
    return state


def _phase_context(state: UnifiedAnalysisState, source: str) -> Dict[str, Any]:
    return {"_state_object": state, "analysed_document_id": opaque_id(source)}


@pytest.fixture
def failing_build_phase(monkeypatch):
    """Route declared, passphrase present, but the BUILD's embedding POST raises
    HTTPError 404 (the claudish route's real answer). The document's OWN span
    retrieval is faked separately and succeeds — so a passing phase proves the
    spans survive a corpus build failure."""
    monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
    monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://test/v1")
    monkeypatch.setenv(sr.EMBEDDING_MODEL_ENV, "fake-embed")
    monkeypatch.setenv("TEXT_CONFIG_PASSPHRASE", "test-passphrase")
    monkeypatch.setenv("OPAQUE_ID_SALT", "test-salt")

    build_calls: List[int] = []

    def _raise_404(route, texts):
        build_calls.append(len(texts))
        raise HTTPError("http://test/v1/embeddings", 404, "Not Found", None, None)  # type: ignore[arg-type]

    monkeypatch.setattr(sr, "_post_embeddings", _raise_404)
    monkeypatch.setattr(
        "argumentation_analysis.core.io_manager.load_extract_definitions",
        lambda config_file, b64_derived_key, **kwargs: _definitions(),
    )
    # The document's own span retrieval never touches the failing embedder.
    monkeypatch.setattr(
        sr,
        "retrieve_priority_spans",
        lambda text, query, route: {
            "spans": [{"start": 0, "end": 40}],
            "scores": [0.9],
            "chunks": 1,
            "ranked": 1,
        },
    )
    return build_calls


async def test_a_failed_kb_build_does_not_raise_and_names_itself(failing_build_phase):
    """Ask 1: the build raises HTTPError 404; the phase must RETURN a named
    ``skipped: corpus_failed`` (exception type + message), not propagate."""
    state = _state_for(DOC_P_TEXT)
    result = await ic._invoke_semantic_index(
        DOC_P_TEXT, _phase_context(state, "planted_p")
    )
    assert result.get("corpus_status", "").startswith("skipped: corpus_failed"), result
    reason = result.get("corpus_reason", "")
    assert "HTTPError" in reason and "404" in reason, reason


async def test_the_document_own_spans_survive_a_corpus_build_failure(
    failing_build_phase,
):
    """Ask 2: a corpus build failure must not cost the document its OWN spans —
    they are returned next to the named corpus skip."""
    state = _state_for(DOC_P_TEXT)
    result = await ic._invoke_semantic_index(
        DOC_P_TEXT, _phase_context(state, "planted_p")
    )
    assert result.get("status") == "ran", result
    assert result.get("priority_spans"), result
    assert result.get("corpus_status", "").startswith("skipped: corpus_failed")


async def test_a_failed_build_is_remembered_for_the_process(failing_build_phase):
    """Ask 3 + 4: doc_P's build fails and is remembered; doc_Q with a FRESH
    context makes NO new embedding call, and the cached status says so."""
    await ic._invoke_semantic_index(
        DOC_P_TEXT, _phase_context(_state_for(DOC_P_TEXT), "planted_p")
    )
    calls_after_first = len(failing_build_phase)
    assert calls_after_first >= 1, "the first build made no embedding call"
    result_q = await ic._invoke_semantic_index(
        DOC_Q_TEXT, _phase_context(_state_for(DOC_Q_TEXT), "planted_q")
    )
    assert (
        len(failing_build_phase) == calls_after_first
    ), "the cached failure still retried the embedding POST"
    assert result_q.get("corpus_status") == "skipped: corpus_failed (cached)", result_q
