"""#2618: the semantic_indexing phase indexes the run's arguments before
searching, and the search never returns another run's arguments.

On main the phase only called ``service.search`` — the #174 indexing half
(``index_arguments``) had no production caller, so the phase searched an
index this repository never filled. These witnesses run the real phase
against a fake Kernel Memory transport (no real service) and require, in
order: an ``/upload`` per argument (with quality and fallacy tags), a
bounded ``/upload-status`` wait, then the argument ``/search``.

The review of #2618 added the scoping requirement: every run used the
default source name ``pipeline``, so document ids collided across runs and
a run's search could return a previous run's arguments. The fake transport
here REMEMBERS uploads and answers ``/search`` from them, applying the
payload filters — the two-runs witness cannot pass on a transport with a
canned answer.

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
    """Kernel Memory endpoint double that remembers uploads and answers
    /search from what was actually uploaded, applying the payload filters."""

    def __init__(self, indexing_completes=True, status_probe_fails=False):
        self.calls = []
        self.docs = {}
        self._indexing_completes = indexing_completes
        self._status_probe_fails = status_probe_fails
        self._uploaded_tags = []

    def get(self, url, headers=None, timeout=None, params=None):
        self.calls.append(("GET", url, dict(params or {})))
        if url.endswith("/health"):
            return _FakeResponse({"ok": True})
        if url.endswith("/upload-status"):
            if self._status_probe_fails:
                raise RuntimeError("probe failed (simulated 500)")
            done = self._indexing_completes
            payload = (
                {"completed": done, "index": "default"}
                if done
                else {"completed": False}
            )
            return _FakeResponse(payload)
        raise AssertionError(f"unexpected GET {url}")

    def post(self, url, files=None, data=None, json=None, headers=None, timeout=None):
        self.calls.append(("POST", url, {"json": json, "data": dict(data or {})}))
        if url.endswith("/upload"):
            tags = list((data or {}).get("tags", []))
            self._uploaded_tags.extend(tags)
            doc_id = (data or {}).get("documentId", "doc")
            text = ""
            file_entry = (files or {}).get("file1")
            if file_entry is not None:
                text = file_entry[1].read().decode("utf-8")
            self.docs[doc_id] = {"text": text, "tags": tags}
            return _FakeResponse({"docId": doc_id})
        if url.endswith("/search"):
            matched = self._filter_docs(json or {})
            return _FakeResponse(
                {
                    "results": [
                        {
                            "documentId": doc_id,
                            "sourceName": "pipeline",
                            "tags": {"tags": meta["tags"]},
                            "partitions": [{"text": meta["text"], "relevance": 0.9}],
                        }
                        for doc_id, meta in matched
                    ]
                }
            )
        raise AssertionError(f"unexpected POST {url}")

    def _filter_docs(self, payload):
        filters = payload.get("filters", [])
        matched = []
        for doc_id, meta in self.docs.items():
            if self._tags_match_filters(meta["tags"], filters):
                matched.append((doc_id, meta))
        return matched[: payload.get("limit", 5)]

    @staticmethod
    def _tags_match_filters(tags, filters):
        """Port of Kernel Memory ``TagsMatchFilters`` (SimpleVectorDb /
        SimpleTextDb): OR across filter objects, AND across conditions
        inside one object, AND across the listed values of one key — the
        real server's semantics, not a simplification of them (#2698
        re-review: the previous AND-everything merge certified a request
        shape a real KM answers differently)."""
        if not filters:
            return True
        tag_set = set(tags)
        for f in filters:
            match = True
            for key, values in f.items():
                for v in values:
                    if f"{key}:{v}" not in tag_set:
                        match = False
                        break
                if not match:
                    break
            if match:
                return True
        return False


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
                # Real producer shape (#2744): the descent attaches the
                # target under ``target_argument`` + a quote anchor — not
                # ``target_argument_id``, which this payload never carries.
                {
                    "type": "appelautorite",
                    "target_argument": "arg_2",
                    "problematic_quote": "argument synthetique deux",
                }
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

    run_name = ic._run_source_name("requete synthetique")
    assert result["status"] == "ran"
    assert result["source_name"] == run_name
    assert result["indexed_count"] == 2
    assert result["arguments_seen"] == 2
    assert result["indexing"]["completed"] == 2
    assert result["indexing"]["timed_out"] is False
    assert result["indexing"]["timeout_seconds"] == ic._KM_INDEXING_WAIT_TIMEOUT

    joined_tags = " ".join(transport._uploaded_tags)
    assert "chunk_type:argument" in joined_tags
    assert "quality_level:high" in joined_tags
    assert "quality_level:low" in joined_tags
    # #2744: the producer's ``target_argument=arg_2`` must reach the indexed
    # tags — searchable via fallacy_type/has_fallacy on this same run.
    assert "fallacy_type:appelautorite" in joined_tags
    assert "has_fallacy:true" in joined_tags
    assert "has_fallacy:false" in joined_tags

    assert result["results"][0]["id"] == f"{run_name}__arg_1"
    assert result["results"][0]["snippet"] == "argument synthetique un assez long"


async def test_two_runs_do_not_cross_contaminate():
    """Review #2618: run B (1 argument) must never receive run A's (2
    arguments) documents — the search is scoped to the run's source_name."""
    transport = _FakeKMTransport()
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        run_a = await ic._invoke_semantic_index("texte du document A", _context())
        run_b = await ic._invoke_semantic_index(
            "texte du document B",
            {
                "phase_extract_output": {
                    "arguments": [
                        {"text": "argument seul du document B", "source_quote": "qB"}
                    ]
                }
            },
        )

    assert run_a["source_name"] != run_b["source_name"]
    b_ids = set(run_b["indexed_document_ids"])
    assert len(b_ids) == 1
    a_ids = set(run_a["indexed_document_ids"])
    assert not (a_ids & b_ids), "ids de documents partages entre deux runs"

    returned_ids = [r["id"] for r in run_b["results"]]
    assert returned_ids, "la recherche du run B ne retourne rien"
    message = (
        f"la recherche du run B retourne des documents d'un autre run: {returned_ids}"
    )
    assert set(returned_ids) <= b_ids, message

    assert a_ids <= set(transport.docs), (
        "les documents du run A ont disparu du transport: l'absence vient du "
        "scope, pas de l'absence de donnees"
    )


def test_fallacy_type_filter_excludes_untagged_arguments():
    """#2698 re-review: on a real Kernel Memory, one criterion per filter
    object is ORed with the others, so ``fallacy_type=X`` alone let every
    ``chunk_type:argument`` through. This witness uploads two argument
    chunks, only one carrying the fallacy tag, and requires the tagged
    one alone to come back."""
    from argumentation_analysis.services.semantic_index_service import (
        SemanticIndexService,
    )

    transport = _FakeKMTransport()
    transport.docs["doc_tagged"] = {
        "text": "argument taggue ad hominem",
        "tags": ["chunk_type:argument", "fallacy_type:ad_hominem"],
    }
    transport.docs["doc_clean"] = {
        "text": "argument sans sophisme",
        "tags": ["chunk_type:argument"],
    }
    service = SemanticIndexService(km_url="http://test:9001")
    with patch.object(service, "_get_requests", return_value=transport):
        results = service.search_arguments(query="argument", fallacy_type="ad_hominem")

    returned = {r.document_id for r in results}
    assert returned == {
        "doc_tagged"
    }, f"le filtre fallacy_type laisse passer des arguments non taggues: {returned}"


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
    assert result["arguments_seen"] == 0
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
    assert result["indexing"]["probe_errors"] == 0
    assert _first(transport, "POST", "/search") is not None


async def test_failing_status_probe_is_not_silent_timeout(monkeypatch):
    """Review #2618 (note): a probe that raises is counted, not read as a
    plain timeout."""
    monkeypatch.setattr(ic, "_KM_INDEXING_WAIT_TIMEOUT", 0.2)
    monkeypatch.setattr(ic, "_KM_INDEXING_POLL_INTERVAL", 0.05)
    transport = _FakeKMTransport(status_probe_fails=True)
    with patch(
        "argumentation_analysis.services.semantic_index_service.SemanticIndexService._get_requests",
        return_value=transport,
    ):
        result = await ic._invoke_semantic_index("requete synthetique", _context())

    assert result["indexing"]["probe_errors"] > 0
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
