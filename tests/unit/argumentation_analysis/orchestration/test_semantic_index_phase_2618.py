"""#2618 service witnesses — kept after the #3387 repoint retired the phase.

What the phase used to do (index the run's own extracted arguments through
Kernel Memory, wait for indexing, search them back under a run-scoped source
name) was measured inert in R1300: no corpus was ever indexed, and nothing
outside the writer read the refs. The 2026-11-05 decision (#3387) repointed
the phase to the analysed document's own text; its contract lives in
``test_semantic_repoint_3387.py``.

The PHASE witnesses of #2618 are therefore RETIRED with the behaviour they
certified — an honest removal, not a burial: the requirement they encoded
("the run never returns another run's content") is now structural, since v1
keeps nothing between runs.

What stays here is the Kernel Memory adapter, which the decision keeps: it is
the student project's surface, and only its default changed. These witnesses
exercise ``SemanticIndexService`` directly, with a fake transport that applies
Kernel Memory's real tag-filter semantics.
"""

import pytest
from unittest.mock import patch

import argumentation_analysis.orchestration.invoke_callables as ic  # noqa: F401 — the module the retired phase lived in


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


def test_wait_for_indexing_polling_is_gone():
    """#2346/#2618: le polling fixe ``time.sleep`` n'existe plus — la boucle
    bornée vit dans la phase (asyncio.sleep), le service n'expose qu'une
    sonde mono-requête."""
    from argumentation_analysis.services.semantic_index_service import (
        SemanticIndexService,
    )

    assert not hasattr(SemanticIndexService, "wait_for_indexing")
    assert hasattr(SemanticIndexService, "indexing_status")


@pytest.mark.parametrize(
    "removed",
    [
        "_wait_km_indexing_bounded",
        "_KM_INDEXING_WAIT_TIMEOUT",
        "_KM_INDEXING_POLL_INTERVAL",
        "_run_source_name",
        "_belief_premises",
    ],
)
def test_the_retired_phase_helpers_are_gone(removed):
    """#3387 — the KM indexing wait and the run-scoped source name had no
    caller outside the old phase; the repoint removed them rather than
    leaving a second, unread path (anti-pendulum: subtract)."""
    assert not hasattr(ic, removed), (
        f"{removed} survit au retrait de la phase qu'il servait: la boucle "
        "d'indexation KM n'a plus d'appelant"
    )
