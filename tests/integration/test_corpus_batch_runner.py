"""Integration tests for scripts/dataset/run_corpus_batch.py.

Uses injected mock pipeline to avoid API calls.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "dataset"
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
        assert "raw_text" not in sig["state"]
        assert sig["state"]["argument_quality_scores"]["a1"]["overall"] == 0.9

        # Files exist
        assert (tmp_path / "dumps" / "state_full_abcd1234.json").exists()
        assert (tmp_path / "sigs" / "signature_abcd1234.json").exists()

    @pytest.mark.asyncio
    async def test_skip_existing(self, tmp_path):
        """skip_existing=True returns None when signature exists."""
        sigs = tmp_path / "sigs"
        sigs.mkdir()
        (sigs / "signature_abcd1234.json").write_text("{}", encoding="utf-8")

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
        assert sig is None

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

    @pytest.mark.asyncio
    async def test_partial_on_timeout(self, tmp_path):
        """Timeout produces partial signature."""

        async def _slow(*a, **kw):
            await asyncio.sleep(10)

        slow_fn = AsyncMock(side_effect=_slow)

        with patch(
            "run_corpus_batch.asyncio.wait_for", side_effect=asyncio.TimeoutError
        ):
            sig = await runner._run_single(
                text="x",
                source_name="x",
                opaque_id_str="tmo12345",
                workflow="spectacular",
                metadata={},
                state_dumps_dir=tmp_path / "dumps",
                signatures_dir=tmp_path / "sigs",
                skip_existing=False,
                pipeline_fn=slow_fn,
                sanitize_fn=_mock_sanitize,
            )

        assert sig is not None
        assert sig.get("partial") is True
