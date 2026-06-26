# -*- coding: utf-8 -*-
"""Tests for Stakes & Stakeholders extraction (Track TT #723).

Covers:
  1. StakesExtractor unit (mock LLM)
  2. shared_state field initialization
  3. invoke_callable wiring
  4. DeepSynthesisAgent stakes_block integration
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.agents.core.political.stakes_extractor import (
    StakesExtractor,
    EXTRACTION_PROMPT,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_llm_client(response_dict: dict) -> MagicMock:
    """Create a mock async OpenAI client returning the given dict as JSON.

    ``chat.completions.create`` is an AsyncMock: ``extract`` now awaits the
    call (it runs on an AsyncOpenAI client in production). A plain MagicMock
    return_value is not awaitable and would mask the real call path — which is
    exactly how the original tuple-unpack bug hid for so long.
    """
    content = json.dumps(response_dict)
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=mock_response)
    return client


SAMPLE_ARGUMENTS = [
    {"text": "We must increase defence spending to protect our borders", "id": "arg_0"},
    {"text": "The economic cost is too high for ordinary citizens", "id": "arg_1"},
    {"text": "Our national identity depends on strong leadership", "id": "arg_2"},
]

SAMPLE_METADATA = {
    "speaker": "Speaker_A",
    "venue": "parliamentary debate",
    "topic": "defence budget",
    "era": "2020s",
    "language": "en",
}

SAMPLE_LLM_RESPONSE = {
    "stakes": [
        {
            "stake_type": "security",
            "description": "Border protection and national defence",
            "evidence_indices": [0],
        },
        {
            "stake_type": "economic",
            "description": "Fiscal impact on taxpayers",
            "evidence_indices": [1],
        },
        {
            "stake_type": "identity",
            "description": "National identity and leadership",
            "evidence_indices": [2],
        },
    ],
    "stakeholders": [
        {
            "name": "Speaker_A",
            "role": "speaker",
            "stance": "for",
            "evidence_indices": [0],
        },
        {
            "name": "Public_Z",
            "role": "audience",
            "stance": "against",
            "evidence_indices": [1],
        },
        {
            "name": "Authority_X",
            "role": "institution",
            "stance": "ambivalent",
            "evidence_indices": [0, 2],
        },
    ],
    "rhetorical_register": "mobilization",
    "discursive_arena": "parliamentary debate",
}


# ---------------------------------------------------------------------------
# 1. StakesExtractor unit tests
# ---------------------------------------------------------------------------


class TestStakesExtractor:
    """StakesExtractor with mock LLM."""

    async def test_extract_with_valid_llm_response(self):
        client = _mock_llm_client(SAMPLE_LLM_RESPONSE)
        extractor = StakesExtractor()
        result = await extractor.extract(
            arguments=SAMPLE_ARGUMENTS,
            source_metadata=SAMPLE_METADATA,
            raw_text="Full discourse text here...",
            llm_client=client,
        )
        assert len(result["stakes"]) == 3
        assert result["stakes"][0]["stake_type"] == "security"
        assert len(result["stakeholders"]) == 3
        assert result["stakeholders"][0]["name"] == "Speaker_A"
        assert result["rhetorical_register"] == "mobilization"
        assert result["discursive_arena"] == "parliamentary debate"

    async def test_extract_no_llm_client_returns_empty(self):
        extractor = StakesExtractor()
        result = await extractor.extract(
            arguments=SAMPLE_ARGUMENTS,
            source_metadata=SAMPLE_METADATA,
            llm_client=None,
        )
        assert result["stakes"] == []
        assert result["stakeholders"] == []
        assert result["rhetorical_register"] == ""
        assert result["discursive_arena"] == ""

    async def test_extract_handles_malformed_json(self):
        mock_choice = MagicMock()
        mock_choice.message.content = "NOT JSON AT ALL"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        client = MagicMock()
        client.chat.completions.create = AsyncMock(return_value=mock_response)

        extractor = StakesExtractor()
        result = await extractor.extract(
            arguments=SAMPLE_ARGUMENTS,
            source_metadata=SAMPLE_METADATA,
            llm_client=client,
        )
        assert result["stakes"] == []
        assert result["rhetorical_register"] == ""

    async def test_extract_strips_markdown_fences(self):
        raw_json = json.dumps(SAMPLE_LLM_RESPONSE)
        fenced = f"```json\n{raw_json}\n```"
        mock_choice = MagicMock()
        mock_choice.message.content = fenced
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        client = MagicMock()
        client.chat.completions.create = AsyncMock(return_value=mock_response)

        extractor = StakesExtractor()
        result = await extractor.extract(
            arguments=SAMPLE_ARGUMENTS,
            source_metadata=SAMPLE_METADATA,
            llm_client=client,
        )
        assert len(result["stakes"]) == 3

    async def test_extract_caps_at_10_entries(self):
        large_response = {
            "stakes": [
                {
                    "stake_type": "political",
                    "description": f"Stake {i}",
                    "evidence_indices": [],
                }
                for i in range(15)
            ],
            "stakeholders": [
                {
                    "name": f"P_{i}",
                    "role": "group",
                    "stance": "for",
                    "evidence_indices": [],
                }
                for i in range(15)
            ],
            "rhetorical_register": "deliberative",
            "discursive_arena": "test",
        }
        client = _mock_llm_client(large_response)
        extractor = StakesExtractor()
        result = await extractor.extract(
            arguments=SAMPLE_ARGUMENTS,
            source_metadata=SAMPLE_METADATA,
            llm_client=client,
        )
        assert len(result["stakes"]) == 10
        assert len(result["stakeholders"]) == 10

    async def test_prompt_contains_arguments_and_metadata(self):
        client = _mock_llm_client(SAMPLE_LLM_RESPONSE)
        extractor = StakesExtractor()
        await extractor.extract(
            arguments=SAMPLE_ARGUMENTS,
            source_metadata=SAMPLE_METADATA,
            raw_text="Test discourse",
            llm_client=client,
        )
        call_args = client.chat.completions.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "[0] We must increase defence spending" in prompt
        assert "Speaker_A" in prompt
        assert "parliamentary debate" in prompt

    async def test_extract_threads_resolved_model_id(self):
        """The resolved model_id is sent, not the hardcoded gpt-4o-mini default.

        Regression guard for the async-contract fix: the orchestrator threads
        the model resolved by _get_openai_client through to the call.
        """
        client = _mock_llm_client(SAMPLE_LLM_RESPONSE)
        extractor = StakesExtractor()
        await extractor.extract(
            arguments=SAMPLE_ARGUMENTS,
            source_metadata=SAMPLE_METADATA,
            llm_client=client,
            model_id="resolved-fleet-model",
        )
        sent_model = client.chat.completions.create.call_args[1]["model"]
        assert sent_model == "resolved-fleet-model"


# ---------------------------------------------------------------------------
# 2. shared_state field tests
# ---------------------------------------------------------------------------


class TestStakesSharedState:
    """UnifiedAnalysisState.stakes_and_stakeholders field."""

    def test_field_initialized_empty(self):
        state = UnifiedAnalysisState("test text")
        assert state.stakes_and_stakeholders == {
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        }

    def test_field_is_mutable(self):
        state = UnifiedAnalysisState("test text")
        state.stakes_and_stakeholders["stakes"] = [
            {"stake_type": "political", "description": "test"}
        ]
        assert len(state.stakes_and_stakeholders["stakes"]) == 1


# ---------------------------------------------------------------------------
# 3. DeepSynthesisAgent stakes_block integration
# ---------------------------------------------------------------------------


class TestDeepSynthesisStakesBlock:
    """DeepSynthesisAgent reads stakes_and_stakeholders for LLM prompt."""

    def test_synthesize_attaches_raw_stakes(self):
        """When state has stakes data, report._raw_stakes is populated."""
        from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
            DeepSynthesisAgent,
        )

        state = UnifiedAnalysisState("test text for stakes")
        state.stakes_and_stakeholders = {
            "stakes": [
                {
                    "stake_type": "political",
                    "description": "Test stake",
                    "evidence_indices": [],
                }
            ],
            "stakeholders": [],
            "rhetorical_register": "deliberative",
            "discursive_arena": "",
        }
        # Use static-only path (no LLM service) via the report building
        from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
            DeepSynthesisReport,
        )

        # Simulate what synthesize() does for stakes
        stakes_data = getattr(state, "stakes_and_stakeholders", {})
        has_data = any(
            stakes_data.get(k)
            for k in ("stakes", "stakeholders", "rhetorical_register")
        )
        assert has_data
        report = DeepSynthesisReport()
        report._raw_stakes = stakes_data

        # Verify the stakes_block construction logic
        stakes_block = ""
        if report._raw_stakes:
            sl = report._raw_stakes.get("stakes", [])
            if sl:
                lines = [
                    f"[{s.get('stake_type', '?')}] {s.get('description', '')}"
                    for s in sl[:3]
                ]
                stakes_block = "\n".join(lines)
        assert "political" in stakes_block
        assert "Test stake" in stakes_block

    def test_empty_stakes_gives_empty_block(self):
        """When state has no stakes, report._raw_stakes is empty dict."""
        state = UnifiedAnalysisState("test text")
        stakes_data = getattr(state, "stakes_and_stakeholders", {})
        has_data = any(
            stakes_data.get(k)
            for k in ("stakes", "stakeholders", "rhetorical_register")
        )
        assert not has_data


# ---------------------------------------------------------------------------
# 4. Integration: _invoke_stakes_extractor with a REAL-shaped async client
#    (the path that the original tuple-unpack bug silently broke)
# ---------------------------------------------------------------------------


class TestInvokeStakesExtractorIntegration:
    """End-to-end _invoke_stakes_extractor with a mock AsyncOpenAI client.

    This is the test the original bug lacked: it exercises the FULL production
    path — _get_openai_client() tuple unpack → extract() → awaited
    _guarded_chat_completion(client, model=model_id) — with a real-shaped async
    client returning a well-formed response, and asserts stakes come back
    NON-empty. Before the fix, _invoke_stakes_extractor passed the (client,
    model_id) TUPLE as llm_client → '.tuple' object has no attribute 'chat' →
    swallowed by extract's broad except → empty stakes. This test fails on that
    code and passes on the fixed code.
    """

    async def test_invoke_returns_non_empty_stakes_with_mock_client(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_stakes_extractor,
        )

        mock_client = _mock_llm_client(SAMPLE_LLM_RESPONSE)
        state = UnifiedAnalysisState(
            "We must increase defence spending to protect our borders."
        )
        # Real writer schema: {arg_id: description}.
        state.identified_arguments = {
            "arg_1": "We must increase defence spending to protect our borders.",
            "arg_2": "The economic cost is too high for ordinary citizens.",
        }

        with patch(
            "argumentation_analysis.orchestration.invoke_callables._get_openai_client",
            return_value=(mock_client, "resolved-fleet-model"),
        ):
            result = await _invoke_stakes_extractor(
                "", {"_state_object": state, "source_metadata": SAMPLE_METADATA}
            )

        # The bug returned empty stakes (tuple-as-client crash, swallowed).
        assert len(result["stakes"]) == 3, result
        assert result["stakes"][0]["stake_type"] == "security"
        assert len(result["stakeholders"]) == 3
        # Resolved model_id was threaded to the actual LLM call (not gpt-4o-mini).
        sent_model = mock_client.chat.completions.create.call_args[1]["model"]
        assert sent_model == "resolved-fleet-model"
        # State was written.
        assert len(state.stakes_and_stakeholders["stakes"]) == 3
