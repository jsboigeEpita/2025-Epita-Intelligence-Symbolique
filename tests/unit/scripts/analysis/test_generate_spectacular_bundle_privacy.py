"""Privacy regression tests for generate_spectacular_bundle scrub pipeline.

Covers 3 leak vectors discovered in Rounds 176/179/180:
  - Vector 1: LLM paraphrase fields (premisses, conclusion, justification, etc.)
  - Vector 2: Entity regex patterns (\b word-boundary + substring for snake_case)
  - Vector 3: FOL formulae + dict keys in nl_to_logic_translations
  - Vector 4: Full integration end-to-end scrub

Entity names in test fixtures are intentionally present to verify scrubbing.
Rule 4 (opaque IDs in commits) applies to PR body and commit messages, not test code.
"""

import copy
import json
import pytest

from scripts.analysis.generate_spectacular_bundle import (
    _scrub_state_for_export,
    _global_entity_scrub,
    _ENTITY_PATTERN,
    _ENTITY_SUBSTR_PATTERN,
    _NL_SCRUB_KEYS,
    _PRIVACY_STRIP_FIELDS,
)


# ---------------------------------------------------------------------------
# Vector 1 — LLM paraphrase fields scrubbed
# ---------------------------------------------------------------------------

class TestVector1LLMParaphrase:
    """Verify all NL fields in _NL_SCRUB_KEYS are replaced with <scrubbed>."""

    def _make_state_with_args(self):
        return {
            "identified_arguments": {
                "arg_1": {
                    "premisses": "The speaker claims that foreign policy is failing",
                    "conclusion": "Therefore we must act",
                    "confidence": 0.85,
                    "source_id": "src_0",
                },
                "arg_2": {
                    "premisses": "Economic sanctions have not worked against the adversary",
                    "conclusion": "Military action is justified",
                    "confidence": 0.7,
                },
            }
        }

    def test_argument_premesses_scrubbed(self):
        result = _scrub_state_for_export(self._make_state_with_args())
        for arg in result["identified_arguments"].values():
            assert arg["premisses"] == "<scrubbed>"

    def test_argument_conclusion_scrubbed(self):
        result = _scrub_state_for_export(self._make_state_with_args())
        for arg in result["identified_arguments"].values():
            assert arg["conclusion"] == "<scrubbed>"

    def test_argument_non_nl_fields_preserved(self):
        result = _scrub_state_for_export(self._make_state_with_args())
        assert result["identified_arguments"]["arg_1"]["confidence"] == 0.85
        assert result["identified_arguments"]["arg_1"]["source_id"] == "src_0"

    def test_fallacy_justification_scrubbed(self):
        state = {
            "identified_fallacies": {
                "fal_1": {
                    "justification": "This is an ad hominem because the speaker attacks the opponent personally",
                    "fallacy_type": "ad_hominem",
                    "severity": "high",
                }
            }
        }
        result = _scrub_state_for_export(state)
        assert result["identified_fallacies"]["fal_1"]["justification"] == "<scrubbed>"

    def test_counter_arguments_text_scrubbed(self):
        state = {
            "counter_arguments": [
                {
                    "text": "However the economic data shows otherwise",
                    "strategy": "counter_example",
                    "counter_content": "The GDP figures contradict this claim",
                },
                {
                    "text": "An alternative reading suggests moderation",
                    "strategy": "reformulation",
                },
            ]
        }
        result = _scrub_state_for_export(state)
        for ca in result["counter_arguments"]:
            assert ca["text"] == "<scrubbed>"
            if "counter_content" in ca:
                assert ca["counter_content"] == "<scrubbed>"

    def test_debate_transcripts_nl_scrubbed(self):
        state = {
            "debate_transcripts": [
                {"speaker": "proponent", "content": "a" * 100},
                {"speaker": "opponent", "content": "b" * 100, "topic": "foreign policy"},
            ]
        }
        result = _scrub_state_for_export(state)
        for dt in result["debate_transcripts"]:
            assert dt.get("content") == "<scrubbed>"
            if "topic" in dt:
                assert dt["topic"] == "<scrubbed>"

    def test_belief_sets_long_content_scrubbed(self):
        state = {
            "belief_sets": {
                "bs_1": {"content": "x" * 100, "type": "PL"},
                "bs_2": {"content": "short", "type": "FOL"},
            }
        }
        result = _scrub_state_for_export(state)
        assert result["belief_sets"]["bs_1"]["content"] == "<scrubbed>"
        # Short content preserved
        assert result["belief_sets"]["bs_2"]["content"] == "short"

    def test_final_conclusion_scrubbed(self):
        state = {"final_conclusion": "The argument structure reveals a pattern of " + "w" * 100}
        result = _scrub_state_for_export(state)
        assert result["final_conclusion"] == "<scrubbed>"

    def test_privacy_strip_fields_removed_entirely(self):
        state = {
            "raw_text": "full plaintext here",
            "full_text": "another full text",
            "source_text": "source material",
            "identified_arguments": {"arg_1": {"conclusion": "test conclusion here"}},
        }
        result = _scrub_state_for_export(state)
        assert "raw_text" not in result
        assert "full_text" not in result
        assert "source_text" not in result
        # Non-stripped fields remain
        assert "identified_arguments" in result

    def test_extracts_long_values_scrubbed(self):
        state = {"extracts": {"ext_1": "p" * 100, "ext_2": "short"}}
        result = _scrub_state_for_export(state)
        assert result["extracts"]["ext_1"] == "<scrubbed>"
        assert result["extracts"]["ext_2"] == "short"


# ---------------------------------------------------------------------------
# Vector 2 — Entity regex patterns
# ---------------------------------------------------------------------------

class TestVector2EntityPatterns:
    """Verify _ENTITY_PATTERN (\b) and _ENTITY_SUBSTR_PATTERN (substring)."""

    def test_word_boundary_match(self):
        assert _ENTITY_PATTERN.search("Trump said something")

    def test_word_boundary_case_insensitive(self):
        assert _ENTITY_PATTERN.search("trump is mentioned")

    def test_no_word_boundary_in_snake_case(self):
        """_ENTITY_PATTERN uses \\b which doesn't match inside snake_case."""
        text = "title_donald_trump_un"
        # \b doesn't fire within underscores — this is WHY we need _ENTITY_SUBSTR_PATTERN
        assert not _ENTITY_PATTERN.search(text)

    def test_substring_matches_snake_case(self):
        text = "title_donald_trump_un"
        assert _ENTITY_SUBSTR_PATTERN.search(text)

    def test_substring_matches_compound_key(self):
        assert _ENTITY_SUBSTR_PATTERN.search("putin_speech_2024_analysis")

    def test_global_scrub_replaces_entity_string(self):
        result = _global_entity_scrub("Trump gave a speech")
        assert result == "<scrubbed>"

    def test_global_scrub_replaces_snake_case_entity(self):
        result = _global_entity_scrub("title_donald_trump_united_nations")
        assert result == "<scrubbed>"

    def test_global_scrub_preserves_clean_string(self):
        result = _global_entity_scrub("a normal string without entities")
        assert result == "a normal string without entities"

    def test_global_scrub_replaces_mixed_entities(self):
        result = _global_entity_scrub("Iran/Russia relations")
        assert result == "<scrubbed>"

    def test_global_scrub_dict_values(self):
        data = {"key1": "trump held a rally", "key2": "safe value"}
        result = _global_entity_scrub(data)
        assert result["key1"] == "<scrubbed>"
        assert result["key2"] == "safe value"

    def test_global_scrub_dict_keys_with_entity(self):
        data = {"trump_speech_analysis": "value", "safe_key": "other"}
        result = _global_entity_scrub(data)
        # Key containing entity should be renamed to key_N
        assert "trump_speech_analysis" not in result
        assert any(k.startswith("key_") for k in result)
        assert "safe_key" in result

    def test_global_scrub_nested_structure(self):
        data = {
            "args": [
                {"description": "putin invaded ukraine", "id": "a1"},
                {"description": "clean text", "id": "a2"},
            ]
        }
        result = _global_entity_scrub(data)
        assert result["args"][0]["description"] == "<scrubbed>"
        assert result["args"][1]["description"] == "clean text"


# ---------------------------------------------------------------------------
# Vector 3 — FOL formulae + dict keys in nl_to_logic_translations
# ---------------------------------------------------------------------------

class TestVector3FOLFormulae:
    """Verify 11th pass: nl_to_logic_translations scrubbing."""

    def _make_nl_translations(self):
        return {
            "nl_to_logic_translations": [
                {
                    "formula": "HasTitle(doc1, title_donald_trump_united_nations)",
                    "original_text": "The speech by Donald Trump at the United Nations",
                    "variables": {
                        "title_donald_trump_united_nations": "doc1_ref",
                        "safe_var": "value1",
                    },
                    "source_id": "src_0",
                    "logic_type": "FOL",
                },
                {
                    "formula": "Mentions(putin, maidan)",
                    "original_text": "Putin referenced the Maidan revolution",
                    "variables": {"maidan_event": "ref2"},
                    "logic_type": "FOL",
                },
            ]
        }

    def test_formula_scrubbed(self):
        result = _scrub_state_for_export(self._make_nl_translations())
        for entry in result["nl_to_logic_translations"]:
            assert entry["formula"] == "<scrubbed>"

    def test_original_text_scrubbed(self):
        result = _scrub_state_for_export(self._make_nl_translations())
        for entry in result["nl_to_logic_translations"]:
            assert entry["original_text"] == "<scrubbed>"

    def test_entity_dict_keys_renamed(self):
        result = _scrub_state_for_export(self._make_nl_translations())
        vars_0 = result["nl_to_logic_translations"][0]["variables"]
        # Entity-bearing key should be renamed to var_N
        assert "title_donald_trump_united_nations" not in vars_0
        assert any(k.startswith("var_") for k in vars_0)
        # Safe keys preserved
        assert vars_0.get("safe_var") == "value1"

    def test_second_entry_entity_keys_renamed(self):
        result = _scrub_state_for_export(self._make_nl_translations())
        vars_1 = result["nl_to_logic_translations"][1]["variables"]
        assert "maidan_event" not in vars_1
        assert any(k.startswith("var_") for k in vars_1)

    def test_non_nl_fields_preserved(self):
        result = _scrub_state_for_export(self._make_nl_translations())
        # logic_type is not an NL field and not an entity → preserved
        for entry in result["nl_to_logic_translations"]:
            assert entry["logic_type"] == "FOL"


# ---------------------------------------------------------------------------
# Vector 4 — Integration end-to-end
# ---------------------------------------------------------------------------

class TestVector4Integration:
    """Full pipeline: _scrub_state_for_export + _global_entity_scrub on a
    realistic state fixture with leaks in every vector."""

    @pytest.fixture()
    def full_dirty_state(self):
        return {
            # Vector 1: raw text fields (must be stripped entirely)
            "raw_text": "Full plaintext of the speech here",
            "full_text": "Another copy of full text",
            # Vector 1: NL paraphrase fields
            "identified_arguments": {
                "arg_1": {
                    "premisses": "Trump claimed that NATO is obsolete",
                    "conclusion": "Therefore alliances must be restructured",
                    "confidence": 0.9,
                },
                "arg_2": {
                    "premisses": "Putin said the sanctions are illegal",
                    "conclusion": "Economic measures should be lifted",
                    "confidence": 0.7,
                },
            },
            "identified_fallacies": {
                "fal_1": {
                    "justification": "This is a straw man because Biden never said that",
                    "fallacy_type": "straw_man",
                },
            },
            "counter_arguments": [
                {"text": "Ukraine has shown resilience against Russia", "strategy": "counter_example"},
            ],
            "debate_transcripts": [
                {"speaker": "A", "content": "z" * 200},
            ],
            # Vector 3: FOL translations
            "nl_to_logic_translations": [
                {
                    "formula": "Invades(putin, ukraine)",
                    "original_text": "Putin invaded Ukraine",
                    "variables": {"ukraine_invasion": "ref_1"},
                },
            ],
            # Extra fields that should survive
            "analysis_metadata": {"version": "1.0"},
            "pipeline_duration": 2345.6,
        }

    def test_no_raw_text_fields_remain(self, full_dirty_state):
        result = _scrub_state_for_export(full_dirty_state)
        for field in _PRIVACY_STRIP_FIELDS:
            assert field not in result, f"Privacy strip field '{field}' should be removed"

    def test_all_nl_fields_scrubbed(self, full_dirty_state):
        result = _scrub_state_for_export(full_dirty_state)
        for arg in result["identified_arguments"].values():
            assert arg["premisses"] == "<scrubbed>"
            assert arg["conclusion"] == "<scrubbed>"

    def test_fallacies_justification_scrubbed(self, full_dirty_state):
        result = _scrub_state_for_export(full_dirty_state)
        for fal in result["identified_fallacies"].values():
            assert fal["justification"] == "<scrubbed>"

    def test_counter_args_scrubbed(self, full_dirty_state):
        result = _scrub_state_for_export(full_dirty_state)
        for ca in result["counter_arguments"]:
            assert ca["text"] == "<scrubbed>"

    def test_nl_translations_formula_and_text_scrubbed(self, full_dirty_state):
        result = _scrub_state_for_export(full_dirty_state)
        for entry in result["nl_to_logic_translations"]:
            assert entry["formula"] == "<scrubbed>"
            assert entry["original_text"] == "<scrubbed>"

    def test_nl_translations_entity_keys_renamed(self, full_dirty_state):
        result = _scrub_state_for_export(full_dirty_state)
        vars_ = result["nl_to_logic_translations"][0]["variables"]
        assert "ukraine_invasion" not in vars_

    def test_entity_grep_zero_hits(self, full_dirty_state):
        """The gold standard: grep for any entity name → 0 hits."""
        result = _scrub_state_for_export(full_dirty_state)
        serialized = json.dumps(result).lower()
        entity_fragments = [
            "trump", "biden", "obama", "putin", "poutine", "zelensky",
            "macron", "netanyahu", "iran", "ukraine", "russia",
            "china", "israel", "nato", "otan", "maidan", "crimea",
            "kremlin", "pentagon", "white_house",
        ]
        for fragment in entity_fragments:
            assert fragment not in serialized, f"Entity '{fragment}' found in scrubbed output"

    def test_non_sensitive_fields_preserved(self, full_dirty_state):
        result = _scrub_state_for_export(full_dirty_state)
        assert result["analysis_metadata"]["version"] == "1.0"
        assert result["pipeline_duration"] == 2345.6
        assert result["identified_arguments"]["arg_1"]["confidence"] == 0.9
        assert result["identified_fallacies"]["fal_1"]["fallacy_type"] == "straw_man"
        assert result["counter_arguments"][0]["strategy"] == "counter_example"

    def test_idempotent(self, full_dirty_state):
        """Running scrub twice produces the same result."""
        result1 = _scrub_state_for_export(full_dirty_state)
        result2 = _scrub_state_for_export(copy.deepcopy(full_dirty_state))
        assert json.dumps(result1, sort_keys=True) == json.dumps(result2, sort_keys=True)

    def test_empty_state_no_crash(self):
        result = _scrub_state_for_export({})
        # Scrub creates default empty structures for known dimensions
        assert isinstance(result, dict)

    def test_state_with_only_clean_data(self):
        state = {
            "identified_arguments": {"arg_1": {"confidence": 0.5}},
            "pipeline_duration": 100.0,
        }
        result = _scrub_state_for_export(state)
        assert result["identified_arguments"]["arg_1"]["confidence"] == 0.5
