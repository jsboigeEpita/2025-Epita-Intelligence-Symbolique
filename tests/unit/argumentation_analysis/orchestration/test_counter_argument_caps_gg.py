"""Tests for the counter-argument volume defect (Track GG #696).

The pipeline used to cap counter-arguments at <=5 (top-3 fallacies + 5 total
targets) on the sequential path and under-produce them on the conversational
path, losing to the zero-shot baseline on the quantitative axis. These tests
verify, with a mocked LLM (no real API), that:

  1. ``_generate_counters_for_targets`` sweeps EVERY target (no cap) and batches
     long target lists across multiple LLM calls.
  2. ``_invoke_counter_argument`` builds one target per fallacy AND per argument
     (no top-3 / total-5 caps).
  3. ``_generate_counter_arguments_from_state`` produces >=1 counter-argument per
     identified argument and writes each back via ``add_counter_argument``.
  4. The conversational orchestrator module imports cleanly with the new 5b-6
     post-processor wired in.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import argumentation_analysis.orchestration.invoke_callables as mod


def _resp(content: str):
    """Build a fake OpenAI chat completion response carrying ``content``."""
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = content
    response.choices = [choice]
    return response


def _client_one_per_target():
    """Mock client whose create() returns one counter per listed target line."""

    async def fake_create(**kwargs):
        user_msg = kwargs["messages"][1]["content"]
        n = len([ln for ln in user_msg.splitlines() if ln.strip()])
        arr = [
            {
                "counter_argument": f"Counter {i}",
                "strategy_used": "distinction",
                "target_argument": f"target {i}",
                "strength": "moderate",
                "reasoning": "because",
            }
            for i in range(n)
        ]
        return _resp(json.dumps(arr))

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_create)
    return client


class TestParseCounterArray:
    """_parse_counter_array tolerates fenced, bare, and single-object JSON."""

    def test_plain_array(self):
        raw = '[{"counter_argument": "x"}, {"counter_argument": "y"}]'
        out = mod._parse_counter_array(raw)
        assert len(out) == 2
        assert out[0]["counter_argument"] == "x"

    def test_json_fenced_array(self):
        raw = '```json\n[{"counter_argument": "x"}]\n```'
        out = mod._parse_counter_array(raw)
        assert len(out) == 1

    def test_single_object_wrapped_to_list(self):
        raw = '{"counter_argument": "only one"}'
        out = mod._parse_counter_array(raw)
        assert out == [{"counter_argument": "only one"}]

    def test_garbage_returns_empty(self):
        assert mod._parse_counter_array("no json here") == []
        assert mod._parse_counter_array("") == []


class TestGenerateCountersForTargets:
    """The batching helper has NO cap and aggregates across batches."""

    async def test_no_cap_sweeps_all_targets(self):
        client = _client_one_per_target()
        targets = [f"arg {i}" for i in range(25)]
        out = await mod._generate_counters_for_targets(
            client, "model", targets, batch_size=12
        )
        # 25 targets => one counter each, never capped at 5.
        assert len(out) == 25

    async def test_batches_split_long_target_lists(self):
        client = _client_one_per_target()
        targets = [f"arg {i}" for i in range(25)]
        await mod._generate_counters_for_targets(
            client, "model", targets, batch_size=12
        )
        # 25 / 12 => batches of 12, 12, 1 => 3 LLM calls.
        assert client.chat.completions.create.call_count == 3

    async def test_one_batch_failure_does_not_sink_others(self):
        calls = {"n": 0}

        async def flaky_create(**kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("transient")
            # Batch 2 returns 1/12 (thin) → triggers retry, which also returns 1.
            return _resp('[{"counter_argument": "ok"}]')

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=flaky_create)
        targets = [f"arg {i}" for i in range(24)]  # 2 batches of 12
        out = await mod._generate_counters_for_targets(
            client, "model", targets, batch_size=12
        )
        # First batch raised. Second batch: 1 CA + 1 retry CA = 2 total.
        assert len(out) == 2


class TestInvokeCounterArgumentNoCaps:
    """_invoke_counter_argument targets every fallacy AND every argument."""

    async def test_all_fallacies_and_args_become_targets(self):
        context = {
            "phase_extract_output": {
                "arguments": [{"text": f"argument number {i}"} for i in range(10)]
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"type": f"fallacy_{i}", "explanation": "e"} for i in range(6)
                ]
            },
            "phase_quality_output": {"per_argument_scores": {}},
        }
        captured = AsyncMock(return_value=[])
        with patch.object(
            mod, "_get_openai_client", return_value=(MagicMock(), "model")
        ), patch.object(mod, "_generate_counters_for_targets", new=captured):
            await mod._invoke_counter_argument("some input text", context)

        # Positional call: (client, model_id, targets)
        targets = captured.call_args.args[2]
        # 6 fallacies (not capped to 3) + 10 args (not capped to 5) = 16.
        assert len(targets) == 16
        assert sum(1 for t in targets if t.startswith("[FALLACY:")) == 6


class TestGenerateCounterArgumentsFromState:
    """The conversational post-processor sweeps every identified argument.

    YY #730 changed the caller default to ``k_per_target=2`` so the CONV path
    beats the zero-shot baseline on counter-argument volume on the observed
    corpora. With the per-target-line mock, the first call returns 1 CA/target
    (mock contract), the helper's thin-batch retry returns another full batch,
    so total CAs per state call = ``2 × len(targets)``.
    """

    async def test_k2_floor_two_counters_per_argument(self):
        state = MagicMock()
        state.identified_arguments = [{"text": "a1"}, {"text": "a2"}, {"text": "a3"}]
        state.add_counter_argument = MagicMock(return_value="ca_1")
        client = _client_one_per_target()
        with patch.object(mod, "_get_openai_client", return_value=(client, "model")):
            result = await mod._generate_counter_arguments_from_state(state)

        assert result["targets"] == 3
        # YY #730: default k=2 ⇒ floor = 2 × targets = 6 (mock + thin-batch retry)
        assert result["added"] == 6
        assert state.add_counter_argument.call_count == 6

    async def test_no_args_is_noop(self):
        state = MagicMock()
        state.identified_arguments = []
        result = await mod._generate_counter_arguments_from_state(state)
        assert result == {"added": 0, "targets": 0}

    async def test_no_client_reports_targets_but_adds_nothing(self):
        state = MagicMock()
        state.identified_arguments = [{"text": "a1"}, {"text": "a2"}]
        state.add_counter_argument = MagicMock()
        with patch.object(mod, "_get_openai_client", return_value=(None, "")):
            result = await mod._generate_counter_arguments_from_state(state)
        assert result == {"added": 0, "targets": 2}
        state.add_counter_argument.assert_not_called()

    async def test_plain_string_arguments_supported(self):
        state = MagicMock()
        state.identified_arguments = ["bare string arg one", "bare string arg two"]
        state.add_counter_argument = MagicMock(return_value="ca")
        client = _client_one_per_target()
        with patch.object(mod, "_get_openai_client", return_value=(client, "model")):
            result = await mod._generate_counter_arguments_from_state(state)
        assert result["targets"] == 2
        # YY #730: 2 targets × k=2 = 4 CAs (initial + thin-batch retry).
        assert result["added"] == 4


class TestConversationalWiring:
    """The 5b-6 post-processor edit must keep the orchestrator importable."""

    def test_orchestrator_imports_and_helper_present(self):
        import argumentation_analysis.orchestration.conversational_orchestrator as co

        assert hasattr(co, "run_conversational_analysis")
        # The helper the 5b-6 block calls must exist on the invoke module.
        assert hasattr(mod, "_generate_counter_arguments_from_state")


class TestGGbisRetryOnThinBatch:
    """GG-bis #709: retry once when a batch returns fewer CAs than targets."""

    async def test_thin_batch_triggers_one_retry(self):
        call_count = {"n": 0}

        async def thin_then_full(**kwargs):
            call_count["n"] += 1
            user_msg = kwargs["messages"][1]["content"]
            n = len([ln for ln in user_msg.splitlines() if ln.strip()])
            if call_count["n"] == 1:
                # First call: return only half
                arr = [
                    {
                        "counter_argument": f"Counter {i}",
                        "strategy_used": "distinction",
                        "target_argument": f"target {i}",
                        "strength": "moderate",
                        "reasoning": "because",
                    }
                    for i in range(n // 2)
                ]
            else:
                # Retry: return full
                arr = [
                    {
                        "counter_argument": f"Counter {i}",
                        "strategy_used": "distinction",
                        "target_argument": f"target {i}",
                        "strength": "moderate",
                        "reasoning": "because",
                    }
                    for i in range(n)
                ]
            return _resp(json.dumps(arr))

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=thin_then_full)
        targets = [f"arg {i}" for i in range(6)]
        out = await mod._generate_counters_for_targets(
            client, "model", targets, batch_size=12
        )
        # First call: 3 CAs (half of 6). Retry: 6 CAs. Total = 9.
        assert len(out) == 9
        assert call_count["n"] == 2

    async def test_full_batch_no_retry(self):
        client = _client_one_per_target()
        targets = [f"arg {i}" for i in range(5)]
        out = await mod._generate_counters_for_targets(
            client, "model", targets, batch_size=12
        )
        # Full batch (5/5), no retry
        assert len(out) == 5
        assert client.chat.completions.create.call_count == 1


class TestGGbisCoverageGuarantee:
    """GG-bis #709: _generate_counter_arguments_from_state retries uncovered args."""

    async def test_uncovered_arguments_get_retried(self):
        """If first pass adds fewer CAs than targets, a retry fills the gap."""
        state = MagicMock()
        state.identified_arguments = [{"text": f"arg_{i}"} for i in range(5)]
        state.counter_arguments = []
        state.add_counter_argument = MagicMock(return_value="ca")

        call_count = {"n": 0}

        async def thin_first(**kwargs):
            call_count["n"] += 1
            user_msg = kwargs["messages"][1]["content"]
            n = len([ln for ln in user_msg.splitlines() if ln.strip()])
            if call_count["n"] == 1:
                # First: only 2 out of 5
                arr = [
                    {
                        "counter_argument": f"Counter {i}",
                        "strategy_used": "distinction",
                        "target_argument": f"target {i}",
                        "strength": "moderate",
                        "reasoning": "because",
                    }
                    for i in range(2)
                ]
            else:
                # Retry: full coverage of uncovered targets
                arr = [
                    {
                        "counter_argument": f"Counter {i}",
                        "strategy_used": "distinction",
                        "target_argument": f"target {i}",
                        "strength": "moderate",
                        "reasoning": "because",
                    }
                    for i in range(n)
                ]
            return _resp(json.dumps(arr))

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=thin_first)
        with patch.object(mod, "_get_openai_client", return_value=(client, "model")):
            result = await mod._generate_counter_arguments_from_state(state)

        # First pass: 2 added. Retry covers the 3 uncovered => total >= 5.
        assert result["targets"] == 5
        assert result["added"] >= 5
        assert call_count["n"] >= 2  # first pass + retry


class TestYYCounterArgumentFloor:
    """Track YY #730: k_per_target floor in CONV CA generation.

    On corpus_C, CONV produced 13 CAs vs 18 zero-shot (LOSS -5). Pattern across
    A/B/C: CONV CA = args_count + 1 — too thin to beat 0-shot when baseline >
    args_count. Fix: ``_generate_counters_for_targets`` accepts ``k_per_target``,
    and ``_generate_counter_arguments_from_state`` defaults k=2 (calibrating
    higher when state exposes ``zero_shot_reference``).
    """

    async def test_helper_k_param_emits_k_in_prompt(self):
        """The helper passes k to the system prompt so the LLM emits k CAs."""
        captured_prompts = []

        async def capture(**kwargs):
            captured_prompts.append(kwargs["messages"][0]["content"])
            return _resp("[]")

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=capture)
        await mod._generate_counters_for_targets(
            client, "model", ["t1", "t2"], k_per_target=3
        )
        assert captured_prompts
        prompt = captured_prompts[0]
        assert "3 DISTINCT" in prompt or "3 distinct" in prompt.lower()
        assert (
            "DIFFERENT strategies" in prompt or "different strategies" in prompt.lower()
        )

    async def test_helper_k1_keeps_single_strategy_clause(self):
        """k=1 preserves the original GG-style 'one per target' phrasing."""
        captured = []

        async def cap(**kwargs):
            captured.append(kwargs["messages"][0]["content"])
            return _resp("[]")

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=cap)
        await mod._generate_counters_for_targets(
            client, "model", ["t1"], k_per_target=1
        )
        assert "EXACTLY one" in captured[0] or "exactly one" in captured[0].lower()

    async def test_zero_shot_reference_calibrates_k(self):
        """When state exposes zero_shot_reference, k is bumped to clear it."""
        state = MagicMock()
        state.identified_arguments = [{"text": f"a{i}"} for i in range(4)]
        # 4 targets vs 0-shot=18 → need ≥19 ⇒ k = ceil(19/4) = 5
        state.zero_shot_reference = {"counter_arguments": 18}
        state.add_counter_argument = MagicMock(return_value="ca")
        captured_prompts: list[str] = []

        async def cap(**kwargs):
            captured_prompts.append(kwargs["messages"][0]["content"])
            user_msg = kwargs["messages"][1]["content"]
            n = len([ln for ln in user_msg.splitlines() if ln.strip()])
            return _resp(
                json.dumps(
                    [
                        {"counter_argument": f"c{i}", "target_argument": f"t{i}"}
                        for i in range(n)
                    ]
                )
            )

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=cap)
        with patch.object(mod, "_get_openai_client", return_value=(client, "model")):
            await mod._generate_counter_arguments_from_state(state)
        assert captured_prompts
        # k should have been bumped to 5 (ceil(19/4))
        assert (
            "5 DISTINCT" in captured_prompts[0]
            or "5 distinct" in captured_prompts[0].lower()
        )

    async def test_missing_zero_shot_reference_defaults_to_k2(self):
        """No zero_shot_reference on state ⇒ caller defaults to k=2 floor."""
        state = MagicMock(spec=["identified_arguments", "add_counter_argument"])
        state.identified_arguments = [{"text": f"a{i}"} for i in range(3)]
        state.add_counter_argument = MagicMock(return_value="ca")
        captured: list[str] = []

        async def cap(**kwargs):
            captured.append(kwargs["messages"][0]["content"])
            user_msg = kwargs["messages"][1]["content"]
            n = len([ln for ln in user_msg.splitlines() if ln.strip()])
            return _resp(
                json.dumps(
                    [
                        {"counter_argument": f"c{i}", "target_argument": f"t{i}"}
                        for i in range(n)
                    ]
                )
            )

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=cap)
        with patch.object(mod, "_get_openai_client", return_value=(client, "model")):
            await mod._generate_counter_arguments_from_state(state)
        assert captured
        # Default k=2 from caller
        assert "2 DISTINCT" in captured[0] or "2 distinct" in captured[0].lower()

    async def test_low_zero_shot_reference_does_not_lower_k_below_2(self):
        """If 0-shot < 2 × args, k stays at the k=2 floor (never drops)."""
        state = MagicMock()
        state.identified_arguments = [{"text": f"a{i}"} for i in range(10)]
        state.zero_shot_reference = {"counter_arguments": 5}  # 5 < 2×10 = 20
        state.add_counter_argument = MagicMock(return_value="ca")
        captured: list[str] = []

        async def cap(**kwargs):
            captured.append(kwargs["messages"][0]["content"])
            user_msg = kwargs["messages"][1]["content"]
            n = len([ln for ln in user_msg.splitlines() if ln.strip()])
            return _resp(
                json.dumps(
                    [
                        {"counter_argument": f"c{i}", "target_argument": f"t{i}"}
                        for i in range(n)
                    ]
                )
            )

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=cap)
        with patch.object(mod, "_get_openai_client", return_value=(client, "model")):
            await mod._generate_counter_arguments_from_state(state)
        assert captured
        assert "2 DISTINCT" in captured[0] or "2 distinct" in captured[0].lower()

    async def test_yy_total_ca_beats_zero_shot_on_corpus_c_shape(self):
        """End-to-end: 12 args + k=2 ⇒ 24 CA ≥ 19 (0-shot+1 on corpus_C)."""
        state = MagicMock()
        state.identified_arguments = [{"text": f"argC_{i}"} for i in range(12)]
        state.add_counter_argument = MagicMock(return_value="ca")
        client = _client_one_per_target()
        with patch.object(mod, "_get_openai_client", return_value=(client, "model")):
            result = await mod._generate_counter_arguments_from_state(state)
        # With per-target mock + thin retry: 12 + 12 = 24 ≥ 19.
        assert result["targets"] == 12
        assert result["added"] >= 19, (
            f"YY #730 floor: 24 expected, got {result['added']} (must be ≥19 to "
            "beat 0-shot=18 on corpus_C)"
        )


class TestG6CounterArgumentValidation:
    """G6 (#1180): surface counter-argument validity from the 5-criteria eval.

    ``_build_counter_argument_validation`` maps the evaluator's already-computed
    overall_score + logical_strength onto the ``ValidationResult`` shape with
    documented thresholds (no fabricated formal/Dung signal — anti-pendule #1019).
    """

    def test_high_score_lands_and_is_valid(self):
        v = mod._build_counter_argument_validation(0.8, 0.7)
        assert v["counter_succeeds"] is True
        assert v["is_valid_attack"] is True
        assert v["logical_consistency"] is True
        # original_survives is the asymmetric partner (a strong counter lowers it)
        assert v["original_survives"] is False
        assert "heuristic" in v["formal_representation"]

    def test_low_score_fails_and_original_survives(self):
        v = mod._build_counter_argument_validation(0.2, 0.1)
        assert v["counter_succeeds"] is False
        assert v["is_valid_attack"] is False
        assert v["logical_consistency"] is False
        assert v["original_survives"] is True

    def test_mid_score_asymmetry(self):
        """A mid-range counter (0.55) both lands AND leaves the original standing."""
        v = mod._build_counter_argument_validation(0.55, 0.3)
        assert v["counter_succeeds"] is True
        assert v["original_survives"] is True
        # logical_strength below 0.4 ⇒ not a coherent/valid attack
        assert v["is_valid_attack"] is False

    def test_validation_populated_in_evaluate_loop(self):
        """``_evaluate_counter_arguments`` attaches validation when eval succeeds.

        We mock the evaluator so the 5-criteria math runs through the real
        population path (not a fabricated signal). Fail-loud: if the evaluator
        returns an object, validation is ALWAYS set.
        """
        fake_eval = MagicMock()
        fake_eval.overall_score = 0.75
        fake_eval.logical_strength = 0.6
        fake_eval.relevance = 0.5
        fake_eval.persuasiveness = 0.5
        fake_eval.originality = 0.5
        fake_eval.clarity = 0.5
        fake_eval.recommendations = []
        fake_evaluator = MagicMock()
        fake_evaluator.evaluate.return_value = fake_eval
        with patch(
            "argumentation_analysis.agents.core.counter_argument.evaluator.CounterArgumentEvaluator",
            return_value=fake_evaluator,
        ):
            out = mod._evaluate_counter_arguments(
                [
                    {
                        "counter_argument": "contredit la thèse par un exemple.",
                        "strategy_used": "counter-example",
                        "target_argument": "la thèse X",
                        "strength": "strong",
                    }
                ],
                "la thèse X",
            )
        assert out and out[0].get("validation") is not None
        assert out[0]["validation"]["counter_succeeds"] is True
        assert out[0]["validation"]["is_valid_attack"] is True

