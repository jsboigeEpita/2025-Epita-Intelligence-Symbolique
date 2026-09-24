"""#2346, residues that each hid a fact from the reader of a report or a log.

- The two extract-repair HTML reports wrote source names, extract names,
  messages, markers and the model's comments into the page without
  escaping: a ``<`` or ``&`` in a marker (a fragment of the source text)
  broke or rewrote the page.
- ``llm_cache.reset_raw_cache`` swallowed a failure to close the cache.
- ``LogicAgentFactory.create_agent`` logged two "DEBUG:" lines at INFO.
"""

import logging

from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.services import llm_cache
from argumentation_analysis.utils.extract_repair import marker_repair_logic
from argumentation_analysis.utils.extract_repair import verify_extracts_with_llm

HOSTILE = '<b>A & "B"</b>'
ESCAPED = "&lt;b&gt;A &amp; &quot;B&quot;&lt;/b&gt;"


def _render(generate_report, results, tmp_path):
    out = tmp_path / "report.html"
    generate_report(results, str(out))
    return out.read_text(encoding="utf-8")


class TestRepairReportsEscapeTheirValues:
    def test_marker_repair_report(self, tmp_path):
        html = _render(
            marker_repair_logic.generate_report,
            [
                {
                    "source_name": HOSTILE,
                    "extract_name": HOSTILE,
                    "status": "repaired",
                    "message": HOSTILE,
                    "old_start_marker": HOSTILE,
                    "new_start_marker": HOSTILE,
                    "old_end_marker": HOSTILE,
                    "new_end_marker": HOSTILE,
                    "explanation": HOSTILE,
                }
            ],
            tmp_path,
        )
        assert HOSTILE not in html
        # source, extract, message, 4 markers, explanation
        assert html.count(ESCAPED) == 8

    def test_llm_verification_report(self, tmp_path):
        html = _render(
            verify_extracts_with_llm.generate_report,
            [
                {
                    "source_name": HOSTILE,
                    "extract_name": HOSTILE,
                    "status": "valid",
                    "coherence": 4,
                    "relevance": 3,
                    "integrity": 5,
                    "comments": HOSTILE,
                },
                {
                    "source_name": "s2",
                    "extract_name": "e2",
                    "status": "error",
                    "message": HOSTILE,
                },
            ],
            tmp_path,
        )
        assert HOSTILE not in html
        # source, extract, comments, error message
        assert html.count(ESCAPED) == 4

    def test_report_markup_is_kept(self, tmp_path):
        """Control: the page's own markup is not escaped."""
        html = _render(
            marker_repair_logic.generate_report,
            [{"source_name": "s", "extract_name": "e", "status": "valid"}],
            tmp_path,
        )
        assert '<tr class="valid">' in html
        assert "<td>s</td>" in html


class _FailingCache:
    def close(self):
        raise OSError("disk gone")


def test_cache_close_failure_is_named(caplog, monkeypatch):
    monkeypatch.setattr(llm_cache, "_raw_cache", _FailingCache())
    monkeypatch.setattr(llm_cache, "_raw_cache_dir", "somewhere")
    with caplog.at_level(logging.WARNING, logger="LLMCache"):
        llm_cache.reset_raw_cache()
    assert llm_cache._raw_cache is None
    assert llm_cache._raw_cache_dir is None
    warnings = [r for r in caplog.records if r.name == "LLMCache"]
    assert len(warnings) == 1
    assert "disk gone" in warnings[0].getMessage()


def test_logic_factory_logs_no_debug_line_at_info(caplog):
    with caplog.at_level(logging.INFO, logger="Orchestration.LogicAgentFactory"):
        assert LogicAgentFactory.create_agent("no-such-logic", kernel=None) is None
    info = [
        r.getMessage()
        for r in caplog.records
        if r.name == "Orchestration.LogicAgentFactory" and r.levelno == logging.INFO
    ]
    assert info, "the factory's INFO lines were not captured"
    assert not [m for m in info if m.startswith("DEBUG:")]
