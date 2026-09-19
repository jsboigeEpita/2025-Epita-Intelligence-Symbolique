# -*- coding: utf-8 -*-
"""#2320 — a replay miss must traverse the invoke layer's degradation handlers.

CI measured it (run ``35435391692``): ``miss_replay=31`` while pytest reported
``22 passed`` — every ``LLMCacheMiss`` raised by the cache was absorbed by a
broad ``except Exception`` sitting on an LLM-call region, so the lane's tests
stayed green on a broken cassette set while the gate (which counts at the
raise site) was the only instrument that saw the hole. #1019 family: the
counter and the verdict never meet.

The fix: ``except LLMCacheMiss: raise`` before each broad except that wraps an
LLM invoke region. ``LLMCacheMiss`` is replay-only — it never raises in live
or record mode — so the re-raise changes ZERO product behavior and only makes
a broken replay lane loud.

These guards exercise the three absorption shapes repaired:

- ``return None`` (quality enrichment) — the miss became "LLM unavailable";
- ``return partial`` (counter-argument batch) — the miss became an empty batch;
- fallback-with-status (fact extraction, the constat-D site of #1603) — the
  miss was retried ``_EXTRACTION_MAX_ATTEMPTS`` times (a miss is
  DETERMINISTIC: same request content → same key → same miss) and then fed
  the #1290 heuristic, whose loud ``extraction_status`` still left pytest
  green.

The fake client raises from ``chat.completions.create`` through the
``cached_raw_chat_completion`` OFF-mode passthrough — the except clauses are
mode-blind, so the traversal is observable without a replay-mode cache.
"""

from typing import Any, Dict, List

import pytest

from argumentation_analysis.orchestration import invoke_callables
from argumentation_analysis.services.llm_cache import LLMCacheMiss


class _MissClient:
    """OpenAI-shaped client whose every completion raises a replay miss."""

    class chat:  # noqa: N801 — mirrors the SDK attribute chain
        class completions:  # noqa: N801
            @staticmethod
            async def create(**_kwargs: Any) -> None:
                raise LLMCacheMiss(
                    "Raw cache miss in replay mode for key 0123456789abcdef... "
                    "Record fixtures first with LLM_CACHE_MODE=record"
                )


async def test_quality_enrichment_miss_traverses_instead_of_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Pre-#2320: absorbed → ``return None`` ("LLM quality enrichment
    # skipped"). The caller then treats a broken cassette set as a missing
    # LLM and the phase completes degraded-but-green.
    monkeypatch.setattr(
        invoke_callables, "_get_openai_client", lambda: (_MissClient(), "test-model")
    )
    heuristic: Dict[str, Any] = {
        "arg_1": {"scores_par_vertu": {"clarte": 4.0}, "note_finale": 5.0}
    }
    with pytest.raises(LLMCacheMiss):
        await invoke_callables._llm_enrich_quality(heuristic, ["un argument"])


async def test_counter_batch_miss_traverses_instead_of_partial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Pre-#2320: absorbed per batch ("Counter-argument batch [0:12] failed")
    # → ``return counters`` with whatever earlier batches produced. A miss on
    # the FIRST batch returned ``[]`` — indistinguishable from "the model
    # found nothing to rebut".
    monkeypatch.setattr(
        invoke_callables, "_get_determinism_params", lambda: {"temperature": 0.0}
    )
    with pytest.raises(LLMCacheMiss):
        await invoke_callables._generate_counters_for_targets(
            _MissClient(), "test-model", ["première cible argumentée"]
        )


async def test_extraction_miss_traverses_instead_of_heuristic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Pre-#2320 (constat D, #1603): the retry loop absorbed the miss as an
    # attempt failure, re-missed identically (deterministic key) for every
    # attempt, then the #1290 heuristic returned claims with
    # ``extraction_status=failed:<reason>``. Loud in the payload, green in
    # pytest — the gate counted misses the verdict never saw.
    monkeypatch.setattr(
        invoke_callables, "_get_openai_client", lambda: (_MissClient(), "test-model")
    )
    text = "Un texte argumentatif suffisamment long pour ouvrir le chemin LLM. " * 3
    result: List[Any] = []
    with pytest.raises(LLMCacheMiss) as excinfo:
        result.append(await invoke_callables._invoke_fact_extraction(text, {}))
    assert not result, "the miss must traverse — never reach the heuristic fallback"
    # The traversing miss is the cache's own, not a wrapped re-raise.
    assert "cache miss" in str(excinfo.value).lower()
