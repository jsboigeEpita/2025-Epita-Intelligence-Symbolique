# tests/unit/argumentation_analysis/utils/test_config_utils.py
"""Tests for config_utils — configuration source lookup by ID."""

import pytest

from argumentation_analysis.utils.config_utils import find_sources_in_config_by_ids


class TestFindSourcesInConfigByIds:
    # ── List-based config ──

    def test_empty_ids(self):
        data = [{"id": "s1", "name": "Source1"}]
        found, ids = find_sources_in_config_by_ids(data, [])
        assert found == []
        assert ids == set()

    def test_find_single_in_list(self):
        data = [
            {"id": "s1", "name": "Source1"},
            {"id": "s2", "name": "Source2"},
        ]
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        assert len(found) == 1
        assert found[0]["name"] == "Source1"
        assert ids == {"s1"}

    def test_find_multiple_in_list(self):
        data = [
            {"id": "s1", "name": "S1"},
            {"id": "s2", "name": "S2"},
            {"id": "s3", "name": "S3"},
        ]
        found, ids = find_sources_in_config_by_ids(data, ["s1", "s3"])
        assert len(found) == 2
        assert ids == {"s1", "s3"}

    def test_id_not_found_in_list(self):
        data = [{"id": "s1", "name": "S1"}]
        found, ids = find_sources_in_config_by_ids(data, ["s999"])
        assert found == []
        assert ids == set()

    def test_partial_match_in_list(self):
        data = [
            {"id": "s1", "name": "S1"},
            {"id": "s2", "name": "S2"},
        ]
        found, ids = find_sources_in_config_by_ids(data, ["s1", "s999"])
        assert len(found) == 1
        assert ids == {"s1"}

    def test_duplicate_ids_in_list(self):
        """If the same ID appears twice in data, only first is returned."""
        data = [
            {"id": "s1", "name": "First"},
            {"id": "s1", "name": "Duplicate"},
        ]
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        assert len(found) == 1
        assert found[0]["name"] == "First"

    def test_non_dict_items_in_list_skipped(self):
        data = ["not_a_dict", {"id": "s1", "name": "S1"}]
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        assert len(found) == 1
        assert ids == {"s1"}

    def test_empty_list(self):
        found, ids = find_sources_in_config_by_ids([], ["s1"])
        assert found == []
        assert ids == set()

    # ── Dict-based config ──

    def test_dict_with_sources_key(self):
        data = {
            "sources": [
                {"id": "s1", "name": "S1"},
                {"id": "s2", "name": "S2"},
            ]
        }
        found, ids = find_sources_in_config_by_ids(data, ["s2"])
        assert len(found) == 1
        assert found[0]["name"] == "S2"

    def test_dict_with_items_key(self):
        data = {"items": [{"id": "s1", "name": "S1"}]}
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        assert len(found) == 1

    def test_dict_with_data_key(self):
        data = {"data": [{"id": "s1", "name": "S1"}]}
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        assert len(found) == 1

    def test_dict_id_as_key(self):
        data = {
            "s1": {"name": "Source1"},
        }
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        assert len(found) == 1
        assert found[0]["name"] == "Source1"
        # Should have id added
        assert found[0]["id"] == "s1"

    def test_dict_id_as_key_with_id_field(self):
        data = {
            "s1": {"id": "s1", "name": "Source1"},
        }
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        assert len(found) == 1
        assert found[0]["id"] == "s1"

    def test_dict_id_key_non_dict_value(self):
        data = {"s1": "not_a_dict"}
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        # Non-dict value should be warned about, not added
        assert len(found) == 0

    def test_dict_is_single_source(self):
        data = {"id": "s1", "name": "SingleSource"}
        found, ids = find_sources_in_config_by_ids(data, ["s1"])
        assert len(found) == 1
        assert found[0]["name"] == "SingleSource"

    # ── Unsupported format ──

    def test_unsupported_type(self):
        found, ids = find_sources_in_config_by_ids("not_valid", ["s1"])
        assert found == []
        assert ids == set()

    def test_none_type(self):
        found, ids = find_sources_in_config_by_ids(None, ["s1"])
        assert found == []
        assert ids == set()
