# -*- coding: utf-8 -*-
"""#1909 slice 2 guard: the valid no-analysis terminal must be countable.

The tranche-cœur (#1909, shipped in PR #2024) taught the pipeline to stop the
DAG on a valid non-argumentative input as a *named terminal success*, but the
batch runner still summarized runs by raw ``outcome.status`` — ``ok`` meant
"an argumentative analysis ran", which ceased to distinguish the new terminal
from a success, and the corpus-level skip populations (``--max-chars``
filters, sources without documents) never entered the count at all.

These tests pin the reader-facing projection the issue DoD demands — five
separate buckets ``argumentative / non_argumentative / failed /
skipped_too_long / source_without_extract`` — plus the per-document
restitution for the valid no-analysis case and the ``document_classification``
surface on signatures.

Lives in ``tests/scripts/`` for the same measured reason as its
``test_corpus_batch_*`` siblings: the CI argv names only
``orchestration|services|workers|api`` under ``tests/integration/``, and a
guard the harness does not name is not a guard.

Anti-theater: no length threshold is a classifier here. ``--max-chars`` is a
corpus-management decision and counts as ``skipped_too_long``; the
non-argumentative terminal comes from the extraction contract
(``analysis_outcome`` / ``document_classification``) — never from sizes.

Synthetic opaque identifiers only — no encrypted dataset, no LLM call.
"""

import importlib.util
import os
from pathlib import Path

os.environ.setdefault("OPAQUE_ID_SALT", "test-salt-1909b")

from argumentation_analysis.evaluation.opaque_id import opaque_id

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "dataset" / "run_corpus_batch.py"
)


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_corpus_batch_under_test_1909b", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _definition(source_name, extracts, metadata=None):
    return {
        "source_name": source_name,
        "extracts": extracts,
        "metadata": metadata or {},
    }


class TestExpandCorpus:
    """The corpus expansion must count the populations it skips, not fold
    them into per-source causes invisible at batch level."""

    def test_skipped_too_long_counts_even_when_siblings_produce_docs(self):
        runner = _load_runner()
        definitions = [
            _definition(
                "Source_A - Doc_One 1940",
                [
                    {"extract_text": "short"},
                    {"extract_text": "x" * 500},
                ],
            ),
            _definition("Source_B - Doc_Two 1940", [{"extract_text": "y" * 500}]),
            _definition("Source_C - Doc_Three 1940", [{"extract_text": "short"}]),
        ]
        docs, omitted, skipped = runner.expand_corpus(definitions, max_chars=100)
        assert len(docs) == 2  # Source_A short extract + Source_C
        assert skipped == 2  # the long extracts
        assert [o["opaque_id"] for o in omitted] == [
            opaque_id("Source_B - Doc_Two 1940")
        ]

    def test_extract_without_text_is_a_source_without_extract(self):
        runner = _load_runner()
        definitions = [_definition("Source_D", [{"": None}])]
        docs, omitted, skipped = runner.expand_corpus(definitions, max_chars=0)
        assert docs == []
        assert skipped == 0
        assert len(omitted) == 1
        assert "without text" in omitted[0]["cause"]

    def test_zero_extract_source_is_omitted(self):
        runner = _load_runner()
        docs, omitted, skipped = runner.expand_corpus(
            [_definition("Source_E", [])], max_chars=0
        )
        assert docs == []
        assert skipped == 0
        assert omitted[0]["cause"] == "0 extract"

    def test_no_limit_skips_nothing_for_length(self):
        runner = _load_runner()
        definitions = [
            _definition("Source_F - Doc_Four 1940", [{"extract_text": "x" * 500}]),
        ]
        docs, omitted, skipped = runner.expand_corpus(definitions, max_chars=0)
        assert len(docs) == 1
        assert skipped == 0
        assert omitted == []


class TestSummarizeBatch:
    """The reader-facing projection: five separate buckets, raw statuses kept."""

    def test_argumentative_bucket_from_ok_status(self):
        runner = _load_runner()
        summary = runner.summarize_batch({"ok": 3}, 0, 0)
        assert summary["argumentative"] == 3
        assert summary["non_argumentative"] == 0
        assert summary["failed"] == 0

    def test_non_argumentative_bucket_is_its_own_bucket(self):
        runner = _load_runner()
        summary = runner.summarize_batch({"non_argumentative": 2}, 0, 0)
        assert summary["non_argumentative"] == 2
        assert summary["argumentative"] == 0
        assert summary["failed"] == 0
        assert "non_argumentative" not in summary["failed_detail"]

    def test_failed_bucket_absorbs_partials_and_unknown_keeping_detail(self):
        runner = _load_runner()
        counts = {
            "ok": 1,
            "non_argumentative": 2,
            "failed": 1,
            "partial_timeout": 1,
            "partial_error": 1,
            "unknown": 1,
        }
        summary = runner.summarize_batch(counts, 7, 3)
        assert summary["argumentative"] == 1
        assert summary["non_argumentative"] == 2
        assert summary["failed"] == 4
        assert summary["skipped_too_long"] == 7
        assert summary["source_without_extract"] == 3
        assert summary["failed_detail"] == {
            "failed": 1,
            "partial_timeout": 1,
            "partial_error": 1,
            "unknown": 1,
        }

    def test_empty_run_is_all_zero(self):
        runner = _load_runner()
        summary = runner.summarize_batch({}, 0, 0)
        assert summary == {
            "argumentative": 0,
            "non_argumentative": 0,
            "failed": 0,
            "skipped_too_long": 0,
            "source_without_extract": 0,
            "failed_detail": {
                "failed": 0,
                "partial_timeout": 0,
                "partial_error": 0,
                "unknown": 0,
            },
        }


class TestRenderBatchSummary:
    def test_summary_line_names_all_five_buckets(self):
        runner = _load_runner()
        summary = runner.summarize_batch(
            {"ok": 1, "non_argumentative": 2, "failed": 1}, 3, 4
        )
        line = runner.render_batch_summary(summary)
        for token in (
            "argumentative=1",
            "non_argumentative=2",
            "failed=1",
            "skipped_too_long=3",
            "source_without_extract=4",
        ):
            assert token in line

    def test_verdict_passes_without_failed_docs(self):
        runner = _load_runner()
        summary = runner.summarize_batch({"non_argumentative": 5}, 0, 1)
        assert "PASS" in runner.render_batch_verdict(summary)

    def test_verdict_fails_when_any_doc_failed(self):
        runner = _load_runner()
        summary = runner.summarize_batch({"partial_timeout": 1}, 0, 0)
        verdict = runner.render_batch_verdict(summary)
        assert "FAIL" in verdict
        assert "1" in verdict  # the gate names its count; the summary owns the detail


class TestDocumentClassificationSurface:
    def test_non_argumentative_outcome_adds_top_level_classification(self):
        runner = _load_runner()
        signature = {"outcome": {"status": "non_argumentative", "phase": "extract"}}
        runner._with_document_classification(signature, signature["outcome"])
        assert signature["document_classification"] == "non_argumentative"

    def test_ok_outcome_leaves_signature_unchanged(self):
        runner = _load_runner()
        signature = {"outcome": {"status": "ok"}}
        runner._with_document_classification(signature, signature["outcome"])
        assert "document_classification" not in signature


class TestNonArgumentativeRestitution:
    def test_restatement_names_material_kind_and_why(self):
        runner = _load_runner()
        text = runner.render_non_argumentative_restitution(
            "doc_A", {"status": "non_argumentative", "phase": "extract"}
        )
        assert "doc_A" in text
        assert "non-argumentative" in text
        assert "skipped" in text
        assert "not a failure" in text

    def test_restatement_is_short_reader_facing(self):
        runner = _load_runner()
        text = runner.render_non_argumentative_restitution(
            "doc_A", {"status": "non_argumentative", "phase": "extract"}
        )
        assert len(text) < 400
