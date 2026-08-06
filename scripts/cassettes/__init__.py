"""Cassettes LLM : record→export→commit→import→replay (#1603).

The runtime LLM cache (`argumentation_analysis.services.llm_cache`) uses
`diskcache.Cache` (SQLite-backed) under `LLM_CACHE_DIR`. Runtime caches are
gitignored; fixtures committed to `tests/fixtures/llm_cassettes/` need a
diff-friendly representation.

Workflow:

1.  **Record** — set ``LLM_CACHE_MODE=record`` and ``LLM_CACHE_DIR`` to the
    runtime location. Run the test suite (or selected tests). The runtime DB
    grows.
2.  **Export** — ``python scripts/cassettes/export.py <runtime_db_dir>
    <fixtures_dir>``. Reads each ``cache.db`` entry, audits the value for
    forbidden plaintext fields (`raw_text`, `full_text`, etc.) and writes
    one ``<sha256>.json`` per entry under ``fixtures_dir``. Each file holds
    the serialized response only — the prompt is recomputed from the
    request.
3.  **Commit** — the fixtures directory. Git diffs line-oriented JSON.
4.  **Replay** — ``python scripts/cassettes/import.py <fixtures_dir> <db_dir>``
    populates a DB from the fixtures, then ``LLM_CACHE_MODE=replay`` replays.
    A miss in replay raises ``LLMCacheMiss`` (fail-loud).

This module stays read-only on the cache layer: it never modifies
`llm_cache.py`. The exported format is the literal output of
`_serialize_response` (list[dict]) and `_serialize_chat_completion` (dict)
in llm_cache.py — round-tripped through ``_deserialize_*`` and
``ChatCompletion.model_validate``.

Privacy: see ``scripts/cassettes/privacy_audit.py`` for the forbidden-fields
list and the probe that runs before export.
"""
