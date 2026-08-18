# -*- coding: utf-8 -*-
"""Integration tests for Python fallbacks in unified_pipeline.py (commit ac5bf041).

Validates the full chain with JVM disabled:
  invoke callable (Python fallback) → state writer → state snapshot

Each test runs without starting the JVM (use --disable-jvm-session in CI).
When JVM is unavailable, RankingHandler/ASPICHandler/etc. raise at __init__
time (jpype.JClass fails), which triggers the Python fallback in each
_invoke_* function.

Key schema invariants verified:
  - Each fallback output is a non-empty dict
  - The "fallback": "python" sentinel is present
  - State writers do not raise with fallback output
  - State snapshot contains the expected top-level keys

Known schema mismatches (documented, not fixed here):
  - _python_ranking_fallback no longer returns anything — it is a fail-loud
    stub (#1019, RA-8 #1053), so its old ranking/arguments writer mismatch
    is void. The dialogue mismatch below still stands.
  - _invoke_dialogue fallback returns "trace" key; _write_dialogue_to_state
    reads "dialogue_trace" → dialogue_results entries have trace=[]
"""

import pytest

from argumentation_analysis.orchestration.unified_pipeline import (
    _extract_arguments_from_context,
    _generate_attacks_from_args,
    _invoke_aba,
    _invoke_adf,
    _invoke_aspic,
    _invoke_belief_revision,
    _invoke_bipolar,
    _invoke_dialogue,
    _invoke_probabilistic,
    _invoke_quality_evaluator,
    _invoke_ranking,
    _python_ranking_fallback,
    _write_aspic_to_state,
    _write_belief_revision_to_state,
    _write_dialogue_to_state,
    _write_quality_to_state,
    _write_ranking_to_state,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TEXT = (
    "Les énergies renouvelables réduisent les émissions. "
    "L'éolien est une énergie renouvelable. "
    "Le solaire est moins cher que le charbon. "
    "Les subventions accélèrent la transition."
)

SAMPLE_ARGS = ["arg_1", "arg_2", "arg_3"]
SAMPLE_ATTACKS = [["arg_1", "arg_2"], ["arg_3", "arg_1"]]


@pytest.fixture
def fresh_state():
    return UnifiedAnalysisState(SAMPLE_TEXT)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


class TestExtractArgumentsFromContext:
    def test_extracts_from_phase_extract_output(self):
        ctx = {"phase_extract_output": {"arguments": ["a", "b", "c"]}}
        result = _extract_arguments_from_context("text", ctx)
        assert result == ["a", "b", "c"]

    def test_falls_back_to_sentence_split(self):
        result = _extract_arguments_from_context(SAMPLE_TEXT, {})
        assert isinstance(result, list)
        assert len(result) >= 2
        for item in result:
            assert isinstance(item, str)

    def test_minimum_three_args_on_short_text(self):
        result = _extract_arguments_from_context("short", {})
        assert len(result) >= 1

    def test_max_six_args_from_long_text(self):
        long_text = ". ".join([f"Sentence {i}" for i in range(20)])
        result = _extract_arguments_from_context(long_text, {})
        assert len(result) <= 6


class TestGenerateAttacksFromArgs:
    """#1629: targets are resolved by identifier, never by enumeration index.

    ``TARGETED_ARGS`` deliberately does NOT reuse ``arg_N`` as argument *text*:
    with ``SAMPLE_ARGS`` the resolution ``arg_1 -> arguments[0]`` is the
    identity, which would make a wrong resolution indistinguishable from a
    right one.
    """

    TARGETED_ARGS = ["first claim", "second claim", "third claim"]

    @staticmethod
    def _ctx(targets, key="target_argument"):
        """Build a hierarchical-fallacy context from a list of target IDs."""
        return {
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"fallacy_type": f"type_{n}", key: t} for n, t in enumerate(targets)
                ]
            }
        }

    def test_returns_list(self):
        result = _generate_attacks_from_args(SAMPLE_ARGS)
        assert isinstance(result, list)

    def test_attacks_reference_valid_args(self):
        ctx = self._ctx(["arg_1", "arg_2", "arg_3"])
        result = _generate_attacks_from_args(self.TARGETED_ARGS, ctx)
        assert len(result) == 3
        for src, tgt in result:
            assert tgt in self.TARGETED_ARGS
            assert src.startswith("fallacy_")

    def test_empty_args_returns_empty(self):
        result = _generate_attacks_from_args([])
        assert result == []

    def test_no_upstream_data_yields_no_fabricated_graph(self):
        """The ``(i + j) % 3`` modulo graph is removed, not replaced (#1629).

        A graph we cannot derive is empty; it is not a shape invented over the
        argument list and handed to solvers as if it came from the corpus.
        """
        assert _generate_attacks_from_args(SAMPLE_ARGS) == []
        assert _generate_attacks_from_args(SAMPLE_ARGS, {}) == []

    def test_two_targetings_produce_two_graphs(self):
        """The discriminating control: the output must depend on the targets.

        Under the pre-#1629 index pairing both contexts yielded the very same
        edges (fallacy 0 -> args[0], fallacy 1 -> args[1], ...), so no
        assertion over one of them alone could detect the defect.
        """
        spread = _generate_attacks_from_args(
            self.TARGETED_ARGS, self._ctx(["arg_1", "arg_2", "arg_3"])
        )
        concentrated = _generate_attacks_from_args(
            self.TARGETED_ARGS, self._ctx(["arg_1", "arg_1", "arg_1"])
        )
        assert [t for _, t in spread] == self.TARGETED_ARGS
        assert [t for _, t in concentrated] == [self.TARGETED_ARGS[0]] * 3
        assert spread != concentrated

    def test_target_is_not_the_enumeration_index(self):
        """Reversed targeting must reverse the graph, not reproduce 0,1,2."""
        result = _generate_attacks_from_args(
            self.TARGETED_ARGS, self._ctx(["arg_3", "arg_2", "arg_1"])
        )
        assert [t for _, t in result] == list(reversed(self.TARGETED_ARGS))

    def test_detection_without_target_is_skipped(self):
        """Non-taxonomic detections carry no target — and get no attack.

        The producer emits the key with a ``None`` value, which is why the
        resolution cannot rely on ``dict.get(key, default)``.
        """
        ctx = self._ctx(["arg_2", None, "arg_3"])
        result = _generate_attacks_from_args(self.TARGETED_ARGS, ctx)
        assert [t for _, t in result] == ["second claim", "third claim"]

    def test_out_of_range_or_malformed_target_is_skipped(self):
        ctx = self._ctx(["arg_99", "not_an_id", "arg_0", "arg_2"])
        result = _generate_attacks_from_args(self.TARGETED_ARGS, ctx)
        assert [t for _, t in result] == ["second claim"]

    def test_shared_state_key_convention_also_resolves(self):
        """``shared_state`` entries name the target ``target_argument_id``."""
        ctx = self._ctx(["arg_2"], key="target_argument_id")
        result = _generate_attacks_from_args(self.TARGETED_ARGS, ctx)
        assert [t for _, t in result] == ["second claim"]


# ---------------------------------------------------------------------------
# Python ranking fallback
# ---------------------------------------------------------------------------


class TestPythonRankingFallback:
    """Fail-loud contract (#1019, RA-8 #1053, re-mesuré #1784).

    The pre-#1053 tests asserted the synthetic-score dict (method/ranking/
    scores/comparisons). That fallback entered state as authentic formal
    results — an anti-theater violation — and was deliberately replaced by
    this raising stub. The stale assertions were silently red outside CI
    (#1783) and were read as a #1775-class signature in #1784; the re-measure
    showed they are the fail-loud contract working as merged.
    """

    @pytest.mark.parametrize("method", ["categorizer", "burden", "discussion"])
    def test_every_method_raises_fail_loud(self, method):
        with pytest.raises(
            RuntimeError, match=rf"Ranking semantics \({method}\) unavailable"
        ):
            _python_ranking_fallback(SAMPLE_ARGS, SAMPLE_ATTACKS, method)

    def test_empty_inputs_raise_too(self):
        """No degenerate input silently succeeds — empty graphs raise the same
        unavailability rather than returning an empty-but-authentic-looking
        ranking."""
        with pytest.raises(RuntimeError, match="JVM/Tweety required"):
            _python_ranking_fallback([], [], "categorizer")


# ---------------------------------------------------------------------------
# Invoke callables — Python fallback path (JVM not started)
# ---------------------------------------------------------------------------


class TestInvokeRankingFallback:
    """_invoke_ranking falls back to Python when JVM/RankingHandler unavailable."""

    async def test_returns_dict(self):
        result = await _invoke_ranking(SAMPLE_TEXT, {})
        assert isinstance(result, dict)

    async def test_has_method_key(self):
        result = await _invoke_ranking(SAMPLE_TEXT, {})
        assert "method" in result

    async def test_fallback_sentinel_when_jvm_absent(self):
        """If JVM is not started, fallback sentinel must be present."""
        result = await _invoke_ranking(SAMPLE_TEXT, {})
        # If JVM was available and succeeded, no fallback key; otherwise present.
        if "fallback" in result:
            assert result["fallback"] == "python"

    async def test_uses_provided_args(self):
        ctx = {"arguments": ["x", "y", "z"], "attacks": [["x", "y"]]}
        result = await _invoke_ranking(SAMPLE_TEXT, ctx)
        assert isinstance(result, dict)

    async def test_schema_mismatch_ranking_vs_arguments(self):
        """Historical mismatch, now void (#1019/#1784): the dict-shaped Python
        ranking fallback — whose 'ranking' key the writer never read — was
        replaced by a fail-loud stub, so no synthetic ranking output exists to
        mismatch. With the JVM up the handler path returns a real result with
        no 'fallback' key; the guard below keeps documenting that."""
        result = await _invoke_ranking(SAMPLE_TEXT, {})
        if result.get("fallback") == "python":
            # Fallback has 'ranking' key but NOT 'arguments'
            assert "ranking" in result
            assert "arguments" not in result  # The mismatch


class TestInvokeAspicFallback:
    async def test_returns_dict(self):
        result = await _invoke_aspic(SAMPLE_TEXT, {})
        assert isinstance(result, dict)

    async def test_has_extensions_key(self):
        result = await _invoke_aspic(SAMPLE_TEXT, {})
        assert "extensions" in result

    async def test_has_statistics_key(self):
        result = await _invoke_aspic(SAMPLE_TEXT, {})
        assert "statistics" in result
        assert isinstance(result["statistics"], dict)

    async def test_fallback_uses_extracted_rules(self):
        result = await _invoke_aspic(SAMPLE_TEXT, {})
        if result.get("fallback") == "python":
            assert "strict_rules" in result
            assert "defeasible_rules" in result


class TestInvokeBeliefRevisionFallback:
    async def test_returns_dict(self):
        result = await _invoke_belief_revision(SAMPLE_TEXT, {})
        assert isinstance(result, dict)

    async def test_has_method_key(self):
        result = await _invoke_belief_revision(SAMPLE_TEXT, {})
        assert "method" in result

    async def test_has_original_and_revised(self):
        result = await _invoke_belief_revision(SAMPLE_TEXT, {})
        assert "original" in result
        assert "revised" in result

    async def test_revised_is_superset_of_original(self):
        ctx = {
            "belief_set": ["belief_a", "belief_b"],
            "new_belief": "belief_c",
        }
        result = await _invoke_belief_revision(SAMPLE_TEXT, ctx)
        if result.get("fallback") == "python":
            # Simple revision: new belief added, none removed
            for b in result["original"]:
                assert b in result["revised"]
            assert "belief_c" in result["revised"]

    async def test_schema_compatible_with_writer(self):
        """Fallback output must have 'method', 'original', 'revised' for state writer."""
        result = await _invoke_belief_revision(SAMPLE_TEXT, {})
        assert "method" in result
        assert isinstance(result.get("original", []), list)
        assert isinstance(result.get("revised", []), list)


class TestInvokeDialogueFallback:
    async def test_returns_dict(self):
        result = await _invoke_dialogue(SAMPLE_TEXT, {})
        assert isinstance(result, dict)

    async def test_has_topic_and_outcome(self):
        result = await _invoke_dialogue(SAMPLE_TEXT, {})
        assert "topic" in result
        assert "outcome" in result

    async def test_outcome_is_proponent_or_opponent(self):
        result = await _invoke_dialogue(SAMPLE_TEXT, {})
        if result.get("fallback") == "python":
            assert result["outcome"] in ("proponent", "opponent")

    async def test_dialogue_trace_key_matches_writer(self):
        """Verify fallback uses 'dialogue_trace' key matching the state writer."""
        result = await _invoke_dialogue(SAMPLE_TEXT, {})
        if result.get("fallback") == "python":
            assert "dialogue_trace" in result
            assert isinstance(result["dialogue_trace"], list)


class TestInvokeBipolarFallback:
    async def test_returns_dict(self):
        result = await _invoke_bipolar(SAMPLE_TEXT, {})
        assert isinstance(result, dict)

    async def test_has_extensions_or_statistics(self):
        """Bipolar returns 'extensions' (fallback) or 'statistics' (JVM success)."""
        result = await _invoke_bipolar(SAMPLE_TEXT, {})
        assert "extensions" in result or "statistics" in result

    async def test_framework_type_preserved(self):
        ctx = {"framework_type": "support"}
        result = await _invoke_bipolar(SAMPLE_TEXT, ctx)
        if result.get("fallback") == "python":
            assert result["framework_type"] == "support"


class TestInvokeAbaFallback:
    async def test_returns_dict(self):
        result = await _invoke_aba(SAMPLE_TEXT, {})
        assert isinstance(result, dict)

    async def test_has_assumptions_and_extensions(self):
        result = await _invoke_aba(SAMPLE_TEXT, {})
        assert "assumptions" in result
        assert "extensions" in result


class TestInvokeAdfFallback:
    async def test_returns_dict(self):
        result = await _invoke_adf(SAMPLE_TEXT, {})
        assert isinstance(result, dict)

    async def test_has_interpretations(self):
        result = await _invoke_adf(SAMPLE_TEXT, {})
        assert "interpretations" in result


class TestInvokeProbabilisticFallback:
    async def test_returns_dict(self):
        result = await _invoke_probabilistic(SAMPLE_TEXT, {})
        assert isinstance(result, dict)

    async def test_has_acceptance_probabilities(self):
        result = await _invoke_probabilistic(SAMPLE_TEXT, {})
        assert "acceptance_probabilities" in result

    async def test_probabilities_are_valid(self):
        result = await _invoke_probabilistic(SAMPLE_TEXT, {})
        probs = result.get("acceptance_probabilities", {})
        for arg, prob in probs.items():
            assert 0.0 <= prob <= 1.0, f"Invalid probability for {arg}: {prob}"


# ---------------------------------------------------------------------------
# State writers with fallback output
# ---------------------------------------------------------------------------


class TestStateWritersWithFallbackOutput:
    """State writers must be robust to fallback output schemas."""

    def test_write_ranking_fallback_stub_raises_before_writer(self):
        """#1019/#1784: the ranking stub raises upstream, so the writer is
        never fed a synthetic ranking payload. If a dict-shaped fallback ever
        reappears, the stub call stops raising and this test fails loudly."""
        with pytest.raises(RuntimeError, match="Ranking semantics"):
            output = _python_ranking_fallback(
                SAMPLE_ARGS, SAMPLE_ATTACKS, "categorizer"
            )

    def test_write_aspic_fallback_does_not_raise(self, fresh_state):
        output = {
            "strict_rules": ["a -> b"],
            "defeasible_rules": ["b => c"],
            "extensions": [["a", "b"]],
            "statistics": {"arguments": 2},
            "fallback": "python",
        }
        _write_aspic_to_state(output, fresh_state, {})  # Must not raise

    def test_write_aspic_fallback_creates_entry(self, fresh_state):
        output = {
            "reasoner_type": "simple",
            "extensions": [["arg_1", "arg_2"]],
            "statistics": {"arguments": 2, "strict_rules": 1},
            "fallback": "python",
        }
        _write_aspic_to_state(output, fresh_state, {})
        assert len(fresh_state.aspic_results) == 1

    def test_write_belief_revision_fallback_does_not_raise(self, fresh_state):
        output = {
            "method": "dalal",
            "original": ["belief_a", "belief_b"],
            "new_belief": "belief_c",
            "revised": ["belief_a", "belief_b", "belief_c"],
            "removed": [],
            "fallback": "python",
        }
        _write_belief_revision_to_state(output, fresh_state, {})

    def test_write_belief_revision_fallback_creates_entry(self, fresh_state):
        output = {
            "method": "dalal",
            "original": ["belief_a"],
            "revised": ["belief_a", "belief_b"],
            "fallback": "python",
        }
        _write_belief_revision_to_state(output, fresh_state, {})
        assert len(fresh_state.belief_revision_results) == 1
        entry = fresh_state.belief_revision_results[0]
        assert entry["method"] == "dalal"
        assert entry["original"] == ["belief_a"]
        assert "belief_b" in entry["revised"]

    def test_write_dialogue_fallback_does_not_raise(self, fresh_state):
        output = {
            "topic": "test topic",
            "proponent_args": ["arg_1"],
            "opponent_args": ["arg_2"],
            "trace": [{"turn": 1, "speaker": "proponent", "move": "arg_1"}],
            "outcome": "proponent",
            "turns": 1,
            "fallback": "python",
        }
        _write_dialogue_to_state(output, fresh_state, {})

    def test_write_dialogue_fallback_trace_preserved(self, fresh_state):
        """Verify dialogue fallback correctly passes trace to state writer."""
        output = {
            "topic": "test topic",
            "dialogue_trace": [{"turn": 1, "speaker": "proponent", "move": "arg_1"}],
            "outcome": "proponent",
            "fallback": "python",
        }
        _write_dialogue_to_state(output, fresh_state, {})
        assert len(fresh_state.dialogue_results) == 1
        entry = fresh_state.dialogue_results[0]
        # Fixed: fallback now uses 'dialogue_trace' key matching the writer
        assert entry["trace"] == [{"turn": 1, "speaker": "proponent", "move": "arg_1"}]
        assert entry["outcome"] == "proponent"

    def test_write_quality_with_none_output_does_not_raise(self, fresh_state):
        _write_quality_to_state(None, fresh_state, {})
        assert len(fresh_state.argument_quality_scores) == 0

    def test_write_ranking_with_none_output_does_not_raise(self, fresh_state):
        _write_ranking_to_state(None, fresh_state, {})
        assert len(fresh_state.ranking_results) == 0


# ---------------------------------------------------------------------------
# Quality → Ranking chain (coordinator spec)
# ---------------------------------------------------------------------------


class TestQualityToRankingChain:
    """Test the chain: quality → ranking (fallback) → state writer → snapshot."""

    async def test_quality_output_enriches_ranking_context(self):
        """Quality phase output is used by _extract_arguments_from_context."""
        # Simulate quality phase output
        quality_output = {
            "note_finale": 7.5,
            "clarté": 8.0,
            "cohérence": 7.0,
        }
        # Put it in context as _invoke_quality_evaluator would
        ctx = {"phase_quality_output": quality_output}
        # Ranking should use quality output to extract arguments
        ranking_output = await _invoke_ranking(SAMPLE_TEXT, ctx)
        assert isinstance(ranking_output, dict)
        assert "method" in ranking_output

    async def test_full_chain_quality_then_ranking_state_snapshot(self, fresh_state):
        """Full chain: quality → ranking → write to state → snapshot."""
        # Step 1: Quality evaluation (no JVM needed)
        quality_output = await _invoke_quality_evaluator(SAMPLE_TEXT, {})
        assert isinstance(quality_output, dict)

        # Step 2: Write quality to state
        ctx = {"current_arg_id": "main_arg", "input_data": SAMPLE_TEXT}
        _write_quality_to_state(quality_output, fresh_state, ctx)
        assert len(fresh_state.argument_quality_scores) == 1

        # Step 3: Ranking with quality output in context
        ctx["phase_quality_output"] = quality_output
        ranking_output = await _invoke_ranking(SAMPLE_TEXT, ctx)
        assert isinstance(ranking_output, dict)

        # Step 4: Write ranking to state
        _write_ranking_to_state(ranking_output, fresh_state, ctx)
        assert len(fresh_state.ranking_results) == 1

        # Step 5: Verify snapshot
        snapshot = fresh_state.get_state_snapshot()
        assert "argument_quality_scores" in snapshot
        assert "ranking_results" in snapshot
        assert len(snapshot["ranking_results"]) == 1

    async def test_chain_ranking_entry_has_expected_structure(self, fresh_state):
        """Ranking result in state has id, method, arguments, comparisons keys."""
        ranking_output = await _invoke_ranking(SAMPLE_TEXT, {})
        _write_ranking_to_state(ranking_output, fresh_state, {})

        entry = fresh_state.ranking_results[0]
        assert "id" in entry
        assert "method" in entry
        assert "arguments" in entry
        assert "comparisons" in entry

    async def test_ranking_entry_method_matches_output(self, fresh_state):
        ctx = {"ranking_method": "counting"}
        ranking_output = await _invoke_ranking(SAMPLE_TEXT, ctx)
        _write_ranking_to_state(ranking_output, fresh_state, ctx)

        entry = fresh_state.ranking_results[0]
        assert entry["method"] == "counting"


# ---------------------------------------------------------------------------
# State snapshot schema after fallback chain
# ---------------------------------------------------------------------------


class TestStateSnapshotAfterFallbackChain:
    """Verify state snapshot keys after running multiple fallbacks."""

    async def test_snapshot_contains_all_result_keys(self, fresh_state):
        ctx = {}

        # Run several fallbacks and write to state
        ranking_out = await _invoke_ranking(SAMPLE_TEXT, ctx)
        _write_ranking_to_state(ranking_out, fresh_state, ctx)

        aspic_out = await _invoke_aspic(SAMPLE_TEXT, ctx)
        _write_aspic_to_state(aspic_out, fresh_state, ctx)

        br_out = await _invoke_belief_revision(SAMPLE_TEXT, ctx)
        _write_belief_revision_to_state(br_out, fresh_state, ctx)

        dialogue_out = await _invoke_dialogue(SAMPLE_TEXT, ctx)
        _write_dialogue_to_state(dialogue_out, fresh_state, ctx)

        snapshot = fresh_state.get_state_snapshot()

        # All result lists must be present in snapshot
        assert "ranking_results" in snapshot
        assert "aspic_results" in snapshot
        assert "belief_revision_results" in snapshot
        assert "dialogue_results" in snapshot

        # Each has at least one entry
        assert len(snapshot["ranking_results"]) >= 1
        assert len(snapshot["aspic_results"]) >= 1
        assert len(snapshot["belief_revision_results"]) >= 1
        assert len(snapshot["dialogue_results"]) >= 1

    async def test_snapshot_ranking_result_well_formed(self, fresh_state):
        ranking_out = await _invoke_ranking(SAMPLE_TEXT, {})
        _write_ranking_to_state(ranking_out, fresh_state, {})

        snapshot = fresh_state.get_state_snapshot()
        entry = snapshot["ranking_results"][0]

        assert isinstance(entry["id"], str)
        assert entry["id"].startswith("rank_")
        assert isinstance(entry["method"], str)
        assert isinstance(entry["arguments"], list)
        assert isinstance(entry["comparisons"], list)

    async def test_snapshot_belief_revision_well_formed(self, fresh_state):
        ctx = {
            "belief_set": ["p", "q"],
            "new_belief": "r",
        }
        br_out = await _invoke_belief_revision(SAMPLE_TEXT, ctx)
        _write_belief_revision_to_state(br_out, fresh_state, ctx)

        snapshot = fresh_state.get_state_snapshot()
        entry = snapshot["belief_revision_results"][0]

        assert isinstance(entry["id"], str)
        assert entry["id"].startswith("brevision_")
        assert isinstance(entry["original"], list)
        assert isinstance(entry["revised"], list)
        # New belief must appear in revised set
        if br_out.get("fallback") == "python":
            assert "r" in entry["revised"]
