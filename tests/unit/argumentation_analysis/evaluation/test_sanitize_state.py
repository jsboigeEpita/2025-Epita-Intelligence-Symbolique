"""Tests for argumentation_analysis.evaluation.sanitize_state."""

import json
from pathlib import Path

import pytest

from argumentation_analysis.evaluation.sanitize_state import sanitize_state

GOLDEN_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "golden"
    / "fixtures"
    / "spectacular"
    / "doc_a_golden.json"
)


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch):
    """#1973: ``opaque_id`` has no default salt any more and raises without one.

    Every source this module feeds the scrubber is fabricated (see the module
    docstring), so a salt protects nothing here — it is pinned at the perimeter
    of the synthetic fixtures rather than provisioned as a CI secret. Two
    reasons, in that order: a repository secret makes the dependency invisible
    (green in CI, red on a fresh clone), and a root-scope ``autouse`` would
    disarm the #1973 fail-loud guard for the whole test environment, letting a
    future production path that forgets the salt pass green. Scoped to this
    module, the guard keeps its teeth everywhere else and
    ``test_opaque_id.py`` keeps asserting the raise.
    """
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-1973")


@pytest.fixture
def golden_state():
    with open(GOLDEN_FIXTURE, encoding="utf-8") as f:
        data = json.load(f)
    return data["state_snapshot"]


class TestSanitizeTopLevel:
    def test_raw_text_stripped(self, golden_state):
        result = sanitize_state(golden_state)
        assert "raw_text" not in result

    def test_full_text_stripped(self):
        state = {"full_text": "sensitive", "count": 5}
        result = sanitize_state(state)
        assert "full_text" not in result
        assert result["count"] == 5

    def test_source_name_stripped(self):
        state = {"source_name": "Secret Speaker", "score": 0.9}
        result = sanitize_state(state)
        assert "source_name" not in result

    def test_all_sensitive_fields_stripped(self):
        state = {
            "raw_text": "x",
            "full_text": "x",
            "full_text_segment": "x",
            "raw_text_snippet": "x",
            "source_name": "x",
            "document_name": "x",
            "author": "x",
            "date_iso": "x",
            "url": "x",
        }
        result = sanitize_state(state)
        for field in state:
            assert field not in result


class TestSanitizeOpaqueReplace:
    def test_source_id_opaque(self):
        state = {"source_id": "Real Name"}
        result = sanitize_state(state)
        assert result["source_id"] != "Real Name"
        assert len(result["source_id"]) == 8

    def test_source_id_stable(self):
        state = {"source_id": "Same Name"}
        a = sanitize_state(state)
        b = sanitize_state(state)
        assert a["source_id"] == b["source_id"]


class TestSanitizePreserved:
    def test_counts_preserved(self, golden_state):
        result = sanitize_state(golden_state)
        assert "summary" not in result  # top-level summary is outside state_snapshot
        # Check that analysis_tasks (counts) are preserved
        if "analysis_tasks" in golden_state:
            assert "analysis_tasks" in result

    def test_scores_preserved(self, golden_state):
        result = sanitize_state(golden_state)
        if "argument_quality_scores" in golden_state:
            assert "argument_quality_scores" in result
            for arg_id, scores in golden_state["argument_quality_scores"].items():
                result_scores = result["argument_quality_scores"][arg_id]
                # llm_assessment (narrative citing the real argument) is stripped;
                # the quantitative aggregates (overall, per-virtue scores) survive.
                assert "llm_assessment" not in result_scores
                for k, v in scores.items():
                    if k == "llm_assessment":
                        continue
                    assert result_scores[k] == v

    def test_structures_preserved(self, golden_state):
        result = sanitize_state(golden_state)
        # Dung framework list structure + arity survive (so argument/attack
        # counts and topology are preserved); the claim *texts* are opacified.
        if "dung_frameworks" in golden_state:
            assert "dung_frameworks" in result
            for df_id, fw in golden_state["dung_frameworks"].items():
                result_fw = result["dung_frameworks"][df_id]
                if "arguments" in fw:
                    assert len(result_fw["arguments"]) == len(fw["arguments"])
                if "attacks" in fw:
                    assert len(result_fw["attacks"]) == len(fw["attacks"])
                    for orig_pair, res_pair in zip(fw["attacks"], result_fw["attacks"]):
                        assert len(res_pair) == len(orig_pair)

    def test_belief_data_preserved(self, golden_state):
        result = sanitize_state(golden_state)
        if "jtms_beliefs" in golden_state:
            assert "jtms_beliefs" in result


class TestSanitizeNarrative:
    def test_narrative_replaced_with_length(self, golden_state):
        result = sanitize_state(golden_state)
        if "narrative_synthesis" in golden_state:
            narr = result["narrative_synthesis"]
            assert isinstance(narr, dict)
            assert "length" in narr
            assert narr["length"] == len(golden_state["narrative_synthesis"])
            assert narr["stripped"] is True


class TestSanitizeCounterArguments:
    def test_counter_content_stripped(self, golden_state):
        result = sanitize_state(golden_state)
        if "counter_arguments" in result:
            for ca in result["counter_arguments"]:
                assert "counter_content" not in ca
                assert "generated_text" not in ca
                # strategy and strength should survive
                assert "strategy" in ca


class TestSanitizeIdempotence:
    def test_idempotent(self):
        state = {
            "raw_text": "secret",
            "source_id": "Name",
            "narrative_synthesis": "A long narrative paragraph.",
            "counter_arguments": [
                {"strategy": "reductio", "counter_content": "text", "strength": 0.8}
            ],
            "score": 0.9,
        }
        first = sanitize_state(state)
        second = sanitize_state(first)
        # Stripped fields stay stripped; scores survive
        assert first["score"] == second["score"] == 0.9
        assert "raw_text" not in second

    def test_idempotent_on_golden(self, golden_state):
        first = sanitize_state(golden_state)
        second = sanitize_state(first)
        # llm_assessment strip is idempotent (a dropped key stays dropped), so
        # argument_quality_scores is stable across passes.
        assert first["argument_quality_scores"] == second["argument_quality_scores"]
        # Dung opacification is idempotent at the structural level (argument/
        # attack arity + topology stable across passes); the opaque values may
        # themselves be re-hashed on a second pass — that is expected for a
        # hash-based opacifier and does not re-introduce nominative content.
        for df_id in first["dung_frameworks"]:
            f_fw = first["dung_frameworks"][df_id]
            s_fw = second["dung_frameworks"][df_id]
            if "arguments" in f_fw:
                assert len(s_fw["arguments"]) == len(f_fw["arguments"])
            if "attacks" in f_fw:
                assert len(s_fw["attacks"]) == len(f_fw["attacks"])


class TestSanitizeIdentifiedArguments:
    def test_arguments_text_stripped(self):
        state = {
            "identified_arguments": {
                "arg1": "Sensitive argument text",
                "arg2": "Another text",
            }
        }
        result = sanitize_state(state)
        assert "identified_arguments" in result
        for v in result["identified_arguments"].values():
            assert isinstance(v, dict)
            assert v["text_stripped"] is True

    def test_non_string_values_preserved(self):
        state = {
            "identified_arguments": {
                "arg1": {"score": 0.9, "type": "premise"},
            }
        }
        result = sanitize_state(state)
        assert result["identified_arguments"]["arg1"] == {
            "score": 0.9,
            "type": "premise",
        }


# ---------------------------------------------------------------------------
# Epic #1258 Track 3 (#1261) — export guard must be watertight on a
# de-anonymized state (real names + readable symbols live in the working
# state; this is the boundary where they are scrubbed).
# ---------------------------------------------------------------------------

# A single nominative marker planted in every NL-bearing field. If it survives
# sanitize_state, the guard leaks. This is the "thé au polonium" test.
LEAK = "NominativeLeakToken"


def _deanonymized_state() -> dict:
    """A synthetic de-anonymized state with LEAK planted in every NL field."""
    return {
        # Opaque-replace (top-level identifier)
        "source_id": LEAK,
        # Opaque-dict-values (structural keys kept, nominative values opacified)
        "source_metadata": {
            "genre": LEAK,
            "speaker_role": LEAK,
            "channel": LEAK,
            "title": LEAK,
        },
        # Narrative fields (strings -> {length, stripped})
        "narrative_synthesis": f"{LEAK} narrative synthesis text",
        "act1_framing": f"{LEAK} act one framing",
        "act2_narrative": f"{LEAK} act two narrative",
        "act3_conclusion": f"{LEAK} act three conclusion",
        "final_conclusion": f"{LEAK} final conclusion",
        # Dict-of-dicts (nominative sub-key dropped)
        "identified_fallacies": {
            "fallacy_1": {
                "type": "ad_hominem",
                "justification": LEAK,
                "family": "relevance",
            }
        },
        "belief_sets": {
            "pl_bs_1": {"logic_type": "PL", "content": f"{LEAK} belief set content"}
        },
        # Dict-of-dicts nominative list sub-keys (#1265: opacified, not dropped,
        # so Dung argument/attack counts + topology survive).
        "dung_frameworks": {
            "dung_1": {
                "name": "fw_1",  # structural label survives
                "arguments": [LEAK, f"{LEAK} second claim"],
                "attacks": [[LEAK, f"{LEAK} second claim"]],
                # #1271: extensions subtree holds the SAME claim texts (sets of
                # the same arguments). Opacified recursively (list-of-lists +
                # flat all_members); count/sizes are structural and survive.
                "extensions": {
                    "extensions": [[LEAK, f"{LEAK} second claim"], [LEAK]],
                    "count": 2,
                    "sizes": [2, 1],
                    "all_members": [LEAK, f"{LEAK} second claim"],
                },
            }
        },
        # Dict-of-dicts narrative sub-key (#1265: llm_assessment dropped, the
        # quantitative ``overall``/``scores`` aggregates survive).
        "argument_quality_scores": {
            "arg_1": {
                "overall": 5.0,  # quantitative — must survive
                "scores": {"clarity": 4, "coherence": 5},  # quantitative — survives
                "llm_assessment": f"{LEAK} narrative citing the real argument",
            }
        },
        # List-of-dicts (nominative sub-keys dropped)
        "counter_arguments": [
            {
                "id": "ca_1",
                "strategy": "reductio",  # must survive
                "counter_content": LEAK,
                "original_argument": LEAK,
                "generated_text": LEAK,
            }
        ],
        "extracts": [{"id": "extract_1", "name": "n", "content": LEAK}],
        "debate_transcripts": [
            {
                "id": "debate_1",
                "topic": LEAK,
                "proponent_move": LEAK,
                "opponent_move": LEAK,
            }
        ],
        "transcription_segments": [{"id": "ts_1", "text": LEAK, "speaker": LEAK}],
        "neural_fallacy_scores": [{"id": "nf_1", "label": "x", "text_segment": LEAK}],
        "analysis_trace": [{"phase": "p", "agent": "a", "summary": LEAK}],
        "nl_to_logic_translations": [
            {
                "id": "nll_1",
                "original_text": LEAK,
                "formula": "p & q",
                "variables": {"p": LEAK, "q": LEAK},  # symbol_mapping
            }
        ],
        "semantic_index_refs": [{"id": "si_1", "query": LEAK, "snippet": LEAK}],
        "formal_synthesis_reports": [{"id": "fsyn_1", "summary": LEAK}],
        # Struct-valued NL field (reduced to counts)
        "stakes_and_stakeholders": {
            "stakes": [LEAK, LEAK],
            "stakeholders": [LEAK],
            "rhetorical_register": LEAK,
            "discursive_arena": LEAK,
        },
        # Preserved aggregate (must survive untouched, no token anyway)
        "score": 0.9,
    }


class TestSanitizeDeAnonymizedState:
    """The guard must leave zero nominative content on a real-name state."""

    def test_no_nominative_leak_anywhere(self):
        result = sanitize_state(_deanonymized_state())
        blob = json.dumps(result, ensure_ascii=False)
        assert LEAK not in blob, f"Nominative leak detected in sanitized state: {blob}"

    def test_aggregates_survive(self):
        result = sanitize_state(_deanonymized_state())
        # Quantitative aggregates must survive the scrub.
        scores = result["argument_quality_scores"]["arg_1"]
        assert scores["overall"] == 5.0
        assert scores["scores"] == {"clarity": 4, "coherence": 5}
        # llm_assessment (narrative citing the real argument) is dropped.
        assert "llm_assessment" not in scores
        # Dung: list structure + arity survive, but claim texts are opacified.
        dung = result["dung_frameworks"]["dung_1"]
        assert dung["name"] == "fw_1"  # structural label survives
        assert isinstance(dung["arguments"], list) and len(dung["arguments"]) == 2
        # topology survives: one attack = one [source, target] pair.
        assert isinstance(dung["attacks"], list) and len(dung["attacks"]) == 1
        assert len(dung["attacks"][0]) == 2
        # #1271: extensions subtree — set arity/topology survive (count, sizes,
        # number of extensions + their sizes), claim texts opacified.
        ext = dung["extensions"]
        assert ext["count"] == 2
        assert ext["sizes"] == [2, 1]
        assert len(ext["extensions"]) == 2  # two extension sets
        assert [len(s) for s in ext["extensions"]] == [2, 1]
        assert len(ext["all_members"]) == 2
        assert result["score"] == 0.9
        # strategy survived counter_arguments scrub.
        assert result["counter_arguments"][0]["strategy"] == "reductio"

    def test_idempotent_on_deanonymized(self):
        first = sanitize_state(_deanonymized_state())
        second = sanitize_state(first)
        assert json.dumps(second, ensure_ascii=False).count(LEAK) == 0


class TestSanitizeNarrativeActs:
    def test_acts_replaced_with_length(self):
        for field in ("act1_framing", "act2_narrative", "act3_conclusion"):
            state = {field: f"{LEAK} content here"}
            result = sanitize_state(state)
            assert isinstance(result[field], dict)
            assert result[field]["length"] == len(f"{LEAK} content here")
            assert result[field]["stripped"] is True

    def test_final_conclusion_replaced_with_length(self):
        state = {"final_conclusion": f"{LEAK} the conclusion"}
        result = sanitize_state(state)
        assert isinstance(result["final_conclusion"], dict)
        assert result["final_conclusion"]["stripped"] is True

    def test_none_conclusion_left_as_none(self):
        state = {"final_conclusion": None}
        result = sanitize_state(state)
        assert result["final_conclusion"] is None


class TestSanitizeDictOfDicts:
    def test_fallacy_justification_dropped(self):
        state = {
            "identified_fallacies": {
                "f1": {"type": "ad_hominem", "justification": LEAK, "family": "x"}
            }
        }
        result = sanitize_state(state)
        entry = result["identified_fallacies"]["f1"]
        assert "justification" not in entry
        assert entry["type"] == "ad_hominem"  # structure preserved

    def test_belief_set_content_dropped(self):
        state = {"belief_sets": {"bs1": {"logic_type": "PL", "content": LEAK}}}
        result = sanitize_state(state)
        entry = result["belief_sets"]["bs1"]
        assert "content" not in entry
        assert entry["logic_type"] == "PL"


class TestSanitizeLists:
    def test_extracts_content_dropped(self):
        # Regression: extracts was registered with an empty text-key set, so
        # nothing was scrubbed. content must now be removed.
        state = {"extracts": [{"id": "e1", "name": "n", "content": LEAK}]}
        result = sanitize_state(state)
        assert "content" not in result["extracts"][0]
        assert result["extracts"][0]["name"] == "n"

    def test_transcription_text_and_speaker_dropped(self):
        state = {
            "transcription_segments": [
                {"id": "t1", "text": LEAK, "speaker": LEAK, "start_time": 0.0}
            ]
        }
        result = sanitize_state(state)
        seg = result["transcription_segments"][0]
        assert "text" not in seg
        assert "speaker" not in seg
        assert seg["start_time"] == 0.0

    def test_analysis_trace_summary_dropped(self):
        state = {"analysis_trace": [{"phase": "p", "agent": "a", "summary": LEAK}]}
        result = sanitize_state(state)
        assert "summary" not in result["analysis_trace"][0]
        assert result["analysis_trace"][0]["agent"] == "a"


class TestSanitizeSymbolMapping:
    def test_variables_opacified(self):
        state = {
            "nl_to_logic_translations": [
                {
                    "id": "n1",
                    "original_text": LEAK,
                    "formula": "p & q",
                    "variables": {"p": "rain is wet", "q": "street wet"},
                }
            ]
        }
        result = sanitize_state(state)
        entry = result["nl_to_logic_translations"][0]
        # original_text dropped
        assert "original_text" not in entry
        # atom keys preserved, NL meanings opacified (8-char hex), no leak
        variables = entry["variables"]
        assert set(variables.keys()) == {"p", "q"}
        assert all(isinstance(v, str) and len(v) == 8 for v in variables.values())
        assert "rain" not in json.dumps(variables)


class TestSanitizeStakes:
    def test_stakes_reduced_to_counts(self):
        state = {
            "stakes_and_stakeholders": {
                "stakes": [LEAK, LEAK, LEAK],
                "stakeholders": [LEAK],
                "rhetorical_register": LEAK,
                "discursive_arena": LEAK,
            }
        }
        result = sanitize_state(state)
        summary = result["stakes_and_stakeholders"]
        assert summary["stakes_count"] == 3
        assert summary["stakeholders_count"] == 1
        assert summary["has_rhetorical_register"] is True
        assert summary["has_discursive_arena"] is True
        assert summary["stripped"] is True
        assert LEAK not in json.dumps(summary)


class TestSanitizeSourceMetadata:
    """source_metadata (threaded real by Track 1 #1259) must be opacified.

    Regression: cross-verify by po-2023 found source_metadata was not scrubbed
    by #1263 — it passed through verbatim, leaking the real title/speaker_role
    (nominative per CLAUDE.md privacy) into the exported JSON.
    """

    def test_values_opacified_keys_kept(self):
        state = {
            "source_metadata": {
                "genre": "political speech",
                "speaker_role": "head of state",
                "channel": "public arena",
                "title": "The Real Nominative Title",
            }
        }
        result = sanitize_state(state)
        meta = result["source_metadata"]
        # Structural keys survive (which metadata was present).
        assert set(meta.keys()) == {"genre", "speaker_role", "channel", "title"}
        # Values are opaque (8-char hex), no real content survives.
        for v in meta.values():
            assert isinstance(v, str)
            assert len(v) == 8
        blob = json.dumps(meta)
        assert "political" not in blob
        assert "Nominative" not in blob
        assert "head of state" not in blob

    def test_empty_metadata_left_untouched(self):
        state = {"source_metadata": {}}
        result = sanitize_state(state)
        assert result["source_metadata"] == {}

    def test_non_string_values_preserved(self):
        # Defensive: a non-string value (shouldn't happen per type, but guard
        # against a drift) is left as-is rather than crashing.
        state = {"source_metadata": {"count": 3, "genre": "x" * 20}}
        result = sanitize_state(state)
        assert result["source_metadata"]["count"] == 3


class TestSanitizeDungListSubkeys:
    """#1265 (Track 3 follow-up): dung_frameworks.arguments/attacks carry the
    real claim text (via _extract_arguments_from_context) and must be opacified.

    The list structure + topology survive (so argument/attack counts and Dung
    extension membership are preserved downstream); only the claim *content*
    is replaced by opaque_id. Cross-verified nominative firsthand by po-2023.
    """

    def test_arguments_opacified_topology_preserved(self):
        state = {
            "dung_frameworks": {
                "df_1": {
                    "name": "fw_1",
                    "arguments": ["real claim alpha", "real claim beta"],
                    "attacks": [["real claim alpha", "real claim beta"]],
                }
            }
        }
        result = sanitize_state(state)
        fw = result["dung_frameworks"]["df_1"]
        # arity preserved
        assert len(fw["arguments"]) == 2
        assert len(fw["attacks"]) == 1
        assert len(fw["attacks"][0]) == 2
        # structural label untouched
        assert fw["name"] == "fw_1"
        # content opacified: 8-char hex, no real text survives
        for arg in fw["arguments"]:
            assert isinstance(arg, str) and len(arg) == 8
        blob = json.dumps(fw)
        assert "real claim" not in blob
        assert "alpha" not in blob and "beta" not in blob

    def test_topology_stable_same_text_same_opaque(self):
        # The same claim text appears as both an argument and an attack source,
        # so the attack must reference the SAME opaque id (topology preserved).
        state = {
            "dung_frameworks": {
                "df_1": {
                    "arguments": ["shared claim"],
                    "attacks": [["shared claim", "shared claim"]],
                }
            }
        }
        result = sanitize_state(state)
        fw = result["dung_frameworks"]["df_1"]
        opaque_arg = fw["arguments"][0]
        # The attack source and target both map to the same opaque id as the arg.
        assert fw["attacks"][0][0] == opaque_arg
        assert fw["attacks"][0][1] == opaque_arg

    def test_attacks_nested_list_opacified(self):
        state = {
            "dung_frameworks": {
                "df_1": {
                    "arguments": [],
                    "attacks": [["attacker text", "target text"]],
                }
            }
        }
        result = sanitize_state(state)
        pair = result["dung_frameworks"]["df_1"]["attacks"][0]
        assert all(isinstance(t, str) and len(t) == 8 for t in pair)
        assert "attacker" not in json.dumps(pair)


class TestSanitizeLlmAssessment:
    """#1265: argument_quality_scores[*].llm_assessment is an LLM narrative
    citing/paraphrasing the real argument (verify-the-verification). Pure
    narrative, 0 quantitative value — dropped. The aggregates survive.
    """

    def test_llm_assessment_dropped_aggregates_survive(self):
        state = {
            "argument_quality_scores": {
                "arg_1": {
                    "overall": 4.5,
                    "scores": {"clarity": 4, "coherence": 5, "relevance": 4},
                    "llm_assessment": "The argument about the real nominative claim is clear.",
                }
            }
        }
        result = sanitize_state(state)
        entry = result["argument_quality_scores"]["arg_1"]
        assert "llm_assessment" not in entry
        assert entry["overall"] == 4.5
        assert entry["scores"] == {"clarity": 4, "coherence": 5, "relevance": 4}
        assert "nominative" not in json.dumps(entry)


class TestSanitizeDungExtensions:
    """#1271: the dung_frameworks[*].extensions subtree holds the SAME claim
    texts as ``arguments`` (Tweety returns extensions as sets of those claims).
    Both ``extensions.extensions`` (list of lists) and ``extensions.all_members``
    (flat list) are opacified recursively; set arity/topology + the structural
    ``count``/``sizes`` survive. ``name`` is verified non-nominative firsthand
    (all callers pass a structural label) and is left untouched.

    Firsthand-surfaced by po-2023 (FB-39 cross-verify of #1268), out of #1265's
    scope (which named only ``arguments``).
    """

    def _make_state(self):
        return {
            "dung_frameworks": {
                "df_1": {
                    "name": "verification_preferred",  # structural label
                    "arguments": ["real claim alpha", "real claim beta"],
                    "attacks": [["real claim alpha", "real claim beta"]],
                    "extensions": {
                        "extensions": [
                            ["real claim alpha"],
                            ["real claim alpha", "real claim beta"],
                        ],
                        "count": 2,
                        "sizes": [1, 2],
                        "all_members": ["real claim alpha", "real claim beta"],
                    },
                }
            }
        }

    def test_extensions_list_of_lists_opacified(self):
        result = sanitize_state(self._make_state())
        ext = result["dung_frameworks"]["df_1"]["extensions"]
        # arity + per-extension size preserved
        assert len(ext["extensions"]) == 2
        assert [len(s) for s in ext["extensions"]] == [1, 2]
        # content opacified
        for ext_set in ext["extensions"]:
            for claim in ext_set:
                assert isinstance(claim, str) and len(claim) == 8
        assert "real claim" not in json.dumps(ext)
        assert "alpha" not in json.dumps(ext) and "beta" not in json.dumps(ext)

    def test_all_members_flat_list_opacified(self):
        result = sanitize_state(self._make_state())
        members = result["dung_frameworks"]["df_1"]["extensions"]["all_members"]
        assert len(members) == 2
        for claim in members:
            assert isinstance(claim, str) and len(claim) == 8
        assert "real claim" not in json.dumps(members)

    def test_structural_count_sizes_preserved(self):
        result = sanitize_state(self._make_state())
        ext = result["dung_frameworks"]["df_1"]["extensions"]
        assert ext["count"] == 2
        assert ext["sizes"] == [1, 2]

    def test_name_structural_label_left_untouched(self):
        # DoD #2: name verified non-nominative firsthand — all callers pass a
        # structural label (verification_<sem>, social_af, delp_analysis, ...).
        # It must survive untouched (anti-pendule: no over-scrub).
        result = sanitize_state(self._make_state())
        assert result["dung_frameworks"]["df_1"]["name"] == "verification_preferred"

    def test_topology_stable_shared_claim_same_opaque(self):
        # The same claim text appears in arguments, an extension set, and
        # all_members — each occurrence must map to the SAME opaque id (so the
        # "which arguments are jointly accepted" topology is preserved).
        state = {
            "dung_frameworks": {
                "df_1": {
                    "name": "fw_1",
                    "arguments": ["shared claim"],
                    "attacks": [],
                    "extensions": {
                        "extensions": [["shared claim"]],
                        "count": 1,
                        "sizes": [1],
                        "all_members": ["shared claim"],
                    },
                }
            }
        }
        result = sanitize_state(state)
        fw = result["dung_frameworks"]["df_1"]
        opaque_arg = fw["arguments"][0]
        assert fw["extensions"]["extensions"][0][0] == opaque_arg
        assert fw["extensions"]["all_members"][0] == opaque_arg

    def test_empty_extensions_handled(self):
        # Degraded Dung result: extensions = {} (no JVM reasoner, #1019).
        state = {"dung_frameworks": {"df_1": {"name": "fw", "extensions": {}}}}
        result = sanitize_state(state)
        assert result["dung_frameworks"]["df_1"]["extensions"] == {}

    def test_extensions_missing_subtree_no_crash(self):
        # Defensive: a dung entry without an extensions subtree is left intact.
        state = {"dung_frameworks": {"df_1": {"name": "fw", "arguments": ["a"]}}}
        result = sanitize_state(state)
        assert "extensions" not in result["dung_frameworks"]["df_1"]


class TestListShapedContainers1664:
    """#1664 — the six list-shaped containers carrying the same claim text.

    Every state here is built by the REAL writers and serialized by the REAL
    ``get_state_snapshot()``. A literal fixture cannot prove anything about
    this defect: the passes written for ``dung_frameworks`` gate on
    ``isinstance(..., dict)``, so a fixture that builds these containers as
    dicts hands the guard the one shape no writer emits, and the test agrees
    with itself while the mechanism is dead.

    The planted string carries NO name from the fixed entity allowlist, so the
    protection under measurement is the SHAPE-based one, not the name-based
    final pass.
    """

    NL = "The speaker asserts that the proposed reform is the only viable path forward"
    OTHER_NL = "A second claim contending that the timetable was never realistic"

    def _snapshot(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("initial")
        state.add_ranking_result("burden", [self.NL], [{"rank": 1}])
        state.add_probabilistic_result([self.NL], {self.NL: 0.75})
        state.add_bipolar_result("necessity", [self.NL], [[self.NL, self.OTHER_NL]])
        state.add_aspic_result(
            "simple", [[self.NL], [self.NL, self.OTHER_NL]], {"n": 2}
        )
        state.add_belief_revision_result("dalal", [self.NL], [self.OTHER_NL])
        state.add_dialogue_result(
            self.NL,
            "accepted",
            [
                {
                    "round": 1,
                    "speaker": "opponent",
                    "action": "attack",
                    "argument": self.OTHER_NL,
                    "target": self.NL,
                }
            ],
        )
        state.add_debate_transcript(
            self.NL,
            [{"proponent_move": self.NL, "opponent_move": self.OTHER_NL}],
            "proponent",
        )
        return state.get_state_snapshot()

    # --- premise guard: must SURVIVE the fix ---------------------------------

    @pytest.mark.parametrize(
        "field",
        [
            "ranking_results",
            "probabilistic_results",
            "bipolar_results",
            "aspic_results",
            "belief_revision_results",
            "dialogue_results",
            "debate_transcripts",
        ],
    )
    def test_writers_emit_list_shaped_containers(self, field):
        # Pins the premise of the whole defect: these are lists, so any pass
        # gated on isinstance(container, dict) is unreachable for them. If a
        # future refactor unifies the shapes, this fails FIRST and says why,
        # instead of letting a dict-gated pass silently re-cover half of them.
        snap = self._snapshot()
        assert isinstance(snap[field], list), f"{field} is no longer list-shaped"
        assert isinstance(snap["dung_frameworks"], dict)

    # --- the defect: must DIE when the fix is reverted ------------------------

    @pytest.mark.parametrize(
        "field,subkey",
        [
            ("ranking_results", "arguments"),
            ("probabilistic_results", "arguments"),
            ("bipolar_results", "arguments"),
            ("bipolar_results", "supports"),
            ("aspic_results", "extensions"),
            ("belief_revision_results", "original"),
            ("belief_revision_results", "revised"),
        ],
    )
    def test_claim_text_subkeys_are_opacified(self, field, subkey):
        result = sanitize_state(self._snapshot())
        assert self.NL not in json.dumps(
            result[field]
        ), f"{field}[*].{subkey}: claim text survived sanitize_state"
        assert self.OTHER_NL not in json.dumps(result[field])

    def test_probabilistic_acceptance_map_keys_opacified_values_kept(self):
        # The map is built as {arg_text: prob} by the producer, so the KEYS
        # carry the payload. The distribution itself must survive intact.
        result = sanitize_state(self._snapshot())
        probs = result["probabilistic_results"][0]["acceptance_probabilities"]
        assert self.NL not in probs
        assert len(probs) == 1
        assert list(probs.values()) == [0.75]

    def test_dialogue_trace_leaves_opacified_vocabulary_kept(self):
        result = sanitize_state(self._snapshot())
        move = result["dialogue_results"][0]["trace"][0]
        assert self.NL not in json.dumps(move)
        assert self.OTHER_NL not in json.dumps(move)
        # Closed vocabularies and turn structure survive.
        assert move["speaker"] == "opponent"
        assert move["action"] == "attack"
        assert move["round"] == 1

    def test_debate_exchanges_moves_opacified(self):
        # _TEXT_STRIP_LISTS already declared proponent_move/opponent_move, but
        # the real writer nests them inside `exchanges` — the declaration had
        # no target until this pass.
        result = sanitize_state(self._snapshot())
        exchange = result["debate_transcripts"][0]["exchanges"][0]
        assert self.NL not in json.dumps(exchange)
        assert self.OTHER_NL not in json.dumps(exchange)

    def test_bipolar_support_topology_preserved(self):
        # Arity and the identity relation must survive: the support pair still
        # links the SAME two opaque ids that appear in `arguments`.
        result = sanitize_state(self._snapshot())
        entry = result["bipolar_results"][0]
        assert len(entry["supports"]) == 1
        assert len(entry["supports"][0]) == 2
        # Non-vacuity: on unscrubbed input both sides are the raw claim text,
        # so the identity below would hold trivially. Pin that the values are
        # opacified FIRST, then that the relation between them survived.
        assert entry["arguments"][0] != self.NL
        assert entry["supports"][0][0] == entry["arguments"][0]

    def test_aspic_attacks_atoms_opacified_scope_vocabulary_kept(self):
        """#1649 privacy follow-up: aspic_results[*].attacks (qualified attacks
        surfaced top-level by #1681, read by the #1699 reader) carry source-
        derived atoms in target/attacker_premises → opacified. scope (undercut/
        rebut/undermine/unresolved) and attacker_rule (def_con_N) are closed
        vocabularies at every producer → preserved, exactly as
        dung_frameworks.name is. Built by the real add_aspic_result +
        get_state_snapshot, not a literal fixture.
        """
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("initial")
        state.add_aspic_result(
            "simple",
            [["a"]],
            {"n": 1},
            attacks=[
                {
                    "target": self.NL,
                    "attacker_premises": [self.OTHER_NL],
                    "scope": "undercut",
                    "attacker_rule": "def_con_1",
                }
            ],
        )
        result = sanitize_state(state.get_state_snapshot())
        atk = result["aspic_results"][0]["attacks"][0]
        # Source-derived atoms opacified (not the raw NL text).
        assert atk["target"] != self.NL
        assert atk["attacker_premises"][0] != self.OTHER_NL
        assert self.NL not in json.dumps(result["aspic_results"])
        assert self.OTHER_NL not in json.dumps(result["aspic_results"])
        # Closed vocabularies survive — the #1699 reader names the scope to
        # qualify the attack; opacifying it would erase the axis's contribution.
        assert atk["scope"] == "undercut"
        assert atk["attacker_rule"] == "def_con_1"

    def test_no_planted_claim_text_survives_anywhere(self):
        blob = json.dumps(sanitize_state(self._snapshot()))
        assert self.NL not in blob
        assert self.OTHER_NL not in blob

    # --- anti-pendulum: structural aggregates must SURVIVE the fix -----------

    def test_structural_labels_not_over_scrubbed(self):
        # Measured at every producer: these are closed vocabularies, and the
        # contract promises to preserve structural aggregates. Scrubbing them
        # would be the pendulum swing.
        result = sanitize_state(self._snapshot())
        assert result["ranking_results"][0]["method"] == "burden"
        assert result["bipolar_results"][0]["framework_type"] == "necessity"
        assert result["aspic_results"][0]["reasoner_type"] == "simple"
        assert result["belief_revision_results"][0]["method"] == "dalal"
        assert result["dialogue_results"][0]["outcome"] == "accepted"
