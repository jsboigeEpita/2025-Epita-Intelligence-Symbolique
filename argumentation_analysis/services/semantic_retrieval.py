"""Corpus retrieval for the analysed document (#3387 repoint).

The semantic-index phase used to index the run's OWN extracted arguments and
search them back, filtered on the run's namespace (measured in R1300: no
corpus was ever indexed, and nothing outside the writer read the refs). The
repoint decided on 2026-11-05 indexes the document under analysis instead —
``chunk_by_arguments`` over its own text — and answers the run's question:
the central thesis the first reading named (#3415).

Privacy (CLAUDE.md "Dataset Privacy Discipline", rules 1, 4, 5 and 7):

- nothing decrypted is persisted: chunks, vectors and spans live in memory for
  the duration of one phase call and are dropped with it (shape A of the
  design note, ``docs/proposals/SEMANTIC_INDEX_REPOINT_3387.md``);
- the phase never writes document text into a tracked file or a commit; this
  module returns OFFSETS into the text the caller already holds, so the state
  records where to look, not what is there.

The only external requirement is an OpenAI-compatible ``/v1/embeddings``
endpoint. Its **key and base URL are read as a PAIR from one source**
(decision 2, the rule #3414 established for the judge): a key from one place
and a URL from another is how a run silently points at the wrong host. The
default source is the pipeline's own provider route
(``llm_service.resolve_chat_endpoint``), which is a PAID route — this module
makes no "free" claim; a dedicated endpoint is declared as a pair and used
alone.
"""

from __future__ import annotations

import json
import logging
import math
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

#: Default embedding model when the route does not name one. Declared here
#: once so the phase, the tests and the docs cannot spell three defaults.
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

#: The dedicated-endpoint pair. Both or neither: half a pair is not a route
#: (see :func:`resolve_embedding_route`), and the caller names the reason.
EMBEDDING_KEY_ENV = "SEMANTIC_INDEX_EMBEDDING_API_KEY"
EMBEDDING_URL_ENV = "SEMANTIC_INDEX_EMBEDDING_BASE_URL"
EMBEDDING_MODEL_ENV = "SEMANTIC_INDEX_EMBEDDING_MODEL"

#: Chunks per HTTP call. A document's own text yields a few hundred chunks at
#: panel scale; batching keeps the request body bounded.
EMBED_BATCH_SIZE = 32

#: How many spans the phase hands the budget selector. Small on purpose: the
#: selector keeps its own budget, and a hint that names half the document
#: stops being a hint.
DEFAULT_TOP_K = 5


@dataclass(frozen=True)
class EmbeddingRoute:
    """Where to embed, and which source said so.

    ``source`` is written into the phase output so a run can say whether it
    spent the provider route or a declared local endpoint. It is a fact about
    the run, never a claim that the call was free.
    """

    api_key: str
    base_url: str
    model: str
    source: str


@dataclass(frozen=True)
class Chunk:
    """One in-memory chunk: its span in the document, and its text."""

    start: int
    end: int
    text: str


def resolve_embedding_route() -> Tuple[Optional[EmbeddingRoute], str]:
    """Resolve the embedding route, or name why there is none.

    Returns ``(route, reason)``. ``reason`` is ``""`` when a route exists and
    otherwise names the absent source — an honest skip, never a silent one.

    The dedicated pair wins when both halves are set; half a pair is refused
    rather than completed from the other source (that completion is exactly
    the key-here-URL-there drift #3414 removed).
    """
    key = (os.environ.get(EMBEDDING_KEY_ENV) or "").strip()
    url = (os.environ.get(EMBEDDING_URL_ENV) or "").strip()
    model = (
        os.environ.get(EMBEDDING_MODEL_ENV) or ""
    ).strip() or DEFAULT_EMBEDDING_MODEL
    if key and url:
        return EmbeddingRoute(key, url.rstrip("/"), model, "declared"), ""
    if key or url:
        missing = EMBEDDING_URL_ENV if key else EMBEDDING_KEY_ENV
        return (
            None,
            (
                f"{EMBEDDING_KEY_ENV} and {EMBEDDING_URL_ENV} are a PAIR read "
                f"from one source: {missing} is unset while its half is set "
                "(a key from one place and a URL from another is how a run "
                "points at the wrong host)"
            ),
        )
    # Default: the pipeline's provider route — one resolver, so key and URL
    # come from the same declaration.
    from argumentation_analysis.core.llm_service import resolve_chat_endpoint

    api_key, base_url, _chat_model = resolve_chat_endpoint()
    if not api_key:
        return None, "no embedding route: no provider key and no declared pair"
    return EmbeddingRoute(api_key, base_url.rstrip("/"), model, "provider"), ""


def _post_embeddings(route: EmbeddingRoute, texts: Sequence[str]) -> List[List[float]]:
    """One ``/v1/embeddings`` call. Raises on transport or shape failure."""
    body = json.dumps({"model": route.model, "input": list(texts)}).encode("utf-8")
    request = urllib.request.Request(
        f"{route.base_url}/embeddings",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {route.api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(
        request, timeout=60
    ) as response:  # noqa: S310 — the route is configured, not user input
        payload = json.loads(response.read().decode("utf-8"))
    data = payload.get("data")
    if not isinstance(data, list) or len(data) != len(texts):
        raise ValueError(
            "embeddings endpoint returned %s vectors for %d inputs"
            % (len(data) if isinstance(data, list) else "no", len(texts))
        )
    vectors: List[List[float]] = []
    for item in data:
        vector = item.get("embedding") if isinstance(item, dict) else None
        if not isinstance(vector, list) or not vector:
            raise ValueError("embeddings endpoint returned an empty vector")
        vectors.append([float(x) for x in vector])
    return vectors


def embed_texts(texts: Sequence[str], route: EmbeddingRoute) -> List[List[float]]:
    """Embed every text, in bounded batches, preserving input order."""
    vectors: List[List[float]] = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = list(texts[start : start + EMBED_BATCH_SIZE])
        vectors.extend(_post_embeddings(route, batch))
    return vectors


def chunk_spans(text: str) -> List[Chunk]:
    """Chunk the document's own text, with the span of each chunk.

    Reuses the existing ``chunk_by_arguments`` chunker (its sentence fallback
    answers for a document with no fact-extraction output) rather than
    introducing a second splitter. The chunker returns stripped strings, so
    the span is recovered by walking a cursor through the source: a chunk the
    text does not carry verbatim has no span and is dropped — an offset that
    does not point at the quote is worse than no offset.
    """
    from argumentation_analysis.services.semantic_index_service import (
        SemanticIndexService,
    )

    raw = SemanticIndexService.chunk_by_arguments(text)
    chunks: List[Chunk] = []
    cursor = 0
    for item in raw:
        chunk_text = str(item.get("text") or "").strip()
        if not chunk_text:
            continue
        start = text.find(chunk_text, cursor)
        if start < 0:
            start = text.find(chunk_text)
        if start < 0:
            continue
        end = start + len(chunk_text)
        chunks.append(Chunk(start=start, end=end, text=chunk_text))
        cursor = max(cursor, end)
    return chunks


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    norm = math.sqrt(sum(a * a for a in left)) * math.sqrt(sum(b * b for b in right))
    return dot / norm if norm else 0.0


def retrieve_priority_spans(
    document_text: str,
    query: str,
    route: EmbeddingRoute,
    top_k: int = DEFAULT_TOP_K,
) -> Dict[str, Any]:
    """Rank the document's chunks against the run's question.

    Returns the ``(start, end)`` spans of the best chunks, their scores, and
    the population they were chosen from — what the caller needs to record
    honestly, and nothing that carries the document's text.
    """
    chunks = chunk_spans(document_text)
    if not chunks:
        return {
            "spans": [],
            "scores": [],
            "chunks": 0,
            "ranked": 0,
            "reason": "the document yielded no chunk",
        }
    vectors = embed_texts([c.text for c in chunks] + [query], route)
    query_vector = vectors[-1]
    scored = sorted(
        (
            (_cosine(vector, query_vector), index)
            for index, vector in enumerate(vectors[:-1])
        ),
        key=lambda pair: (-pair[0], pair[1]),
    )
    top = scored[: max(0, top_k)]
    return {
        "spans": [[chunks[i].start, chunks[i].end] for _, i in top],
        "scores": [round(score, 4) for score, _ in top],
        "chunks": len(chunks),
        "ranked": len(scored),
        "reason": "",
    }
