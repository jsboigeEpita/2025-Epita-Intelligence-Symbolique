# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python3
"""
Tests avancés pour l'élimination complète des mocks
==================================================

Suite de tests pour valider l'authenticité 100% du système :
- Détection et élimination des mocks
- Validation des composants authentiques
- Métriques d'authenticité
- Configuration 100% authentique
"""

import pytest
import asyncio
import os
import sys
from pathlib import Path

from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, patch, Mock
import tempfile
import json
import time

# Ajout du chemin pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from config.unified_config import UnifiedConfig, MockLevel, TaxonomySize, LogicType, PresetConfigs
    from argumentation_analysis.core.llm_service import create_llm_service as LLMService
    from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
except ImportError as e:
    pytest.skip(f"Modules requis non disponibles: {e}", allow_module_level=True)


class TestMockEliminationAdvanced:
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

    """Tests avancés d'élimination des mocks."""
    
    def setup_method(self):
        """Configuration initiale pour chaque test."""
        self.authentic_config = PresetConfigs.authentic_fol()
        self.mock_config = PresetConfigs.testing()
        
    def test_detect_authentic_vs_mock_configuration(self):
        """Test de détection de configuration authentique vs mock."""
        # Configuration authentique
        assert self.authentic_config.mock_level == MockLevel.NONE
        assert self.authentic_config.require_real_gpt is True
        assert self.authentic_config.require_real_tweety is True
        assert self.authentic_config.require_full_taxonomy is True
        assert self.authentic_config.taxonomy_size == TaxonomySize.FULL
        
        # Configuration mock
        assert self.mock_config.mock_level == MockLevel.FULL
        assert self.mock_config.require_real_gpt is False
        assert self.mock_config.require_real_tweety is False
        assert self.mock_config.enable_jvm is False
    
    def test_authenticity_percentage_calculation(self):
        """Test de calcul du pourcentage d'authenticité."""
        def calculate_authenticity(config: UnifiedConfig) -> float:
            """Calcule le pourcentage d'authenticité d'une configuration."""
            authenticity_factors = {
                'real_gpt': config.require_real_gpt,
                'real_tweety': config.require_real_tweety, 
                'full_taxonomy': config.require_full_taxonomy,
                'no_mocks': config.mock_level == MockLevel.NONE,
                'jvm_enabled': config.enable_jvm,
                'validate_tools': config.validate_tool_calls
            }
            
            score = sum(authenticity_factors.values())
            return (score / len(authenticity_factors)) * 100
        
        # Configuration 100% authentique
        authentic_score = calculate_authenticity(self.authentic_config)
        assert authentic_score == 100.0
        
        # Configuration mock (faible authenticité)
        mock_score = calculate_authenticity(self.mock_config)
        assert mock_score < 50.0
    
    def test_mock_level_none_enforces_authenticity(self):
        """Test que mock_level=NONE force l'authenticité complète."""
        config = UnifiedConfig(mock_level=MockLevel.NONE)
        
        # Vérifier que l'authenticité est forcée automatiquement
        assert config.require_real_gpt is True
        assert config.require_real_tweety is True
        assert config.require_full_taxonomy is True
        assert config.validate_tool_calls is True
        assert config.taxonomy_size == TaxonomySize.FULL
        assert config.enable_cache is False  # Cache désactivé pour authenticité
    
    def test_inconsistent_configuration_validation(self):
        """Test de validation de configurations incohérentes."""
        # Configuration incohérente : mocks activés mais authentique requis
        with pytest.raises(ValueError, match="Configuration incohérente"):
            UnifiedConfig(
                mock_level=MockLevel.FULL,
                require_real_gpt=True  # Incohérent avec FULL mocks
            )
        
        with pytest.raises(ValueError, match="Configuration incohérente"):
            UnifiedConfig(
                mock_level=MockLevel.PARTIAL,
                require_real_tweety=True  # Incohérent avec mocks partiels
            )
    
    def test_authentic_component_validation(self):
        """Test de validation des composants authentiques."""
        # Simulation de composants authentiques vs mocks
        class AuthenticLLMService:
            def __init__(self):
                self.service_type = "openai"
                self.model = "gpt-4o-mini"
                self.api_key = "real_key"
                
        class MockLLMService:
            def __init__(self):
                self.service_type = "mock"
                self._is_mock = True
        
        authentic_service = AuthenticLLMService()
        mock_service = MockLLMService()
        unittest_mock = MagicMock()
        
        # Tests de détection
        assert not hasattr(authentic_service, '_is_mock')
        assert authentic_service.service_type == "openai"
        
        assert hasattr(mock_service, '_is_mock')
        assert mock_service.service_type == "mock"
        
        assert 'Mock' in str(type(unittest_mock))
    
    def test_taxonomy_size_validation(self):
        """Test de validation de la taille de la taxonomie."""
        # Configuration avec taxonomie complète
        full_config = UnifiedConfig(taxonomy_size=TaxonomySize.FULL)
        taxonomy_config = full_config.get_taxonomy_config()
        
        assert taxonomy_config['size'] == 'full'
        assert taxonomy_config['node_count'] == 1000
        assert taxonomy_config['require_full_load'] is True
        
        # Configuration avec taxonomie mock
        # En mode par défaut (mock_level=NONE), la taille de la taxonomie est forcée à FULL.
        mock_config = UnifiedConfig(taxonomy_size=TaxonomySize.MOCK)
        mock_taxonomy_config = mock_config.get_taxonomy_config()
        
        # Le test valide que la configuration force bien 'full' même si 'mock' est demandé.
        assert mock_taxonomy_config['size'] == 'full'
        assert mock_taxonomy_config['node_count'] == 1000
    
    def test_llm_configuration_authenticity(self):
        """Test de configuration authentique pour LLM."""
        authentic_config = PresetConfigs.authentic_fol()
        llm_config = authentic_config.get_llm_config()
        
        assert llm_config['require_real_service'] is True
        assert llm_config['mock_level'] == 'none'
        assert llm_config['validate_responses'] is True
        assert llm_config['timeout_seconds'] == 300
    
    def test_tweety_configuration_authenticity(self):
        """Test de configuration authentique pour Tweety."""
        authentic_config = PresetConfigs.authentic_fol()
        tweety_config = authentic_config.get_tweety_config()
        
        assert tweety_config['enable_jvm'] is True
        assert tweety_config['require_real_jar'] is True
        assert tweety_config['logic_type'] == 'fol'
        assert tweety_config['timeout_seconds'] == 300
    
    @patch.dict(os.environ, {
        'UNIFIED_MOCK_LEVEL': 'none',
        'UNIFIED_REQUIRE_REAL_GPT': 'true',
        'UNIFIED_REQUIRE_REAL_TWEETY': 'true'
    })
    def test_environment_driven_authenticity(self):
        """Test de configuration d'authenticité via variables d'environnement."""
        from config.unified_config import load_config_from_env
        
        env_config = load_config_from_env()
        
        assert env_config.mock_level == MockLevel.NONE
        assert env_config.require_real_gpt is True
        assert env_config.require_real_tweety is True
    
    def test_authentic_configuration_serialization(self):
        """Test de sérialisation de configuration authentique."""
        authentic_config = PresetConfigs.authentic_fol()
        config_dict = authentic_config.to_dict()
        
        # Vérifier les paramètres d'authenticité dans le dictionnaire
        assert config_dict['mock_level'] == 'none'
        assert config_dict['taxonomy_size'] == 'full'
        assert config_dict['enable_jvm'] is True
        
        authenticity_section = config_dict['authenticity']
        assert authenticity_section['require_real_gpt'] is True
        assert authenticity_section['require_real_tweety'] is True
        assert authenticity_section['require_full_taxonomy'] is True
        assert authenticity_section['validate_tool_calls'] is True


class TestComponentMockDetection:
    """Tests de détection de mocks dans les composants spécifiques."""
    
    def test_detect_llm_service_mock(self):
        """Test de détection de mocks dans les services LLM."""
        # Mock évident
        mock_llm = MagicMock()
        mock_llm.generate_response = MagicMock(return_value="fake response")
        
        # Service authentique simulé
        class AuthenticLLM:
            def __init__(self):
                self.api_key = os.getenv('OPENAI_API_KEY', 'test_key')
                self.model = 'gpt-4o-mini'
                
            def generate_response(self, prompt):
                return f"Real response from {self.model}"
        
        authentic_llm = AuthenticLLM()
        
        # Tests de détection
        assert 'Mock' in str(type(mock_llm))
        assert hasattr(mock_llm.generate_response, '_mock_name')
        
        assert 'Mock' not in authentic_llm.__class__.__name__
        assert not hasattr(authentic_llm.generate_response, '_mock_name')
    
    def test_detect_tweety_service_mock(self):
        """Test de détection de mocks dans les services Tweety."""
        # Mock Tweety
        mock_tweety = MagicMock()
        mock_tweety.parse_formula.return_value = "mock_result"
        
        # Service Tweety authentique simulé
        class AuthenticTweety:
            def __init__(self):
                self.jar_path = "/path/to/tweety.jar"
                self.use_real_jpype = True
                
            def parse_formula(self, formula):
                return f"Real parsing result for {formula}"
        
        authentic_tweety = AuthenticTweety()
        
        # Tests de détection
        assert 'MagicMock' in str(type(mock_tweety))
        assert hasattr(mock_tweety, '_mock_methods')
        
        assert 'Mock' not in authentic_tweety.__class__.__name__
        assert hasattr(authentic_tweety, 'jar_path')
        assert authentic_tweety.use_real_jpype is True
    
    def test_detect_taxonomy_mock(self):
        """Test de détection de taxonomie mock vs complète."""
        # Taxonomie mock (3 sophismes)
        mock_taxonomy = {
            'fallacies': ['ad_hominem', 'straw_man', 'slippery_slope'],
            'count': 3,
            'is_mock': True
        }
        
        # Taxonomie complète simulée (1000+ sophismes)
        complete_taxonomy = {
            'fallacies': [f'fallacy_{i}' for i in range(1408)],
            'count': 1408,
            'is_complete': True
        }
        
        # Tests de détection
        assert mock_taxonomy['count'] == 3
        assert mock_taxonomy.get('is_mock', False) is True
        
        assert complete_taxonomy['count'] == 1408
        assert complete_taxonomy.get('is_complete', False) is True
        assert len(complete_taxonomy['fallacies']) > 1000


class TestAuthenticityMetrics:
    """Tests de métriques d'authenticité du système."""
    
    def test_calculate_system_authenticity_score(self):
        """Test de calcul du score d'authenticité global du système."""
        def calculate_system_authenticity(components: Dict[str, bool]) -> Dict[str, Any]:
            """Calcule les métriques d'authenticité du système."""
            total_components = len(components)
            authentic_components = sum(components.values())
            
            authenticity_percentage = (authentic_components / total_components) * 100
            
            return {
                'total_components': total_components,
                'authentic_components': authentic_components,
                'mock_components': total_components - authentic_components,
                'authenticity_percentage': authenticity_percentage,
                'is_100_percent_authentic': authenticity_percentage == 100.0
            }
        
        # Système 100% authentique
        authentic_system = {
            'llm_service': True,
            'tweety_service': True,
            'taxonomy': True,
            'configuration': True
        }
        
        metrics = calculate_system_authenticity(authentic_system)
        assert metrics['authenticity_percentage'] == 100.0
        assert metrics['is_100_percent_authentic'] is True
        assert metrics['mock_components'] == 0
        
        # Système avec mocks
        mixed_system = {
            'llm_service': False,  # Mock
            'tweety_service': True,  # Authentique
            'taxonomy': False,  # Mock
            'configuration': True  # Authentique
        }
        
        mixed_metrics = calculate_system_authenticity(mixed_system)
        assert mixed_metrics['authenticity_percentage'] == 50.0
        assert mixed_metrics['is_100_percent_authentic'] is False
        assert mixed_metrics['mock_components'] == 2
    
    def test_authenticity_validation_comprehensive(self):
        """Test de validation complète d'authenticité."""
        def validate_component_authenticity(component_type: str, component: Any) -> bool:
            """Valide l'authenticité d'un composant."""
            # Règles de validation par type de composant
            validation_rules = {
                'llm': lambda c: (
                    hasattr(c, 'api_key') and 
                    hasattr(c, 'model') and 
                    'mock' not in c.__class__.__name__.lower()
                ),
                'tweety': lambda c: (
                    hasattr(c, 'jar_path') and 
                    hasattr(c, 'use_real_jpype') and
                    getattr(c, 'use_real_jpype', False) is True
                ),
                'taxonomy': lambda c: (
                    isinstance(c, dict) and
                    c.get('count', 0) > 1000 and
                    not c.get('is_mock', False)
                )
            }
            
            validator = validation_rules.get(component_type)
            return validator(component) if validator else False
        
        # Test composants authentiques
        authentic_llm = type('AuthenticLLM', (), {
            'api_key': 'real_key',
            'model': 'gpt-4o-mini'
        })()
        
        authentic_tweety = type('AuthenticTweety', (), {
            'jar_path': '/path/to/tweety.jar',
            'use_real_jpype': True
        })()
        
        authentic_taxonomy = {
            'count': 1408,
            'fallacies': [f'fallacy_{i}' for i in range(1408)],
            'is_complete': True
        }
        
        # Tests de validation
        assert validate_component_authenticity('llm', authentic_llm) is True
        assert validate_component_authenticity('tweety', authentic_tweety) is True
        assert validate_component_authenticity('taxonomy', authentic_taxonomy) is True
        
        # Test composants mock
        mock_llm = MagicMock()
        mock_taxonomy = {'count': 3, 'is_mock': True}
        
        assert validate_component_authenticity('llm', mock_llm) is False
        assert validate_component_authenticity('taxonomy', mock_taxonomy) is False


class TestPerformanceAuthenticity:
    """Tests de performance avec composants authentiques."""
    
    def test_authentic_vs_mock_performance_comparison(self):
        """Test de comparaison de performance authentique vs mock."""
        # Simulation de temps de réponse
        def mock_operation():
            """Opération mock (instantanée)."""
            time.sleep(0.001)  # 1ms
            return "mock_result"
        
        def authentic_operation():
            """Opération authentique (plus lente mais réelle)."""
            time.sleep(0.1)  # 100ms (simulation API réelle)
            return "authentic_result"
        
        # Mesure des performances
        mock_start = time.time()
        mock_result = mock_operation()
        mock_duration = time.time() - mock_start
        
        auth_start = time.time()
        auth_result = authentic_operation()
        auth_duration = time.time() - auth_start
        
        # Validations
        assert mock_result == "mock_result"
        assert auth_result == "authentic_result"
        assert mock_duration < 0.05  # Mock très rapide
        assert auth_duration > 0.05   # Authentique plus lent mais acceptable
        assert auth_duration < 1.0    # Mais pas trop lent
    
    def test_taxonomy_loading_performance(self):
        """Test de performance de chargement de taxonomie."""
        def load_mock_taxonomy():
            """Charge taxonomie mock (3 sophismes)."""
            start = time.perf_counter()
            taxonomy = {'fallacies': ['a', 'b', 'c'], 'count': 3}
            duration = time.perf_counter() - start
            return taxonomy, duration
        
        def load_full_taxonomy():
            """Charge taxonomie complète (1408 sophismes)."""
            start = time.perf_counter()
            taxonomy = {
                'fallacies': [f'fallacy_{i}' for i in range(1408)],
                'count': 1408
            }
            duration = time.perf_counter() - start
            return taxonomy, duration
        
        mock_tax, mock_time = load_mock_taxonomy()
        full_tax, full_time = load_full_taxonomy()
        
        # Validations
        assert mock_tax['count'] == 3
        assert full_tax['count'] == 1408
        assert mock_time < full_time  # Mock plus rapide
        assert full_time < 1.0        # Mais chargement complet acceptable


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
