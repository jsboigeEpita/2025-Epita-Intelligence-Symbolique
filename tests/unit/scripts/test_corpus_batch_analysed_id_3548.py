"""#3548 R1205 rework — the batch runner carries the analysed id to the phase.

The coordinator measured the defect on the 407 recorded ``state_full_*.json``:
none carries ``source_name`` in ``source_metadata``, because
``run_corpus_batch.py`` passes ``metadata=doc["metadata"]`` while the opaque id
stays at the top level of the doc dict. An exclusion reading the state can
therefore never fire in a panel run.

This witness pins the production path end to end at the runner's own
doc-to-pipeline seam: ``_run_single`` (the function the batch loop calls once
per document) must hand the pipeline a context carrying the analysed
document's opaque id. Seat-free: the pipeline is a fake that captures its
keyword arguments; no corpus, no key, no network.
"""

from __future__ import annotations

import faulthandler
import importlib.util
from pathlib import Path
from typing import Any, Dict, List

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3] / "scripts" / "dataset" / "run_corpus_batch.py"
)

SYNTHETIC_SOURCE = "Synthetic Analysed Id Alpha"
SYNTHETIC_ID = "synthetic_analysed_id_alpha_ext0"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_corpus_batch_under_test_3548", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _disarm_teardown_watchdog():
    """These tests call ``_run_single`` directly, so its tail arms a real 60 s
    faulthandler one-shot that only ``main()``'s finally cancels (#2080)."""
    yield
    faulthandler.cancel_dump_traceback_later()


@pytest.mark.asyncio
async def test_run_single_hands_the_pipeline_the_analysed_id(tmp_path):
    runner = _load_runner()
    calls: List[Dict[str, Any]] = []

    async def fake_pipeline(*args, **kwargs):
        calls.append(kwargs)
        return {"analysis_outcome": {"status": "ok"}, "state_snapshot": {}}

    signature = await runner._run_single(
        text="A synthetic document long enough to be a document.",
        source_name=SYNTHETIC_SOURCE,
        opaque_id_str=SYNTHETIC_ID,
        workflow="spectacular",
        metadata={"discourse_type": "political", "era": "unknown"},
        state_dumps_dir=tmp_path / "dumps",
        signatures_dir=tmp_path / "sigs",
        skip_existing=False,
        pipeline_fn=fake_pipeline,
        sanitize_fn=lambda state: dict(state),
    )

    assert signature is not None and signature["outcome"] == {"status": "ok"}
    assert len(calls) == 1, calls
    context = calls[0].get("context")
    assert context == {"analysed_document_id": SYNTHETIC_ID}, (
        "#3548 R1205: the batch runner must carry the analysed document's "
        f"opaque id to the phase by context; got {context!r}"
    )
    # The id must NOT ride source_metadata: Act I renders every key of it.
    assert "analysed_document_id" not in calls[0].get("source_metadata") or {}
    assert calls[0].get("source_metadata") == {
        "discourse_type": "political",
        "era": "unknown",
    }
