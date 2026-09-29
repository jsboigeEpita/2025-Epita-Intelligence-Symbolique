"""Capacity guard for the local embedding capability (#2116 item 2, decision A1).

``argumentation_analysis.nlp.embedding_utils`` is the repository's only local
embedding capability — the external alternative is the Kernel Memory HTTP
service (``services/semantic_index_service.py``). The orphan pipeline link
(``pipelines/embedding_pipeline.py``) was withdrawn; this guard pins the
capability itself so the dormant module cannot become a silent retraction
candidate without a red test.

Real embeddings on synthetic input — no mocks. The model is the module's own
docstring example (``all-MiniLM-L6-v2``, 384 dimensions).

Where the measurement runs: it needs a working torch stack. The gate env
loads torch since #2856 (the #1651 "runner image" verdict was a conda-lock
defect — two providers of ``libiomp5md.dll`` clobbering each other — repaired
in the solve), so the old blocker is gone; sentence-transformers is still
NOT provisioned pending its own CI measurement (#2116: provisioning it adds
a module-level torch import at collection for this file and
``test_embedding_utils.py``, and a model download in the gate run). The
capacity tests therefore skip wherever the package is absent and measure for
real wherever it is installed (dev boxes).
"""

import importlib.util

import pytest

ST_MODEL = "all-MiniLM-L6-v2"
EXPECTED_DIMS = 384

ST_SKIP_REASON = (
    "sentence-transformers unavailable: not provisioned in the gate env "
    "(#2116 decision A1, under re-examination since #2856 removed the "
    "torch-loading blocker); the capability is measured wherever the "
    "package is installed"
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
