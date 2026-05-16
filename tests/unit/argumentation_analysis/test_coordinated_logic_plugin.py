"""Tests for CoordinatedLogicPlugin — 2-pass PL/FOL extraction via SK plugin.

Issues #560 (PL), #561 (FOL).
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def plugin():
    from argumentation_analysis.plugins.coordinated_logic_plugin import CoordinatedLogicPlugin
    return CoordinatedLogicPlugin()


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI response factory."""
    def _make(content):
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        return resp
    return _make


# ── Pass 1: PL atom extraction ──

class TestExtractSharedPLAtoms:

    @pytest.mark.asyncio
    async def test_extracts_valid_atoms(self, plugin, mock_openai_response):
        llm_output = json.dumps({"propositions": ["is_mortal", "foreign_threat", "has_power"]})
        long_text = "Socrates is mortal and Greece faces threats. " * 5  # >100 chars
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            client = AsyncMock()
            client.chat.completions.create = AsyncMock(return_value=mock_openai_response(llm_output))
            mock_client.return_value = (client, "gpt-test", "key")

            result = await plugin.extract_shared_pl_atoms(full_text=long_text)
            data = json.loads(result)

        assert data["shared_atoms"] == ["is_mortal", "foreign_threat", "has_power"]
        assert data["count"] == 3

    @pytest.mark.asyncio
    async def test_filters_invalid_atoms(self, plugin, mock_openai_response):
        llm_output = json.dumps({"propositions": ["valid_atom", "has space", "123start", "good_one"]})
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            client = AsyncMock()
            client.chat.completions.create = AsyncMock(return_value=mock_openai_response(llm_output))
            mock_client.return_value = (client, "gpt-test", "key")

            result = await plugin.extract_shared_pl_atoms(full_text="A" * 200)
            data = json.loads(result)

        assert "valid_atom" in data["shared_atoms"]
        assert "good_one" in data["shared_atoms"]
        assert "has space" not in data["shared_atoms"]
        assert "123start" not in data["shared_atoms"]

    @pytest.mark.asyncio
    async def test_returns_empty_for_short_text(self, plugin):
        result = await plugin.extract_shared_pl_atoms(full_text="short")
        data = json.loads(result)
        assert data["shared_atoms"] == []

    @pytest.mark.asyncio
    async def test_returns_error_when_no_api_key(self, plugin):
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client",
            return_value=(None, "", ""),
        ):
            result = await plugin.extract_shared_pl_atoms(full_text="A" * 200)
            data = json.loads(result)
        assert data["shared_atoms"] == []
        assert "error" in data


# ── Pass 1: FOL signature extraction ──

class TestExtractSharedFOLSignature:

    @pytest.mark.asyncio
    async def test_extracts_signature(self, plugin, mock_openai_response):
        llm_output = json.dumps({
            "sorts": {"Person": ["socrates", "plato"]},
            "predicates": {"Mortal": ["Person"]},
            "constants": {"socrates": "the philosopher"},
        })
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            client = AsyncMock()
            client.chat.completions.create = AsyncMock(return_value=mock_openai_response(llm_output))
            mock_client.return_value = (client, "gpt-test", "key")

            result = await plugin.extract_shared_fol_signature(full_text="A" * 200)
            data = json.loads(result)

        assert "Person" in data["sorts"]
        assert "Mortal" in data["predicates"]
        assert "socrates" in data["constants"]

    @pytest.mark.asyncio
    async def test_generates_thing_sort_when_only_constants(self, plugin, mock_openai_response):
        llm_output = json.dumps({
            "sorts": {},
            "predicates": {},
            "constants": {"a": "x", "b": "y"},
        })
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            client = AsyncMock()
            client.chat.completions.create = AsyncMock(return_value=mock_openai_response(llm_output))
            mock_client.return_value = (client, "gpt-test", "key")

            result = await plugin.extract_shared_fol_signature(full_text="A" * 200)
            data = json.loads(result)

        assert data["sorts"] == {"Thing": ["a", "b"]}


# ── Pass 2: PL formula generation ──

class TestGeneratePLFormulasWithSharedAtoms:

    @pytest.mark.asyncio
    async def test_generates_formulas(self, plugin, mock_openai_response):
        llm_output = json.dumps({"formulas": ["is_mortal => has_power", "foreign_threat && is_mortal"]})
        atoms_json = json.dumps(["is_mortal", "foreign_threat", "has_power"])

        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            client = AsyncMock()
            client.chat.completions.create = AsyncMock(return_value=mock_openai_response(llm_output))
            mock_client.return_value = (client, "gpt-test", "key")

            result = await plugin.generate_pl_formulas_with_shared_atoms(
                argument_text="Socrates is mortal and has power.",
                shared_atoms=atoms_json,
            )
            data = json.loads(result)

        assert len(data["formulas"]) == 2
        assert data["used_atoms"] == ["is_mortal", "foreign_threat", "has_power"]

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_atoms(self, plugin):
        result = await plugin.generate_pl_formulas_with_shared_atoms(
            argument_text="test", shared_atoms="[]"
        )
        data = json.loads(result)
        assert data["formulas"] == []


# ── Pass 2: FOL formula generation ──

class TestGenerateFOLFormulasWithSharedSignature:

    @pytest.mark.asyncio
    async def test_generates_fol_formulas(self, plugin, mock_openai_response):
        llm_output = json.dumps({"formulas": ["forall X: Person => Mortal(X)"]})
        sig_json = json.dumps({"sorts": {"Person": ["socrates"]}, "predicates": {"Mortal": ["Person"]}})

        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            client = AsyncMock()
            client.chat.completions.create = AsyncMock(return_value=mock_openai_response(llm_output))
            mock_client.return_value = (client, "gpt-test", "key")

            result = await plugin.generate_fol_formulas_with_shared_signature(
                argument_text="All persons are mortal.",
                shared_signature=sig_json,
            )
            data = json.loads(result)

        assert len(data["formulas"]) == 1
        assert "Mortal" in data["formulas"][0]

    @pytest.mark.asyncio
    async def test_handles_invalid_signature_json(self, plugin):
        result = await plugin.generate_fol_formulas_with_shared_signature(
            argument_text="test", shared_signature="not json{"
        )
        data = json.loads(result)
        assert data["formulas"] == []
        assert "error" in data


# ── Integration: FormalAgent instructions reference plugin ──

class TestFormalAgentInstructions:

    def test_instructions_reference_coordinated_logic_methods(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import AGENT_CONFIG

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "extract_shared_pl_atoms" in instructions
        assert "extract_shared_fol_signature" in instructions
        assert "generate_fol_formulas_with_shared_signature" in instructions
        assert "generate_pl_formulas_with_shared_atoms" in instructions

    def test_instructions_have_etape_0_building(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import AGENT_CONFIG

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        assert "ETAPE 0" in instructions
        assert "#560" in instructions or "#561" in instructions

    def test_factory_has_coordinated_logic_in_formal_speciality(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP, _PLUGIN_REGISTRY

        assert "coordinated_logic" in AGENT_SPECIALITY_MAP["formal_logic"]
        assert "coordinated_logic" in _PLUGIN_REGISTRY

    def test_plugin_registry_points_to_correct_module(self):
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        module_path, class_name = _PLUGIN_REGISTRY["coordinated_logic"]
        assert module_path == "argumentation_analysis.plugins.coordinated_logic_plugin"
        assert class_name == "CoordinatedLogicPlugin"
