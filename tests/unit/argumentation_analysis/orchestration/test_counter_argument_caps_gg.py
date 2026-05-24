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
            return _resp('[{"counter_argument": "ok"}]')

        client = MagicMock()
        client.chat.completions.create = AsyncMock(side_effect=flaky_create)
        targets = [f"arg {i}" for i in range(24)]  # 2 batches of 12
        out = await mod._generate_counters_for_targets(
            client, "model", targets, batch_size=12
        )
        # First batch raised, second succeeded => still get the survivor.
        assert len(out) == 1


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
    """The conversational post-processor sweeps every identified argument."""

    async def test_one_counter_per_argument_written_back(self):
        state = MagicMock()
        state.identified_arguments = [{"text": "a1"}, {"text": "a2"}, {"text": "a3"}]
        state.add_counter_argument = MagicMock(return_value="ca_1")
        client = _client_one_per_target()
        with patch.object(
            mod, "_get_openai_client", return_value=(client, "model")
        ), patch.object(mod, "_evaluate_counter_arguments", side_effect=lambda c, t: c):
            result = await mod._generate_counter_arguments_from_state(state)

        assert result["targets"] == 3
        assert result["added"] == 3
        assert state.add_counter_argument.call_count == 3

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
        with patch.object(
            mod, "_get_openai_client", return_value=(client, "model")
        ), patch.object(mod, "_evaluate_counter_arguments", side_effect=lambda c, t: c):
            result = await mod._generate_counter_arguments_from_state(state)
        assert result["targets"] == 2
        assert result["added"] == 2


class TestConversationalWiring:
    """The 5b-6 post-processor edit must keep the orchestrator importable."""

    def test_orchestrator_imports_and_helper_present(self):
        import argumentation_analysis.orchestration.conversational_orchestrator as co

        assert hasattr(co, "run_conversational_analysis")
        # The helper the 5b-6 block calls must exist on the invoke module.
        assert hasattr(mod, "_generate_counter_arguments_from_state")
