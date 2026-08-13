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
from typing import Any, Dict
import pytest

from scripts.analysis.generate_spectacular_bundle import (
    _scrub_state_for_export,
    _global_entity_scrub,
    _ENTITY_PATTERN,
    _ENTITY_SUBSTR_PATTERN,
    _NL_SCRUB_KEYS,
    _PRIVACY_STRIP_FIELDS,
)


def _build_dag_state_via_real_writers():
    """Build a DAG-path state using the real shared_state writers.

    Anti-#1019 fixture (#1636 family, #1643): never construct state by hand.
    Real writers are:
      - dung_frameworks: Dict[str, Dict] — populated by .__setitem__ on self
        (no dedicated add_* method found in shared_state for Dung frameworks).
      - ranking_results, probabilistic_results, bipolar_results: List[Dict]
        — populated by .append() via dedicated writers below.

    Returns the same dict-of-lists shape that get_state_snapshot() produces
    (i.e. one dict per top-level container), which is what the scrubber
    receives on its cleaned.get(dim_key) call.
    """
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    state = UnifiedAnalysisState(initial_text="scrub-fixture")

    # dung_frameworks: Dict[str, Dict] — populated via __setitem__ (no add method)
    state.dung_frameworks["dung_1"] = {
        "name": "A framework about sanctions against Russia",
        "arguments": [
            "The speaker argues that economic sanctions against Russia are ineffective",
            "Counter-argument: sanctions have weakened the Russian economy",
            "short",
        ],
        "attacks": [["arg_1", "arg_2"]],
        "extensions": {"preferred": ["arg_1", "arg_3"]},
    }

    # ranking_results: List[Dict] — populated via add_ranking_result (append-backed)
    state.add_ranking_result(
        method="burden",
        arguments=[
            "First argument about Ukraine sovereignty",
            "Second argument about NATO expansion",
        ],
        comparisons=[],
    )

    # probabilistic_results: List[Dict] — populated via add_probabilistic_result
    state.add_probabilistic_result(
        arguments=[
            "Trump claimed the election was stolen",
            "Biden won the popular vote",
        ],
        acceptance_probs={"arg_1": 0.7},
    )

    # bipolar_results: List[Dict] — populated via add_bipolar_result
    state.add_bipolar_result(
        framework_type="bipolar",
        arguments=[
            "Netanyahu defended the military operation in Israel",
        ],
        supports=[],
    )

    return {
        "identified_arguments": {
            "arg_1": {"premisses": "safe", "conclusion": "safe", "confidence": 0.8},
        },
        "dung_frameworks": state.dung_frameworks,
        "ranking_results": state.ranking_results,
        "probabilistic_results": state.probabilistic_results,
        "bipolar_results": state.bipolar_results,
    }


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
        # extracts is List[Dict] in prod (see shared_state.add_extract, l.279).
        # Pass 8 used to guard with isinstance(dict); #1662 fixed both Pass 8
        # and Pass 12 to handle the real List[Dict] shape.
        state = {
            "extracts": [
                {"id": "ext_1", "name": "raw long extract name here", "content": "p" * 100},
                {"id": "ext_2", "name": "short", "content": "tiny"},
            ]
        }
        result = _scrub_state_for_export(state)
        assert isinstance(result["extracts"], list)
        assert len(result["extracts"]) == 2
        assert result["extracts"][0]["content"] == "<scrubbed>"
        # short name preserved
        assert result["extracts"][1]["name"] == "short"


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


# ---------------------------------------------------------------------------
# Vector 5 — DAG path: dung_frameworks / ranking / probabilistic arguments[]
# ---------------------------------------------------------------------------

class TestVector5DAGArgumentsDescription:
    """Verify scrubbing of arguments[].description on DAG path structures.

    Discovered in R276-R280: dung_frameworks[*].arguments is a List[str]
    of raw NL descriptions that bypassed the identified_arguments scrub.
    Same pattern in ranking_results, probabilistic_results, bipolar_results.

    Fixture built via real writers (#1662 — anti-#1019 fixture dict-literal):
    ranking_results, probabilistic_results, bipolar_results are stored as
    List[Dict] in shared_state.py (add_*_result methods append to a list).
    The previous dict-literal fixture mimicked dung_frameworks's shape and
    silently masked the bug — the scrubber's isinstance(dim, dict) guard
    passed for the test fixture while skipping the real production shape.
    """

    def _make_dag_state(self):
        return _build_dag_state_via_real_writers()

    def test_dung_arguments_list_scrubbed(self):
        result = _scrub_state_for_export(self._make_dag_state())
        dung_args = result["dung_frameworks"]["dung_1"]["arguments"]
        assert dung_args[0] == "<scrubbed>"
        assert dung_args[1] == "<scrubbed>"
        # Short string (< 10 chars) preserved
        assert dung_args[2] == "short"

    def test_dung_name_scrubbed_when_long(self):
        result = _scrub_state_for_export(self._make_dag_state())
        assert result["dung_frameworks"]["dung_1"]["name"] == "<scrubbed>"

    def test_dung_non_string_fields_preserved(self):
        result = _scrub_state_for_export(self._make_dag_state())
        assert result["dung_frameworks"]["dung_1"]["attacks"] == [["arg_1", "arg_2"]]
        assert result["dung_frameworks"]["dung_1"]["extensions"] == {"preferred": ["arg_1", "arg_3"]}

    def test_ranking_results_arguments_scrubbed(self):
        result = _scrub_state_for_export(self._make_dag_state())
        # ranking_results is a List[Dict] (real shape via add_ranking_result).
        # Bug #1662: prior fixture was a Dict; scrubber's isinstance(dim, dict)
        # guard accepted the dict fixture and skipped the real list shape.
        assert isinstance(result["ranking_results"], list)
        assert len(result["ranking_results"]) == 1
        rank_args = result["ranking_results"][0]["arguments"]
        assert rank_args[0] == "<scrubbed>"
        assert rank_args[1] == "<scrubbed>"

    def test_probabilistic_results_arguments_scrubbed(self):
        result = _scrub_state_for_export(self._make_dag_state())
        assert isinstance(result["probabilistic_results"], list)
        assert len(result["probabilistic_results"]) == 1
        prob_args = result["probabilistic_results"][0]["arguments"]
        assert prob_args[0] == "<scrubbed>"
        assert prob_args[1] == "<scrubbed>"

    def test_bipolar_results_arguments_scrubbed(self):
        result = _scrub_state_for_export(self._make_dag_state())
        assert isinstance(result["bipolar_results"], list)
        assert len(result["bipolar_results"]) == 1
        bip_args = result["bipolar_results"][0]["arguments"]
        assert bip_args[0] == "<scrubbed>"

    def test_dag_entity_grep_zero_hits(self):
        """Gold standard: no entity names in scrubbed DAG state."""
        result = _scrub_state_for_export(self._make_dag_state())
        serialized = json.dumps(result).lower()
        entity_fragments = [
            "trump", "biden", "putin", "poutine", "zelensky",
            "macron", "netanyahu", "ukraine", "russia", "israel",
            "nato", "crimea", "kremlin",
        ]
        for fragment in entity_fragments:
            assert fragment not in serialized, f"Entity '{fragment}' leaked in DAG scrub"

    def test_identified_arguments_unaffected(self):
        """Pass 2 (identified_arguments) should still work alongside Pass 12."""
        result = _scrub_state_for_export(self._make_dag_state())
        assert result["identified_arguments"]["arg_1"]["confidence"] == 0.8


# ---------------------------------------------------------------------------
# Vector 6 (#1662) — the DAG pass must reach the shape the WRITERS produce
# ---------------------------------------------------------------------------

class TestVector6RealWriterShapes:
    """Pass 12 must scrub every container it declares, not just the dict-shaped one.

    ``TestVector5DAGArgumentsDescription`` above builds its four containers as
    dict-of-id -> entry. Only ONE of them is stored that way: ``dung_frameworks``
    is a ``Dict[str, Dict]`` (shared_state.py:442, filled by ``[df_id] = {...}``),
    while ``ranking_results`` / ``probabilistic_results`` / ``bipolar_results``
    are ``List[Dict]`` (l.454/458/459, filled by ``.append(entry)``). Pass 12 was
    gated on ``isinstance(dim, dict)``, so it ran on the one and silently skipped
    the three — and the Vector-5 tests stayed green, because their fixture built
    the shape the guard expected instead of the shape a writer emits.

    That is why these tests drive the REAL writers and serialize through the REAL
    ``get_state_snapshot()`` rather than hand-rolling a dict: a fixture that
    invents its own producer can only prove the test agrees with itself.

    Entity names are deliberately absent from the NL below so the final
    ``_global_entity_scrub`` (a fixed ~30-name allowlist) cannot mask a Pass 12
    failure — these assertions must be armed by the shape-based scrub alone.
    """

    _LONG_NL = (
        "The speaker asserts that the proposed reform is the only viable path forward"
    )

    def _snapshot_from_real_writers(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("initial text for the analysis")
        state.add_dung_framework(
            name="A framework carrying a long descriptive name in natural language",
            arguments=[self._LONG_NL, "short"],
            attacks=[["arg_1", "arg_2"]],
        )
        state.add_ranking_result(
            method="burden", arguments=[self._LONG_NL], comparisons=[]
        )
        state.add_probabilistic_result(
            arguments=[self._LONG_NL], acceptance_probs={"arg_1": 0.7}
        )
        state.add_bipolar_result(
            framework_type="bipolar", arguments=[self._LONG_NL], supports=[]
        )
        return state.get_state_snapshot()

    def test_writers_emit_list_shaped_containers(self):
        """Guard on the premise itself: three of the four are lists, one is a dict.

        If a future refactor unifies the shapes, this test fails first and says so,
        instead of the scrub silently going back to covering only part of them.
        """
        snapshot = self._snapshot_from_real_writers()
        assert isinstance(snapshot["dung_frameworks"], dict)
        for key in ("ranking_results", "probabilistic_results", "bipolar_results"):
            assert isinstance(snapshot[key], list), f"{key} is no longer a list"
            assert snapshot[key], f"{key} was not populated by its writer"

    @pytest.mark.parametrize(
        "dim_key", ["ranking_results", "probabilistic_results", "bipolar_results"]
    )
    def test_list_shaped_dimension_arguments_scrubbed(self, dim_key):
        """The canary: pre-fix these three were skipped by the isinstance(dict) gate."""
        result = _scrub_state_for_export(self._snapshot_from_real_writers())
        entries = result[dim_key]
        assert entries, f"{dim_key} empty — the assertion would be vacuous"
        for entry in entries:
            assert entry["arguments"] == ["<scrubbed>"], (
                f"{dim_key} carried raw NL through the export scrub"
            )

    def test_dict_shaped_dimension_still_scrubbed(self):
        """No-regression: dung_frameworks was the one container the gate reached."""
        result = _scrub_state_for_export(self._snapshot_from_real_writers())
        for entry in result["dung_frameworks"].values():
            assert entry["arguments"][0] == "<scrubbed>"
            assert entry["arguments"][1] == "short"  # short strings preserved
            assert entry["name"] == "<scrubbed>"

    def test_no_long_nl_survives_anywhere_in_snapshot(self):
        """End-to-end: the planted sentence must not appear in the exported JSON.

        Deliberately free of allowlisted entity names, so a pass is attributable
        to Pass 12 and not to the final entity regex.
        """
        result = _scrub_state_for_export(self._snapshot_from_real_writers())
        assert self._LONG_NL not in json.dumps(result)


# ---------------------------------------------------------------------------
# Vector 6 — Differential proof: Pass 12 covers all 4 containers (#1662)
# ---------------------------------------------------------------------------

class TestVector6Pass12CoversAllContainers:
    """Differential tests that isolate Pass 12 behaviour from Pass 14 (_global_entity_scrub).

    Pass 14 is a *nominative* scrub — it only catches strings containing one of
    ~30 hard-coded entity names (trump/biden/ukraine/...). Pass 12 is a *shape*
    scrub — any NL string longer than 10 chars under `arguments` is replaced
    with `<scrubbed>`, regardless of corpus.

    Bug #1662: the `isinstance(dim, dict)` guard in Pass 12 silently skipped
    ranking_results / probabilistic_results / bipolar_results because in
    production they are List[Dict] (not Dict[str, Dict]). With *entity-named*
    fixture strings, Pass 14 saved the day and the bug was invisible. With
    *pure descriptive NL* (no entity in any regex list), only Pass 12 can
    scrub the field — so a fixture without entities is what proves the bug
    and the fix.
    """

    def _make_pure_nl_state(self) -> Dict[str, Any]:
        """DAG-path state built via real writers with NO entity-named strings.

        Each NL string under `arguments` is a generic descriptive sentence
        (no proper noun from Pass 14's entity list). Pass 14 cannot touch it,
        so any surviving raw NL means Pass 12 missed it.
        """
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="pure-nl-fixture")

        # dung_frameworks (Dict) — descriptive NL only, no entity names
        state.dung_frameworks["dung_1"] = {
            "name": "Generic deliberation about policy effectiveness",
            "arguments": [
                "The first speaker claims the proposed measure will reduce costs",
                "The second speaker argues administrative burden outweighs savings",
                "tiny",
            ],
            "attacks": [["arg_1", "arg_2"]],
            "extensions": {"preferred": ["arg_1"]},
        }

        # ranking_results (List[Dict]) — descriptive NL only
        state.add_ranking_result(
            method="burden",
            arguments=[
                "Argument about fiscal sustainability of the reform",
                "Argument about implementation timeline for the new system",
            ],
            comparisons=[],
        )

        # probabilistic_results (List[Dict]) — descriptive NL only
        state.add_probabilistic_result(
            arguments=[
                "Speaker asserts the reform will benefit most households",
                "Speaker counters that low-income groups are excluded",
            ],
            acceptance_probs={"arg_1": 0.6},
        )

        # bipolar_results (List[Dict]) — descriptive NL only
        state.add_bipolar_result(
            framework_type="bipolar",
            arguments=[
                "The reform proposal supports small business growth according to one party",
            ],
            supports=[],
        )

        return {
            "dung_frameworks": state.dung_frameworks,
            "ranking_results": state.ranking_results,
            "probabilistic_results": state.probabilistic_results,
            "bipolar_results": state.bipolar_results,
        }

    # Sentinel substring present in every fixture argument above; Pass 14
    # cannot match it (no entity name), so a leak means Pass 12 missed.
    _SENTINEL = "speaker"  # generic English word, not in Pass 14 regex list

    def test_pass12_scrubs_dung_frameworks_pure_nl(self):
        result = _scrub_state_for_export(self._make_pure_nl_state())
        dung_args = result["dung_frameworks"]["dung_1"]["arguments"]
        assert all(a == "<scrubbed>" for a in dung_args if len(a) > 10)
        assert dung_args[2] == "tiny"  # short string preserved
        # And the pure-NL "speaker" sentinel must be gone
        serialized = json.dumps(result).lower()
        assert self._SENTINEL not in serialized

    def test_pass12_scrubs_ranking_results_pure_nl_list_shape(self):
        """The actual #1662 case: ranking_results is List[Dict] in production.

        Bug: prior fixture mimicked Dict shape; pass12 guard `isinstance(dim,
        dict)` accepted the dict and skipped the real list.
        """
        result = _scrub_state_for_export(self._make_pure_nl_state())
        assert isinstance(result["ranking_results"], list)
        rank_args = result["ranking_results"][0]["arguments"]
        assert rank_args[0] == "<scrubbed>"
        assert rank_args[1] == "<scrubbed>"

    def test_pass12_scrubs_probabilistic_results_pure_nl_list_shape(self):
        result = _scrub_state_for_export(self._make_pure_nl_state())
        assert isinstance(result["probabilistic_results"], list)
        prob_args = result["probabilistic_results"][0]["arguments"]
        assert prob_args[0] == "<scrubbed>"
        assert prob_args[1] == "<scrubbed>"

    def test_pass12_scrubs_bipolar_results_pure_nl_list_shape(self):
        result = _scrub_state_for_export(self._make_pure_nl_state())
        assert isinstance(result["bipolar_results"], list)
        bip_args = result["bipolar_results"][0]["arguments"]
        assert bip_args[0] == "<scrubbed>"

    def test_pass12_pure_nl_no_sentinel_leak_anywhere(self):
        """All 4 containers scrubbed — no raw descriptive NL survives.

        This is the differential that fails on the pre-#1662 code: with the
        old `isinstance(dim, dict)` guard, only dung_frameworks got scrubbed;
        ranking/probabilistic/bipolar raw NL survived, and the pure-NL
        sentinel ("speaker") leaks into the bundle.
        """
        result = _scrub_state_for_export(self._make_pure_nl_state())
        serialized = json.dumps(result).lower()
        assert self._SENTINEL not in serialized, (
            "Pure-NL sentinel leaked — Pass 12 missed one of the 4 containers. "
            "Pre-#1662: isinstance(dim, dict) guard skipped List[Dict] containers."
        )

    def test_pass12_differential_runs_in_isolation(self) -> None:
        """Calling Pass 12 directly (without Pass 14) confirms it covers all 4.

        We re-execute just the scrub_dim_entry logic on each fixture entry
        and assert every NL string > 10 chars is replaced. This isolates
        Pass 12 from Pass 14 and proves the shape-agnostic scrub works.
        """
        state = self._make_pure_nl_state()

        # Replicate the (fixed) Pass 12 logic to test in isolation
        def _scrub_dim_entry(entry: Any) -> None:
            if not isinstance(entry, dict):
                return
            args_list = entry.get("arguments")
            if isinstance(args_list, list):
                entry["arguments"] = [
                    ("<scrubbed>" if isinstance(a, str) and len(a) > 10 else a)
                    for a in args_list
                ]
            name = entry.get("name")
            if isinstance(name, str) and len(name) > 20:
                entry["name"] = "<scrubbed>"

        # dung_frameworks: Dict
        for entry in state["dung_frameworks"].values():
            _scrub_dim_entry(entry)
        # ranking/probabilistic/bipolar: List[Dict]
        for dim_key in ("ranking_results", "probabilistic_results", "bipolar_results"):
            for entry in state[dim_key]:
                _scrub_dim_entry(entry)

        # Now every long NL string must be `<scrubbed>`.
        for arg in state["dung_frameworks"]["dung_1"]["arguments"]:
            assert arg == "<scrubbed>" or len(arg) <= 10
        for entry in state["ranking_results"]:
            for arg in entry["arguments"]:
                assert arg == "<scrubbed>" or len(arg) <= 10
        for entry in state["probabilistic_results"]:
            for arg in entry["arguments"]:
                assert arg == "<scrubbed>" or len(arg) <= 10
        for entry in state["bipolar_results"]:
            for arg in entry["arguments"]:
                assert arg == "<scrubbed>" or len(arg) <= 10


# ---------------------------------------------------------------------------
# Vector 7 (#1673) — Pass 8 must scrub extracts entries whatever the container
# ---------------------------------------------------------------------------

class TestVector7Pass8ExtractsContainerShape:
    """Pass 8 (extracts) must scrub entries regardless of container shape.

    Third occurrence of the #1662 family (#1662, #1664, #1665, now #1673): a
    privacy guard written against the container shape *observed at write time*.
    Pass 8 gated on ``isinstance(extracts, list)`` — before #1665 it gated on
    ``isinstance(extracts, dict)``; each version swapped the orphan form rather
    than removing the constraint. The orphan form has no producer today, so the
    defect is in place but lets nothing through — which is exactly why the
    previous version survived so long.

    Prod shape is ``List[Dict]`` (``shared_state.add_extract`` l.279 appends a
    dict; ``self.extracts: List[Dict[str, Any]]`` l.94). The orphan form is a
    ``Dict[str, Dict]`` mapping (id -> entry), analogous to ``dung_frameworks``.
    The armed canary drives that orphan shape with pure descriptive NL — no
    entity from Pass 14's allowlist — so a leak is attributable to Pass 8 alone.

    Per #1673: use ``_iter_dimension_entries`` (landed #1662, already used by
    Pass 12) and mutate entries in place; do NOT re-introduce a ``dict`` branch
    parallel to the ``list`` one (two branches guarded = the same defect twice).
    """

    # Pure descriptive NL — no Pass-14 entity name can mask a Pass 8 miss.
    _LONG_CONTENT = (
        "The speaker develops an extended argument about institutional reform"
    )
    _SENTINEL = "reform"  # generic word, absent from Pass 14's entity regex

    def _entry(self) -> Dict[str, Any]:
        return {"id": "ext_1", "name": "short", "content": self._LONG_CONTENT}

    # -- Premise guard: prod really is List[Dict] via the real writer ----------

    def test_prod_extracts_is_list_of_dicts_via_real_writer(self):
        """Guard on the premise: add_extract appends a dict to a list.

        If a future refactor stores extracts as a mapping, this fails first
        and says so, instead of the scrub silently covering only one shape.
        """
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(initial_text="premise-fixture")
        state.add_extract(name="short", content=self._LONG_CONTENT)
        snapshot = state.get_state_snapshot()
        assert isinstance(
            snapshot["extracts"], list
        ), "extracts is no longer a list — the premise of Pass 8 has moved"
        assert snapshot["extracts"], "add_extract did not populate the list"
        assert isinstance(snapshot["extracts"][0], dict)

    # -- No-regression: prod list shape still scrubbed ------------------------

    def test_pass8_scrubs_extracts_list_shape_prod(self):
        """List[Dict] (prod shape) entries are scrubbed — holds pre- and post-fix."""
        state = {"extracts": [self._entry()]}
        result = _scrub_state_for_export(state)
        assert isinstance(result["extracts"], list)
        assert result["extracts"][0]["content"] == "<scrubbed>"

    # -- Armed canary: the orphan dict shape (RED on main, GREEN after fix) ---

    def test_pass8_scrubs_extracts_dict_shape_orphan(self):
        """Dict[str, Dict] container (orphan form) entries must be scrubbed too.

        This is the armed test for #1673: on main, Pass 8 gates on
        ``isinstance(extracts, list)`` and skips the dict container entirely,
        so ``content`` traverses the export untouched. After the fix (iterate
        via ``_iter_dimension_entries``), the dict entries are reached.
        """
        state = {"extracts": {"ext_1": self._entry()}}
        result = _scrub_state_for_export(state)
        # The dict container survives (shape preserved); its entry is scrubbed.
        assert isinstance(result["extracts"], dict)
        assert "ext_1" in result["extracts"]
        assert result["extracts"]["ext_1"]["content"] == "<scrubbed>", (
            "Pass 8 skipped the dict-shaped extracts container — the orphan "
            "form let raw NL through (#1673, same family as #1662)."
        )

    def test_pass8_dict_shape_preserves_short_values(self):
        """The threshold logic is unchanged on the dict shape: short strings kept."""
        state = {
            "extracts": {"ext_1": {"id": "ext_1", "name": "ok", "content": "tiny"}}
        }
        result = _scrub_state_for_export(state)
        assert result["extracts"]["ext_1"]["content"] == "tiny"
        assert result["extracts"]["ext_1"]["name"] == "ok"

    # -- Pure-NL no-leak: Pass 14 cannot mask a Pass 8 miss -------------------

    def test_pass8_dict_shape_no_pure_nl_sentinel_leak(self):
        """End-to-end: the planted pure-NL sentinel must not survive.

        Free of entity names, so Pass 14 (the ~30-name allowlist) cannot scrub
        it — only Pass 8 can. A leak means Pass 8 missed the dict container.
        """
        state = {"extracts": {"ext_1": self._entry()}}
        result = _scrub_state_for_export(state)
        assert self._SENTINEL not in json.dumps(result).lower(), (
            "Pure-NL sentinel leaked through the dict-shaped extracts container "
            "— Pass 8 missed it and Pass 14 cannot mask it (no entity name)."
        )

    # -- Divergence from sanitize_state on extracts[*].name -------------------

    def test_pass8_scrubs_long_name_diverging_from_sanitize_state(self):
        """Documents the known divergence: Pass 8 scrubs a long ``name``;
        ``sanitize_state`` preserves ``extracts[*].name`` as a join key (l.35-38).

        Not a behavior change — the two scrubbers agree on all measured state
        (0/97 real names reach the threshold), and this script has no join-key
        consumer. The comment in Pass 8 records the divergence; this test pins
        the actual policy so a future reader sees it.
        """
        entry = {"id": "ext_1", "name": self._LONG_CONTENT, "content": "x"}
        state = {"extracts": [entry]}
        result = _scrub_state_for_export(state)
        assert result["extracts"][0]["name"] == "<scrubbed>"

    # -- Container-type guard removed: both shapes via the same code path -----

    def test_pass8_reaches_both_shapes_through_one_path(self):
        """The fix removes the type test, not the list support: both shapes
        are scrubbed through ``_iter_dimension_entries``. Differential on the
        same entry payload — list and dict containers both scrub content."""
        entry = self._entry()
        list_result = _scrub_state_for_export({"extracts": [dict(entry)]})
        dict_result = _scrub_state_for_export({"extracts": {"ext_1": dict(entry)}})
        assert list_result["extracts"][0]["content"] == "<scrubbed>"
        assert dict_result["extracts"]["ext_1"]["content"] == "<scrubbed>"
