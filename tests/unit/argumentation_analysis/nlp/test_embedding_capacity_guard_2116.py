"""Capacity guard for the local embedding capability (#2116 item 2, decision A1).

``argumentation_analysis.nlp.embedding_utils`` is the repository's only local
embedding capability — the external alternative is the Kernel Memory HTTP
service (``services/semantic_index_service.py``). The orphan pipeline link
(``pipelines/embedding_pipeline.py``) was withdrawn; this guard pins the
capability itself so the dormant module cannot become a silent retraction
candidate without a red test.

Real embeddings on synthetic input — no mocks. The model is the module's own
docstring example (``all-MiniLM-L6-v2``, 384 dimensions).

Where the measurement runs: it needs a working torch stack. CI runners cannot
load torch DLLs at all (#1651 — probe VERDICT 4/8: torch_cpu/fbgemm/shm/
torch_python, winerror 182, deterministic on 3/3 runs 2026-09-15), so
sentence-transformers is deliberately NOT provisioned there — provisioning it
made this file's and ``test_embedding_utils.py``'s module-level imports reach
``import torch`` at COLLECTION time and abort the whole run (PR #2267 run 2).
In CI the capacity tests skip with that reason; on any machine where the
stack loads (dev boxes) they measure for real.
"""

import importlib.util

import pytest

ST_MODEL = "all-MiniLM-L6-v2"
EXPECTED_DIMS = 384

ST_SKIP_REASON = (
    "sentence-transformers unavailable: not provisioned in CI because the "
    "runner image cannot load torch DLLs (#1651 — probe VERDICT 4/8, "
    "winerror 182, deterministic on 3/3 runs 2026-09-15); the capability "
    "is measured wherever the stack loads"
)


@pytest.fixture(scope="module")
def real_embeddings():
    pytest.importorskip("sentence_transformers", reason=ST_SKIP_REASON)
    from argumentation_analysis.nlp.embedding_utils import get_embeddings_for_chunks

    return get_embeddings_for_chunks(
        ["argument alpha", "counter beta", "synthesis gamma"], ST_MODEL
    )


def test_real_embeddings_dimensions(real_embeddings):
    """One embedding per input chunk, all of the model's dimensionality."""
    assert len(real_embeddings) == 3
    assert all(len(vector) == EXPECTED_DIMS for vector in real_embeddings)
    assert all(
        isinstance(component, float)
        for vector in real_embeddings
        for component in vector
    )


def test_real_embeddings_plurality(real_embeddings):
    """Distinct inputs yield distinct embeddings — the output is not constant."""
    vectors = {tuple(vector) for vector in real_embeddings}
    assert len(vectors) == 3


def test_embedding_pipeline_orphan_link_is_gone():
    """The orphan pipeline link was withdrawn (#2116 A1); capability stays in nlp/."""
    spec = importlib.util.find_spec(
        "argumentation_analysis.pipelines.embedding_pipeline"
    )
    assert spec is None, (
        "embedding_pipeline.py was withdrawn (#2116 A1); the local embedding "
        "capability lives in argumentation_analysis.nlp.embedding_utils, "
        "pinned by the capacity tests in this file"
    )
