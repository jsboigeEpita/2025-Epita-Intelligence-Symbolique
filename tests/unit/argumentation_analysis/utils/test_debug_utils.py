# tests/unit/argumentation_analysis/utils/test_debug_utils.py
"""Tests for debug_utils — extract sources display and inspection."""

import json
import pytest
from pathlib import Path

from argumentation_analysis.utils.debug_utils import display_extract_sources_details


class TestDisplayExtractSourcesDetails:
    """Tests for the display function — verifies it doesn't crash with various inputs."""

    def test_empty_list(self):
        """Should handle empty list without errors."""
        display_extract_sources_details([])

    def test_non_list_input(self):
        """Should handle non-list input gracefully."""
        display_extract_sources_details("not a list")

    def test_single_source(self):
        """Should display basic source info."""
        data = [
            {
                "id": "s1",
                "source_name": "TestSource",
                "path": "/test/path",
                "host_parts": ["example", "com"],
                "extracts": [
                    {
                        "extract_name": "E1",
                        "start_marker": "start",
                        "end_marker": "end",
                    }
                ],
            }
        ]
        display_extract_sources_details(data)

    def test_source_id_filter(self):
        data = [
            {"id": "s1", "source_name": "Source1", "full_text": "content"},
            {"id": "s2", "source_name": "Source2"},
        ]
        # Should not crash when filtering by ID
        display_extract_sources_details(data, source_id_to_inspect="s1")

    def test_source_id_not_found(self):
        data = [{"id": "s1", "source_name": "Source1"}]
        # Should not crash when ID doesn't exist
        display_extract_sources_details(data, source_id_to_inspect="nonexistent")

    def test_source_without_full_text(self):
        data = [{"id": "s1", "source_name": "S1"}]
        display_extract_sources_details(data, source_id_to_inspect="s1")

    def test_show_all(self):
        data = [
            {"id": "s1", "source_name": "Source1", "host_parts": [], "extracts": []},
            {"id": "s2", "source_name": "Source2", "host_parts": [], "extracts": []},
        ]
        display_extract_sources_details(data, show_all=True)

    def test_show_all_french(self):
        data = [
            {
                "id": "s1",
                "source_name": "lemonde article",
                "path": "",
                "host_parts": ["lemonde", "fr"],
                "extracts": [],
            },
            {
                "id": "s2",
                "source_name": "english source",
                "path": "",
                "host_parts": ["example", "com"],
                "extracts": [],
            },
        ]
        display_extract_sources_details(data, show_all_french=True)

    def test_show_all_overrides_french(self):
        data = [
            {
                "id": "s1",
                "source_name": "any",
                "path": "",
                "host_parts": [],
                "extracts": [],
            }
        ]
        display_extract_sources_details(data, show_all=True, show_all_french=True)

    def test_non_dict_items_skipped(self):
        data = ["not_a_dict", {"id": "s1", "source_name": "S1", "host_parts": [], "extracts": []}]
        display_extract_sources_details(data, show_all=True)

    def test_source_with_full_text_preview(self):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "host_parts": [],
                "full_text": "A" * 300,
                "extracts": [],
            }
        ]
        display_extract_sources_details(data, show_all=True)

    def test_source_with_empty_full_text(self):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "host_parts": [],
                "full_text": "",
                "extracts": [],
            }
        ]
        display_extract_sources_details(data, show_all=True)

    def test_output_json(self, tmp_path):
        data = [{"id": "s1", "source_name": "S1"}]
        output_path = str(tmp_path / "output.json")
        display_extract_sources_details(data, output_json_path=output_path)
        written = json.loads(Path(output_path).read_text(encoding="utf-8"))
        assert written == data

    def test_output_json_creates_dirs(self, tmp_path):
        data = [{"id": "s1"}]
        output_path = str(tmp_path / "sub" / "dir" / "output.json")
        display_extract_sources_details(data, output_json_path=output_path)
        assert Path(output_path).exists()

    def test_default_display_few_items(self):
        """Default mode displays first 2 items."""
        data = [
            {"id": "s1", "source_name": "S1", "full_text": "text1"},
            {"id": "s2", "source_name": "S2"},
            {"id": "s3", "source_name": "S3"},
        ]
        display_extract_sources_details(data)

    def test_empty_default_display(self):
        display_extract_sources_details([])

    def test_french_keywords_in_path(self):
        data = [
            {
                "id": "s1",
                "source_name": "doc",
                "path": "/assemblee-nationale/doc",
                "host_parts": [],
                "extracts": [],
            }
        ]
        display_extract_sources_details(data, show_all_french=True)

    def test_french_keywords_in_domain(self):
        data = [
            {
                "id": "s1",
                "source_name": "doc",
                "path": "",
                "host_parts": ["conseil-constitutionnel", "fr"],
                "extracts": [],
            }
        ]
        display_extract_sources_details(data, show_all_french=True)

    def test_no_french_sources_found(self):
        data = [
            {
                "id": "s1",
                "source_name": "english",
                "path": "/en/doc",
                "host_parts": ["example", "com"],
                "extracts": [],
            }
        ]
        display_extract_sources_details(data, show_all_french=True)
