"""#3667 ask 2 — the cycle names the lenses that were absent.

The phase table records ``completed`` over a skipped output; this reads the
OUTPUT (``formal_synthesis_reports[*].phase_results.<phase>.status``) of the
harvested states and prints, per phase, on how many documents it was skipped.
Names and counts only — never a reason string. A report, not a gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from scripts.panel import run_cycle  # noqa: E402


def _write_state(states_dir, doc, phases_by_report):
    reports = [{"phase_results": phases} for phases in phases_by_report]
    (states_dir / f"state_full_{doc}.json").write_text(
        json.dumps({"formal_synthesis_reports": reports}), encoding="utf-8"
    )


def test_one_skipped_phase_is_named_with_its_document_count(tmp_path, capsys):
    """The DoD witness: two states, one with semantic_indexing skipped → the
    report names semantic_indexing with a count of 1."""
    _write_state(
        tmp_path,
        "doc_P",
        [{"semantic_indexing": {"status": "ran"}, "dung": {"status": "ran"}}],
    )
    _write_state(
        tmp_path,
        "doc_Q",
        [
            {
                "semantic_indexing": {
                    "status": "skipped: embedding_failed",
                    # a reason string must never reach the report
                    "reason": "HTTPError: 404 with some payload",
                },
                "dung": {"status": "ran"},
            }
        ],
    )
    counts = run_cycle.skipped_phases(tmp_path, ["doc_P", "doc_Q"])
    assert counts == {"semantic_indexing": 1}
    run_cycle.report_skipped_phases(counts)
    out = capsys.readouterr().out
    assert "semantic_indexing" in out and "1" in out
    assert "404" not in out and "payload" not in out


def test_an_all_ran_pair_prints_nothing(tmp_path, capsys):
    _write_state(tmp_path, "doc_P", [{"dung": {"status": "ran"}}])
    _write_state(tmp_path, "doc_Q", [{"dung": {"status": "ran"}}])
    counts = run_cycle.skipped_phases(tmp_path, ["doc_P", "doc_Q"])
    assert counts == {}
    run_cycle.report_skipped_phases(counts)
    assert capsys.readouterr().out == ""


def test_two_reports_on_one_document_count_once(tmp_path):
    """The count is per DOCUMENT, not per report."""
    _write_state(
        tmp_path,
        "doc_P",
        [
            {"semantic_indexing": {"status": "skipped: no_embedding_route"}},
            {"semantic_indexing": {"status": "skipped: no_embedding_route"}},
        ],
    )
    assert run_cycle.skipped_phases(tmp_path, ["doc_P"]) == {"semantic_indexing": 1}


def test_a_missing_state_is_skipped_not_counted(tmp_path):
    _write_state(tmp_path, "doc_P", [{"dung": {"status": "skipped: no_jvm"}}])
    counts = run_cycle.skipped_phases(tmp_path, ["doc_P", "doc_absent"])
    assert counts == {"dung": 1}


def test_a_state_without_reports_is_not_an_all_clear(tmp_path):
    (tmp_path / "state_full_doc_P.json").write_text("{}", encoding="utf-8")
    assert run_cycle.skipped_phases(tmp_path, ["doc_P"]) == {}
