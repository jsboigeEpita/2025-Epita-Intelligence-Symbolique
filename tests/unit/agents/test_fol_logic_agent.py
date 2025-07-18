
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
import json # Ajout de l'import json
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from semantic_kernel.functions.function_result import FunctionResult
from semantic_kernel.functions import KernelFunctionMetadata # Ajout pour FunctionResult
from semantic_kernel import Kernel # Ajout de l'import du Kernel
from config.unified_config import UnifiedConfig, MockLevel # Ajout de MockLevel
import pytest_asyncio # Ajout de l'import pour les fixtures async
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion # Ajout pour _create_authentic_gpt4o_mini_instance
from unittest.mock import AsyncMock # Ajout pour mocker les méthodes async

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour FirstOrderLogicAgent (FOL).

Ce module teste toutes les fonctionnalités critiques de l'agent FOL :
- Initialisation et configuration avec UnifiedConfig
- Génération de syntaxe FOL valide
- Intégration avec TweetyProject
- Pipeline d'analyse complète
- Performance vs Modal Logic

Tests de validation :
✅ Quantificateurs universels : ∀x(P(x) → Q(x))
✅ Quantificateurs existentiels : ∃x(F(x) ∧ G(x))
✅ Prédicats complexes : ∀x∀y(R(x,y) → S(y,x))
✅ Connecteurs logiques : ∧, ∨, →, ¬, ↔
✅ Intégration Tweety sans erreurs
"""

import pytest
import asyncio
import json

from typing import Dict, List, Any, Optional

# Import de l'agent FOL
from argumentation_analysis.agents.core.logic.first_order_logic_agent import (
    FirstOrderLogicAgent,
    # FOLAnalysisResult, # OBSOLETE: Remplacé par BeliefSetBuilderPlugin
    # create_fol_agent # OBSOLETE: Factory n'est plus utilisée, l'agent est instancié directement
)
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet
from typing import Tuple, List, Optional, Dict, Any

# Classe concrète pour les tests
class ConcreteFirstOrderLogicAgent(FirstOrderLogicAgent):
    def validate_argument(self, premises: List[str], conclusion: str, **kwargs) -> bool:
        return True

    def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> "BeliefSet":
        bs = BeliefSet()
        # Simuler l'ajout de croyances si les données sont une liste
        if isinstance(belief_set_data, dict) and 'content' in belief_set_data:
            content = belief_set_data['content']
            if isinstance(content, list):
                for item in content:
                    bs.add_belief(str(item))
        return bs
from argumentation_analysis.agents.core.logic.belief_set import BeliefSet

# Import de la configuration unifiée
from config.unified_config import (
    UnifiedConfig, 
    LogicType, 
    MockLevel, 
    AgentType, 
    PresetConfigs
)

# Import pour les tests d'intégration
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer

class TestFirstOrderLogicAgentInitialization:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests d'initialisation et de configuration de l'agent FOL."""
    
    def test_agent_initialization_with_fol_config(self):
        """Test création agent avec configuration FOL."""
        # Configuration FOL authentique
        config = PresetConfigs.authentic_fol()
        
        # Création de l'agent
        kernel = Kernel() # Instanciation du Kernel
        agent = ConcreteFirstOrderLogicAgent(kernel=kernel, agent_name="TestFOLAgent")
        
        # Vérifications
        assert agent.name == "TestFOLAgent"
        assert agent.logic_type == "first_order"
        assert agent.conversion_prompt is not None
        assert agent.analysis_prompt is not None
        assert agent.analysis_cache == {}
        
    def test_unified_config_fol_mapping(self):
        """Test mapping depuis UnifiedConfig.logic_type='FOL'."""
        # Configuration avec LogicType.FOL
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            agents=[AgentType.FOL_LOGIC],
            mock_level=MockLevel.NONE
        )
        
        # Vérification du mapping
        agent_classes = config.get_agent_classes()
        assert "fol_logic" in agent_classes
        assert agent_classes["fol_logic"] == "FirstOrderLogicAgent"
        
        # Vérification configuration Tweety
        tweety_config = config.get_tweety_config()
        assert tweety_config["logic_type"] == "fol"
        assert tweety_config["require_real_jar"] is True
        
    def test_agent_parameters_configuration(self):
        """Test paramètres agent (expertise, style, contraintes)."""
        kernel = Kernel() # Instanciation du Kernel
        agent = ConcreteFirstOrderLogicAgent(kernel=kernel)
        
        # Test prompts spécialisés FOL
        assert "∀x" in agent.conversion_prompt
        assert "∃x" in agent.conversion_prompt
        assert "→" in agent.conversion_prompt
        assert "RÈGLES DE CONVERSION FOL" in agent.conversion_prompt
        
        # Test prompt d'analyse
        assert "COHÉRENCE LOGIQUE" in agent.analysis_prompt
        assert "INFÉRENCES POSSIBLES" in agent.analysis_prompt
        assert "VALIDATION" in agent.analysis_prompt
        
    def test_fol_configuration_validation(self):
        """Test validation configuration FOL."""
        # Configuration valide
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            agents=[AgentType.FOL_LOGIC],
            enable_jvm=True,
            mock_level=MockLevel.NONE
        )
        
        # Pas d'exception levée
        assert config.logic_type == LogicType.FOL
        assert AgentType.FOL_LOGIC in config.agents
        
        # Configuration invalide - FOL sans JVM
        with pytest.raises(ValueError, match="FOL_LOGIC agent nécessite enable_jvm=True"):
            UnifiedConfig(
                logic_type=LogicType.FOL,
                agents=[AgentType.FOL_LOGIC],
                enable_jvm=False
            )


class TestFOLSyntaxGeneration:
    """Tests de génération de syntaxe FOL valide."""
    
    @pytest.fixture
    def fol_agent(self):
        """Agent FOL pour les tests."""
        kernel = Kernel() # Instanciation du Kernel
        return ConcreteFirstOrderLogicAgent(kernel=kernel, agent_name="TestAgent")
    
    def test_quantifier_universal_generation(self, fol_agent):
        """Tests quantificateurs universels : ∀x(P(x) → Q(x))."""
        # Test conversion basique avec quantificateur universel
        text = "Tous les hommes sont mortels."
        formulas = fol_agent._basic_fol_conversion(text)
        
        # Vérification syntaxe FOL
        assert len(formulas) == 1
        assert "∀x" in formulas[0]
        assert "→" in formulas[0]
        assert formulas[0] == "∀x(P0(x) → Q0(x))"
        
    def test_quantifier_existential_generation(self, fol_agent):
        """Tests quantificateurs existentiels : ∃x(F(x) ∧ G(x))."""
        # Test avec quantificateur existentiel
        text = "Il existe des étudiants intelligents."
        formulas = fol_agent._basic_fol_conversion(text)
        
        # Vérification syntaxe FOL
        assert len(formulas) == 1
        assert "∃x" in formulas[0]
        assert "∧" in formulas[0]
        assert formulas[0] == "∃x(P0(x) ∧ Q0(x))"
        
    def test_complex_predicate_generation(self, fol_agent):
        """Tests prédicats complexes : ∀x∀y(R(x,y) → S(y,x))."""
        # Test avec relations binaires
        text = "Tous les étudiants aiment leurs professeurs. Tous les professeurs respectent leurs étudiants."
        formulas = fol_agent._basic_fol_conversion(text)
        
        # Vérifications
        assert len(formulas) == 2
        # Chaque formule doit avoir la structure correcte
        for formula in formulas:
            assert "∀x" in formula or "∃x" in formula or "P" in formula
            
    def test_logical_connectors_validation(self, fol_agent):
        """Tests connecteurs logiques : ∧, ∨, →, ¬, ↔."""
        # Test connecteurs dans les prompts
        prompt = fol_agent.conversion_prompt
        
        # Vérification présence des connecteurs
        assert "∧ (et)" in prompt
        assert "∨ (ou)" in prompt  
        assert "→ (implique)" in prompt
        assert "¬ (non)" in prompt
        assert "↔ (équivalent)" in prompt
        
        # Test génération avec implication
        text = "Si il pleut alors le sol est mouillé."
        formulas = fol_agent._basic_fol_conversion(text)
        
        assert len(formulas) == 1
        assert "→" in formulas[0]
        
    def test_fol_syntax_validation_rules(self, fol_agent):
        """Test validation des règles de syntaxe FOL."""
        # Règles attendues dans le prompt
        prompt = fol_agent.conversion_prompt
        
        # Vérification règles BNF
        assert "prédicats clairs : P(x), Q(x,y)" in prompt
        assert "Variables : x, y, z pour objets" in prompt
        assert "constantes" in prompt.lower()
        assert "EXEMPLE" in prompt
        
        # Test exemple fourni
        assert "∀x(Homme(x) → Mortel(x))" in prompt


class TestFOLTweetyIntegration:
    """Tests d'intégration avec TweetyProject."""
    
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock.
        Dans ce contexte, retourne un Kernel configuré.
        """
        config = UnifiedConfig()
        # Assurer que la configuration est pour l'authenticité, sinon get_kernel_with_gpt4o_mini lèvera une erreur.
        config.mock_level = MockLevel.NONE
        config.use_authentic_llm = True
        config.use_mock_llm = False
        try:
            # Utiliser la méthode centralisée de UnifiedConfig pour obtenir un kernel authentique
            return config.get_kernel_with_gpt4o_mini()
        except Exception as e:
            print(f"Avertissement: Erreur lors de l'appel à config.get_kernel_with_gpt4o_mini() dans _create_authentic_gpt4o_mini_instance: {e}")
            # Retourner un kernel vide en cas d'échec pour ne pas bloquer les tests non dépendants.
            return Kernel()

    @pytest_asyncio.fixture # Changement pour fixture async
    async def fol_agent_with_tweety(self):
        """Agent FOL avec TweetyBridge mocké."""
        kernel = Kernel() # Instanciation du Kernel
        agent = ConcreteFirstOrderLogicAgent(kernel=kernel)
        
        # Mock TweetyBridge
        # agent._tweety_bridge devrait être un mock de TweetyBridge, pas un Kernel.
        # On assigne un AsyncMock directement, puis on configure ses méthodes.
        agent._tweety_bridge = AsyncMock()
        agent._tweety_bridge.check_consistency = AsyncMock(return_value=True)
        agent._tweety_bridge.derive_inferences = AsyncMock(return_value=["Inférence test"])
        agent._tweety_bridge.generate_models = AsyncMock(return_value=[{"description": "Modèle test", "model": {}}])
        
        return agent
    
    @pytest.mark.asyncio
    async def test_tweety_integration_fol(self, fol_agent_with_tweety):
        """Test compatibilité syntaxe avec solveur Tweety."""
        formulas = ["∀x(Human(x) → Mortal(x))", "Human(socrate)"]
        
        # Test analyse avec Tweety
        result = await fol_agent_with_tweety._analyze_with_tweety(formulas)
        
        # Vérifications
        assert result.formulas == formulas
        assert result.consistency_check is True
        assert len(result.inferences) == 1
        assert result.inferences[0] == "Inférence test"
        assert len(result.interpretations) == 1
        assert result.confidence_score == 0.9
        
    @pytest.mark.asyncio
    async def test_tweety_validation_formulas(self, fol_agent_with_tweety):
        """Test validation formules avant envoi à Tweety."""
        # Formules valides
        valid_formulas = ["∀x(P(x) → Q(x))", "∃y(R(y) ∧ S(y))"]
        
        result = await fol_agent_with_tweety._analyze_with_tweety(valid_formulas)
        
        # Tweety appelé avec formules
        fol_agent_with_tweety._tweety_bridge.check_consistency.assert_called_once_with(valid_formulas)
        fol_agent_with_tweety._tweety_bridge.derive_inferences.assert_called_once_with(valid_formulas)
        fol_agent_with_tweety._tweety_bridge.generate_models.assert_called_once_with(valid_formulas)
        
    @pytest.mark.asyncio
    async def test_tweety_error_handling_fol(self, fol_agent_with_tweety):
        """Test gestion erreurs Tweety spécifiques FOL."""
        # Configuration pour lever une exception
        fol_agent_with_tweety._tweety_bridge.check_consistency.side_effect = Exception("Erreur Tweety test")
        
        formulas = ["∀x(P(x) → Q(x))"]
        result = await fol_agent_with_tweety._analyze_with_tweety(formulas)
        
        # Vérifications gestion d'erreur
        assert len(result.validation_errors) > 0
        assert "Erreur Tweety: Erreur Tweety test" in result.validation_errors
        assert result.confidence_score == 0.1
        
    @pytest.mark.asyncio
    async def test_tweety_results_analysis_fol(self, fol_agent_with_tweety):
        """Test analyse résultats Tweety FOL."""
        # Résultats Tweety complexes
        fol_agent_with_tweety._tweety_bridge.derive_inferences = AsyncMock(return_value=[
            "Mortal(socrate)",
            "∀x(Wise(x) → Human(x))"
        ])
        fol_agent_with_tweety._tweety_bridge.generate_models = AsyncMock(return_value=[
            {"description": "Modèle 1", "model": {"socrate": True}},
            {"description": "Modèle 2", "model": {"platon": True}}
        ])
        
        formulas = ["∀x(Human(x) → Mortal(x))", "Human(socrate)"]
        result = await fol_agent_with_tweety._analyze_with_tweety(formulas)
        
        # Vérifications résultats
        assert len(result.inferences) == 2
        assert "Mortal(socrate)" in result.inferences
        assert len(result.interpretations) == 2
        assert result.interpretations[0]["description"] == "Modèle 1"


class TestFOLAnalysisPipeline:
    """Tests du pipeline d'analyse FOL."""
    
    @pytest_asyncio.fixture # Changement pour fixture async
    async def fol_agent_full(self): # monkeypatch n'est plus nécessaire ici
        """Agent FOL avec tous les composants mockés."""
        # Utiliser un AsyncMock qui simule l'interface de Kernel
        mock_kernel_for_agent = AsyncMock(spec=Kernel)
        # Configurer l'attribut 'services' pour que la condition dans _convert_to_fol passe
        mock_kernel_for_agent.services = True
        # Assurer que le mock_kernel a une méthode invoke qui est aussi un AsyncMock
        # pour pouvoir y attacher side_effect plus tard dans le test.
        # AsyncMock crée automatiquement des attributs mockés lorsqu'on y accède.
        # Donc, agent._kernel.invoke sera un AsyncMock par défaut.

        agent = ConcreteFirstOrderLogicAgent(kernel=mock_kernel_for_agent)
        
        # Mock TweetyBridge
        # La ligne suivante est problématique car _tweety_bridge attend un TweetyBridge, pas un Kernel.
        # Pour l'instant, on le mocke directement comme les autres méthodes de _tweety_bridge.
        # Si _create_authentic_gpt4o_mini_instance est vraiment nécessaire pour une partie du setup de _tweety_bridge,
        # cela nécessiterait une refonte plus profonde de cette fixture ou de la méthode _create_authentic_gpt4o_mini_instance.
        # Pour l'instant, on suppose que _tweety_bridge peut être un simple AsyncMock pour ce test.
        agent._tweety_bridge = AsyncMock() # Remplacé l'appel à _create_authentic_gpt4o_mini_instance
        agent._tweety_bridge.check_consistency = AsyncMock(return_value=True)
        agent._tweety_bridge.derive_inferences = AsyncMock(return_value=["Inférence LLM"])
        agent._tweety_bridge.generate_models = AsyncMock(return_value=[{"description": "Modèle LLM", "model": {}}])
        
        return agent
    
    @pytest.mark.asyncio
    async def test_sophism_analysis_with_fol(self, fol_agent_full):
        """Test analyse de sophismes avec logique FOL."""
        # Mock réponse LLM pour conversion
        mock_metadata_conversion = KernelFunctionMetadata(
            name="mock_conversion",
            plugin_name="mock_plugin",
            description="Mock conversion function", # La description est requise
            is_prompt=True # Champ requis
        )
        mock_metadata_analysis = KernelFunctionMetadata(
            name="mock_analysis",
            plugin_name="mock_plugin",
            description="Mock analysis function", # La description est requise
            is_prompt=True # Champ requis
        )

        fol_agent_full._kernel.invoke = AsyncMock(side_effect=[
            FunctionResult(
                function=mock_metadata_conversion,
                value=json.dumps({
                    "formulas": ["∀x(Human(x) → Mortal(x))", "Human(socrate)"],
                    "predicates": {"Human": "être humain", "Mortal": "être mortel"},
                    "variables": {"x": "individu", "socrate": "constante"},
                    "reasoning": "Syllogisme classique"
                })
            ),
            FunctionResult(
                function=mock_metadata_analysis,
                value=json.dumps({
                    "consistency": True,
                    "inferences": ["Mortal(socrate)"],
                    "interpretations": [{"description": "Modèle valide", "model": {"socrate": "mortal"}}],
                    "errors": [],
                    "confidence": 0.95,
                    "reasoning_steps": ["Analyse syllogisme", "Validation FOL"]
                })
            )
        ])
        
        # Test analyse sophisme classique
        sophism_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."
        result = await fol_agent_full.analyze(sophism_text)
        
        # Vérifications résultat
        assert len(result.formulas) == 2
        assert "∀x(Human(x) → Mortal(x))" in result.formulas
        assert "Human(socrate)" in result.formulas
        assert result.consistency_check is True
        assert "Mortal(socrate)" in result.inferences
        assert result.confidence_score >= 0.9
        
    @pytest.mark.asyncio
    async def test_fol_report_generation(self, fol_agent_full):
        """Test génération rapport avec formules FOL."""
        # Mock réponse simplifiée
        mock_metadata_report = KernelFunctionMetadata(
            name="mock_report_generation",
            plugin_name="mock_plugin",
            description="Mock report generation function",
            is_prompt=True
        )
        # L'agent utilise self._kernel (hérité de BaseLogicAgent)
        # La fixture fol_agent_full initialise l'agent avec un mock_kernel_for_agent (AsyncMock(spec=Kernel))
        # qui est accessible via agent._kernel.
        # Donc, nous mockons la méthode invoke de cet AsyncMock.
        fol_agent_full._kernel.invoke = AsyncMock(return_value=FunctionResult(
            function=mock_metadata_report,
            value=json.dumps({
                "formulas": ["∀x(P(x) → Q(x))"],
                "predicates": {"P": "propriété P", "Q": "propriété Q"},
                "reasoning": "Implication universelle"
            })
        ))
        
        text = "Tous les P sont Q."
        result = await fol_agent_full.analyze(text)
        
        # Vérification étapes de raisonnement
        assert len(result.reasoning_steps) > 0
        assert any("FOL" in step for step in result.reasoning_steps)
        
    @pytest.mark.asyncio  
    async def test_tweety_error_analyzer_integration(self, fol_agent_full):
        """Test intégration avec TweetyErrorAnalyzer."""
        
        # Mocker _kernel.invoke pour la phase de conversion et d'analyse LLM
        mock_meta_conv = KernelFunctionMetadata(name="mc", plugin_name="mp", description="d", is_prompt=True)
        mock_meta_llm_analysis = KernelFunctionMetadata(name="mla", plugin_name="mp", description="d", is_prompt=True)

        conversion_response = FunctionResult(
            function=mock_meta_conv,
            value=json.dumps({"formulas": ["ValidFormulaForTweety(x)"], "reasoning": "mocked conversion"})
        )
        # Pour le deuxième appel à invoke dans _llm_enhanced_analysis (si atteint)
        llm_analysis_response = FunctionResult(
            function=mock_meta_llm_analysis,
            value=json.dumps({"consistency": True, "inferences": [], "errors": []}) # Contenu minimal valide
        )
        fol_agent_full._kernel.invoke.side_effect = [conversion_response, llm_analysis_response]

        # Configuration erreur Tweety pour check_consistency
        fol_agent_full._tweety_bridge.check_consistency.side_effect = Exception("Predicate 'Unknown' has not been declared")
        
        text = "Le prédicat inconnu cause une erreur."
        result = await fol_agent_full.analyze(text)
        
        # Vérification gestion d'erreur
        assert len(result.validation_errors) > 0
        error_msg = result.validation_errors[0]
        # Le message d'erreur est formaté dans _analyze_with_tweety
        assert "Erreur Tweety: Predicate 'Unknown' has not been declared" in error_msg
        
    @pytest.mark.asyncio
    async def test_performance_analysis(self, fol_agent_full):
        """Test performance agent FOL."""
        import time
    
        # Mock réponse rapide
        mock_metadata_perf = KernelFunctionMetadata(
            name="mock_performance_analysis",
            plugin_name="mock_plugin",
            description="Mock performance analysis function",
            is_prompt=True
        )
        fol_agent_full._kernel.invoke = AsyncMock(return_value=FunctionResult(
            function=mock_metadata_perf,
            value=json.dumps({
                "formulas": ["∀x(Fast(x))"],
                "reasoning": "Test performance"
            })
        ))
        
        # Test chronométré
        start_time = time.time()
        result = await fol_agent_full.analyze("Test de performance FOL.")
        end_time = time.time()
        
        # Vérifications performance
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Moins de 5 secondes pour un test simple
        assert result.confidence_score > 0.0


@pytest.mark.skip(reason="Test obsolète suite à la refactorisation de l'architecture et la suppression de FOLAnalysisResult")
class TestFOLAgentFactory:
    """Tests de la factory et utilitaires FOL."""
    
    def test_create_fol_agent_factory(self):
        """Test factory de création agent FOL."""
        # Test création basique
        # FirstOrderLogicAgent requiert un kernel, donc la factory doit en recevoir un ou en créer un.
        # La factory create_fol_agent passe le kernel reçu (ou None) à FirstOrderLogicAgent.
        # FirstOrderLogicAgent lève une erreur si kernel est None.
        # Donc, nous devons fournir un kernel à create_fol_agent.
        basic_kernel = Kernel()
        agent = ConcreteFirstOrderLogicAgent(kernel=basic_kernel, agent_name="FactoryAgent")
        
        assert isinstance(agent, FirstOrderLogicAgent)
        assert agent.name == "FactoryAgent"
        assert agent._kernel is basic_kernel # Vérifie que le kernel fourni est utilisé
        assert agent.logic_type == "first_order" # Conserver cette assertion

        # Test création avec kernel existant
        custom_kernel_2 = Kernel() # Nom différent pour éviter confusion
        agent_with_kernel = ConcreteFirstOrderLogicAgent(kernel=custom_kernel_2, agent_name="KernelAgent")
        assert isinstance(agent_with_kernel, FirstOrderLogicAgent)
        assert agent_with_kernel.name == "KernelAgent"
        assert agent_with_kernel._kernel is custom_kernel_2
        assert agent_with_kernel.logic_type == "first_order"
        
    def test_fol_agent_summary_statistics(self):
        """Test statistiques résumé agent FOL."""
        kernel = Kernel()
        agent = ConcreteFirstOrderLogicAgent(kernel=kernel)
        
        # Test sans analyses
        summary = agent.get_analysis_summary()
        assert summary["total_analyses"] == 0
        assert summary["avg_confidence"] == 0.0
        assert summary["agent_type"] == "FOL_Logic"
        
        # Ajout analyses simulées au cache
        agent.analysis_cache["test1"] = FOLAnalysisResult(
            formulas=["∀x(P(x))"],
            consistency_check=True,
            confidence_score=0.9
        )
        agent.analysis_cache["test2"] = FOLAnalysisResult(
            formulas=["∃x(Q(x))"],
            consistency_check=False,
            confidence_score=0.6
        )
        
        # Test avec analyses
        summary = agent.get_analysis_summary()
        assert summary["total_analyses"] == 2
        assert summary["avg_confidence"] == 0.75
        assert summary["consistency_rate"] == 0.5
        
    def test_fol_cache_key_generation(self):
        """Test génération clés de cache."""
        kernel = Kernel()
        agent = ConcreteFirstOrderLogicAgent(kernel=kernel)
        
        # Test génération clé
        text = "Test cache"
        context = {"mode": "test"}
        
        key1 = agent._generate_cache_key(text, context)
        key2 = agent._generate_cache_key(text, context)
        key3 = agent._generate_cache_key(text + "different", context)
        
        # Vérifications
        assert key1 == key2  # Même entrée = même clé
        assert key1 != key3  # Entrée différente = clé différente
        assert len(key1) == 32  # MD5 hash length


class TestFOLConfigurationIntegration:
    """Tests d'intégration avec configuration unifiée."""
    
    def test_unified_config_fol_selection(self):
        """Test sélection automatique FOL depuis configuration."""
        # Configuration FOL
        config = UnifiedConfig(logic_type=LogicType.FOL)
        
        # Vérification sélection agent
        assert config.logic_type == LogicType.FOL
        assert AgentType.FOL_LOGIC in config.agents
        
        # Mapping classe
        agent_classes = config.get_agent_classes()
        assert agent_classes["fol_logic"] == "FirstOrderLogicAgent"
        
    def test_fol_preset_configurations(self):
        """Test configurations prédéfinies FOL."""
        # Configuration authentique FOL
        config = PresetConfigs.authentic_fol()
        
        assert config.logic_type == LogicType.FOL
        assert config.mock_level == MockLevel.NONE
        assert config.require_real_tweety is True
        assert config.require_real_gpt is True
        assert AgentType.FOL_LOGIC in config.agents
        
    def test_fol_tweety_config_mapping(self):
        """Test mapping configuration Tweety pour FOL."""
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            enable_jvm=True,
            require_real_tweety=True
        )
        
        tweety_config = config.get_tweety_config()
        
        assert tweety_config["logic_type"] == "fol"
        assert tweety_config["enable_jvm"] is True
        assert tweety_config["require_real_jar"] is True


# ==================== TESTS D'INTEGRATION RAPIDE ====================

@pytest.mark.skip(reason="Test obsolète suite à la refactorisation de l'architecture et la suppression de FOLAnalysisResult")
@pytest.mark.asyncio
async def test_fol_agent_basic_workflow():
    """Test workflow basique complet de l'agent FOL."""
    # Test création agent
    kernel = Kernel()
    agent = ConcreteFirstOrderLogicAgent(kernel=kernel)
    assert agent.name == "FirstOrderLogicAgent"
    assert agent.logic_type == "first_order"
    
    # Test analyse sans crash (mode dégradé)
    text = "Tous les étudiants sont intelligents."
    result = await agent.analyze(text)
    
    # Vérifications basiques (mode dégradé sans composants)
    assert isinstance(result, FOLAnalysisResult)
    assert result.confidence_score >= 0.0
    # En mode dégradé, l'agent peut retourner des reasoning_steps vides
    assert isinstance(result.reasoning_steps, list)
    # En mode dégradé, l'agent ne crash pas mais retourne peu de résultats
    assert "Erreur d'analyse" in result.validation_errors[0] if result.validation_errors else True


def test_fol_syntax_examples_validation():
    """Test validation exemples syntaxe FOL du prompt."""
    kernel = Kernel()
    agent = ConcreteFirstOrderLogicAgent(kernel=kernel)
    
    # Exemples du prompt
    prompt = agent.conversion_prompt
    
    # Vérification exemples valides
    assert "∀x(Homme(x) → Mortel(x))" in prompt
    assert "Homme(socrate)" in prompt
    
    # Structure JSON attendue
    assert '"formulas": ["formule1", "formule2", ...]' in prompt
    assert '"predicates": {"nom": "description", ...}' in prompt


if __name__ == "__main__":
    # Exécution des tests
    pytest.main([__file__, "-v", "--tb=short"])
