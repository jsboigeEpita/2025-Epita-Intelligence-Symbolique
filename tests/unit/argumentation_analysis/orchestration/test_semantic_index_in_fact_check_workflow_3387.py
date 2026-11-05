"""#3387 — the repointed semantic index inside the PRODUCTION fact-check workflow.

#2763 had put this phase on the fact-check run's own premises: it uploaded
them to Kernel Memory and searched them back. R1300 measured that path inert
(no corpus was ever indexed, and nothing outside the writer read the refs),
and the 2026-11-05 decision repointed the phase to the analysed document. The
witnesses that certified the premise-indexing contract went with the
behaviour; this module keeps the part that is still true — the phase is WIRED
into ``build_fact_check_workflow``, and the repointed phase must still behave
honestly there.

Two outcomes are measured end to end through a real ``WorkflowExecutor``:

- a run whose first reading named a thesis: the phase runs on the document's
  own text and hands back spans (fake embedder — no network, no paid call);
- a run with no reading: the phase says why it skipped, instead of answering
  ``ran`` on nothing.

Privacy (CLAUDE.md rules 1, 4 and 6): the text is synthetic, ids are opaque,
and what the phase returns are OFFSETS, never passages.
"""

import re
import zlib
from typing import Any, List, Sequence

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)
from argumentation_analysis.orchestration.workflow_dsl import WorkflowExecutor
from argumentation_analysis.services import semantic_retrieval as sr
from argumentation_analysis.workflows.fact_check_pipeline import (
    build_fact_check_workflow,
)

import argumentation_analysis.orchestration.invoke_callables as ic  # noqa: F401

_DIM = 96

#: The passage a reading's thesis points at — placed past the head of the
#: document on purpose: a head-anchored pass never reaches it.
_THESIS_SENTENCE = (
    "Le budget proposé transfère la décision fiscale du parlement vers "
    "l'exécutif sans débat public préalable."
)


def _vector(text: str) -> List[float]:
    vec = [0.0] * _DIM
    for word in re.findall(r"[0-9a-zà-ÿ]+", text.lower()):
        vec[zlib.crc32(word.encode("utf-8")) % _DIM] += 1.0
    return vec


def _fake_post_embeddings(route: Any, texts: Sequence[str]) -> List[List[float]]:
    return [_vector(t) for t in texts]


def _document(sentences: int = 60) -> str:
    filler = (
        "La séance reprend après une pause et la parole circule entre les "
        "groupes selon un ordre convenu à l'avance."
    )
    head = " ".join(filler for _ in range(sentences // 2))
    tail = " ".join(filler for _ in range(sentences // 2))
    return f"{head} {_THESIS_SENTENCE} {tail}"


def _registry() -> CapabilityRegistry:
    """The four capabilities the fact-check DAG demands, two of them doubles."""

    async def quality_invoke(text, ctx):
        return {"note_finale": 0.55, "scores_par_vertu": {"clarte": 0.6}}

    async def belief_invoke(text, ctx):
        return {"beliefs": {}, "belief_count": 0}

    async def counter_invoke(text, ctx):
        return {"llm_counter_arguments": []}

    registry = CapabilityRegistry()
    registry.register(
        "quality",
        ComponentType.AGENT,
        capabilities=["argument_quality"],
        invoke=quality_invoke,
    )
    registry.register(
        "jtms",
        ComponentType.SERVICE,
        capabilities=["belief_maintenance"],
        invoke=belief_invoke,
    )
    registry.register(
        "counter",
        ComponentType.AGENT,
        capabilities=["counter_argument_generation"],
        invoke=counter_invoke,
    )
    registry.register(
        "semantic_index",
        ComponentType.SERVICE,
        capabilities=["semantic_indexing"],
        invoke=ic._invoke_semantic_index,
    )
    return registry


async def test_the_workflow_hands_the_phase_the_document_and_the_reading(
    monkeypatch,
):
    """The production DAG reaches the repointed phase with both of its inputs:
    the document under analysis, and the thesis the first reading named."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
    monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://test/v1")
    monkeypatch.setattr(sr, "_post_embeddings", _fake_post_embeddings)

    document = _document()
    state = UnifiedAnalysisState(initial_text=document)
    state.defining_moves = {
        "moves": [
            {
                "kind": "thesis",
                "reading": "Le texte déplace la décision fiscale vers l'exécutif.",
                "quote": _THESIS_SENTENCE,
                "offset": None,
            }
        ]
    }

    results = await WorkflowExecutor(_registry()).execute(
        build_fact_check_workflow(), document, state=state
    )

    output = results["indexing"].output
    assert output["status"] == "ran", output
    assert output["route_source"] == "declared"
    assert output["priority_spans"], "la phase n'a rendu aucun passage"
    assert output["query_chars"] > 0


async def test_without_a_reading_the_phase_skips_honestly(monkeypatch):
    """A fact-check run carries no first reading, so the repointed phase has
    no question. It must say so — an empty ``ran`` is exactly the theatre
    #1019 forbids — and the workflow must still complete."""
    monkeypatch.setenv(sr.EMBEDDING_KEY_ENV, "k")
    monkeypatch.setenv(sr.EMBEDDING_URL_ENV, "http://test/v1")
    monkeypatch.setattr(sr, "_post_embeddings", _fake_post_embeddings)

    results = await WorkflowExecutor(_registry()).execute(
        build_fact_check_workflow(), _document()
    )

    output = results["indexing"].output
    assert output["status"] == "skipped: no_reading_query", output
    assert output["reason"], "un saut muet n'est pas un saut honnête"
    assert results["belief_tracking"].output["belief_count"] == 0
