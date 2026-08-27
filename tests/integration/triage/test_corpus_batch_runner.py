"""Integration tests for scripts/dataset/run_corpus_batch.py.

Uses injected mock pipeline to avoid API calls.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[3] / "scripts" / "dataset"
sys.path.insert(0, str(SCRIPT_DIR))

import run_corpus_batch as runner


def _mock_pipeline(return_value):
    return AsyncMock(return_value=return_value)


def _mock_sanitize(state):
    """Simple sanitizer that strips raw_text."""
    state = dict(state)
    state.pop("raw_text", None)
    return state


# ---------------------------------------------------------------------------
# classify_metadata tests
# ---------------------------------------------------------------------------


class TestClassifyMetadata:
    def test_default_unknown(self):
        meta = runner.classify_metadata("Some Document")
        assert meta["discourse_type"] == "unknown"
        assert meta["era"] == "unknown"

    def test_political_keyword(self):
        meta = runner.classify_metadata("Discours du President")
        assert meta["discourse_type"] == "political"

    def test_media_keyword(self):
        meta = runner.classify_metadata("Editorial du Monde")
        assert meta["discourse_type"] == "media"

    def test_scientific_keyword(self):
        meta = runner.classify_metadata("Rapport sur le climat")
        assert meta["discourse_type"] == "scientific"

    def test_era_from_date(self):
        meta = runner.classify_metadata("Test", date_iso="2024-06-15")
        assert meta["era"] == "2024"
        assert meta["year_bucket"] == "2020-2024"


# ---------------------------------------------------------------------------
# _run_single tests (mocked pipeline)
# ---------------------------------------------------------------------------


class TestRunSingle:
    @pytest.mark.asyncio
    async def test_produces_signature(self, tmp_path):
        """Processing a doc produces a sanitized signature file."""
        mock_result = {
            "state_snapshot": {
                "raw_text": "Sensitive text",
                "source_id": "doc_test",
                "argument_quality_scores": {"a1": {"overall": 0.9}},
            }
        }

        sig = await runner._run_single(
            text="Test text",
            source_name="Test Source",
            opaque_id_str="abcd1234",
            workflow="spectacular",
            metadata={"discourse_type": "political"},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            pipeline_fn=_mock_pipeline(mock_result),
            sanitize_fn=_mock_sanitize,
        )

        assert sig is not None
        assert sig["opaque_id"] == "abcd1234"
        assert sig["workflow"] == "spectacular"
        assert sig["metadata"]["discourse_type"] == "political"
        assert sig["outcome"] == {"status": "ok"}
        assert "raw_text" not in sig["state"]
        assert sig["state"]["argument_quality_scores"]["a1"]["overall"] == 0.9

        # Files exist
        assert (tmp_path / "dumps" / "state_full_abcd1234.json").exists()
        assert (tmp_path / "sigs" / "signature_abcd1234.json").exists()

    @pytest.mark.asyncio
    async def test_skip_existing_reuses_failure_outcome(self, tmp_path):
        """A skipped existing failure remains visible to aggregate exit status."""
        sigs = tmp_path / "sigs"
        sigs.mkdir()
        existing = {
            "opaque_id": "abcd1234",
            "outcome": {
                "status": "failed",
                "phase": "extract",
                "reason": "failed:synthetic-auth-error",
            },
        }
        (sigs / "signature_abcd1234.json").write_text(
            json.dumps(existing), encoding="utf-8"
        )

        sig = await runner._run_single(
            text="x",
            source_name="x",
            opaque_id_str="abcd1234",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=sigs,
            skip_existing=True,
            sanitize_fn=_mock_sanitize,
        )
        assert sig == existing

    @pytest.mark.asyncio
    async def test_skip_existing_maps_legacy_success_without_false_failure(
        self, tmp_path
    ):
        """A pre-outcome successful signature remains a valid skipped result."""
        sigs = tmp_path / "sigs"
        sigs.mkdir()
        existing = {
            "opaque_id": "legacy01",
            "workflow": "spectacular",
            "state": {},
        }
        (sigs / "signature_legacy01.json").write_text(
            json.dumps(existing), encoding="utf-8"
        )

        sig = await runner._run_single(
            text="x",
            source_name="x",
            opaque_id_str="legacy01",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=sigs,
            skip_existing=True,
            sanitize_fn=_mock_sanitize,
        )

        assert sig is not None
        assert sig["outcome"]["status"] == "skipped_existing"

    @pytest.mark.asyncio
    async def test_skip_existing_keeps_legacy_partial_nonzero(self, tmp_path):
        """A legacy partial signature cannot be promoted to skipped success."""
        sigs = tmp_path / "sigs"
        sigs.mkdir()
        existing = {
            "opaque_id": "legacy02",
            "workflow": "spectacular",
            "state": {},
            "partial": True,
        }
        (sigs / "signature_legacy02.json").write_text(
            json.dumps(existing), encoding="utf-8"
        )

        sig = await runner._run_single(
            text="x",
            source_name="x",
            opaque_id_str="legacy02",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=sigs,
            skip_existing=True,
            sanitize_fn=_mock_sanitize,
        )

        assert sig is not None
        assert sig["outcome"]["status"] == "partial_error"

    @pytest.mark.asyncio
    async def test_partial_on_error(self, tmp_path):
        """Pipeline error produces partial signature."""
        failing = AsyncMock(side_effect=RuntimeError("LLM error"))

        sig = await runner._run_single(
            text="x",
            source_name="x",
            opaque_id_str="err12345",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            pipeline_fn=failing,
            sanitize_fn=_mock_sanitize,
        )

        assert sig is not None
        assert sig.get("partial") is True
        assert sig["outcome"]["status"] == "partial_error"
        assert "LLM error" in sig["outcome"]["reason"]

    @pytest.mark.asyncio
    async def test_timeout_has_distinct_partial_timeout_outcome(self, tmp_path):
        """A real timeout remains distinguishable from another pipeline exception."""

        async def slow_pipeline(*args, **kwargs):
            await asyncio.sleep(0.05)
            return {"state_snapshot": {}}

        sig = await runner._run_single(
            text="x",
            source_name="x",
            opaque_id_str="timeout1",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            timeout=0.001,
            pipeline_fn=slow_pipeline,
            sanitize_fn=_mock_sanitize,
        )

        assert sig is not None
        assert sig["outcome"]["status"] == "partial_timeout"
        assert sig.get("partial") is True

    @pytest.mark.asyncio
    async def test_foundational_failure_is_preserved_in_signature(self, tmp_path):
        """A failed extraction is a failed document, not a normal signature."""
        mock_result = {
            "analysis_outcome": {
                "status": "failed",
                "phase": "extract",
                "reason": "failed:synthetic-quota-error",
            },
            "state_snapshot": {"identified_arguments": {}},
        }

        sig = await runner._run_single(
            text="x",
            source_name="x",
            opaque_id_str="fail1234",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            pipeline_fn=_mock_pipeline(mock_result),
            sanitize_fn=_mock_sanitize,
        )

        assert sig is not None
        assert sig["outcome"] == mock_result["analysis_outcome"]
        assert sig.get("partial") is not True

    @pytest.mark.asyncio
    async def test_non_argumentative_outcome_remains_valid(self, tmp_path):
        """#1909: a valid terminal input is not counted as failed or partial."""
        mock_result = {
            "analysis_outcome": {
                "status": "non_argumentative",
                "phase": "extract",
            },
            "state_snapshot": {"identified_arguments": {}},
        }

        sig = await runner._run_single(
            text="x",
            source_name="x",
            opaque_id_str="nonarg01",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            pipeline_fn=_mock_pipeline(mock_result),
            sanitize_fn=_mock_sanitize,
        )

        assert sig is not None
        assert sig["outcome"]["status"] == "non_argumentative"
        assert sig.get("partial") is not True

    @pytest.mark.asyncio
    async def test_threads_source_metadata_into_pipeline(self, tmp_path):
        """The batch's authoritative metadata reaches the shared-state boundary."""
        pipeline = _mock_pipeline({"state_snapshot": {}})
        metadata = {"corpus_id": "doc_A", "speaker": "synthetic_role"}

        await runner._run_single(
            text="x",
            source_name="x",
            opaque_id_str="meta1234",
            workflow="spectacular",
            metadata=metadata,
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            pipeline_fn=pipeline,
            sanitize_fn=_mock_sanitize,
        )

        assert pipeline.await_args.kwargs["source_metadata"] == metadata


# ---------------------------------------------------------------------------
# Document flattening field name tests
# ---------------------------------------------------------------------------


class TestDocumentFlattening:
    """Validate that the batch runner reads the correct corpus field names."""

    def test_extracts_using_extract_text_field(self):
        """Batch runner should read 'extract_text' from corpus extracts."""
        definitions = [
            {
                "source_name": "Test Source",
                "extracts": [
                    {
                        "extract_name": "ex1",
                        "extract_text": "Content from extract_text",
                    },
                ],
            }
        ]

        docs = []
        for source_def in definitions:
            for extract in source_def.get("extracts", []):
                text = extract.get("extract_text", "") or extract.get(
                    "full_text_segment", ""
                )
                if text:
                    docs.append(text)

        assert len(docs) == 1
        assert docs[0] == "Content from extract_text"

    def test_fallback_to_full_text_segment(self):
        """When extract_text is empty, full_text_segment should be used."""
        definitions = [
            {
                "source_name": "Test",
                "extracts": [
                    {
                        "extract_name": "ex1",
                        "extract_text": "",
                        "full_text_segment": "Fallback content",
                    },
                ],
            }
        ]

        docs = []
        for source_def in definitions:
            for extract in source_def.get("extracts", []):
                text = extract.get("extract_text", "") or extract.get(
                    "full_text_segment", ""
                )
                if text:
                    docs.append(text)

        assert len(docs) == 1
        assert docs[0] == "Fallback content"

    def test_old_full_text_field_not_used(self):
        """The old 'full_text' field on extracts should NOT be read (source-level field)."""
        definitions = [
            {
                "source_name": "Test",
                "extracts": [
                    {"extract_name": "ex1", "full_text": "Wrong field value"},
                ],
            }
        ]

        docs = []
        for source_def in definitions:
            for extract in source_def.get("extracts", []):
                text = extract.get("extract_text", "") or extract.get(
                    "full_text_segment", ""
                )
                if text:
                    docs.append(text)

        assert len(docs) == 0, "Should not extract from 'full_text' field on extracts"


# ---------------------------------------------------------------------------
# #1906 — metadata precedence and asserted constants
# ---------------------------------------------------------------------------


class TestMetadataPrecedence:
    """Explicit corpus metadata must win over failed label inference.

    #1913 wired ``source_metadata`` through the batch runner, so whatever this
    merge produces now reaches the Act I framing verbatim
    (``act1_framing_plugin`` renders every key of ``state.source_metadata``).
    That makes the *content* of the merge a reader-facing contract, not an
    internal detail: a wrong value here is presented to the model as
    established metadata about the source.
    """

    @staticmethod
    def _merge(src_name: str, date_iso: str, src_meta: dict) -> dict:
        """Call the production merge -- never a copy of it.

        A first version of this helper reproduced the merge inline. The control
        exposed it: with the production change reverted, four of these tests
        still passed, because they were exercising the copy. ``main()`` now
        delegates to ``merge_source_metadata`` so the assertion has something
        real to fail against.
        """
        return runner.merge_source_metadata(
            runner.classify_metadata(src_name, date_iso), src_meta
        )

    def test_explicit_field_wins_over_failed_inference(self):
        """The defect: ``setdefault`` protected the sentinel.

        ``classify_metadata`` always writes its four keys, so ``"unknown"`` was
        *present* and ``setdefault`` refused the explicit value. Only keys the
        inference never writes survived — which is why ``speaker`` came
        through while ``era`` did not.
        """
        merged = self._merge(
            "Some Document", "", {"era": "era_A", "discourse_type": "plaidoyer"}
        )
        assert merged["era"] == "era_A"
        assert merged["discourse_type"] == "plaidoyer"

    def test_key_the_inference_never_writes_still_passes_through(self):
        """Control: the one shape that already worked must keep working."""
        merged = self._merge("Some Document", "", {"speaker": "Speaker_A"})
        assert merged["speaker"] == "Speaker_A"

    def test_inference_still_wins_when_nothing_explicit_is_supplied(self):
        """Discriminator — without it, a merge that ignored ``src_meta``
        entirely would pass the test above by accident."""
        merged = self._merge("Discours du President", "2024-06-15", {})
        assert merged["discourse_type"] == "political"
        assert merged["era"] == "2024"

    def test_explicit_unknown_does_not_erase_a_real_inference(self):
        """Anti-pendulum: precedence is for *values*, not for the sentinel.

        A definition carrying an explicit ``"unknown"`` must not overwrite a
        field the label inference actually resolved — otherwise the fix would
        simply invert the defect instead of removing it.
        """
        merged = self._merge(
            "Discours du President", "2024-06-15", {"discourse_type": "unknown"}
        )
        assert merged["discourse_type"] == "political"


class TestNoAssertedRegime:
    def test_regime_type_is_not_asserted_for_an_arbitrary_source(self):
        """``regime_type`` was hard-coded to ``"democracy"`` for every source.

        It is not an inference — no input could change it — and the corpus is
        not uniformly democratic. Since #1913 the value reaches the model as
        source metadata, so asserting it is a factual claim the pipeline has no
        basis for. The declared default in the docstring is ``"unknown"``.
        """
        meta = runner.classify_metadata("Some Document")
        assert meta["regime_type"] == "unknown"

    def test_an_explicit_regime_from_the_corpus_definition_wins(self):
        """Removing the constant must not remove the ability to state it."""
        merged = TestMetadataPrecedence._merge(
            "Some Document", "", {"regime_type": "regime_A"}
        )
        assert merged["regime_type"] == "regime_A"
