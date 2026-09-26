"""#2618: the semantic_indexing phase indexes the run's arguments before
searching.

On main the phase only called ``service.search`` — the #174 indexing half
(``index_arguments``) had no production caller, so the phase searched an
index this repository never filled. These witnesses run the real phase
against a fake Kernel Memory transport (no real service) and require, in
order: an ``/upload`` per argument (with quality and fallacy tags), a
bounded ``/upload-status`` wait, then the argument ``/search``.

Fixtures use opaque ids and synthetic text only (privacy: indexed payloads
stay local to the KM instance).
"""

import pytest
from unittest.mock import patch

import argumentation_analysis.orchestration.invoke_callables as ic


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeKMTransport:
    """Records the ordered call log a Kernel Memory endpoint would see."""

    def __init__(self, indexing_completes=True):
        self.calls = []
        self._indexing_completes = indexing_completes
        self._uploaded_tags = []

    def get(self, url, headers=None, timeout=None, params=None):
        self.calls.append(("GET", url, dict(params or {})))
        if url.endswith("/health"):
            return _FakeResponse({"ok": True})
        if url.endswith("/upload-status"):
            done = self._indexing_completes
            payload = (
                {"completed": done, "index": "default"}
                if done
                else {"completed": False}
            )
            return _FakeResponse(payload)
        raise AssertionError(f"unexpected GET {url}")

    def post(self, url, files=None, data=None, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url, {"json": json, "data": data}))
        if url.endswith("/upload"):
            tags = list((data or {}).get("tags", []))
            self._uploaded_tags.extend(tags)
            doc_id = (data or {}).get("documentId", "doc")
            return _FakeResponse({"docId": doc_id})
        if url.endswith("/search"):
            return _FakeResponse(
                {
                    "results": [
                        {
                            "documentId": "pipeline__arg_1",
                            "sourceName": "pipeline",
                            "tags": {"tags": ["chunk_type:argument"]},
                            "partitions": [
                                {"text": "argument synthetique un", "relevance": 0.9}
                            ],
                        }
                    ]
                }
            )
        raise AssertionError(f"unexpected POST {url}")


_ARGS = [
    {"text": "argument synthetique un assez long", "source_quote": "quote1"},
    {"text": "argument synthetique deux assez long", "source_quote": "quote2"},
]


def _context():
    return {
        "phase_extract_output": {"arguments": [dict(a) for a in _ARGS]},
        "phase_quality_output": {
            "per_argument_scores": {
                "arg_1": {
                    "note_finale": 0.8,
                    "scores_par_vertu": {"clarte": 0.9, "refutation_constructive": 0.4},
                },
                "arg_2": {"note_finale": 0.3, "scores_par_vertu": {"clarte": 0.2}},
            }
        },
        "phase_hierarchical_fallacy_output": {
            "fallacies": [
                {"target_argument_id": "arg_2", "fallacy_type": "appelautorite"}
            ]
        },
    }


def _first(transport, method, suffix):
    for i, (m, url, _) in enumerate(transport.calls):
        if m == method and url.endswith(suffix):
            return i
    return None


async def test_phase_indexes_arguments_before_searching():
    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        result = await ic._invoke_semantic_index("requete synthetique", _context())

    first_upload = _first(transport, "POST", "/upload")
    first_status = _first(transport, "GET", "/upload-status")
    first_search = _first(transport, "POST", "/search")
    assert first_upload is not None, "aucun upload: la phase n'indexe pas"
    assert first_search is not None
    assert first_upload < first_search, "la recherche precede l'indexation"
    assert first_status is not None and first_upload < first_status < first_search

    assert result["status"] == "ran"
    assert result["indexed_count"] == 2
    assert result["indexing"]["completed"] == 2
    assert result["indexing"]["timed_out"] is False
    assert result["indexing"]["timeout_seconds"] == ic._KM_INDEXING_WAIT_TIMEOUT

    joined_tags = " ".join(transport._uploaded_tags)
    assert "chunk_type:argument" in joined_tags
    assert "quality_level:high" in joined_tags
    assert "quality_level:low" in joined_tags
    assert "fallacy_type:appelautorite" in joined_tags

    assert result["results"][0]["id"] == "pipeline__arg_1"
    assert result["results"][0]["snippet"] == "argument synthetique un"


async def test_phase_without_arguments_still_searches():
    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        result = await ic._invoke_semantic_index("requete synthetique", {})

    assert _first(transport, "POST", "/upload") is None
    assert _first(transport, "POST", "/search") is not None
    assert result["status"] == "ran"
    assert result["indexed_count"] == 0
    assert result["indexing"]["total"] == 0
    assert result["indexing"]["timed_out"] is False


async def test_indexing_wait_is_bounded_and_named(monkeypatch):
    monkeypatch.setattr(ic, "_KM_INDEXING_WAIT_TIMEOUT", 0.2)
    monkeypatch.setattr(ic, "_KM_INDEXING_POLL_INTERVAL", 0.05)
    transport = _FakeKMTransport(indexing_completes=False)
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        result = await ic._invoke_semantic_index("requete synthetique", _context())

    assert result["status"] == "ran"
    assert result["indexing"]["timed_out"] is True
    assert result["indexing"]["completed"] == 0
    assert result["indexing"]["timeout_seconds"] == 0.2
    assert _first(transport, "POST", "/search") is not None


def test_wait_for_indexing_polling_is_gone():
    """#2346/#2618: le polling fixe ``time.sleep`` n'existe plus — la boucle
    bornée vit dans la phase (asyncio.sleep), le service n'expose qu'une
    sonde mono-requête."""
    from argumentation_analysis.services.semantic_index_service import (
        SemanticIndexService,
    )

    assert not hasattr(SemanticIndexService, "wait_for_indexing")
    assert hasattr(SemanticIndexService, "indexing_status")
