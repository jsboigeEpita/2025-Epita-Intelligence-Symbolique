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
    async def test_signature_carries_run_provenance(self, tmp_path):
        """#2045 : la signature doit porter la provenance du run.

        Un dump d'état adressé par un hash sans provenance n'est pas
        attributable à un run (mesuré : 41 dumps balayés sans retrouver
        celui d'un run rendu). La signature écrite au moment du dump doit
        porter horodatage, SHA de code et identité de modèle.
        """
        mock_result = {
            "state_snapshot": {"source_id": "doc_test"},
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
        prov = sig.get("provenance")
        assert isinstance(prov, dict), "signature sans bloc provenance (#2045)"
        assert prov.get("run_started_utc"), "horodatage de run absent"
        assert "code_sha" in prov, "version de code absente"
        assert "chat_model_id" in prov, "identité de modèle absente"
        assert prov.get("params", {}).get("workflow") == "spectacular"

        # Le bloc est persisté dans le fichier, pas seulement en mémoire —
        # c'est le fichier que le forensic lira.
        on_disk = json.loads(
            (tmp_path / "sigs" / "signature_abcd1234.json").read_text(encoding="utf-8")
        )
        assert "provenance" in on_disk
        assert on_disk["provenance"]["run_started_utc"] == prov["run_started_utc"]

    @pytest.mark.asyncio
    async def test_signature_reprobes_environment_at_doc_end(self, tmp_path):
        """#2282 : la signature re-sonde l'environment à son écriture.

        Le provenance de lot est sondé AVANT la boucle : son jvm_started
        est nécessairement False (rien n'a booté). Si la signature le
        réutilise tel quel, un run sain estampille sa propre signature
        jvm_started=False — le stamp loud ment sur le run qu'il atteste
        (mesuré : run sain 74 jars, phases Tweety exécutées, signature
        jvm_started=False car probe de début de lot).
        """
        batch_prov = {
            "chat_model_id": "m",
            "code_sha": "s",
            "params": {"workflow": "spectacular", "timeout_s": 30},
            "run_started_utc": "2026-09-18T00:00:00Z",
            "environment": {"jvm": {"jvm_started": False, "probe": "batch-start"}},
        }

        sig = await runner._run_single(
            text="Test text",
            source_name="Test Source",
            opaque_id_str="env_probe_doc",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            pipeline_fn=_mock_pipeline({"state_snapshot": {}}),
            sanitize_fn=_mock_sanitize,
            provenance=batch_prov,
        )

        assert sig is not None
        prov = sig["provenance"]
        # L'identité de lot (#2045) est préservée
        assert prov["run_started_utc"] == "2026-09-18T00:00:00Z"
        assert prov["params"]["workflow"] == "spectacular"
        # L'environment est re-sondé à la fin du doc, pas partagé avec le lot
        assert prov["environment"] is not batch_prov["environment"]
        assert prov["environment"]["jvm"].get("probe") is None
        assert isinstance(prov["environment"]["jvm"].get("jvm_started"), bool)

    @pytest.mark.asyncio
    async def test_signature_persists_zero_shot_surplus(self, tmp_path):
        """#2298 : la signature porte la projection structurée du surplus.

        Tri-état : un état vivant rend une projection mesurée (même vide) ;
        un run sans objet d'état rend ``unavailable_reason`` — jamais une
        case vide indiscernable d'un instrument débranché.
        """
        from types import SimpleNamespace

        async def _pipe_with_state(*a, **k):
            return {
                "analysis_outcome": {"status": "ok"},
                "state_snapshot": {"source_id": "doc_test"},
                "unified_state": SimpleNamespace(),
            }

        sig = await runner._run_single(
            text="Test text",
            source_name="Test Source",
            opaque_id_str="surplus_doc",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            pipeline_fn=_pipe_with_state,
            sanitize_fn=_mock_sanitize,
        )
        assert sig is not None
        proj = sig["zero_shot_surplus"]
        assert "unavailable_reason" not in proj
        assert "carries_non_procedural_surplus" in proj

        async def _pipe_partial(*a, **k):
            raise asyncio.TimeoutError()

        sig2 = await runner._run_single(
            text="Test text",
            source_name="Test Source",
            opaque_id_str="surplus_partial",
            workflow="spectacular",
            metadata={},
            state_dumps_dir=tmp_path / "dumps",
            signatures_dir=tmp_path / "sigs",
            skip_existing=False,
            timeout=1,
            pipeline_fn=_pipe_partial,
            sanitize_fn=_mock_sanitize,
        )
        assert sig2 is not None
        assert (
            sig2["zero_shot_surplus"]["unavailable_reason"]
            == "no state object (partial run)"
        )

    def test_surplus_aggregate_non_vacuity(self):
        """#2298 : un agrégat vide DIT sa vacuité mesurée, avec ventilation."""

        thin = {
            "zero_shot_surplus": {
                "established_items": [],
                "established_by_nature": {},
                "procedural_items": 2,
                "carries_non_procedural_surplus": False,
            }
        }
        out = runner.render_surplus_aggregate([thin, thin])
        assert "0/2 documents carry non-procedural surplus" in out
        assert "measured absence" in out, "an empty aggregate says it"

        rich = {
            "zero_shot_surplus": {
                "established_items": [
                    {"nature": "decisif_formel", "cites": ["FOL"]}
                ],
                "established_by_nature": {"decisif_formel": 1},
                "procedural_items": 0,
                "carries_non_procedural_surplus": True,
            }
        }
        out2 = runner.render_surplus_aggregate([rich, thin])
        assert "1/2 documents carry non-procedural surplus" in out2
        assert "decisif_formel=1" in out2

        partial = {"zero_shot_surplus": {"unavailable_reason": "no state object (partial run)"}}
        out3 = runner.render_surplus_aggregate([rich, partial])
        assert "1/1 documents carry" in out3
        assert "1 document(s) unavailable" in out3

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
