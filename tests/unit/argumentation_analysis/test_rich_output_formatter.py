"""Tests for Rich CLI output formatter (#364)."""

import io
import json
import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.cli.output_formatter import (
    render_spectacular_result,
    render_state_snapshot,
    _section_ref,
    _truncate,
    _count_non_empty,
    _render_plain,
    HAS_RICH,
    SECTIONS,
)


# ── Fixtures ──

@pytest.fixture
def sample_result():
    """Minimal spectacular result with all sections populated."""
    return {
        "workflow_name": "standard",
        "state_snapshot": {
            "identified_arguments": {"arg1": "All men are mortal", "arg2": "Socrates is a man"},
            "extracts": [{"claim": "claim1"}, {"claim": "claim2"}],
            "fol_analysis_results": [{"formula": "∀x Man(x)→Mortal(x)"}],
            "propositional_analysis_results": [{"formula": "P → Q"}],
            "modal_analysis_results": [{"formula": "□(P → Q)"}],
            "nl_to_logic_translations": [{"source": "text", "logic": "P→Q"}],
            "identified_fallacies": {
                "f1": {"type": "ad_hominem", "justification": "Attacks the person"},
                "f2": {"type": "straw_man", "justification": "Misrepresents the argument"},
            },
            "neural_fallacy_scores": [{"fallacy": "ad_hominem", "score": 0.85}],
            "jtms_beliefs": {
                "b1": {"status": "IN", "confidence": 0.9},
                "b2": {"status": "OUT", "confidence": 0.3},
                "b3": {"status": "UNDECIDED", "confidence": 0.5, "valid": False},
            },
            "dung_frameworks": {
                "framework1": {"extensions": {"grounded": ["arg1", "arg2"]}},
            },
            "counter_arguments": [
                {"strategy": "reductio", "counter_content": "If P then contradiction"},
            ],
            "debate_transcripts": [{"round": 1, "proponent": "arg1", "opponent": "counter1"}],
            "governance_decisions": [{"method": "majority", "result": "accepted"}],
            "argument_quality_scores": {
                "arg1": {"overall": 0.85},
            },
            "final_conclusion": "The argument is valid with minor fallacies.",
        },
        "summary": {"completed": 5, "total": 8, "failed": 1, "skipped": 2},
        "capabilities_used": ["fact_extraction", "fallacy_detection", "dung_analysis"],
    }


@pytest.fixture
def empty_result():
    """Result with empty state snapshot."""
    return {
        "workflow_name": "light",
        "state_snapshot": {},
        "summary": {"completed": 0, "total": 3},
        "capabilities_used": [],
    }


# ── Helper function tests ──

class TestSectionRef:
    def test_valid_section_numbers(self):
        assert "see Section 1 (Extraction)" == _section_ref(1)
        assert "see Section 3 (Fallacies)" == _section_ref(3)
        assert "see Section 10 (Narrative)" == _section_ref(10)

    def test_unknown_section_number(self):
        assert "see Section 99" == _section_ref(99)


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello") == "hello"

    def test_exact_length_unchanged(self):
        text = "x" * 100
        assert _truncate(text, 100) == text

    def test_long_text_truncated(self):
        text = "x" * 150
        result = _truncate(text, 100)
        assert len(result) == 100
        assert result.endswith("...")


class TestCountNonEmpty:
    def test_all_empty(self):
        assert _count_non_empty({"a": [], "b": {}, "c": "", "d": None, "e": 0}) == 0

    def test_mixed(self):
        data = {"a": [1], "b": {}, "c": "text", "d": None}
        assert _count_non_empty(data) == 2

    def test_all_populated(self):
        data = {"a": [1], "b": {"k": "v"}, "c": "text"}
        assert _count_non_empty(data) == 3


# ── Plain renderer tests ──

class TestRenderPlain:
    def test_renders_without_error(self, sample_result, capsys):
        _render_plain(sample_result)
        output = capsys.readouterr().out
        assert "standard" in output
        assert "5/8" in output

    def test_empty_state(self, empty_result, capsys):
        _render_plain(empty_result)
        output = capsys.readouterr().out
        assert "light" in output


# ── Rich renderer tests ──

class TestRenderSpectacularResult:
    def test_rich_render_with_mock_console(self, sample_result):
        console = MagicMock()
        render_spectacular_result(sample_result, console=console)
        # Console.print should have been called multiple times
        assert console.print.call_count > 5

    def test_rich_render_empty_state(self, empty_result):
        console = MagicMock()
        render_spectacular_result(empty_result, console=console)
        # Should still print the header panel
        assert console.print.call_count >= 1

    def test_rich_render_no_state_snapshot(self):
        console = MagicMock()
        result = {"summary": {"completed": 1, "total": 2}, "capabilities_used": []}
        render_spectacular_result(result, console=console)
        assert console.print.call_count >= 1

    def test_fallback_to_plain_when_no_console(self, sample_result, capsys):
        with patch("argumentation_analysis.cli.output_formatter.HAS_RICH", False):
            render_spectacular_result(sample_result)
            output = capsys.readouterr().out
            assert "standard" in output

    def test_rich_header_content(self, sample_result):
        console = MagicMock()
        render_spectacular_result(sample_result, console=console)
        first_call_arg = console.print.call_args_list[0][0][0]
        # First print is the Panel header
        assert hasattr(first_call_arg, "title")  # It's a Rich Panel


class TestRenderStateSnapshot:
    def test_with_mock_state(self):
        console = MagicMock()
        mock_state = MagicMock()
        mock_state.get_state_snapshot.return_value = {
            "identified_arguments": {"a1": "test"},
        }
        render_state_snapshot(mock_state, console=console)
        assert console.print.call_count >= 1

    def test_with_non_mock_state(self):
        console = MagicMock()
        render_state_snapshot({}, console=console)
        # Should not crash even with non-object state


# ── Individual section renderer tests ──

class TestSectionRenderers:
    def test_extraction_section(self):
        from argumentation_analysis.cli.output_formatter import _render_extraction
        console = MagicMock()
        state = {"identified_arguments": {"a1": "test arg"}}
        _render_extraction(console, state)
        assert console.print.call_count >= 1

    def test_extraction_empty(self):
        from argumentation_analysis.cli.output_formatter import _render_extraction
        console = MagicMock()
        _render_extraction(console, {})
        assert console.print.call_count == 0

    def test_formal_logic_section(self):
        from argumentation_analysis.cli.output_formatter import _render_formal_logic
        console = MagicMock()
        state = {"fol_analysis_results": [{"formula": "∀x P(x)"}]}
        _render_formal_logic(console, state)
        assert console.print.call_count >= 1

    def test_fallacies_section(self):
        from argumentation_analysis.cli.output_formatter import _render_fallacies
        console = MagicMock()
        state = {
            "identified_fallacies": {
                "f1": {"type": "ad_hominem", "justification": "test"},
            }
        }
        _render_fallacies(console, state)
        assert console.print.call_count >= 1

    def test_jtms_section(self):
        from argumentation_analysis.cli.output_formatter import _render_jtms
        console = MagicMock()
        state = {
            "jtms_beliefs": {
                "b1": {"status": "IN", "confidence": 0.9},
                "b2": {"status": "OUT"},
            }
        }
        _render_jtms(console, state)
        assert console.print.call_count >= 1

    def test_dung_section(self):
        from argumentation_analysis.cli.output_formatter import _render_dung
        console = MagicMock()
        state = {
            "dung_frameworks": {
                "fw1": {"extensions": {"grounded": ["a1", "a2"]}},
            }
        }
        _render_dung(console, state)
        assert console.print.call_count >= 1

    def test_counter_arguments_section(self):
        from argumentation_analysis.cli.output_formatter import _render_counter_arguments
        console = MagicMock()
        state = {
            "counter_arguments": [{"strategy": "reductio", "counter_content": "test"}]
        }
        _render_counter_arguments(console, state)
        assert console.print.call_count >= 1

    def test_debate_section(self):
        from argumentation_analysis.cli.output_formatter import _render_debate
        console = MagicMock()
        state = {
            "debate_transcripts": [{"round": 1}],
            "governance_decisions": [{"method": "majority", "result": "accepted"}],
        }
        _render_debate(console, state)
        assert console.print.call_count >= 1

    def test_quality_section(self):
        from argumentation_analysis.cli.output_formatter import _render_quality
        console = MagicMock()
        state = {
            "argument_quality_scores": {"arg1": {"overall": 0.85}}
        }
        _render_quality(console, state)
        assert console.print.call_count >= 1

    def test_narrative_section(self):
        from argumentation_analysis.cli.output_formatter import _render_narrative
        console = MagicMock()
        state = {"final_conclusion": "The argument is sound."}
        result = {"state_snapshot": state}
        _render_narrative(console, state, result)
        assert console.print.call_count >= 1

    def test_narrative_with_cross_refs(self):
        from argumentation_analysis.cli.output_formatter import _render_narrative
        console = MagicMock()
        state = {
            "final_conclusion": "Conclusion here",
            "identified_fallacies": {"f1": {}},
            "jtms_beliefs": {"b1": {}},
            "dung_frameworks": {"fw1": {}},
        }
        result = {"state_snapshot": state}
        _render_narrative(console, state, result)
        # Should include cross-references
        printed = str(console.print.call_args_list)
        assert "Section 3" in printed or "Section 4" in printed


# ── Cross-reference tests ──

class TestCrossReferences:
    def test_sections_list_complete(self):
        assert len(SECTIONS) == 10
        numbers = [n for n, _ in SECTIONS]
        assert numbers == list(range(1, 11))

    def test_quality_refs_fallacies(self):
        """Quality section should cross-ref to fallacies (#3)."""
        console = MagicMock()
        from argumentation_analysis.cli.output_formatter import _render_quality
        state = {
            "argument_quality_scores": {"arg1": {"overall": 0.5}}
        }
        _render_quality(console, state)
        printed = str(console.print.call_args_list)
        assert "Section 3" in printed
