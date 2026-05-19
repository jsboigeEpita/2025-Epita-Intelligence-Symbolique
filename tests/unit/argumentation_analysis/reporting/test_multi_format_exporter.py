"""Tests for MultiFormatExporter — 6 format round-trips + schema checks."""

import csv
import io
import json
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock

import pytest

from argumentation_analysis.reporting.multi_format_exporter import MultiFormatExporter


@pytest.fixture
def mock_state():
    state = MagicMock()
    state.get_state_snapshot.return_value = {
        "identified_arguments": {"arg_1": "First argument", "arg_2": "Second argument"},
        "identified_fallacies": {
            "fallacy_1": {"type": "ad_hominem", "target": "arg_1", "justification": "attack on person"},
        },
        "counter_arguments": [{"strategy": "reductio", "content": "counter content"}],
        "argument_quality_scores": {"arg_1": {"overall": 0.8}},
        "jtms_beliefs": {"b1": {"status": "IN", "name": "belief_1"}},
        "dung_frameworks": {"fw_1": {"attacks": 3}},
        "governance_decisions": [{"method": "majority", "result": "approved"}],
        "debate_transcripts": [{"round": 1, "content": "debate text"}],
        "neural_fallacy_scores": [],
        "ranking_results": [],
        "aspic_results": [],
        "belief_revision_results": [],
        "final_conclusion": "The analysis is complete.",
        "fol_analysis_results": [],
        "propositional_analysis_results": [],
        "modal_analysis_results": [],
    }
    return state


@pytest.fixture
def exporter(mock_state):
    return MultiFormatExporter(mock_state)


class TestJSON:
    def test_to_json_valid(self, exporter):
        result = exporter.to_json(pretty=True)
        data = json.loads(result)
        assert "identified_arguments" in data
        assert data["identified_arguments"]["arg_1"] == "First argument"

    def test_to_json_compact(self, exporter):
        result = exporter.to_json(pretty=False)
        assert "\n" not in result

    def test_to_json_round_trip(self, exporter):
        result = exporter.to_json()
        data = json.loads(result)
        assert len(data["identified_arguments"]) == 2
        assert len(data["counter_arguments"]) == 1


class TestXML:
    def test_to_xml_well_formed(self, exporter):
        xml_str = exporter.to_xml()
        root = ET.fromstring(xml_str)
        assert root.tag == "analysis_state"

    def test_to_xml_contains_arguments(self, exporter):
        xml_str = exporter.to_xml()
        root = ET.fromstring(xml_str)
        args = root.find("identified-arguments")
        assert args is not None
        assert args.get("count") == "2"

    def test_to_xml_escaped_entities(self, mock_state):
        mock_state.get_state_snapshot.return_value = {
            "identified_arguments": {"arg_1": 'He said "hello" & <goodbye>'},
        }
        exporter = MultiFormatExporter(mock_state)
        xml_str = exporter.to_xml()
        root = ET.fromstring(xml_str)
        assert root is not None


class TestMarkdown:
    def test_to_markdown_has_headers(self, exporter):
        md = exporter.to_markdown()
        assert "# SCDA State Export" in md
        assert "## Arguments (2)" in md
        assert "## Fallacies (1)" in md

    def test_to_markdown_filtered_sections(self, exporter):
        md = exporter.to_markdown(sections=["identified_arguments", "final_conclusion"])
        assert "## Arguments" in md
        assert "## Final Conclusion" in md
        assert "Fallacies" not in md

    def test_to_markdown_empty_section(self, mock_state):
        mock_state.get_state_snapshot.return_value = {"identified_arguments": {}}
        exporter = MultiFormatExporter(mock_state)
        md = exporter.to_markdown()
        assert "## Arguments (0)" in md


class TestCSVBundle:
    def test_to_csv_bundle_creates_files(self, exporter, tmp_path):
        written = exporter.to_csv_bundle(tmp_path)
        filenames = [p.name for p in written]
        assert "args.csv" in filenames
        assert "fallacies.csv" in filenames
        assert "counter_args.csv" in filenames

    def test_to_csv_bundle_args_content(self, exporter, tmp_path):
        exporter.to_csv_bundle(tmp_path)
        args_file = tmp_path / "args.csv"
        with open(args_file, encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        assert len(reader) == 2
        assert reader[0]["id"] == "arg_1"


class TestHTML:
    def test_to_html_valid(self, exporter):
        html = exporter.to_html()
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "SCDA Spectacular" in html

    def test_to_html_has_collapsible_sections(self, exporter):
        html = exporter.to_html()
        assert "<details>" in html
        assert "</details>" in html

    def test_to_html_summary_cards(self, exporter):
        html = exporter.to_html()
        assert "card-count" in html
        assert "card-label" in html


class TestRichTerminal:
    def test_to_rich_terminal_fallback(self, exporter):
        result = exporter.to_rich_terminal()
        assert isinstance(result, str)
        assert len(result) > 0


class TestCacheReset:
    def test_cache_invalidated(self, mock_state):
        exporter = MultiFormatExporter(mock_state)
        _ = exporter.snapshot
        assert exporter._snapshot is not None
        exporter._reset_cache()
        assert exporter._snapshot is None
