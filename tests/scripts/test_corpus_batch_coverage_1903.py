# -*- coding: utf-8 -*-
"""#1903 guard: the corpus batch runner's silent exclusions must be visible.

The runner builds its documents inside the extract loop: a source with
``extracts: []`` produced zero documents without emitting a single line, while
the ``--max-chars`` filter three lines below logged its own exclusions. That
asymmetry is the defect: a final report writing "20 sources analyzed" would
have been silently wrong by 2. The guard pins, on synthetic definitions only
(no encrypted dataset, no LLM call):

- every source contributing 0 documents is named by opaque ID **with its
  cause** ("0 extract" vs "all filtered" vs "no text after fallback");
- a coverage summary ``N sources -> M documents; K sources without documents``
  is printed to STDOUT before processing starts (the surface #1874
  established for run-visible facts), not only at verbose level;
- anti-pendule: a zero-extract source's ``full_text`` must NEVER be fed to the
  pipeline — the fix is visibility, not a population change;
- a partial corpus stays usable (exit code 0).
"""

import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / "scripts" / "dataset" / "run_corpus_batch.py"
)

COVERED = "Synthetic Covered Alpha"
ZERO_EXTRACT = "Synthetic Zero Extract Beta"
ALL_FILTERED = "Synthetic Filtered Gamma"
NO_TEXT = "Synthetic No Text Delta"
BETA_SENTINEL = "BETA_FALLBACK_SENTINEL_must_never_reach_the_pipeline"

SYNTHETIC_DEFINITIONS = [
    {
        "source_name": COVERED,
        "extracts": [
            {"extract_name": "a1", "extract_text": "Alpha extract one."},
            {"extract_name": "a2", "extract_text": "Alpha extract two."},
        ],
    },
    {
        "source_name": ZERO_EXTRACT,
        "extracts": [],
        "full_text": BETA_SENTINEL,
    },
    {
        "source_name": ALL_FILTERED,
        "extracts": [{"extract_name": "g1", "extract_text": "g" * 500}],
    },
    {
        "source_name": NO_TEXT,
        "extracts": [
            {"extract_name": "d1", "extract_text": "", "full_text_segment": ""}
        ],
    },
]


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_corpus_batch_under_test_1903", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def batch(monkeypatch, tmp_path, capsys, caplog):
    """Drive the full ``main()`` argv on synthetic definitions."""
    from argumentation_analysis.evaluation.opaque_id import opaque_id

    runner = _load_runner()

    # Deterministic oids regardless of the machine env: pin an explicit
    # synthetic salt. The sources here are fabricated ("Synthetic ..."), so
    # the salt carries no secrecy; opaque_id has no default to fall back on
    # since #1973 and would raise without it.
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-1903")

    pipeline_calls = []

    async def fake_run_single(**kwargs):
        pipeline_calls.append(kwargs)
        return {
            "opaque_id": kwargs["opaque_id_str"],
            "partial": False,
            "outcome": {"status": "ok"},
        }

    monkeypatch.setattr(runner, "_run_single", fake_run_single)
    monkeypatch.setattr(
        "argumentation_analysis.core.utils.crypto_utils.derive_encryption_key",
        lambda passphrase: b"synthetic-key",
    )
    monkeypatch.setattr(
        "argumentation_analysis.core.io_manager.load_extract_definitions",
        lambda **kwargs: SYNTHETIC_DEFINITIONS,
    )
    monkeypatch.setenv("TEXT_CONFIG_PASSPHRASE", "synthetic")

    caplog.set_level(logging.INFO, logger="corpus_batch")
    rc = runner.main(["--max-chars", "100", "--output-dir", str(tmp_path / "sigs")])
    captured = capsys.readouterr()
    return SimpleNamespace(
        rc=rc,
        calls=pipeline_calls,
        stdout=captured.out,
        stderr=captured.err,
        log_text=caplog.text,
        oid=opaque_id,
    )


class TestOmittedSourceIsNamed:
    def test_zero_extract_source_named_with_cause(self, batch):
        oid = batch.oid(ZERO_EXTRACT)
        lines = [ln for ln in batch.log_text.splitlines() if oid in ln]
        assert any("0 extract" in ln for ln in lines), (
            "#1903: a source with extracts == [] produces zero documents "
            "without any log line -- the omission must be named with its "
            f"cause, got {lines!r}"
        )

    def test_all_filtered_source_named_with_cause(self, batch):
        oid = batch.oid(ALL_FILTERED)
        lines = [ln for ln in batch.log_text.splitlines() if oid in ln]
        assert any("filtered" in ln for ln in lines), (
            "#1903: a source whose every extract is filtered by --max-chars "
            "contributes zero documents; the source-level omission must be "
            f"named with its cause, got {lines!r}"
        )

    def test_no_text_extract_is_logged(self, batch):
        oid = batch.oid(NO_TEXT)
        lines = [ln for ln in batch.log_text.splitlines() if oid in ln]
        assert any("text" in ln for ln in lines), (
            "#1903: the silent ``continue`` on the empty-fallback chain "
            "(l.429) emitted nothing -- it must log like the --max-chars "
            f"filter does, got {lines!r}"
        )


class TestCoverageSummary:
    def test_summary_on_stdout_before_processing(self, batch):
        out = batch.stdout
        assert "4 sources" in out and "2 documents" in out, (
            "#1903: the coverage summary (N sources -> M documents) must "
            "appear in the run's standard output, not only at verbose level; "
            f"stdout was {out!r}"
        )
        assert "3 sources without documents" in out, (
            "#1903: the summary must state how many sources contribute no "
            f"document; stdout was {out!r}"
        )
        for name in (ZERO_EXTRACT, ALL_FILTERED, NO_TEXT):
            assert (
                batch.oid(name) in out
            ), f"#1903: the summary must name omitted source {batch.oid(name)}"


class TestMaxDocsCoverage1919:
    @staticmethod
    def _run(monkeypatch, tmp_path, capsys, max_docs):
        from argumentation_analysis.evaluation.opaque_id import opaque_id

        runner = _load_runner()
        definitions = [
            {
                "source_name": "Synthetic Kept Source",
                "extracts": [{"extract_text": "Kept document."}],
            },
            {
                "source_name": "Synthetic Truncated Source",
                "extracts": [{"extract_text": "Truncated document."}],
            },
        ]
        calls = []

        async def fake_run_single(**kwargs):
            calls.append(kwargs)
            return {"opaque_id": kwargs["opaque_id_str"], "outcome": {"status": "ok"}}

        monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-1903")
        monkeypatch.setattr(runner, "_run_single", fake_run_single)
        monkeypatch.setattr(
            "argumentation_analysis.core.utils.crypto_utils.derive_encryption_key",
            lambda passphrase: b"synthetic-key",
        )
        monkeypatch.setattr(
            "argumentation_analysis.core.io_manager.load_extract_definitions",
            lambda **kwargs: definitions,
        )
        monkeypatch.setenv("TEXT_CONFIG_PASSPHRASE", "synthetic")

        rc = runner.main(
            [
                "--max-docs",
                str(max_docs),
                "--output-dir",
                str(tmp_path / f"max-{max_docs}"),
            ]
        )
        return rc, calls, capsys.readouterr().out, opaque_id

    def test_truncation_names_the_population_it_excludes(
        self, monkeypatch, tmp_path, capsys
    ):
        rc, calls, out, opaque_id = self._run(monkeypatch, tmp_path, capsys, max_docs=1)

        assert rc == 0
        assert len(calls) == 1
        assert "2 documents before --max-docs" in out
        assert "1 documents processed" in out
        assert "1 sources excluded by --max-docs" in out
        assert opaque_id("Synthetic Truncated Source") in out

    def test_unlimited_coverage_line_is_byte_identical(
        self, monkeypatch, tmp_path, capsys
    ):
        rc, calls, out, _opaque_id = self._run(
            monkeypatch, tmp_path, capsys, max_docs=0
        )

        assert rc == 0
        assert len(calls) == 2
        # The coverage line itself is the contract; it stays byte-identical
        # and first in stdout. #1909 slice 2 adds the batch summary and the
        # gate verdict *after* it, so whole-stdout equality no longer holds —
        # the pin moves to the line, which is what #1903 actually promised.
        assert out.splitlines()[0] == (
            "Coverage: 2 sources -> 2 documents; "
            "0 sources without documents: []"
        )


class TestBatchOutcomeAggregation1913:
    def test_failed_document_does_not_abort_later_documents(
        self, monkeypatch, tmp_path, caplog
    ):
        """The campaign continues, but its aggregate process status fails honestly."""
        runner = _load_runner()
        definitions = [
            {
                "source_name": "Synthetic Failed Source",
                "extracts": [{"extract_text": "Failed document."}],
            },
            {
                "source_name": "Synthetic Later Source",
                "extracts": [{"extract_text": "Later document."}],
            },
        ]
        calls = []

        async def fake_run_single(**kwargs):
            calls.append(kwargs["opaque_id_str"])
            if len(calls) == 1:
                return {
                    "opaque_id": kwargs["opaque_id_str"],
                    "outcome": {
                        "status": "failed",
                        "phase": "extract",
                        "reason": "failed:synthetic-auth-error",
                    },
                }
            return {
                "opaque_id": kwargs["opaque_id_str"],
                "outcome": {"status": "ok"},
            }

        monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-1903")
        monkeypatch.setattr(runner, "_run_single", fake_run_single)
        monkeypatch.setattr(
            "argumentation_analysis.core.utils.crypto_utils.derive_encryption_key",
            lambda passphrase: b"synthetic-key",
        )
        monkeypatch.setattr(
            "argumentation_analysis.core.io_manager.load_extract_definitions",
            lambda **kwargs: definitions,
        )
        monkeypatch.setenv("TEXT_CONFIG_PASSPHRASE", "synthetic")
        caplog.set_level(logging.INFO, logger="corpus_batch")

        rc = runner.main(["--output-dir", str(tmp_path / "outcomes")])

        assert len(calls) == 2, "the failed first document must not abort the batch"
        assert rc == 1
        assert "'failed': 1" in caplog.text
        assert "'ok': 1" in caplog.text


class TestPopulationUnchanged:
    def test_only_extractable_documents_reach_the_pipeline(self, batch):
        assert len(batch.calls) == 2, (
            "#1903 population pin: exactly the 2 extracts of the covered "
            f"source must be processed, got {len(batch.calls)}"
        )
        texts = [c["text"] for c in batch.calls]
        assert texts == ["Alpha extract one.", "Alpha extract two."]

    def test_zero_extract_source_full_text_never_analyzed(self, batch):
        fed = " ".join(c["text"] for c in batch.calls)
        assert BETA_SENTINEL not in fed, (
            "#1903 anti-pendule: making the zero-extract source fall back on "
            "its full_text would change the analyzed population under cover "
            "of traceability -- visibility only, never a population change"
        )

    def test_partial_corpus_remains_usable(self, batch):
        assert batch.rc == 0, (
            "#1903: the omission must stay visible, not fatal -- a partial "
            "corpus has to remain exploitable"
        )
