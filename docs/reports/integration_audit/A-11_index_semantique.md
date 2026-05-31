# Audit A-11: Index Semantique

**Issue**: #174 (CLOSED) | **SUIVI**: Score 80% | **Date audit**: 2026-05-31

## Status: 🟡 Partial

## What was delivered (student source)

Student project `Arg_Semantic_Index/` delivered a semantic indexing system based on Microsoft Kernel Memory. The system provides:

- Document ingestion and chunking (including argument-level chunking)
- Vector-based semantic search over indexed documents
- RAG-style "ask" functionality (question answering over indexed content)
- A standalone Streamlit frontend for interactive querying
- Integration with the Kernel Memory service (runs as a separate process)

Issue #174 tracked the argument-level chunking enhancement and was CLOSED.

## What exists in argumentation_analysis/

### Service adapter

- **`services/semantic_index_service.py`** (582 LOC) — `SemanticIndexService` class providing:
  - `index()` — document ingestion and chunking
  - `search()` — vector-based semantic search
  - `ask()` — RAG-style question answering over indexed content
  - Argument-level chunking logic (Issue #174 deliverable)

### Registration

- **`registry_setup.py:301-308`** — `semantic_index_service` registered in `CapabilityRegistry` with capabilities for indexing and search.

### Frontend

- **`Arg_Semantic_Index/`** — Standalone Streamlit application for interactive semantic search. NOT wired into the main web interface.

## Preservation Assessment

| Aspect | Status | Notes |
|--------|--------|-------|
| Index functionality | **Preserved** | Document ingestion and chunking intact |
| Search functionality | **Preserved** | Vector-based semantic search working |
| Ask/RAG functionality | **Preserved** | Question answering over indexed content present |
| Argument-level chunking | **Preserved** | Issue #174 enhancement implemented and closed |
| Registry integration | **Preserved** | Registered in CapabilityRegistry |
| Streamlit frontend | **Standalone** | Not integrated into main web UI |
| Embedding model config | **Not configurable** | Hard-coded in Python adapter |
| External dependency | **Required** | Kernel Memory service at port 9001 |

## Gap Analysis

### Gap 1: Embedding model NOT configurable in Python adapter

The `SemanticIndexService` hard-codes the embedding model reference. Users cannot switch embedding models (e.g., from OpenAI `text-embedding-3-small` to a local model) without modifying the source code. The underlying Kernel Memory service supports model configuration, but the Python adapter does not expose this.

**Impact**: Medium. Ties deployments to a specific embedding model. Changing models requires code changes rather than configuration.

### Gap 2: Ask/RAG not surfaced as registry capability

The `ask()` method is implemented in the service but is not declared as a distinct capability in the `CapabilityRegistry`. Consumers searching for "RAG" or "question_answering" capabilities cannot discover this service through the Lego Architecture's discovery mechanism.

**Impact**: Medium. The capability exists but is invisible to capability-based service discovery.

### Gap 3: Streamlit frontend not wired into main web interface

The standalone Streamlit app in `Arg_Semantic_Index/` runs as a separate service on its own port. It is not integrated into either the Starlette (port 5003) or FastAPI (port 8000) web applications. Users must navigate to a separate URL to use the semantic search UI.

**Impact**: Low-Medium. The Streamlit app functions correctly as a standalone tool, but it is not part of the unified web experience.

### Gap 4: Runtime dependency on external Kernel Memory service

The `SemanticIndexService` requires an external Kernel Memory service running on port 9001. This is a separate process that must be started independently. There is no health check, auto-start, or documented bootstrap procedure in the main application.

**Impact**: Low. The service works when the dependency is running, but the setup is not self-contained. Developers must know to start Kernel Memory separately.

## Recommended Action

1. **Make embedding model configurable** — Add an `embedding_model` parameter to `SemanticIndexService.__init__()` with a sensible default, reading from config/environment if available.
2. **Surface ask/RAG as registry capability** — Add `"rag"`, `"question_answering"` to the capability list in `registry_setup.py` so consumers can discover the ask functionality.
3. **Add health check for Kernel Memory** — Implement a simple `is_available()` method that pings port 9001, and call it during bootstrap to provide a clear error message when the dependency is missing.
4. **Document Kernel Memory setup** — Add a section to `docs/guides/` explaining how to start the Kernel Memory service and configure the connection.
5. **Evaluate Streamlit integration** — Decide whether to keep the standalone Streamlit app or migrate the search UI into the React frontend. If standalone, document it as a separate service.

## Source Files

| File | Role |
|------|------|
| `argumentation_analysis/services/semantic_index_service.py` | SemanticIndexService (582 LOC) |
| `argumentation_analysis/core/capability_registry.py` | Registry (registration at lines 301-308) |
| `Arg_Semantic_Index/` | Standalone Streamlit frontend |
| Issue #174 | Argument-level chunking (CLOSED) |
