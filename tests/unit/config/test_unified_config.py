
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le système de configuration unifié (UnifiedConfig).

Ce module teste toutes les fonctionnalités critiques du système de configuration
dynamique, incluant :
- Validation des paramètres de logique (FOL/PL/Modal)
- Niveaux de mock (NONE/PARTIAL/FULL)
- Tailles de taxonomie (3/1000 nœuds)
- Modes d'orchestration
- Contraintes d'authenticité
"""

import os
import pytest
import asyncio
from unittest.mock import patch # Ajout de patch

from typing import List, Dict, Any

# Import du système de configuration à tester
from config.unified_config import (
    UnifiedConfig,
    LogicType,
    MockLevel,
    OrchestrationType,
    SourceType,
    TaxonomySize,
    AgentType,
    PresetConfigs,
    load_config_from_env,
    validate_config
)


class TestUnifiedConfig:
    def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        async def _run():
            config = UnifiedConfig()
            return await config.get_kernel_with_gpt4o_mini()
        return asyncio.run(_run())
        
    def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        async def _run():
            try:
                kernel = self._create_authentic_gpt4o_mini_instance()
                result = await kernel.invoke("chat", input=prompt)
                return str(result)
            except Exception as e:
                logger.warning(f"Appel LLM authentique échoué: {e}")
                return "Authentic LLM call failed"
        return asyncio.run(_run())

    """Tests unitaires pour la classe UnifiedConfig."""
    
    def test_default_configuration_loading(self):
        """Test le chargement de la configuration par défaut."""
        config = UnifiedConfig()
        
        # Vérification des valeurs par défaut
        assert config.logic_type == LogicType.FOL
        assert config.mock_level == MockLevel.NONE
        assert config.taxonomy_size == TaxonomySize.FULL
        assert config.orchestration_type == OrchestrationType.UNIFIED
        assert config.require_real_gpt is True
        assert config.require_real_tweety is True
        assert config.require_full_taxonomy is True
        assert config.validate_tool_calls is True
        assert config.enable_jvm is True
        
        # Vérification des agents par défaut
        expected_agents = [AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS]
        assert config.agents == expected_agents
        
        # Vérification des modes d'analyse par défaut
        assert "fallacies" in config.analysis_modes
        assert "coherence" in config.analysis_modes
        assert "semantic" in config.analysis_modes

    def test_logic_type_validation(self):
        """Test la validation des types de logique."""
        # Test logique FOL valide
        config_fol = UnifiedConfig(logic_type=LogicType.FOL)
        assert config_fol.logic_type == LogicType.FOL
        
        # Test logique PL valide
        config_pl = UnifiedConfig(logic_type=LogicType.PL)
        assert config_pl.logic_type == LogicType.PL
        
        # Test logique Modal (problématique mais autorisée avec mocks)
        config_modal = UnifiedConfig(
            logic_type=LogicType.MODAL,
            mock_level=MockLevel.PARTIAL,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
        assert config_modal.logic_type == LogicType.MODAL
        
        # Test alias FIRST_ORDER
        config_first_order = UnifiedConfig(logic_type=LogicType.FIRST_ORDER)
        assert config_first_order.logic_type == LogicType.FIRST_ORDER

    def test_mock_level_validation(self):
        """Test la validation des niveaux de mock."""
        # Test NONE (authentique)
        config_none = UnifiedConfig(mock_level=MockLevel.NONE)
        assert config_none.mock_level == MockLevel.NONE
        assert config_none.require_real_gpt is True
        assert config_none.require_real_tweety is True
        assert config_none.taxonomy_size == TaxonomySize.FULL
        
        # Test PARTIAL (développement)
        config_partial = UnifiedConfig(
            mock_level=MockLevel.PARTIAL,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
        assert config_partial.mock_level == MockLevel.PARTIAL
        
        # Test FULL (test)
        config_full = UnifiedConfig(
            mock_level=MockLevel.FULL,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
        assert config_full.mock_level == MockLevel.FULL

    def test_taxonomy_size_validation(self):
        """Test la validation des tailles de taxonomie."""
        # Test taxonomie complète (1000 nœuds)
        config_full = UnifiedConfig(taxonomy_size=TaxonomySize.FULL)
        assert config_full.taxonomy_size == TaxonomySize.FULL
        taxonomy_config = config_full.get_taxonomy_config()
        assert taxonomy_config["node_count"] == 1000
        assert taxonomy_config["size"] == "full"
        
        # Test taxonomie mock (3 nœuds)
        config_mock = UnifiedConfig(
            taxonomy_size=TaxonomySize.MOCK,
            mock_level=MockLevel.PARTIAL,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
        assert config_mock.taxonomy_size == TaxonomySize.MOCK
        taxonomy_config = config_mock.get_taxonomy_config()
        assert taxonomy_config["node_count"] == 3
        assert taxonomy_config["size"] == "mock"

    def test_orchestration_mode_validation(self):
        """Test la validation des modes d'orchestration."""
        # Test UNIFIED
        config_unified = UnifiedConfig(orchestration_type=OrchestrationType.UNIFIED)
        assert config_unified.orchestration_type == OrchestrationType.UNIFIED
        
        # Test CONVERSATION
        config_conversation = UnifiedConfig(orchestration_type=OrchestrationType.CONVERSATION)
        assert config_conversation.orchestration_type == OrchestrationType.CONVERSATION
        
        # Test REAL (legacy)
        config_real = UnifiedConfig(orchestration_type=OrchestrationType.REAL)
        assert config_real.orchestration_type == OrchestrationType.REAL
        
        # Test CUSTOM
        config_custom = UnifiedConfig(orchestration_type=OrchestrationType.CUSTOM)
        assert config_custom.orchestration_type == OrchestrationType.CUSTOM

    def test_invalid_combinations(self):
        """Test les combinaisons invalides de paramètres."""
        # Test 1: Mock level != NONE avec require_real_* = True
        with pytest.raises(ValueError, match="Configuration incohérente"):
            UnifiedConfig(
                mock_level=MockLevel.PARTIAL,
                require_real_gpt=True
            )
        
        with pytest.raises(ValueError, match="Configuration incohérente"):
            UnifiedConfig(
                mock_level=MockLevel.FULL,
                require_real_tweety=True
            )
        
        # Test 2: FOL_LOGIC agent sans JVM
        with pytest.raises(ValueError, match="FOL_LOGIC agent nécessite enable_jvm=True"):
            UnifiedConfig(
                agents=[AgentType.FOL_LOGIC],
                enable_jvm=False
            )

    def test_valid_combinations(self):
        """Test les combinaisons valides de paramètres."""
        # Configuration production optimale
        config_prod = UnifiedConfig(
            logic_type=LogicType.FOL,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL,
            orchestration_type=OrchestrationType.UNIFIED,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS]
        )
        assert config_prod.logic_type == LogicType.FOL
        assert config_prod.mock_level == MockLevel.NONE
        assert config_prod.require_real_gpt is True
        assert config_prod.require_real_tweety is True
        
        # Configuration développement
        config_dev = UnifiedConfig(
            logic_type=LogicType.FOL,
            mock_level=MockLevel.PARTIAL,
            taxonomy_size=TaxonomySize.MOCK,
            orchestration_type=OrchestrationType.CONVERSATION,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
        assert config_dev.mock_level == MockLevel.PARTIAL
        assert config_dev.taxonomy_size == TaxonomySize.MOCK
        
        # Configuration test rapide
        config_test = UnifiedConfig(
            logic_type=LogicType.PL,
            mock_level=MockLevel.FULL,
            taxonomy_size=TaxonomySize.MOCK,
            orchestration_type=OrchestrationType.CONVERSATION,
            agents=[AgentType.INFORMAL, AgentType.SYNTHESIS],
            enable_jvm=False,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False
        )
        assert config_test.logic_type == LogicType.PL
        assert config_test.enable_jvm is False

    def test_configuration_persistence(self):
        """Test la persistance et sérialisation de la configuration."""
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            mock_level=MockLevel.NONE,
            taxonomy_size=TaxonomySize.FULL,
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC],
            analysis_modes=["fallacies", "coherence"]
        )
        
        # Test conversion en dictionnaire
        config_dict = config.to_dict()
        assert config_dict["logic_type"] == "fol"
        assert config_dict["mock_level"] == "none"
        assert config_dict["taxonomy_size"] == "full"
        assert config_dict["agents"] == ["informal", "fol_logic"]
        assert config_dict["analysis_modes"] == ["fallacies", "coherence"]
        
        # Test section authenticité
        assert "authenticity" in config_dict
        auth = config_dict["authenticity"]
        assert auth["require_real_gpt"] is True
        assert auth["require_real_tweety"] is True
        assert auth["require_full_taxonomy"] is True
        assert auth["validate_tool_calls"] is True

    def test_agent_normalization(self):
        """Test la normalisation automatique des agents."""
        # Test remplacement automatique LOGIC -> FOL_LOGIC pour FOL
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            agents=[AgentType.INFORMAL, AgentType.LOGIC, AgentType.SYNTHESIS]
        )
        
        # Vérification du remplacement automatique
        assert AgentType.FOL_LOGIC in config.agents
        assert AgentType.LOGIC not in config.agents
        assert AgentType.INFORMAL in config.agents
        assert AgentType.SYNTHESIS in config.agents

    def test_authenticity_constraints(self):
        """Test l'application automatique des contraintes d'authenticité."""
        config = UnifiedConfig(mock_level=MockLevel.NONE)
        
        # Vérification de l'application automatique
        assert config.require_real_gpt is True
        assert config.require_real_tweety is True
        assert config.require_full_taxonomy is True
        assert config.validate_tool_calls is True
        assert config.taxonomy_size == TaxonomySize.FULL
        assert config.enable_cache is False

    def test_service_configurations(self):
        """Test les configurations spécialisées pour les services."""
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            mock_level=MockLevel.NONE,
            timeout_seconds=120
        )
        
        # Test configuration Tweety
        tweety_config = config.get_tweety_config()
        assert tweety_config["enable_jvm"] is True
        assert tweety_config["require_real_jar"] is True
        assert tweety_config["logic_type"] == "fol"
        assert tweety_config["timeout_seconds"] == 120
        
        # Test configuration LLM
        llm_config = config.get_llm_config()
        assert llm_config["require_real_service"] is True
        assert llm_config["mock_level"] == "none"
        assert llm_config["validate_responses"] is True
        assert llm_config["timeout_seconds"] == 120
        
        # Test configuration Taxonomie
        taxonomy_config = config.get_taxonomy_config()
        assert taxonomy_config["size"] == "full"
        assert taxonomy_config["require_full_load"] is True
        assert taxonomy_config["node_count"] == 1000

    def test_get_agent_classes(self):
        """Test le mapping des agents vers leurs classes."""
        config = UnifiedConfig(
            agents=[AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS, AgentType.PM]
        )
        
        agent_classes = config.get_agent_classes()
        assert agent_classes["informal"] == "InformalAnalysisAgent"
        assert agent_classes["fol_logic"] == "FirstOrderLogicAgent"
        assert agent_classes["synthesis"] == "SynthesisAgent"
        assert agent_classes["pm"] == "ProjectManagerAgent"


class TestPresetConfigs:
    """Tests pour les configurations prédéfinies."""
    
    def test_authentic_fol_preset(self):
        """Test la configuration authentique FOL."""
        config = PresetConfigs.authentic_fol()
        
        assert config.logic_type == LogicType.FOL
        assert config.mock_level == MockLevel.NONE
        assert config.taxonomy_size == TaxonomySize.FULL
        assert config.orchestration_type == OrchestrationType.UNIFIED
        assert config.require_real_gpt is True
        assert config.require_real_tweety is True
        assert config.require_full_taxonomy is True
        
        expected_agents = [AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS]
        assert config.agents == expected_agents

    def test_authentic_pl_preset(self):
        """Test la configuration authentique PL."""
        config = PresetConfigs.authentic_pl()
        
        assert config.logic_type == LogicType.PL
        assert config.mock_level == MockLevel.NONE
        assert config.taxonomy_size == TaxonomySize.FULL

    def test_development_preset(self):
        """Test la configuration de développement."""
        config = PresetConfigs.development()
        
        assert config.logic_type == LogicType.PL
        assert config.mock_level == MockLevel.PARTIAL
        assert config.taxonomy_size == TaxonomySize.MOCK
        assert config.enable_jvm is False
        assert config.require_real_gpt is False
        assert config.require_real_tweety is False
        
        # Vérifier que les agents n'incluent pas FOL_LOGIC (pas de JVM)
        assert AgentType.FOL_LOGIC not in config.agents
        assert AgentType.INFORMAL in config.agents
        assert AgentType.SYNTHESIS in config.agents

    def test_testing_preset(self):
        """Test la configuration de test."""
        config = PresetConfigs.testing()
        
        assert config.logic_type == LogicType.PL
        assert config.mock_level == MockLevel.FULL
        assert config.taxonomy_size == TaxonomySize.MOCK
        assert config.enable_jvm is False
        assert config.timeout_seconds == 30
        
        # Les agents de test ne doivent pas inclure FOL_LOGIC (pas de JVM)
        assert AgentType.FOL_LOGIC not in config.agents
        assert AgentType.INFORMAL in config.agents
        assert AgentType.SYNTHESIS in config.agents


class TestConfigUtilities:
    """Tests pour les utilitaires de configuration."""
    
    @patch.dict(os.environ, {
        'UNIFIED_LOGIC_TYPE': 'fol',
        'UNIFIED_AGENTS': 'informal,fol_logic,synthesis',
        'UNIFIED_ORCHESTRATION': 'conversation',
        'UNIFIED_MOCK_LEVEL': 'partial',
        'UNIFIED_REQUIRE_REAL_GPT': 'true',
        'UNIFIED_REQUIRE_REAL_TWEETY': 'true'
    })
    def test_load_config_from_env(self):
        """Test le chargement de configuration depuis l'environnement."""
        config = load_config_from_env()
        
        assert config.logic_type == LogicType.FOL
        assert config.orchestration_type == OrchestrationType.CONVERSATION
        assert config.mock_level == MockLevel.PARTIAL
        assert config.require_real_gpt is True
        assert config.require_real_tweety is True
        
        expected_agents = [AgentType.INFORMAL, AgentType.FOL_LOGIC, AgentType.SYNTHESIS]
        assert config.agents == expected_agents

    @patch.dict(os.environ, {}, clear=True)
    def test_load_config_from_env_defaults(self):
        """Test le chargement avec variables d'environnement vides."""
        config = load_config_from_env()
        
        # Doit utiliser les valeurs par défaut
        assert config.logic_type == LogicType.FOL
        assert config.mock_level == MockLevel.NONE
        assert config.orchestration_type == OrchestrationType.UNIFIED

    def test_validate_config_success(self):
        """Test la validation d'une configuration valide."""
        config = UnifiedConfig(
            logic_type=LogicType.FOL,
            mock_level=MockLevel.NONE,
            agents=[AgentType.INFORMAL, AgentType.SYNTHESIS]
        )
        
        errors = validate_config(config)
        assert len(errors) == 0

    def test_validate_config_errors(self):
        """Test la validation avec erreurs."""
        # Créer une config qui passe __post_init__ mais échoue validate_config
        config_for_validation = UnifiedConfig(
            mock_level=MockLevel.PARTIAL,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False,
            enable_jvm=True,
            agents=[AgentType.INFORMAL]  # Pas de FOL_LOGIC pour éviter l'exception
        )
        
        # Modifier manuellement pour tester
        config_for_validation.require_real_gpt = True  # Créer incohérence
        config_for_validation.require_real_tweety = False  # Créer incohérence avec JVM
        
        errors = validate_config(config_for_validation)
        assert len(errors) > 0
        assert any("Mock level != none mais require_real_gpt=True" in error for error in errors)
        assert any("JVM activée mais Tweety non-réel" in error for error in errors)

    def test_validate_config_jvm_agents_mismatch(self):
        """Test validation agents logiques sans JVM."""
        config = UnifiedConfig(
            logic_type=LogicType.PL,  # Éviter FOL qui force FOL_LOGIC
            mock_level=MockLevel.FULL,
            enable_jvm=False,
            require_real_gpt=False,
            require_real_tweety=False,
            require_full_taxonomy=False,
            agents=[AgentType.INFORMAL, AgentType.SYNTHESIS]
        )
        
        # Modifier manuellement pour tester
        config.agents.append(AgentType.FOL_LOGIC)
        
        errors = validate_config(config)
        assert len(errors) > 0
        assert any("Agents logiques nécessitent JVM" in error for error in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])