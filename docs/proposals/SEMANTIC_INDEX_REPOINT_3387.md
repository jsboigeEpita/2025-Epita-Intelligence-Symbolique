# Semantic Index Repoint — Design Note (#3387)

Status: **proposal** — first deliverable of the R1143 decision ("repointer",
option 1a: index the corpus, then retrieval). Decision owner: coordinator.

## What was decided, and why this note starts from confidentiality

The wire-or-retire audit (R1300, 2026-11-05) measured the semantic-index phase
as self-referential — it indexes the run's own extracted arguments, then
searches them back, filtered on the run's namespace; no corpus was ever
indexed — and unread (`phase_index_output` has zero readers outside its
writer). The coordinator's decision: **repoint**. This note designs that
repoint. It starts from the confidentiality constraint because that
constraint decides the architecture before any capability question is reached.

## The constraint, and what it excludes

The canonical dataset is `argumentation_analysis/data/extract_sources.json.gz.enc`
(encrypted, tracked; CLAUDE.md "Dataset Privacy Discipline"). Two rules bind
any index:

1. **Decrypted text never touches disk** (rule 5): downstream consumers load
   the definitions in memory (`load_extract_definitions`) and never persist
   them.
2. **A document identifier never enters a tracked file** (rule 7), and
   GitHub-indexed surfaces carry opaque ids only (rule 4).

This excludes, as-is, the architecture the service currently wraps:

- **The Kernel Memory docker (`kernelmemory/service`, port 9001).**
  `upload_document` POSTs the full plaintext as a file to the service, which
  persists it in its own volumes — disk outside this repo's gitignore
  discipline, in a store whose dumps we do not control. Rule 1 fails by
  construction, before any deployment question.
- **Measured on this seat (po-2023, 2026-11-05): nothing serves 9001.** No
  listener on the port, no container, and the seat `.env` carries no
  `KERNEL_MEMORY_URL`, so every default-constructed `SemanticIndexService`
  points at a dead endpoint (`skipped: endpoint_unavailable`). The other
  seats' localhost is not measurable from here; each lane can report its own
  state with the probe below. If no seat serves it, the phase as written has
  never run outside fixtures — consistent with the R1300 census (46/46 seat
  dumps carry `semantic_index_refs`, zero non-empty).

Probe (run on each seat; no credentials needed):

```bash
curl -s -m 5 http://127.0.0.1:9001/health; docker ps -a --format '{{.Names}} {{.Ports}}' | grep 9001
```

## What this seat actually hosts, and what the repoint uses

The embedding compute on po-2023 is **not** the KM service:

- `127.0.0.1:8005` — vLLM OpenAI-compatible embeddings server (container
  `qwen3_4b_awq_embedding_server`, up, healthy at probe time), **auth-required**:
  `/v1/models` and `/v1/embeddings` both answer `{"error":"Unauthorized"}`
  without a bearer key. `127.0.0.1:8004` fronts it with a logging proxy.
  A key is provisioned on the seat (the stack is watched by a local vigie
  lane); it must come from the seat environment, never from a tracked file.

The repoint therefore does not depend on KM at all: an OpenAI-compatible
`/v1/embeddings` endpoint is the only external requirement, and this seat has
one running.

## Two compliant index shapes

Both start from the same in-memory loader and differ in what survives the
process.

**A — volatile, in-process (recommended for v1).** At run start: chunk each
panel document, embed the chunks, keep `{opaque_doc_id, chunk_offset, vector}`
in memory; at exit, everything is gone. Nothing persists, so no new privacy
surface exists at all. Cost: re-embedding per run. The panel is 10 documents
(the four longest are 47 644–179 139 chars), i.e. on the order of a few
hundred chunks at ~2k chars — seconds on the local vLLM lane, zero paid calls.

**B — persisted, opaque ids + vectors only.** A gitignored file under the
already-ignored evaluation results area stores `{opaque doc id, chunk
offsets, vectors, source checksum}` — **no text**. Text is resolved at query
time by joining offsets against the in-memory decrypted definitions.
Compliant: no plaintext, no name; the ids are the same opaque ids the rest of
the pipeline already uses. Worth it only if embedding the corpus becomes a
wall-clock cost (it is not, at panel scale) or if runs want warm starts
across processes. **Defer B until A measures slow.**

Chunking: reuse the existing `chunk_by_arguments` chunker (guarded by
`tests/unit/argumentation_analysis/test_semantic_index_chunking.py`) rather
than introducing a new one.

## The other half of the repoint: a reader

An index with no reader is the defect R1300 measured, wearing a new coat. The
repoint is complete only when retrieval feeds a production consumer. One
candidate, grounded in what the pipeline already does:

- **`select_for_budget(priority_spans=)`** — the #3406 consumer. Retrieval
  ranks corpus passages against the run's question and feeds them as priority
  spans; the budget selector already accepts exactly this input, so the
  reader side is a wiring change, not a new surface.

One consumer in v1. More can join later; the capability census
(`test_one_capability_surface_1842`) keeps counting real demand.

## Open questions (coordinator)

1. **Corpus scope** — the 10-document panel (#3375), or the full encrypted
   dataset? This note assumes the panel (the Panel Bar's unit); a different
   scope changes the chunk-count estimate, nothing structural.
2. **Embedding endpoint** — the local vLLM lane (8005, free) as default, or a
   paid embedding API? This note assumes local.
3. **The KM path after the repoint** — with the index living in-process, the
   KM upload/search path (the 9001 default, `Arg_Semantic_Index`'s docker) is
   dead code on every measured seat. Recommendation: retire the KM HTTP path
   with the repoint, keep the pure chunker. Alternative: keep the adapter for
   offline fixtures only. This is the same wire-or-retire class the
   coordinator pre-triaged on #3386.

Refs #3387, Refs #3374
