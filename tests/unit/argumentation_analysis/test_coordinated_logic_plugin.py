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


# ── Pass 1: Modal signature extraction (#1396) ──

class TestExtractSharedModalSignature:

    @pytest.mark.asyncio
    async def test_extracts_modal_atoms_on_cued_text(self, plugin, mock_openai_response):
        """Modal atoms extracted when text carries FR modal cues (#1396)."""
        llm_output = json.dumps({
            "atoms": ["citizen", "ObeysLaw", "peace"],
            "modal_flavors": ["deontic"],
        })
        cued_text = (
            "Les citoyens doivent voter et il est obligatoire de respecter la loi. "
            "Ils peuvent manifester pacifiquement. " * 5  # >100 chars, modal cues
        )
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            client = AsyncMock()
            client.chat.completions.create = AsyncMock(return_value=mock_openai_response(llm_output))
            mock_client.return_value = (client, "gpt-test", "key")

            result = await plugin.extract_shared_modal_signature(full_text=cued_text)
            data = json.loads(result)

        assert data["atoms"] == ["citizen", "ObeysLaw", "peace"]
        assert data["modal_present"] is True
        assert data["count"] == 3

    @pytest.mark.asyncio
    async def test_filters_underscore_atoms(self, plugin, mock_openai_response):
        """Underscored atoms filtered out (MlParser rejects them, #1327)."""
        llm_output = json.dumps({"atoms": ["valid_atom", "bad_atom_name", "ok"]})
        cued_text = "Il faut agir et on doit respecter la loi. " * 5
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            client = AsyncMock()
            client.chat.completions.create = AsyncMock(return_value=mock_openai_response(llm_output))
            mock_client.return_value = (client, "gpt-test", "key")

            result = await plugin.extract_shared_modal_signature(full_text=cued_text)
            data = json.loads(result)

        # Underscores rejected by [A-Za-z][A-Za-z0-9]* -- only "ok" survives
        assert data["atoms"] == ["ok"]

    @pytest.mark.asyncio
    async def test_cue_gate_no_modal_cues_returns_empty_without_llm_call(self, plugin):
        """Anti-theater #1019 (#1396): non-modal text -> honest empty, NO LLM call."""
        non_modal_text = (
            "Socrates is a philosopher. Plato was his student. They discussed ideas "
            "about justice and the nature of knowledge in ancient Athens. " * 3  # >100 chars
        )
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client"
        ) as mock_client:
            result = await plugin.extract_shared_modal_signature(full_text=non_modal_text)
            data = json.loads(result)
            # The cue-gate must short-circuit BEFORE any LLM client is built.
            mock_client.assert_not_called()

        assert data["atoms"] == []
        assert data["modal_present"] is False

    @pytest.mark.asyncio
    async def test_returns_empty_for_short_text(self, plugin):
        result = await plugin.extract_shared_modal_signature(full_text="short")
        data = json.loads(result)
        assert data["atoms"] == []
        assert data["modal_present"] is False

    @pytest.mark.asyncio
    async def test_returns_error_when_no_api_key(self, plugin):
        # 'obligatoire' is an exact FR modal cue (substring 'doit' != 'doivent')
        cued_text = "Il est obligatoire de voter et de respecter la loi. " * 5
        with patch(
            "argumentation_analysis.plugins.coordinated_logic_plugin._get_openai_client",
            return_value=(None, "", ""),
        ):
            result = await plugin.extract_shared_modal_signature(full_text=cued_text)
            data = json.loads(result)
        assert data["atoms"] == []
        assert data["modal_present"] is False
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

    def test_instructions_reference_modal_lane(self):
        """#1396: modal co-equal lane wired into ETAPE 0 + ETAPE 1."""
        from argumentation_analysis.orchestration.conversational_orchestrator import AGENT_CONFIG

        instructions = AGENT_CONFIG["FormalAgent"]["instructions"]
        # Modal Pass-1 inventory in ETAPE 0 (cue-gated)
        assert "extract_shared_modal_signature" in instructions
        # Modal Pass-2 consumes the shared atoms for inter-arg coherence
        assert "shared_atoms" in instructions
        # ETAPE 1 RAISONNEMENT rebalanced: 3 logics co-equal, cue-keyed
        assert "co-egales" in instructions or "co-egales" in instructions.replace("é", "e")

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
