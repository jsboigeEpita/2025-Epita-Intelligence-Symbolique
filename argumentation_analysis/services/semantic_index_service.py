"""
Semantic Index Service — adapter for Arg_Semantic_Index student project.

Wraps the Kernel Memory HTTP client (km_client.py) from the student
project to provide document indexing, semantic search, and RAG-based
question answering through the argumentation_analysis framework.

Endpoints and API keys are configurable via constructor params or
environment variables (no hardcoded values).

Dependencies:
  - requests (HTTP client)
  - A running Kernel Memory service (Docker or standalone)

Integration from student project Arg_Semantic_Index (GitHub #50).
"""

import logging
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

DEFAULT_KM_URL = "http://127.0.0.1:9001"
ENV_KM_URL = "KERNEL_MEMORY_URL"
ENV_KM_API_KEY = "KERNEL_MEMORY_API_KEY"


# ── Data classes ─────────────────────────────────────────────────────────


@dataclass
class SearchResult:
    """A single search result from semantic search."""

    text: str
    relevance: float
    document_id: str = ""
    source_name: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class AskResult:
    """Result from a RAG question-answering query."""

    answer: str
    sources: List[SearchResult] = field(default_factory=list)
    raw_response: Optional[Dict] = None


# ── Service class ────────────────────────────────────────────────────────


class SemanticIndexService:
    """Adapter for Kernel Memory-based semantic search and RAG.

    Wraps HTTP calls to a Kernel Memory service for:
    - Document upload and indexing
    - Semantic search over indexed documents
    - RAG-based question answering

    Register with CapabilityRegistry:
        registry.register_service(
            "semantic_index",
            SemanticIndexService,
            capabilities=["semantic_search", "document_indexing", "rag_qa"],
        )
    """

    def __init__(
        self,
        km_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_index: str = "default",
        timeout: int = 30,
    ):
        self._km_url = (km_url or os.environ.get(ENV_KM_URL) or DEFAULT_KM_URL).rstrip(
            "/"
        )
        self._api_key = api_key or os.environ.get(ENV_KM_API_KEY)
        self._default_index = default_index
        self._timeout = timeout
        self._requests = None
        self._available = None

    def _get_requests(self):
        """Lazy import of requests library."""
        if self._requests is None:
            import requests

            self._requests = requests
        return self._requests

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def is_available(self) -> bool:
        """Check if the Kernel Memory service is reachable."""
        if self._available is None:
            try:
                requests = self._get_requests()
                r = requests.get(
                    f"{self._km_url}/health",
                    headers=self._headers(),
                    timeout=5,
                )
                self._available = r.status_code == 200
            except Exception as e:
                logger.debug(f"KM service not reachable: {e}")
                self._available = False
        return self._available

    @staticmethod
    def format_doc_id(source_name: str) -> str:
        """Generate ASCII-safe document ID from source name."""
        normalized = unicodedata.normalize("NFKD", source_name)
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"\W+", "_", ascii_name)
        return slug.strip("_").lower()

    def upload_document(
        self,
        name: str,
        text: str,
        source_type: str = "text",
        tags: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload a document for indexing.

        Args:
            name: Human-readable document name.
            text: Full text content to index.
            source_type: Type of source (e.g., "text", "url", "file").
            tags: Additional tags for filtering.

        Returns:
            Document ID.

        Raises:
            RuntimeError: If upload fails.
        """
        import io

        requests = self._get_requests()
        doc_id = self.format_doc_id(name)

        file_obj = io.BytesIO(text.encode("utf-8"))
        files = {"file1": (f"{doc_id}.txt", file_obj)}
        data = {
            "documentId": doc_id,
            "tags": [
                f"source_name:{name}",
                f"source_type:{source_type}",
            ],
        }
        if tags:
            data["tags"].extend(f"{k}:{v}" for k, v in tags.items())

        resp = requests.post(
            f"{self._km_url}/upload",
            files=files,
            data=data,
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        logger.info(f"Uploaded document: {doc_id}")
        return doc_id

    def wait_for_indexing(
        self,
        doc_id: str,
        timeout: float = 60.0,
        poll_interval: float = 2.0,
    ) -> str:
        """Poll upload status until indexing is complete.

        Returns:
            Index name where the document was stored.
        """
        import time

        requests = self._get_requests()
        deadline = time.time() + timeout

        while time.time() < deadline:
            r = requests.get(
                f"{self._km_url}/upload-status",
                params={"documentId": doc_id},
                headers=self._headers(),
                timeout=self._timeout,
            )
            r.raise_for_status()
            info = r.json()
            if info.get("completed", False):
                return info.get("index", self._default_index)
            time.sleep(poll_interval)

        raise RuntimeError(f"Timeout waiting for indexing of {doc_id}")

    def search(
        self,
        query: str,
        index: Optional[str] = None,
        source_filter: Optional[str] = None,
        limit: int = 5,
    ) -> List[SearchResult]:
        """Semantic search over indexed documents.

        Args:
            query: Search query text.
            index: Index to search in (defaults to service default).
            source_filter: Filter by source name.
            limit: Max results to return.

        Returns:
            List of SearchResult objects.
        """
        requests = self._get_requests()
        payload: Dict[str, Any] = {
            "index": index or self._default_index,
            "query": query,
            "limit": limit,
        }
        if source_filter:
            payload["filters"] = [{"source_name": [source_filter]}]

        resp = requests.post(
            f"{self._km_url}/search",
            json=payload,
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        body = resp.json()

        results = []
        for item in body.get("results", []):
            for partition in item.get("partitions", []):
                results.append(
                    SearchResult(
                        text=partition.get("text", ""),
                        relevance=partition.get("relevance", 0.0),
                        document_id=item.get("documentId", ""),
                        source_name=item.get("sourceName", ""),
                        tags={
                            t.split(":", 1)[0]: t.split(":", 1)[1]
                            for t in item.get("tags", {}).get("tags", [])
                            if ":" in t
                        },
                    )
                )
        return results

    def ask(
        self,
        question: str,
        index: Optional[str] = None,
        source_filter: Optional[str] = None,
    ) -> AskResult:
        """RAG-based question answering.

        Args:
            question: Question to answer.
            index: Index to search in.
            source_filter: Filter by source name.

        Returns:
            AskResult with answer text and source references.
        """
        requests = self._get_requests()
        payload: Dict[str, Any] = {
            "index": index or self._default_index,
            "question": question,
        }
        if source_filter:
            payload["filters"] = [{"source_name": [source_filter]}]

        resp = requests.post(
            f"{self._km_url}/ask",
            json=payload,
            headers=self._headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        body = resp.json()

        sources = []
        for src in body.get("relevantSources", []):
            for partition in src.get("partitions", []):
                sources.append(
                    SearchResult(
                        text=partition.get("text", ""),
                        relevance=partition.get("relevance", 0.0),
                        document_id=src.get("documentId", ""),
                        source_name=src.get("sourceName", ""),
                    )
                )

        return AskResult(
            answer=body.get("text", ""),
            sources=sources,
            raw_response=body,
        )

    def get_status_details(self) -> Dict[str, Any]:
        """Return service status details."""
        return {
            "service_type": "SemanticIndexService",
            "km_url": self._km_url,
            "available": self.is_available(),
            "default_index": self._default_index,
        }
