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

    # ── Argument-level chunking (#174) ──────────────────────────────────

    def index_arguments(
        self,
        arguments: List[Dict[str, Any]],
        source_name: str = "pipeline",
        quality_scores: Optional[Dict[str, Dict]] = None,
        fallacies: Optional[List[Dict[str, Any]]] = None,
        index: Optional[str] = None,
    ) -> List[str]:
        """Index individual arguments as separate vectors with metadata.

        Instead of chunking by fixed token count, each argument from
        fact_extraction is indexed as its own vector with quality and
        fallacy metadata attached for filtered search.

        Args:
            arguments: List of argument dicts from fact_extraction
                       (each has 'text' and optionally 'source_quote').
            source_name: Name of the source document.
            quality_scores: Per-argument quality scores from quality evaluator
                           {arg_id: {scores_par_vertu: {...}, note_finale: float}}.
            fallacies: List of detected fallacies with target_argument references.
            index: Index to store in (defaults to service default).

        Returns:
            List of document IDs for indexed arguments.
        """
        quality_scores = quality_scores or {}
        fallacies = fallacies or []
        doc_ids = []

        # Build fallacy lookup: arg_index → fallacy type
        fallacy_by_arg: Dict[int, str] = {}
        for f in fallacies:
            if isinstance(f, dict):
                target = f.get("target_argument_id", f.get("argument_index", -1))
                ftype = f.get("type", f.get("fallacy_type", "unknown"))
                if isinstance(target, int) and target >= 0:
                    fallacy_by_arg[target] = str(ftype)
                elif isinstance(target, str) and target.startswith("arg_"):
                    try:
                        idx = int(target.split("_")[1]) - 1
                        fallacy_by_arg[idx] = str(ftype)
                    except (ValueError, IndexError):
                        pass

        for i, arg in enumerate(arguments):
            arg_text = arg.get("text", str(arg)) if isinstance(arg, dict) else str(arg)
            if not arg_text or len(arg_text) < 5:
                continue

            arg_id = f"arg_{i+1}"
            source_quote = (
                arg.get("source_quote", "") if isinstance(arg, dict) else ""
            )

            # Build metadata tags
            tags: Dict[str, str] = {
                "chunk_type": "argument",
                "argument_index": str(i),
                "argument_id": arg_id,
                "source_name": source_name,
            }

            # Add quality metadata
            q_scores = quality_scores.get(arg_id, {})
            if isinstance(q_scores, dict):
                overall = q_scores.get("note_finale", 0)
                if isinstance(overall, (int, float)):
                    tags["quality_score"] = f"{float(overall):.2f}"
                    # Bin into categories for filtered search
                    if overall >= 0.7:
                        tags["quality_level"] = "high"
                    elif overall >= 0.4:
                        tags["quality_level"] = "medium"
                    else:
                        tags["quality_level"] = "low"

                virtues = q_scores.get("scores_par_vertu", {})
                if isinstance(virtues, dict):
                    # Store weakest virtue for targeted search
                    weakest = min(
                        ((k, v) for k, v in virtues.items() if isinstance(v, (int, float))),
                        key=lambda x: x[1],
                        default=None,
                    )
                    if weakest:
                        tags["weakest_virtue"] = weakest[0]

            # Add fallacy metadata
            if i in fallacy_by_arg:
                tags["fallacy_type"] = fallacy_by_arg[i]
                tags["has_fallacy"] = "true"
            else:
                tags["has_fallacy"] = "false"

            if source_quote:
                tags["source_quote"] = source_quote[:200]

            try:
                doc_id = self.upload_document(
                    name=f"{source_name}__{arg_id}",
                    text=arg_text,
                    source_type="argument",
                    tags=tags,
                )
                doc_ids.append(doc_id)
            except Exception as e:
                logger.warning(f"Failed to index argument {arg_id}: {e}")

        logger.info(
            f"Indexed {len(doc_ids)}/{len(arguments)} arguments from '{source_name}'"
        )
        return doc_ids

    def search_arguments(
        self,
        query: str,
        index: Optional[str] = None,
        fallacy_type: Optional[str] = None,
        quality_level: Optional[str] = None,
        has_fallacy: Optional[bool] = None,
        limit: int = 5,
    ) -> List[SearchResult]:
        """Search indexed arguments with metadata filtering.

        Args:
            query: Semantic search query.
            index: Index to search in.
            fallacy_type: Filter by specific fallacy type.
            quality_level: Filter by quality level ("high", "medium", "low").
            has_fallacy: Filter for arguments with/without fallacies.
            limit: Max results.

        Returns:
            List of SearchResult objects with metadata tags.
        """
        requests = self._get_requests()
        payload: Dict[str, Any] = {
            "index": index or self._default_index,
            "query": query,
            "limit": limit,
        }

        # Build filters
        filters = []
        if fallacy_type:
            filters.append({"fallacy_type": [fallacy_type]})
        if quality_level:
            filters.append({"quality_level": [quality_level]})
        if has_fallacy is not None:
            filters.append({"has_fallacy": ["true" if has_fallacy else "false"]})
        filters.append({"chunk_type": ["argument"]})

        if filters:
            payload["filters"] = filters

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

    @staticmethod
    def chunk_by_arguments(
        text: str,
        fact_extraction_output: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Split text into argument-level chunks.

        Uses fact_extraction output if available, otherwise falls back
        to sentence-level splitting with heuristic argument detection.

        Args:
            text: Raw input text.
            fact_extraction_output: Output from fact_extraction phase
                containing 'arguments' and 'claims' lists.

        Returns:
            List of argument dicts with 'text' and 'source_quote' fields.
        """
        if fact_extraction_output and isinstance(fact_extraction_output, dict):
            arguments = fact_extraction_output.get("arguments", [])
            claims = fact_extraction_output.get("claims", [])

            chunks = []
            for arg in arguments:
                if isinstance(arg, dict):
                    chunks.append({
                        "text": arg.get("text", str(arg)),
                        "source_quote": arg.get("source_quote", ""),
                        "chunk_type": "argument",
                    })
                elif isinstance(arg, str) and len(arg) >= 10:
                    chunks.append({
                        "text": arg,
                        "source_quote": "",
                        "chunk_type": "argument",
                    })

            for claim in claims:
                if isinstance(claim, dict):
                    chunks.append({
                        "text": claim.get("text", str(claim)),
                        "source_quote": claim.get("source_quote", ""),
                        "chunk_type": "claim",
                    })
                elif isinstance(claim, str) and len(claim) >= 10:
                    chunks.append({
                        "text": claim,
                        "source_quote": "",
                        "chunk_type": "claim",
                    })

            if chunks:
                return chunks

        # Fallback: sentence-level splitting
        import re
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [
            {"text": s.strip(), "source_quote": "", "chunk_type": "sentence"}
            for s in sentences
            if len(s.strip()) >= 15
        ]
