# Authentic gpt-5-mini imports (replacing mocks)
import openai
import json
import sys
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
import asyncio

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from semantic_kernel import Kernel
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from semantic_kernel.functions.function_result import FunctionResult
from semantic_kernel.functions import KernelFunctionMetadata
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet
from config.unified_config import (
    UnifiedConfig,
    LogicType,
    MockLevel,
    AgentType,
    PresetConfigs,
)
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer


# Classe concrète pour les tests
class ConcreteFOLLogicAgent(FOLLogicAgent):
    def validate_argument(self, premises: list[str], conclusion: str, **kwargs) -> bool:
        return True

    def _create_belief_set_from_data(
        self, belief_set_data: dict[str, any]
    ) -> "BeliefSet":
        bs = BeliefSet()
        if isinstance(belief_set_data, dict) and "content" in belief_set_data:
            content = belief_set_data["content"]
            if isinstance(content, list):
                for item in content:
                    bs.add_belief(str(item))
        return bs


class TestFOLLogicAgentInitialization:
    """Tests d'initialisation et de configuration de l'agent FOL."""

    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    @pytest.mark.real_jpype
    def test_agent_initialization_with_fol_config(self):
        """Test création agent avec configuration FOL."""
        config = PresetConfigs.authentic_fol()
        kernel = Kernel()
        # Ajouter un service LLM mock pour éviter KernelServiceNotFoundError
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        kernel.add_service(
            OpenAIChatCompletion(
                service_id="default",
                ai_model_id="gpt-4",
                api_key="test-key",  # Mock pour tests
            )
        )
        agent = ConcreteFOLLogicAgent(kernel=kernel, agent_name="TestFOLAgent")

        assert agent.name == "TestFOLAgent"
        assert agent.logic_type == "first_order"
        assert agent.conversion_prompt is not None
        assert agent.analysis_prompt is not None
        assert agent.analysis_cache == {}

    def test_unified_config_fol_mapping(self):
        """Test mapping depuis UnifiedConfig.logic_type='FOL'."""
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            agents=[AgentType.FOL_LOGIC],
            mock_level=MockLevel.NONE,
        )

        agent_classes = config.get_agent_classes()
        assert "fol_logic" in agent_classes
        assert agent_classes["fol_logic"] == "FOLLogicAgent"

        tweety_config = config.get_tweety_config()
        assert tweety_config["logic_type"] == "fol"
        assert tweety_config["require_real_jar"] is True

    def test_agent_parameters_configuration(self):
        """Test paramètres agent (expertise, style, contraintes)."""
        kernel = Kernel()
        kernel.add_service(
            OpenAIChatCompletion(
                service_id="default", ai_model_id="gpt-4", api_key="test-key"
            )
        )
        agent = ConcreteFOLLogicAgent(kernel=kernel)

        assert "forall" in agent.conversion_prompt
        assert "exists" in agent.conversion_prompt
        assert "=>" in agent.conversion_prompt
        assert "ANALYSE LE TEXTE SUIVANT" in agent.conversion_prompt

        assert "COHÉRENCE LOGIQUE" in agent.analysis_prompt
        assert "INFÉRENCES POSSIBLES" in agent.analysis_prompt
        assert "VALIDATION" in agent.analysis_prompt

    def test_fol_configuration_validation(self):
        """Test validation configuration FOL."""
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            agents=[AgentType.FOL_LOGIC],
            enable_jvm=True,
            mock_level=MockLevel.NONE,
        )

        assert config.logic_type == LogicType.FOL
        assert AgentType.FOL_LOGIC in config.agents

        with pytest.raises(
            ValueError, match="FOL_LOGIC agent nécessite enable_jvm=True"
        ):
            UnifiedConfig(
                logic_type=LogicType.FOL, agents=[AgentType.FOL_LOGIC], enable_jvm=False
            )


class TestFOLSyntaxGeneration:
    """Tests de génération de syntaxe FOL valide."""

    @pytest.fixture
    def fol_agent(self):
        """Agent FOL pour les tests."""
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        kernel = Kernel()
        # Ajouter un service LLM mock pour éviter KernelServiceNotFoundError
        kernel.add_service(
            OpenAIChatCompletion(
                service_id="default",
                ai_model_id="gpt-4",
                api_key="test-key",  # Mock pour tests
            )
        )
        return ConcreteFOLLogicAgent(kernel=kernel, agent_name="TestAgent")

    def test_quantifier_universal_generation(self, fol_agent):
        """Tests quantificateurs universels : forall X: (P(X) => Q(X))."""
        text = "Tous les hommes sont mortels."
        all_lines = fol_agent._basic_fol_conversion(text)

        # _basic_fol_conversion now returns declarations + formulas for Tweety
        formulas = [f for f in all_lines if f and not f.startswith("thing") and not f.startswith("type(")]
        assert len(formulas) == 1
        assert "forall" in formulas[0]
        assert "=>" in formulas[0]

    def test_quantifier_existential_generation(self, fol_agent):
        """Tests quantificateurs existentiels : exists X: (P(X) && Q(X))."""
        text = "Il existe des étudiants intelligents."
        all_lines = fol_agent._basic_fol_conversion(text)

        formulas = [f for f in all_lines if f and not f.startswith("thing") and not f.startswith("type(")]
        assert len(formulas) == 1
        assert "exists" in formulas[0]
        assert "&&" in formulas[0]

    def test_complex_predicate_generation(self, fol_agent):
        """Tests prédicats complexes multi-sentences."""
        text = "Tous les étudiants aiment leurs professeurs. Tous les professeurs respectent leurs étudiants."
        all_lines = fol_agent._basic_fol_conversion(text)

        formulas = [f for f in all_lines if f and not f.startswith("thing") and not f.startswith("type(")]
        assert len(formulas) == 2
        for formula in formulas:
            assert "forall" in formula or "exists" in formula or "P" in formula

    def test_logical_connectors_validation(self, fol_agent):
        """Tests connecteurs logiques ASCII pour Tweety : &&, ||, =>, !, <=>."""
        prompt = fol_agent.conversion_prompt

        assert "&& (et)" in prompt
        assert "|| (ou)" in prompt
        assert "=> (implique)" in prompt
        assert "! (non)" in prompt
        assert "<=> (équivalent)" in prompt

        text = "Si il pleut alors le sol est mouillé."
        all_lines = fol_agent._basic_fol_conversion(text)

        formulas = [f for f in all_lines if f and not f.startswith("thing") and not f.startswith("type(")]
        assert len(formulas) == 1
        assert "=>" in formulas[0]

    def test_fol_syntax_validation_rules(self, fol_agent):
        """Test validation des règles de syntaxe FOL Tweety."""
        prompt = fol_agent.conversion_prompt

        assert "Homme(X)" in prompt or "Homme(x)" in prompt
        assert "forall" in prompt
        assert "EXEMPLE" in prompt
        assert "Mortel" in prompt


class TestFOLTweetyIntegration:
    """Tests d'intégration avec TweetyProject."""

    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = UnifiedConfig()
        config.mock_level = MockLevel.NONE
        config.use_authentic_llm = True
        config.use_mock_llm = False
        try:
            return config.get_kernel_with_gpt4o_mini()
        except Exception as e:
            print(
                f"Avertissement: Erreur lors de l'appel à config.get_kernel_with_gpt4o_mini(): {e}"
            )
            return Kernel()

    @pytest_asyncio.fixture
    async def fol_agent_with_tweety(self):
        """Agent FOL avec TweetyBridge mocké."""
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        kernel = Kernel()
        # Ajouter un service LLM mock pour éviter KernelServiceNotFoundError
        kernel.add_service(
            OpenAIChatCompletion(
                service_id="default",
                ai_model_id="gpt-4",
                api_key="test-key",  # Mock pour tests
            )
        )

        # Récupérer le service ajouté pour le passer à l'agent
        llm_service = kernel.get_service("default")
        agent = ConcreteFOLLogicAgent(
            kernel=kernel,
            agent_name="TestFOLAgent",
            service_id=llm_service,  # CORRECT: service_id au lieu de service
        )

        agent._tweety_bridge = AsyncMock()
        agent._tweety_bridge.check_consistency = AsyncMock(return_value=True)
        agent._tweety_bridge.derive_inferences = AsyncMock(
            return_value=["Inférence test"]
        )
        agent._tweety_bridge.generate_models = AsyncMock(
            return_value=[{"description": "Modèle test", "model": {}}]
        )

        return agent

    @pytest.mark.asyncio
    async def test_tweety_integration_fol(self, fol_agent_with_tweety):
        """Test compatibilité syntaxe avec solveur Tweety."""
        formulas = ["∀x(Human(x) → Mortal(x))", "Human(socrate)"]

        result = await fol_agent_with_tweety._analyze_with_tweety(formulas)

        assert result.formulas == formulas
        assert result.consistency_check is True
        assert len(result.inferences) == 1
        assert result.inferences[0] == "Inférence test"
        assert len(result.interpretations) == 1
        assert result.confidence_score == 0.9

    @pytest.mark.asyncio
    async def test_tweety_validation_formulas(self, fol_agent_with_tweety):
        """Test validation formules avant envoi à Tweety."""
        valid_formulas = ["∀x(P(x) → Q(x))", "∃y(R(y) ∧ S(y))"]

        result = await fol_agent_with_tweety._analyze_with_tweety(valid_formulas)

        fol_agent_with_tweety._tweety_bridge.check_consistency.assert_called_once_with(
            "∀x(P(x) → Q(x))\n∃y(R(y) ∧ S(y))", "first_order"
        )
        fol_agent_with_tweety._tweety_bridge.derive_inferences.assert_called_once_with(
            valid_formulas
        )
        fol_agent_with_tweety._tweety_bridge.generate_models.assert_called_once_with(
            valid_formulas
        )

    @pytest.mark.asyncio
    async def test_tweety_error_handling_fol(self, fol_agent_with_tweety):
        """Test gestion erreurs Tweety spécifiques FOL."""
        fol_agent_with_tweety._tweety_bridge.check_consistency.side_effect = Exception(
            "Erreur Tweety test"
        )

        formulas = ["∀x(P(x) → Q(x))"]
        result = await fol_agent_with_tweety._analyze_with_tweety(formulas)

        assert len(result.validation_errors) > 0
        assert "Erreur Tweety: Erreur Tweety test" in result.validation_errors
        assert result.confidence_score == 0.1

    @pytest.mark.asyncio
    async def test_tweety_results_analysis_fol(self, fol_agent_with_tweety):
        """Test analyse résultats Tweety FOL."""
        fol_agent_with_tweety._tweety_bridge.derive_inferences = AsyncMock(
            return_value=["Mortal(socrate)", "∀x(Wise(x) → Human(x))"]
        )
        fol_agent_with_tweety._tweety_bridge.generate_models = AsyncMock(
            return_value=[
                {"description": "Modèle 1", "model": {"socrate": True}},
                {"description": "Modèle 2", "model": {"platon": True}},
            ]
        )

        formulas = ["∀x(Human(x) → Mortal(x))", "Human(socrate)"]
        result = await fol_agent_with_tweety._analyze_with_tweety(formulas)

        assert len(result.inferences) == 2
        assert "Mortal(socrate)" in result.inferences
        assert len(result.interpretations) == 2
        assert result.interpretations[0]["description"] == "Modèle 1"


class TestFOLAnalysisPipeline:
    """Tests du pipeline d'analyse FOL."""

    @pytest_asyncio.fixture
    async def fol_agent_full(self):
        """Agent FOL avec tous les composants mockés."""
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        kernel = Kernel()
        kernel.add_service(
            OpenAIChatCompletion(
                service_id="default", ai_model_id="gpt-4", api_key="test-key"
            )
        )

        agent = ConcreteFOLLogicAgent(
            kernel=kernel,
            agent_name="TestFOLAgent",
        )

        # Pre-install mock invoke on kernel (bypass Pydantic V2 __setattr__)
        object.__setattr__(kernel, "invoke", AsyncMock())

        agent._tweety_bridge = AsyncMock()
        agent._tweety_bridge.check_consistency = AsyncMock(return_value=True)
        agent._tweety_bridge.derive_inferences = AsyncMock(
            return_value=["Inférence LLM"]
        )
        agent._tweety_bridge.generate_models = AsyncMock(
            return_value=[{"description": "Modèle LLM", "model": {}}]
        )

        return agent

    @pytest.mark.asyncio
    async def test_sophism_analysis_with_fol(self, fol_agent_full):
        """Test analyse de sophismes avec logique FOL."""
        mock_metadata = KernelFunctionMetadata(
            name="mock", plugin_name="mock", description="mock", is_prompt=True
        )

        fol_agent_full.kernel.invoke.side_effect = [
            FunctionResult(
                function=mock_metadata,
                value=json.dumps(
                    {
                        "formulas": ["∀x(Human(x) → Mortal(x))", "Human(socrate)"],
                        "predicates": {
                            "Human": "être humain",
                            "Mortal": "être mortel",
                        },
                        "variables": {"x": "individu", "socrate": "constante"},
                        "reasoning": "Syllogisme classique",
                    }
                ),
            ),
            FunctionResult(
                function=mock_metadata,
                value=json.dumps(
                    {
                        "consistency": True,
                        "inferences": ["Mortal(socrate)"],
                        "interpretations": [
                            {
                                "description": "Modèle valide",
                                "model": {"socrate": "mortal"},
                            }
                        ],
                        "errors": [],
                        "confidence": 0.95,
                        "reasoning_steps": ["Analyse syllogisme", "Validation FOL"],
                    }
                ),
            ),
        ]

        sophism_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
        result = await fol_agent_full.analyze(sophism_text)

        assert len(result.formulas) == 2
        assert "forall x(Human(x) => Mortal(x))" in result.formulas or "∀x(Human(x) → Mortal(x))" in result.formulas
        assert "Human(socrate)" in result.formulas
        assert result.consistency_check is True
        assert "Mortal(socrate)" in result.inferences
        assert result.confidence_score >= 0.9

    @pytest.mark.asyncio
    async def test_fol_report_generation(self, fol_agent_full):
        """Test génération rapport avec formules FOL."""
        mock_metadata = KernelFunctionMetadata(
            name="mock", plugin_name="mock", description="mock", is_prompt=True
        )
        fol_agent_full.kernel.invoke.return_value = FunctionResult(
            function=mock_metadata,
            value=json.dumps(
                {
                    "formulas": ["∀x(P(x) → Q(x))"],
                    "predicates": {"P": "propriété P", "Q": "propriété Q"},
                    "reasoning": "Implication universelle",
                }
            ),
        )

        text = "Tous les P sont Q."
        result = await fol_agent_full.analyze(text)

        assert len(result.reasoning_steps) > 0
        assert any("FOL" in step for step in result.reasoning_steps)

    @pytest.mark.asyncio
    async def test_tweety_error_analyzer_integration(self, fol_agent_full):
        """Test intégration avec TweetyErrorAnalyzer."""
        mock_meta = KernelFunctionMetadata(
            name="m", plugin_name="mp", description="d", is_prompt=True
        )

        conversion_response = FunctionResult(
            function=mock_meta,
            value=json.dumps(
                {
                    "formulas": ["ValidFormulaForTweety(x)"],
                    "reasoning": "mocked conversion",
                }
            ),
        )
        llm_analysis_response = FunctionResult(
            function=mock_meta,
            value=json.dumps({"consistency": True, "inferences": [], "errors": []}),
        )
        fol_agent_full.kernel.invoke.side_effect = [
            conversion_response,
            llm_analysis_response,
        ]

        fol_agent_full._tweety_bridge.check_consistency.side_effect = Exception(
            "Predicate 'Unknown' has not been declared"
        )

        text = "Le prédicat inconnu cause une erreur."
        result = await fol_agent_full.analyze(text)

        assert len(result.validation_errors) > 0
        error_msg = result.validation_errors[0]
        assert "Erreur Tweety: Predicate 'Unknown' has not been declared" in error_msg

    @pytest.mark.asyncio
    async def test_performance_analysis(self, fol_agent_full):
        """Test performance agent FOL."""
        import time

        mock_metadata = KernelFunctionMetadata(
            name="mock", plugin_name="mock", description="mock", is_prompt=True
        )
        fol_agent_full.kernel.invoke.return_value = FunctionResult(
            function=mock_metadata,
            value=json.dumps(
                {"formulas": ["∀x(Fast(x))"], "reasoning": "Test performance"}
            ),
        )

        start_time = time.time()
        result = await fol_agent_full.analyze("Test de performance FOL.")
        end_time = time.time()

        execution_time = end_time - start_time
        assert execution_time < 5.0
        assert result.confidence_score > 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
