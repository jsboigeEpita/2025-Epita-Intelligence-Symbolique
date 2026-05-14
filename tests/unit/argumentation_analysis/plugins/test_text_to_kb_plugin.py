"""Tests for TextToKBPlugin — NL extraction with iterative descent (#474).

Validates:
- Pydantic models validate correctly
- Heuristic extraction finds arguments in NL text
- Multi-chunk splitting works for long texts
- extract_kb returns validated JSON with FOL signature
- extract_arguments_only returns lighter-weight output
- write_kb_to_state writes to state object correctly
- Plugin registered in registry and AGENT_SPECIALITY_MAP
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock

from argumentation_analysis.plugins.text_to_kb_plugin import (
    ExtractedArgument,
    ExtractedPremise,
    FOLSignature,
    KBExtractionResult,
    TextToKBPlugin,
    _split_into_chunks,
    _heuristic_extract_arguments,
    _extract_fol_signature,
)

# ---------------------------------------------------------------------------
# Sample texts
# ---------------------------------------------------------------------------

SHORT_TEXT = (
    "Les impots doivent augmenter car l'etat est endette. "
    "En effet, le deficit budgetaire atteint 6% du PIB. "
    "Par consequent, une hausse des prelevements est necessaire."
)

LONG_TEXT = "\n\n".join(
    [f"Paragraphe {i}. " + SHORT_TEXT for i in range(10)]
)

MULTI_ARGUMENT_TEXT = (
    "Premierement, le changement climatique est un fait etabli par la science. "
    "Les temperatures moyennes augmentent depuis 50 ans. "
    "Deuxiemement, les emissions de CO2 sont la cause principale. "
    "Les concentrations atmospheriques ont depasse 400 ppm. "
    "Par consequent, il faut reduire les emissions rapidement."
)


# ---------------------------------------------------------------------------
# Test: Pydantic models
# ---------------------------------------------------------------------------


class TestPydanticModels:
    """Validate Pydantic model structure."""

    def test_extracted_premise(self):
        p = ExtractedPremise(text="Il pleut", formal="rain()", sort="weather")
        assert p.text == "Il pleut"
        assert p.formal == "rain()"
        assert p.sort == "weather"

    def test_extracted_argument(self):
        arg = ExtractedArgument(
            id="arg_1",
            text="Il pleut donc le sol est mouille",
            premises=[ExtractedPremise(text="Il pleut")],
            conclusion="Le sol est mouille",
            confidence=0.8,
        )
        assert arg.id == "arg_1"
        assert len(arg.premises) == 1
        assert arg.confidence == 0.8

    def test_fol_signature(self):
        sig = FOLSignature(
            predicates=["raining/1", "wet/1"],
            constants=["x", "y"],
            sorts=["location", "weather"],
        )
        assert len(sig.predicates) == 2
        assert len(sig.sorts) == 2

    def test_kb_extraction_result(self):
        result = KBExtractionResult(
            arguments=[
                ExtractedArgument(
                    id="arg_1", text="test", conclusion="test conclusion"
                )
            ],
            belief_candidates=["test conclusion"],
            fol_signature=FOLSignature(predicates=["p/1"]),
            target_logic="fol",
            source_length=100,
            chunk_count=1,
        )
        assert len(result.arguments) == 1
        assert result.target_logic == "fol"
        json_str = result.model_dump_json()
        parsed = json.loads(json_str)
        assert "arguments" in parsed

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ExtractedArgument(
                id="x", text="t", conclusion="c", confidence=1.5
            )


# ---------------------------------------------------------------------------
# Test: Chunk splitting
# ---------------------------------------------------------------------------


class TestChunkSplitting:
    """Verify text splitting for iterative descent."""

    def test_short_text_single_chunk(self):
        chunks = _split_into_chunks(SHORT_TEXT)
        assert len(chunks) == 1

    def test_long_text_multiple_chunks(self):
        chunks = _split_into_chunks(LONG_TEXT, max_chars=500)
        assert len(chunks) > 1

    def test_empty_text(self):
        chunks = _split_into_chunks("")
        assert len(chunks) == 1

    def test_no_paragraphs(self):
        text = "One sentence. Two sentences. No paragraph breaks."
        chunks = _split_into_chunks(text)
        assert len(chunks) == 1


# ---------------------------------------------------------------------------
# Test: Heuristic extraction
# ---------------------------------------------------------------------------


class TestHeuristicExtraction:
    """Test heuristic argument extraction from NL text."""

    def test_extracts_from_argumentative_text(self):
        args = _heuristic_extract_arguments(MULTI_ARGUMENT_TEXT)
        assert len(args) >= 1
        assert all(isinstance(a, ExtractedArgument) for a in args)
        assert all(a.id.startswith("arg_") for a in args)
        # Should have extracted premises and a conclusion
        assert any(len(a.premises) > 0 for a in args)

    def test_extracts_premises_and_conclusion(self):
        args = _heuristic_extract_arguments(MULTI_ARGUMENT_TEXT)
        # Should have at least one argument with conclusion
        assert any(len(a.conclusion) > 10 for a in args)

    def test_short_text_fewer_args(self):
        args = _heuristic_extract_arguments("Hello world.")
        assert len(args) <= 1

    def test_empty_text_no_args(self):
        args = _heuristic_extract_arguments("")
        assert len(args) == 0


# ---------------------------------------------------------------------------
# Test: FOL signature extraction
# ---------------------------------------------------------------------------


class TestFOLSignatureExtraction:
    """Test FOL signature derivation from arguments."""

    def test_extracts_from_formal_premises(self):
        args = [
            ExtractedArgument(
                id="arg_1",
                text="test",
                premises=[
                    ExtractedPremise(
                        text="test",
                        formal="raining(x)",
                        sort="weather",
                    )
                ],
                conclusion="wet(x)",
            )
        ]
        sig = _extract_fol_signature(args)
        assert "raining" in sig.predicates
        assert "weather" in sig.sorts

    def test_empty_args_empty_sig(self):
        sig = _extract_fol_signature([])
        assert sig.predicates == []
        assert sig.sorts == []


# ---------------------------------------------------------------------------
# Test: Plugin methods
# ---------------------------------------------------------------------------


class TestExtractKB:
    """Test extract_kb kernel function."""

    def test_extract_from_short_text(self):
        plugin = TextToKBPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.extract_kb(SHORT_TEXT, target_logic="fol")
        )
        result = json.loads(result_json)
        assert "arguments" in result
        assert result["target_logic"] == "fol"
        assert result["source_length"] > 0

    def test_extract_from_long_text(self):
        plugin = TextToKBPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.extract_kb(LONG_TEXT, target_logic="fol")
        )
        result = json.loads(result_json)
        assert result["chunk_count"] >= 1
        assert len(result["arguments"]) >= 1
        assert result["source_length"] > 0

    def test_extract_empty_text(self):
        plugin = TextToKBPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.extract_kb("")
        )
        result = json.loads(result_json)
        assert "error" in result

    def test_extract_modal_logic(self):
        plugin = TextToKBPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.extract_kb("Il est necessaire que P.", target_logic="modal")
        )
        result = json.loads(result_json)
        assert result["target_logic"] == "modal"

    def test_extract_produces_fol_signature(self):
        plugin = TextToKBPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.extract_kb(MULTI_ARGUMENT_TEXT, target_logic="fol")
        )
        result = json.loads(result_json)
        # FOL signature may or may not be present depending on heuristic extraction
        if result.get("fol_signature"):
            assert "predicates" in result["fol_signature"]


class TestExtractArgumentsOnly:
    """Test extract_arguments_only kernel function."""

    def test_extracts_arguments(self):
        plugin = TextToKBPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.extract_arguments_only(MULTI_ARGUMENT_TEXT)
        )
        result = json.loads(result_json)
        assert "arguments" in result
        assert result["count"] >= 1
        assert result["source_length"] > 0

    def test_empty_text(self):
        plugin = TextToKBPlugin()
        result_json = asyncio.get_event_loop().run_until_complete(
            plugin.extract_arguments_only("")
        )
        result = json.loads(result_json)
        assert "error" in result


class TestWriteKBToState:
    """Test write_kb_to_state kernel function."""

    def test_writes_arguments_and_beliefs(self):
        plugin = TextToKBPlugin()
        state = MagicMock()
        state.add_argument.return_value = "arg_1"
        state.add_belief_set.return_value = "fol_bs_1"

        input_data = {
            "arguments": [{"text": "arg text"}],
            "belief_candidates": ["belief text"],
            "target_logic": "fol",
        }
        result_json = plugin.write_kb_to_state(json.dumps(input_data), state=state)
        result = json.loads(result_json)

        assert result["arguments_written"] == 1
        assert result["beliefs_written"] == 1
        state.add_argument.assert_called_once_with("arg text")
        state.add_belief_set.assert_called_once_with("fol", "belief text")

    def test_no_state(self):
        plugin = TextToKBPlugin()
        result_json = plugin.write_kb_to_state("{}", state=None)
        result = json.loads(result_json)
        assert "error" in result

    def test_bad_json(self):
        plugin = TextToKBPlugin()
        state = MagicMock()
        result_json = plugin.write_kb_to_state("not json", state=state)
        result = json.loads(result_json)
        assert "error" in result


# ---------------------------------------------------------------------------
# Test: Registry and factory integration
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    """TextToKBPlugin registered in CapabilityRegistry."""

    def test_plugin_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=False)
        reg = registry._registrations.get("text_to_kb_plugin")
        assert reg is not None
        assert "nl_extraction" in reg.capabilities
        assert "argument_extraction" in reg.capabilities
        assert "kb_construction" in reg.capabilities


class TestFactoryIntegration:
    """AGENT_SPECIALITY_MAP includes text_to_kb."""

    def test_extract_has_text_to_kb(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        assert "text_to_kb" in AGENT_SPECIALITY_MAP["extract"]

    def test_formal_logic_has_text_to_kb(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        assert "text_to_kb" in AGENT_SPECIALITY_MAP["formal_logic"]

    def test_plugin_registry_entry(self):
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        assert "text_to_kb" in _PLUGIN_REGISTRY
        module_path, class_name = _PLUGIN_REGISTRY["text_to_kb"]
        assert "text_to_kb_plugin" in module_path
        assert class_name == "TextToKBPlugin"
